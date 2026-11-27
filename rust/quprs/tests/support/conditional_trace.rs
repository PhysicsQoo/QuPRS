//! Trace-only exact constraint substitution pilot. No EQ verdict.
use quprs::{PathSum,PhaseCoeff,pathsum::{PhasePolynomial,Monomial}};
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
// Research observer: no-op callback on ordinary experimental path.
#[derive(Clone,Copy,Debug)]
enum IterWitness{Sub{y:u32,row:usize},Free{y:u32},Hh{y:u32},Omega{y:u32}}
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
        self.step_policy_observe(guarded,rejected,|_,_,_,_|{})
    }
    fn step_policy_observe(&mut self,guarded:bool,rejected:&mut usize,
        mut emit:impl FnMut(IterWitness,&Trace,&Trace,bool))->Option<(u32,usize)>{
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
            let witness=IterWitness::Sub{y,row:i};
            if guarded&&!self.accepts(&trial){*rejected+=1;emit(witness,self,&trial,false);continue;}
            emit(witness,self,&trial,true);
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
    iterate_policy_observe(t,fuel,guarded,|_,_,_,_|{})
}
fn iterate_policy_observe(t:&mut Trace,fuel:usize,guarded:bool,
    mut emit:impl FnMut(IterWitness,&Trace,&Trace,bool))->(usize,usize,usize,usize,usize){
    assert!(fuel<=64);
    let (mut subs,mut elim,mut hh,mut omega,mut rejected)=(0,0,0,0,0);
    for _ in 0..fuel{
        if t.step_policy_observe(guarded,&mut rejected,&mut emit).is_some(){subs+=1;continue;}
        let mut q=t.clone();
        if let Some((rule,y))=q.integrate(){
            let witness=match rule{"elim"=>IterWitness::Free{y},"hh"=>IterWitness::Hh{y},_=>unreachable!()};
            if !guarded||t.accepts(&q){
                match rule{"elim"=>elim+=1,"hh"=>hh+=1,_=>unreachable!()}
                emit(witness,t,&q,true);*t=q;continue;
            }
            emit(witness,t,&q,false);rejected+=1;
        }
        let mut q=t.clone();
        if let Some(y)=q.omega(){
            let witness=IterWitness::Omega{y};
            if !guarded||t.accepts(&q){omega+=1;emit(witness,t,&q,true);*t=q;continue;}
            emit(witness,t,&q,false);rejected+=1;
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
        for _ in 0..STEP_CAP{
            let b=t.clone();
            let Some((y,len))=t.step()else{break;};
            assert!(check_observed_substitution(&b,&t,y,len));
            steps+=1;
        }
        let view=t.encoding_view(&ps);
        let roundtrip=Trace::from_native(&view).unwrap();
        for x in 0..4{assert_eq!(hist(&original,x),hist(&t,x));assert_eq!(hist(&t,x),hist(&roundtrip,x));checks+=1;}
    }
    assert!(steps>0);
    println!("CRR_TRACE_ORACLE models=512 input_hist_checks={checks} substitutions={steps} independent_substitution_checks={steps}");
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
        let (mut elim,mut hh)=(0,0);
        for _ in 0..STEP_CAP{
            let b=t.clone();
            if let Some((y,len))=t.step(){assert!(check_observed_substitution(&b,&t,y,len));continue;}
            match t.integrate(){
                Some(("elim",_))=>{check_free_elim(&b,&t,1,0).unwrap();elim+=1;},
                Some(("hh",y))=>{check_hh(&b,&t,y,1,0).unwrap();hh+=1;},
                None=>break,
                _=>unreachable!(),
            }
        }
        total_elim+=elim;total_hh+=hh;
        let round=Trace::from_native(&t.encoding_view(&ps)).unwrap();
        for x in 0..4{
            assert_eq!(coeff(&orig,x,0),coeff(&t,x,elim+hh));
            assert_eq!(coeff(&t,x,elim+hh),coeff(&round,x,elim+hh));
            checks+=1;
        }
    }
    assert!(total_elim>=512&&total_hh>0);
    println!("CRR_ITERATE_ORACLE models=512 checks={checks} elim={total_elim} hh={total_hh} independent_hh_checks={total_hh} independent_free_checks={total_elim}");
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
        let (mut subs,mut e,mut h,mut o)=(0,0,0,0);
        for _ in 0..STEP_CAP{
            let b=t.clone();
            if let Some((y,len))=t.step(){assert!(check_observed_substitution(&b,&t,y,len));subs+=1;continue;}
            match t.integrate(){
                Some(("elim",_))=>{check_free_elim(&b,&t,1,0).unwrap();e+=1;continue;},
                Some(("hh",y))=>{check_hh(&b,&t,y,1,0).unwrap();h+=1;continue;},
                None=>{},
                _=>unreachable!(),
            }
            if let Some(y)=t.omega(){check_omega(&b,&t,y,0,1).unwrap();o+=1;continue;}
            break;
        }
        // Preserve parity against the original unguarded policy, not
        // just the independently replayed local sequence.
        let mut reference=orig.clone();
        assert_eq!(iterate_all(&mut reference),(subs,e,h,o));
        assert_eq!(reference.live,t.live);
        assert_eq!(reference.p.terms,t.p.terms);
        assert_eq!(reference.constraints,t.constraints);
        let mut guarded=orig.clone();
        let (_,ge,gh,go,_)=iterate_policy(&mut guarded,64,true);
        assert!(guarded.cost().0<=orig.cost().0&&guarded.cost().1<=orig.cost().1);
        for x in 0..4{assert_eq!(coeff(&orig,x,0,0),coeff(&guarded,x,ge+gh,go));}
        let (ledger_end,ledger,counts)=record_guarded_ledger(&orig);
        let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
        let k=2*(counts.1+counts.2)+counts.3;
        check_ordered_ledger(&ps,&orig,&ledger_end,&ledger,twice,counts,k).unwrap();
        let mut native=orig.clone();
        assert_eq!(batch_then_iterate(&mut native),counts);
        assert!(same_trace(&native,&ledger_end));
        for x in 0..4{assert_eq!(coeff(&orig,x,0,0),coeff(&ledger_end,x,counts.1+counts.2,counts.3));}
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
    println!("CRR_OMEGA_ORACLE models=512 checks={checks} omega={total_omega} odd_models={odd} even_models={even} independent_omega_checks={total_omega} policy_parity_models=512 guarded_batch_ledger_models=512");
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
pub(super) fn restore_count(mut c:Count,m:usize,o:usize,twice:i32)->(Count,quprs::precision_count::PrintedVerdict){
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
pub(super) fn route_encode(ps:&PathSum)->(quprs::wmc::WmcManager,usize,usize){
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
    // Independently reconstruct exact phase coefficients. Keep the
    // rational turns (modulo 1) separate from the rational radian part.
    // In particular, do not use Rational::add or PhasePolynomial::add_term:
    // native fixed-width arithmetic can approximate after a denominator cap.
    use num_bigint::BigInt;
    use num_integer::Integer;
    use num_rational::BigRational;
    use num_traits::Zero;
    type ExactCoeff=(BigRational,BigRational);
    fn mod_one(q:BigRational)->BigRational{
        BigRational::new(q.numer().mod_floor(q.denom()),q.denom().clone())
    }
    fn exact(c:&quprs::rational::PhaseCoeff)->Result<ExactCoeff,&'static str>{
        if !c.symbols.is_empty(){return Err("unsupported symbolic phase");}
        let r=c.constant;
        if r.denom<=0||r.numer<0||r.numer>=r.denom{return Err("noncanonical phase fraction");}
        let turns=BigRational::new(BigInt::from(r.numer),BigInt::from(r.denom));
        if turns.numer()!=&BigInt::from(r.numer)||turns.denom()!=&BigInt::from(r.denom){
            return Err("noncanonical phase fraction");
        }
        if c.radians.as_ref().is_some_and(|r|r.is_zero()){return Err("noncanonical zero radians");}
        Ok((turns,c.radians.clone().unwrap_or_else(BigRational::zero)))
    }
    let mut expected:BTreeMap<Vec<u32>,ExactCoeff>=BTreeMap::new();
    for (mono,c) in &before.p.terms{
        let mut support=BTreeSet::new();
        for &v in mono{support.insert(root(&map,v)?);}
        let key:Vec<_>=support.into_iter().collect();
        let (turns,rad)=exact(c)?;
        let e=expected.entry(key).or_insert_with(||(BigRational::zero(),BigRational::zero()));
        e.0=mod_one(e.0.clone()+turns);e.1+=rad;
    }
    expected.retain(|_,(turns,rad)|!turns.is_zero()||!rad.is_zero());
    let mut actual=BTreeMap::new();
    for (mono,c) in &after.p.terms{
        let coeff=exact(c)?;
        if coeff.0.is_zero()&&coeff.1.is_zero(){return Err("noncanonical zero phase term");}
        actual.insert(mono.clone(),coeff);
    }
    // A capped or otherwise inaccurate native result cannot pass this check,
    // even when the reducer did not set an approximate flag.
    if expected!=actual{return Err("exact phase transport mismatch");}
    // Original-source phase provenance and normalization are NOT certified.
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
    // The final edge 4 -> 0 is not literally in the source rows.
    // The input-input equation implied by 1=3=2=0 remains.
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
    println!("CRR_UNION_CERTIFICATE_NEGATIVE accepted=1 rejected={rejected} rejected_trial_uncommitted=1 phase_coefficients_certified=true");
}


#[test]
fn exact_trace_union_phase_certificate(){
    use quprs::rational::{PhaseCoeff,Rational,FreeRational};
    use num_bigint::BigInt;
    use num_rational::BigRational;
    let rad=BigRational::new(BigInt::from(7),BigInt::from(19));
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    for _ in 0..3{ps.v.get_fresh_var();}
    let mut before=Trace::from_native(&ps).unwrap();
    before.constraints=vec![[vec![0],vec![1]].into_iter().collect(),
        [vec![0],vec![2]].into_iter().collect()];
    let mut a=PhaseCoeff::new_constant(Rational::new(1,3));a.radians=Some(rad.clone());
    let mut b=PhaseCoeff::new_constant(Rational::new(2,3));b.radians=Some(-rad.clone());
    before.p.add_term(vec![1],a);
    before.p.add_term(vec![2],b);
    let mut c=PhaseCoeff::QUARTER;c.radians=Some(rad.clone());
    before.p.add_term(vec![1,3],c);
    before.p.add_term(vec![2,3],PhaseCoeff::HALF);
    let mut after=before.clone();
    let (n,steps,cert)=recorded_batch_alias(&mut after,64);assert_eq!(n,2);
    let cert=cert.unwrap();
    assert_eq!(check_union_certificate(&before,&after,&steps,&cert),Ok(()));
    assert!(!after.p.terms.contains_key(&vec![0]));
    let key=vec![0,3];
    assert_eq!(after.p.terms[&key].constant,Rational::THREE_QUARTERS);
    assert_eq!(after.p.terms[&key].radians,Some(rad));
    let mut bad=after.clone();bad.p.terms.get_mut(&key).unwrap().constant=Rational::HALF;
    assert_eq!(check_union_certificate(&before,&bad,&steps,&cert),Err("exact phase transport mismatch"));
    let mut bad=after.clone();bad.p.terms.get_mut(&key).unwrap().radians=None;
    assert_eq!(check_union_certificate(&before,&bad,&steps,&cert),Err("exact phase transport mismatch"));
    let mut bad=after.clone();bad.p.terms.remove(&key);
    assert_eq!(check_union_certificate(&before,&bad,&steps,&cert),Err("exact phase transport mismatch"));
    let mut bad=after.clone();bad.p.add_term(vec![3],PhaseCoeff::HALF);
    assert_eq!(check_union_certificate(&before,&bad,&steps,&cert),Err("exact phase transport mismatch"));
    let mut bad=before.clone();bad.p.terms.get_mut(&vec![1]).unwrap().symbols.insert(0,FreeRational::HALF);
    assert_eq!(check_union_certificate(&bad,&after,&steps,&cert),Err("unsupported symbolic phase"));
    let mut bad=after.clone();bad.p.terms.get_mut(&key).unwrap().constant=Rational{numer:2,denom:4};
    assert_eq!(check_union_certificate(&before,&bad,&steps,&cert),Err("noncanonical phase fraction"));

    // These coprime denominators yield an exact reduced denominator
    // larger than i64::MAX, so no native Rational can encode the sum.
    let mut capped=before.clone();capped.p=PhasePolynomial::new();
    capped.p.add_term(vec![1],PhaseCoeff::new_constant(Rational::new(1,4_000_000_007)));
    capped.p.add_term(vec![2],PhaseCoeff::new_constant(Rational::new(1,4_000_000_009)));
    let mut candidate=capped.clone();
    let (n,s,m)=recorded_batch_alias(&mut candidate,64);assert_eq!(n,2);
    assert_eq!(check_union_certificate(&capped,&candidate,&s,&m.unwrap()),Err("exact phase transport mismatch"));
    println!("CRR_UNION_PHASE_CERTIFICATE mixed_positive=1 rejected_mutations=6 rejected_native_cap=1 normalization_certified=false");
}

// Alias-only normalization certificate, relative to the represented native
// post-RR residual. Do not derive its exponent from the encoder adapter:
// diagonal conditioning removes a uniquely determined variable, not a
// Hadamard normalization factor. No Elim/HH/omega or source-QASM claim.
#[cfg(test)]
fn check_residual_normalization(original:&PathSum,before:&Trace,twice:i32)
    ->Result<(), &'static str>{
    use std::collections::BTreeSet;
    let n=original.v.num_qubits;
    if original.rr_approximate||original.rr_tolerance!=0.0||!original.v.continuous_vars.is_empty(){
        return Err("residual admission");
    }
    if n!=before.n||original.v.path_vars!=before.live||original.p.terms!=before.p.terms
        ||original.f.functions.len()!=n{return Err("residual binding");}
    // Reconstruct diagonal equations independently, retaining empty source
    // rows here (the subsequent union certificate may delete them).
    for (i,row) in original.f.functions.iter().enumerate(){
        let mut q:BTreeSet<_>=row.iter().cloned().collect();
        let x=vec![u32::try_from(i).map_err(|_|"input index overflow")?];
        if !q.insert(x.clone()){q.remove(&x);}
        if before.constraints.get(i).map(|r|r.iter().cloned().collect::<BTreeSet<_>>())!=Some(q){
            return Err("residual diagonal binding");
        }
    }
    if before.constraints.len()!=n{return Err("residual diagonal binding");}
    let hidden=before.live.len().checked_sub(n).ok_or("hidden underflow")?;
    let expected=n.checked_mul(2).and_then(|v|v.checked_add(hidden))
        .and_then(|v|i32::try_from(v).ok()).ok_or("normalization overflow")?;
    if twice!=expected{return Err("original normalization mismatch");}
    Ok(())
}
#[cfg(test)]
fn check_alias_normalization(original:&PathSum,before:&Trace,after:&Trace,
    steps:&[UnionWitness],claimed:&AliasMap,twice:i32,m:usize,o:usize)
    ->Result<(), &'static str>{
    check_residual_normalization(original,before,twice)?;
    check_union_certificate(before,after,steps,claimed)?;
    if m!=0||o!=0{return Err("alias multiplier must be one");}
    // Independent cardinality check: every committed link removes exactly
    // one hidden variable, with unique extension supplied by union replay.
    if before.live.len().checked_sub(after.live.len())!=Some(claimed.len()){
        return Err("alias cardinality mismatch");
    }
    Ok(())
}

