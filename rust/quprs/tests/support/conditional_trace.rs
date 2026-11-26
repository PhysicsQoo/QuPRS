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
    // Cheap structural proxies; not actual CNF size or solver time.
    fn cost(&self)->(usize,usize){
        let phase=self.p.terms.keys().map(|m|1+m.len()).sum::<usize>();
        let constraints=self.constraints.iter().flatten().map(|m|1+m.len()).sum::<usize>();
        (phase,phase+constraints+self.live.len())
    }
    fn accepts(&self,trial:&Trace)->bool{
        let a=self.cost();let b=trial.cost();
        b.0<=a.0&&b.1<a.1
    }
    fn step(&mut self)->Option<(u32,usize)>{
        self.step_policy(false,&mut 0usize)
    }
    fn step_policy(&mut self,guarded:bool,rejected:&mut usize)->Option<(u32,usize)>{
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
        let limit=if guarded{16}else{usize::MAX};
        for (_,len,y,i) in choices.into_iter().take(limit){
            let mut rhs=self.constraints[i].clone();rhs.remove(&vec![y]);
            let mut trial=self.clone();
            trial.p.substitute_var_with_poly(y,&rhs);
            trial.constraints=trial.constraints.iter().enumerate()
                .filter(|(j,_)|*j!=i).map(|(_,q)|sub(q,y,&rhs)).filter(|q|!q.is_empty()).collect();
            if trial.size()>TERM_CAP{continue;}
            assert!(trial.live.remove(&y));
            assert!(trial.p.terms.keys().all(|m|m.iter().all(|v|trial.live.contains(v))));
            assert!(trial.constraints.iter().flatten().all(|m|m.iter().all(|v|trial.live.contains(v))));
            if guarded&&!self.accepts(&trial){*rejected+=1;continue;}
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
    let (s,e,h,o,_)=iterate_policy(t,STEP_CAP,false);
    (s,e,h,o)
}
// Guard each transition transactionally. For integration we inspect
// only the first native-eligible candidate per rule family; a rejected
// integration is not evidence that all alternatives are unprofitable.
fn iterate_policy(t:&mut Trace,fuel:usize,guarded:bool)->(usize,usize,usize,usize,usize){
    assert!(fuel<=64);
    let (mut subs,mut elim,mut hh,mut omega,mut rejected)=(0,0,0,0,0);
    for _ in 0..fuel{
        if t.step_policy(guarded,&mut rejected).is_some(){subs+=1;continue;}
        let mut q=t.clone();
        if let Some((rule,_))=q.integrate(){
            if !guarded||t.accepts(&q){
                match rule{"elim"=>elim+=1,"hh"=>hh+=1,_=>unreachable!()}
                *t=q;continue;
            }
            rejected+=1;
        }
        let mut q=t.clone();
        if q.omega().is_some(){
            if !guarded||t.accepts(&q){omega+=1;*t=q;continue;}
            rejected+=1;
        }
        break;
    }
    (subs,elim,hh,omega,rejected)
}
pub(super) fn profile(ps:&PathSum,case:&str){
    if std::env::var_os("CRR_ROUTED").is_some(){route_profile(ps,case);return;}
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
        let aware=std::env::var_os("CRR_COST_AWARE").is_some();
        let original=Trace::from_native(ps).expect("admitted");
        if aware{
            for fuel in [32,64]{
                for guarded in [false,true]{
                    let mut q=original.clone();let start=std::time::Instant::now();
                    let (a,b,c,d,rejected)=iterate_policy(&mut q,fuel,guarded);
                    let cost=q.cost();
                    println!("CRR_FUEL case={case} fuel={fuel} guarded={guarded} subs={a} elim={b} hh={c} omega={d} rejected={rejected} fuel_exhausted={} hidden={} phase_terms={} phase_proxy={} total_proxy={} original_phase_proxy={} original_total_proxy={} elapsed_s={}",
                        a+b+c+d==fuel,q.live.len()-q.n,q.p.terms.len(),cost.0,cost.1,original.cost().0,original.cost().1,start.elapsed().as_secs_f64());
                }
            }
        }
        let mut iterated=original.clone();
        let it_start=std::time::Instant::now();
        let fuel=if aware{64}else{STEP_CAP};
        let (subs,elim,hh,omega,rejected)=iterate_policy(&mut iterated,fuel,aware);
        let multiplier_power=elim+hh;
        println!("CRR_ITERATE case={case} subs={subs} elim={elim} hh={hh} omega={omega} multiplier_power={multiplier_power} multiplier_sqrt2_power={omega} hidden_after={} phase_after={} constraints_after={} iterate_s={} guarded={aware} fuel={fuel} rejected={rejected}",
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
        let mut guarded=orig.clone();
        let (_,ge,gh,go,_)=iterate_policy(&mut guarded,64,true);
        assert!(guarded.cost().0<=orig.cost().0&&guarded.cost().1<=orig.cost().1);
        for x in 0..4{assert_eq!(coeff(&orig,x,0,0),coeff(&guarded,x,ge+gh,go));}
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


#[test]
fn exact_trace_cost_policy_rejects_growth(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();
    let z=ps.v.get_fresh_var();
    let w=ps.v.get_fresh_var();
    // Sole isolated internal pivot y = x*z XOR x*w. An eighth-cycle
    // coefficient expands to three nonzero arithmetic monomials.
    ps.f.functions[0].insert(vec![y]);
    ps.f.functions[0].insert(vec![0,z]);
    ps.f.functions[0].insert(vec![0,w]);
    ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,8)));
    let orig=Trace::from_native(&ps).unwrap();
    let mut greedy=orig.clone();assert!(greedy.step().is_some());
    assert!(greedy.cost().0>orig.cost().0);
    let mut guarded=orig.clone();let mut rejected=0;
    assert!(guarded.step_policy(true,&mut rejected).is_none());
    assert_eq!(rejected,1);
    assert_eq!(guarded.cost(),orig.cost());
    for x in 0..2{assert_eq!(hist(&orig,x),hist(&guarded,x));}
    // Safe one-monomial substitution must not be rejected.
    ps.f.functions[0].remove(&vec![0,w]);
    let orig=Trace::from_native(&ps).unwrap();
    // Use a singleton input RHS to avoid a phase-degree increase.
    ps.f.functions[0].remove(&vec![0,z]);
    ps.f.functions[0].remove(&vec![0]); // q = y XOR x
    let orig2=Trace::from_native(&ps).unwrap();
    let mut q=orig2.clone();let mut rejected=0;
    assert!(q.step_policy(true,&mut rejected).is_some());
    assert_eq!(rejected,0);
    for x in 0..2{assert_eq!(hist(&orig2,x),hist(&q,x));}
    assert!(q.cost().0<=orig2.cost().0&&q.cost().1<orig2.cost().1);
    assert!(orig.cost().1>0);
    println!("CRR_COST_ORACLE reject_growth=1 accept_nonincrease=1 guarded_omega_models=512");
}


