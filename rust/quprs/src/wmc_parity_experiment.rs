//! Explicit research-only parity encoder. The default WmcManager path is untouched.
//! Return only precise GPMC-format bytes, never a manager with placeholder f64
//! weights accessible to another adapter.
use super::*;
use crate::rational::{PhaseCoeff,Rational};
use num_bigint::BigInt;
use std::collections::BTreeMap;
use anyhow::ensure;

type RadMap=BTreeMap<Monomial,BigRational>;
fn subsets(m:&[u32],mask:usize)->Monomial {
    m.iter().enumerate().filter_map(|(i,v)| ((mask>>i)&1==1).then_some(*v)).collect()
}
fn inverse(source:&RadMap,cap:usize)->Result<(RadMap,usize)> {
    let mut pending:BTreeMap<(usize,Monomial),BigRational>=source.iter()
        .filter(|(_,c)|!c.is_zero()).map(|(m,c)|((m.len(),m.clone()),c.clone())).collect();
    let mut result=RadMap::new();
    let mut work=0usize;
    if let Some(c)=pending.remove(&(0,vec![])){result.insert(vec![],c);}
    while let Some(((d,m),v))=pending.pop_last() {
        if v.is_zero(){continue}
        ensure!(d>0 && d<usize::BITS as usize,"parity degree cap");
        let limit=1usize<<d;
        work=work.checked_add(limit-1).ok_or_else(||anyhow!("parity work overflow"))?;
        ensure!(work<=cap,"parity work cap");
        let scale=BigRational::from_integer(BigInt::from(-2).pow((d-1) as u32));
        let c=v/scale;
        for mask in 1..limit-1 {
            let s=subsets(&m,mask);
            let factor=BigRational::from_integer(BigInt::from(-2).pow((s.len()-1) as u32));
            *pending.entry((s.len(),s)).or_insert_with(BigRational::zero)-=&c*factor;
        }
        result.insert(m,c);
    }
    Ok((result,work))
}

