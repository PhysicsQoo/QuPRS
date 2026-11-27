//! Private strict numeric CPR construction; explicit experimental opt-in only.
//! Frozen N5c policy, no separate gate schedule or solver.
//! Untracked Elim is fail-closed.
use crate::{PathSum, PhaseCoeff, Rational};
use crate::ir::QuantumOp;
use crate::pathsum::{Monomial,Register};
use rustc_hash::FxHashSet;
use crate::clock::Instant;
type Anf = FxHashSet<Monomial>;
pub(super) const TERM_CAP:usize=4096;
const LIFT_CAP:usize=32;
// Internal typed boundary for exact extraction/normalization failures.
#[derive(Debug)]
pub(super) struct NormalizationError;
impl std::fmt::Display for NormalizationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("CPR extraction or normalization failed")
    }
}
impl std::error::Error for NormalizationError {}

#[derive(Debug,PartialEq,Eq)]
pub(crate) enum BuildStop { Deadline, TermCap, LiftCap, UntrackedElim, Approximate, InvalidResidual }
pub(crate) struct Built {
    pub(crate) residual:PathSum,
    pub(crate) pairs:Vec<(u32,u32)>,
    pub(crate) gates_applied:usize,
}
fn terms(ps:&PathSum)->usize { ps.p.terms.len()+ps.f.functions.iter().map(|f|f.len()).sum::<usize>() }
fn incidence(ps:&PathSum)->usize { ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).map(|m|m.len()+1).sum() }
fn guard(ps:&PathSum)->Result<(),BuildStop>{
    if ps.stats.elim.successes!=0{return Err(BuildStop::UntrackedElim);}
    if ps.rr_approximate||ps.rr_tolerance!=0.0{return Err(BuildStop::Approximate);}
    Ok(())
}
pub(super) fn lift_output(ps:&mut PathSum,q:usize)->(u32,u32){
    let old=ps.f.functions[q].clone();
    let u=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    let mut cross=vec![u,z];cross.sort_unstable();
    ps.p.add_term(cross,PhaseCoeff::HALF);
    for mut m in old{
        m.push(z);m.sort_unstable();m.dedup();
        ps.p.add_term(m,PhaseCoeff::HALF);
    }
    ps.f.functions[q]=[vec![u]].into_iter().collect();
    (u,z)
}
fn lift_input(ps:&mut PathSum,x:u32)->(u32,u32){
    assert!((x as usize)<ps.v.num_qubits);
    let u=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    let rhs:Anf=[vec![u]].into_iter().collect();
    ps.p.substitute_var_with_poly(x,&rhs);
    ps.f.substitute_var_with_poly(x,&rhs);
    ps.p.add_term(vec![x,z],PhaseCoeff::HALF);
    ps.p.add_term(vec![u,z],PhaseCoeff::HALF);
    (u,z)
}

