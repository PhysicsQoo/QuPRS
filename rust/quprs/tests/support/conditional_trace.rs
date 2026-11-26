//! Trace-only exact constraint substitution pilot. No EQ verdict.
use quprs::{PathSum,pathsum::PhasePolynomial};
use rustc_hash::FxHashSet;
type Poly=FxHashSet<Vec<u32>>;
const TERM_CAP:usize=4096;
const RHS_CAP:usize=8;
const WORK_CAP:usize=32768;
const STEP_CAP:usize=32;

fn toggle(p:&mut Poly,mut m:Vec<u32>){
    m.sort_unstable();m.dedup();
    if !p.insert(m.clone()){p.remove(&m);}
}
fn sub(p:&Poly,y:u32,rhs:&Poly)->Poly{
    let mut q=Poly::default();
    for m in p{
        if m.contains(&y){
            let rest:Vec<_>=m.iter().copied().filter(|&v|v!=y).collect();
            for r in rhs{let mut a=rest.clone();a.extend(r);toggle(&mut q,a);}
        }else{toggle(&mut q,m.clone());}
    }
    q
}
#[derive(Clone)]
struct Trace{
    p:PhasePolynomial, constraints:Vec<Poly>, live:PolyIds, n:usize
}
type PolyIds=FxHashSet<u32>;
impl Trace{
    fn from_native(ps:&PathSum)->Option<Self>{
        let n=ps.v.num_qubits;
        if ps.rr_approximate||ps.rr_tolerance!=0.0||!ps.v.continuous_vars.is_empty()
            ||ps.f.functions.len()!=n||(0..n).any(|x|!ps.v.path_vars.contains(&(x as u32)))
            ||ps.p.terms.iter().any(|(m,c)|!c.symbols.is_empty()||m.iter().any(|v|!ps.v.path_vars.contains(v)))
            ||ps.f.functions.iter().flatten().any(|m|m.iter().any(|v|!ps.v.path_vars.contains(v))){
            return None;
        }
        let mut constraints=ps.f.functions.clone();
        for (i,p) in constraints.iter_mut().enumerate(){toggle(p,vec![i as u32]);}
        Some(Self{p:ps.p.clone(),constraints,live:ps.v.path_vars.clone(),n})
    }
    // Adapter for the existing production trace encoder ONLY. Its
    // output rows encode the remaining equations, not an operator.
    // Never send this view through RR, circuit comparison or normalization.
    fn encoding_view(&self, original:&PathSum)->PathSum{
        assert!(self.constraints.len()<=self.n);
        let mut out=original.clone();
        out.p=self.p.clone();
        out.v.path_vars=self.live.clone();
        for i in 0..self.n{
            let mut q=self.constraints.get(i).cloned().unwrap_or_default();
            toggle(&mut q,vec![i as u32]);
            out.f.functions[i]=q;
        }
        out
    }
    fn size(&self)->usize{self.p.terms.len()+self.constraints.iter().map(|p|p.len()).sum::<usize>()}
    fn empty(&self)->bool{self.constraints.iter().any(|p|p.len()==1&&p.contains(&Vec::new()))}
    fn step(&mut self)->Option<(u32,usize)>{
        if self.empty()||self.size()>TERM_CAP{return None;}
        // Each equation is q=0. y XOR r=0 admits exactly one y for
        // every remaining assignment; no factor of two is introduced.
        let mut choices=Vec::new();
        for (i,q) in self.constraints.iter().enumerate(){
            if q.is_empty()||q.len()>RHS_CAP+1{continue;}
            for m in q.iter().filter(|m|m.len()==1){
                let y=m[0];
                if (y as usize)<self.n||!self.live.contains(&y)
                    ||q.iter().any(|t|t!=m&&t.contains(&y)){continue;}
                let len=q.len()-1;
                let affected=self.p.terms.keys().filter(|m|m.contains(&y)).count();
                let ca=self.constraints.iter().flatten().filter(|m|m.contains(&y)).count();
                let work=affected.checked_mul(1usize<<len)?.checked_add(ca.checked_mul(len.max(1))?)?;
                if work<=WORK_CAP{choices.push((work,len,y,i));}
            }
        }
        choices.sort_unstable();
        for (_,len,y,i) in choices{
            let mut rhs=self.constraints[i].clone();rhs.remove(&vec![y]);
            let mut trial=self.clone();
            trial.p.substitute_var_with_poly(y,&rhs);
            trial.constraints=trial.constraints.iter().enumerate()
                .filter(|(j,_)|*j!=i).map(|(_,q)|sub(q,y,&rhs)).filter(|q|!q.is_empty()).collect();
            if trial.size()>TERM_CAP{continue;}
            assert!(trial.live.remove(&y));
            assert!(trial.p.terms.keys().all(|m|m.iter().all(|v|trial.live.contains(v))));
            assert!(trial.constraints.iter().flatten().all(|m|m.iter().all(|v|trial.live.contains(v))));
            *self=trial;
            return Some((y,len));
        }
        None
    }
    // Trace-specific integration: never treat the encoding view as an
    // operator. Both phase and every remaining constraint are transported.
    // Each accepted step below has raw sum multiplier exactly 2.
    fn integrate(&mut self)->Option<(&'static str,u32)>{
        if self.empty()||self.size()>TERM_CAP{return None;}
        let mut ids:Vec<_>=self.live.iter().copied().filter(|&v|v as usize>=self.n).collect();
        ids.sort_unstable();
        for &y in &ids{
            if self.constraints.iter().flatten().any(|m|m.contains(&y)){continue;}
            if !self.p.terms.keys().any(|m|m.contains(&y)){
                assert!(self.live.remove(&y));
                return Some(("elim",y));
            }
        }
        for &y in &ids{
            if self.constraints.iter().flatten().any(|m|m.contains(&y)){continue;}
            let ys:Vec<_>=self.p.terms.iter().filter(|(m,_)|m.contains(&y)).collect();
            if ys.is_empty()||ys.len()>RHS_CAP+1||ys.iter().any(|(_,c)|!c.is_pure_half()){continue;}
            let phi:Poly=ys.iter().map(|(m,_)|m.iter().copied().filter(|&v|v!=y).collect()).collect();
            let mut pivots:Vec<_>=phi.iter().filter(|m|m.len()==1)
                .filter(|m|m[0] as usize>=self.n&&self.live.contains(&m[0]))
                .filter(|m|phi.iter().all(|q|q==*m||!q.contains(&m[0])))
                .map(|m|m[0]).collect();
            pivots.sort_unstable();
            for z in pivots{
                let mut rhs=phi.clone();rhs.remove(&vec![z]);
                let len=rhs.len();
                let pa=self.p.terms.keys().filter(|m|!m.contains(&y)&&m.contains(&z)).count();
                let ca=self.constraints.iter().flatten().filter(|m|m.contains(&z)).count();
                let work=pa.checked_mul(1usize<<len)?.checked_add(ca.checked_mul(len.max(1))?)?;
                if work>WORK_CAP{continue;}
                let mut q=self.clone();
                q.p.terms.retain(|m,_|!m.contains(&y));
                q.p.substitute_var_with_poly(z,&rhs);
                q.constraints=q.constraints.iter().map(|p|sub(p,z,&rhs)).filter(|p|!p.is_empty()).collect();
                if q.size()>TERM_CAP{continue;}
                assert!(q.live.remove(&y)&&q.live.remove(&z));
                assert!(q.p.terms.keys().all(|m|m.iter().all(|v|q.live.contains(v))));
                assert!(q.constraints.iter().flatten().all(|m|m.iter().all(|v|q.live.contains(v))));
                *self=q;
                return Some(("hh",y));
            }
        }
        None
    }
    // Exact omega integration on trace-only state. The integrator
    // must not occur in ANY constraint. Raw multiplier is sqrt(2).
    fn omega(&mut self)->Option<u32>{
        use quprs::rational::{PhaseCoeff,Rational};
        if self.empty()||self.size()>TERM_CAP{return None;}
        let mut ids:Vec<_>=self.live.iter().copied().filter(|&v|v as usize>=self.n).collect();
        ids.sort_unstable();
        for y in ids{
            if self.constraints.iter().flatten().any(|m|m.contains(&y)){continue;}
            let Some(c)=self.p.terms.get(&vec![y])else{continue;};
            let positive=c.is_pure_quarter();
            if !positive&&!c.is_pure_three_quarters(){continue;}
            let ys:Vec<_>=self.p.terms.iter().filter(|(m,_)|m.len()>1&&m.contains(&y)).collect();
            if ys.len()>RHS_CAP||ys.iter().any(|(_,c)|!c.is_pure_half()){continue;}
            let phi:Poly=ys.iter().map(|(m,_)|m.iter().copied().filter(|&v|v!=y).collect()).collect();
            if (1usize<<phi.len())>WORK_CAP{continue;}
            let mut q=self.clone();
            q.p.terms.retain(|m,_|!m.contains(&y));
            q.p+=PhaseCoeff::new_constant(Rational::new(if positive{1}else{7},8));
            q.p+=(&phi,PhaseCoeff::new_constant(Rational::new(if positive{3}else{1},4)));
            if q.size()>TERM_CAP{continue;}
            assert!(q.live.remove(&y));
            assert!(q.p.terms.keys().all(|m|m.iter().all(|v|q.live.contains(v))));
            *self=q;
            return Some(y);
        }
        None
    }
}
// Alternate unique extension (factor 1) and exact integration (factor 2).
// The fuel cap applies to their combined number of accepted steps.
fn iterate(t:&mut Trace)->(usize,usize,usize){
    let (mut subs,mut elim,mut hh)=(0,0,0);
    for _ in 0..STEP_CAP{
        if t.step().is_some(){subs+=1;continue;}
        match t.integrate(){
            Some(("elim",_))=>elim+=1,
            Some(("hh",_))=>hh+=1,
            None=>break,
            _=>unreachable!(),
        }
    }
    (subs,elim,hh)
}
// Full alternation; keep the earlier Elim/HH oracle on its original
// routine so its results remain comparable.
fn iterate_all(t:&mut Trace)->(usize,usize,usize,usize){
    let (mut subs,mut elim,mut hh,mut omega)=(0,0,0,0);
    for _ in 0..STEP_CAP{
        if t.step().is_some(){subs+=1;continue;}
        match t.integrate(){
            Some(("elim",_))=>{elim+=1;continue;},
            Some(("hh",_))=>{hh+=1;continue;},
            None=>{},
            _=>unreachable!(),
        }
        if t.omega().is_some(){omega+=1;continue;}
        break;
    }
    (subs,elim,hh,omega)
}
pub(super) fn profile(ps:&PathSum,case:&str){
    let start=std::time::Instant::now();
    let Some(mut t)=Trace::from_native(ps) else{
        println!("CRR_TRACE case={case} status=unsupported");return;
    };
    if t.size()>TERM_CAP{println!("CRR_TRACE case={case} status=term_cap");return;}
    let before=t.live.len();let terms=t.p.terms.len();
    let constraints=t.constraints.iter().filter(|q|!q.is_empty()).count();
    let mut steps=0;let mut max_rhs=0;let mut pivots=Vec::new();
    for _ in 0..STEP_CAP{
        let Some((y,k))=t.step()else{break;};
        steps+=1;max_rhs=max_rhs.max(k);pivots.push(y);
    }
    let free=t.live.iter().filter(|&&v|(v as usize)>=t.n
        &&!t.p.terms.keys().any(|m|m.contains(&v))
        &&!t.constraints.iter().flatten().any(|m|m.contains(&v))).count();
    println!("CRR_TRACE case={case} status={} steps={steps} live_before={before} live_after={} phase_before={terms} phase_after={} constraints_before={constraints} constraints_after={} max_rhs={max_rhs} free_candidates={free} pivots={pivots:?} original_hidden={} trace_s={}",
        if t.empty(){"empty"}else{"profiled"},t.live.len(),t.p.terms.len(),
        t.constraints.iter().filter(|q|!q.is_empty()).count(),before-t.n,start.elapsed().as_secs_f64());
    if std::env::var_os("CRR_GPMC_COMPARE").is_some(){
        let mut iterated=Trace::from_native(ps).expect("admitted");
        let it_start=std::time::Instant::now();
        let (subs,elim,hh,omega)=iterate_all(&mut iterated);
        let multiplier_power=elim+hh;
        println!("CRR_ITERATE case={case} subs={subs} elim={elim} hh={hh} omega={omega} multiplier_power={multiplier_power} multiplier_sqrt2_power={omega} hidden_after={} phase_after={} constraints_after={} iterate_s={}",
            iterated.live.len()-iterated.n,iterated.p.terms.len(),iterated.constraints.iter().filter(|q|!q.is_empty()).count(),it_start.elapsed().as_secs_f64());
        compare_gpmc(ps,&t,&iterated,multiplier_power,omega,case);
    }
}