#[test]
fn exact_trace_alias_normalization_certificate(){
    use quprs::rational::PhaseCoeff;
    // H H residual on one qubit: y,z are two hidden variables.
    // Conditioning z=x eliminates one variable with multiplicity one.
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    ps.f.functions[0].clear();ps.f.functions[0].insert(vec![z]);
    ps.p.add_term(vec![0,y],PhaseCoeff::HALF);
    ps.p.add_term(vec![y,z],PhaseCoeff::HALF);
    let before=Trace::from_native(&ps).unwrap();
    let mut after=before.clone();
    let (n,steps,cert)=recorded_batch_alias(&mut after,64);assert_eq!(n,1);
    let cert=cert.unwrap();
    let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
    assert_eq!(twice,4);
    assert_eq!(check_alias_normalization(&ps,&before,&after,&steps,&cert,twice,0,0),Ok(()));
    let adapter=after.encoding_view(&ps);
    let wrong=(adapter.v.num_qubits+adapter.v.path_vars.len()) as i32;
    assert_eq!(wrong,3);
    assert_eq!(check_alias_normalization(&ps,&before,&after,&steps,&cert,wrong,0,0),
        Err("original normalization mismatch"));
    assert_eq!(check_alias_normalization(&ps,&before,&after,&steps,&cert,twice+1,0,0),
        Err("original normalization mismatch"));
    assert_eq!(check_alias_normalization(&ps,&before,&after,&steps,&cert,twice,1,0),
        Err("alias multiplier must be one"));
    assert_eq!(check_alias_normalization(&ps,&before,&after,&steps,&cert,twice,0,1),
        Err("alias multiplier must be one"));
    let mut bad=ps.clone();bad.p.add_term(vec![],PhaseCoeff::HALF);
    assert_eq!(check_alias_normalization(&bad,&before,&after,&steps,&cert,twice,0,0),
        Err("residual binding"));
    let mut bad=ps.clone();bad.f.functions[0].clear();bad.f.functions[0].insert(vec![y]);
    assert_eq!(check_alias_normalization(&bad,&before,&after,&steps,&cert,twice,0,0),
        Err("residual diagonal binding"));
    let mut bad=ps.clone();bad.v.get_fresh_var();
    assert_eq!(check_alias_normalization(&bad,&before,&after,&steps,&cert,twice,0,0),
        Err("residual binding"));
    let mut bad=ps.clone();bad.rr_tolerance=1e-8;
    assert_eq!(check_alias_normalization(&bad,&before,&after,&steps,&cert,twice,0,0),
        Err("residual admission"));
    // Unnormalized trace equals 4, not 4 times an extra sqrt(2).
    for x in 0..2{assert_eq!(hist(&before,x),hist(&after,x));}
    println!("CRR_ALIAS_NORMALIZATION_CERTIFICATE positive=1 rejected=8 original_twice=4 adapter_twice=3 alias_multiplier=1 source_qasm_certified=false integration_certified=false");
}

// Independent substitution transport: GF(2) for constraints, integer
// Boolean-function expansion for exact phase coefficients. No native
// substitution, phase addition, toggle, or reducer helper is used.
#[cfg(test)]
type ExactPair=(Rat,Rat);
#[cfg(test)]
fn exact_pair(c:&quprs::rational::PhaseCoeff)->Result<ExactPair,&'static str>{
    use num_bigint::BigInt;
    use num_traits::Zero;
    if !c.symbols.is_empty(){return Err("unsupported symbolic phase");}
    let r=c.constant;
    if r.denom<=0||r.numer<0||r.numer>=r.denom{return Err("noncanonical phase fraction");}
    let t=Rat::new(BigInt::from(r.numer),BigInt::from(r.denom));
    if t.numer()!=&BigInt::from(r.numer)||t.denom()!=&BigInt::from(r.denom){
        return Err("noncanonical phase fraction");
    }
    if c.radians.as_ref().is_some_and(|v|v.is_zero()){return Err("noncanonical zero radians");}
    let r=c.radians.clone().unwrap_or_else(Rat::zero);
    if t.is_zero()&&r.is_zero(){return Err("noncanonical zero phase term");}
    Ok((t,r))
}
#[cfg(test)]
fn check_substitution_transport(before:&Trace,after:&Trace,y:u32,
    rhs:&std::collections::BTreeSet<Vec<u32>>,skip:Option<usize>)
    ->Result<(), &'static str>{
    use std::collections::{BTreeMap,BTreeSet};
    use num_bigint::BigInt;
    use num_integer::Integer;
    use num_traits::Zero;
    if before.n!=after.n||(y as usize)<before.n||!before.live.contains(&y){
        return Err("invalid substitution variable");
    }
    if (0..before.n).any(|i|u32::try_from(i).ok().map_or(true,|v|!before.live.contains(&v))){
        return Err("missing input");
    }
    let live:BTreeSet<_>=before.live.iter().copied().filter(|&v|v!=y).collect();
    if live!=after.live.iter().copied().collect(){return Err("substitution domain mismatch");}
    let valid=|m:&Vec<u32>|m.windows(2).all(|w|w[0]<w[1])&&m.iter().all(|v|before.live.contains(v));
    if before.p.terms.keys().chain(before.constraints.iter().flatten()).any(|m|!valid(m)){
        return Err("invalid original support");
    }
    if rhs.iter().any(|m|!valid(m)||m.contains(&y)){return Err("invalid replacement support");}
    if rhs.len()>8||before.size()>4096{return Err("certificate expansion cap");}
    fn join(a:&[u32],b:&[u32])->Vec<u32>{
        a.iter().chain(b).copied().collect::<BTreeSet<_>>().into_iter().collect()
    }
    fn parity(p:&mut BTreeSet<Vec<u32>>,m:Vec<u32>){
        if !p.insert(m.clone()){p.remove(&m);}
    }
    // Iterative arithmetic XOR: A xor B = A+B-2AB.
    // With <=8 RHS terms, sum of absolute integer coefficients is
    // bounded by (3^8-1)/2, so i64 is exact even after support merging.
    let mut arithmetic:BTreeMap<Vec<u32>,i64>=BTreeMap::new();
    for mono in rhs{
        let prior=arithmetic.clone();
        *arithmetic.entry(mono.clone()).or_default()+=1;
        for (part,k) in prior{
            *arithmetic.entry(join(&part,mono)).or_default()-=2*k;
        }
        arithmetic.retain(|_,v|*v!=0);
    }
    let mut expected:BTreeMap<Vec<u32>,ExactPair>=BTreeMap::new();
    let mut add=|key:Vec<u32>,c:&ExactPair,k:i64|{
        let scale=Rat::from_integer(BigInt::from(k));
        let e=expected.entry(key).or_insert_with(||(Rat::zero(),Rat::zero()));
        e.0+=&c.0*&scale;e.1+=&c.1*&scale;
        e.0=Rat::new(e.0.numer().mod_floor(e.0.denom()),e.0.denom().clone());
    };
    for (mono,c) in &before.p.terms{
        let c=exact_pair(c)?;
        if mono.contains(&y){
            let rest:Vec<_>=mono.iter().copied().filter(|&v|v!=y).collect();
            for (part,&k) in &arithmetic{add(join(&rest,part),&c,k);}
        }else{add(mono.clone(),&c,1);}
    }
    expected.retain(|_,(a,b)|!a.is_zero()||!b.is_zero());
    let mut actual=BTreeMap::new();
    for (mono,c) in &after.p.terms{actual.insert(mono.clone(),exact_pair(c)?);}
    if expected!=actual{return Err("substitution phase mismatch");}
    let mut rows=Vec::new();
    for (i,row) in before.constraints.iter().enumerate(){
        if skip==Some(i){continue;}
        let mut q=BTreeSet::new();
        for mono in row{
            if mono.contains(&y){
                let rest:Vec<_>=mono.iter().copied().filter(|&v|v!=y).collect();
                for part in rhs{parity(&mut q,join(&rest,part));}
            }else{parity(&mut q,mono.clone());}
        }
        if !q.is_empty(){rows.push(q);}
    }
    let actual:Vec<BTreeSet<Vec<u32>>>=after.constraints.iter().map(|q|q.iter().cloned().collect()).collect();
    if rows!=actual{return Err("substitution ANF mismatch");}
    Ok(())
}

#[cfg(test)]
fn check_general_substitution(before:&Trace,after:&Trace,y:u32,row:usize,m:usize,o:usize)
    ->Result<(), &'static str>{
    if m!=0||o!=0{return Err("substitution multiplier must be one");}
    let mut rhs=before.constraints.get(row).ok_or("missing source row")?.iter().cloned()
        .collect::<std::collections::BTreeSet<_>>();
    if !rhs.remove(&vec![y])||rhs.iter().any(|m|m.contains(&y)){
        return Err("nonisolated source pivot");
    }
    check_substitution_transport(before,after,y,&rhs,Some(row))
}

// The actual reducer returns pivot and RHS length, not row index.
// Independently find an original isolated equation that explains the
// committed transition; this checks existence, not native choice order.
#[cfg(test)]
fn check_observed_substitution(before:&Trace,after:&Trace,y:u32,len:usize)->bool{
    before.constraints.iter().enumerate().any(|(i,r)|r.len()==len+1
        &&check_general_substitution(before,after,y,i,0,0).is_ok())
}

#[cfg(test)]
fn check_hh(before:&Trace,after:&Trace,y:u32,m:usize,o:usize)->Result<(), &'static str>{
    use std::collections::BTreeSet;
    use num_traits::Zero;
    if m!=1||o!=0{return Err("HH multiplier mismatch");}
    if (y as usize)<before.n||!before.live.contains(&y)
        ||before.constraints.iter().flatten().any(|p|p.contains(&y)){
        return Err("invalid HH integrator");
    }
    let mut phi=BTreeSet::new();
    for (mono,c) in &before.p.terms{
        if !mono.contains(&y){continue;}
        let (turns,rad)=exact_pair(c)?;
        if turns!=Rat::new(1.into(),2.into())||!rad.is_zero(){return Err("HH nonhalf phase");}
        if !mono.windows(2).all(|w|w[0]<w[1])||mono.iter().any(|v|!before.live.contains(v)){
            return Err("invalid HH support");
        }
        phi.insert(mono.iter().copied().filter(|&v|v!=y).collect::<Vec<_>>());
    }
    let removed:Vec<_>=before.live.iter().copied().filter(|v|!after.live.contains(v)).collect();
    if removed.len()!=2||!removed.contains(&y){return Err("HH domain mismatch");}
    let z=*removed.iter().find(|&&v|v!=y).unwrap();
    if (z as usize)<before.n||!phi.remove(&vec![z])||phi.iter().any(|p|p.contains(&z)){
        return Err("nonisolated HH pivot");
    }
    let mut base=before.clone();
    base.live.remove(&y);base.p.terms.retain(|p,_|!p.contains(&y));
    check_substitution_transport(&base,after,z,&phi,None)
}

#[test]
fn exact_trace_general_substitution_certificate(){
    use quprs::rational::PhaseCoeff;
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();
    let mut before=Trace::from_native(&ps).unwrap();
    before.constraints=vec![[vec![y],vec![0],vec![1]].into_iter().collect(),
        [vec![0,y],vec![1]].into_iter().collect()];
    let mut c=PhaseCoeff::QUARTER;c.radians=Some(Rat::new(7.into(),19.into()));
    before.p.add_term(vec![y],c);
    before.p.add_term(vec![0,y],PhaseCoeff::QUARTER);
    let mut after=before.clone();assert_eq!(after.step(),Some((y,2)));
    assert_eq!(check_general_substitution(&before,&after,y,0,0,0),Ok(()));
    let mut bad=after.clone();bad.p.add_term(vec![],PhaseCoeff::HALF);
    assert_eq!(check_general_substitution(&before,&bad,y,0,0,0),Err("substitution phase mismatch"));
    let mut bad=after.clone();bad.constraints.clear();
    assert_eq!(check_general_substitution(&before,&bad,y,0,0,0),Err("substitution ANF mismatch"));
    assert_eq!(check_general_substitution(&before,&after,y,1,0,0),Err("nonisolated source pivot"));
    assert_eq!(check_general_substitution(&before,&after,y,0,1,0),Err("substitution multiplier must be one"));
    let mut bad=after.clone();bad.live.insert(y);
    assert_eq!(check_general_substitution(&before,&bad,y,0,0,0),Err("substitution domain mismatch"));
    for rhs in [vec![vec![y]],vec![vec![y],vec![]]]{
        let mut b=before.clone();b.constraints=vec![rhs.into_iter().collect()];
        let mut a=b.clone();assert!(a.step().is_some());
        assert_eq!(check_general_substitution(&b,&a,y,0,0,0),Ok(()));
    }
    println!("CRR_GENERAL_SUBSTITUTION_CERTIFICATE mixed=1 constant=2 rejected=5 expansion_rhs_cap=8");
}

#[test]
fn exact_trace_hh_certificate(){
    use quprs::rational::PhaseCoeff;
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    let mut before=Trace::from_native(&ps).unwrap();
    before.constraints=vec![[vec![0,z],vec![1]].into_iter().collect()];
    for v in [0,1,z]{before.p.add_term(vec![y,v],PhaseCoeff::HALF);}
    before.p.add_term(vec![0,z],PhaseCoeff::QUARTER);
    let mut after=before.clone();assert_eq!(after.integrate(),Some(("hh",y)));
    assert_eq!(check_hh(&before,&after,y,1,0),Ok(()));
    for x in 0..4{
        let a=hist(&before,x);let b=hist(&after,x);
        for i in 0..4{assert_eq!(a[i] as i64-a[i+4] as i64,2*(b[i] as i64-b[i+4] as i64));}
    }
    assert_eq!(check_hh(&before,&after,y,0,0),Err("HH multiplier mismatch"));
    assert_eq!(check_hh(&before,&after,y,1,1),Err("HH multiplier mismatch"));
    let mut bad=before.clone();bad.constraints.push([vec![y]].into_iter().collect());
    assert_eq!(check_hh(&bad,&after,y,1,0),Err("invalid HH integrator"));
    let mut bad=before.clone();bad.p.add_term(vec![y],PhaseCoeff::QUARTER);
    assert_eq!(check_hh(&bad,&after,y,1,0),Err("HH nonhalf phase"));
    let mut bad=before.clone();bad.p.add_term(vec![y,z,0],PhaseCoeff::HALF);
    assert_eq!(check_hh(&bad,&after,y,1,0),Err("nonisolated HH pivot"));
    let mut bad=after.clone();bad.p.add_term(vec![],PhaseCoeff::HALF);
    assert_eq!(check_hh(&before,&bad,y,1,0),Err("substitution phase mismatch"));
    let mut bad=after.clone();bad.constraints.clear();
    assert_eq!(check_hh(&before,&bad,y,1,0),Err("substitution ANF mismatch"));
    let mut bad=after.clone();bad.live.insert(z);
    assert_eq!(check_hh(&before,&bad,y,1,0),Err("HH domain mismatch"));
    println!("CRR_HH_CERTIFICATE positive=1 rejected=8 exact_signed_histogram_checks=4 multiplier_power=1");
}