// Research-only actual dispatch. Timed interval includes post-RR
// admission, reductions, discarded encodings, selected solver and
// count restoration/classification. Native RR is shared upstream.
type Count=quprs::precision_count::PrintedCount;
type Rat=num_rational::BigRational;
fn restore_count(mut c:Count,m:usize,o:usize,twice:i32)->(Count,quprs::precision_count::PrintedVerdict){
    use num_bigint::BigInt;
    use quprs::precision_count::observed_distance_verdict;
    let factor=Rat::from_integer(BigInt::from(1u8)<<(m+o/2));
    c.real*=&factor;c.imag*=&factor;
    c.real_half_unit*=&factor;c.imag_half_unit*=&factor;
    let verdict=observed_distance_verdict(&c,twice-(o%2) as i32,"1e-8").expect("distance");
    if o%2==1{
        let den=BigInt::from(1u8)<<384usize;
        let target=&den*&den*2u8;
        let mut lo=den.clone();let mut hi=&den*2u8;
        while &hi-&lo>BigInt::from(1u8){
            let mid=(&hi+&lo)/2u8;
            if &mid*&mid<=target{lo=mid;}else{hi=mid;}
        }
        assert!(&lo*&lo<=target&&&hi*&hi>target);
        let root=Rat::new(lo,den);
        c.real*=&root;c.imag*=&root;
        // Half-unit fields now describe the scaled printed resolution,
        // not the sqrt enclosure or a certified numerical error bound.
        c.real_half_unit*=&root;c.imag_half_unit*=&root;
    }
    (c,verdict)
}
fn route_encode(ps:&PathSum)->(quprs::wmc::WmcManager,usize,usize){
    let mut mgr=quprs::wmc::WmcManager::new(ps);
    mgr.enable_precise_gpmc_weights(256);
    mgr.encode_trace(ps).expect("encode");
    let dimacs=mgr.try_to_dimacs_string("gpmc").expect("serialize");
    let h:Vec<_>=dimacs.lines().find(|l|l.starts_with("p cnf ")).expect("header").split_whitespace().collect();
    (mgr,h[2].parse().expect("vars"),h[3].parse().expect("clauses"))
}
// Linear-time-in-support heuristic (up to sorting small monomials).
// Only inspect singleton equalities q=y XOR z, and never merge two
// inputs. This is a projection of supports, NOT a rewrite or proof.
// Duplicate projected monomials may cancel in exact phase arithmetic;
// this proxy counts each distinct support once, without coefficients.
type AliasMap=rustc_hash::FxHashMap<u32,u32>;
fn alias_root(parent:&AliasMap,mut v:u32)->u32{
    while let Some(&p)=parent.get(&v){v=p;}v
}
// Optional witness recording uses the very same union loop as the
// uninstrumented experimental reducer; the no-op callback allocates no log.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
struct UnionWitness { x:u32, y:u32, child:u32, par:u32 }
fn alias_map_observe(t:&Trace,mut emit:impl FnMut(UnionWitness))->AliasMap{
    let mut pairs:Vec<_>=t.constraints.iter().filter(|q|q.len()==2&&q.iter().all(|m|m.len()==1))
        .map(|q|{let mut v:Vec<_>=q.iter().map(|m|m[0]).collect();v.sort_unstable();(v[0],v[1])}).collect();
    pairs.sort_unstable();
    let mut parent=AliasMap::default();
    for (x,y) in pairs{
        let a=alias_root(&parent,x);let b=alias_root(&parent,y);
        let lo=a.min(b);let hi=a.max(b);
        if lo!=hi&&hi as usize>=t.n{
            // Orient endpoints to match the Lean UnionStep relation.
            let (x,y)=if a==hi{(x,y)}else{(y,x)};
            emit(UnionWitness{x,y,child:hi,par:lo});
            parent.insert(hi,lo);
        }
    }
    parent
}
fn alias_map(t:&Trace)->AliasMap{alias_map_observe(t,|_|{})}
fn alias_mono(parent:&AliasMap,m:&[u32])->Vec<u32>{
    let mut v:Vec<_>=m.iter().map(|&x|alias_root(parent,x)).collect();
    v.sort_unstable();v.dedup();v
}
fn alias_screen(t:&Trace)->(usize,usize,usize){
    let parent=alias_map(t);
    let projected:Poly=t.p.terms.keys().map(|m|alias_mono(&parent,m)).collect();
    (parent.len(),t.cost().0,projected.iter().map(|m|1+m.len()).sum())
}
// Every forest edge is an equality of two currently distinct roots,
// with an internal child. Eliminating the forest has unique extension.
// All original equations are mapped (including nonforest edges,
// cycles, and constraints relating two inputs); only zero rows vanish.
// Coefficients merge in the native exact phase domain, constraints in F2.
fn batch_alias(t:&mut Trace,fuel:usize)->usize{
    batch_alias_observe(t,fuel,|_|{},|_|{})
}
// A trial may emit tentative links, but only the commit callback
// publishes a final parent map after all admission checks succeed.
fn batch_alias_observe(t:&mut Trace,fuel:usize,emit:impl FnMut(UnionWitness),
    commit:impl FnOnce(&AliasMap))->usize{
    if t.empty()||t.size()>TERM_CAP{return 0;}
    let parent=alias_map_observe(t,emit);
    if parent.is_empty()||parent.len()>fuel{return 0;}
    let mut q=t.clone();
    let mut phase=PhasePolynomial::new();
    // Deterministic insertion order for reproducible coefficient merging.
    let mut terms:Vec<_>=t.p.terms.iter().collect();
    terms.sort_unstable_by(|(a,_),(b,_)|a.cmp(b));
    for (m,c) in terms{phase.add_term(alias_mono(&parent,m),c.clone());}
    q.p=phase;
    q.constraints=t.constraints.iter().map(|p|{
        let mut r=Poly::default();
        for m in p{toggle(&mut r,alias_mono(&parent,m));}
        r
    }).filter(|p|!p.is_empty()).collect();
    for &v in parent.keys(){assert!(v as usize>=q.n&&q.live.remove(&v));}
    assert!(q.p.terms.keys().all(|m|m.iter().all(|v|q.live.contains(v))));
    assert!(q.constraints.iter().flatten().all(|m|m.iter().all(|v|q.live.contains(v))));
    if q.size()>TERM_CAP||!t.accepts(&q){return 0;}
    let n=parent.len();*t=q;commit(&parent);n
}