fn lift_saturate(ps:&mut PathSum)->Result<(),BuildStop>{
    guard(ps)?;
    for _ in 0..16{
        let ids=ps.get_reducible_vars();
        if ids.is_empty(){return Ok(());}
        if ps.try_reduce_elim(&ids){return Err(BuildStop::UntrackedElim);}
        let mut index=rustc_hash::FxHashMap::<u32,Vec<(&Monomial,&PhaseCoeff)>>::default();
        for (m,c) in &ps.p.terms{
            for &v in m{index.entry(v).or_default().push((m,c));}
        }
        let mut accepted=None;
        let mut local_trials=0;
        for rule in [1,2]{
            for &y in &ids{
                if local_trials>=8{break;}
                let ys=index.get(&y).cloned().unwrap_or_default();
                if ys.is_empty(){continue;}
                if rule==1{
                    if ys.len()>24||!ys.iter().any(|(m,c)|m.len()==1&&(c.is_pure_quarter()||c.is_pure_fraction(3,4)))||
                        ys.iter().any(|(m,c)|m.len()>1&&!c.is_pure_half()){continue;}
                }else{
                    if ys.len()>12||ys.iter().any(|(_,c)|!c.is_pure_half()){continue;}
                    let phi:Anf=ys.iter().map(|(m,_)|m.iter().copied().filter(|v|*v!=y).collect()).collect();
                    let Some(v)=phi.iter().filter(|m|m.len()==1&&phi.iter().all(|r|r==*m||!r.contains(&m[0]))).map(|m|m[0]).max() else{continue;};
                    if v<ps.v.num_qubits as u32||!ps.v.path_vars.contains(&v){continue;}
                    let affected=ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).filter(|m|m.contains(&v)&&!m.contains(&y)).count();
                    if affected.saturating_mul(1usize<<(phi.len()-1))>TERM_CAP{continue;}
                }
                local_trials+=1;
                let mut trial=ps.clone();
                let ok=if rule==1{trial.try_reduce_omega(&[y])}else{trial.try_reduce_hh(&[y])};
                if !ok{continue;}
                guard(&trial)?;
                let removed=if rule==1{1}else{2};
                if trial.v.path_vars.len()+removed!=ps.v.path_vars.len(){return Err(BuildStop::InvalidResidual);}
                if terms(&trial)<=TERM_CAP&&incidence(&trial)<=incidence(ps){
                    accepted=Some(trial);break;
                }
            }
            if accepted.is_some()||local_trials>=8{break;}
        }
        drop(index);
        if let Some(trial)=accepted{*ps=trial;}else{return Ok(());}
    }
    Ok(())
}
fn expansion_bound(s:usize,d:usize,cap:usize)->usize{
    let mut c=1u128;let mut sum=0u128;
    for j in 1..=s.min(d){
        c=c*(s-j+1) as u128/j as u128;
        sum+=c;if sum>=cap as u128{return cap;}
    }
    sum as usize
}
fn coeff_order(c:&PhaseCoeff,s:usize)->usize{
    if c.is_zero(){return 0;}
    let d=c.constant.denom as u64;
    if c.radians.is_some()||!c.symbols.is_empty()||!d.is_power_of_two(){s}
    else{d.trailing_zeros() as usize}
}
fn phase_gate_bound(op:&crate::ir::QuantumOp,ps:&PathSum)->Option<(usize,usize)>{
    use crate::ir::QuantumOp::*;
    let cap=1_000_000usize;
    let (q,coeffs,cross)=match op{
        RZ(q,a)|P(q,a)|U1(q,a)=>(*q,vec![(a.clone()/2).to_phase_coeff()],0),
        S(q)|SDG(q)=>(*q,vec![PhaseCoeff::QUARTER],0),
        T(q)|TDG(q)=>(*q,vec![PhaseCoeff::new_constant(Rational::new(1,8))],0),
        RX(q,_)=>(*q,vec![PhaseCoeff::QUARTER,PhaseCoeff::THREE_QUARTERS],1),
        RY(q,_)=>(*q,vec![PhaseCoeff::THREE_QUARTERS],1),
        U2(q,_,l)|U3(q,_,_,l)|U(q,_,_,l)=>(*q,vec![(l.clone()/2).to_phase_coeff(),PhaseCoeff::THREE_QUARTERS],1),
        _=>return None,
    };
    let s=ps.f.functions[q].len();
    let work=coeffs.iter().map(|c|expansion_bound(s,coeff_order(c,s),cap)).sum::<usize>().saturating_add(cross*s);
    Some((q,work))
}
fn generic_lift_trigger(op:&crate::ir::QuantumOp,ps:&PathSum,bra:bool)->bool{
    if !bra{
        return phase_gate_bound(op,ps).is_some_and(|(q,w)|w>2048&&w>8*(ps.f.functions[q].len()+2));
    }
    if let crate::ir::QuantumOp::CX(_,t)=op{
        let x=*t as u32;
        let p=ps.p.terms.keys().filter(|m|m.contains(&x)).count();
        let f=ps.f.functions.iter().flatten().filter(|m|m.contains(&x)).count();
        return terms(ps).saturating_add(2*p+f)>TERM_CAP;
    }
    false
}


 
pub(crate) fn build_difference(
    n:usize,a:&[QuantumOp],b:&[QuantumOp],deadline:Instant,
)->Result<Built,BuildStop>{
    let mut ps=PathSum::quantum_circuit(&[Register::new("q",n)],None);
    ps.rr_tolerance=0.0;
    let mut pairs=Vec::new();
    let mut active=false;
    let mut gates_applied=0usize;
    crate::strategy::visit_difference(a,b,|gate,bra|{
        if Instant::now()>=deadline{return Err(BuildStop::Deadline);}
        guard(&ps)?;
        if !active{active=generic_lift_trigger(gate,&ps,bra);}
        if !active{
            gate.apply(&mut ps,bra);
            gates_applied+=1;
            guard(&ps)?;
            if terms(&ps)>TERM_CAP{return Err(BuildStop::TermCap);}
            return Ok(());
        }
        ps.set_auto_reduce(false);
        if !bra{
            if let Some((q,w))=phase_gate_bound(gate,&ps){
                if w>2048&&w>8*(ps.f.functions[q].len()+2){
                    if pairs.len()>=LIFT_CAP{return Err(BuildStop::LiftCap);}
                    pairs.push(lift_output(&mut ps,q));
                }
            }
        }
        let rescue=bra&&pairs.len()<LIFT_CAP&&match gate{
            QuantumOp::CX(_,target)=>{
                let x=*target as u32;
                let p=ps.p.terms.keys().filter(|m|m.contains(&x)).count();
                let f=ps.f.functions.iter().flatten().filter(|m|m.contains(&x)).count();
                terms(&ps).saturating_add(2*p+f)>TERM_CAP
            }
            _=>false
        };
        let checkpoint=if rescue{Some(ps.clone())}else{None};
        gate.apply(&mut ps,bra);
        if terms(&ps)>TERM_CAP{
            if let (Some(mut trial),QuantumOp::CX(_,target))=(checkpoint,gate){
                let pair=lift_input(&mut trial,*target as u32);
                gate.apply(&mut trial,true);
                if terms(&trial)<terms(&ps)&&terms(&trial)<=TERM_CAP{
                    ps=trial;pairs.push(pair);
                }
            }
        }
        ps.set_auto_reduce(true);
        if terms(&ps)>TERM_CAP{return Err(BuildStop::TermCap);}
        lift_saturate(&mut ps)?;
        guard(&ps)?;
        if terms(&ps)>TERM_CAP{return Err(BuildStop::TermCap);}
        gates_applied+=1;
        Ok(())
    })?;
    if !active {
        ps.full_reduce();guard(&ps)?;
        ps.full_reduce();guard(&ps)?;
    }
    if Instant::now()>=deadline{return Err(BuildStop::Deadline);}
    if terms(&ps)>TERM_CAP{return Err(BuildStop::TermCap);}
    if !ps.v.continuous_vars.is_empty()||ps.p.terms.values().any(|c|!c.symbols.is_empty()){
        return Err(BuildStop::InvalidResidual);
    }
    Ok(Built{residual:ps,pairs,gates_applied})
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::VerificationStrategy;
    fn deadline()->Instant{Instant::now()+crate::clock::Duration::from_secs(15)}
    #[test]
    fn i1b_stream_and_fail_closed(){
        use QuantumOp::*;
        let a=[H(0),CX(0,1),T(1),H(0)];
        let b=[H(0),CX(0,1),S(1)];
        for (left,right) in [(&a[..],&b[..]),(&a[..],&[][..]),(&[][..],&b[..]),(&[][..],&[][..])]{
            let built=build_difference(2,left,right,deadline()).unwrap();
            let mut direct=VerificationStrategy::Difference.run(PathSum::quantum_circuit(&[Register::new("q",2)],None),left,right);
            direct.full_reduce();
            assert!(built.pairs.is_empty());
            assert_eq!(built.gates_applied,left.len()+right.len());
            assert_eq!(built.residual.p.terms,direct.p.terms);
            assert_eq!(built.residual.f.functions,direct.f.functions);
            assert_eq!(built.residual.v.path_vars,direct.v.path_vars);
        }
        let mut ps=PathSum::new(1);
        let z=ps.v.get_fresh_var();
        assert!(ps.try_reduce_elim(&[z]));
        assert_eq!(guard(&ps),Err(BuildStop::UntrackedElim));
        let mut ps=PathSum::new(1);
        let z=ps.v.get_fresh_var();
        assert_eq!(lift_saturate(&mut ps),Err(BuildStop::UntrackedElim));
        assert!(!ps.v.path_vars.contains(&z));
        assert!(matches!(build_difference(2,&a,&b,Instant::now()),Err(BuildStop::Deadline)));
        println!("CPR_I1B_STREAM_GATE no_lift=4 prefix_elim=blocked continuation_elim=blocked deadline=blocked");
    }
    #[test]
    fn i1b_frozen_heavy_construction(){
        let root=std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let cases=[
            ("qwalk-noancilla",5,"h,ry,rz,cx",7,387),
            ("qwalk-noancilla",5,"Random_Rotation",7,399),
            ("grover-noancilla",6,"h,ry,rz,cx",1,259),
            ("wstate",16,"h,ry,rz,cx",1,84),
            ("wstate",16,"Random_Rotation",1,87),
        ];
        for (family,n,folder,pairs,twice) in cases{
            let filename=format!("{family}_nativegates_ibm_qiskit_opt0_{n}.qasm");
            let dir=root.join("benchmarks/MQTBench");
            let (a,na)=crate::qasm::parse_qasm_str(&std::fs::read_to_string(dir.join(&filename)).unwrap()).unwrap();
            let (b,nb)=crate::qasm::parse_qasm_str(&std::fs::read_to_string(dir.join(folder).join(&filename)).unwrap()).unwrap();
            assert_eq!((na,nb),(n,n));
            let built=build_difference(n,&a,&b,deadline()).unwrap();
            assert_eq!(built.gates_applied,a.len()+b.len());
            assert_eq!(built.pairs.len(),pairs,"{family} {folder}");
            assert_eq!(n+built.residual.v.path_vars.len(),twice,"{family} {folder}");
            assert_eq!(built.residual.stats.elim.successes,0);
            println!("CPR_I1B_HEAVY family={family} n={n} folder={folder} pairs={pairs} twice={twice} terms={} gates={} elim=0",terms(&built.residual),built.gates_applied);
        }
        println!("CPR_I1B_HEAVY_GATE cases=5 shape_parity=true");
    }
}


