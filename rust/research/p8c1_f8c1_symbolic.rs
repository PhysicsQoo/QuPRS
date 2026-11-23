//! Independent compositional symbolic source and S8C1 root checker.
//! Boolean ring: GF(2)[x_0,..,x_m]/(x_i^2-x_i).
//! No source-path assignment enumeration is performed in acceptance.
//! This uses independent ANF and three-bit ripple adder source rules,
//! not the original P8C1 evolve/parity lift nor S8C1 Builder.
//! Any algebraic expansion/fuel limit fails UNKNOWN_RESOURCE, not PROVED.
//! Gate source denotation and Boolean arithmetic are explicit assumptions
//! until mechanized by an external proof assistant.
use super::*;
use std::collections::BTreeSet;
type Poly=BTreeSet<u16>;
type PhaseBits=[Poly;3];
const MAX_ANF_TERMS:usize=4096;
const MAX_OPS:usize=3_000_000;
struct Algebra{remaining:usize}
impl Algebra {
    fn new()->Self{Self{remaining:MAX_OPS}}
    fn charge(&mut self,amount:usize)->Check<()>{
        self.remaining=self.remaining.checked_sub(amount)
            .ok_or(Error::UnknownResource)?;
        Ok(())
    }
    fn empty()->Poly{Poly::new()}
    fn one()->Poly{BTreeSet::from([0])}
    fn var(index:usize)->Check<Poly>{
        if index>=16{return Err(Error::UnknownResource);}
        Ok(BTreeSet::from([1u16<<index]))
    }
    fn xor(&mut self,a:&Poly,b:&Poly)->Check<Poly>{
        self.charge(a.len().checked_add(b.len())
            .ok_or(Error::UnknownResource)?.max(1))?;
        let mut result=a.clone();
        for &m in b {
            if !result.insert(m){result.remove(&m);}
        }
        if result.len()>MAX_ANF_TERMS{return Err(Error::UnknownResource);}
        Ok(result)
    }
    fn and(&mut self,a:&Poly,b:&Poly)->Check<Poly>{
        let cost=a.len().checked_mul(b.len()).ok_or(Error::UnknownResource)?;
        self.charge(cost.max(1))?;
        let mut out=Poly::new();
        for &x in a {for &y in b{
            let m=x|y;
            if !out.insert(m){out.remove(&m);}
        }}
        if out.len()>MAX_ANF_TERMS{return Err(Error::UnknownResource);}
        Ok(out)
    }
    fn or(&mut self,a:&Poly,b:&Poly)->Check<Poly>{
        let ab=self.and(a,b)?;
        let xy=self.xor(a,b)?;
        self.xor(&xy,&ab)
    }
    fn not(&mut self,a:&Poly)->Check<Poly>{
        self.xor(a,&Self::one())
    }
    fn add3(&mut self,first:&PhaseBits,second:&PhaseBits)->Check<PhaseBits>{
        let mut result=std::array::from_fn(|_|Self::empty());
        let mut carry=Self::empty();
        for i in 0..3 {
            let xor=self.xor(&first[i],&second[i])?;
            result[i]=self.xor(&xor,&carry)?;
            let ab=self.and(&first[i],&second[i])?;
            let xc=self.and(&xor,&carry)?;
            carry=self.xor(&ab,&xc)?;
        }
        Ok(result)
    }
    fn negate3(&mut self,p:&PhaseBits)->Check<PhaseBits>{
        let inverted=[
            self.not(&p[0])?,self.not(&p[1])?,self.not(&p[2])?
        ];
        let one=[Self::one(),Self::empty(),Self::empty()];
        self.add3(&inverted,&one)
    }
    fn contribution(&mut self,wire:&Poly,shift:usize)->Check<PhaseBits>{
        let mut bits=std::array::from_fn(|_|Self::empty());
        bits[shift]=wire.clone();
        Ok(bits)
    }
}
#[derive(Clone)]
pub(super) struct Symbolic {
    n:usize,h:usize,outputs:Vec<Poly>,phase:PhaseBits,
}
impl Symbolic {
    fn new(n:usize)->Check<Self>{
        let mut outputs=Vec::new();
        for i in 0..n{outputs.push(Algebra::var(i)?);}
        Ok(Self{n,h:0,outputs,
            phase:std::array::from_fn(|_|Algebra::empty())})
    }
    fn step(&mut self,gate:RawGate,a:&mut Algebra)->Check<()>{
        let add=match gate{
            RawGate::H(q)=>{
                let fresh=Algebra::var(self.n+self.h)?;
                let contribution=a.and(&self.outputs[q],&fresh)?;
                self.outputs[q]=fresh;
                self.h+=1;
                Some(a.contribution(&contribution,2)?)
            },
            RawGate::X(q)=>{
                self.outputs[q]=a.not(&self.outputs[q])?;
                None
            },
            RawGate::Cx(c,t)=>{
                self.outputs[t]=a.xor(&self.outputs[t],&self.outputs[c])?;
                None
            },
            RawGate::T(q)=>Some(a.contribution(&self.outputs[q],0)?),
            RawGate::S(q)=>Some(a.contribution(&self.outputs[q],1)?),
            RawGate::Z(q)=>Some(a.contribution(&self.outputs[q],2)?),
            RawGate::Cz(c,t)=>{
                let cross=a.and(&self.outputs[c],&self.outputs[t])?;
                Some(a.contribution(&cross,2)?)
            },
            RawGate::Global=>Some(a.contribution(&Algebra::one(),0)?),
        };
        if let Some(term)=add {self.phase=a.add3(&self.phase,&term)?;}
        Ok(())
    }
}
fn phase_claim_to_bits(
    phase:&Phase,allowed:usize,a:&mut Algebra
)->Check<PhaseBits>{
    let mut result=std::array::from_fn(|_|Algebra::empty());
    for (&mon,&coefficient) in phase {
        let m=u16::try_from(mon).map_err(|_|Error::InvalidProof)?;
        if mon >> allowed !=0{return Err(Error::InvalidProof);}
        let atom=BTreeSet::from([m]);
        let mut b=std::array::from_fn(|_|Algebra::empty());
        for (i,bit) in b.iter_mut().enumerate(){
            if (coefficient>>i)&1==1{*bit=atom.clone();}
        }
        result=a.add3(&result,&b)?;
    }
    Ok(result)
}
fn as_poly(set:&super::super::Anf)->Check<Poly>{
    set.iter().map(|&m|u16::try_from(m)
        .map_err(|_|Error::InvalidProof)).collect()
}
pub(super) fn check_p8c1_prefixes(
    src:&[u8],proof:&[u8],raw:&RawCircuit
)->Check<(Symbolic,usize)>{
    if proof.len()>MAX_PROOF_BYTES{return Err(Error::UnknownResource);}
    let mut reader=Cursor::new(proof);
    if reader.bytes(4)?!=b"P8C1"
        || reader.u8()? as usize!=raw.n
        || reader.u16()?!=raw.gates.len()
        || reader.bytes(32)?!=sha256(src){
        return Err(Error::InvalidProof);
    }
    let mut state=Symbolic::new(raw.n)?;
    let mut a=Algebra::new();
    let mut aggregate=0usize;
    let mut checked=0usize;
    for &gate in &raw.gates {
        state.step(gate,&mut a)?;
        let h=reader.u8()? as usize;
        if h!=state.h || h>4{return Err(Error::InvalidProof);}
        let mut local=0usize;
        for output in &state.outputs{
            let read=read_termset(&mut reader,raw.n+h,&mut aggregate,&mut local)?;
            if as_poly(&read)?!=*output{return Err(Error::InvalidProof);}
            checked+=1;
        }
        let phase=read_phase(&mut reader,raw.n+h,&mut aggregate,&mut local)?;
        let actual=phase_claim_to_bits(&phase,raw.n+h,&mut a)?;
        for bit in 0..3{
            if actual[bit]!=state.phase[bit]{return Err(Error::InvalidProof);}
            checked+=1;
        }
        if aggregate>MAX_TOTAL_TERMS||local>MAX_FRAME_TERMS{
            return Err(Error::UnknownResource);
        }
    }
    if reader.at!=proof.len() || state.h!=raw.h{
        return Err(Error::InvalidProof);
    }
    Ok((state,checked))
}
fn specialize(
    p:&Poly,n:usize,h:usize,input:usize,offset:usize,a:&mut Algebra
)->Check<Poly>{
    let mut out=Poly::new();
    a.charge(p.len().max(1))?;
    for &mon in p{
        let mut admissible=true;
        for q in 0..n{
            if mon&(1u16<<q)!=0 && input&(1usize<<q)==0{
                admissible=false;break;
            }
        }
        if !admissible{continue;}
        let mut mapped=0u16;
        for y in 0..h{
            if mon&(1u16<<(n+y))!=0 {
                mapped|=1u16<<(offset+y);
            }
        }
        if !out.insert(mapped){out.remove(&mapped);}
    }
    if out.len()>MAX_ANF_TERMS{return Err(Error::UnknownResource);}
    Ok(out)
}
fn specialized_phase(
    s:&Symbolic,input:usize,offset:usize,a:&mut Algebra
)->Check<PhaseBits>{
    Ok([
        specialize(&s.phase[0],s.n,s.h,input,offset,a)?,
        specialize(&s.phase[1],s.n,s.h,input,offset,a)?,
        specialize(&s.phase[2],s.n,s.h,input,offset,a)?,
    ])
}
pub(super) fn check_bucket_roots(
    state:&Symbolic,network:&two_copy_structural::Structural,
    first:usize,second:usize,bad:u64,
)->Check<usize>{
    let mut a=Algebra::new();
    if network.primary!=2*state.h {return Err(Error::InvalidProof);}
    let mut symbolic=Vec::with_capacity(network.primary+network.gates.len());
    for i in 0..network.primary {symbolic.push(Algebra::var(i)?);}
    for gate in &network.gates {
        let get=|id:u16|->Check<Poly>{
            symbolic.get(id as usize).cloned().ok_or(Error::InvalidProof)
        };
        let value=match gate.op{
            two_copy_structural::Op::Zero=>Algebra::empty(),
            two_copy_structural::Op::One=>Algebra::one(),
            two_copy_structural::Op::Not=>a.not(&get(gate.a)?)?,
            two_copy_structural::Op::And=>a.and(&get(gate.a)?,&get(gate.b)?)?,
            two_copy_structural::Op::Or=>a.or(&get(gate.a)?,&get(gate.b)?)?,
            two_copy_structural::Op::Xor=>a.xor(&get(gate.a)?,&get(gate.b)?)?,
        };
        symbolic.push(value);
    }
    let mut same=Algebra::one();
    let mut left=Vec::new();
    for p in &state.outputs{
        let l=specialize(p,state.n,state.h,first,0,&mut a)?;
        let r=specialize(p,state.n,state.h,second,state.h,&mut a)?;
        let different=a.xor(&l,&r)?;
        let equal=a.not(&different)?;
        same=a.and(&same,&equal)?;
        left.push(l);
    }
    let mut in_bad=Algebra::empty();
    for idx in 0..(1usize<<state.n){
        if bad&(1u64<<idx)==0{continue;}
        let mut matcher=Algebra::one();
        for (q,p) in left.iter().enumerate(){
            let matched=if idx&(1usize<<q)!=0{
                p.clone()
            }else{a.not(p)?};
            matcher=a.and(&matcher,&matched)?;
        }
        in_bad=a.or(&in_bad,&matcher)?;
    }
    let eligible=a.and(&same,&in_bad)?;
    let lphase=specialized_phase(state,first,0,&mut a)?;
    let rphase=specialized_phase(state,second,state.h,&mut a)?;
    let neg=a.negate3(&lphase)?;
    let diff=a.add3(&rphase,&neg)?;
    for bucket in 0..8{
        let mut root=eligible.clone();
        for (bit,p) in diff.iter().enumerate(){
            let matched=if bucket&(1usize<<bit)!=0{
                p.clone()
            }else{a.not(p)?};
            root=a.and(&root,&matched)?;
        }
        if symbolic.get(network.bucket[bucket] as usize)!=Some(&root){
            return Err(Error::InvalidProof);
        }
    }
    Ok(8)
}