// Research-only independent structural certificate checker. It never calls
// alias_map, alias_root, alias_mono, toggle or the reducer. It consumes the
// original trace and the claimed committed result, with no solver verdict.
#[cfg(test)]
fn check_union_certificate(before:&Trace,after:&Trace,steps:&[UnionWitness],
    claimed:&AliasMap)->Result<(), &'static str>{
    use std::collections::{BTreeMap,BTreeSet};
    fn root(map:&BTreeMap<u32,u32>,mut v:u32)->Result<u32,&'static str>{
        while let Some(&p)=map.get(&v){
            if p>=v{return Err("nondecreasing parent");}
            v=p;
        }
        Ok(v)
    }
    if before.n!=after.n{return Err("input count");}
    if before.n>before.live.len()||(0..before.n).any(|v|u32::try_from(v).ok().map_or(true,|v|!before.live.contains(&v))){
        return Err("missing input");
    }
    if before.constraints.iter().flatten().chain(before.p.terms.keys()).flatten()
        .any(|v|!before.live.contains(v)){return Err("dangling original support");}
    let mut edges=BTreeSet::new();
    for row in &before.constraints{
        if row.len()==2&&row.iter().all(|m|m.len()==1){
            let mut ids=row.iter().map(|m|m[0]);
            let a=ids.next().unwrap();let b=ids.next().unwrap();
            edges.insert((a.min(b),a.max(b)));
        }
    }
    let mut map=BTreeMap::new();
    for s in steps{
        if ![s.x,s.y,s.child,s.par].iter().all(|v|before.live.contains(v)){
            return Err("nonlive link");
        }
        if s.x==s.y||!edges.contains(&(s.x.min(s.y),s.x.max(s.y))){return Err("source row");}
        if s.par>=s.child{return Err("nondecreasing parent");}
        if (s.child as usize)<before.n{return Err("input child");}
        if root(&map,s.x)?!=s.child||root(&map,s.y)?!=s.par{return Err("stale root");}
        if map.contains_key(&s.child)||map.contains_key(&s.par){return Err("nonterminal root");}
        map.insert(s.child,s.par);
    }
    if claimed.len()!=map.len()||map.iter().any(|(v,p)|claimed.get(v)!=Some(p)){
        return Err("parent map mismatch");
    }
    let live:BTreeSet<_>=before.live.iter().copied().filter(|v|!map.contains_key(v)).collect();
    if live!=after.live.iter().copied().collect(){return Err("live domain mismatch");}
    // Independently map every original row, cancel identical supports over F2,
    // and preserve row order. Only genuinely empty rows may be removed.
    let mut rows=Vec::new();
    for row in &before.constraints{
        let mut parity=BTreeSet::new();
        for mono in row{
            let mut support=BTreeSet::new();
            for &v in mono{support.insert(root(&map,v)?);}
            let m:Vec<_>=support.into_iter().collect();
            if !parity.insert(m.clone()){parity.remove(&m);}
        }
        if !parity.is_empty(){rows.push(parity);}
    }
    let actual:Vec<BTreeSet<Vec<u32>>>=after.constraints.iter().map(|q|q.iter().cloned().collect()).collect();
    if rows!=actual{return Err("ANF transport mismatch");}
    if after.p.terms.keys().flatten().any(|v|!after.live.contains(v)){return Err("dangling reduced phase");}
    // IMPORTANT: phase coefficients and normalization are NOT certified here.
    Ok(())
}

#[cfg(test)]
fn recorded_batch_alias(t:&mut Trace,fuel:usize)->(usize,Vec<UnionWitness>,Option<AliasMap>){
    let mut steps=Vec::new();let mut committed=None;
    let n=batch_alias_observe(t,fuel,|s|steps.push(s),|m|committed=Some(m.clone()));
    (n,steps,committed)
}

#[test]
fn exact_trace_union_certificate_negative_controls(){
    use quprs::rational::PhaseCoeff;
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    for _ in 0..4{ps.v.get_fresh_var();}
    let mut before=Trace::from_native(&ps).unwrap();
    // The final edge 3 -> 0 is not literally in the source rows.
    // The input-input equation implied by 1=3 and 0=2=3 remains.
    before.constraints=vec![
        [vec![0],vec![2]].into_iter().collect(),
        [vec![2],vec![3]].into_iter().collect(),
        [vec![1],vec![3]].into_iter().collect(),
        [vec![2],vec![4]].into_iter().collect(),
        [vec![2,4],vec![3],vec![5]].into_iter().collect(),
    ];
    before.p.add_term(vec![2,3],PhaseCoeff::HALF);
    let mut after=before.clone();
    let (n,steps,committed)=recorded_batch_alias(&mut after,64);
    assert_eq!(n,3);
    let parent=committed.unwrap();
    assert_eq!(check_union_certificate(&before,&after,&steps,&parent),Ok(()));
    let mut rejected=0;
    let reject=|b:&Trace,a:&Trace,s:&[UnionWitness],m:&AliasMap|{
        assert!(check_union_certificate(b,a,s,m).is_err());
    };
    let mut bad=steps.clone();bad[0].x=5;reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad[0].child=99;reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad[0].par=bad[0].child;reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad[0].child=1;bad[0].par=0;reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad[0].child=5;reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad.push(steps[0]);reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=steps.clone();bad.pop();reject(&before,&after,&bad,&parent);rejected+=1;
    let mut bad=parent.clone();bad.insert(5,0);reject(&before,&after,&steps,&bad);rejected+=1;
    let mut bad=after.clone();bad.live.remove(&0);reject(&before,&bad,&steps,&parent);rejected+=1;
    let mut bad=after.clone();bad.constraints.pop();reject(&before,&bad,&steps,&parent);rejected+=1;
    let mut bad=before.clone();bad.live.remove(&2);reject(&bad,&after,&steps,&parent);rejected+=1;
    let mut bad=after.clone();bad.n+=1;reject(&before,&bad,&steps,&parent);rejected+=1;
    let mut capped=before.clone();
    let (count,_,commit)=recorded_batch_alias(&mut capped,1);
    assert_eq!(count,0);assert!(commit.is_none());assert_eq!(before.cost(),capped.cost());
    println!("CRR_UNION_CERTIFICATE_NEGATIVE accepted=1 rejected={rejected} rejected_trial_uncommitted=1 phase_coefficients_certified=false");
}