// Same existing encoder and GPMC adapter on both arms. The count is
// raw, not rescaled using the modified view's number of variables.
fn compare_gpmc(original:&PathSum,t:&Trace,iterated:&Trace,multiplier_power:usize,omega:usize,case:&str){
    use quprs::wmc::WmcManager;
    use quprs::precision_count::{PrintedCount,observed_distance_verdict};
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use num_traits::{Signed,ToPrimitive};
    use std::time::{Instant,Duration};
    let solver_secs=std::env::var("CRR_SOLVER_SECS").ok()
        .map(|s|s.parse::<u64>().expect("solver seconds")).unwrap_or(8);
    assert!((8..=60).contains(&solver_secs));
    let reduced=t.encoding_view(original);
    let original_twice=(2*original.v.num_qubits+original.v.path_vars.len()-original.v.num_qubits) as i32;
    let encode=|ps:&PathSum,arm:&str|->(WmcManager,usize,usize){
        let start=Instant::now();
        let mut mgr=WmcManager::new(ps);
        mgr.enable_precise_gpmc_weights(256);
        mgr.encode_trace(ps).expect("trace encode");
        let dimacs=mgr.try_to_dimacs_string("gpmc").expect("serialize");
        let header=dimacs.lines().find(|l|l.starts_with("p cnf ")).expect("DIMACS header");
        let sizes:Vec<_>=header.split_whitespace().collect();
        println!("CRR_CNF case={case} arm={arm} vars={} clauses={} weights={} bytes={} encode_and_serialize_s={} normalization_twice={original_twice}",
            sizes[2],sizes[3],mgr.numerical_weight_count(),dimacs.len(),start.elapsed().as_secs_f64());
        (mgr,sizes[2].parse().expect("vars"),sizes[3].parse().expect("clauses"))
    };
    let (a,av,ac)=encode(original,"baseline");let (b,bv,bc)=encode(&reduced,"conditioned");
    let (c,cv,cc)=encode(&iterated.encoding_view(original),"iterated");
    // Diagnostic routing only: prefer baseline unless both dimensions
    // are nonincreasing and at least one strictly improves.
    let mut route=("baseline",ac,av);
    for (arm,v,k) in [("conditioned",bv,bc),("iterated",cv,cc)]{
        if v<=av&&k<=ac&&(k,v)<(route.1,route.2){route=(arm,k,v);}
    }
    println!("CRR_ROUTE case={case} predicted_arm={} vars={} clauses={} policy=nonincreasing_cnf",route.0,route.2,route.1);
    let solve=|mgr:&WmcManager,arm:&str|->Option<PrintedCount>{
        let start=Instant::now();
        let result=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(start+Duration::from_secs(solver_secs)),90);
        let elapsed=start.elapsed().as_secs_f64();
        match result{
            Ok(c)=>{
                println!("CRR_GPMC case={case} arm={arm} status=complete call_s={elapsed} real={} imag={} format={}",c.real,c.imag,c.format_name);
                Some(c)
            }
            Err(e)=>{
                // No fabricated count or verdict; preserve the actual error.
                println!("CRR_GPMC case={case} arm={arm} status=incomplete call_s={elapsed} error={e:#}");
                None
            }
        }
    };
    let repeat=std::env::var("CRR_REPEAT").ok().map(|r|r.parse::<usize>().expect("repeat")).unwrap_or(0);
    let arms=[(&a,"baseline"),(&b,"conditioned"),(&c,"iterated")];
    let mut counts:[Option<PrintedCount>;3]=[None,None,None];
    println!("CRR_ORDER case={case} repeat={repeat} first={} second={} third={}",arms[repeat%3].1,arms[(repeat+1)%3].1,arms[(repeat+2)%3].1);
    for k in 0..3{
        let idx=(repeat+k)%3;
        counts[idx]=solve(arms[idx].0,arms[idx].1);
    }
    let [x,y,z]=counts;
    let (Some(y),Some(mut z))=(y,z)else{
        println!("CRR_PAIR case={case} status=incomplete");
        println!("CRR_COMPARE case={case} status=incomplete");return;
    };
    let scale=BigRational::from_integer(BigInt::from(1u8)<<(original_twice as usize/2));
    let bound=&scale/BigRational::from_integer(BigInt::from(10u8).pow(50));
    let dy=observed_distance_verdict(&y,original_twice,"1e-8").expect("conditioned distance");
    let factor=BigRational::from_integer(BigInt::from(1u8)<<(multiplier_power+omega/2));
    z.real*=&factor;z.imag*=&factor;
    z.real_half_unit*=&factor;z.imag_half_unit*=&factor;
    // Exact rational midpoint distance: absorb only the residual odd
    // sqrt(2) into the squared normalization exponent, not the count.
    let vz=observed_distance_verdict(&z,original_twice-(omega%2) as i32,"1e-8").expect("iterated distance");
    assert!(std::mem::discriminant(&dy)==std::mem::discriminant(&vz));
    // For the complex count parity observation, use a rational lower
    // enclosure of sqrt(2) with width 2^-384, constructed by integer
    // bisection and verified. This is not a solver error certificate.
    if omega%2==1{
        let den=BigInt::from(1u8)<<384usize;
        let target=&den*&den*2u8;
        let mut lo=den.clone();let mut hi=&den*2u8;
        while &hi-&lo>BigInt::from(1u8){
            let mid=(&hi+&lo)/2u8;
            if &mid*&mid<=target{lo=mid;}else{hi=mid;}
        }
        assert!(&lo*&lo<=target&&&hi*&hi>target);
        let root=BigRational::new(lo,den);
        z.real*=&root;z.imag*=&root;
    }
    let pair=(&y.real-&z.real).abs()+(&y.imag-&z.imag).abs();
    assert!(pair<=bound,"conditioned/iterated count disagreement for {case}");
    println!("CRR_PAIR case={case} status=matched normalized_l1_delta={:.5e}",(pair/&scale).to_f64().unwrap_or(f64::INFINITY));
    let Some(x)=x else{
        println!("CRR_COMPARE case={case} status=incomplete");return;
    };
    let delta=(&x.real-&y.real).abs()+(&x.imag-&y.imag).abs();
    assert!(delta<=bound,"raw complex count disagreement for {case}");
    let dx=observed_distance_verdict(&x,original_twice,"1e-8").expect("baseline distance");
    assert!(std::mem::discriminant(&dx)==std::mem::discriminant(&dy));
    let dz=(&x.real-&z.real).abs()+(&x.imag-&z.imag).abs();
    assert!(dz<=bound,"iterated raw complex count disagreement for {case}");
    println!("CRR_COMPARE case={case} status=matched normalized_l1_delta={:.5e} iterated_normalized_l1_delta={:.5e} distance_midpoint_match=true normalization_twice={original_twice}",
        (delta/&scale).to_f64().unwrap_or(f64::INFINITY),(dz/&scale).to_f64().unwrap_or(f64::INFINITY));
}