// Trusted lift provenance only. Extraction does not create a new
// operator representation; the constraints belong to the terminal count.
pub(super) fn extract_terminal(ps:&PathSum,pairs:&[(u32,u32)])
    ->anyhow::Result<Option<(PathSum,Vec<Vec<Monomial>>)>>{
    guard(ps).map_err(|e|anyhow::anyhow!("CPR residual rejected: {e:?}"))?;
    let mut view=ps.clone();
    let mut rows:Vec<Vec<Monomial>>=Vec::new();
    for &(_,z) in pairs{
        if !view.v.path_vars.contains(&z)||!view.get_reducible_vars().contains(&z)||
            rows.iter().flatten().any(|m|m.contains(&z)){continue;}
        let support:Vec<_>=view.p.terms.iter().filter(|(m,_)|m.contains(&z))
            .map(|(m,c)|(m.clone(),c.clone())).collect();
        if support.is_empty()||support.iter().any(|(_,c)|!c.is_pure_half()){continue;}
        let mut row=Anf::default();
        for (m,_) in &support{
            let t:Monomial=m.iter().copied().filter(|&v|v!=z).collect();
            if !row.remove(&t){row.insert(t);}
        }
        for (m,_) in support{view.p.terms.remove(&m);}
        anyhow::ensure!(view.v.path_vars.remove(&z),"CPR absent integrator");
        let mut row:Vec<_>=row.into_iter().collect();row.sort_unstable();
        anyhow::ensure!(row.iter().flatten().all(|v|view.v.path_vars.contains(v)),"CPR dangling guard");
        rows.push(row);
    }
    anyhow::ensure!(ps.v.path_vars.len()==view.v.path_vars.len()+rows.len(),"CPR extraction cardinality");
    if rows.is_empty(){Ok(None)}else{Ok(Some((view,rows)))}
}