// Free hidden variables contribute exactly 2 per variable, regardless
// of the remaining constraints. Preserve original input representatives.
fn batch_free(t:&mut Trace,fuel:usize)->usize{
    if t.empty()||fuel==0{return 0;}
    let mut used=PolyIds::default();
    for m in t.p.terms.keys().chain(t.constraints.iter().flatten()){
        used.extend(m.iter().copied());
    }
    let mut free:Vec<_>=t.live.iter().copied().filter(|&v|v as usize>=t.n&&!used.contains(&v)).collect();
    free.sort_unstable();free.truncate(fuel);
    for &v in &free{assert!(t.live.remove(&v));}
    free.len()
}
fn batch_then_iterate(t:&mut Trace)->(usize,usize,usize,usize,usize,usize,usize){
    let a=batch_alias(t,64);
    let f=batch_free(t,64-a);
    let (s,e,h,o,r)=iterate_policy(t,64-a-f,true);
    (a+s,f+e,h,o,r,a,f)
}
fn screen_accept(t:&Trace)->(bool,usize,usize,usize){
    let (aliases,before,after)=alias_screen(t);
    // Conservative heuristic, not a proof of no possible gain.
    // Keep at least 5% projected incidence gain and an actual alias.
    (aliases>0&&before>0&&after<before&&after.saturating_mul(100)<=before.saturating_mul(95),
     aliases,before,after)
}
// Exact dimension accounting for the CURRENT native encode_trace
// topology, not an alternative encoding and not a WMC result.
// All phase monomials introduce a literal; output ANF uses one
// auxiliary for constant/AND terms and one per XOR link. No sharing.
// The admitted PathSum contains all input and referenced variables.
fn trace_cnf_dimensions(ps:&PathSum)->(usize,usize){
    let mut vars=ps.v.path_vars.len()+ps.p.terms.len();
    let mut clauses:usize=ps.p.terms.keys().map(|m|m.len()+1).sum();
    for f in &ps.f.functions{
        clauses+=2; // equality to input
        if f.is_empty(){vars+=1;clauses+=1;continue;}
        for m in f{
            if m.len()!=1{vars+=1;clauses+=m.len()+1;}
        }
        let xor=f.len()-1;
        vars+=xor;clauses+=4*xor;
    }
    (vars,clauses)
}
// The cost comparison is exact for the locked encoder topology;
// verify the chosen header against actual serialization before use.
// Never materialize a placeholder or low precision solver problem.
fn lazy_prepare(ps:&PathSum)->(quprs::wmc::WmcManager,usize,usize,usize,usize,bool){
    let (av,ac)=trace_cnf_dimensions(ps);
    if let Some((p,m,o))=benchmark_candidate(ps,true){
        let (bv,bc)=trace_cnf_dimensions(&p);
        if bv<=av&&bc<=ac&&(bv<av||bc<ac){
            let (mgr,v,c)=route_encode(&p);
            assert_eq!((v,c),(bv,bc),"candidate dimension drift");
            return (mgr,v,c,m,o,true);
        }
    }
    let (mgr,v,c)=route_encode(ps);
    assert_eq!((v,c),(av,ac),"baseline dimension drift");
    (mgr,v,c,0,0,false)
}
fn route_profile(ps:&PathSum,case:&str){
    use std::time::{Instant,Duration};
    use num_bigint::BigInt;
    use num_traits::{Signed,ToPrimitive};
    let repeat=std::env::var("CRR_REPEAT").ok().map(|v|v.parse::<usize>().unwrap()).unwrap_or(0);
    let secs=std::env::var("CRR_SOLVER_SECS").ok().map(|v|v.parse::<u64>().unwrap()).unwrap_or(12);
    assert!((8..=180).contains(&secs));
    let twice=(2*ps.v.num_qubits+ps.v.path_vars.len()-ps.v.num_qubits) as i32;
    // Admit using the same restricted trace representation; do not
    // misreport an unsupported input as a successful no-op candidate.
    let Some(admitted)=Trace::from_native(ps)else{
        println!("CRR_TRACE case={case} status=unsupported");return;
    };
    if admitted.size()>TERM_CAP{
        println!("CRR_TRACE case={case} status=term_cap");return;
    }
    println!("CRR_TRACE case={case} status=profiled mode=routed");
    let run=|arm:&str|{
        let routed=arm!="baseline";
        let screened=arm=="screened"||arm=="batched";
        let batched=arm=="batched";
        let start=Instant::now();
        // Lazy arm uses the same pre-screen and batched candidate as
        // the eager arm, but only encodes the selected problem.
        if arm=="lazy"{
            let (av,ac)=trace_cnf_dimensions(ps);
            let (mgr,vars,clauses,mult,omega,chosen)=lazy_prepare(ps);
            let selected=if chosen{"conditioned"}else{"baseline"};
            let prepare=start.elapsed().as_secs_f64();
            println!("CRR_DISPATCH case={case} arm={arm} selected={selected} reason=dimension_gate vars={vars} clauses={clauses} baseline_vars={av} baseline_clauses={ac} prepare_s={prepare}");
            let begin=Instant::now();
            let result=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(begin+Duration::from_secs(secs)),90);
            let call=begin.elapsed().as_secs_f64();
            return match result{
                Ok(c)=>{
                    let (c,v)=restore_count(c,mult,omega,twice);
                    println!("CRR_ROUTED_CALL case={case} arm={arm} status=complete selected={selected} call_s={call} total_s={} real={} imag={} normalization_twice={twice}",start.elapsed().as_secs_f64(),c.real,c.imag);
                    Some((c,v))
                }
                Err(e)=>{
                    println!("CRR_ROUTED_CALL case={case} arm={arm} status=incomplete selected={selected} call_s={call} total_s={} error={e:#}",start.elapsed().as_secs_f64());None
                }
            };
        }
        let (mut mgr,av,ac)=route_encode(ps);
        let mut vars=av;let mut clauses=ac;let mut mult=0;let mut omega=0;
        let mut selected="baseline";let mut reason="baseline_control";
        let mut rejected=0;let mut subs=0;let mut elim=0;let mut hh=0;let mut o=0;
        let mut initial_cp=0;let mut final_cp=0;
        let mut batch_aliases=0;let mut batch_frees=0;
        if routed{
            let mut t=Trace::from_native(ps).expect("admitted");
            initial_cp=t.cost().0;
            let admitted=if screened{
                let (admit,aliases,before,after)=screen_accept(&t);
                println!("CRR_SCREEN case={case} arm={arm} admit={admit} aliases={aliases} phase_before={before} projected_phase={after}");
                admit
            }else{true};
            // Skip reduction when there is no internal pivot or
            // integrator. Otherwise all actual trial cost is timed.
            if t.live.len()==t.n{
                reason="no_hidden";final_cp=initial_cp;
            }else if !admitted{
                reason="early_screen_reject";final_cp=initial_cp;
            }else{
                if batched{
                    (subs,elim,hh,o,rejected,batch_aliases,batch_frees)=batch_then_iterate(&mut t);
                }else{
                    (subs,elim,hh,o,rejected)=iterate_policy(&mut t,64,true);
                }
                final_cp=t.cost().0;
                // A fixed, preregistered heuristic: require >=5%
                // phase incidence improvement before second encoding.
                // It is not an optimality or performance guarantee.
                if initial_cp==0||final_cp.saturating_mul(100)>initial_cp.saturating_mul(95)
                    ||final_cp==initial_cp{
                    reason="proxy_reject";
                }else{
                    let (candidate,bv,bc)=route_encode(&t.encoding_view(ps));
                    if bv<=av&&bc<=ac&&(bv<av||bc<ac){
                        mgr=candidate;vars=bv;clauses=bc;
                        mult=elim+hh;omega=o;selected="conditioned";reason="cnf_accept";
                    }else{reason="cnf_reject";}
                }
            }
        }
        let prepare=start.elapsed().as_secs_f64();
        println!("CRR_DISPATCH case={case} arm={arm} selected={selected} reason={reason} vars={vars} clauses={clauses} baseline_vars={av} baseline_clauses={ac} subs={subs} elim={elim} hh={hh} omega={o} rejected={rejected} phase_before={initial_cp} phase_after={final_cp} batch_aliases={batch_aliases} batch_frees={batch_frees} prepare_s={prepare}");
        let begin=Instant::now();
        let r=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(begin+Duration::from_secs(secs)),90);
        let call=begin.elapsed().as_secs_f64();
        match r{
            Ok(c)=>{
                let (c,v)=restore_count(c,mult,omega,twice);
                println!("CRR_ROUTED_CALL case={case} arm={arm} status=complete selected={selected} call_s={call} total_s={} real={} imag={} normalization_twice={twice}",start.elapsed().as_secs_f64(),c.real,c.imag);
                Some((c,v))
            }
            Err(e)=>{
                println!("CRR_ROUTED_CALL case={case} arm={arm} status=incomplete selected={selected} call_s={call} total_s={} error={e:#}",start.elapsed().as_secs_f64());
                None
            }
        }
    };
    let arms=["baseline","batched","lazy"];
    let mut counts:[Option<(Count,quprs::precision_count::PrintedVerdict)>;3]=[None,None,None];
    // Cyclic positions; for short cases 3 repeats cover each position.
    for k in 0..3{
        let idx=(repeat+k)%3;
        counts[idx]=run(arms[idx]);
    }
    let [a,b,c]=counts;
    let scale=Rat::from_integer(BigInt::from(1u8)<<(twice as usize/2));
    let bound=Rat::new(BigInt::from(1u8),BigInt::from(10u8).pow(50));
    let compare=|(x,vx):&(Count,quprs::precision_count::PrintedVerdict),(y,vy):&(Count,quprs::precision_count::PrintedVerdict)|{
        let delta=((&x.real-&y.real).abs()+(&x.imag-&y.imag).abs())/&scale;
        assert!(delta<=bound,"dispatch count mismatch {case}");
        assert!(std::mem::discriminant(vx)==std::mem::discriminant(vy));
        delta.to_f64().unwrap_or(f64::INFINITY)
    };
    if let (Some(b),Some(c))=(&b,&c){
        println!("CRR_LAZY_PAIR case={case} status=matched normalized_l1_delta={:.5e}",compare(b,c));
    }else{println!("CRR_LAZY_PAIR case={case} status=incomplete");}
    let (Some(a),Some(b),Some(c))=(a,b,c)else{
        println!("CRR_COMPARE case={case} status=incomplete");return;
    };
    let d=compare(&a,&b).max(compare(&a,&c));
    println!("CRR_COMPARE case={case} status=matched normalized_l1_delta={d:.5e} distance_midpoint_match=true");
}