// Exact omega certificate: independently reconstruct the two signs of
// the correction in Q/Z x Q, using subset expansion rather than the
// reducer's phase addition or shared XOR expansion.
#[cfg(test)]
fn check_omega(before:&Trace,after:&Trace,y:u32,m:usize,o:usize)->Result<(), &'static str>{
    use std::collections::{BTreeMap,BTreeSet};
    use num_bigint::BigInt;
    use num_integer::Integer;
    use num_traits::Zero;
    if m!=0||o!=1{return Err("omega multiplier mismatch");}
    if before.n!=after.n||(y as usize)<before.n||!before.live.contains(&y)
        ||before.constraints.iter().flatten().any(|p|p.contains(&y)){
        return Err("invalid omega integrator");
    }
    if (0..before.n).any(|i|u32::try_from(i).ok().map_or(true,|v|!before.live.contains(&v))){
        return Err("missing input");
    }
    let live:BTreeSet<_>=before.live.iter().copied().filter(|&v|v!=y).collect();
    if live!=after.live.iter().copied().collect(){return Err("omega domain mismatch");}
    if before.constraints!=after.constraints{return Err("omega ANF mismatch");}
    if before.p.terms.keys().chain(before.constraints.iter().flatten())
        .any(|p|!p.windows(2).all(|w|w[0]<w[1])||p.iter().any(|v|!before.live.contains(v))){
        return Err("invalid omega support");
    }
    let (turns,rad)=exact_pair(before.p.terms.get(&vec![y]).ok_or("missing omega singleton")?)?;
    let sign:i64=if rad.is_zero()&&turns==Rat::new(1.into(),4.into()){1}
        else if rad.is_zero()&&turns==Rat::new(3.into(),4.into()){-1}
        else{return Err("invalid omega singleton");};
    let mut phi=BTreeSet::new();
    let mut expected:BTreeMap<Vec<u32>,ExactPair>=BTreeMap::new();
    for (mono,c) in &before.p.terms{
        let c=exact_pair(c)?;
        if mono.contains(&y){
            if mono.len()==1{continue;}
            if c.0!=Rat::new(1.into(),2.into())||!c.1.is_zero(){return Err("omega nonhalf interaction");}
            phi.insert(mono.iter().copied().filter(|&v|v!=y).collect::<Vec<_>>());
        }else{expected.insert(mono.clone(),c);}
    }
    if phi.len()>8||before.size()>4096{return Err("certificate expansion cap");}
    let phi:Vec<_>=phi.into_iter().collect();
    let mut add=|key:Vec<u32>,delta:Rat|{
        let e=expected.entry(key).or_insert_with(||(Rat::zero(),Rat::zero()));
        e.0+=delta;e.0=Rat::new(e.0.numer().mod_floor(e.0.denom()),e.0.denom().clone());
    };
    add(Vec::new(),Rat::new(BigInt::from(sign),BigInt::from(8)));
    for mask in 1usize..(1usize<<phi.len()){
        let mut support=BTreeSet::new();
        for (i,p) in phi.iter().enumerate(){
            if mask&(1usize<<i)!=0{support.extend(p.iter().copied());}
        }
        // (-2)^(|J|-1) times -sign/4, exact for bounded RHS.
        let factor=(-2i64).pow(mask.count_ones()-1);
        add(support.into_iter().collect(),Rat::new(BigInt::from(-sign*factor),BigInt::from(4)));
    }
    expected.retain(|_,(a,b)|!a.is_zero()||!b.is_zero());
    let mut actual=BTreeMap::new();
    for (mono,c) in &after.p.terms{actual.insert(mono.clone(),exact_pair(c)?);}
    if expected!=actual{return Err("omega phase mismatch");}
    Ok(())
}

#[test]
fn exact_trace_omega_certificate(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut ps=PathSum::new(2);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();
    let mut before=Trace::from_native(&ps).unwrap();
    before.constraints=vec![[vec![0],vec![1]].into_iter().collect()];
    for p in [vec![0,y],vec![1,y],vec![0,1,y]]{before.p.add_term(p,PhaseCoeff::HALF);}
    // Preserve the exact rational radians on an overlapping support
    // while modifying only its turns component.
    let mut c=PhaseCoeff::QUARTER;c.radians=Some(Rat::new(7.into(),19.into()));
    before.p.add_term(vec![0],c);
    before.p.add_term(vec![],PhaseCoeff::new_constant(Rational::new(7,8)));
    before.p.add_term(vec![y],PhaseCoeff::QUARTER);
    let mut after=before.clone();assert_eq!(after.omega(),Some(y));
    assert_eq!(check_omega(&before,&after,y,0,1),Ok(()));
    assert!(!after.p.terms.contains_key(&Vec::new()));
    assert_eq!(after.p.terms[&vec![0]].radians,Some(Rat::new(7.into(),19.into())));
    let mut negative=before.clone();negative.p.terms.get_mut(&vec![y]).unwrap().constant=Rational::THREE_QUARTERS;
    let mut out=negative.clone();assert_eq!(out.omega(),Some(y));
    assert_eq!(check_omega(&negative,&out,y,0,1),Ok(()));
    for quarter in [Rational::QUARTER,Rational::THREE_QUARTERS]{
        let mut b=before.clone();b.p=PhasePolynomial::new();b.p.add_term(vec![y],PhaseCoeff::new_constant(quarter));
        let mut a=b.clone();assert_eq!(a.omega(),Some(y));
        assert_eq!(check_omega(&b,&a,y,0,1),Ok(()));
    }
    assert_eq!(check_omega(&before,&after,y,0,0),Err("omega multiplier mismatch"));
    assert_eq!(check_omega(&before,&after,y,1,1),Err("omega multiplier mismatch"));
    let mut bad=before.clone();bad.constraints.push([vec![y]].into_iter().collect());
    assert_eq!(check_omega(&bad,&after,y,0,1),Err("invalid omega integrator"));
    let mut bad=before.clone();bad.p.terms.remove(&vec![y]);
    assert_eq!(check_omega(&bad,&after,y,0,1),Err("missing omega singleton"));
    let mut bad=before.clone();bad.p.terms.get_mut(&vec![y]).unwrap().constant=Rational::HALF;
    assert_eq!(check_omega(&bad,&after,y,0,1),Err("invalid omega singleton"));
    let mut bad=before.clone();bad.p.terms.get_mut(&vec![0,y]).unwrap().constant=Rational::QUARTER;
    assert_eq!(check_omega(&bad,&after,y,0,1),Err("omega nonhalf interaction"));
    let mut bad=after.clone();bad.p.add_term(vec![],PhaseCoeff::HALF);
    assert_eq!(check_omega(&before,&bad,y,0,1),Err("omega phase mismatch"));
    let mut bad=after.clone();bad.p.terms.get_mut(&vec![0]).unwrap().radians=None;
    bad.p.terms.retain(|_,c|!(c.constant==Rational::new(0,1)&&c.radians.is_none()&&c.symbols.is_empty()));
    assert_eq!(check_omega(&before,&bad,y,0,1),Err("omega phase mismatch"));
    let mut bad=after.clone();bad.constraints.clear();
    assert_eq!(check_omega(&before,&bad,y,0,1),Err("omega ANF mismatch"));
    let mut bad=after.clone();bad.live.insert(y);
    assert_eq!(check_omega(&before,&bad,y,0,1),Err("omega domain mismatch"));
    let mut bad=after.clone();bad.live.insert(99);
    assert_eq!(check_omega(&before,&bad,y,0,1),Err("omega domain mismatch"));
    println!("CRR_OMEGA_CERTIFICATE positive_sign=1 negative_sign=1 empty_phi=2 rejected=11 multiplier_sqrt2_power=1");
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
// Independent free-variable certificate: infer the removed set from
// both domains, not the reducer's used-set scan or claimed count.
// Local relation only: phases and rows must be unchanged exactly.
#[cfg(test)]
fn check_free_elim(before:&Trace,after:&Trace,m:usize,o:usize)
    ->Result<std::collections::BTreeSet<u32>, &'static str>{
    use std::collections::BTreeSet;
    if before.n!=after.n{return Err("input count");}
    if (0..before.n).any(|i|u32::try_from(i).ok().map_or(true,|v|!before.live.contains(&v))){
        return Err("missing input");
    }
    if before.p.terms.keys().chain(before.constraints.iter().flatten()).flatten()
        .any(|v|!before.live.contains(v)){return Err("dangling original support");}
    let old:BTreeSet<_>=before.live.iter().copied().collect();
    let new:BTreeSet<_>=after.live.iter().copied().collect();
    if !new.is_subset(&old){return Err("new live variable");}
    let removed:BTreeSet<_>=old.difference(&new).copied().collect();
    if removed.iter().any(|&v|(v as usize)<before.n){return Err("removed input");}
    if before.p.terms.keys().flatten().any(|v|removed.contains(v)){
        return Err("removed phase variable");
    }
    if before.constraints.iter().flatten().flatten().any(|v|removed.contains(v)){
        return Err("removed constraint variable");
    }
    if before.p.terms!=after.p.terms{return Err("phase drift");}
    if before.constraints!=after.constraints{return Err("constraint drift");}
    if m!=removed.len()||o!=0{return Err("free multiplier mismatch");}
    Ok(removed)
}

// Compose the already checked alias step and free integration without
// rebasing normalization on either intermediate domain.
#[cfg(test)]
fn check_alias_free_normalization(original:&PathSum,before:&Trace,aliased:&Trace,
    after:&Trace,steps:&[UnionWitness],claimed:&AliasMap,twice:i32,m:usize,o:usize)
    ->Result<(), &'static str>{
    check_alias_normalization(original,before,aliased,steps,claimed,twice,0,0)?;
    check_free_elim(aliased,after,m,o)?;
    Ok(())
}

#[test]
fn exact_trace_free_elim_certificate(){
    use quprs::rational::PhaseCoeff;
    use std::collections::BTreeSet;
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let phase=ps.v.get_fresh_var();let row=ps.v.get_fresh_var();
    let a=ps.v.get_fresh_var();let b=ps.v.get_fresh_var();
    ps.p.add_term(vec![phase],PhaseCoeff::QUARTER);
    ps.f.functions[0].insert(vec![row]);
    let before=Trace::from_native(&ps).unwrap();
    let mut after=before.clone();
    let f=batch_free(&mut after,64);assert_eq!(f,2);
    assert_eq!(check_free_elim(&before,&after,f,0),Ok([a,b].into_iter().collect::<BTreeSet<_>>()));
    for x in 0..2{assert_eq!(hist(&before,x),hist(&after,x).map(|v|v*4));}
    let mut partial=before.clone();
    let f=batch_free(&mut partial,1);assert_eq!(f,1);
    assert_eq!(check_free_elim(&before,&partial,f,0),Ok([a].into_iter().collect()));
    let mut single=partial.clone();
    assert_eq!(single.integrate(),Some(("elim",b)));
    assert_eq!(check_free_elim(&partial,&single,1,0),Ok([b].into_iter().collect()));
    assert_eq!(single.live,after.live);
    let mut noop=before.clone();assert_eq!(batch_free(&mut noop,0),0);
    assert_eq!(check_free_elim(&before,&noop,0,0),Ok(BTreeSet::new()));
    // Contradictory residuals are declined by the reducer; no committed
    // deletion or multiplier may be fabricated for that no-op.
    let mut impossible=before.clone();impossible.constraints.push([Vec::new()].into_iter().collect());
    let mut rejected=impossible.clone();assert_eq!(batch_free(&mut rejected,64),0);
    assert_eq!(check_free_elim(&impossible,&rejected,0,0),Ok(BTreeSet::new()));
    assert_eq!(check_free_elim(&before,&after,1,0),Err("free multiplier mismatch"));
    assert_eq!(check_free_elim(&before,&after,2,1),Err("free multiplier mismatch"));
    let mut bad=after.clone();bad.live.remove(&0);
    assert_eq!(check_free_elim(&before,&bad,3,0),Err("removed input"));
    let mut bad=after.clone();bad.live.remove(&phase);
    assert_eq!(check_free_elim(&before,&bad,3,0),Err("removed phase variable"));
    let mut bad=after.clone();bad.live.remove(&row);
    assert_eq!(check_free_elim(&before,&bad,3,0),Err("removed constraint variable"));
    let mut bad=after.clone();bad.live.insert(99);
    assert_eq!(check_free_elim(&before,&bad,2,0),Err("new live variable"));
    let mut bad=after.clone();bad.p.add_term(vec![],PhaseCoeff::HALF);
    assert_eq!(check_free_elim(&before,&bad,2,0),Err("phase drift"));
    let mut bad=after.clone();bad.constraints.clear();
    assert_eq!(check_free_elim(&before,&bad,2,0),Err("constraint drift"));
    let mut bad=before.clone();bad.live.remove(&phase);
    assert_eq!(check_free_elim(&bad,&after,2,0),Err("dangling original support"));
    let mut bad=after.clone();bad.n+=1;
    assert_eq!(check_free_elim(&before,&bad,2,0),Err("input count"));
    let mut bad=before.clone();bad.live.remove(&0);
    assert_eq!(check_free_elim(&bad,&after,2,0),Err("missing input"));
    println!("CRR_FREE_ELIM_CERTIFICATE batch=1 partial=1 single=1 noop=2 rejected=11 multiplier_power=2 source_qasm_certified=false hh_omega_certified=false");
}

// In-memory research ledger for the actual experimental guarded path.
// A full state snapshot is intentional: proof/debug evidence, not a
// production or compact serialized certificate.
#[cfg(test)]
#[derive(Clone)]
enum LedgerRule{Alias(Vec<UnionWitness>,AliasMap),BatchFree,Iter(IterWitness)}
#[cfg(test)]
#[derive(Clone)]
struct LedgerEntry{rule:LedgerRule,before:Trace,trial:Trace,accepted:bool}
#[cfg(test)]
fn same_trace(a:&Trace,b:&Trace)->bool{
    a.n==b.n&&a.live==b.live&&a.p.terms==b.p.terms&&a.constraints==b.constraints
}
#[cfg(test)]
fn independent_cost(t:&Trace)->(usize,usize){
    let p=t.p.terms.keys().fold(0,|a,m|a+1+m.len());
    let c=t.constraints.iter().fold(0,|a,r|a+r.iter().fold(0,|b,m|b+1+m.len()));
    (p,p+c+t.live.len())
}
#[cfg(test)]
type LedgerCounts=(usize,usize,usize,usize,usize,usize,usize);
#[cfg(test)]
fn record_guarded_ledger(original:&Trace)->(Trace,Vec<LedgerEntry>,LedgerCounts){
    let mut t=original.clone();
    let mut log=Vec::new();
    let b=t.clone();
    let (a,links,parent)=recorded_batch_alias(&mut t,64);
    if a>0{
        log.push(LedgerEntry{rule:LedgerRule::Alias(links,parent.unwrap()),before:b,trial:t.clone(),accepted:true});
    }else{assert!(parent.is_none()&&same_trace(&b,&t));}
    let b=t.clone();let f=batch_free(&mut t,64-a);
    if f>0{log.push(LedgerEntry{rule:LedgerRule::BatchFree,before:b,trial:t.clone(),accepted:true});}
    else{assert!(same_trace(&b,&t));}
    let (s,e,h,o,r)=iterate_policy_observe(&mut t,64-a-f,true,|w,b,q,accepted|{
        log.push(LedgerEntry{rule:LedgerRule::Iter(w),before:b.clone(),trial:q.clone(),accepted});
    });
    (t,log,(a+s,f+e,h,o,r,a,f))
}