// Independent finite exact oracle: per-input signed/cyclotomic exponent
// histograms before/after substitution. Equality is stronger than the
// unnormalized trace amplitude equality in the admitted Z8 fragment.
#[cfg(test)]
fn hist(t:&Trace,x:usize)->[u32;8]{
    let mut h=[0;8];
    let mut ids:Vec<_>=t.live.iter().copied().filter(|&v|v as usize>=t.n).collect();ids.sort_unstable();
    assert!(ids.len()<=8);
    for a in 0..(1usize<<ids.len()){
        let bit=|v:u32|if (v as usize)<t.n{(x>>v)&1!=0}else{
            let i=ids.iter().position(|&z|z==v).expect("live reference");(a>>i)&1!=0
        };
        let mono=|m:&Vec<u32>|m.iter().all(|&v|bit(v));
        if t.constraints.iter().any(|q|q.iter().filter(|m|mono(m)).count()%2!=0){continue;}
        let e=t.p.terms.iter().filter(|(m,_)|mono(m)).map(|(_,c)|{
            assert!(c.radians.is_none()&&c.symbols.is_empty());
            assert_eq!(8%c.constant.denom,0);
            8*c.constant.numer/c.constant.denom
        }).sum::<i64>().rem_euclid(8) as usize;
        h[e]+=1;
    }
    h
}
#[test]
fn exact_trace_constraint_substitution(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut seed=17u64;
    let mut next=||{seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);seed>>32};
    let mut checks=0;let mut steps=0;
    for _ in 0..512{
        let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
        for _ in 0..3{ps.v.get_fresh_var();}
        // Force equation y2 XOR R(x0,x1,y3,y4)=0, with arbitrary
        // additional diagonal constraint, arbitrary Z8 phases.
        for q in &mut ps.f.functions{q.clear();}
        ps.f.functions[0].insert(vec![0]);ps.f.functions[0].insert(vec![2]);
        for mask in 0u32..16{
            if next()%5==0{let ids=[0u32,1,3,4];toggle(&mut ps.f.functions[0],ids.iter().enumerate().filter(|(i,_)|mask>>i&1!=0).map(|(_,v)|*v).collect());}
        }
        for mask in 0u32..32{
            let m:Vec<_>=(0..5).filter(|i|mask>>i&1!=0).collect();
            if next()%7==0{toggle(&mut ps.f.functions[1],m.clone());}
            if next()%4==0{ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new((next()%8) as i64,8)));}
        }
        let original=Trace::from_native(&ps).unwrap();let mut t=original.clone();
        for _ in 0..STEP_CAP{if t.step().is_none(){break;}steps+=1;}
        let view=t.encoding_view(&ps);
        let roundtrip=Trace::from_native(&view).unwrap();
        for x in 0..4{assert_eq!(hist(&original,x),hist(&t,x));assert_eq!(hist(&t,x),hist(&roundtrip,x));checks+=1;}
    }
    assert!(steps>0);
    println!("CRR_TRACE_ORACLE models=512 input_hist_checks={checks} substitutions={steps}");
}