#[test]
fn gpmc_trace_witness(){
    use quprs::rational::{PhaseCoeff,Rational};
    use quprs::precision_count::PrintedVerdict;
    use num_bigint::BigInt;
    use num_traits::Signed;
    use std::time::{Instant,Duration};
    // Explicit invocation after pinned solver provision. Failure,
    // including timeout, is a hard failure for these tiny witnesses.
    assert!(std::env::var_os("QUPRS_GPMC_PATH").is_some());
    for (name,quarter,global,er,ei,eq,expected_omega) in [
        ("hh_identity",false,false,4i64,0i64,true,0usize),
        ("hh_global_minus",false,true,-4,0,true,0),
        ("hsh_neq_odd_omega",true,false,2,2,false,1),
    ]{
        // H (S or I) H on one qubit, path variables y,z;
        // f=z, p=(x*y+y*z)/2 + y/4 [S] +1/2 [global].
        // Diagonal z=x cancels both half terms. Independently known
        // raw trace is 4, -4 or 2+2i; norm is 4 (twice log2 =4).
        let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
        let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
        ps.f.functions[0].clear();ps.f.functions[0].insert(vec![z]);
        ps.p.add_term(vec![0,y],PhaseCoeff::HALF);
        ps.p.add_term(vec![y,z],PhaseCoeff::HALF);
        if quarter{ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,4)));}
        if global{ps.p.add_term(vec![],PhaseCoeff::HALF);}
        let mut t=Trace::from_native(&ps).unwrap();
        // Deliberately unguarded: must exercise odd omega even if a
        // cost policy would reject a small fixture.
        let (_,e,h,o,_)=iterate_policy(&mut t,64,false);
        assert_eq!(o,expected_omega);
        let candidate=t.encoding_view(&ps);
        for (arm,p,m,o) in [("baseline",&ps,0,0),("iterated",&candidate,e+h,o)]{
            let (mgr,_,_)=route_encode(p);
            let c=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(Instant::now()+Duration::from_secs(8)),90).expect("witness solve");
            let (c,v)=restore_count(c,m,o,4);
            let err=(c.real-Rat::from_integer(BigInt::from(er))).abs()+(c.imag-Rat::from_integer(BigInt::from(ei))).abs();
            assert!(err<=Rat::new(BigInt::from(1u8),BigInt::from(10u8).pow(50)));
            // Compare discriminants using explicit expected classification.
            let wanted=if eq{PrintedVerdict::Equivalent}else{PrintedVerdict::NotEquivalent};
            assert!(std::mem::discriminant(&v)==std::mem::discriminant(&wanted));
            println!("CRR_WITNESS case={name} arm={arm} expected_real={er} expected_imag={ei} expected_eq={eq} omega={o} status=matched");
        }
    }
}


