//! Bounded source-linked 2-copy CNF research prototype.
//!
//! C8C1 encodes eight *canonical full-assignment blocking CNFs*. For each
//! eighth-root phase bucket k, a clause excludes each (y,z) assignment
//! not satisfying the two-copy same-bad-output / phase-difference predicate.
//! All surviving assignments carry weight zeta8^k. The checker does not
//! trust the serialized CNF or counts: it checks every clause against the
//! independently evaluated source-bound P8C1 state and recounts models.
//!
//! This is exhaustive exponential truth-table CNF, NOT a scalable Tseitin
//! encoding, third-party weighted model counting certificate, or solver proof.
use super::{sha256,replay_state,Check,Error,State,Cursor};
use super::two_copy_wmc;
const C8C1_MAX_PATHS:usize=4;
const C8C1_MAX_BYTES:usize=12_000;
const C8C1_HEADER:usize=79;

#[derive(Clone,Debug,PartialEq,Eq)]
pub(super) struct BucketCnf {
    pub(super) first:u8,
    pub(super) second:u8,
    pub(super) bad_mask:u64,
    pub(super) h:u8,
    // One CNF per phase bucket, each clause (positive,negative) masks.
    pub(super) clauses:[Vec<(u16,u16)>;8],
}
fn eval(state:&State,input:usize,path:usize)->(usize,u8){
    let bits=(input as u64)|((path as u64)<<state.n);
    let mut output=0usize;
    for (index,terms) in state.outputs.iter().enumerate(){
        let parity=terms.iter().filter(|&&mon|bits&mon==mon).count()%2==1;
        if parity {output|=1<<index;}
    }
    let mut exponent=0u8;
    for (&mon,&coefficient) in &state.phase {
        if bits&mon==mon {exponent=(exponent+coefficient)%8;}
    }
    (output,exponent)
}
fn pair_bucket(state:&State,first:usize,second:usize,bad_mask:u64,assignment:usize)
    ->Option<usize>
{
    let path_mask=(1usize<<state.paths)-1;
    let (a,ka)=eval(state,first,assignment&path_mask);
    let (b,kb)=eval(state,second,assignment>>state.paths);
    if a!=b || (bad_mask&(1u64<<a))==0 {return None;}
    Some((kb as usize+8-ka as usize)%8)
}
fn clause_from_excluded(excluded:usize,variables:usize)->(u16,u16){
    let mask=(1usize<<variables)-1;
    ((!excluded&mask) as u16,excluded as u16)
}
fn excludes_assignment((positive,negative):(u16,u16),assignment:usize)->bool{
    ((positive as usize)&assignment)==0 &&
    ((negative as usize)&!assignment)==0
}
pub(super) fn build(state:&State,first:usize,second:usize,bad_mask:u64)
    ->Check<BucketCnf>
{
    if state.paths>C8C1_MAX_PATHS || state.n==0 || state.n>3{
        return Err(Error::UnknownResource);
    }
    let dimension=1usize<<state.n;
    if first>=dimension || second>=dimension || bad_mask==0 ||
       bad_mask & !((1u64<<dimension)-1)!=0 {
        return Err(Error::InvalidSource);
    }
    let total=1usize<<(2*state.paths);
    let mut clauses:[Vec<(u16,u16)>;8]=std::array::from_fn(|_|Vec::new());
    for assignment in 0..total {
        let permitted=pair_bucket(state,first,second,bad_mask,assignment);
        for(bucket,list)in clauses.iter_mut().enumerate(){
            if permitted!=Some(bucket){
                list.push(clause_from_excluded(assignment,2*state.paths));
            }
        }
    }
    Ok(BucketCnf {first:first as u8,second:second as u8,
        bad_mask,h:state.paths as u8,clauses})
}
pub(super) fn count_models(c:&BucketCnf)->Check<[u16;8]>{
    if c.h as usize>C8C1_MAX_PATHS{return Err(Error::UnknownResource);}
    let vars=2*c.h as usize;
    let total=1usize<<vars;
    let mask=(total-1) as u16;
    let mut result=[0u16;8];
    for (bucket,clauses) in c.clauses.iter().enumerate(){
        for &(p,n) in clauses {
            if p&n!=0 || (p|n)!=mask {
                return Err(Error::InvalidProof);
            }
        }
        for assignment in 0..total {
            if clauses.iter().all(|&clause|!excludes_assignment(clause,assignment)){
                result[bucket]=result[bucket].checked_add(1)
                    .ok_or(Error::UnknownResource)?;
            }
        }
    }
    Ok(result)
}
pub(super) fn encode(source:&[u8],proof:&[u8],c:&BucketCnf)->Check<Vec<u8>>{
    let mut out=Vec::with_capacity(C8C1_HEADER+8*4*(1<<(2*c.h)));
    out.extend_from_slice(b"C8C1");
    out.extend_from_slice(&sha256(source));
    out.extend_from_slice(&sha256(proof));
    out.extend_from_slice(&[c.first,c.second]);
    out.extend_from_slice(&c.bad_mask.to_le_bytes());
    out.push(c.h);
    for clauses in &c.clauses {
        out.extend_from_slice(&(u16::try_from(clauses.len())
            .map_err(|_|Error::UnknownResource)?).to_le_bytes());
        for &(p,n) in clauses{
            out.extend_from_slice(&p.to_le_bytes());
            out.extend_from_slice(&n.to_le_bytes());
        }
    }
    if out.len()>C8C1_MAX_BYTES {return Err(Error::UnknownResource);}
    Ok(out)
}
pub(super) fn verify(source:&[u8],proof:&[u8],serialized:&[u8])
    ->Check<([u16;8],[u16;8])>
{
    if serialized.len()>C8C1_MAX_BYTES{return Err(Error::UnknownResource);}
    let mut cur=Cursor::new(serialized);
    if cur.bytes(4)?!=b"C8C1" ||
       cur.bytes(32)?!=sha256(source) ||
       cur.bytes(32)?!=sha256(proof) {
        return Err(Error::InvalidProof);
    }
    let(first,second)=(cur.u8()? as usize,cur.u8()? as usize);
    let bad_mask=cur.u64()?;
    let h=cur.u8()? as usize;
    if h>C8C1_MAX_PATHS{return Err(Error::UnknownResource);}
    let (_,state)=replay_state(source,proof)?;
    if state.paths!=h{return Err(Error::InvalidProof);}
    let dimension=1usize<<state.n;
    if first>=dimension||second>=dimension||bad_mask==0 ||
       bad_mask&!((1u64<<dimension)-1)!=0 {
        return Err(Error::InvalidProof);
    }
    let max_clauses=1usize<<(2*h);
    let mut clauses:[Vec<(u16,u16)>;8]=std::array::from_fn(|_|Vec::new());
    let variable_mask=(max_clauses-1) as u16;
    for bucket in 0..8 {
        let count=cur.u16()?;
        if count>max_clauses{return Err(Error::InvalidProof);}
        let mut previous=None;
        for _ in 0..count {
            let p=cur.u16()? as u16;
            let n=cur.u16()? as u16;
            if p&n!=0||(p|n)!=variable_mask {
                return Err(Error::InvalidProof);
            }
            let excluded=n as usize;
            if previous.is_some_and(|before|excluded<=before) ||
                clause_from_excluded(excluded,2*h)!=(p,n) {
                return Err(Error::InvalidProof);
            }
            // Independent source-bound semantic *clause* check.
            if pair_bucket(&state,first,second,bad_mask,excluded)==Some(bucket){
                return Err(Error::InvalidProof);
            }
            previous=Some(excluded);
            clauses[bucket].push((p,n));
        }
        // Completeness: every assignment not in this bucket must have a
        // blocking clause; no solver-supplied model count is trusted.
        for assignment in 0..max_clauses {
            let excluded=clauses[bucket].binary_search_by_key(
                &assignment,|&(_,negative)|negative as usize
            ).is_ok();
            if excluded!=(pair_bucket(&state,first,second,bad_mask,assignment)!=Some(bucket)){
                return Err(Error::InvalidProof);
            }
        }
    }
    if cur.at!=serialized.len(){return Err(Error::InvalidProof);}
    let cnf=BucketCnf {
        first:first as u8,second:second as u8,bad_mask,h:h as u8,clauses
    };
    let counted=count_models(&cnf)?;
    let independently_counted=two_copy_wmc::enumerate_pairs(
        &state,first,second,bad_mask
    )?.buckets;
    if counted!=independently_counted{return Err(Error::InvalidProof);}
    Ok((counted,independently_counted))
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::{BTreeMap,BTreeSet};
    fn h_state()->State{
        State{n:1,paths:1,outputs:vec![BTreeSet::from([2])],
            phase:BTreeMap::from([(3,4)])}
    }
    #[test]
    fn h_two_copy_cnf_model_count_is_one(){
        let c=build(&h_state(),0,1,1).unwrap();
        assert_eq!(count_models(&c).unwrap(),[1,0,0,0,0,0,0,0]);
        assert_eq!(c.clauses[0].len(),3);
        for k in 1..8{assert_eq!(c.clauses[k].len(),4);}
        println!("C8C1_H_TWO_COPY_CNF models=1 buckets=8 canonical_full_clause=true");
    }
    #[test]
    fn invalid_clause_and_resource_bounds_fail_closed(){
        let c=build(&h_state(),0,1,1).unwrap();
        let mut forged=c.clone();
        forged.clauses[0][0]=(0,0);
        assert_eq!(count_models(&forged),Err(Error::InvalidProof));
        let huge=State{n:1,paths:5,outputs:vec![BTreeSet::from([1])],
            phase:BTreeMap::new()};
        assert_eq!(build(&huge,0,0,1),Err(Error::UnknownResource));
    }
}
