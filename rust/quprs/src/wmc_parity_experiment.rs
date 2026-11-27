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
fn canonical_trace(w:&mut WmcManager,ps:&PathSum) {
        // Existing trace ANF method does not sort XOR input operands for
        // every gate. Match E1e's explicit canonical ordering instead.
        for (i,f) in ps.f.functions.iter().enumerate(){
            let mut terms:Vec<_>=f.iter().collect();terms.sort_unstable();
            let mut roots=Vec::new();
            for m in terms {
                let ops:Vec<_>=m.iter().map(|v|w.var_map[v]).collect();
                roots.push(if ops.len()==1{ops[0]}else{and(w,&ops)});
            }
            let z=if roots.is_empty(){let z=fresh(w);w.clauses.push(vec![-z]);z}
            else {
                let mut z=roots[0];
                for &b in &roots[1..]{z=xor(w,z,b,&mut BTreeMap::new());}
                z
            };
            let a=w.var_map[&(i as u32)];w.clauses.extend([vec![-a,z],vec![a,-z]]);
        }

}

#[derive(Debug)]
enum Block {
    Complement(Monomial,u32),
    Xor(Monomial,u32,u32),
}

// Compare exact modulo-turn arithmetic WITHOUT the legacy Rational operators,
// which may approximate a large intermediate denominator. The i128 products
// fit because normalized source components have positive i64 denominators.
fn scaled_eq(target:&PhaseCoeff,source:&PhaseCoeff,k:i64)->bool {
    let d=source.constant.denom as i128;
    let n=(source.constant.numer as i128*k as i128).rem_euclid(d);
    if n*target.constant.denom as i128!=target.constant.numer as i128*d {return false}
    match (&target.radians,&source.radians) {
        (None,None)=>true,
        (Some(a),Some(b))=>a==&(b*BigRational::from_integer(BigInt::from(k))),
        (None,Some(b))=>b.is_zero()||k==0,
        (Some(a),None)=>a.is_zero(),
    }
}
fn factor_plan(ps:&PathSum,cap:usize)->Result<(Vec<(Block,PhaseCoeff)>,std::collections::BTreeSet<Monomial>,usize)> {
    let p=&ps.p.terms;
    let mut order:Vec<_>=p.keys().collect();
    order.sort_unstable_by(|a,b|b.len().cmp(&a.len()).then_with(||a.cmp(b)));
    let mut unused:std::collections::BTreeSet<Monomial>=p.keys().cloned().collect();
    let mut plan=Vec::new();let mut probes=0usize;
    for u in order {
        if u.is_empty()||!unused.contains(u){continue}
        let children:Vec<Monomial>=(0..u.len()).map(|i|u.iter().enumerate().filter_map(|(j,v)|(i!=j).then_some(*v)).collect()).collect();
        let mut found=false;
        for (i,a) in children.iter().enumerate() {
            probes+=1;ensure!(probes<=cap,"factor probe cap");
            if unused.contains(a)&&scaled_eq(&p[u],&p[a],-1) {
                plan.push((Block::Complement(a.clone(),u[i]),p[a].clone()));
                unused.remove(u);unused.remove(a);found=true;break
            }
        }
        if found||u.len()<2{continue}
        'pairs: for (i,a) in children.iter().enumerate(){
            for (j,b) in children.iter().enumerate().skip(i+1){
                probes+=1;ensure!(probes<=cap,"factor probe cap");
                if unused.contains(a)&&unused.contains(b)&&p[a]==p[b]&&scaled_eq(&p[u],&p[a],-2) {
                    let common=u.iter().enumerate().filter_map(|(k,v)|(k!=i&&k!=j).then_some(*v)).collect();
                    plan.push((Block::Xor(common,u[j],u[i]),p[a].clone()));
                    unused.remove(u);unused.remove(a);unused.remove(b);break 'pairs
                }
            }
        }
    }
    Ok((plan,unused,probes))
}

