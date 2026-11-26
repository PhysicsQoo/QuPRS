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
        for x in 0..4{assert_eq!(hist(&original,x),hist(&t,x));checks+=1;}
    }
    assert!(steps>0);
    println!("CRR_TRACE_ORACLE models=512 input_hist_checks={checks} substitutions={steps}");
}
