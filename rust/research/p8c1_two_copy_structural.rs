//! Source-bound structural two-copy Tseitin / GF(2)-XOR encoding.
//! A deterministic auxiliary gate network replaces truth-table blocking CNF.
//! Every full primary path assignment has EXACTLY ONE auxiliary extension
//! (induction over the ordered definitional gates). The eight bucket
//! selection outputs remain separate; no solver count is trusted.
//!
//! Bounded proof of concept, not a general model-counting certificate or
//! source-standard parser. SourceTrust is intentionally outside this scope.
use super::{sha256,replay_state,Check,Error,State,Cursor};
use super::{two_copy_cnf,two_copy_wmc};
const S8C1_MAX_PATHS:usize=4;
const S8C1_MAX_GATES:usize=8192;
const S8C1_MAX_BYTES:usize=65536;
const HEADER:usize=4+32+32+2+8+1+2;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) enum Op {Zero=0,One=1,Not=2,And=3,Or=4,Xor=5}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) struct Gate {pub(super) op:Op,pub(super) a:u16,pub(super) b:u16}
#[derive(Clone,Debug,PartialEq,Eq)]
pub(super) struct Structural {
    pub(super) primary:usize,
    pub(super) gates:Vec<Gate>,
    pub(super) bucket:[u16;8],
}
struct Builder {
    primary:usize,
    gates:Vec<Gate>,
    zero:u16,
    one:u16,
}
impl Builder {
    fn new(primary:usize)->Check<Self>{
        let mut b=Self{primary,gates:Vec::new(),zero:0,one:0};
        b.zero=b.push(Op::Zero,0,0)?;
        b.one=b.push(Op::One,0,0)?;
        Ok(b)
    }
    fn push(&mut self,op:Op,a:u16,b:u16)->Check<u16>{
        if self.gates.len()>=S8C1_MAX_GATES{return Err(Error::UnknownResource);}
        let index=self.primary.checked_add(self.gates.len()).ok_or(Error::UnknownResource)?;
        let id=u16::try_from(index).map_err(|_|Error::UnknownResource)?;
        let valid=|x:u16|(x as usize)<index;
        if matches!(op,Op::Not|Op::And|Op::Or|Op::Xor)&&!valid(a){
            return Err(Error::InvalidProof);
        }
        if matches!(op,Op::And|Op::Or|Op::Xor)&&!valid(b){
            return Err(Error::InvalidProof);
        }
        self.gates.push(Gate{op,a,b});
        Ok(id)
    }
    fn and(&mut self,x:u16,y:u16)->Check<u16>{self.push(Op::And,x,y)}
    fn or(&mut self,x:u16,y:u16)->Check<u16>{self.push(Op::Or,x,y)}
    fn xor(&mut self,x:u16,y:u16)->Check<u16>{self.push(Op::Xor,x,y)}
    fn not(&mut self,x:u16)->Check<u16>{self.push(Op::Not,x,0)}
    fn monomial(&mut self,mask:u64,n:usize,h:usize,input:usize,offset:usize)->Check<u16>{
        let allowed=(1u64<<(n+h))-1;
        if mask&!allowed!=0{return Err(Error::InvalidProof);}
        for i in 0..n {
            if (mask>>i)&1==1 && (input>>i)&1==0{return Ok(self.zero);}
        }
        let mut out=self.one;
        for i in 0..h {
            if (mask>>(n+i))&1==1 {
                let path=u16::try_from(offset+i).map_err(|_|Error::UnknownResource)?;
                out=self.and(out,path)?;
            }
        }
        Ok(out)
    }
    fn anf(&mut self,terms:&std::collections::BTreeSet<u64>,
        n:usize,h:usize,input:usize,offset:usize)->Check<u16>{
        let mut out=self.zero;
        for &mask in terms {
            let value=self.monomial(mask,n,h,input,offset)?;
            out=self.xor(out,value)?;
        }
        Ok(out)
    }
    fn phase(&mut self,state:&State,input:usize,offset:usize,negative:bool)
        ->Check<[u16;3]>{
        let mut acc=[self.zero;3];
        for (&mon,&coeff) in &state.phase {
            let bit=self.monomial(mon,state.n,state.paths,input,offset)?;
            let amount=if negative {(8-coeff)%8}else{coeff};
            let mut carry=self.zero;
            for index in 0..3 {
                let rhs=if (amount>>index)&1==1 {bit}else{self.zero};
                let x=self.xor(acc[index],rhs)?;
                let y=self.xor(x,carry)?;
                let c1=self.and(acc[index],rhs)?;
                let c2=self.and(x,carry)?;
                carry=self.or(c1,c2)?;
                acc[index]=y;
            }
        }
        Ok(acc)
    }
}
pub(super) fn build(state:&State,first:usize,second:usize,bad:u64)->Check<Structural>{
    if state.paths>S8C1_MAX_PATHS || state.n==0 || state.n>3 {
        return Err(Error::UnknownResource);
    }
    let dim=1usize<<state.n;
    if first>=dim || second>=dim || bad==0 || bad&!((1u64<<dim)-1)!=0 {
        return Err(Error::InvalidSource);
    }
    let h=state.paths;
    let mut b=Builder::new(2*h)?;
    let mut left=Vec::new();
    let mut right=Vec::new();
    for output in &state.outputs {
        left.push(b.anf(output,state.n,h,first,0)?);
        right.push(b.anf(output,state.n,h,second,h)?);
    }
    let mut same=b.one;
    for q in 0..state.n{
        let unequal=b.xor(left[q],right[q])?;
        let equal=b.not(unequal)?;
        same=b.and(same,equal)?;
    }
    let mut in_bad=b.zero;
    for index in 0..dim {
        if bad&(1u64<<index)==0 {continue;}
        let mut matches=b.one;
        for q in 0..state.n{
            let val=if (index>>q)&1==1 {left[q]} else {b.not(left[q])?};
            matches=b.and(matches,val)?;
        }
        in_bad=b.or(in_bad,matches)?;
    }
    let admissible=b.and(same,in_bad)?;
    let mut diff=b.phase(state,first,0,true)?;
    let positive=b.phase(state,second,h,false)?;
    let mut carry=b.zero;
    for k in 0..3{
        let x=b.xor(diff[k],positive[k])?;
        let y=b.xor(x,carry)?;
        let c1=b.and(diff[k],positive[k])?;
        let c2=b.and(x,carry)?;
        carry=b.or(c1,c2)?;
        diff[k]=y;
    }
    let mut bucket=[0u16;8];
    for (value,slot) in bucket.iter_mut().enumerate(){
        let mut root=admissible;
        for (k,&phase_bit) in diff.iter().enumerate(){
            let eq=if (value>>k)&1==1 {phase_bit}else{b.not(phase_bit)?};
            root=b.and(root,eq)?;
        }
        *slot=root;
    }
    Ok(Structural{primary:2*h,gates:b.gates,bucket})
}
pub(super) fn evaluate(c:&Structural,assignment:usize)->Check<Vec<bool>>{
    if c.primary>8 || c.gates.len()>S8C1_MAX_GATES{return Err(Error::UnknownResource);}
    let mut values=Vec::with_capacity(c.primary+c.gates.len());
    for i in 0..c.primary{values.push((assignment>>i)&1==1);}
    for gate in &c.gates {
        let index=values.len();
        let get=|node:u16|->Check<bool>{
            if node as usize>=index{return Err(Error::InvalidProof);}
            Ok(values[node as usize])
        };
        let result=match gate.op {
            Op::Zero=>false,Op::One=>true,Op::Not=>!get(gate.a)?,
            Op::And=>get(gate.a)?&get(gate.b)?,
            Op::Or=>get(gate.a)?|get(gate.b)?,
            Op::Xor=>get(gate.a)?^get(gate.b)?,
        };
        values.push(result);
    }
    Ok(values)
}
fn literal(id:usize,positive:bool)->Check<i32>{
    let v=i32::try_from(id.checked_add(1).ok_or(Error::UnknownResource)?)
        .map_err(|_|Error::UnknownResource)?;
    Ok(if positive {v}else{-v})
}
// Each auxiliary node is fully constrained by its input nodes.
// Thus each primary assignment has exactly one satisfying extension.
fn gate_clauses(index:usize,g:Gate)->Check<Vec<Vec<i32>>>{
    let z=literal(index,true)?;
    let a=literal(g.a as usize,true)?;
    let b=literal(g.b as usize,true)?;
    Ok(match g.op {
        Op::Zero=>vec![vec![-z]],
        Op::One=>vec![vec![z]],
        Op::Not=>vec![vec![-z,-a],vec![z,a]],
        Op::And=>vec![vec![-z,a],vec![-z,b],vec![z,-a,-b]],
        Op::Or=>vec![vec![z,-a],vec![z,-b],vec![-z,a,b]],
        Op::Xor=>vec![
            vec![-a,-b,-z],vec![a,b,-z],
            vec![a,-b,z],vec![-a,b,z],
        ]
    })
}
fn satisfies(clauses:&[Vec<i32>],values:&[bool])->bool{
    clauses.iter().all(|clause|clause.iter().any(|&lit|{
        let value=values[lit.unsigned_abs() as usize-1];
        if lit<0 {!value}else{value}
    }))
}
// Explicit finite truth-table validation for every local Tseitin rule.
// This is also a guard against accidentally changing the gate clauses.
fn check_local_unique_extension()->Check<()>{
    for op in [Op::Zero,Op::One,Op::Not,Op::And,Op::Or,Op::Xor]{
        let gate=Gate{op,a:0,b:1};
        let clauses=gate_clauses(2,gate)?;
        for mask in 0..4 {
            let x=mask&1!=0;let y=mask&2!=0;
            let expected=match op{
                Op::Zero=>false,Op::One=>true,Op::Not=>!x,
                Op::And=>x&y,Op::Or=>x|y,Op::Xor=>x^y,
            };
            let mut extensions=0;
            for z in [false,true]{
                let vals=[x,y,z];
                if satisfies(&clauses,&vals){
                    extensions+=1;
                    if z!=expected{return Err(Error::InvalidProof);}
                }
            }
            if extensions!=1{return Err(Error::InvalidProof);}
        }
    }
    Ok(())
}
pub(super) fn encode(src:&[u8],proof:&[u8],state:&State,
    first:usize,second:usize,bad:u64)->Check<Vec<u8>>{
    let c=build(state,first,second,bad)?;
    let mut out=Vec::with_capacity(HEADER+5*c.gates.len()+16);
    out.extend_from_slice(b"S8C1");
    out.extend_from_slice(&sha256(src));
    out.extend_from_slice(&sha256(proof));
    out.push(first as u8);out.push(second as u8);
    out.extend_from_slice(&bad.to_le_bytes());
    out.push(state.paths as u8);
    out.extend_from_slice(&(c.gates.len() as u16).to_le_bytes());
    for gate in &c.gates{
        out.push(gate.op as u8);
        out.extend_from_slice(&gate.a.to_le_bytes());
        out.extend_from_slice(&gate.b.to_le_bytes());
    }
    for &r in &c.bucket{out.extend_from_slice(&r.to_le_bytes());}
    if out.len()>S8C1_MAX_BYTES {return Err(Error::UnknownResource);}
    Ok(out)
}
// Checks the complete source-bound deterministic structural gate DAG,
// including the exact canonical byte representation, WITHOUT enumerating
// 2^(2h) primary assignments. D8C1 consumes this admitted circuit and
// verifies its own local Shannon count trace instead.
pub(super) fn verify_schema_without_enumeration(
    src:&[u8],proof:&[u8],bytes:&[u8]
)->Check<Structural>{
    if bytes.len()>S8C1_MAX_BYTES{return Err(Error::UnknownResource);}
    if bytes.len()<HEADER+16{return Err(Error::InvalidProof);}
    let mut reader=Cursor::new(bytes);
    if reader.bytes(4)?!=b"S8C1"
        ||reader.bytes(32)?!=sha256(src)
        ||reader.bytes(32)?!=sha256(proof) {
        return Err(Error::InvalidProof);
    }
    let first=reader.u8()? as usize;
    let second=reader.u8()? as usize;
    let bad=reader.u64()?;
    let h=reader.u8()? as usize;
    let declared=reader.u16()?;
    if h>S8C1_MAX_PATHS || declared>S8C1_MAX_GATES {
        return Err(Error::UnknownResource);
    }
    let (_,state)=replay_state(src,proof)?;
    if state.paths!=h{return Err(Error::InvalidProof);}
    let expected=encode(src,proof,&state,first,second,bad).map_err(|e|
        if e==Error::InvalidSource {Error::InvalidProof}else{e}
    )?;
    if expected!=bytes{return Err(Error::InvalidProof);}
    let network=build(&state,first,second,bad).map_err(|e|
        if e==Error::InvalidSource {Error::InvalidProof}else{e}
    )?;
    if network.gates.len()!=declared{return Err(Error::InvalidProof);}
    check_local_unique_extension()?;
    Ok(network)
}