impl WmcManager {
    #[doc(hidden)]
    pub fn research_factored_cnf(ps:&PathSum,epsilon:f64,cap:usize)->Result<(String,usize,usize)> {
        ensure!(ps.v.continuous_vars.is_empty(),"continuous variables unsupported");
        ensure!(ps.f.functions.len()==ps.v.num_qubits,"invalid output domain");
        let mut domain:Vec<_>=ps.v.path_vars.iter().copied().collect();domain.sort_unstable();
        ensure!(domain.len()<=1_000_000&&ps.p.terms.len()<=1_000_000,"factor resource cap");
        ensure!((0..ps.v.num_qubits).all(|i|ps.v.path_vars.contains(&(i as u32))),"missing input");
        let valid=|m:&Monomial|m.windows(2).all(|p|p[0]<p[1])&&m.iter().all(|v|ps.v.path_vars.contains(v));
        for (m,c) in &ps.p.terms {
            ensure!(valid(m)&&m.len()<=128&&c.symbols.is_empty(),"invalid or unsupported phase");
            ensure!(c.constant.denom>0&&c.constant.numer>=0&&c.constant.numer<c.constant.denom,"noncanonical turns");
        }
        for f in &ps.f.functions {ensure!(f.iter().all(valid),"invalid output support");}
        let outputs=ps.f.functions.iter().fold(0usize,|a,f|a.saturating_add(f.len().saturating_mul(2).saturating_add(1)));
        ensure!(domain.len().saturating_add(ps.p.terms.len().saturating_mul(2)).saturating_add(outputs)<i32::MAX as usize,"DIMACS ID cap");
        let (plan,unused,probes)=factor_plan(ps,cap.min(3_000_000))?;
        let bits=crate::precise_weight::bits_for_distance(epsilon,ps.p.terms.len())?;
        let mut w=Self::new(ps);w.enable_precise_gpmc_weights(bits);
        for v in domain {w.get_dimacs_var(v);}
        let mut cache=BTreeMap::new();
        for (block,c) in plan {
            let ops=match block {
                Block::Complement(a,b)=>{
                    let mut ops:Vec<_>=a.iter().map(|v|w.var_map[v]).collect();ops.push(-w.var_map[&b]);ops
                }
                Block::Xor(common,x,y)=>{
                    let a=w.var_map[&x];let b=w.var_map[&y];
                    let z=xor(&mut w,a,b,&mut cache);
                    let mut ops:Vec<_>=common.iter().map(|v|w.var_map[v]).collect();ops.push(z);ops
                }
            };
            weighted(&mut w,&ops,&c,bits)?;
        }
        for m in unused {
            let ops:Vec<_>=m.iter().map(|v|w.var_map[v]).collect();
            weighted(&mut w,&ops,&ps.p.terms[&m],bits)?;
        }
        canonical_trace(&mut w,ps);
        Ok((w.try_to_dimacs_string("gpmc")?,probes,bits))
    }
}

/// Explicit experimental entry point: accepts a residual PathSum, preserves
/// original term-count precision budget and emits canonical GPMC bytes.
/// No automatic selection, solver invocation, or verification verdict.
impl WmcManager {
    #[doc(hidden)]
    pub fn research_parity_cnf(ps:&PathSum,epsilon:f64,cap:usize)->Result<(String,usize,usize)> {
        let (w,work,bits)=Self::research_parity_manager(ps,epsilon,cap)?;
        Ok((w.try_to_dimacs_string("gpmc")?,work,bits))
    }

    pub(crate) fn research_parity_manager(ps:&PathSum,epsilon:f64,cap:usize)->Result<(Self,usize,usize)> {
        Self::research_parity_impl(ps,epsilon,cap,false)?.ok_or_else(||anyhow!("forced parity unexpectedly rejected"))
    }

    #[cfg(feature="research-parity-e2e")]
    pub(crate) fn research_auto_parity_manager(ps:&PathSum,epsilon:f64)->Result<Option<(Self,usize,usize)>> {
        // Cheap eligibility before cloning any rational coefficients.
        // Conservative exploratory policy, not a proof of solver speed.
        if ps.p.terms.len()>100_000 || ps.p.terms.len()<128 ||
            ps.p.terms.values().filter(|c|c.radians.as_ref().is_some_and(|r|!r.is_zero())).take(128).count()<128 ||
            !ps.v.continuous_vars.is_empty() || ps.p.terms.values().any(|c|!c.symbols.is_empty()) {
            return Ok(None)
        }
        Self::research_parity_impl(ps,epsilon,200_000,true)
    }

