//! Shared research-only CNF encoder; no production API.
#![allow(dead_code)]
use quprs::PathSum;
use std::collections::{BTreeMap,BTreeSet};
pub(crate) type Anf = BTreeSet<u64>;
pub(crate) type Lit = i32;
pub(crate) const ONE: Lit = 1;
pub(crate) const ZERO: Lit = -1;

#[derive(Clone)]
pub(crate) struct Cnf { pub(crate) vars: usize, pub(crate) clauses: Vec<Vec<Lit>> }
impl Cnf {
    pub(crate) fn new(primary: usize) -> Self {
        Self { vars: primary+1, clauses: vec![vec![ONE]] }
    }
    pub(crate) fn fresh(&mut self) -> Lit {
        self.vars += 1;
        self.vars as Lit
    }
    pub(crate) fn and(&mut self,a:Lit,b:Lit)->Lit {
        if a==ZERO||b==ZERO||a == -b{return ZERO;}
        if a==ONE||a==b{return b;}
        if b==ONE{return a;}
        let z=self.fresh();
        self.clauses.extend([vec![-z,a],vec![-z,b],vec![z,-a,-b]]);
        z
    }
    pub(crate) fn xor(&mut self,a:Lit,b:Lit)->Lit {
        if a==b{return ZERO;}
        if a == -b{return ONE;}
        if a==ZERO{return b;}
        if b==ZERO{return a;}
        if a==ONE{return -b;}
        if b==ONE{return -a;}
        let z=self.fresh();
        self.clauses.extend([vec![-a,-b,-z],vec![a,b,-z],vec![a,-b,z],vec![-a,b,z]]);
        z
    }
    pub(crate) fn or(&mut self,a:Lit,b:Lit)->Lit { -self.and(-a,-b) }
    pub(crate) fn monomial(&mut self,m:u64,bits:&[Lit])->Lit {
        bits.iter().enumerate().filter(|(i,_)|m>>i&1!=0)
            .fold(ONE,|a,(_,b)|self.and(a,*b))
    }
    pub(crate) fn anf(&mut self,p:&Anf,bits:&[Lit])->Lit {
        p.iter().fold(ZERO,|a,&m|{let b=self.monomial(m,bits);self.xor(a,b)})
    }
    pub(crate) fn add3(&mut self,a:[Lit;3],b:[Lit;3])->[Lit;3]{
        let mut carry=ZERO;
        let mut out=[ZERO;3];
        for i in 0..3 {
            let t=self.xor(a[i],b[i]);
            out[i]=self.xor(t,carry);
            if i<2{
                let ab=self.and(a[i],b[i]);
                let tc=self.and(t,carry);
                carry=self.or(ab,tc);
            }
        }
        out
    }
    pub(crate) fn enforce(&mut self,l:Lit){self.clauses.push(vec![l]);}
    pub(crate) fn bounded(&self)->bool{self.vars<=512&&self.clauses.len()<=4096}
}

