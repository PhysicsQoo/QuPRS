//! Shared bounded Boolean guard algebra for research CPS.
//! Native IDs are not bit positions in the sparse backend. The narrow
//! representation retains its original bitwise operations and order.
use std::collections::{BTreeMap,BTreeSet};
use super::native_dyadic_cnf::{Cnf,Lit,ONE,ZERO};

pub(crate) trait GuardMonomial: Clone+Ord {
    fn union(&self, other:&Self)->Self;
    fn contains_id(&self,id:u32)->bool;
    fn without_id(&self,id:u32)->Self;
}
impl GuardMonomial for u64 {
    fn union(&self,other:&Self)->Self{*self|*other}
    fn contains_id(&self,id:u32)->bool{id<64&&*self&(1u64<<id)!=0}
    fn without_id(&self,id:u32)->Self{if id<64{*self&!(1u64<<id)}else{*self}}
}
#[derive(Clone,Debug,PartialEq,Eq,PartialOrd,Ord)]
pub(crate) struct SparseMono(Vec<u32>);
impl SparseMono {
    // Native PathSum monomials are canonical sorted, unique IDs.
    // Reject malformed ingress; never silently discard duplicates.
    pub(crate) fn new(ids:Vec<u32>)->Option<Self>{
        ids.windows(2).all(|w|w[0]<w[1]).then_some(Self(ids))
    }
    pub(crate) fn ids(&self)->&[u32]{&self.0}
}
impl GuardMonomial for SparseMono {
    fn union(&self,other:&Self)->Self{
        let mut out=Vec::with_capacity(self.0.len()+other.0.len());
        let (mut i,mut j)=(0,0);
        while i<self.0.len()&&j<other.0.len(){
            let (a,b)=(self.0[i],other.0[j]);
            out.push(a.min(b));
            if a<=b{i+=1;}
            if b<=a{j+=1;}
        }
        out.extend_from_slice(&self.0[i..]);out.extend_from_slice(&other.0[j..]);
        Self(out)
    }
    fn contains_id(&self,id:u32)->bool{self.0.binary_search(&id).is_ok()}
    fn without_id(&self,id:u32)->Self{
        Self(self.0.iter().copied().filter(|&v|v!=id).collect())
    }
}
pub(crate) type SparseAnf=BTreeSet<SparseMono>;

fn toggle<M:GuardMonomial>(f:&mut BTreeSet<M>,m:M){
    if !f.remove(&m){f.insert(m);}
}
// Identical bounds to the original narrow mul_anf.
pub(crate) fn guard_mul<M:GuardMonomial>(a:&BTreeSet<M>,b:&BTreeSet<M>)->Option<BTreeSet<M>>{
    if a.len().checked_mul(b.len())?>4096{return None;}
    let mut out=BTreeSet::new();
    for x in a{for y in b{toggle(&mut out,x.union(y));}}
    if out.len()>256{return None;}Some(out)
}
// Preserve the original intermediate bound as well as the final bound.
pub(crate) fn guard_substitute<M:GuardMonomial>(g:&BTreeSet<M>,target:u32,repl:&BTreeSet<M>)->Option<BTreeSet<M>>{
    if repl.iter().any(|m|m.contains_id(target)){return None;}
    if g.len().checked_mul(repl.len().max(1))?>4096{return None;}
    let mut next=BTreeSet::new();
    for m in g{
        if !m.contains_id(target){toggle(&mut next,m.clone());}
        else{
            let rest=m.without_id(target);
            for t in repl{toggle(&mut next,rest.union(t));}
        }
        if next.len()>256{return None;}
    }
    Some(next)
}
// Width-independent literal lowering, using the existing unique-extension
// Cnf gates. This is a guard primitive, not an alternative verifier.
pub(crate) fn sparse_guard_lit(c:&mut Cnf,p:&SparseAnf,map:&BTreeMap<u32,Lit>)->Option<Lit>{
    if p.iter().flat_map(|m|m.ids()).any(|id|!map.contains_key(id)){return None;}
    let mut acc=ZERO;
    for m in p{
        let mut t=ONE;
        for id in m.ids(){t=c.and(t,*map.get(id)?);}
        acc=c.xor(acc,t);
    }
    Some(acc)
}