// Frozen N5c bounded Raw/All structure router.
#[derive(Debug,PartialEq,Eq)]
struct CprGraph { width:usize, weighted:usize, weighted_degree:usize }

fn cpr_graph(cnf:&str, deadline:crate::clock::Instant)->Option<CprGraph>{
    use std::collections::BTreeSet;
    let mut lines=cnf.lines();
    let header:Vec<_>=lines.next()?.split_whitespace().collect();
    if header.len()!=4||header[0]!="p"||header[1]!="cnf"{return None;}
    let n:usize=header[2].parse().ok()?;
    let clauses:usize=header[3].parse().ok()?;
    if n>4096||clauses>65536{return None;}
    let mut adj=vec![BTreeSet::<usize>::new();n+1];
    let mut weights=BTreeSet::new();
    let mut edges=0usize;let mut seen=0usize;
    const CAP:usize=250_000;
    for line in lines{
        if crate::clock::Instant::now()>=deadline{return None;}
        let t:Vec<_>=line.split_whitespace().collect();
        if t.is_empty(){continue;}
        if t[0]=="c"{
            if t.starts_with(&["c","p","weight"]){
                if t.len()!=7||t[6]!="0"{return None;}
                let v=t[3].parse::<i32>().ok()?.unsigned_abs() as usize;
                if v==0||v>n{return None;}
                weights.insert(v);
            }
            continue;
        }
        if t.last()!=Some(&"0"){return None;}
        seen+=1;
        let mut vs=BTreeSet::new();
        for lit in &t[..t.len()-1]{
            let v=lit.parse::<i32>().ok()?.unsigned_abs() as usize;
            if v==0||v>n{return None;}vs.insert(v);
        }
        let vs:Vec<_>=vs.into_iter().collect();
        if edges.saturating_add(vs.len().saturating_mul(vs.len().saturating_sub(1))/2)>CAP{return None;}
        for (i,&v) in vs.iter().enumerate(){
            for &u in &vs[i+1..]{
                if adj[v].insert(u){adj[u].insert(v);edges+=1;}
            }
        }
    }
    if seen!=clauses{return None;}
    let weighted=weights.len();
    let weighted_degree=weights.iter().map(|&v|adj[v].len()).sum();
    let mut queue:BTreeSet<_>=(1..=n).map(|v|(adj[v].len(),v)).collect();
    let mut width=0;
    while let Some((d,v))=queue.pop_first(){
        if crate::clock::Instant::now()>=deadline||edges.saturating_add(d.saturating_mul(d.saturating_sub(1))/2)>CAP{return None;}
        width=width.max(d);
        let ns:Vec<_>=adj[v].iter().copied().collect();
        for &u in &ns{
            if !queue.remove(&(adj[u].len(),u)){return None;}
            adj[u].remove(&v);
        }
        adj[v].clear();edges-=d;
        for (i,&u) in ns.iter().enumerate(){
            for &z in &ns[i+1..]{
                if adj[u].insert(z){adj[z].insert(u);edges+=1;}
            }
        }
        for &u in &ns{queue.insert((adj[u].len(),u));}
    }
    Some(CprGraph{width,weighted,weighted_degree})
}
fn cpr_extract_choice(raw:Option<&CprGraph>, ext:Option<&CprGraph>)->bool{
    match (raw,ext){
        (Some(r),Some(e))=>e.width<=r.width&&e.weighted<r.weighted&&e.weighted_degree<r.weighted_degree,
        _=>false
    }
}

pub(super) fn choose_extracted(raw:&str,ext:&str,deadline:Instant)->bool{
    let r=cpr_graph(raw,deadline);
    let e=cpr_graph(ext,deadline);
    cpr_extract_choice(r.as_ref(),e.as_ref())
}