#[test]
fn exact_trace_iterated_elim_hh(){
    use quprs::rational::{PhaseCoeff,Rational};
    // Z8 quotient Z[z]/(z^4+1): histogram equality is not required
    // after interference cancellation; compare exact signed coefficients.
    fn coeff(t:&Trace,x:usize,pow:usize)->[i64;4]{
        let h=hist(t,x);
        std::array::from_fn(|i|(h[i] as i64-h[i+4] as i64)*(1i64<<pow))
    }
    let mut seed=29u64;
    let mut next=||{seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);seed>>32};
    let (mut checks,mut total_elim,mut total_hh)=(0,0,0);
    for k in 0..512{
        let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
        for _ in 0..5{ps.v.get_fresh_var();}
        // y2 is an HH integrator, z3 its internal pivot.
        // y2 is absent from constraints; the pivot occurs in the phase
        // and constraints. y6 is initially free in every model.
        ps.p.add_term(vec![2,3],PhaseCoeff::HALF);
        for mask in 0u32..16{
            let ids=[0u32,1,4,5];
            let m:Vec<_>=ids.iter().enumerate().filter(|(i,_)|mask>>i&1!=0).map(|(_,v)|*v).collect();
            if next()%7==0{let mut q=m.clone();q.push(2);ps.p.add_term(q,PhaseCoeff::HALF);}
        }
        // Output equation with no isolated singleton pivot at first:
        // ensures HH can expose new constraint substitution.
        ps.f.functions[0].insert(vec![3,4]);
        ps.f.functions[0].insert(vec![4,5]);
        if k%2==0{ps.f.functions[1].insert(vec![3,5]);}
        for mask in 0u32..32{
            let ids=[0u32,1,3,4,5];
            let m:Vec<_>=ids.iter().enumerate().filter(|(i,_)|mask>>i&1!=0).map(|(_,v)|*v).collect();
            if next()%5==0{ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new((next()%8) as i64,8)));}
        }
        let orig=Trace::from_native(&ps).unwrap();let mut t=orig.clone();
        let (_,elim,hh)=iterate(&mut t);total_elim+=elim;total_hh+=hh;
        let round=Trace::from_native(&t.encoding_view(&ps)).unwrap();
        for x in 0..4{
            assert_eq!(coeff(&orig,x,0),coeff(&t,x,elim+hh));
            assert_eq!(coeff(&t,x,elim+hh),coeff(&round,x,elim+hh));
            checks+=1;
        }
    }
    assert!(total_elim>=512&&total_hh>0);
    println!("CRR_ITERATE_ORACLE models=512 checks={checks} elim={total_elim} hh={total_hh}");
    // Negative normalization control: omitting a free-variable factor
    // changes a nonzero trace coefficient exactly.
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;ps.v.get_fresh_var();
    let orig=Trace::from_native(&ps).unwrap();let mut t=orig.clone();
    let (_,e,h)=iterate(&mut t);assert_eq!((e,h),(1,0));
    assert_ne!(coeff(&orig,0,0),coeff(&t,0,0));
    assert_eq!(coeff(&orig,0,0),coeff(&t,0,1));
}


