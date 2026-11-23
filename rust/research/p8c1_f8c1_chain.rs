//! F8C1: bounded, source-bound end-to-end proof envelope (research only).
//!
//! The independent checker validates each source/P8C1 prefix and every
//! S8C1 bucket root using compositional GF(2) Boolean-ring polynomials
//! with independent three-bit phase-addition rules. Exact D8C1/M8D1 counts
//! are checked without trusting a solver.
//!
//! BOUNDED SYMBOLIC AUDIT: <=3 qubits, <=4 H paths, OPENQASM 3.0 H/X/CX/
//! T/S/Z/CZ/gphase(pi/4). Primary path enumeration is test-only.
//! QASM 3.1, QASM2, U/u3, controlled sources, symbolic parameters, and
//! production SourceTrust are NOT certified by this envelope.
use super::{
    sha256, Check, Error, Cursor, State, Phase, MAX_SOURCE_BYTES, MAX_PROOF_BYTES,
    MAX_TOTAL_TERMS, MAX_FRAME_TERMS, read_termset, read_phase,
    replay_state, evaluate_monomial, two_copy_structural,
    two_copy_count_trace, two_copy_count_dag,
};
#[path = "p8c1_f8c1_symbolic.rs"]
mod symbolic;
const MAGIC: &[u8;4]=b"F8C1";
const LENGTH:usize=4+1+4*32+1+1+8+1+8*2;
#[derive(Clone,Copy)]
enum RawGate {
    H(usize), X(usize), Cx(usize,usize), T(usize), S(usize),
    Z(usize), Cz(usize,usize), Global
}
struct RawCircuit {n:usize,gates:Vec<RawGate>,h:usize}
fn number(s:&str)->Check<usize>{
    if s.is_empty() || (s.len()>1&&s.starts_with('0'))
        || !s.bytes().all(|b|b.is_ascii_digit()) {
        return Err(Error::InvalidSource);
    }
    s.parse().map_err(|_|Error::InvalidSource)
}
fn wire(s:&str,n:usize)->Check<usize>{
    let index=s.strip_prefix("q[")
        .and_then(|s|s.strip_suffix(']'))
        .ok_or(Error::InvalidSource)?;
    let q=number(index)?;
    if q>=n{return Err(Error::InvalidSource);}
    Ok(q)
}
fn independent_raw_source(src:&[u8])->Check<RawCircuit>{
    if src.len()>MAX_SOURCE_BYTES{return Err(Error::UnknownResource);}
    let s=std::str::from_utf8(src).map_err(|_|Error::InvalidSource)?;
    let mut lines=s.lines().map(str::trim).filter(|s|!s.is_empty());
    if lines.next()!=Some("OPENQASM 3.0;") {
        return Err(Error::UnsupportedSource);
    }
    if lines.next()!=Some("include \"stdgates.inc\";"){
        return Err(Error::UnsupportedSource);
    }
    let decl=lines.next().ok_or(Error::InvalidSource)?;
    let n=number(decl.strip_prefix("qubit[")
        .and_then(|s|s.strip_suffix("] q;"))
        .ok_or(Error::InvalidSource)?)?;
    if !(1..=3).contains(&n){return Err(Error::UnsupportedSource);}
    let mut gates=Vec::new();
    let mut h=0usize;
    for text in lines {
        if gates.len()>=1024{return Err(Error::UnknownResource);}
        let gate=if text=="gphase(pi/4);" {
            RawGate::Global
        }else{
            let stmt=text.strip_suffix(';').ok_or(Error::InvalidSource)?;
            let (name,operand)=stmt.split_once(' ').ok_or(Error::InvalidSource)?;
            // Modifiers are valid OpenQASM syntax but outside this scoped
            // proof grammar; do not misclassify them as malformed source.
            if matches!(name,"ctrl"|"negctrl"|"inv"|"pow"){
                return Err(Error::UnsupportedSource);
            }
            if operand.contains(char::is_whitespace){
                return Err(Error::InvalidSource);
            }
            match name{
                "h"=>{let t=wire(operand,n)?;h+=1;RawGate::H(t)}
                "x"=>RawGate::X(wire(operand,n)?),
                "t"=>RawGate::T(wire(operand,n)?),
                "s"=>RawGate::S(wire(operand,n)?),
                "z"=>RawGate::Z(wire(operand,n)?),
                "cx"|"cz"=>{
                    let (a,b)=operand.split_once(',').ok_or(Error::InvalidSource)?;
                    let a=wire(a,n)?;let b=wire(b,n)?;
                    if a==b{return Err(Error::InvalidSource);}
                    if name=="cx"{RawGate::Cx(a,b)}else{RawGate::Cz(a,b)}
                }
                _=>return Err(Error::UnsupportedSource),
            }
        };
        if h>4{return Err(Error::UnknownResource);}
        gates.push(gate);
    }
    if gates.is_empty(){return Err(Error::InvalidSource);}
    Ok(RawCircuit{n,gates,h})
}
// Raw gate-by-gate path semantics, independent of ANF polynomial evolution.
fn paths(c:&RawCircuit,input:usize,assignment:usize)->Vec<(usize,u8,usize)>{
    let mut basis=input;
    let mut phase=0u8;
    let mut fresh=0usize;
    let mut prefixes=Vec::with_capacity(c.gates.len());
    for &gate in &c.gates {
        match gate {
            RawGate::H(q)=>{
                let before=(basis>>q)&1;
                let next=(assignment>>fresh)&1;
                phase=(phase+4*(before*next) as u8)%8;
                basis=(basis&!(1usize<<q))|(next<<q);
                fresh+=1;
            }
            RawGate::X(q)=>basis^=1usize<<q,
            RawGate::Cx(a,b)=>{
                if ((basis>>a)&1)==1{basis^=1usize<<b;}
            }
            RawGate::Cz(a,b)=>{
                phase=(phase+4*(((basis>>a)&1)*((basis>>b)&1)) as u8)%8;
            }
            RawGate::T(q)=>phase=(phase+((basis>>q)&1) as u8)%8,
            RawGate::S(q)=>phase=(phase+2*((basis>>q)&1) as u8)%8,
            RawGate::Z(q)=>phase=(phase+4*((basis>>q)&1) as u8)%8,
            RawGate::Global=>phase=(phase+1)%8,
        };
        prefixes.push((basis,phase,fresh));
    }
    prefixes
}
fn polynomial_semantics(state:&State,input:usize,assignment:usize)->(usize,u8){
    let bits=(input as u64)|((assignment as u64)<<state.n);
    let mut output=0usize;
    for (q,f) in state.outputs.iter().enumerate(){
        let value=f.iter().fold(false,|a,&mon|a^evaluate_monomial(mon,bits));
        if value{output|=1<<q;}
    }
    let mut p=0u8;
    for (&mon,&coeff) in &state.phase{
        if evaluate_monomial(mon,bits){p=(p+coeff)%8;}
    }
    (output,p)
}
// Every serialized source-step frame is independently compared to the
// raw matrix/path interpretation, including intermediate phase. This
// rejects two incorrect steps whose phase errors cancel at the endpoint.
fn check_all_prefixes(src:&[u8],proof:&[u8],raw:&RawCircuit)->Check<usize>{
    if proof.len()>MAX_PROOF_BYTES{return Err(Error::UnknownResource);}
    let mut cursor=Cursor::new(proof);
    if cursor.bytes(4)?!=b"P8C1"
        ||cursor.u8()? as usize!=raw.n
        ||cursor.u16()?!=raw.gates.len()
        ||cursor.bytes(32)?!=sha256(src){
        return Err(Error::InvalidProof);
    }
    let mut total=0usize;
    let mut aggregate=0usize;
    for (step,_) in raw.gates.iter().enumerate(){
        let h=cursor.u8()? as usize;
        if h>4{return Err(Error::UnknownResource);}
        let mut local=0usize;
        let width=raw.n+h;
        let mut outputs=Vec::with_capacity(raw.n);
        for _ in 0..raw.n {
            outputs.push(read_termset(&mut cursor,width,&mut aggregate,&mut local)?);
        }
        let phase:Phase=read_phase(&mut cursor,width,&mut aggregate,&mut local)?;
        if aggregate>MAX_TOTAL_TERMS || local>MAX_FRAME_TERMS {
            return Err(Error::UnknownResource);
        }
        let state=State{n:raw.n,paths:h,outputs,phase};
        for x in 0..(1usize<<raw.n){
            for y in 0..(1usize<<h){
                let direct=paths(raw,x,y)[step];
                if direct.2!=h || polynomial_semantics(&state,x,y)!=(direct.0,direct.1){
                    return Err(Error::InvalidProof);
                }
                total+=1;
            }
        }
    }
    if cursor.at!=proof.len(){return Err(Error::InvalidProof);}
    Ok(total)
}
#[derive(Debug,Clone,PartialEq,Eq)]
pub(super) struct ResultCounts{
    pub(super) buckets:[u16;8],
    pub(super) prefix_checks:usize,
    pub(super) pair_checks:usize, // zero in symbolic acceptance
    pub(super) root_checks:usize,
    pub(super) method:u8,
    pub(super) first:usize,
    pub(super) second:usize,
    pub(super) bad:u64,
}
fn layers(
    src:&[u8],proof:&[u8],structure:&[u8],trace:&[u8]
)->Check<ResultCounts>{
    let raw=independent_raw_source(src)?;
    // Independent gate/phase semantics is additional to the canonical P8C1
    // transition replay; neither authority is simply assumed from a digest.
    let (_,state)=replay_state(src,proof)?;
    if state.n!=raw.n || state.paths!=raw.h{return Err(Error::InvalidProof);}
    let (source_symbolic,prefix_checks)=
        symbolic::check_p8c1_prefixes(src,proof,&raw)?;
    let network=two_copy_structural::verify_schema_without_enumeration(
        src,proof,structure)?;
    let mut reader=Cursor::new(structure);
    if reader.bytes(4)?!=b"S8C1"
        || reader.bytes(32)?!=sha256(src)
        || reader.bytes(32)?!=sha256(proof){
        return Err(Error::InvalidProof);
    }
    let first=reader.u8()? as usize;
    let second=reader.u8()? as usize;
    let bad=reader.u64()?;
    if first>=(1usize<<raw.n) || second>=(1usize<<raw.n)
        || bad==0 || (bad>> (1usize<<raw.n))!=0 {
        return Err(Error::InvalidProof);
    }
    if network.primary!=2*raw.h{return Err(Error::InvalidProof);}
    let (claimed,method)=if trace.starts_with(b"M8D1"){
        (two_copy_count_dag::verify(src,proof,structure,trace)?.buckets,1u8)
    }else if trace.starts_with(b"D8C1"){
        (two_copy_count_trace::verify(src,proof,structure,trace)?.buckets,0u8)
    }else{return Err(Error::InvalidProof);};
    // All-valuations identities are checked in the GF(2) Boolean ring,
    // not by traversing the 2^(2h) primary-path assignment space.
    let root_checks=symbolic::check_bucket_roots(
        &source_symbolic,&network,first,second,bad)?;
    Ok(ResultCounts{
        buckets:claimed,prefix_checks,pair_checks:0,root_checks,
        method,first,second,bad,
    })
}
fn canonical(
    src:&[u8],proof:&[u8],structure:&[u8],trace:&[u8],
    result:&ResultCounts
)->Vec<u8>{
    let mut out=Vec::with_capacity(LENGTH);
    out.extend_from_slice(MAGIC);
    out.push(1); // exact protocol version
    for part in [src,proof,structure,trace] {
        out.extend_from_slice(&sha256(part));
    }
    out.push(result.first as u8);
    out.push(result.second as u8);
    out.extend_from_slice(&result.bad.to_le_bytes());
    out.push(result.method);
    for &count in &result.buckets{
        out.extend_from_slice(&count.to_le_bytes());
    }
    debug_assert_eq!(out.len(),LENGTH);
    out
}
pub(super) fn encode(
    src:&[u8],proof:&[u8],structure:&[u8],trace:&[u8]
)->Check<Vec<u8>>{
    let checked=layers(src,proof,structure,trace)?;
    Ok(canonical(src,proof,structure,trace,&checked))
}
pub(super) fn verify(
    src:&[u8],proof:&[u8],structure:&[u8],trace:&[u8],claim:&[u8]
)->Check<ResultCounts>{
    if claim.len()!=LENGTH{return Err(Error::InvalidProof);}
    // Make the root/source/proof identities fail closed *before* any expensive
    // verification. Hashes are identity bindings, NOT cryptographic signatures.
    let mut cursor=Cursor::new(claim);
    if cursor.bytes(4)?!=MAGIC || cursor.u8()?!=1
        || cursor.bytes(32)?!=sha256(src)
        || cursor.bytes(32)?!=sha256(proof)
        || cursor.bytes(32)?!=sha256(structure)
        || cursor.bytes(32)?!=sha256(trace){
        return Err(Error::InvalidProof);
    }
    let result=layers(src,proof,structure,trace)?;
    if claim!=canonical(src,proof,structure,trace,&result){
        return Err(Error::InvalidProof);
    }
    Ok(result)
}
