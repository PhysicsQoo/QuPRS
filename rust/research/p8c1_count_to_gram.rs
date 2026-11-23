//! G8D1 research bridge: D8C1 verified two-copy counts -> rank-two
//! coherent Gram -> exact PSD property. No exhaustive primary enumeration
//! occurs on this *verifier* path. The D8C1 producer remains exhaustive.
//!
//! Three typed obligations: (i,i), (j,j), and (i,j), all for the SAME
//! source-bound P8C1, source-bound SCG1 span and bad-output projector.
//! The checker rejects a swapped, incomplete or forged count transcript.
//! Limited to n<=3, h<=4. No normative OpenQASM or solver trust.
use super::{
    sha256,Check,Error,Cursor,CoherentGram,CoherentSpanSpec,CoherentVerdict,
    parse_scg1_spec,encode_p8g1_claim,gram_psd_verdict,
    two_copy_count_trace,checked_i64,
};

const MAX_STRUCTURE:usize=65_536;
const MAX_TRACE:usize=65_536;
const G8D1_OBLIGATIONS:usize=3;

#[derive(Debug,Clone,PartialEq,Eq)]
pub(super) struct VerifiedBridge {
    pub(super) gram:CoherentGram,
    pub(super) verdict:CoherentVerdict,
    pub(super) counted_nodes:usize,
    pub(super) early_leaves:usize,
}
pub(super) fn four_root_coefficients(counts:&[u16;8])->[i128;4]{
    std::array::from_fn(|i|counts[i] as i128-counts[i+4] as i128)
}
pub(super) fn real_coefficients(counts:&[u16;8])->Check<(i64,i64)>{
    let four=four_root_coefficients(counts);
    // A physically diagonal Gram element is exactly real; this is also
    // an independent consistency check on the counting proof.
    if four[2]!=0 || four[1]!=-four[3]{
        return Err(Error::InvalidProof);
    }
    Ok((checked_i64(four[0])?,checked_i64(four[1])?))
}
fn structural_metadata(data:&[u8])->Check<(usize,usize,u64,usize)>{
    if data.len()<81 || data.len()>MAX_STRUCTURE || &data[..4]!=b"S8C1"{
        return Err(Error::InvalidProof);
    }
    let mut reader=Cursor::new(&data[68..79]);
    let first=reader.u8()? as usize;
    let second=reader.u8()? as usize;
    let bad=reader.u64()?;
    let paths=reader.u8()? as usize;
    Ok((first,second,bad,paths))
}
pub(super) fn verify(
    source:&[u8],proof:&[u8],spec_bytes:&[u8],
    structural:[&[u8];G8D1_OBLIGATIONS],
    traces:[&[u8];G8D1_OBLIGATIONS],
    gram_claim:&[u8],
)->Check<VerifiedBridge>{
    let spec:CoherentSpanSpec=parse_scg1_spec(spec_bytes)?;
    let pair=[(spec.first,spec.first),(spec.second,spec.second),
        (spec.first,spec.second)];
    let mut roots=[[0u16;8];G8D1_OBLIGATIONS];
    let mut stats_nodes=0usize;
    let mut stats_early=0usize;
    let mut agreed_h=None;
    for index in 0..G8D1_OBLIGATIONS {
        if structural[index].len()>MAX_STRUCTURE || traces[index].len()>MAX_TRACE{
            return Err(Error::UnknownResource);
        }
        let (first,second,bad,h)=structural_metadata(structural[index])?;
        if (first,second)!=pair[index] || bad!=spec.bad_mask{
            return Err(Error::InvalidProof);
        }
        if let Some(previous)=agreed_h{
            if h!=previous{return Err(Error::InvalidProof);}
        }
        agreed_h=Some(h);
        // D8C1 independently checks source/P8C1/S8C1 byte commitments,
        // full structural DAG and conservative local Shannon steps.
        // It never trusts the serialized count and never enumerates paths.
        let result=two_copy_count_trace::verify(
            source,proof,structural[index],traces[index]
        )?;
        roots[index]=result.buckets;
        stats_nodes=stats_nodes.checked_add(result.stats.nodes)
            .ok_or(Error::UnknownResource)?;
        stats_early=stats_early.checked_add(result.stats.early_leaves)
            .ok_or(Error::UnknownResource)?;
    }
    let h=agreed_h.ok_or(Error::InvalidProof)?;
    if h>4{return Err(Error::UnknownResource);}
    let first=checked_i64(spec.first as i128)?;
    let second=checked_i64(spec.second as i128)?;
    let gram=CoherentGram {
        n:u8::try_from(spec.n).map_err(|_|Error::UnknownResource)?,
        h:u8::try_from(h).map_err(|_|Error::UnknownResource)?,
        first:u8::try_from(first).map_err(|_|Error::UnknownResource)?,
        second:u8::try_from(second).map_err(|_|Error::UnknownResource)?,
        bad_mask:spec.bad_mask,
        diag0:real_coefficients(&roots[0])?,
        diag1:real_coefficients(&roots[1])?,
        off:four_root_coefficients(&roots[2]).map(checked_i64)
            .into_iter().collect::<Check<Vec<_>>>()?
            .try_into().map_err(|_|Error::InvalidProof)?,
    };
    // This is an existing independently typed P8G1 Gram claim (176B).
    // Compare exact canonical bytes; no path histogram or exhaustive
    // count is recomputed here. Its digest commits source, spec and P8C1.
    if gram_claim.len()!=176 || gram_claim!=encode_p8g1_claim(
        source,proof,spec_bytes,&gram
    ){
        return Err(Error::InvalidProof);
    }
    let verdict=gram_psd_verdict(&gram,&spec)?;
    Ok(VerifiedBridge{
        gram,verdict,counted_nodes:stats_nodes,early_leaves:stats_early
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reject_nonreal_diagonal_and_fake_metadata(){
        let mut counts=[0u16;8];
        counts[2]=1;
        assert_eq!(real_coefficients(&counts),Err(Error::InvalidProof));
        counts=[0;8]; counts[1]=2;counts[3]=1;
        assert_eq!(real_coefficients(&counts),Err(Error::InvalidProof));
        counts=[0;8];counts[1]=2;counts[7]=2;
        assert_eq!(real_coefficients(&counts),Ok((0,2)));
        let mut header=[0u8;81];header[..4].copy_from_slice(b"S8C1");
        header[68]=0;header[69]=1;header[78]=2;
        header[70..78].copy_from_slice(&1u64.to_le_bytes());
        assert_eq!(structural_metadata(&header),Ok((0,1,1,2)));
        header[0]=0;
        assert_eq!(structural_metadata(&header),Err(Error::InvalidProof));
    }
}