#[cfg(test)]
fn check_ordered_ledger(original:&PathSum,start:&Trace,final_state:&Trace,
    entries:&[LedgerEntry],twice:i32,counts:LedgerCounts,claimed_k:usize)
    ->Result<(), &'static str>{
    check_residual_normalization(original,start,twice)?;
    let mut current=start;
    let (mut s,mut e,mut h,mut o,mut r,mut a,mut f)=(0usize,0usize,0usize,0usize,0usize,0usize,0usize);
    let mut used=0usize;
    let mut prefix=0;
    for entry in entries{
        if !same_trace(current,&entry.before){return Err("ledger chain mismatch");}
        if used>=64{return Err("ledger fuel exceeded");}
        let x=independent_cost(current);let y=independent_cost(&entry.trial);
        let improves=y.0<=x.0&&y.1<x.1;
        if !entry.accepted{
            if !matches!(&entry.rule,LedgerRule::Iter(_))||improves{return Err("invalid rejected trial");}
            prefix=2;r+=1;continue;
        }
        if !improves{return Err("invalid committed cost");}
        let cost=match &entry.rule{
            LedgerRule::Alias(links,parent)=>{
                if prefix!=0||links.is_empty(){return Err("alias prefix order");}
                check_union_certificate(current,&entry.trial,links,parent)?;
                a=parent.len();s+=a;prefix=1;a
            },
            LedgerRule::BatchFree=>{
                if prefix==2{return Err("free prefix order");}
                let count=current.live.len().checked_sub(entry.trial.live.len()).ok_or("free domain growth")?;
                if count==0{return Err("empty batch free");}
                check_free_elim(current,&entry.trial,count,0)?;
                f=count;e+=count;prefix=2;count
            },
            LedgerRule::Iter(w)=>{
                prefix=2;
                match *w{
                    IterWitness::Sub{y,row}=>{check_general_substitution(current,&entry.trial,y,row,0,0)?;s+=1;},
                    IterWitness::Free{y}=>{
                        let removed=check_free_elim(current,&entry.trial,1,0)?;
                        if !removed.contains(&y){return Err("free witness mismatch");}e+=1;
                    },
                    IterWitness::Hh{y}=>{check_hh(current,&entry.trial,y,1,0)?;h+=1;},
                    IterWitness::Omega{y}=>{check_omega(current,&entry.trial,y,0,1)?;o+=1;},
                }
                1
            }
        };
        used=used.checked_add(cost).ok_or("ledger fuel overflow")?;
        if used>64{return Err("ledger fuel exceeded");}
        current=&entry.trial;
    }
    if !same_trace(current,final_state){return Err("ledger final mismatch");}
    if (s,e,h,o,r,a,f)!=counts{return Err("ledger counts mismatch");}
    let k=e.checked_add(h).and_then(|v|v.checked_mul(2)).and_then(|v|v.checked_add(o))
        .ok_or("ledger multiplier overflow")?;
    if k!=claimed_k{return Err("ledger multiplier mismatch");}
    // Integer exponent splitting used by restore_count: a rational
    // factor 2^(e+h+floor(o/2)), residual odd sqrt2 in N-(o mod 2).
    let integer=e+h+o/2;
    let adjusted=twice.checked_sub((o%2) as i32).ok_or("ledger normalization overflow")?;
    if i64::from(adjusted)-2*(integer as i64)!=i64::from(twice)-(k as i64){
        return Err("ledger normalization split");
    }
    Ok(())
}

// Portable snapshots retain exact coefficient fractions, not only
// the research hash of Debug output. Canonical ordering is independent
// of hash-map iteration; row order itself is preserved.
#[cfg(test)]
fn ledger_snapshot(t:&Trace)->String{
    fn mono(m:&[u32])->String{
        if m.is_empty(){"-".into()}else{m.iter().map(u32::to_string).collect::<Vec<_>>().join(",")}
    }
    let mut live:Vec<_>=t.live.iter().copied().collect();live.sort_unstable();
    let mut phase:Vec<_>=t.p.terms.iter().collect();phase.sort_unstable_by(|(a,_),(b,_)|a.cmp(b));
    let phase=phase.into_iter().map(|(m,c)|{
        let (a,b)=exact_pair(c).unwrap();
        format!("{}:{}:{}:{}:{}",mono(m),a.numer(),a.denom(),b.numer(),b.denom())
    }).collect::<Vec<_>>().join("|");
    let rows=t.constraints.iter().map(|p|{
        let mut ms:Vec<_>=p.iter().collect();ms.sort();
        if ms.is_empty(){"~".into()}else{ms.into_iter().map(|m|mono(m)).collect::<Vec<_>>().join(":")}
    }).collect::<Vec<_>>().join("|");
    format!("{};{};{};{}",t.n,mono(&live),if phase.is_empty(){"~"}else{&phase},
        if rows.is_empty(){"!"}else{&rows})
}
#[cfg(test)]
fn export_ordered_ledger(name:&str,start:&Trace,end:&Trace,entries:&[LedgerEntry],
    twice:i32,counts:LedgerCounts,k:usize){
    use std::fmt::Write as _;
    use std::io::Write as _;
    let Some(dir)=std::env::var_os("CRR_GATE_DIR")else{return;};
    assert!(name.chars().all(|c|c.is_ascii_alphanumeric()||c=='_'));
    let dir=std::path::PathBuf::from(dir).join("ledgers");
    std::fs::create_dir_all(&dir).unwrap();
    let mut text=format!("crr-ledger-v2 {twice} {k} {} {} {} {} {} {} {}\nstart {}\n",
        counts.0,counts.1,counts.2,counts.3,counts.4,counts.5,counts.6,ledger_snapshot(start));
    for entry in entries{
        let (kind,witness)=match &entry.rule{
            LedgerRule::Alias(links,map)=>{
                let a=links.iter().map(|v|format!("{},{},{},{}",v.x,v.y,v.child,v.par)).collect::<Vec<_>>().join("|");
                let mut p:Vec<_>=map.iter().collect();p.sort_unstable();
                let b=p.iter().map(|(x,y)|format!("{x},{y}")).collect::<Vec<_>>().join("|");
                (0,format!("{a}:{b}"))
            },
            LedgerRule::BatchFree=>(1,"-".into()),
            LedgerRule::Iter(IterWitness::Sub{y,row})=>(2,format!("{y},{row}")),
            LedgerRule::Iter(IterWitness::Free{y})=>(3,y.to_string()),
            LedgerRule::Iter(IterWitness::Hh{y})=>(4,y.to_string()),
            LedgerRule::Iter(IterWitness::Omega{y})=>(5,y.to_string()),
        };
        writeln!(&mut text,"step {kind} {} {witness} {} {}",u8::from(entry.accepted),
            ledger_snapshot(&entry.before),ledger_snapshot(&entry.trial)).unwrap();
    }
    writeln!(&mut text,"end {}",ledger_snapshot(end)).unwrap();
    let path=dir.join(format!("{name}.ledger"));
    let mut f=std::fs::OpenOptions::new().create_new(true).write(true).open(path).unwrap();
    f.write_all(text.as_bytes()).unwrap();
    println!("CRR_PORTABLE_LEDGER name={name} steps={} sha256={}",entries.len(),receipt_sha(text.as_bytes()));
}

#[test]
fn exact_trace_ordered_ledger(){
    use quprs::rational::{PhaseCoeff,Rational};
    // Alias plus a free variable and an omega integration with no
    // interaction: constant phase correction can reduce incidence.
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();ps.v.get_fresh_var();
    ps.f.functions[0].clear();ps.f.functions[0].insert(vec![y]);
    ps.p.add_term(vec![y],PhaseCoeff::HALF);
    ps.p.add_term(vec![0],PhaseCoeff::HALF);
    ps.p.add_term(vec![z],PhaseCoeff::QUARTER);
    let start=Trace::from_native(&ps).unwrap();
    let (end,log,counts)=record_guarded_ledger(&start);
    let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
    let k=2*(counts.1+counts.2)+counts.3;
    assert_eq!((counts.5,counts.6,counts.3),(1,1,1));
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&log,twice,counts,k),Ok(()));
    export_ordered_ledger("synthetic_mixed",&start,&end,&log,twice,counts,k);
    let mut native=start.clone();assert_eq!(batch_then_iterate(&mut native),counts);assert!(same_trace(&native,&end));
    let mut bad=log.clone();bad.swap(0,1);
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&bad,twice,counts,k),Err("ledger chain mismatch"));
    let mut bad=log.clone();bad.pop();
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&bad,twice,counts,k),Err("ledger final mismatch"));
    let mut bad=log.clone();bad[0].accepted=false;
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&bad,twice,counts,k),Err("invalid rejected trial"));
    let mut bad=counts;bad.3+=1;
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&log,twice,bad,k),Err("ledger counts mismatch"));
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&log,twice,counts,k+1),Err("ledger multiplier mismatch"));
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&log,twice-1,counts,k),Err("original normalization mismatch"));
    // Real cost-policy rejection from the existing growth fixture.
    let mut ps=PathSum::new(1);ps.rr_tolerance=0.0;
    let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();let w=ps.v.get_fresh_var();
    ps.f.functions[0].insert(vec![y]);ps.f.functions[0].insert(vec![0,z]);ps.f.functions[0].insert(vec![0,w]);
    ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,8)));
    let start=Trace::from_native(&ps).unwrap();
    let (end,log,counts)=record_guarded_ledger(&start);
    let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
    assert!(counts.4>0);
    let k=2*(counts.1+counts.2)+counts.3;
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&log,twice,counts,k),Ok(()));
    export_ordered_ledger("synthetic_rejection",&start,&end,&log,twice,counts,k);
    let mut bad=log.clone();let i=bad.iter().position(|e|!e.accepted).unwrap();bad[i].accepted=true;
    assert_eq!(check_ordered_ledger(&ps,&start,&end,&bad,twice,counts,k),Err("invalid committed cost"));
    let mut leaked=end.clone();leaked.live=log[i].trial.live.clone();
    assert_eq!(check_ordered_ledger(&ps,&start,&leaked,&log,twice,counts,k),Err("ledger final mismatch"));
    println!("CRR_ORDERED_LEDGER_CERTIFICATE positive=2 rejected_mutations=8 rejected_trials={} snapshot_scope=research_only",counts.4);
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
        let cert=cert.unwrap();
        let residual=orig.encoding_view(&ps);
        let twice=(residual.v.num_qubits+residual.v.path_vars.len()) as i32;
        assert_eq!(check_alias_normalization(&residual,&orig,&q,&steps,&cert,twice,0,0),Ok(()));
        aliases+=n;
        assert!((0..3).all(|x|q.live.contains(&x)));
        let aliased=q.clone();
        let f=batch_free(&mut q,64-n);assert!(f>=1);free_count+=f;
        assert_eq!(check_alias_free_normalization(&residual,&orig,&aliased,&q,&steps,&cert,twice,f,0),Ok(()));
        assert_eq!(check_alias_free_normalization(&residual,&orig,&aliased,&q,&steps,&cert,twice,f-1,0),
            Err("free multiplier mismatch"));
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
    println!("CRR_BATCH_ORACLE models=513 histogram_checks={checks} alias_eliminations={aliases} free_eliminations={free_count} cycle_control=1 union_certificate_checks=513 alias_normalization_checks=512 alias_free_certificate_checks=512 alias_free_wrong_multiplier_rejected=512");
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


// Source-locked receipt pilot. The same bytes are hashed and parsed.
// Git blob pins are copied from the locked paper corpus manifest;
// SHA256 binds the actual byte payload rather than a filename.
#[cfg(test)]
fn receipt_sha(data:&[u8])->String{
    use sha2::{Digest,Sha256};
    format!("{:x}",Sha256::digest(data))
}
#[cfg(test)]
fn receipt_read(path:&std::path::Path,expected:&str)->(String,String){
    use std::io::Write;
    use std::process::{Command,Stdio};
    let bytes=std::fs::read(path).expect("source bytes");
    let mut child=Command::new("git").args(["hash-object","--no-filters","--stdin"])
        .stdin(Stdio::piped()).stdout(Stdio::piped()).spawn().expect("git blob hash");
    child.stdin.take().unwrap().write_all(&bytes).unwrap();
    let out=child.wait_with_output().unwrap();assert!(out.status.success());
    assert_eq!(std::str::from_utf8(&out.stdout).unwrap().trim(),expected,"source pin drift: {path:?}");
    let sha=receipt_sha(&bytes);
    (String::from_utf8(bytes).expect("UTF8 QASM"),sha)
}
#[cfg(test)]
fn receipt_trace(t:&Trace)->String{
    let mut live:Vec<_>=t.live.iter().copied().collect();live.sort_unstable();
    let mut phase:Vec<_>=t.p.terms.iter().collect();phase.sort_unstable_by(|(a,_),(b,_)|a.cmp(b));
    let rows:Vec<Vec<Vec<u32>>>=t.constraints.iter().map(|r|{
        let mut p:Vec<_>=r.iter().cloned().collect();p.sort();p
    }).collect();
    // Versioned deterministic research hash; not a serialized proof format.
    let text=format!("crr-trace-v1|n={}|live={live:?}|phase={phase:?}|rows={rows:?}",t.n);
    receipt_sha(text.as_bytes())
}
#[cfg(test)]
fn receipt_ledger(entries:&[LedgerEntry])->String{
    let mut text=String::from("crr-ledger-v1");
    for e in entries{
        let rule=match &e.rule{
            LedgerRule::Alias(links,map)=>{
                let mut p:Vec<_>=map.iter().collect();p.sort_unstable();
                format!("alias:{links:?}:{p:?}")
            },
            LedgerRule::BatchFree=>"batch_free".into(),
            LedgerRule::Iter(w)=>format!("{w:?}"),
        };
        text.push_str(&format!("|{rule}|{}|{}|{}",e.accepted,receipt_trace(&e.before),receipt_trace(&e.trial)));
    }
    receipt_sha(text.as_bytes())
}