#[test]
fn exact_trace_iterated_omega(){
    use quprs::rational::{PhaseCoeff,Rational};
    // Exact multiplication by sqrt(2)=zeta8-zeta8^3 in Z[z]/(z^4+1).
    fn coeff(t:&Trace,x:usize,pow:usize,omega:usize)->[i64;4]{
        let h=hist(t,x);
        let mut a:[i64;4]=std::array::from_fn(|i|(h[i] as i64-h[i+4] as i64)*(1i64<<pow));
        for _ in 0..omega{
            let mut b=[0i64;4];
            for (i,&v) in a.iter().enumerate(){
                for (shift,sign) in [(1usize,1i64),(3,-1)]{
                    let j=i+shift;
                    b[j%4]+=v*sign*if j>=4{-1}else{1};
                }
            }
            a=b;
        }
        a
    }
    let (mut checks,mut total_omega,mut odd,mut even)=(0,0,0,0);
    for k in 0u32..512{
        let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
        for _ in 0..4{ps.v.get_fresh_var();}
        // q0= y2 XOR x1: unique extension first; exposes a quarter
        // singleton on y3 from an originally obstructing interaction.
        ps.f.functions[0].insert(vec![2]);
        ps.f.functions[0].insert(vec![1]);
        ps.p.add_term(vec![3],PhaseCoeff::new_constant(Rational::new(if k&1==0{1}else{3},4)));
        ps.p.add_term(vec![2,3],PhaseCoeff::HALF);
        if k&2!=0{ps.p.add_term(vec![0,3],PhaseCoeff::HALF);}
        if k&4!=0{ps.p.add_term(vec![0,1,3],PhaseCoeff::HALF);}
        // Optional second omega, giving even/odd powers. Variable y5
        // remains constrained or free depending on fixture.
        if k&8!=0{
            ps.p.add_term(vec![4],PhaseCoeff::new_constant(Rational::new(if k&16==0{1}else{3},4)));
            if k&32!=0{ps.p.add_term(vec![0,4],PhaseCoeff::HALF);}
        }
        if k&64!=0{ps.f.functions[1].insert(vec![0,5]);}
        if k&128!=0{ps.p.add_term(vec![0,1],PhaseCoeff::new_constant(Rational::new(3,8)));}
        if k&256!=0{ps.p.add_term(vec![5],PhaseCoeff::HALF);}
        let orig=Trace::from_native(&ps).unwrap();let mut t=orig.clone();
        let (_,e,h,o)=iterate_all(&mut t);
        total_omega+=o;if o%2==1{odd+=1;}else{even+=1;}
        let round=Trace::from_native(&t.encoding_view(&ps)).unwrap();
        for x in 0..4{
            assert_eq!(coeff(&orig,x,0,0),coeff(&t,x,e+h,o));
            assert_eq!(coeff(&t,x,e+h,o),coeff(&round,x,e+h,o));
            checks+=1;
        }
    }
    assert!(odd>0&&even>0&&total_omega>=512);
    // A constrained omega candidate cannot be integrated out.
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();
    ps.p.add_term(vec![y],PhaseCoeff::QUARTER);
    ps.f.functions[0].insert(vec![0,y]);
    let mut t=Trace::from_native(&ps).unwrap();assert!(t.omega().is_none());
    // Missing sqrt(2) is observably wrong.
    ps.f.functions[0].remove(&vec![0,y]);
    let orig=Trace::from_native(&ps).unwrap();let mut t=orig.clone();
    assert_eq!(t.omega(),Some(y));
    assert_ne!(coeff(&orig,0,0,0),coeff(&t,0,0,0));
    assert_eq!(coeff(&orig,0,0,0),coeff(&t,0,0,1));
    println!("CRR_OMEGA_ORACLE models=512 checks={checks} omega={total_omega} odd_models={odd} even_models={even}");
}
