//! Tiny, bounded two-copy weighted-counting research obligation.
//! For source-verified Path-sum (n,h,F,Phi), compute
//!    2^h G_ij = sum_{y,z} [F(i,y)=F(j,z) in B]
//!                          zeta_8^(Phi(j,z)-Phi(i,y)).
//!
//! The complete truth table is the independent finite checking oracle.
//! This is NOT a scalable CNF encoding, solver certificate, or general WMC.
use super::{sha256,replay_state,Check,Error,State,Cursor};
const W8C1_BYTES:usize=95;
const MAX_DOUBLE_PATH_VARS:usize=12;

#[derive(Clone,Debug,PartialEq,Eq)]
pub(super) struct TwoCopyCount {
    pub(super) first:u8,
    pub(super) second:u8,
    pub(super) bad_mask:u64,
    pub(super) h:u8,
    pub(super) buckets:[u16;8],
}
fn assignment(state:&State,input:usize,paths:usize)->(usize,u8){
    let bits=(input as u64)|((paths as u64)<<state.n);
    let mut output=0usize;
    for (q,anf) in state.outputs.iter().enumerate() {
        let mut parity=false;
        for monomial in anf {
            // Tseitin-free independent interpretation of the GF(2)
            // monomial under a fixed concrete Boolean assignment.
            if bits&monomial==*monomial {parity=!parity;}
        }
        if parity {output|=1usize<<q;}
    }
    let mut phase=0usize;
    for(&monomial,&coefficient) in &state.phase {
        if bits&monomial==monomial {
            phase=(phase+coefficient as usize)%8;
        }
    }
    (output,phase as u8)
}
pub(super) fn enumerate_pairs(
    state:&State,first:usize,second:usize,bad_mask:u64
)->Check<TwoCopyCount>{
    if state.n==0 || state.n>3 || state.paths*2>MAX_DOUBLE_PATH_VARS {
        return Err(Error::UnknownResource);
    }
    let dim=1usize<<state.n;
    if first>=dim||second>=dim||bad_mask==0 ||
        bad_mask & !((1u64<<dim)-1)!=0 {
        return Err(Error::InvalidSource);
    }
    let paths=1usize<<state.paths;
    let mut buckets=[0u16;8];
    for y in 0..paths {
        let (out_i,phase_i)=assignment(state,first,y);
        if bad_mask&(1u64<<out_i)==0 {continue;}
        for z in 0..paths {
            let (out_j,phase_j)=assignment(state,second,z);
            if out_i!=out_j {continue;}
            let k=(phase_j as usize+8-phase_i as usize)%8;
            buckets[k]=buckets[k].checked_add(1)
                .ok_or(Error::UnknownResource)?;
        }
    }
    Ok(TwoCopyCount{
        first:first as u8,second:second as u8,bad_mask,
        h:state.paths as u8,buckets
    })
}
pub(super) fn cyclotomic_four(t:&TwoCopyCount)->[i128;4]{
    std::array::from_fn(|i|t.buckets[i] as i128-t.buckets[i+4] as i128)
}
pub(super) fn encode_w8c1(source:&[u8],proof:&[u8],t:&TwoCopyCount)
->[u8;W8C1_BYTES]{
    let mut out=[0u8;W8C1_BYTES];
    out[..4].copy_from_slice(b"W8C1");
    out[4..36].copy_from_slice(&sha256(source));
    out[36..68].copy_from_slice(&sha256(proof));
    out[68]=t.first;out[69]=t.second;
    out[70..78].copy_from_slice(&t.bad_mask.to_le_bytes());
    out[78]=t.h;
    for (index,&count) in t.buckets.iter().enumerate(){
        out[79+2*index..81+2*index].copy_from_slice(&count.to_le_bytes());
    }
    out
}
pub(super) fn verify_w8c1(
    source:&[u8],proof:&[u8],claim:&[u8]
)->Check<TwoCopyCount>{
    if claim.len()!=W8C1_BYTES {return Err(Error::InvalidProof);}
    let mut cur=Cursor::new(claim);
    if cur.bytes(4)?!=b"W8C1"
        ||cur.bytes(32)?!=sha256(source)
        ||cur.bytes(32)?!=sha256(proof) {
        return Err(Error::InvalidProof);
    }
    let first=cur.u8()? as usize;
    let second=cur.u8()? as usize;
    let bad_mask=cur.u64()?;
    let h=cur.u8()?;
    let mut counts=[0u16;8];
    for value in &mut counts{*value=cur.u16()? as u16;}
    if cur.at!=claim.len(){return Err(Error::InvalidProof);}
    let (_,state)=replay_state(source,proof)?;
    if state.paths>6 || state.n>3{return Err(Error::UnknownResource);}
    if h as usize!=state.paths{return Err(Error::InvalidProof);}
    let actual=enumerate_pairs(&state,first,second,bad_mask)?;
    if counts!=actual.buckets{return Err(Error::InvalidProof);}
    Ok(actual)
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::{CoherentGram,path_coherent_gram,gram_psd_verdict};
    #[test]
    fn h_one_qubit_two_copy_closed_form() {
        let state=State{
            n:1,paths:1,
            outputs:vec![std::collections::BTreeSet::from([2])],
            phase:std::collections::BTreeMap::from([(3,4)]),
        };
        let w=enumerate_pairs(&state,0,1,1).unwrap();
        assert_eq!(w.buckets,[1,0,0,0,0,0,0,0]);
        assert_eq!(cyclotomic_four(&w),[1,0,0,0]);
        let d=enumerate_pairs(&state,0,0,1).unwrap();
        assert_eq!(d.buckets,[1,0,0,0,0,0,0,0]);
        println!("W8C1_TWO_COPY_H h=1 offdiag=1 diagonal=1 exact=true");
    }
    #[test]
    fn rejects_resource_and_aliasing_invalid_inputs(){
        let large=State{
            n:1,paths:7,
            outputs:vec![std::collections::BTreeSet::from([1])],
            phase:std::collections::BTreeMap::new()
        };
        assert_eq!(enumerate_pairs(&large,0,0,1),
            Err(Error::UnknownResource));
        let small=State{
            n:1,paths:0,
            outputs:vec![std::collections::BTreeSet::from([1])],
            phase:std::collections::BTreeMap::new()
        };
        assert_eq!(enumerate_pairs(&small,2,0,1),Err(Error::InvalidSource));
        assert_eq!(enumerate_pairs(&small,0,0,0),Err(Error::InvalidSource));
        println!("W8C1_FAIL_CLOSED double_paths_cap=12 out_of_range=true zero_bad=true");
    }
}
