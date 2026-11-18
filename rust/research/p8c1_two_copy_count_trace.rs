//! D8C1: a bounded, source-bound, count-carrying Shannon proof tree.
//!
//! Each node contains [tag, claimed u16 count]:
//!  0 = certified FALSE for the whole remaining primary cube (count 0)
//!  1 = certified TRUE for the whole remaining primary cube (count 2^(m-depth))
//!  2 = split on the next primary path variable with two child nodes.
//! The verifier re-evaluates the canonical S8C1 definitional gate circuit
//! over Kleene three-valued partial assignments; it does NOT enumerate
//! all 2^m assignments or compare a separately solved WMC count.
//!
//! Producer uses a DIFFERENT exhaustive Boolean evaluation for its leaf
//! selection. This minimizes shared checker/prover proof-tree semantics.
//! S8C1's source->network canonical builder is still in the TCB; this is
//! not a machine-checked source-to-CNF theorem or third-party solver proof.
use super::{sha256,Check,Error,Cursor};
use super::two_copy_structural::{self,Structural,Op};
const MAX_BYTES:usize=65_536;
const MAX_NODES:usize=8192;
const MAGIC:&[u8;4]=b"D8C1";
const HEADER:usize=4+32+32+32+1;

#[derive(Debug,Clone,Copy,PartialEq,Eq)]
enum Tri {False,True,Unknown}
fn tri_not(x:Tri)->Tri{
    match x{Tri::False=>Tri::True,Tri::True=>Tri::False,Tri::Unknown=>Tri::Unknown}
}
fn tri_and(x:Tri,y:Tri)->Tri{
    match (x,y) {
        (Tri::False,_)|(_,Tri::False)=>Tri::False,
        (Tri::True,Tri::True)=>Tri::True,
        _=>Tri::Unknown,
    }
}
fn tri_or(x:Tri,y:Tri)->Tri{
    match (x,y) {
        (Tri::True,_)|(_,Tri::True)=>Tri::True,
        (Tri::False,Tri::False)=>Tri::False,
        _=>Tri::Unknown,
    }
}
fn tri_xor(x:Tri,y:Tri)->Tri{
    match(x,y){
        (Tri::True,Tri::True)|(Tri::False,Tri::False)=>Tri::False,
        (Tri::True,Tri::False)|(Tri::False,Tri::True)=>Tri::True,
        _=>Tri::Unknown,
    }
}
// Independent ternary evaluation over partial primary assignments.
// Conservative UNKNOWN is sound; only true/false justify early leaves.
fn partial_bucket(c:&Structural,bucket:usize,depth:usize,prefix:usize)->Check<Tri>{
    if c.primary>8 || depth>c.primary || bucket>=8
        || prefix>>depth!=0 {return Err(Error::InvalidProof);}
    let mut values=Vec::with_capacity(c.primary+c.gates.len());
    for i in 0..c.primary{
        values.push(if i>=depth {Tri::Unknown}
            else if prefix&(1usize<<i)!=0 {Tri::True}
            else {Tri::False});
    }
    for gate in &c.gates {
        let index=values.len();
        let read=|id:u16|->Check<Tri>{
            values.get(id as usize).copied().filter(|_|
                (id as usize)<index).ok_or(Error::InvalidProof)
        };
        let tri=match gate.op {
            Op::Zero=>Tri::False,
            Op::One=>Tri::True,
            Op::Not=>tri_not(read(gate.a)?),
            Op::And=>tri_and(read(gate.a)?,read(gate.b)?),
            Op::Or=>tri_or(read(gate.a)?,read(gate.b)?),
            Op::Xor=>tri_xor(read(gate.a)?,read(gate.b)?),
        };
        values.push(tri);
    }
    values.get(c.bucket[bucket] as usize)
        .copied().ok_or(Error::InvalidProof)
}
#[derive(Debug,Default,Clone,Copy)]
pub(super) struct Stats {
    pub(super) nodes:usize,
    pub(super) early_leaves:usize,
    pub(super) forced_splits:usize,
}
#[derive(Debug)]
pub(super) struct Counts {
    pub(super) buckets:[u16;8],
    pub(super) stats:Stats,
}
fn append_node(bytes:&mut Vec<u8>,tag:u8,count:u16)->Check<()>{
    if bytes.len().checked_add(3).ok_or(Error::UnknownResource)?>MAX_BYTES{
        return Err(Error::UnknownResource);
    }
    bytes.push(tag);
    bytes.extend_from_slice(&count.to_le_bytes());
    Ok(())
}
// Generator: exhaustively checks all completions to choose a whole-cube
// TRUE/FALSE leaf. Checker does NOT use this function or the exhaustive
// evaluate(c, full_assignment) path.
fn generator_node(c:&Structural,bucket:usize,depth:usize,prefix:usize,
    bytes:&mut Vec<u8>,stats:&mut Stats)->Check<u16>{
    stats.nodes+=1;
    if stats.nodes>MAX_NODES{return Err(Error::UnknownResource);}
    let remaining=c.primary-depth;
    let mut true_count=0u16;
    for extension in 0..(1usize<<remaining){
        let full=prefix|(extension<<depth);
        let values=two_copy_structural::evaluate(c,full)?;
        if values[c.bucket[bucket] as usize]{
            true_count=true_count.checked_add(1).ok_or(Error::UnknownResource)?;
        }
    }
    if true_count==0 {
        stats.early_leaves+=1;
        append_node(bytes,0,0)?;
    } else if true_count as usize ==(1usize<<remaining){
        stats.early_leaves+=1;
        append_node(bytes,1,true_count)?;
    } else {
        if depth>=c.primary{return Err(Error::InvalidProof);}
        stats.forced_splits+=1;
        append_node(bytes,2,true_count)?;
        let left=generator_node(c,bucket,depth+1,prefix,bytes,stats)?;
        let right=generator_node(c,bucket,depth+1,prefix|(1<<depth),bytes,stats)?;
        if left.checked_add(right)!=Some(true_count){
            return Err(Error::InvalidProof);
        }
    }
    Ok(true_count)
}
pub(super) fn emit(src:&[u8],proof:&[u8],structural:&[u8])->Check<Vec<u8>>{
    let c=two_copy_structural::verify_schema_without_enumeration(src,proof,structural)?;
    if c.primary>8{return Err(Error::UnknownResource);}
    let mut bytes=Vec::new();
    bytes.extend_from_slice(MAGIC);
    bytes.extend_from_slice(&sha256(src));
    bytes.extend_from_slice(&sha256(proof));
    bytes.extend_from_slice(&sha256(structural));
    bytes.push(c.primary as u8);
    let mut stats=Stats::default();
    for bucket in 0..8 {
        generator_node(&c,bucket,0,0,&mut bytes,&mut stats)?;
    }
    Ok(bytes)
}
fn check_node(c:&Structural,bucket:usize,depth:usize,prefix:usize,
    reader:&mut Cursor<'_>,stats:&mut Stats)->Check<u16>{
    stats.nodes=stats.nodes.checked_add(1).ok_or(Error::UnknownResource)?;
    if stats.nodes>MAX_NODES{return Err(Error::UnknownResource);}
    let tag=reader.u8()?;
    let count=reader.u16()?;
    let known=partial_bucket(c,bucket,depth,prefix)?;
    let remaining=c.primary-depth;
    match known {
        Tri::False=>{
            if tag!=0||count!=0{return Err(Error::InvalidProof);}
            stats.early_leaves+=1;
        }
        Tri::True=>{
            let exact=u16::try_from(1usize<<remaining).map_err(|_|Error::UnknownResource)?;
            if tag!=1||count!=exact{return Err(Error::InvalidProof);}
            stats.early_leaves+=1;
        }
        Tri::Unknown=>{
            if tag!=2||depth==c.primary{return Err(Error::InvalidProof);}
            stats.forced_splits+=1;
            let left=check_node(c,bucket,depth+1,prefix,reader,stats)?;
            let right=check_node(c,bucket,depth+1,prefix|(1usize<<depth),reader,stats)?;
            if left.checked_add(right)!=Some(count){return Err(Error::InvalidProof);}
        }
    }
    Ok(count)
}
pub(super) fn verify(src:&[u8],proof:&[u8],structural:&[u8],
    bytes:&[u8])->Check<Counts>{
    if bytes.len()>MAX_BYTES{return Err(Error::UnknownResource);}
    if bytes.len()<HEADER+8*3{return Err(Error::InvalidProof);}
    let c=two_copy_structural::verify_schema_without_enumeration(src,proof,structural)?;
    if c.primary>8{return Err(Error::UnknownResource);}
    let mut reader=Cursor::new(bytes);
    if reader.bytes(4)?!=MAGIC
        ||reader.bytes(32)?!=sha256(src)
        ||reader.bytes(32)?!=sha256(proof)
        ||reader.bytes(32)?!=sha256(structural)
        ||reader.u8()? as usize!=c.primary {
        return Err(Error::InvalidProof);
    }
    let mut buckets=[0u16;8];
    let mut stats=Stats::default();
    for (bucket,slot) in buckets.iter_mut().enumerate() {
        *slot=check_node(&c,bucket,0,0,&mut reader,&mut stats)?;
    }
    if reader.at!=bytes.len(){return Err(Error::InvalidProof);}
    Ok(Counts{buckets,stats})
}
#[cfg(test)]
mod tests {
    use super::*;
    use super::super::two_copy_structural::{Gate,Op};
    #[test]
    fn partial_kleene_evaluation_can_certify_entire_false_cubes(){
        // One primary x and three deterministic nodes: 0, 1, x AND 0.
        // The bucket is FALSE with the primary unassigned.
        let c=Structural{
            primary:1,
            gates:vec![
                Gate{op:Op::Zero,a:0,b:0},
                Gate{op:Op::One,a:0,b:0},
                Gate{op:Op::And,a:0,b:1},
            ],
            bucket:[3;8],
        };
        assert_eq!(partial_bucket(&c,0,0,0),Ok(Tri::False));
        let mut stream=Vec::new();
        let mut stats=Stats::default();
        assert_eq!(generator_node(&c,0,0,0,&mut stream,&mut stats),Ok(0));
        let mut cursor=Cursor::new(&stream);
        let mut checked=Stats::default();
        assert_eq!(check_node(&c,0,0,0,&mut cursor,&mut checked),Ok(0));
        assert_eq!(checked.nodes,1);
        assert_eq!(checked.early_leaves,1);
    }
    #[test]
    fn partial_kleene_xor_unknown_and_split_counts(){
        let c=Structural{primary:1,gates:vec![Gate{
            op:Op::Xor,a:0,b:0
        }],bucket:[1;8]};
        // x XOR x is semantically false but conservative Kleene XOR
        // returns UNKNOWN: the verifier requires a branch, not a guess.
        assert_eq!(partial_bucket(&c,0,0,0),Ok(Tri::Unknown));
        let mut stream=Vec::new();
        let mut stats=Stats::default();
        assert_eq!(generator_node(&c,0,0,0,&mut stream,&mut stats),Ok(0));
        let mut cursor=Cursor::new(&stream);
        // Generator's exhaustive compression may choose FALSE at root,
        // but checker rejects it because local partial truth is UNKNOWN.
        assert_eq!(check_node(&c,0,0,0,&mut cursor,&mut Stats::default()),
            Err(Error::InvalidProof));
    }
}