pub(super) fn verify(src:&[u8],proof:&[u8],bytes:&[u8])->Check<[u16;8]>{
    if bytes.len()>S8C1_MAX_BYTES{return Err(Error::UnknownResource);}
    if bytes.len()<HEADER+16{return Err(Error::InvalidProof);}
    let mut c=Cursor::new(bytes);
    if c.bytes(4)?!=b"S8C1"
        ||c.bytes(32)?!=sha256(src)
        ||c.bytes(32)?!=sha256(proof) {return Err(Error::InvalidProof);}
    let first=c.u8()? as usize;
    let second=c.u8()? as usize;
    let bad=c.u64()?;
    let h=c.u8()? as usize;
    let gate_count=c.u16()?;
    if h>S8C1_MAX_PATHS || gate_count>S8C1_MAX_GATES{
        return Err(Error::UnknownResource);
    }
    let (_,state)=replay_state(src,proof)?;
    if state.paths!=h{return Err(Error::InvalidProof);}
    // Invalid indices or bad-output masks in an untrusted serialized
    // claim are INVALID_PROOF, not errors attributed to the admitted source.
    let expected=encode(src,proof,&state,first,second,bad).map_err(|e|
        if e==Error::InvalidSource {Error::InvalidProof}else{e}
    )?;
    // The complete deterministic gate DAG, including every structural
    // definition, is bound to a fresh independent source replay. Reject
    // dummy, orphan, reordered or noncanonical auxiliary variables.
    if expected!=bytes{return Err(Error::InvalidProof);}
    let structured=build(&state,first,second,bad)?;
    if structured.gates.len()!=gate_count{return Err(Error::InvalidProof);}
    check_local_unique_extension()?;
    let canonical=two_copy_cnf::build(&state,first,second,bad)?;
    let original=two_copy_cnf::count_models(&canonical)?;
    let weighted=two_copy_wmc::enumerate_pairs(&state,first,second,bad)?.buckets;
    let mut observed=[0u16;8];
    for assignment in 0..(1usize<<(2*h)){
        let extension=evaluate(&structured,assignment)?;
        // Every complete Tseitin clause must be true under its *unique*
        // auxiliary assignment. The final root unit clauses select buckets.
        for (i,&gate) in structured.gates.iter().enumerate(){
            let clauses=gate_clauses(structured.primary+i,gate)?;
            if !satisfies(&clauses,&extension){return Err(Error::InvalidProof);}
        }
        for bucket in 0..8 {
            let selected=extension[structured.bucket[bucket] as usize];
            let selected_by_reference=canonical.clauses[bucket].iter().all(|&(p,n)|{
                !(((p as usize)&assignment)==0
                    &&((n as usize)&!assignment)==0)
            });
            if selected!=selected_by_reference{return Err(Error::InvalidProof);}
            if selected{
                observed[bucket]=observed[bucket].checked_add(1)
                    .ok_or(Error::UnknownResource)?;
            }
        }
    }
    if observed!=original || observed!=weighted {return Err(Error::InvalidProof);}
    Ok(observed)
}
#[cfg(test)]
mod tests{
    use super::*;
    use std::collections::{BTreeSet,BTreeMap};
    fn h_state()->State{
        State {n:1,paths:1,outputs:vec![BTreeSet::from([2])],
            phase:BTreeMap::from([(3,4)])}
    }
    #[test]
    fn boolean_tseitin_gates_have_unique_extension(){
        assert_eq!(check_local_unique_extension(),Ok(()));
    }
    #[test]
    fn structural_network_exact_h_bucket_and_unique_extension(){
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n";
        // The real external round-trip test obtains its proof from the
        // source-bound QuPRS research producer; this local test checks
        // only the source-independent structural network itself.
        let state=h_state();
        let circuit=build(&state,0,1,1).unwrap();
        let mut counts=[0u16;8];
        for primary in 0..4{
            let values=evaluate(&circuit,primary).unwrap();
            for (k,&node) in circuit.bucket.iter().enumerate(){
                if values[node as usize]{counts[k]+=1;}
            }
        }
        assert_eq!(counts,[1,0,0,0,0,0,0,0]);
        assert_eq!(counts,two_copy_cnf::count_models(
            &two_copy_cnf::build(&state,0,1,1).unwrap()).unwrap());
        assert!(src.starts_with(b"OPENQASM 3.0"));
        println!("S8C1_H_STRUCTURAL exact_phase_buckets=true unique_extension=true");
    }
}