#[test]
fn exact_trace_alias_screen_controls(){
    use quprs::rational::PhaseCoeff;
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();
    let z=ps.v.get_fresh_var();
    // y=x0, z=x1: support coalescence after diagonal conditioning.
    ps.f.functions[0].clear();ps.f.functions[0].insert(vec![y]);
    ps.f.functions[1].clear();ps.f.functions[1].insert(vec![z]);
    ps.p.add_term(vec![0,z],PhaseCoeff::HALF);
    ps.p.add_term(vec![y,1],PhaseCoeff::HALF);
    let t=Trace::from_native(&ps).unwrap();
    let (admit,aliases,before,after)=screen_accept(&t);
    assert!(admit&&aliases==2&&after<before);
    // No pair equation: this heuristic declines, not a semantic verdict.
    ps.f.functions[0].clear();ps.f.functions[0].insert(vec![0,y]);
    ps.f.functions[1].clear();ps.f.functions[1].insert(vec![1,z]);
    let t=Trace::from_native(&ps).unwrap();
    assert!(!screen_accept(&t).0);
    // Input-input equality must not be folded by the screen.
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    ps.f.functions[0].clear();ps.f.functions[0].insert(vec![1]);
    ps.p.add_term(vec![0,1],PhaseCoeff::HALF);
    let t=Trace::from_native(&ps).unwrap();
    assert_eq!(alias_screen(&t).0,0);
    println!("CRR_SCREEN_ORACLE coalescence=1 nonalias_reject=1 input_input_reject=1");
}


#[test]
fn exact_trace_batched_alias_forest(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut seed=123u64;
    let mut next=||{seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);seed>>32};
    let mut aliases=0;let mut checks=0;let mut free_count=0;
    for k in 0..512{
        let mut ps=PathSum::new(3);ps.rr_tolerance=0.0;
        for _ in 0..5{ps.v.get_fresh_var();}
        // y3=x0; y4=y3; and either y4=x1 (retained input
        // equality) or y5=y4. y6 may appear in nonalias phase;
        // y7 is initially free. Constraints are built as trace
        // rows and then round-tripped through the encoder view.
        let mut orig=Trace::from_native(&ps).unwrap();
        orig.constraints=vec![
            [vec![0],vec![3]].into_iter().collect(),
            [vec![3],vec![4]].into_iter().collect(),
            if k%2==0{[vec![4],vec![1]].into_iter().collect()}
            else{[vec![4],vec![5]].into_iter().collect()}
        ];
        for mask in 0u32..128{
            let m:Vec<_>=(0..7).filter(|i|mask>>i&1!=0).collect();
            if next()%9==0{orig.p.add_term(m,PhaseCoeff::new_constant(Rational::new((next()%8) as i64,8)));}
        }
        let mut q=orig.clone();
        let (n,steps,cert)=recorded_batch_alias(&mut q,64);assert_eq!(n,if k%2==0{2}else{3});
        assert_eq!(check_union_certificate(&orig,&q,&steps,&cert.unwrap()),Ok(()));
        aliases+=n;
        assert!((0..3).all(|x|q.live.contains(&x)));
        let f=batch_free(&mut q,64-n);assert!(f>=1);free_count+=f;
        let round=Trace::from_native(&q.encoding_view(&ps)).unwrap();
        for x in 0..8{
            let h=hist(&q,x).map(|v|v*(1u32<<f));
            assert_eq!(hist(&orig,x),h);
            assert_eq!(hist(&q,x),hist(&round,x));
            checks+=1;
        }
        let mut capped=orig.clone();
        assert_eq!(batch_alias(&mut capped,1),0);
        assert_eq!(capped.cost(),orig.cost());
    }
    // Cycle + nonlinear equation: no removal of a second input,
    // and every residual row is mapped with F2 cancellation.
    let mut ps=PathSum::new(4);ps.rr_tolerance=0.0;
    for _ in 0..3{ps.v.get_fresh_var();}
    let mut orig=Trace::from_native(&ps).unwrap();
    orig.constraints=vec![
        [vec![4],vec![5]].into_iter().collect(),
        [vec![5],vec![6]].into_iter().collect(),
        [vec![4],vec![6]].into_iter().collect(),
        [vec![0,4],vec![0,5],vec![1]].into_iter().collect()
    ];
    orig.p.add_term(vec![4,6],PhaseCoeff::HALF);
    let mut q=orig.clone();let (n,steps,cert)=recorded_batch_alias(&mut q,64);assert_eq!(n,2);
    assert_eq!(check_union_certificate(&orig,&q,&steps,&cert.unwrap()),Ok(()));
    assert_eq!(q.constraints.len(),1);
    assert!(q.constraints[0].contains(&vec![1]));
    for x in 0..16{assert_eq!(hist(&orig,x),hist(&q,x));checks+=1;}
    println!("CRR_BATCH_ORACLE models=513 histogram_checks={checks} alias_eliminations={aliases} free_eliminations={free_count} cycle_control=1 union_certificate_checks=513");
}