fn fresh(w:&mut WmcManager)->i32 {
    let z=w.next_var_id;w.next_var_id+=1;z
}
fn and(w:&mut WmcManager,ops:&[i32])->i32 {
    let z=fresh(w);
    for &x in ops {w.clauses.push(vec![-z,x]);}
    let mut last=vec![z];last.extend(ops.iter().map(|x|-*x));w.clauses.push(last);z
}
fn xor(w:&mut WmcManager,a:i32,b:i32,cache:&mut BTreeMap<(i32,i32),i32>)->i32 {
    let (a,b)=(a.min(b),a.max(b));
    if let Some(&z)=cache.get(&(a,b)){return z}
    let z=fresh(w);
    w.clauses.extend([vec![-a,-b,-z],vec![a,b,-z],vec![a,-b,z],vec![-a,b,z]]);
    cache.insert((a,b),z);z
}
fn weighted(w:&mut WmcManager,ops:&[i32],c:&PhaseCoeff,bits:usize)->Result<()> {
    let z=and(w,ops);
    let weight=crate::precise_weight::from_phase(c,bits)?;
    w.precise_weights.as_mut().expect("research precise mode").insert(z,weight);
    w.weights.insert(z,Complex::new(1.0,0.0));Ok(())
}
fn coefficient(turn:Rational,rad:Option<&BigRational>)->PhaseCoeff {
    PhaseCoeff{constant:turn,radians:rad.filter(|r|!r.is_zero()).cloned(),symbols:Default::default()}
}
/// Explicit experimental entry point: accepts a residual PathSum, preserves
/// original term-count precision budget and emits canonical GPMC bytes.
/// No automatic selection, solver invocation, or verification verdict.
impl WmcManager {
    #[doc(hidden)]
    pub fn research_parity_cnf(ps:&PathSum,epsilon:f64,cap:usize)->Result<(String,usize,usize)> {
        #[cfg(feature="browser-transport")]
        ensure!(!crate::browser_transport::active(),"native experiment only");
        ensure!(ps.v.continuous_vars.is_empty(),"continuous variables unsupported");
        ensure!(ps.f.functions.len()==ps.v.num_qubits,"invalid output domain");
        let mut domain:Vec<_>=ps.v.path_vars.iter().copied().collect();domain.sort_unstable();
        ensure!(domain.len()<=1_000_000,"primary variable cap");
        ensure!((0..ps.v.num_qubits).all(|i|ps.v.path_vars.contains(&(i as u32))),"missing input");
        let valid=|m:&Monomial|m.windows(2).all(|p|p[0]<p[1])&&m.iter().all(|v|ps.v.path_vars.contains(v));
        let mut rad=RadMap::new();let mut turns=BTreeMap::new();
        for (m,c) in &ps.p.terms {
            ensure!(valid(m)&&c.symbols.is_empty(),"invalid or symbolic phase");
            ensure!(c.constant.denom>0&&c.constant.numer>=0&&c.constant.numer<c.constant.denom,"noncanonical turns");
            if !c.constant.is_zero(){turns.insert(m.clone(),c.constant);}
            if let Some(r)=&c.radians {if !r.is_zero(){rad.insert(m.clone(),r.clone());}}
        }
        for f in &ps.f.functions {ensure!(f.iter().all(valid),"invalid output support");}
        let (parity,work)=inverse(&rad,cap.min(3_000_000))?;
        // Explicit E1e encoding, including structurally regressive controls.
        // Scope resource guard: maximum IDs bounded by primary + source
        // terms + subset work + output gate bound, before allocating clauses.
        let outputs=ps.f.functions.iter().try_fold(0usize,|a,f|a.checked_add(f.len().saturating_mul(2).saturating_add(1))).ok_or_else(||anyhow!("output cap overflow"))?;
        ensure!(domain.len().saturating_add(ps.p.terms.len()).saturating_add(work.saturating_mul(2)).saturating_add(outputs)<i32::MAX as usize,"DIMACS ID cap");
        let bits=crate::precise_weight::bits_for_distance(epsilon,ps.p.terms.len())?;
        let mut w=Self::new(ps);w.enable_precise_gpmc_weights(bits);
        for v in domain {w.get_dimacs_var(v);}
        for (m,r) in &parity {if m.len()<=1 {turns.entry(m.clone()).or_insert(Rational::ZERO);let _=r;}}
        for (m,t) in turns {
            let c=coefficient(t,if m.len()<=1{parity.get(&m)}else{None});
            let ops:Vec<_>=m.iter().map(|v|w.var_map[v]).collect();
            weighted(&mut w,&ops,&c,bits)?;
        }
        let mut cache=BTreeMap::new();
        for (m,c) in &parity {
            if m.len()<2{continue}
            let mut z=w.var_map[&m[0]];
            for v in &m[1..] {let b=w.var_map[v];z=xor(&mut w,z,b,&mut cache);}
            weighted(&mut w,&[z],&coefficient(Rational::ZERO,Some(c)),bits)?;
        }
        // Existing trace ANF method does not sort XOR input operands for
        // every gate. Match E1e's explicit canonical ordering instead.
        for (i,f) in ps.f.functions.iter().enumerate(){
            let mut terms:Vec<_>=f.iter().collect();terms.sort_unstable();
            let mut roots=Vec::new();
            for m in terms {
                let ops:Vec<_>=m.iter().map(|v|w.var_map[v]).collect();
                roots.push(if ops.len()==1{ops[0]}else{and(&mut w,&ops)});
            }
            let z=if roots.is_empty(){let z=fresh(&mut w);w.clauses.push(vec![-z]);z}
            else {
                let mut z=roots[0];
                for &b in &roots[1..]{z=xor(&mut w,z,b,&mut BTreeMap::new());}
                z
            };
            let a=w.var_map[&(i as u32)];w.clauses.extend([vec![-a,z],vec![a,-z]]);
        }
        Ok((w.try_to_dimacs_string("gpmc")?,work,bits))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_inverse_and_cap(){
        let c=BigRational::new(1.into(),7.into());
        let p=RadMap::from([(vec![0],c.clone()),(vec![1],c.clone()),(vec![0,1],-&c-&c)]);
        let (q,work)=inverse(&p,3).unwrap();
        assert_eq!(q,RadMap::from([(vec![0,1],c)]));assert_eq!(work,3);
        assert!(inverse(&p,2).is_err());
    }
}