#[test]
fn exact_trace_source_locked_receipts(){
    use quprs::{check_equivalence_with_options,EquivalenceStatus,VerificationMethod,VerificationOptions};
    use quprs::qasm::parse_qasm_str;
    use std::path::Path;
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    // Manifest table2_mqt, fixed cohort selected before running.
    let cases=[
        ("qft_16","qft_nativegates_ibm_qiskit_opt0_16.qasm","398b32262259af75fcf44ab711b77281818d0cc7","d321013120dbad7082892026e1ee7a70f9edc206"),
        ("qpeexact_8","qpeexact_nativegates_ibm_qiskit_opt0_8.qasm","4582df5b4cefe3cc69227d29eb2894ccd1c5412a","46a2b00a19bbc769aefa77eebb14fa262fd98302"),
        ("ghz_32","ghz_nativegates_ibm_qiskit_opt0_32.qasm","07c16aaefc4b33750e86a73a0cf276fafe59f8cd","dc87f6aa2dde89a153685bd2b16c446bbc30c261"),
        ("graphstate_16","graphstate_nativegates_ibm_qiskit_opt0_16.qasm","ab34308febb31ea9a49e9761a988aad7017f3487","c2c6f9d04f6a8c2778415572aa247ee93e138c09"),
    ];
    let (mut passed,mut active,mut selected_count,mut skipped,mut refused)=(0,0,0,0,0);
    for (case,file,src_pin,dst_pin) in cases{
        let (src,src_sha)=receipt_read(&root.join("benchmarks/MQTBench").join(file),src_pin);
        let (dst,dst_sha)=receipt_read(&root.join("benchmarks/MQTBench/h,ry,rz,cx").join(file),dst_pin);
        let (a,n)=parse_qasm_str(&src).expect("source parse");
        let (b,m)=parse_qasm_str(&dst).expect("target parse");
        assert_eq!(n,m);
        let r=check_equivalence_with_options(n,&a,&b,&VerificationOptions{
            method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,
            ..VerificationOptions::default()
        }).expect("native RR");
        assert!(!r.solver_invoked);
        let p=r.final_pathsum();
        let native=r.status.as_str();
        let prefix=format!("CRR_SOURCE_RECEIPT case={case} source_sha256={src_sha} target_sha256={dst_sha} native={native}");
        if r.rr_approximate||matches!(&r.status,EquivalenceStatus::Timeout|EquivalenceStatus::MemoryOut){
            println!("{prefix} status=not_admitted reason=native_admission source_semantics_certified=false solver=not_run");
            skipped+=1;continue;
        }
        let Some(start)=Trace::from_native(p)else{
            println!("{prefix} status=not_admitted reason=trace_admission source_semantics_certified=false solver=not_run");
            skipped+=1;continue;
        };
        if start.size()>TERM_CAP{
            println!("{prefix} status=not_admitted reason=term_cap source_semantics_certified=false solver=not_run");
            skipped+=1;continue;
        }
        let twice=(n+p.v.path_vars.len()) as i32;
        let (end,ledger,counts)=record_guarded_ledger(&start);
        let k=2*(counts.1+counts.2)+counts.3;
        if let Err(reason)=check_ordered_ledger(p,&start,&end,&ledger,twice,counts,k){
            println!("{prefix} status=certificate_rejected reason={reason:?} source_semantics_certified=false solver=not_run");
            refused+=1;continue;
        }
        export_ordered_ledger(&format!("{case}_selected"),&start,&end,&ledger,twice,counts,k);
        let candidate=end.encoding_view(p);
        let (av,ac)=trace_cnf_dimensions(p);
        let (bv,bc)=trace_cnf_dimensions(&candidate);
        let before=start.cost().0;let after=end.cost().0;
        let eligible=start.live.len()!=start.n&&screen_accept(&start).0
            &&before>0&&after<before&&after.saturating_mul(100)<=before.saturating_mul(95);
        let selected=eligible&&bv<=av&&bc<=ac&&(bv<av||bc<ac);
        let chosen=if selected{&candidate}else{p};
        let (mgr,v,c)=route_encode(chosen);
        assert_eq!((v,c),if selected{(bv,bc)}else{(av,ac)});
        let dimacs=mgr.try_to_dimacs_string("gpmc").expect("receipt DIMACS");
        let (_,gate_receipt,weight_checks)=check_receipt_cnf(chosen,&dimacs).unwrap_or_else(|e|panic!("selected CNF certificate {case}: {e}"));
        let input_bound=normalized_input_bound(chosen.v.path_vars.len(),weight_checks,twice,if selected{k}else{0}).unwrap();
        export_portable_gate(&format!("{case}_selected"),&portable_gate_text(&gate_receipt,v),&dimacs,false);
        export_phase_sidecar(&format!("{case}_selected"),&gate_receipt);
        export_guard_sidecar(&format!("{case}_selected"),chosen);
        println!("CRR_GATE_RECEIPT case={case} arm=selected sha256={} gates={} equalities={}",gate_receipt_sha(&gate_receipt),gate_receipt.defs.len(),gate_receipt.equalities.len());
        println!("CRR_REAL_CNF_CERTIFICATE case={case} status=matched vars={v} clauses={c} weights={weight_checks} structural=true numerical_weight_check=true normalized_input_bound={input_bound} bound_conditional_on_reference=true solver_count_certified=false");
        let (_,lv,lc,lm,lo,ls)=lazy_prepare(p);
        assert_eq!((v,c,selected),(lv,lc,ls));
        assert_eq!((lm,lo),if selected{(counts.1+counts.2,counts.3)}else{(0,0)});
        let initial_sha=receipt_trace(&start);let final_sha=receipt_trace(&end);
        let ledger_sha=receipt_ledger(&ledger);let cnf_sha=receipt_sha(dimacs.as_bytes());
        let accepted=ledger.iter().filter(|e|e.accepted).count();
        println!("{prefix} status=certified residual_sha256={initial_sha} final_sha256={final_sha} ledger_sha256={ledger_sha} cnf_sha256={cnf_sha} accepted={accepted} rejected={} alias={} free={} hh={} omega={} normalization_twice={twice} multiplier_squared_exponent={k} selected={selected} vars={v} clauses={c} selected_multiplier_squared_exponent={} source_semantics_certified=false cnf_semantics_certified=false solver=not_run",
            counts.4,counts.5,counts.1,counts.2,counts.3,if selected{k}else{0});
        passed+=1;active+=usize::from(accepted>0);selected_count+=usize::from(selected);
    }
    assert_eq!(passed+skipped+refused,cases.len());
    assert!(passed>0&&active>0,"no nontrivial real residual certificate");
    println!("CRR_SOURCE_RECEIPT_SUMMARY cohort=4 certified={passed} nontrivial={active} selected={selected_count} not_admitted={skipped} rejected={refused} solver_calls=0");
}


// Direct, bounded research invocation of the *same serialized bytes*
// whose digest is recorded. Do not change production adapter visibility,
// global environment or solver dispatch. GNU timeout is the CI guard.
#[cfg(test)]
fn receipt_solve(dimacs:&str,exe:&std::path::Path,case:&str,arm:&str)
    ->Option<(Count,String,String)>{
    use std::process::Command;
    use std::io::Write;
    use std::time::{SystemTime,UNIX_EPOCH};
    struct Temp(std::path::PathBuf);
    impl Drop for Temp{fn drop(&mut self){let _=std::fs::remove_dir_all(&self.0);}}
    let root=std::env::temp_dir().join(format!("crr-solver-receipt-{}-{}",std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()));
    std::fs::create_dir(&root).expect("receipt directory");
    let root=Temp(root);
    let cnf=root.0.join("input.cnf");
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(&cnf).unwrap();
    file.write_all(dimacs.as_bytes()).unwrap();drop(file);
    let cnf_sha=receipt_sha(&std::fs::read(&cnf).unwrap());
    assert_eq!(cnf_sha,receipt_sha(dimacs.as_bytes()));
    let exe_sha=receipt_sha(&std::fs::read(exe).unwrap());
    let out=Command::new("timeout").args(["--kill-after=2s","12s"])
        .arg(exe).args(["-mode=1","-prec=90"]).arg(&cnf).output().expect("bounded GPMC invocation");
    assert_eq!(receipt_sha(&std::fs::read(&cnf).unwrap()),cnf_sha);
    assert_eq!(receipt_sha(&std::fs::read(exe).unwrap()),exe_sha);
    let stdout_sha=receipt_sha(&out.stdout);let stderr_sha=receipt_sha(&out.stderr);
    let prefix=format!("CRR_SOLVER_INVOCATION case={case} arm={arm} cnf_sha256={cnf_sha} executable_sha256={exe_sha} stdout_sha256={stdout_sha} stderr_sha256={stderr_sha} weight_bits=256 digits=90 deadline_s=12");
    if !out.status.success(){
        println!("{prefix} status=incomplete exit={:?} solver_count_certified=false",out.status.code());
        return None;
    }
    let stdout=std::str::from_utf8(&out.stdout).expect("UTF8 GPMC stdout");
    let raw=quprs::precision_count::parse_stdout(stdout).expect("typed printed GPMC count");
    println!("{prefix} status=complete raw_real={} raw_imag={} real_half_unit={} imag_half_unit={} format={:?} solver_count_certified=false",
        raw.real,raw.imag,raw.real_half_unit,raw.imag_half_unit,raw.format_name);
    Some((raw,cnf_sha,stdout_sha))
}

#[test]
fn gpmc_trace_witness_source_receipts(){
    use quprs::{check_equivalence_with_options,EquivalenceStatus,VerificationMethod,VerificationOptions};
    use quprs::qasm::parse_qasm_str;
    use quprs::precision_count::PrintedVerdict;
    use num_bigint::BigInt;
    use num_traits::Signed;
    use std::path::Path;
    let exe=std::path::PathBuf::from(std::env::var("QUPRS_GPMC_PATH").expect("pinned GPMC"));
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    // Small source-locked analytical controls. The QASM byte hashes are
    // fixed independently of the parser and solver. HH is identity,
    // HSH has normalized trace magnitude 1/sqrt(2), X has trace zero.
    const HH:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nh q[0];\nh q[0];\n";
    const HSH:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nh q[0];\ns q[0];\nh q[0];\n";
    const X:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nx q[0];\n";
    const HH_SHA:&str="444ebc5f455b5d5d2d5b41ba842ce4563cce55111e4e71cb4712387544f8e9e2";
    const HSH_SHA:&str="7a2a99a74691a0129e85bd2ab91b9bf944736b02873891c8a5bfab6cda154b4c";
    const X_SHA:&str="6d0c49fcc92e79d6bbed4f2d7f0eb06926666988cf4c87271d8ae059f572580a";
    const I2:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\nh q[0];\nh q[0];\n";
    const CZ:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\nh q[1];\ncx q[0],q[1];\nh q[1];\n";
    const CX:&str="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncx q[0],q[1];\n";
    const I2_SHA:&str="1a9ccd1a9fac8cdd85a09ac745f1f4818099c704d97d4f5e3d30f68c675be088";
    const CZ_SHA:&str="c84b86843a732059981d7b58caa2d4ba715a8ea45a0063f8cb1b0f6397518a13";
    const CX_SHA:&str="53acdf2573ff69c7561545518ad4fbe6d5cd3b0310dcd2623158e217b36d1006";
    let mut cases=Vec::new();
    for (id,source,pin,want) in [("hh_source_eq",HH,HH_SHA,4i64),("hsh_source_neq",HSH,HSH_SHA,2),("x_source_neq",X,X_SHA,0)]{
        assert_eq!(receipt_sha(source.as_bytes()),pin);
        assert_eq!(receipt_sha(HH.as_bytes()),HH_SHA);
        cases.push((id,source.to_string(),HH.to_string(),pin.to_string(),HH_SHA.to_string(),Some(want)));
    }
    for (id,source,pin) in [("cz_source_neq",CZ,CZ_SHA),("cx_source_neq",CX,CX_SHA)]{
        assert_eq!(receipt_sha(source.as_bytes()),pin);assert_eq!(receipt_sha(I2.as_bytes()),I2_SHA);
        cases.push((id,source.to_string(),I2.to_string(),pin.to_string(),I2_SHA.to_string(),Some(1)));
    }
    for (id,file,a,b) in [
        ("qft_16","qft_nativegates_ibm_qiskit_opt0_16.qasm","398b32262259af75fcf44ab711b77281818d0cc7","d321013120dbad7082892026e1ee7a70f9edc206"),
        ("qpeexact_8","qpeexact_nativegates_ibm_qiskit_opt0_8.qasm","4582df5b4cefe3cc69227d29eb2894ccd1c5412a","46a2b00a19bbc769aefa77eebb14fa262fd98302"),
    ]{
        let (src,sa)=receipt_read(&root.join("benchmarks/MQTBench").join(file),a);
        let (dst,sb)=receipt_read(&root.join("benchmarks/MQTBench/h,ry,rz,cx").join(file),b);
        cases.push((id,src,dst,sa,sb,None));
    }
    let (mut controls,mut real_pairs,mut incomplete)=(0,0,0);
    for (case,src,dst,src_sha,dst_sha,expected) in cases{
        let (a,n)=parse_qasm_str(&src).expect("source parse");
        let (b,m)=parse_qasm_str(&dst).expect("target parse");assert_eq!(n,m);
        let r=check_equivalence_with_options(n,&a,&b,&VerificationOptions{
            method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,
            ..VerificationOptions::default()
        }).expect("native RR");
        assert!(!r.solver_invoked&&!r.rr_approximate);
        assert!(!matches!(&r.status,EquivalenceStatus::Timeout|EquivalenceStatus::MemoryOut));
        let p=r.final_pathsum();let start=Trace::from_native(p).expect("receipt admission");
        assert!(start.size()<=TERM_CAP);
        let twice=(n+p.v.path_vars.len()) as i32;
        let (end,ledger,counts)=record_guarded_ledger(&start);
        let k=2*(counts.1+counts.2)+counts.3;
        check_ordered_ledger(p,&start,&end,&ledger,twice,counts,k).expect("real ledger");
        export_ordered_ledger(&format!("{case}_paired"),&start,&end,&ledger,twice,counts,k);
        let reduced=end.encoding_view(p);
        let (baseline,_,_)=route_encode(p);
        let (conditioned,_,_)=route_encode(&reduced);
        let mut results=Vec::new();
        for (arm,mgr,m,o) in [("baseline",baseline,0,0),("certified",conditioned,counts.1+counts.2,counts.3)]{
            let cnf=mgr.try_to_dimacs_string("gpmc").expect("solver receipt CNF");
            let encoded=if arm=="baseline"{p}else{&reduced};
            let (actual,e,w)=check_receipt_cnf(encoded,&cnf).unwrap_or_else(|err|panic!("solver CNF {case} {arm}: {err}"));
            let input_bound=normalized_input_bound(encoded.v.path_vars.len(),w,twice,2*m+o).unwrap();
            println!("CRR_SOLVER_CNF_CERTIFICATE case={case} arm={arm} weights={w} cnf_sha256={} structural=true numerical_weight_check=true normalized_input_bound={input_bound} bound_conditional_on_reference=true",receipt_sha(cnf.as_bytes()));
            export_portable_gate(&format!("{case}_{arm}"),&portable_gate_text(&e,actual.vars),&cnf,false);
            export_phase_sidecar(&format!("{case}_{arm}"),&e);
            export_guard_sidecar(&format!("{case}_{arm}"),encoded);
            println!("CRR_GATE_RECEIPT case={case} arm={arm} sha256={} gates={} equalities={}",gate_receipt_sha(&e),e.defs.len(),e.equalities.len());
            let exact=if let Some(want)=expected{
                let count=exact_serialized_wmc(&actual).unwrap();
                assert_eq!(count,exact_live_wmc(encoded,&actual,&e).unwrap());
                let (lo,hi)=ideal_trace_squared_interval(&count,twice,2*m+o,&input_bound);
                let truth=Rat::new(want.into(),4.into());
                assert!(lo<=truth&&truth<=hi,"conditional ideal reference {case} {arm}");
                println!("CRR_IDEAL_TRACE_INTERVAL case={case} arm={arm} lower={lo} upper={hi} analytic_truth={truth} conditional=true");
                Some(count)
            }else{None};
            if let Some((raw,cnf_sha,stdout_sha))=receipt_solve(&cnf,&exe,case,arm){
                if let Some((re,im))=exact{
                    let delta=(&raw.real-re).abs()+(&raw.imag-im).abs();
                    assert!(delta<=Rat::new(1.into(),BigInt::from(10u8).pow(50)));
                    println!("CRR_BOUNDED_WMC_REFERENCE case={case} arm={arm} status=matched raw_l1_delta={delta} exact_serialized_count=true external_solver_error_certified=false");
                }
                // Midpoint distance uses exact rational scaling and an
                // adjusted integer exponent; no rounded sqrt2 needed.
                let factor=Rat::from_integer(BigInt::from(1u8)<<(m+o/2));
                let scaled_norm=(&raw.real*&raw.real+&raw.imag*&raw.imag)*&factor*&factor;
                let normalizer=Rat::from_integer(BigInt::from(1u8)<<((twice-(o%2) as i32) as usize));
                let trace_sq=scaled_norm/normalizer;
                let (restored,verdict)=restore_count(raw,m,o,twice);
                println!("CRR_SOLVER_BOUND case={case} arm={arm} source_sha256={src_sha} target_sha256={dst_sha} residual_sha256={} final_sha256={} ledger_sha256={} cnf_sha256={cnf_sha} stdout_sha256={stdout_sha} normalization_twice={twice} multiplier_squared_exponent={} trace_modulus_squared={trace_sq} verdict={verdict:?} source_semantics_certified=false cnf_semantics_certified=false solver_count_certified=false",
                    receipt_trace(&start),receipt_trace(&end),receipt_ledger(&ledger),2*m+o);
                if let Some(want)=expected{
                    let truth=Rat::new(want.into(),4.into());
                    assert!((&trace_sq-&truth).abs()<=Rat::new(1.into(),BigInt::from(10u8).pow(50)));
                    let wanted=if want==4{PrintedVerdict::Equivalent}else{PrintedVerdict::NotEquivalent};
                    assert_eq!(std::mem::discriminant(&verdict),std::mem::discriminant(&wanted));
                }
                results.push((trace_sq,restored,verdict));
            }else{incomplete+=1;}
        }
        if expected.is_some(){assert_eq!(results.len(),2,"analytic control incomplete");controls+=1;}
        if results.len()==2{
            let (x,a,va)=&results[0];let (y,b,vb)=&results[1];
            let tol=Rat::new(1.into(),BigInt::from(10u8).pow(50));
            assert!((x-y).abs()<=tol);
            assert_eq!(std::mem::discriminant(va),std::mem::discriminant(vb));
            let scale=Rat::from_integer(BigInt::from(1u8)<<(twice as usize/2));
            assert!(((&a.real-&b.real).abs()+(&a.imag-&b.imag).abs())/scale<=tol);
            if expected.is_none(){real_pairs+=1;}
        }
    }
    assert_eq!(controls,5);assert!(real_pairs>0,"no complete real solver receipt pair");
    println!("CRR_SOLVER_RECEIPT_SUMMARY analytic_controls={controls} real_matched_pairs={real_pairs} incomplete_calls={incomplete} source_semantics_certified=false solver_count_certified=false");
}


