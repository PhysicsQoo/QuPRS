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

#[cfg(test)]
mod tests{
    use super::*;
    fn value(poly:&Poly,assignment:u16)->bool{
        poly.iter().fold(false,|acc,&mon|acc^((mon&assignment)==mon))
    }
    #[test]
    fn symbolic_boolean_ring_reduction_local_truth_table(){
        let mut algebra=Algebra::new();
        let x=Algebra::var(0).unwrap();
        let y=Algebra::var(1).unwrap();
        let xy=algebra.and(&x,&y).unwrap();
        let sum=algebra.xor(&x,&y).unwrap();
        let or=algebra.or(&x,&y).unwrap();
        let not=algebra.not(&x).unwrap();
        for input in 0..4u16{
            let a=input&1!=0;let b=input&2!=0;
            assert_eq!(value(&xy,input),a&b);
            assert_eq!(value(&sum,input),a^b);
            assert_eq!(value(&or,input),a|b);
            assert_eq!(value(&not,input),!a);
        }
        assert_eq!(algebra.and(&x,&x).unwrap(),x,
            "Boolean quotient x^2=x must hold symbolically");
        assert_eq!(algebra.xor(&x,&x).unwrap(),Algebra::empty());
    }
    #[test]
    fn symbolic_three_bit_adder_and_negation_local_truth_table(){
        let mut algebra=Algebra::new();
        let left=[Algebra::var(0).unwrap(),Algebra::var(1).unwrap(),
            Algebra::var(2).unwrap()];
        let right=[Algebra::var(3).unwrap(),Algebra::var(4).unwrap(),
            Algebra::var(5).unwrap()];
        let result=algebra.add3(&left,&right).unwrap();
        let negative=algebra.negate3(&left).unwrap();
        for pair in 0..64u16{
            let l=(pair&7) as u8;
            let r=((pair>>3)&7) as u8;
            let sum=(0..3).fold(0u8,|acc,bit|
                acc|((value(&result[bit],pair) as u8)<<bit));
            let neg=(0..3).fold(0u8,|acc,bit|
                acc|((value(&negative[bit],pair) as u8)<<bit));
            assert_eq!(sum,(l+r)%8);
            assert_eq!(neg,(8-l)%8);
        }
    }
    #[test]
    fn symbolic_xor_parity_to_z8_lifting_independent_local_identity(){
        let mut algebra=Algebra::new();
        // Boolean parity x XOR y = x+y-2*x*y (mod 8).
        // The coefficient six is -2 in Z8; omitting the product is unsound.
        let correct=Phase::from([(1u64,1u8),(2u64,1u8),(3u64,6u8)]);
        let bits=phase_claim_to_bits(&correct,2,&mut algebra).unwrap();
        let expected=algebra.xor(&Algebra::var(0).unwrap(),
            &Algebra::var(1).unwrap()).unwrap();
        assert_eq!(bits[0],expected);
        assert_eq!(bits[1],Algebra::empty());
        assert_eq!(bits[2],Algebra::empty());
        let incorrect=Phase::from([(1u64,1u8),(2u64,1u8)]);
        let bad=phase_claim_to_bits(&incorrect,2,&mut algebra).unwrap();
        assert_ne!(bad,bits,"unsound omission of parity interaction detected");
    }
    // Independent reference inversion over Boolean truth-table vectors.
    // For a multilinear ANF f(x)=XOR_{m subset x} c_m, the
    // Boolean-lattice Möbius transform is its own inverse in GF(2).
    fn truth_to_masked_coefficients(n:usize,truth:&[bool])->Poly{
        let width=1usize<<n;
        assert_eq!(truth.len(),width);
        let mut c=truth.to_vec();
        for i in 0..n{
            for m in 0..width{
                if m&(1usize<<i)!=0{
                    c[m]^=c[m^(1usize<<i)];
                }
            }
        }
        c.iter().enumerate().filter_map(|(mon,&enabled)|
            enabled.then_some(mon as u16)).collect()
    }
    fn coefficient_bits(n:usize,bitfield:u32)->Poly{
        let width=1usize<<n;
        (0..width).filter(|&mon|bitfield&(1u32<<mon)!=0)
            .map(|mon|mon as u16).collect()
    }
    #[test]
    fn symbolic_bitmask_mobius_inverse_exhaustive(){
        let mut checked=0usize;
        // All 278 ANFs on <=3 variables: 2 + 4 + 16 + 256.
        // This is a differential Rust-to-monomial-mask conformance
        // check, not an arbitrary-width Rust refinement theorem.
        for n in 0..=3{
            let width=1usize<<n;
            for packed in 0..(1u32<<width){
                let p=coefficient_bits(n,packed);
                let truth=(0..width).map(|a|value(&p,a as u16))
                    .collect::<Vec<_>>();
                let recovered=truth_to_masked_coefficients(n,&truth);
                assert_eq!(recovered,p,
                    "noncanonical coefficient encoding n={n} packed={packed}");
                checked+=1;
            }
        }
        assert_eq!(checked,278);
        println!(
            "ANF_MASK_MOBIUS_INVERSE exhaustive_polynomials={checked} \
             max_variables=3 canonical_coefficients=true reference=independent_truth_transform"
        );
    }
    #[test]
    fn symbolic_bitmask_boolean_ops_truth_refinement(){
        let mut a=Algebra::new();
        let mut checks=0usize;
        // Each pair of 2-variable canonical ANFs. This covers XOR
        // cancellation, monomial idempotence, cross products and
        // complement independently of how the Rust set is mutated.
        for x in 0..16u32{
            for y in 0..16u32{
                let left=coefficient_bits(2,x);
                let right=coefficient_bits(2,y);
                let and=a.and(&left,&right).unwrap();
                let or=a.or(&left,&right).unwrap();
                let xor=a.xor(&left,&right).unwrap();
                let not=a.not(&left).unwrap();
                for input in 0..4u16{
                    let l=value(&left,input);
                    let r=value(&right,input);
                    assert_eq!(value(&and,input),l&r);
                    assert_eq!(value(&or,input),l|r);
                    assert_eq!(value(&xor,input),l^r);
                    assert_eq!(value(&not,input),!l);
                    checks+=4;
                }
            }
        }
        assert_eq!(checks,4096);
        println!(
            "ANF_MASK_OPERATOR_REFINEMENT operations={checks} \
             all_2variable_coefficient_pairs=true independent_truth_oracle=true"
        );
    }
    #[test]
    fn symbolic_u16_monomial_bit_order_and_squarefree_product(){
        // Independent exact single-monomial oracle, including the most
        // significant Rust u16 bit. This is a bounded *implementation*
        // test, not a proof that Rust compiles to the Lean semantics.
        let mut a=Algebra::new();
        let mut checked=0usize;
        for left in 0..16 {
            let l=Algebra::var(left).unwrap();
            assert_eq!(l,BTreeSet::from([1u16<<left]));
            for right in 0..16 {
                let r=Algebra::var(right).unwrap();
                let p=a.and(&l,&r).unwrap();
                assert_eq!(p,BTreeSet::from([(1u16<<left)|(1u16<<right)]));
                assert_eq!(a.and(&p,&p).unwrap(),p);
                // Use a sparse, independent variable-based truth oracle
                // that does not call the source/path-sum evaluator.
                for bits in [
                    0u16,0xffff,0xaaaa,0x5555,0x8000,0x0001,
                    1u16<<left,1u16<<right,
                    (1u16<<left)|(1u16<<right),
                ] {
                    let truth=((bits>>left)&1!=0) && ((bits>>right)&1!=0);
                    assert_eq!(value(&p,bits),truth);
                    checked+=1;
                }
            }
        }
        assert_eq!(checked,2304);
        assert_eq!(Algebra::var(16),Err(Error::UnknownResource));
        println!(
            "ANF_U16_MASK_SQUAREFREE positions=16 products=256 \
             truth_checks={checked} msb_bit15=true bit16_rejected=true"
        );
    }
    #[test]
    fn symbolic_term_and_fuel_bounds_cannot_issue_partial_proofs(){
        let mut a=Algebra::new();
        // A one-term over-limit input cannot be silently truncated.
        let oversized=(0..=(MAX_ANF_TERMS as u16)).collect::<Poly>();
        assert_eq!(oversized.len(),MAX_ANF_TERMS+1);
        assert_eq!(a.xor(&oversized,&Algebra::empty()),Err(Error::UnknownResource));
        // Charge large Cartesian products *before* construction to
        // fail closed without allocating a potentially huge expansion.
        let dense=(0..(MAX_ANF_TERMS as u16)).collect::<Poly>();
        let mut constrained=Algebra::new();
        assert_eq!(constrained.and(&dense,&dense),Err(Error::UnknownResource));
        assert!(constrained.remaining<=MAX_OPS);
        let one=Algebra::one();
        assert_eq!(Algebra{remaining:0}.and(&one,&one),Err(Error::UnknownResource));
        println!(
            "ANF_U16_RESOURCE_GUARD term_limit={} operation_fuel={} \
             fail_closed=true no_partial_result=true",
            MAX_ANF_TERMS,MAX_OPS
        );
    }
    #[test]
    fn symbolic_expansion_budget_is_fail_closed(){
        let mut exhausted=Algebra{remaining:0};
        let one=Algebra::one();
        assert_eq!(exhausted.and(&one,&one),Err(Error::UnknownResource));
        assert_eq!(exhausted.xor(&one,&one),Err(Error::UnknownResource));
    }
}