// CodSpeed-only entry points. The benchmark crate includes this same
// research module, so the measured reducer is not a copied algorithm.
// Fixture construction and native RR are outside the measured window.
#[allow(dead_code)]
pub(super) fn benchmark_candidate(ps:&PathSum,batched:bool)->Option<(PathSum,usize,usize)>{
    let mut t=Trace::from_native(ps)?;
    if t.size()>TERM_CAP||t.live.len()==t.n||!screen_accept(&t).0{return None;}
    let before=t.cost().0;
    let (e,h,o)=if batched{
        let (_,e,h,o,_,_,_)=batch_then_iterate(&mut t);(e,h,o)
    }else{
        let (_,e,h,o,_)=iterate_policy(&mut t,64,true);(e,h,o)
    };
    let after=t.cost().0;
    if before==0||after==before||after.saturating_mul(100)>before.saturating_mul(95){return None;}
    Some((t.encoding_view(ps),e+h,o))
}
#[allow(dead_code)]
pub(super) fn benchmark_prepare(ps:&PathSum,variant:usize)->(quprs::wmc::WmcManager,usize,usize,usize,usize,bool){
    assert!(variant<=3);
    if variant==3{return lazy_prepare(ps);}
    let (baseline,av,ac)=route_encode(ps);
    if variant!=0{
        if let Some((p,m,o))=benchmark_candidate(ps,variant==2){
            let (candidate,bv,bc)=route_encode(&p);
            if bv<=av&&bc<=ac&&(bv<av||bc<ac){return (candidate,bv,bc,m,o,true);}
        }
    }
    (baseline,av,ac,0,0,false)
}


#[test]
fn exact_trace_cnf_dimensions(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut seed=73u64;
    let mut next=||{seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);seed>>32};
    let mut checks=0;
    for k in 0..128{
        let mut ps=PathSum::new(3);ps.rr_tolerance=0.0;
        for _ in 0..4{ps.v.get_fresh_var();}
        // Mix empty ANFs, constant and singleton output monomials,
        // arbitrary multi-AND/XOR, phase constant and free variables.
        for f in &mut ps.f.functions{f.clear();}
        for mask in 0u32..64{
            let m:Vec<_>=(0..6).filter(|i|mask>>i&1!=0).collect();
            if next()%11==0{ps.p.add_term(m.clone(),PhaseCoeff::new_constant(Rational::new((next()%7+1) as i64,8)));}
            for i in 0..3{if next()%13==0{ps.f.functions[i].insert(m.clone());}}
        }
        if k%4==0{ps.f.functions[0].clear();}
        if k%4==1{ps.f.functions[0].clear();ps.f.functions[0].insert(vec![]);}
        if k%4==2{ps.f.functions[0].clear();ps.f.functions[0].insert(vec![3]);}
        let (_,v,c)=route_encode(&ps);assert_eq!(trace_cnf_dimensions(&ps),(v,c));checks+=1;
        let mut t=Trace::from_native(&ps).unwrap();
        let _=batch_then_iterate(&mut t);
        let view=t.encoding_view(&ps);
        let (_,v,c)=route_encode(&view);assert_eq!(trace_cnf_dimensions(&view),(v,c));checks+=1;
        // Both routes must choose the same dimensions, multipliers
        // and fallback. The selected manager alone is fully weighted.
        let (_,a,b,m,o,z)=benchmark_prepare(&ps,2);
        let (_,x,y,n,p,w)=lazy_prepare(&ps);
        assert_eq!((a,b,m,o,z),(x,y,n,p,w));
    }
    println!("CRR_DIMENSION_ORACLE models=128 header_checks={checks} dispatch_checks=128");
}