// Research-only independent DIMACS certificate. Recover the declared
// allocation schedule from the exact PathSum instance passed to encode_trace;
// do not read the manager's private maps or invoke its Boolean encoder.
// Compare a multiset of clauses generated from truth tables (not its templates).
#[cfg(test)]
#[derive(Clone)]
struct CnfReceipt{
    vars:usize,clauses:Vec<Vec<i32>>,weights:std::collections::BTreeMap<i32,ExactPair>,
}
#[cfg(test)]
fn receipt_decimal(v:&str)->Result<Rat,&'static str>{
    use num_bigint::BigInt;
    if v.len()>512{return Err("weight token cap");}
    let (m,e)=if let Some(i)=v.find(['e','E']){
        (&v[..i],v[i+1..].parse::<i32>().map_err(|_|"weight exponent")?)
    }else{(v,0)};
    if e.unsigned_abs()>4096{return Err("weight exponent cap");}
    let unsigned=m.strip_prefix('-').or_else(||m.strip_prefix('+')).unwrap_or(m);
    if unsigned.is_empty()||unsigned.matches('.').count()>1
        ||!unsigned.chars().all(|c|c.is_ascii_digit()||c=='.'){return Err("weight mantissa");}
    let digits=unsigned.replace('.',"");
    let mut n=digits.parse::<BigInt>().map_err(|_|"weight digits")?;
    if m.starts_with('-'){n=-n;}
    let shift=e-unsigned.split_once('.').map_or(0,|(_,r)|r.len() as i32);
    let power=BigInt::from(10u8).pow(shift.unsigned_abs());
    Ok(if shift>=0{Rat::from_integer(n*power)}else{Rat::new(n,power)})
}
#[cfg(test)]
fn parse_receipt_cnf(s:&str)->Result<CnfReceipt,&'static str>{
    use std::collections::BTreeMap;
    let mut lines=s.lines();
    let header:Vec<_>=lines.next().ok_or("missing header")?.split_whitespace().collect();
    if header.len()!=4||header[0]!="p"||header[1]!="cnf"{return Err("bad header");}
    let vars=header[2].parse::<usize>().map_err(|_|"bad variable count")?;
    let count=header[3].parse::<usize>().map_err(|_|"bad clause count")?;
    if vars>100_000||count>1_000_000{return Err("CNF cap");}
    if lines.next()!=Some("c t wmc"){return Err("bad weight mode");}
    let mut clauses=Vec::new();let mut weights=BTreeMap::new();
    for line in lines{
        let t:Vec<_>=line.split_whitespace().collect();
        if t.first()==Some(&"c"){
            if !clauses.is_empty()||t.len()!=7||t[..3]!=["c","p","weight"]||t[6]!="0"{return Err("bad weight line");}
            let id=t[3].parse::<i32>().map_err(|_|"weight id")?;
            if id==0||id.unsigned_abs() as usize>vars{return Err("weight range");}
            if weights.insert(id,(receipt_decimal(t[4])?,receipt_decimal(t[5])?)).is_some(){return Err("duplicate weight");}
        }else{
            if t.last()!=Some(&"0"){return Err("missing clause terminator");}
            let mut row=Vec::new();
            for v in &t[..t.len()-1]{
                let lit=v.parse::<i32>().map_err(|_|"clause literal")?;
                if lit==0||lit.unsigned_abs() as usize>vars{return Err("clause range");}
                row.push(lit);
            }
            row.sort_unstable();clauses.push(row);
        }
    }
    if clauses.len()!=count{return Err("clause count mismatch");}
    clauses.sort();
    Ok(CnfReceipt{vars,clauses,weights})
}
#[cfg(test)]
#[derive(Clone,Debug)]
enum GateOp{False,And(Vec<i32>),Xor(i32,i32)}
#[cfg(test)]
#[derive(Clone)]
struct ExpectedCnf{
    next:i32,live:std::collections::BTreeMap<u32,i32>,clauses:Vec<Vec<i32>>,
    phase:std::collections::BTreeMap<i32,(Vec<u32>,ExactPair)>,
    defs:Vec<(i32,GateOp)>,equalities:Vec<(i32,i32)>,
}
#[cfg(test)]
impl ExpectedCnf{
    fn fresh(&mut self)->i32{let v=self.next;self.next+=1;v}
    fn var(&mut self,v:u32)->i32{
        if let Some(&id)=self.live.get(&v){return id;}
        let id=self.fresh();self.live.insert(v,id);id
    }
    fn clause(&mut self,mut row:Vec<i32>){row.sort_unstable();self.clauses.push(row);}
    fn and(&mut self,z:i32,inputs:&[i32]){
        self.defs.push((z,GateOp::And(inputs.to_vec())));
        // Minimal implicates of z=AND(inputs): each forbidden pair
        // (z=1,input=0) and the single all-ones input with z=0.
        for &v in inputs{self.clause(vec![-z,v]);}
        let mut row:Vec<_>=inputs.iter().map(|v|-v).collect();row.push(z);self.clause(row);
    }
    fn xor(&mut self,a:i32,b:i32,z:i32){
        self.defs.push((z,GateOp::Xor(a,b)));
        for bits in 0..8{
            let x=bits&1!=0;let y=bits&2!=0;let out=bits&4!=0;
            if out!=(x^y){self.clause(vec![if x{-a}else{a},if y{-b}else{b},if out{-z}else{z}]);}
        }
    }
    fn equality(&mut self,a:i32,b:i32){
        self.equalities.push((a,b));
        for (x,y) in [(true,false),(false,true)]{
            self.clause(vec![if x{-a}else{a},if y{-b}else{b}]);
        }
    }
}
#[cfg(test)]
fn expected_receipt_cnf(ps:&PathSum)->Result<ExpectedCnf,&'static str>{
    use std::collections::BTreeMap;
    let mut e=ExpectedCnf{next:1,live:BTreeMap::new(),clauses:Vec::new(),phase:BTreeMap::new(),defs:Vec::new(),equalities:Vec::new()};
    if Trace::from_native(ps).is_none(){return Err("CNF residual admission");}
    for (mono,c) in &ps.p.terms{
        let z=e.fresh();
        let inputs:Vec<_>=mono.iter().map(|&v|e.var(v)).collect();
        e.and(z,&inputs);e.phase.insert(z,(mono.clone(),exact_pair(c)?));
    }
    for (i,row) in ps.f.functions.iter().enumerate(){
        let a=e.var(i as u32);
        let mut values=Vec::new();
        for mono in row{
            let inputs:Vec<_>=mono.iter().map(|&v|e.var(v)).collect();
            let id=if inputs.len()==1{inputs[0]}else{let z=e.fresh();e.and(z,&inputs);z};
            values.push(id);
        }
        let b=if values.is_empty(){let z=e.fresh();e.defs.push((z,GateOp::False));e.clause(vec![-z]);z}else{
            let mut v=values[0];
            for &w in &values[1..]{let z=e.fresh();e.xor(v,w,z);v=z;}
            v
        };
        e.equality(a,b);
    }
    let mut missing:Vec<_>=ps.v.path_vars.iter().filter(|v|!e.live.contains_key(v)).copied().collect();
    missing.sort_unstable();for v in missing{e.var(v);}
    if e.live.len()!=ps.v.path_vars.len()||e.live.keys().any(|v|!ps.v.path_vars.contains(v)){
        return Err("CNF live domain mismatch");
    }
    e.clauses.sort();Ok(e)
}

// Independent fixed-point numerical oracle. Machin pi and Taylor
// sin/cos use integer truncation, not native MPFR or binary64.
// Reduce the angle by an integer multiple of the independently
// computed 2*pi before Taylor. Cap the quotient to 10000; with
// 10^90 scale, the Machin error (<4001 units) is amplified by at
// most 20002, plus Taylor and final truncation. Reference component
// budget 10^-80 is conservative within this domain. This is not a
// kernel-checked numerical theorem or an external solver error bound.
#[cfg(test)]
fn reference_weight(c:&ExactPair)->Result<ExactPair,&'static str>{
    use num_bigint::BigInt;
    use num_integer::Integer;
    use num_traits::{Signed,Zero};
    // Keep the oracle's own precondition explicit, even if the caller
    // bypasses exact_pair. Large noncanonical turns can cancel a large
    // radian term while still amplifying the fixed-point pi error.
    if c.0.is_negative()||c.0>=Rat::from_integer(1.into()){
        return Err("weight reference noncanonical turns");
    }
    let scale=BigInt::from(10u8).pow(90);
    fn atan_inv(q:u32,scale:&BigInt)->BigInt{
        let q=BigInt::from(q);let mut power=q.clone();let square=&q*&q;
        let mut sum=BigInt::from(0);
        for j in 0..200u32{
            let term=scale/(&power*BigInt::from(2*j+1));
            if j%2==0{sum+=term;}else{sum-=term;}power*=&square;
        }
        sum
    }
    let pi=16i32*atan_inv(5,&scale)-4i32*atan_inv(239,&scale);
    let period:BigInt=2i32*pi;
    let angle=&c.0*Rat::from_integer(period.clone())+&c.1*Rat::from_integer(2i32*&scale);
    // Reduce in fixed-point units with exact rational arithmetic.
    // The floor is taken after integer truncation; even a quotient
    // off by one is harmless because we subtract an integer period.
    let q=angle.to_integer().div_floor(&period);
    if q.abs()>BigInt::from(10_000){return Err("weight reference period cap");}
    let x=(angle-Rat::from_integer(q*period)).to_integer();
    if x.abs()>8i32*&scale{return Err("weight reference reduced angle cap");}
    let mut term=scale.clone();let mut re=scale.clone();let mut im=BigInt::zero();
    for j in 1..=200u32{
        term=term*&x/(&scale*BigInt::from(j));
        match j%4{0=>re+=&term,1=>im+=&term,2=>re-=&term,_=>im-=&term}
    }
    Ok((Rat::new(re,scale.clone()),Rat::new(im,scale)))
}
#[cfg(test)]
fn check_receipt_cnf(ps:&PathSum,s:&str)->Result<(CnfReceipt,ExpectedCnf,usize),&'static str>{
    use num_bigint::BigInt;
    use num_traits::{Signed,Zero};
    let actual=parse_receipt_cnf(s)?;
    let expected=expected_receipt_cnf(ps)?;
    if actual.vars!=(expected.next-1) as usize{return Err("CNF variable count mismatch");}
    if actual.clauses!=expected.clauses{return Err("CNF clause mismatch");}
    verify_gate_receipt(&actual,&expected)?;
    if actual.weights.len()!=2*expected.phase.len(){return Err("CNF weight coverage");}
    let one=Rat::from_integer(1.into());let zero=Rat::zero();
    let tolerance=Rat::new(1.into(),BigInt::from(10u8).pow(65));
    let mut checked=0;
    for (&z,(_,phase)) in &expected.phase{
        if actual.weights.get(&-z)!=Some(&(one.clone(),zero.clone())){return Err("negative weight mismatch");}
        let w=actual.weights.get(&z).ok_or("missing positive weight")?;
        let exact=if phase.1.is_zero(){
            (0..4).find(|&k|phase.0==Rat::new(k.into(),4.into()))
        }else{None};
        if let Some(k)=exact{
            let (a,b)=match k{0=>(1,0),1=>(0,1),2=>(-1,0),_=>(0,-1)};
            if w!=&(Rat::from_integer(a.into()),Rat::from_integer(b.into())){return Err("exact Clifford weight mismatch");}
        }else{
            let reference=reference_weight(phase)?;
            if (&w.0-&reference.0).abs()>tolerance||(&w.1-&reference.1).abs()>tolerance{
                return Err("numerical phase weight mismatch");
            }
        }
        checked+=1;
    }
    Ok((actual,expected,checked))
}
#[cfg(test)]
fn check_cnf_fibers(ps:&PathSum,actual:&CnfReceipt,e:&ExpectedCnf)->usize{
    use std::collections::BTreeMap;
    assert!(actual.vars<=18);
    let mut fibers:BTreeMap<Vec<bool>,usize>=BTreeMap::new();
    for bits in 0usize..(1usize<<actual.vars){
        let value=|id:i32|bits>>(id.unsigned_abs()-1)&1!=0;
        if !actual.clauses.iter().all(|row|row.iter().any(|&v|value(v)==(v>0))){continue;}
        let key:Vec<_>=e.live.values().map(|&v|value(v)).collect();
        for (&z,(m,_)) in &e.phase{
            assert_eq!(value(z),m.iter().all(|v|value(e.live[v])));
        }
        *fibers.entry(key).or_default()+=1;
    }
    for bits in 0usize..(1usize<<e.live.len()){
        let key:Vec<_>=(0..e.live.len()).map(|i|bits>>i&1!=0).collect();
        let value: BTreeMap<_,_>=e.live.keys().copied().zip(key.iter().copied()).collect();
        let diagonal=ps.f.functions.iter().enumerate().all(|(i,row)|{
            let parity=row.iter().filter(|m|m.iter().all(|v|value[v])).count()%2!=0;
            parity==value[&(i as u32)]
        });
        assert_eq!(fibers.get(&key).copied().unwrap_or(0),usize::from(diagonal));
    }
    1usize<<e.live.len()
}
#[test]
fn exact_trace_cnf_semantic_certificate(){
    use quprs::rational::{PhaseCoeff,Rational};
    let mut fibers=0;let mut weights=0;let mut wmc=0;
    // Vary constants, empty outputs, nonlinear products, XOR, free
    // live variables, and mixed rational radian/turn coefficients.
    for mask in 0..32{
        let mut p=PathSum::new(2);p.rr_tolerance=0.0;
        let y=p.v.get_fresh_var();p.v.get_fresh_var();
        p.f.functions[0].clear();
        if mask&1!=0{p.f.functions[0].insert(vec![]);}
        if mask&2!=0{p.f.functions[0].insert(vec![0,y]);}
        if mask&4!=0{p.f.functions[0].insert(vec![1]);}
        p.p.add_term(vec![],PhaseCoeff::HALF);
        p.p.add_term(vec![0,y],PhaseCoeff::new_constant(Rational::new(1,8)));
        if mask&8!=0{let mut c=PhaseCoeff::QUARTER;c.radians=Some(Rat::new(7.into(),19.into()));p.p.add_term(vec![1],c);}
        if mask&16!=0{p.p.add_term(vec![y],PhaseCoeff::QUARTER);}
        let (mgr,_,_)=route_encode(&p);
        let s=mgr.try_to_dimacs_string("gpmc").unwrap();
        let (a,e,w)=check_receipt_cnf(&p,&s).unwrap();
        fibers+=check_cnf_fibers(&p,&a,&e);weights+=w;
        assert_eq!(exact_serialized_wmc(&a).unwrap(),exact_live_wmc(&p,&a,&e).unwrap());wmc+=1;
    }
    let mut p=PathSum::new(1);p.rr_tolerance=0.0;
    let y=p.v.get_fresh_var();p.p.add_term(vec![y],PhaseCoeff::QUARTER);
    let (mgr,_,_)=route_encode(&p);let s=mgr.try_to_dimacs_string("gpmc").unwrap();
    let (a,e,_)=check_receipt_cnf(&p,&s).unwrap();
    let z=*e.phase.keys().next().unwrap();
    // These edit actual DIMACS, not a separately constructed formula.
    let bad=s.replacen(&format!("p cnf {} ",a.vars),&format!("p cnf {} ",a.vars+1),1);
    assert!(matches!(check_receipt_cnf(&p,&bad),Err("CNF variable count mismatch")));
    let mut lines:Vec<_>=s.lines().map(str::to_string).collect();
    let i=lines.iter().position(|l|!l.starts_with('p')&&!l.starts_with('c')).unwrap();
    let mut row:Vec<i32>=lines[i].split_whitespace().map(|x|x.parse().unwrap()).collect();
    row[0]=-row[0];lines[i]=row.iter().map(i32::to_string).collect::<Vec<_>>().join(" ");
    assert!(matches!(check_receipt_cnf(&p,&lines.join("\n")),Err("CNF clause mismatch")));
    let bad=s.replace(&format!("c p weight {z} 0.0 1.0 0"),&format!("c p weight {z} 1.0 0.0 0"));
    assert_ne!(bad,s);assert!(matches!(check_receipt_cnf(&p,&bad),Err("exact Clifford weight mismatch")));
    let bad=s.replace(&format!("c p weight -{z} 1.0 0.0 0"),&format!("c p weight -{z} 0.0 1.0 0"));
    assert_ne!(bad,s);assert!(matches!(check_receipt_cnf(&p,&bad),Err("negative weight mismatch")));
    let bad=s.replace(&format!("c p weight -{z} 1.0 0.0 0\n"),"");
    assert!(matches!(check_receipt_cnf(&p,&bad),Err("CNF weight coverage")));
    let bad=s.replace("c t wmc\n",&format!("c t wmc\nc p weight {z} 0.0 1.0 0\n"));
    assert!(matches!(check_receipt_cnf(&p,&bad),Err("duplicate weight")));
    let mut p=PathSum::new(1);p.rr_tolerance=0.0;
    p.p.add_term(vec![0],PhaseCoeff::new_constant(Rational::new(1,8)));
    let (mgr,_,_)=route_encode(&p);let s=mgr.try_to_dimacs_string("gpmc").unwrap();
    let (_,e,_)=check_receipt_cnf(&p,&s).unwrap();let z=*e.phase.keys().next().unwrap();
    let bad=s.lines().map(|l|if l.starts_with(&format!("c p weight {z} ")){
        format!("c p weight {z} 1.0 0.0 0")
    }else{l.to_string()}).collect::<Vec<_>>().join("\n");
    assert!(matches!(check_receipt_cnf(&p,&bad),Err("numerical phase weight mismatch")));
    println!("CRR_CNF_SEMANTIC_CERTIFICATE models=32 fibers={fibers} weights={weights} rejected=7 exact_serialized_wmc={wmc} reference_component_error_budget=1e-80 observed_weight_tolerance=1e-65 solver_count_certified=false");
}


