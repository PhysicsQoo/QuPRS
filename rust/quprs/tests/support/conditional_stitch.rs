//! Bounded mixed-rule pilot. The production PathSum and RR API are unchanged.
use super::{internal, probe, restrict, terms, TERM_CAP};
use quprs::{PathSum, PhaseCoeff, Rational, VerificationMethod, VerificationOptions};
use quprs::{check_equivalence_with_options, qasm::parse_qasm_str};
use quprs::pathsum::{BooleanState, Monomial, PhasePolynomial};
use rustc_hash::FxHashSet;
use std::time::Instant;

type Anf = FxHashSet<Monomial>;
const BRANCH_CAP: usize = 4096;

fn toggle(poly: &mut Anf, mono: Monomial) {
    if !poly.remove(&mono) { poly.insert(mono); }
}
fn product(a: &[u32], b: &[u32]) -> Monomial {
    let mut m = a.to_vec();
    m.extend_from_slice(b);
    m.sort_unstable(); m.dedup(); m
}
fn selector(guards: [u32; 2], values: [bool; 2]) -> Vec<(Monomial, i64)> {
    let mut out = vec![(vec![],1)];
    for (g, val) in guards.into_iter().zip(values) {
        let next: Vec<_> = out.iter().map(|(m,c)| (product(m,&[g]), if val {*c} else {-*c})).collect();
        if val {out=next;} else {out.extend(next);}
    }
    out
}
fn guard_sub(g: &mut Anf, ps: &PathSum, v: u32, rhs: &Anf) {
    let mut f = BooleanState {functions: vec![g.clone()], registers: ps.f.registers.clone()};
    f.substitute_var_with_poly(v,rhs);
    *g = f.functions.pop().unwrap();
}
#[derive(Clone)]
struct Branch {
    values: [bool;2],
    rule: usize,
    pivot: Option<u32>,
    rhs: Anf,
    terms: usize,
}
struct Candidate {
    ps: PathSum,
    guard: Option<Anf>,
    branches: Vec<Branch>,
}
fn stitch(ps: &PathSum, guard: Option<&Anf>, y: u32, gs: [u32;2]) -> Result<Candidate,&'static str> {
    if ps.rr_approximate || ps.rr_tolerance != 0.0 || !ps.v.continuous_vars.is_empty()
        || ps.p.terms.values().any(|c|!c.symbols.is_empty())
        || terms(ps)>TERM_CAP || gs[0]==gs[1] || gs.contains(&y)
        || !ps.v.path_vars.contains(&y) || (y as usize)<ps.v.num_qubits
        || gs.iter().any(|v|!ps.v.path_vars.contains(v))
        || guard.is_some_and(|g|g.len()>BRANCH_CAP || g.iter().flatten().any(|v|!ps.v.path_vars.contains(v))) {
        return Err("admission");
    }
    // Preserve each guard coordinate (including any original input).
    let mut out = ps.clone();
    out.v.path_vars.remove(&y);
    out.p = PhasePolynomial::new();
    out.f.functions.iter_mut().for_each(|f|f.clear());
    let mut out_guard = guard.map(|_|Anf::default());
    let mut branches = Vec::new();
    for a in [false,true] { for b in [false,true] {
        let values=[a,b];
        let mut q=restrict(&restrict(ps,gs[0],a),gs[1],b);
        let mut g=guard.cloned();
        if let Some(ref mut g)=g {
            for (v,val) in gs.into_iter().zip(values) {
                let mut rhs=Anf::default(); if val {rhs.insert(vec![]);}
                guard_sub(g,ps,v,&rhs);
            }
            if g.iter().any(|m|m.contains(&y)) {return Err("guard depends on integrator");}
        }
        let rule=if probe(&q,y,1){1}else if probe(&q,y,2){2}else{return Err("uncovered branch");};
        let before=q.v.path_vars.clone();
        let mut rhs=Anf::default();
        let pivot=if rule==2 {
            let phi: Anf=q.p.terms.iter().filter(|(m,_)|m.contains(&y)).map(|(m,_)|
                m.iter().copied().filter(|v|*v!=y).collect()).collect();
            let v=phi.iter().filter(|m|m.len()==1).filter(|m|phi.iter().all(|n|n==*m||!n.contains(&m[0])))
                .map(|m|m[0]).max().ok_or("HH pivot")?;
            if gs.contains(&v)||v==y||(v as usize)<ps.v.num_qubits {return Err("guard/input pivot");}
            rhs=phi; rhs.remove(&vec![v]);
            if let Some(ref mut g)=g {guard_sub(g,ps,v,&rhs);}
            Some(v)
        }else{None};
        let applied=if rule==1{q.try_reduce_omega(&[y])}else{q.try_reduce_hh(&[y])};
        if !applied || q.rr_approximate {return Err("native rewrite");}
        let mut expected=before; expected.remove(&y);
        if let Some(v)=pivot {expected.remove(&v);}
        if q.v.path_vars!=expected{return Err("native domain");}
        if let Some(v)=pivot {
            // Reuse the removed pivot slot as an independent phase-only bit.
            q.v.path_vars.insert(v);
            q.p.add_term(vec![v],PhaseCoeff::QUARTER);
            q.p.add_term(vec![],PhaseCoeff::new_constant(Rational::new(-1,8)));
        }
        // Internal branch guard coordinates are restored by the selector.
        for v in gs {q.v.path_vars.insert(v);}
        if q.v.path_vars!=out.v.path_vars || terms(&q)>BRANCH_CAP {return Err("balanced domain/cap");}
        let sel=selector(gs,values);
        for (m,c) in &q.p.terms {for (sm,sign) in &sel {
            out.p.add_term(product(m,sm),c.clone()* *sign);
        }}
        for (dst,src) in out.f.functions.iter_mut().zip(&q.f.functions) {
            for m in src {for (sm,_) in &sel {toggle(dst,product(m,sm));}}
        }
        if let (Some(dst),Some(src))=(&mut out_guard,&g) {
            for m in src {for (sm,_) in &sel {toggle(dst,product(m,sm));}}
        }
        if terms(&out)>TERM_CAP || out_guard.as_ref().is_some_and(|g|g.len()>BRANCH_CAP) {
            return Err("stitch term cap");
        }
        branches.push(Branch{values,rule,pivot,rhs,terms:terms(&q)});
    }}
    if !branches.iter().any(|b|b.rule==1)||!branches.iter().any(|b|b.rule==2){return Err("not mixed");}
    if out.p.terms.keys().chain(out.f.functions.iter().flatten()).flatten().any(|v|!out.v.path_vars.contains(v))
        || out_guard.as_ref().is_some_and(|g|g.iter().flatten().any(|v|!out.v.path_vars.contains(v))){
        return Err("dead coordinate");
    }
    Ok(Candidate{ps:out,guard:out_guard,branches})
}
fn sorted(poly:&Anf)->Vec<Monomial>{
    let mut rows:Vec<_>=poly.iter().cloned().collect();rows.sort();rows
}
fn ir(ps:&PathSum, g:Option<&Anf>)->String {
    let mut live:Vec<_>=ps.v.path_vars.iter().copied().collect();live.sort_unstable();
    let mut p:Vec<_>=ps.p.terms.iter().collect();p.sort_by(|a,b|a.0.cmp(b.0));
    let rows:Vec<_>=p.iter().map(|(m,c)|format!("[{:?},\"{}\",\"{}\"]",m,c.constant,
        c.radians.as_ref().map(|r|r.to_string()).unwrap_or_else(||"0".into()))).collect();
    let outputs:Vec<_>=ps.f.functions.iter().map(sorted).collect();
    let guard=g.map(|g|format!("{:?}",sorted(g))).unwrap_or_else(||"null".into());
    format!("{{\"n\":{},\"live\":{:?},\"phase\":[{}],\"outputs\":{:?},\"guard\":{guard}}}",
        ps.v.num_qubits,live,rows.join(","),outputs)
}
fn incidence(ps:&PathSum)->usize{
    ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).map(|m|m.len()+1).sum()
}
fn report(name:&str, ps:&PathSum,g:Option<&Anf>,y:u32,gs:[u32;2]){
    let start=Instant::now();
    match stitch(ps,g,y,gs) {
        Ok(c)=>{
            let elapsed=start.elapsed().as_secs_f64();
            let branches:Vec<_>=c.branches.iter().map(|b|format!(
                "{{\"values\":{:?},\"rule\":{},\"pivot\":{},\"rhs\":{:?},\"terms\":{}}}",
                b.values,b.rule,b.pivot.map(|v|v.to_string()).unwrap_or_else(||"null".into()),
                sorted(&b.rhs),b.terms)).collect();
            let mut reduced=c.ps.clone();
            let t=Instant::now();
            // Only the original unconstrained pathsum may invoke normal RR.
            if g.is_none(){reduced.full_reduce();}
            let rr=t.elapsed().as_secs_f64();
            println!("CRR_STITCH {{\"case\":\"{name}\",\"status\":\"candidate\",\"y\":{y},\"guards\":{:?},\"before\":{},\"after\":{},\"branches\":[{}],\"hidden_before\":{},\"hidden_after\":{},\"terms_before\":{},\"terms_after\":{},\"incidence_before\":{},\"incidence_after\":{},\"stitch_s\":{elapsed},\"post_rr_s\":{rr},\"post_rr_hidden\":{},\"post_rr_terms\":{},\"post_rr_identity_shape\":{}}}",
                gs,ir(ps,g),ir(&c.ps,c.guard.as_ref()),branches.join(","),internal(ps).len(),internal(&c.ps).len(),terms(ps),terms(&c.ps),incidence(ps),incidence(&c.ps),internal(&reduced).len(),terms(&reduced),reduced.is_identity_up_to_phase());
        }
        Err(reason)=>println!("CRR_STITCH {{\"case\":\"{name}\",\"status\":\"rejected\",\"reason\":\"{reason}\"}}")
    }
}
#[test]
fn native_mixed_stitch_pilot(){
    let mut ps=PathSum::new(2);
    let c=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();let y=ps.v.get_fresh_var();
    ps.p.add_term(vec![y,z],PhaseCoeff::HALF);
    ps.p.add_term(vec![0,c,y],PhaseCoeff::QUARTER);
    ps.f.functions[0]=[vec![z]].into_iter().collect();
    ps.f.functions[1]=[vec![c],vec![1]].into_iter().collect();
    assert!((0..3).all(|r|!probe(&ps,y,r)));
    let g:Anf=[vec![0],vec![z]].into_iter().collect();
    report("synthetic_original",&ps,None,y,[0,c]);
    report("synthetic_guarded",&ps,Some(&g),y,[0,c]);
    let bad:Anf=[vec![y]].into_iter().collect();
    assert_eq!(stitch(&ps,Some(&bad),y,[0,c]).err(),Some("guard depends on integrator"));
    assert_eq!(stitch(&ps,None,y,[y,c]).err(),Some("admission"));
    println!("CRR_STITCH_NEGATIVE guard_integrator=reject guard_target=reject");
    let source=std::env::var("CRR_SOURCE").expect("source-locked Grover fixture");
    let target=std::env::var("CRR_TARGET").expect("source-locked Grover target");
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(source).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(target).unwrap()).unwrap();
    assert_eq!((n,m),(4,4));
    let options=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:0.0,
        timeout_secs:20,..VerificationOptions::default()};
    let result=check_equivalence_with_options(n,&a,&b,&options).unwrap();
    assert!(!result.solver_invoked && !result.rr_approximate);
    let p=result.final_pathsum();
    println!("CRR_STITCH_BASE status={} hidden={} terms={} rr_s={}",result.equivalent(),internal(p).len(),terms(p),result.verification_time);
    // Historical receipt coordinates are admitted only on the pinned shape.
    if result.equivalent()!="unknown" || internal(p).len()!=29 || terms(p)!=92 ||
        (0..3).any(|r|probe(p,87,r)) {
        println!("CRR_STITCH {{\"case\":\"grover-noancilla_4\",\"status\":\"rejected\",\"reason\":\"historical residual shape or fixpoint mismatch\"}}");
        return;
    }
    report("grover-noancilla_4",p,None,87,[3,67]);
}