// Full native release-build research pipeline, with native RR independently
// executed in each arm. Not the public Hybrid API: the post-RR numerical
// path uses the experiment's explicit 256-bit/90-digit precision.
#[test]
fn native_full_pipeline_paired(){
    use quprs::{check_equivalence_with_options,EquivalenceStatus,VerificationMethod,VerificationOptions};
    use quprs::qasm::parse_qasm_str;
    use quprs::precision_count::PrintedVerdict;
    use num_bigint::BigInt;
    use num_traits::{Signed,ToPrimitive};
    use std::time::{Instant,Duration};
    let case=std::env::var("CRR_CASE").expect("case");
    let source=std::env::var("CRR_SOURCE").expect("source");
    let target=std::env::var("CRR_TARGET").expect("target");
    let repeat=std::env::var("CRR_REPEAT").expect("repeat").parse::<usize>().unwrap();
    let secs=std::env::var("CRR_SOLVER_SECS").expect("solver deadline").parse::<u64>().unwrap();
    assert!((8..=60).contains(&secs));
    assert!(std::env::var_os("QUPRS_GPMC_PATH").is_some());
    let run=|lazy:bool|->Option<(String,Option<(Count,i32)>)>{
        let arm=if lazy{"lazy"}else{"baseline"};
        let start=Instant::now();
        let (a,n)=parse_qasm_str(&std::fs::read_to_string(&source).expect("source bytes")).expect("source parse");
        let (b,m)=parse_qasm_str(&std::fs::read_to_string(&target).expect("target bytes")).expect("target parse");
        assert_eq!(n,m);
        let parse=start.elapsed().as_secs_f64();
        let begin=Instant::now();
        let options=VerificationOptions{method:VerificationMethod::ReductionRules,
            rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
        let result=check_equivalence_with_options(n,&a,&b,&options).expect("native RR");
        assert!(!result.solver_invoked);
        let rr=begin.elapsed().as_secs_f64();
        let native=result.status.as_str();
        // An approximate or incomplete native result is not a decision.
        if result.rr_approximate||matches!(&result.status,EquivalenceStatus::Timeout|EquivalenceStatus::MemoryOut){
            println!("CRR_FULL_CALL case={case} arm={arm} status=incomplete native={native} reason=native_admission parse_s={parse} rr_s={rr} total_s={}",start.elapsed().as_secs_f64());
            return None;
        }
        if matches!(&result.status,EquivalenceStatus::Equivalent|EquivalenceStatus::EquivalentUpToGlobalPhase|EquivalenceStatus::NotEquivalent){
            let verdict=if matches!(&result.status,EquivalenceStatus::NotEquivalent){"NEQ"}else{"EQ"};
            println!("CRR_FULL_CALL case={case} arm={arm} status=complete native={native} selected=native_rr verdict={verdict} solver=false parse_s={parse} rr_s={rr} prepare_s=0 call_s=0 total_s={}",start.elapsed().as_secs_f64());
            return Some((verdict.to_string(),None));
        }
        let p=result.final_pathsum();
        let begin=Instant::now();
        if Trace::from_native(p).is_none()||p.p.terms.len()+p.f.functions.iter().map(|f|f.len()).sum::<usize>()>TERM_CAP{
            println!("CRR_FULL_CALL case={case} arm={arm} status=incomplete native={native} reason=residual_admission parse_s={parse} rr_s={rr} total_s={}",start.elapsed().as_secs_f64());
            return None;
        }
        let twice=(n+p.v.path_vars.len()) as i32;
        let (mgr,v,c,m,o,chosen)=if lazy{lazy_prepare(p)}else{
            let (mgr,v,c)=route_encode(p);(mgr,v,c,0,0,false)
        };
        let prepare=begin.elapsed().as_secs_f64();
        let selected=if chosen{"conditioned"}else{"baseline"};
        let begin=Instant::now();
        let count=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(begin+Duration::from_secs(secs)),90);
        let call=begin.elapsed().as_secs_f64();
        match count{
            Ok(raw)=>{
                let (raw,decision)=restore_count(raw,m,o,twice);
                let verdict=match decision{
                    PrintedVerdict::Equivalent=>"EQ",
                    PrintedVerdict::NotEquivalent=>"NEQ",
                    _=>"UNKNOWN",
                };
                println!("CRR_FULL_CALL case={case} arm={arm} status=complete native={native} selected={selected} verdict={verdict} solver=true vars={v} clauses={c} multiplier_power={m} omega={o} parse_s={parse} rr_s={rr} prepare_s={prepare} call_s={call} total_s={} normalization_twice={twice} real={} imag={}",start.elapsed().as_secs_f64(),raw.real,raw.imag);
                Some((verdict.to_string(),Some((raw,twice))))
            }
            Err(e)=>{
                println!("CRR_FULL_CALL case={case} arm={arm} status=incomplete native={native} selected={selected} solver=true parse_s={parse} rr_s={rr} prepare_s={prepare} call_s={call} total_s={} error={e:#}",start.elapsed().as_secs_f64());
                None
            }
        }
    };
    let (a,b)=if repeat%2==0{(run(false),run(true))}else{let b=run(true);(run(false),b)};
    let (Some((va,ca)),Some((vb,cb)))=(a,b)else{
        println!("CRR_FULL_COMPARE case={case} status=incomplete");return;
    };
    assert_eq!(va,vb,"full pipeline verdict mismatch {case}");
    match (ca,cb){
        (Some((a,na)),Some((b,nb)))=>{
            assert_eq!(na,nb,"original normalization drift");
            let scale=Rat::from_integer(BigInt::from(1u8)<<(na as usize/2));
            let delta=((&a.real-&b.real).abs()+(&a.imag-&b.imag).abs())/scale;
            assert!(delta<=Rat::new(BigInt::from(1u8),BigInt::from(10u8).pow(50)));
            println!("CRR_FULL_COMPARE case={case} status=matched verdict={va} scope=solver_count normalized_l1_delta={:.5e}",delta.to_f64().unwrap_or(f64::INFINITY));
        }
        (None,None)=>println!("CRR_FULL_COMPARE case={case} status=matched verdict={va} scope=native_rr"),
        _=>panic!("native RR dispatch differs across arms"),
    }
}


// Export untouched native RR residual, before any CRR transform.
// Diagnostic only: even native definite cases may be counted here.
// JSONL transport preserves exact rational coefficients.
#[test]
fn native_reference_export(){
    use quprs::{check_equivalence_with_options,EquivalenceStatus,VerificationMethod,VerificationOptions};
    use quprs::qasm::parse_qasm_str;
    use std::time::{Instant,Duration};
    let source=std::env::var("CRR_SOURCE").expect("source");
    let target=std::env::var("CRR_TARGET").expect("target");
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(source).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(target).unwrap()).unwrap();
    assert_eq!(n,m);
    let r=check_equivalence_with_options(n,&a,&b,&VerificationOptions{
        method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,
        ..VerificationOptions::default()
    }).expect("native RR");
    let p=r.final_pathsum();
    if r.rr_approximate||matches!(r.status,EquivalenceStatus::Timeout|EquivalenceStatus::MemoryOut)
        ||Trace::from_native(p).is_none()||p.p.terms.len()+p.f.functions.iter().map(|f|f.len()).sum::<usize>()>TERM_CAP{
        println!("CRR_REF_SKIP reason=native_admission");return;
    }
    let mut live:Vec<_>=p.v.path_vars.iter().copied().collect();live.sort_unstable();
    let twice=(n+live.len()) as i32;
    let mut phase:Vec<_>=p.p.terms.iter().collect();phase.sort_unstable_by(|(a,_),(b,_)|a.cmp(b));
    let terms:Vec<_>=phase.iter().map(|(m,c)|format!("[{:?},\"{}\",\"{}\"]",m,c.constant,c.radians.as_ref().map(|r|r.to_string()).unwrap_or_else(||"0".into()))).collect();
    let outputs:Vec<Vec<Vec<u32>>>=p.f.functions.iter().map(|f|{let mut v:Vec<_>=f.iter().cloned().collect();v.sort();v}).collect();
    println!("CRR_REF_IR {{\"n\":{n},\"twice\":{twice},\"native\":\"{}\",\"live\":{:?},\"phase\":[{}],\"outputs\":{:?}}}",r.status.as_str(),live,terms.join(","),outputs);
    let (mgr,v,c,m,o,chosen)=lazy_prepare(p);
    match mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(Instant::now()+Duration::from_secs(12)),90){
        Ok(raw)=>{
            let (raw,decision)=restore_count(raw,m,o,twice);
            println!("CRR_REF_SOLVER {{\"status\":\"complete\",\"real\":\"{}\",\"imag\":\"{}\",\"verdict\":\"{:?}\",\"selected\":{},\"vars\":{v},\"clauses\":{c}}}",raw.real,raw.imag,decision,chosen);
        }
        Err(_)=>println!("CRR_REF_SOLVER {{\"status\":\"incomplete\"}}"),
    }
}