// Exact arithmetic on the *serialized decimal weights*, not the
// transcendental ideal weights. Two independent finite sums:
// all satisfying DIMACS assignments vs all diagonal live assignments.
#[cfg(test)]
fn receipt_mul(a:&ExactPair,b:&ExactPair)->ExactPair{
    (&a.0*&b.0-&a.1*&b.1,&a.0*&b.1+&a.1*&b.0)
}
#[cfg(test)]
fn exact_serialized_wmc(actual:&CnfReceipt)->Result<ExactPair,&'static str>{
    use num_traits::Zero;
    if actual.vars>18{return Err("bounded WMC variable cap");}
    let mut sum=(Rat::zero(),Rat::zero());
    for bits in 0usize..(1usize<<actual.vars){
        let bit=|v:i32|bits>>(v.unsigned_abs()-1)&1!=0;
        if !actual.clauses.iter().all(|r|r.iter().any(|&v|bit(v)==(v>0))){continue;}
        let mut weight=(Rat::from_integer(1.into()),Rat::zero());
        for (&lit,w) in &actual.weights{
            if bit(lit)==(lit>0){weight=receipt_mul(&weight,w);}
        }
        sum.0+=weight.0;sum.1+=weight.1;
    }
    Ok(sum)
}
#[cfg(test)]
fn exact_live_wmc(ps:&PathSum,actual:&CnfReceipt,e:&ExpectedCnf)->Result<ExactPair,&'static str>{
    use std::collections::BTreeMap;
    use num_traits::Zero;
    if e.live.len()>18{return Err("bounded live WMC variable cap");}
    let mut sum=(Rat::zero(),Rat::zero());
    for bits in 0usize..(1usize<<e.live.len()){
        let assignment:BTreeMap<_,_>=e.live.keys().enumerate().map(|(i,&v)|(v,bits>>i&1!=0)).collect();
        let monomial=|m:&Vec<u32>|m.iter().all(|v|assignment[v]);
        if !ps.f.functions.iter().enumerate().all(|(i,row)|
            (row.iter().filter(|m|monomial(m)).count()%2!=0)==assignment[&(i as u32)]){continue;}
        let mut weight=(Rat::from_integer(1.into()),Rat::zero());
        for (&z,(mono,_)) in &e.phase{
            let lit=if monomial(mono){z}else{-z};
            weight=receipt_mul(&weight,actual.weights.get(&lit).ok_or("missing live weight")?);
        }
        sum.0+=weight.0;sum.1+=weight.1;
    }
    Ok(sum)
}

// Conditional analytic input perturbation bound. Per-component error
// <= 1e-65+1e-80 implies modulus error <= 3e-65. For unit ideal
// weights, binomial expansion <= geometric series:
// (1+d)^L - 1 <= L*d/(1-L*d). Use the number of all live assignments
// as a fiber-count upper bound and round the power-of-two scaling
// upward using floor((N-k)/2). No external solver error included.
#[cfg(test)]
fn normalized_input_bound(live:usize,terms:usize,twice:i32,k:usize)->Result<Rat,&'static str>{
    use num_bigint::BigInt;
    let one=Rat::from_integer(1.into());
    let d=Rat::new(3.into(),BigInt::from(10u8).pow(65));
    let ld=d*Rat::from_integer(BigInt::from(terms));
    if ld>=one{return Err("input perturbation cap");}
    let exponent=i64::try_from(live).map_err(|_|"bound live overflow")?
        -(i64::from(twice)-i64::try_from(k).map_err(|_|"bound exponent overflow")?).div_euclid(2);
    if exponent.unsigned_abs()>100_000{return Err("bound scaling cap");}
    let pow=BigInt::from(1u8)<<(exponent.unsigned_abs() as usize);
    let scale=if exponent>=0{Rat::from_integer(pow)}else{Rat::new(1.into(),pow)};
    Ok(scale*&ld/(one-ld))
}
#[test]
fn exact_trace_weight_range_and_input_bound(){
    use quprs::rational::PhaseCoeff;
    use num_bigint::BigInt;
    use num_traits::Zero;
    let mut checks=0;
    for r in [100i64,-100,1000,-1000,10000,-10000]{
        let mut p=PathSum::new(1);p.rr_tolerance=0.0;
        let mut c=PhaseCoeff::QUARTER;c.radians=Some(Rat::new(r.into(),1.into()));
        p.p.add_term(vec![0],c);
        let (mgr,_,_)=route_encode(&p);
        let dimacs=mgr.try_to_dimacs_string("gpmc").unwrap();
        check_receipt_cnf(&p,&dimacs).unwrap();checks+=1;
    }
    let large=(Rat::zero(),Rat::from_integer(100_000.into()));
    assert_eq!(reference_weight(&large),Err("weight reference period cap"));
    for turns in [Rat::new((-1).into(),4.into()),Rat::from_integer(1.into()),
        Rat::from_integer(BigInt::from(10u8).pow(90))]{
        let bad=(turns,Rat::zero());
        assert_eq!(reference_weight(&bad),Err("weight reference noncanonical turns"));
    }
    println!("CRR_WEIGHT_REFERENCE_DOMAIN noncanonical_turns_rejected=3");
    let zero=normalized_input_bound(8,0,16,0).unwrap();assert!(zero.is_zero());
    let d=Rat::new(3.into(),BigInt::from(10u8).pow(65));
    let base=normalized_input_bound(8,1,16,0).unwrap();
    assert_eq!(base,&d/(Rat::from_integer(1.into())-&d));
    assert_eq!(normalized_input_bound(8,1,17,1).unwrap(),base);
    assert_eq!(normalized_input_bound(8,1,16,1).unwrap(),&base*Rat::from_integer(2.into()));
    assert!(normalized_input_bound(8,2,16,0).unwrap()>base);
    println!("CRR_WEIGHT_RANGE_BOUND signed_large_angles={checks} cap_rejected=1 perturbation_controls=5 solver_error_included=false");
}


// Explicit topological gate receipt. Recheck its graph and reconstruct
// clause multiset from the typed witness, independent of allocation order.
// The source binding still uses expected_receipt_cnf on the same PathSum;
// this is not yet a cross-language serialized Lean refinement.
#[cfg(test)]
fn verify_gate_receipt(actual:&CnfReceipt,e:&ExpectedCnf)->Result<(),&'static str>{
    use std::collections::{BTreeMap,BTreeSet};
    let in_range=|v:i32|v>0&&(v as usize)<=actual.vars;
    let mut seen=BTreeSet::new();
    for &v in e.live.values(){
        if !in_range(v)||!seen.insert(v){return Err("gate live mapping");}
    }
    let mut gates=BTreeMap::new();
    let mut clauses=Vec::new();
    let mut add=|mut row:Vec<i32>|{row.sort_unstable();clauses.push(row);};
    for (z,op) in &e.defs{
        if !in_range(*z)||seen.contains(z){return Err("gate output not fresh");}
        match op{
            GateOp::False=>add(vec![-*z]),
            GateOp::And(inputs)=>{
                let mut unique=BTreeSet::new();
                for &v in inputs{
                    if !seen.contains(&v)||!unique.insert(v){return Err("gate AND dependency");}
                    add(vec![-*z,v]);
                }
                let mut last=vec![*z];last.extend(inputs.iter().map(|&v|-v));add(last);
            },
            GateOp::Xor(a,b)=>{
                if !seen.contains(a)||!seen.contains(b){return Err("gate XOR dependency");}
                for x in [false,true]{for y in [false,true]{
                    let out=!(x^y);
                    add(vec![if x{-*a}else{*a},if y{-*b}else{*b},if out{-*z}else{*z}]);
                }}
            },
        }
        seen.insert(*z);gates.insert(*z,op);
    }
    if seen.len()!=actual.vars{return Err("gate domain coverage");}
    for &(a,b) in &e.equalities{
        if !seen.contains(&a)||!seen.contains(&b){return Err("gate equality dependency");}
        add(vec![-a,b]);add(vec![a,-b]);
    }
    for (&z,(mono,_)) in &e.phase{
        let expected:Option<Vec<_>>=mono.iter().map(|v|e.live.get(v).copied()).collect();
        match (gates.get(&z),expected){
            (Some(GateOp::And(inputs)),Some(expected)) if *inputs==expected=>{},
            _=>return Err("gate phase binding"),
        }
    }
    clauses.sort();
    if clauses!=actual.clauses{return Err("gate clause mismatch");}
    Ok(())
}
#[cfg(test)]
fn gate_receipt_sha(e:&ExpectedCnf)->String{
    receipt_sha(format!("crr-gates-v1|live={:?}|defs={:?}|equalities={:?}|phase={:?}",
        e.live,e.defs,e.equalities,e.phase).as_bytes())
}


// Portable research schema v1: ASCII, one record per line, explicit
// DIMACS IDs; export the exact CNF bytes separately, not reconstructed
// clauses. Lean independently parses both files. Weights remain outside
// the Boolean replay boundary (Rust numerical check retained).
#[cfg(test)]
fn portable_gate_text(e:&ExpectedCnf,vars:usize)->String{
    use std::fmt::Write;
    let mut out=format!("crr-gate-v1 {vars}\n");
    for (&v,&id) in &e.live{writeln!(&mut out,"live {v} {id}").unwrap();}
    for (z,op) in &e.defs{
        match op{
            GateOp::False=>writeln!(&mut out,"false {z}").unwrap(),
            GateOp::And(inputs)=>{
                write!(&mut out,"and {z}").unwrap();
                for v in inputs{write!(&mut out," {v}").unwrap();}
                out.push('\n');
            },
            GateOp::Xor(a,b)=>writeln!(&mut out,"xor {z} {a} {b}").unwrap(),
        }
    }
    for (a,b) in &e.equalities{writeln!(&mut out,"eq {a} {b}").unwrap();}
    for (&z,(mono,_)) in &e.phase{
        write!(&mut out,"phase {z}").unwrap();
        for v in mono{write!(&mut out," {v}").unwrap();}
        out.push('\n');
    }
    out
}
#[cfg(test)]
fn export_guard_sidecar(name:&str,ps:&PathSum){
    use std::fmt::Write as _;
    use std::io::Write as _;
    let Some(dir)=std::env::var_os("CRR_GATE_DIR")else{return;};
    assert!(name.chars().all(|c|c.is_ascii_alphanumeric()||c=='_'));
    let dir=std::path::PathBuf::from(dir).join("accept");
    let mut text=String::from("crr-guard-v1\n");
    for (i,row) in ps.f.functions.iter().enumerate(){
        write!(&mut text,"row {i}").unwrap();
        // Reverse the native iteration order to follow the final
        // XOR output back to its prefix. No gate-derived ANF here.
        let terms:Vec<_>=row.iter().collect();
        for mono in terms.into_iter().rev(){
            text.push(' ');
            if mono.is_empty(){text.push('-');}
            else{
                for (j,v) in mono.iter().enumerate(){
                    if j>0{text.push(',');}
                    write!(&mut text,"{v}").unwrap();
                }
            }
        }
        text.push('\n');
    }
    let path=dir.join(format!("{name}.gate.guard"));
    let mut f=std::fs::OpenOptions::new().create_new(true).write(true).open(path).unwrap();
    f.write_all(text.as_bytes()).unwrap();
    println!("CRR_PORTABLE_GUARD name={name} rows={} sha256={}",ps.f.functions.len(),receipt_sha(text.as_bytes()));
}
#[cfg(test)]
fn export_phase_sidecar(name:&str,e:&ExpectedCnf){
    use std::fmt::Write as _;
    use std::io::Write as _;
    let Some(dir)=std::env::var_os("CRR_GATE_DIR")else{return;};
    assert!(name.chars().all(|c|c.is_ascii_alphanumeric()||c=='_'));
    let dir=std::path::PathBuf::from(dir).join("accept");
    let mut text=String::from("crr-phase-v1\n");
    for (&z,(mono,(turns,radians))) in &e.phase{
        write!(&mut text,"coef {z} {} {} {} {}",turns.numer(),turns.denom(),
            radians.numer(),radians.denom()).unwrap();
        for v in mono{write!(&mut text," {v}").unwrap();}
        text.push('\n');
    }
    let path=dir.join(format!("{name}.gate.phase"));
    let mut f=std::fs::OpenOptions::new().create_new(true).write(true).open(path).unwrap();
    f.write_all(text.as_bytes()).unwrap();
    println!("CRR_PORTABLE_PHASE name={name} terms={} sha256={}",e.phase.len(),receipt_sha(text.as_bytes()));
}
#[cfg(test)]
fn export_portable_gate(name:&str,text:&str,cnf:&str,negative:bool){
    let Some(dir)=std::env::var_os("CRR_GATE_DIR")else{return;};
    assert!(name.chars().all(|c|c.is_ascii_alphanumeric()||c=='_'));
    let dir=std::path::PathBuf::from(dir).join(if negative{"reject"}else{"accept"});
    std::fs::create_dir_all(&dir).unwrap();
    let gate=dir.join(format!("{name}.gate"));
    let dimacs=dir.join(format!("{name}.gate.cnf"));
    // Each case/arm has a distinct name. Refuse stale/duplicate files.
    use std::io::Write;
    for (path,bytes) in [(&gate,text.as_bytes()),(&dimacs,cnf.as_bytes())]{
        let mut f=std::fs::OpenOptions::new().create_new(true).write(true).open(path).unwrap();
        f.write_all(bytes).unwrap();
    }
    println!("CRR_PORTABLE_GATE name={name} negative={negative} gate_sha256={} cnf_sha256={}",receipt_sha(text.as_bytes()),receipt_sha(cnf.as_bytes()));
}