    #[cfg(feature="research-parity-e2e")]
    #[doc(hidden)]
    pub fn research_auto_parity_cnf(ps:&PathSum,epsilon:f64)->Result<Option<String>> {
        Self::research_auto_parity_manager(ps,epsilon)?.map(|(w,_,_)|w.try_to_dimacs_string("gpmc")).transpose()
    }

    fn research_parity_impl(ps:&PathSum,epsilon:f64,cap:usize,auto:bool)->Result<Option<(Self,usize,usize)>> {
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
        let (parity,work)=match inverse(&rad,cap.min(3_000_000)) {
            Ok(v)=>v,
            Err(_) if auto=>return Ok(None),
            Err(e)=>return Err(e),
        };
        if auto {
            // Require at least 2x exact radian-factor compression and 20%
            // savings in BOTH complete CNF dimensions, before MPFR calls or
            // allocating any candidate clause. Same trace cost for both.
            if parity.len().saturating_mul(2)>rad.len(){return Ok(None)}
            let mut tv=0usize;let mut tc=0usize;
            for f in &ps.f.functions {
                if f.is_empty(){tv+=1;tc+=1;}
                else {
                    tv+=f.iter().filter(|m|m.len()!=1).count()+f.len()-1;
                    tc+=f.iter().filter(|m|m.len()!=1).map(|m|m.len()+1).sum::<usize>()+4*(f.len()-1);
                }
                tc+=2;
            }
            let fv=domain.len()+tv+ps.p.terms.len();
            let fc=tc+ps.p.terms.keys().map(|m|m.len()+1).sum::<usize>();
            let mut mono:std::collections::BTreeSet<&Monomial>=turns.keys().collect();
            mono.extend(parity.keys().filter(|m|m.len()<=1));
            let mut prefix=std::collections::BTreeSet::new();
            let mut multi=0usize;
            for m in parity.keys().filter(|m|m.len()>1) {
                multi+=1;
                for k in 2..=m.len(){prefix.insert(&m[..k]);}
            }
            let pv=domain.len()+tv+mono.len()+multi+prefix.len();
            let pc=tc+mono.iter().map(|m|m.len()+1).sum::<usize>()+2*multi+4*prefix.len();
            if (pv as u128)*5>(fv as u128)*4 || (pc as u128)*5>(fc as u128)*4 {return Ok(None)}
        }
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
        canonical_trace(&mut w,ps);
        Ok(Some((w,work,bits)))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn factor_exact_and_cap(){
        let mut ps=PathSum::new(3);
        let c=coefficient(Rational::QUARTER,Some(&BigRational::new(1.into(),7.into())));
        let neg2=coefficient(Rational::HALF,Some(&BigRational::new((-2).into(),7.into())));
        ps.p.terms.insert(vec![0,1],c.clone());
        ps.p.terms.insert(vec![0,2],c.clone());
        ps.p.terms.insert(vec![0,1,2],neg2);
        let (plan,left,_)=factor_plan(&ps,100).unwrap();
        assert_eq!(plan.len(),1);assert!(left.is_empty());
        assert!(matches!(&plan[0].0,Block::Xor(common,_,_) if common==&vec![0]));
        assert!(factor_plan(&ps,0).is_err());
        let target=ps.p.terms.get_mut(&vec![0,1,2]).unwrap();
        *target.radians.as_mut().unwrap()+=BigRational::new(1.into(),BigInt::from(10).pow(40));
        assert!(factor_plan(&ps,100).unwrap().0.is_empty());
    }
    #[test]
    fn exact_inverse_and_cap(){
        let c=BigRational::new(1.into(),7.into());
        let p=RadMap::from([(vec![0],c.clone()),(vec![1],c.clone()),(vec![0,1],-&c-&c)]);
        let (q,work)=inverse(&p,3).unwrap();
        assert_eq!(q,RadMap::from([(vec![0,1],c)]));assert_eq!(work,3);
        assert!(inverse(&p,2).is_err());
    }
}
