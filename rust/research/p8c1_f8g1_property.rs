//! F8G1: a bounded, source+spec-bound rank-two coherent property certificate.
//!
//! Three independent F8C1 source-to-count proofs (i,i),(j,j),(i,j), each
//! including symbolic source semantics, the P8C1 prefix proof, S8C1 root
//! predicates and exact D8C1 or M8D1 counting, are composed into a
//! canonical P8G1 Gram and exact PSD verdict. An UNSAFE verdict must carry
//! a separately verified P8W1 constructive normalized-state witness.
//!
//! Scope: strict 1..3q, <=4 Hadamard paths, exact Clifford+T source grammar
//! of F8C1, rank-two SCG1, and fixed-precision checked cyclotomic integers.
//! This is NOT a general OpenQASM proof, full symbolic theorem, external
//! WMC proof, production SourceTrust or a production "PROVED" verdict.
use super::{
    sha256,Check,Error,Cursor,CoherentGram,CoherentVerdict,
    parse_scg1_spec,replay_state,gram_psd_verdict,encode_p8g1_claim,
    verify_p8w1_witness,checked_i64,P8G1_BYTES,P8W1_BYTES,Real,
    count_to_gram,f8c1_chain,
};
const MAGIC:&[u8;4]=b"F8G1";
const LENGTH:usize=4+1+14*32+1;
#[derive(Debug,Clone,PartialEq,Eq)]
pub(super) struct ResultProperty {
    pub(super) verdict:CoherentVerdict,
    pub(super) prefix_checks:usize,
    pub(super) root_checks:usize,
    pub(super) proof_method_mask:u8,
    pub(super) witness_gap:Option<Real>,
}
fn checked_layers(
    source:&[u8],p8:&[u8],spec_bytes:&[u8],
    structures:[&[u8];3],traces:[&[u8];3],f8s:[&[u8];3],
    gram_claim:&[u8],witness:&[u8],
)->Check<ResultProperty>{
    let spec=parse_scg1_spec(spec_bytes)?;
    let (_,state)=replay_state(source,p8)?;
    if state.n!=spec.n || state.n>3 || state.paths>4{
        return Err(Error::UnsupportedSource);
    }
    let expected_pairs=[
        (spec.first,spec.first),
        (spec.second,spec.second),
        (spec.first,spec.second),
    ];
    let mut roots=[[0u16;8];3];
    let mut prefix_checks=0usize;
    let mut root_checks=0usize;
    let mut method_mask=0u8;
    for i in 0..3{
        let proof=f8c1_chain::verify(
            source,p8,structures[i],traces[i],f8s[i]
        )?;
        if (proof.first,proof.second)!=expected_pairs[i] ||
            proof.bad!=spec.bad_mask{
            return Err(Error::InvalidProof);
        }
        roots[i]=proof.buckets;
        prefix_checks=prefix_checks.checked_add(proof.prefix_checks)
            .ok_or(Error::UnknownResource)?;
        root_checks=root_checks.checked_add(proof.root_checks)
            .ok_or(Error::UnknownResource)?;
        method_mask|=1u8 << proof.method;
    }
    let off=count_to_gram::four_root_coefficients(&roots[2])
        .map(checked_i64).into_iter().collect::<Check<Vec<_>>>()?
        .try_into().map_err(|_|Error::InvalidProof)?;
    let gram=CoherentGram{
        n:state.n as u8,h:state.paths as u8,
        first:spec.first as u8,second:spec.second as u8,
        bad_mask:spec.bad_mask,
        diag0:count_to_gram::real_coefficients(&roots[0])?,
        diag1:count_to_gram::real_coefficients(&roots[1])?,
        off,
    };
    if gram_claim.len()!=P8G1_BYTES ||
        gram_claim!=encode_p8g1_claim(source,p8,spec_bytes,&gram){
        return Err(Error::InvalidProof);
    }
    let verdict=gram_psd_verdict(&gram,&spec)?;
    let witness_gap=match verdict{
        CoherentVerdict::ScopedSatisfied=>{
            if !witness.is_empty(){return Err(Error::InvalidProof);}
            None
        }
        CoherentVerdict::ScopedViolated{..}=>{
            if witness.len()!=P8W1_BYTES{return Err(Error::InvalidProof);}
            // Checks the exact source/spec/Gram binding, positive norm and
            // STRICT negative quadratic on the normalized coherent input;
            // a non-PSD label without an actual witness cannot be accepted.
            let (_,gap)=verify_p8w1_witness(
                source,p8,spec_bytes,gram_claim,witness
            )?;
            Some(gap)
        }
    };
    Ok(ResultProperty{
        verdict,prefix_checks,root_checks,
        proof_method_mask:method_mask,witness_gap,
    })
}
fn canonical(
    source:&[u8],p8:&[u8],spec_bytes:&[u8],
    structures:[&[u8];3],traces:[&[u8];3],f8s:[&[u8];3],
    gram_claim:&[u8],witness:&[u8],
    result:&ResultProperty
)->Vec<u8>{
    let mut out=Vec::with_capacity(LENGTH);
    out.extend_from_slice(MAGIC);
    out.push(1); // protocol version
    for bytes in [
        source,p8,spec_bytes,
        structures[0],structures[1],structures[2],
        traces[0],traces[1],traces[2],
        f8s[0],f8s[1],f8s[2],
        gram_claim,witness
    ] {
        out.extend_from_slice(&sha256(bytes));
    }
    let tag=match result.verdict{
        CoherentVerdict::ScopedSatisfied=>0,
        CoherentVerdict::ScopedViolated{..}=>1,
    };
    out.push(tag);
    debug_assert_eq!(out.len(),LENGTH);
    out
}
pub(super) fn encode(
    source:&[u8],p8:&[u8],spec_bytes:&[u8],
    structures:[&[u8];3],traces:[&[u8];3],f8s:[&[u8];3],
    gram_claim:&[u8],witness:&[u8],
)->Check<Vec<u8>>{
    let property=checked_layers(
        source,p8,spec_bytes,structures,traces,f8s,gram_claim,witness
    )?;
    Ok(canonical(source,p8,spec_bytes,
        structures,traces,f8s,gram_claim,witness,&property))
}
pub(super) fn verify(
    source:&[u8],p8:&[u8],spec_bytes:&[u8],
    structures:[&[u8];3],traces:[&[u8];3],f8s:[&[u8];3],
    gram_claim:&[u8],witness:&[u8],claim:&[u8],
)->Check<ResultProperty>{
    if claim.len()!=LENGTH{return Err(Error::InvalidProof);}
    // Identity commitments alone are not proof: the bound artifacts must
    // all be re-read, checked and recomposed before a property verdict.
    let mut reader=Cursor::new(claim);
    if reader.bytes(4)?!=MAGIC ||reader.u8()?!=1{
        return Err(Error::InvalidProof);
    }
    for bytes in [
        source,p8,spec_bytes,
        structures[0],structures[1],structures[2],
        traces[0],traces[1],traces[2],
        f8s[0],f8s[1],f8s[2],
        gram_claim,witness
    ] {
        if reader.bytes(32)?!=sha256(bytes){
            return Err(Error::InvalidProof);
        }
    }
    let tag=reader.u8()?;
    if tag>1 || reader.at!=claim.len(){
        return Err(Error::InvalidProof);
    }
    let property=checked_layers(
        source,p8,spec_bytes,structures,traces,f8s,gram_claim,witness
    )?;
    if claim!=canonical(source,p8,spec_bytes,
        structures,traces,f8s,gram_claim,witness,&property){
        return Err(Error::InvalidProof);
    }
    Ok(property)
}