// Wide-ID dyadic phase projection. Keep native P/f/v; use stable
// ID -> CNF literal maps, never shift by a native ID. For D=2^k,
// N(delta=0)-N(delta=D/2) is nonnegative and vanishes iff the
// projected operator vanishes. It is NOT the physical leakage.
pub(crate) fn native_dyadic_projection_with_limits(ps:&PathSum,pre:&[Anf],post:&[Anf],max_vars:usize,max_clauses:usize)
    ->Option<(Cnf,Lit,u32)>{
    native_dyadic_projection_variant(ps,pre,post,max_vars,max_clauses,false)
}
pub(crate) fn native_dyadic_projection_variant(ps:&PathSum,pre:&[Anf],post:&[Anf],max_vars:usize,max_clauses:usize,heap:bool)
    ->Option<(Cnf,Lit,u32)>{
    let n=ps.v.num_qubits;
    if n==0||n>16||ps.rr_approximate||ps.rr_tolerance!=0.0||
        !ps.v.continuous_vars.is_empty()||ps.f.functions.len()!=n||
        pre.iter().chain(post).flatten().any(|&m|m>>n!=0){return None;}
    let mut ids:Vec<_>=ps.v.path_vars.iter().copied().collect();ids.sort_unstable();
    if ids.len()<n||ids.len()>512||(0..n).any(|i|ids[i]!=i as u32)||
        ps.p.terms.len()+ps.f.functions.iter().map(|f|f.len()).sum::<usize>()>8192{return None;}
    let h=ids.len()-n;
    let mut d=2u32;
    for (m,c) in &ps.p.terms{
        if c.radians.is_some()||!c.symbols.is_empty()||
            m.iter().any(|v|!ps.v.path_vars.contains(v)){return None;}
        let den=u32::try_from(c.constant.denom).ok()?;
        if !den.is_power_of_two()||den>64{return None;}
        d=d.max(den);
    }
    let k=d.trailing_zeros() as usize;
    let mut c=Cnf::new(n+2*h);
    let l:BTreeMap<u32,Lit>=ids.iter().enumerate().map(|(i,&id)|(id,i as Lit+2)).collect();
    let r:BTreeMap<u32,Lit>=ids.iter().enumerate().map(|(i,&id)|(id,(if i<n{i}else{i+h}) as Lit+2)).collect();
    let il:Vec<_>=(0..n).map(|i|l[&(i as u32)]).collect();
    for p in pre{let v=c.anf(p,&il);c.enforce(v);}
    let mut z=Vec::new();
    for o in &ps.f.functions{
        let mut pair=[ZERO;2];
        let mut ms:Vec<_>=o.iter().collect();ms.sort();
        for (j,map) in [&l,&r].into_iter().enumerate(){
            for m in &ms{
                let mut v=ONE;
                for id in m.iter(){v=c.and(v,*map.get(id)?);}
                pair[j]=c.xor(pair[j],v);
            }
        }
        let diff=c.xor(pair[0],pair[1]);c.enforce(-diff);z.push(pair[0]);
    }
    let good=post.iter().fold(ONE,|a,q|{let v=c.anf(q,&z);c.and(a,v)});
    c.enforce(-good);
    let mut acc=vec![ZERO;k];
    let mut ts:Vec<_>=ps.p.terms.iter().collect();ts.sort_by(|a,b|a.0.cmp(b.0));
    if heap {
        // w*l - w*r = w*l + w*!r - w, modulo D. Use the same
        // sparse positive coefficient on both sides; negative
        // coefficients no longer become dense two's-complement words.
        // Column compression is an exact integer identity; discard only
        // carries beyond k bits. Every gate is a unique-extension Tseitin.
        let mut columns=vec![Vec::<Lit>::new();k];
        let mut constant=0i128;
        let mut cache=BTreeMap::<Vec<Lit>,Lit>::new();
        for (m,coeff) in ts{
            if m.iter().all(|&id|(id as usize)<n){continue;} // shared input term cancels
            let w=(d as i128*coeff.constant.numer as i128/coeff.constant.denom as i128).rem_euclid(d as i128) as u32;
            if w==0{continue;}
            constant-=w as i128;
            for (map,negative) in [(&l,false),(&r,true)]{
                let mut key=m.iter().map(|id|map.get(id).copied()).collect::<Option<Vec<_>>>()?;
                key.sort_unstable();key.dedup();
                let term=if let Some(&v)=cache.get(&key){v}else{
                    let v=key.iter().fold(ONE,|a,&b|c.and(a,b));
                    cache.insert(key,v);v
                };
                for i in 0..k{if w>>i&1!=0{columns[i].push(if negative{-term}else{term});}}
            }
            if c.vars>max_vars||c.clauses.len()>max_clauses{return None;}
        }
        let offset=constant.rem_euclid(d as i128) as u32;
        for i in 0..k{if offset>>i&1!=0{columns[i].push(ONE);}}
        for i in 0..k{
            // Pairwise exact cancellation of l + !l; l + l carries l.
            // Deterministic literal grouping before column compression.
            let mut grouped=BTreeMap::<Lit,usize>::new();
            for v in std::mem::take(&mut columns[i]){if v!=ZERO{*grouped.entry(v).or_default()+=1;}}
            let keys:Vec<_>=grouped.keys().copied().filter(|&v|v>0).collect();
            let mut ones=0usize;
            for v in keys{
                let a=grouped.get(&v).copied().unwrap_or(0);
                let b=grouped.get(&-v).copied().unwrap_or(0);
                let pairs=a.min(b);ones+=pairs;
                if pairs>0{grouped.insert(v,a-pairs);grouped.insert(-v,b-pairs);}
            }
            // Constant ONE terms already counted in grouped; ZERO removed.
            ones+=grouped.remove(&ONE).unwrap_or(0);
            if i+1<k{columns[i+1].extend(std::iter::repeat_n(ONE,ones/2));}
            if ones%2==1{columns[i].push(ONE);}
            for (v,num) in grouped{
                if i+1<k{columns[i+1].extend(std::iter::repeat_n(v,num/2));}
                if num%2==1{columns[i].push(v);}
            }
            if i+1==k{
                acc[i]=columns[i].iter().fold(ZERO,|a,&b|c.xor(a,b));
            }else{
                while columns[i].len()>1{
                    let a=columns[i].pop().unwrap();let b=columns[i].pop().unwrap();
                    let ab=c.xor(a,b);
                    if let Some(v)=columns[i].pop(){
                        let sum=c.xor(ab,v);
                        let ab1=c.and(a,b);let ab2=c.and(ab,v);
                        let carry=c.or(ab1,ab2);
                        columns[i].push(sum);columns[i+1].push(carry);
                    }else{
                        columns[i].push(ab);columns[i+1].push(c.and(a,b));
                    }
                    if c.vars>max_vars||c.clauses.len()>max_clauses{return None;}
                }
                acc[i]=columns[i].pop().unwrap_or(ZERO);
            }
        }
    }else{
        for (m,coeff) in ts{
            if m.is_empty(){continue;} // identical constant phase cancels
            let v=(d as i128*coeff.constant.numer as i128/coeff.constant.denom as i128).rem_euclid(d as i128);
            for (map,signed) in [(&l,v),(&r,-v)]{
                let w=signed.rem_euclid(d as i128) as u32;
                if w==0{continue;}
                let mut term=ONE;
                for id in m{term=c.and(term,*map.get(id)?);}
                let mut carry=ZERO;
                for i in 0..k{
                    let b=if w>>i&1!=0{term}else{ZERO};
                    let a=acc[i];let t=c.xor(a,b);acc[i]=c.xor(t,carry);
                    if i+1<k{let ab=c.and(a,b);let tc=c.and(t,carry);carry=c.or(ab,tc);}
                }
                if c.vars>max_vars||c.clauses.len()>max_clauses{return None;}
            }
        }
    
    }
    // Only phase difference 0 or half a cycle can satisfy these
    // low-bit constraints. MSB is a signed-count selector.
    for &v in &acc[..k-1]{c.enforce(-v);}
    if c.vars>max_vars||c.clauses.len()>max_clauses{return None;}
    Some((c,acc[k-1],d))
}


pub(crate) fn native_dyadic_projection(ps:&PathSum,pre:&[Anf],post:&[Anf])->Option<(Cnf,Lit,u32)>{
    native_dyadic_projection_with_limits(ps,pre,post,4096,32768)
}