#[test]
fn exact_trace_gate_interface(){
    use quprs::rational::PhaseCoeff;
    let mut p=PathSum::new(2);p.rr_tolerance=0.0;
    let y=p.v.get_fresh_var();p.v.get_fresh_var();
    p.p.add_term(vec![0,y],PhaseCoeff::HALF);
    p.f.functions[0].clear();p.f.functions[0].insert(vec![0,y]);p.f.functions[0].insert(vec![1]);
    p.f.functions[1].clear();
    let (mgr,_,_)=route_encode(&p);let cnf=mgr.try_to_dimacs_string("gpmc").unwrap();
    let (a,e,_)=check_receipt_cnf(&p,&cnf).unwrap();
    assert_eq!(verify_gate_receipt(&a,&e),Ok(()));
    export_portable_gate("synthetic", &portable_gate_text(&e,a.vars),&cnf,false);
    export_phase_sidecar("synthetic",&e);
    export_guard_sidecar("synthetic",&p);
    let mut bad=e.clone();bad.defs[0].0=*e.live.values().next().unwrap();
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate output not fresh"));
    export_portable_gate("duplicate_output",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut bad=e.clone();let z=bad.defs[0].0;bad.defs[0].1=GateOp::And(vec![z]);
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate AND dependency"));
    export_portable_gate("self_dependency",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut bad=e.clone();bad.defs.pop();
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate domain coverage"));
    export_portable_gate("missing_gate",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut bad=e.clone();bad.equalities.pop();
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate clause mismatch"));
    export_portable_gate("missing_equality",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut bad=e.clone();bad.phase.values_mut().next().unwrap().0=vec![1];
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate phase binding"));
    export_portable_gate("wrong_phase",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut bad=e.clone();let v=*e.live.values().next().unwrap();bad.live.insert(99,v);
    assert_eq!(verify_gate_receipt(&a,&bad),Err("gate live mapping"));
    export_portable_gate("duplicate_live",&portable_gate_text(&bad,a.vars),&cnf,true);
    let mut lines:Vec<_>=cnf.lines().map(str::to_string).collect();
    let i=lines.iter().position(|l|!l.starts_with('p')&&!l.starts_with('c')).unwrap();
    let mut row:Vec<i32>=lines[i].split_whitespace().map(|x|x.parse().unwrap()).collect();
    row[0]=-row[0];lines[i]=row.iter().map(i32::to_string).collect::<Vec<_>>().join(" ");
    export_portable_gate("wrong_clause",&portable_gate_text(&e,a.vars),&lines.join("\n"),true);
    let gate=portable_gate_text(&e,a.vars);
    let no_phase=gate.lines().filter(|line|!line.starts_with("phase ")).collect::<Vec<_>>().join("\n");
    export_portable_gate("missing_phase",&no_phase,&cnf,true);
    let weight=cnf.lines().find(|line|line.starts_with("c p weight ")&&!line.starts_with("c p weight -")).unwrap();
    let no_weight=cnf.lines().filter(|line|*line!=weight).collect::<Vec<_>>().join("\n");
    export_portable_gate("missing_positive_weight",&gate,&no_weight,true);
    let duplicate=cnf.replacen("c t wmc\n",&format!("c t wmc\n{weight}\n"),1);
    export_portable_gate("duplicate_weight",&gate,&duplicate,true);
    let negative=cnf.lines().find(|line|line.starts_with("c p weight -")).unwrap();
    let fields:Vec<_>=negative.split_whitespace().collect();
    assert_eq!(&fields[4..],&["1.0","0.0","0"]);
    let wrong=cnf.replace(negative,&format!("c p weight {} 0.0 1.0 0",fields[3]));
    export_portable_gate("wrong_negative_weight",&gate,&wrong,true);
    println!("CRR_GATE_INTERFACE_CERTIFICATE positive=1 rejected=6 digest={} cross_language_refinement=false",gate_receipt_sha(&e));
}

// Enclose normalized squared modulus using the exact serialized count
// and the conditional ideal-input error bound. No use of solver output.
// The rational upper bound on |a| uses L1 and an upward-rounded scale.
#[cfg(test)]
fn ideal_trace_squared_interval(raw:&ExactPair,twice:i32,k:usize,bound:&Rat)->(Rat,Rat){
    use num_bigint::BigInt;
    use num_traits::{Signed,Zero};
    fn pow2(exponent:i64)->Rat{
        assert!(exponent.unsigned_abs()<=100_000);
        let p=BigInt::from(1u8)<<(exponent.unsigned_abs() as usize);
        if exponent>=0{Rat::from_integer(p)}else{Rat::new(1.into(),p)}
    }
    let exponent=i64::try_from(k).unwrap()-i64::from(twice);
    let center=(&raw.0*&raw.0+&raw.1*&raw.1)*pow2(exponent);
    let norm_upper=(raw.0.abs()+raw.1.abs())*pow2(-(-exponent).div_euclid(2));
    let err=Rat::from_integer(2.into())*norm_upper*bound+bound*bound;
    ((&center-&err).max(Rat::zero()),center+err)
}
#[test]
fn exact_trace_interval_reference(){
    use num_bigint::BigInt;
    use num_traits::Zero;
    let d=Rat::new(1.into(),BigInt::from(10u8).pow(65));
    let zero=Rat::zero();let one=Rat::from_integer(1.into());let two=Rat::from_integer(2.into());
    assert_eq!(ideal_trace_squared_interval(&(two.clone(),zero.clone()),2,0,&zero),(one.clone(),one.clone()));
    let (lo,hi)=ideal_trace_squared_interval(&(one.clone(),one.clone()),2,0,&d);
    let half=Rat::new(1.into(),2.into());assert!(lo<half&&hi>half);
    let (lo,hi)=ideal_trace_squared_interval(&(zero.clone(),zero.clone()),2,0,&d);
    assert_eq!(lo,zero);assert_eq!(hi,&d*&d);
    assert_eq!(ideal_trace_squared_interval(&(one.clone(),zero.clone()),2,1,&Rat::zero()),(half.clone(),half));
    println!("CRR_INTERVAL_REFERENCE controls=4 exact_serialized_center=true input_bound_conditional=true external_solver_error_included=false");
}


// Research-only late HH split: integrate the half-phase Fourier variable,
// retain its Boolean relation instead of substituting a costly pivot.
// Original trace normalization remains fixed and raw count is restored.
fn extract_lift_integrators(ps:&PathSum,pairs:&[(u32,u32)])->(PathSum,Vec<Vec<Monomial>>){
    let mut view=ps.clone();
    let mut rows:Vec<Vec<Monomial>>=Vec::new();
    for &(u,z) in pairs{
        if !view.v.path_vars.contains(&z)||!view.get_reducible_vars().contains(&z)||
            rows.iter().flatten().any(|m|m.contains(&z)){
            println!("CRR_HANDOFF_PAIR u={u} z={z} status=not_integrator");continue;
        }
        let support:Vec<_>=view.p.terms.iter().filter(|(m,_)|m.contains(&z)).map(|(m,c)|(m.clone(),c.clone())).collect();
        if support.is_empty()||support.iter().any(|(_,c)|!c.is_pure_half()){
            println!("CRR_HANDOFF_PAIR u={u} z={z} status=not_pure_half support={}",support.len());continue;
        }
        let mut row:Poly=Poly::default();
        for (m,_) in &support{
            toggle(&mut row,m.iter().copied().filter(|&v|v!=z).collect());
        }
        // A constant zero row is just a free sum. Do not introduce a
        // Boolean variable for a tautology; still restore its factor 2.
        for (m,_) in support{view.p.terms.remove(&m);}
        assert!(view.v.path_vars.remove(&z));
        let mut row:Vec<_>=row.into_iter().collect();row.sort_unstable();
        assert!(row.iter().flatten().all(|v|view.v.path_vars.contains(v)));
        println!("CRR_HANDOFF_PAIR u={u} z={z} status=extracted guard_terms={}",row.len());
        rows.push(row);
    }
    assert_eq!(ps.v.path_vars.len(),view.v.path_vars.len()+rows.len());
    (view,rows)
}

pub(super) fn lift_trace_handoff(ps:&PathSum,pairs:&[(u32,u32)],case:&str,construct_s:f64,control:bool){
    use std::time::{Instant,Duration};
    use num_bigint::BigInt;
    use num_traits::{Signed,ToPrimitive};
    assert!(Trace::from_native(ps).is_some());
    let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
    let start=Instant::now();
    let (view,rows)=extract_lift_integrators(ps,pairs);
    let extract_s=start.elapsed().as_secs_f64();
    if control{assert_eq!(rows.len(),pairs.len());}
    let run=|arm:&str|->Option<(Count,quprs::precision_count::PrintedVerdict)>{
        let start=Instant::now();
        let (mgr,v,c,m,o)=match arm{
            "original"=>{
                let (mgr,v,c)=route_encode(ps);(mgr,v,c,0,0)
            }
            "lazy"=>{
                let (mgr,v,c,m,o,_)=lazy_prepare(ps);(mgr,v,c,m,o)
            }
            "extracted"=>{
                let mut mgr=quprs::wmc::WmcManager::new(&view);
                mgr.enable_precise_gpmc_weights(256);
                mgr.encode_trace_with_zero_constraints(&view,&rows).expect("exact guard encode");
                let dimacs=mgr.try_to_dimacs_string("gpmc").expect("serialize");
                let h:Vec<_>=dimacs.lines().find(|l|l.starts_with("p cnf ")).unwrap().split_whitespace().collect();
                (mgr,h[2].parse().unwrap(),h[3].parse().unwrap(),rows.len(),0)
            }
            _=>unreachable!()
        };
        let prep=start.elapsed().as_secs_f64()+if arm=="extracted"{extract_s}else{0.0};
        let begin=Instant::now();
        match mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(begin+Duration::from_secs(12)),90){
            Ok(raw)=>{
                let (count,verdict)=restore_count(raw,m,o,twice);
                println!("CRR_HANDOFF_CALL case={case} arm={arm} status=complete verdict={verdict:?} vars={v} clauses={c} multiplier_power={m} omega={o} twice={twice} construct_s={construct_s} prepare_s={prep} solve_s={} total_s={} real={} imag={}",begin.elapsed().as_secs_f64(),construct_s+prep+begin.elapsed().as_secs_f64(),count.real,count.imag);
                Some((count,verdict))
            }
            Err(e)=>{
                println!("CRR_HANDOFF_CALL case={case} arm={arm} status=incomplete vars={v} clauses={c} multiplier_power={m} construct_s={construct_s} prepare_s={prep} solve_s={} error={e:#}",begin.elapsed().as_secs_f64());None
            }
        }
    };
    let a=run("original");let b=run("extracted");
    let c=if control{None}else{run("lazy")};
    let scale=Rat::from_integer(BigInt::from(1u8)<<(twice as usize/2));
    let compare=|x:&Option<(Count,quprs::precision_count::PrintedVerdict)>,y:&Option<(Count,quprs::precision_count::PrintedVerdict)>,label:&str|{
        if let (Some((x,v)),Some((y,w)))=(x,y){
            let delta=((&x.real-&y.real).abs()+(&x.imag-&y.imag).abs())/&scale;
            assert!(delta<=Rat::new(BigInt::from(1u8),BigInt::from(10u8).pow(50)), "count parity {case} {label}");
            assert_eq!(v,w,"verdict parity {case} {label}");
            println!("CRR_HANDOFF_COMPARE case={case} pair={label} status=matched normalized_l1={:.5e}",delta.to_f64().unwrap_or(f64::INFINITY));
        }else{
            println!("CRR_HANDOFF_COMPARE case={case} pair={label} status=incomplete");
            assert!(!control,"mandatory control incomplete");
        }
    };
    compare(&a,&b,"original-extracted");
    if !control{compare(&a,&c,"original-lazy");compare(&b,&c,"extracted-lazy");}
}

#[test]
fn lift_trace_handoff_controls(){
    // 1q identity and Z, each represented by a balanced inverse HH.
    // Includes phase-bearing u, and nontrivial AND/XOR guard fixture.
    for (name,flip) in [("identity",false),("z",true)]{
        let mut ps=PathSum::new(1);
        let u=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
        ps.p.add_term(vec![0,z],PhaseCoeff::HALF);
        ps.p.add_term(vec![u,z],PhaseCoeff::HALF);
        if flip{ps.p.add_term(vec![u],PhaseCoeff::HALF);}
        ps.f.functions[0]=[vec![u]].into_iter().collect();
        lift_trace_handoff(&ps,&[(u,z)],name,0.0,true);
    }
    let mut ps=PathSum::new(2);
    let u=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    for m in [vec![0,z],vec![0,1,z],vec![u,z]]{ps.p.add_term(m,PhaseCoeff::HALF);}
    ps.p.add_term(vec![u],PhaseCoeff::QUARTER);
    ps.f.functions[0]=[vec![u]].into_iter().collect();
    lift_trace_handoff(&ps,&[(u,z)],"nonlinear",0.0,true);
    // Negative control: an additional quarter invalidates integration.
    ps.p.add_term(vec![z],PhaseCoeff::QUARTER);
    let (_,rows)=extract_lift_integrators(&ps,&[(u,z)]);assert!(rows.is_empty());
    println!("CRR_HANDOFF_CONTROLS count_pairs=3 rejected=1");
}


// One solver call per independently reconstructed arm. No selected
// source verdict, no fallback pretending a censored run completed.
pub(super) fn generic_trace_handoff(ps:&PathSum,pairs:&[(u32,u32)],case:&str,variant:&str,arm:&str,construct_s:f64){
    use std::time::{Instant,Duration};
    if Trace::from_native(ps).is_none()||ps.p.terms.len()+ps.f.functions.iter().map(|p|p.len()).sum::<usize>()>TERM_CAP{
        println!("CRR_GENERIC_STOP case={case} variant={variant} arm={arm} reason=residual_admission");return;
    }
    let twice=(ps.v.num_qubits+ps.v.path_vars.len()) as i32;
    let start=Instant::now();
    let (view,rows)=extract_lift_integrators(ps,pairs);
    let mut mgr=quprs::wmc::WmcManager::new(&view);
    mgr.enable_precise_gpmc_weights(256);
    mgr.encode_trace_with_zero_constraints(&view,&rows).expect("trace");
    let dimacs=mgr.try_to_dimacs_string("gpmc").expect("serialize");
    let h:Vec<_>=dimacs.lines().find(|l|l.starts_with("p cnf ")).unwrap().split_whitespace().collect();
    let (v,c)=(h[2],h[3]);let prep=start.elapsed().as_secs_f64();
    let begin=Instant::now();
    match mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(begin+Duration::from_secs(12)),90){
        Ok(raw)=>{
            let (count,verdict)=restore_count(raw,rows.len(),0,twice);
            println!("CRR_GENERIC_CALL case={case} variant={variant} arm={arm} status=complete verdict={verdict:?} vars={v} clauses={c} pairs={} extracted={} twice={twice} construct_s={construct_s} prepare_s={prep} solve_s={} total_s={} real={} imag={}",pairs.len(),rows.len(),begin.elapsed().as_secs_f64(),construct_s+prep+begin.elapsed().as_secs_f64(),count.real,count.imag);
        }
        Err(e)=>println!("CRR_GENERIC_CALL case={case} variant={variant} arm={arm} status=incomplete vars={v} clauses={c} pairs={} extracted={} twice={twice} construct_s={construct_s} prepare_s={prep} solve_s={} error={e:#}",pairs.len(),rows.len(),begin.elapsed().as_secs_f64())
    }
}
