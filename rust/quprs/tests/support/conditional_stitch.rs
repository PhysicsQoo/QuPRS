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


// Direct mixed HH/omega for the original PathSum only.
// P=P0+y*(Phi/2+C/4), Phi=v XOR A XOR C*B; C is a 2-bit monomial.
// Replace old v by A XOR C*v in P0 and outputs. The surviving v is
// phase-only padding on C=0, and a bijective reparameterization on C=1.
struct Direct {ps:PathSum, guards:[u32;2], pivot:u32, shift:Anf}
fn direct_mixed(ps:&PathSum,y:u32)->Result<Direct,&'static str>{
    if ps.rr_approximate || ps.rr_tolerance!=0.0 || !ps.v.continuous_vars.is_empty()
        || ps.p.terms.values().any(|c|!c.symbols.is_empty())
        || terms(ps)>TERM_CAP || !ps.get_reducible_vars().contains(&y){
        return Err("admission");
    }
    let ys=ps.p.extract_terms_with_var(y);
    if ys.is_empty()||ys.len()>8{return Err("integrator term cap");}
    let mut selector_mono=None;
    let mut phi=Anf::default();
    for (m,c) in ys{
        let rest:Monomial=m.iter().copied().filter(|&v|v!=y).collect();
        if c.is_pure_quarter()&&rest.len()==2&&selector_mono.is_none(){
            selector_mono=Some([rest[0],rest[1]]);
        }else if c.is_pure_half(){toggle(&mut phi,rest);}
        else{return Err("mixed coefficient pattern");}
    }
    let gs=selector_mono.ok_or("missing conditional quarter")?;
    if gs.iter().any(|g|!ps.v.path_vars.contains(g)){return Err("selector domain");}
    let v=phi.iter().filter(|m|m.len()==1)
        .filter(|m|(m[0] as usize)>=ps.v.num_qubits&&ps.v.path_vars.contains(&m[0])
            &&!gs.contains(&m[0])&&phi.iter().all(|n|n==*m||!n.contains(&m[0])))
        .map(|m|m[0]).max().ok_or("isolated pivot")?;
    phi.remove(&vec![v]);
    let mut a=Anf::default();let mut b=Anf::default();
    for m in phi{
        if gs.iter().all(|g|m.contains(g)){
            toggle(&mut b,m.into_iter().filter(|g|!gs.contains(g)).collect());
        }else{toggle(&mut a,m);}
    }
    if a.len()>3||b.len()>4{return Err("substitution cap");}
    let mut rhs=a.clone();toggle(&mut rhs,product(&gs,&[v]));
    let affected=ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).filter(|m|m.contains(&v)).count();
    if affected.saturating_mul(1usize<<rhs.len())>TERM_CAP{return Err("work cap");}
    let mut out=ps.clone();
    out.p.terms.retain(|m,_|!m.contains(&y));
    out.p.substitute_var_with_poly(v,&rhs);
    out.f.substitute_var_with_poly(v,&rhs);
    out.v.path_vars.remove(&y);
    // Both arms have common padding 1/8-v/4. On C=1 add
    // C*(3/4*(v XOR B)+v/4).
    out.p.add_term(vec![],PhaseCoeff::new_constant(Rational::new(1,8)));
    out.p.add_term(vec![v],PhaseCoeff::THREE_QUARTERS);
    toggle(&mut b,vec![v]);
    let mut extra=PhasePolynomial::new();extra+=(&b,PhaseCoeff::THREE_QUARTERS);
    extra.add_term(vec![v],PhaseCoeff::QUARTER);
    for (m,c) in extra.terms{out.p.add_term(product(&gs,&m),c);}
    if terms(&out)>TERM_CAP||out.p.terms.keys().chain(out.f.functions.iter().flatten()).flatten()
        .any(|id|!out.v.path_vars.contains(id)){return Err("result domain/cap");}
    Ok(Direct{ps:out,guards:gs,pivot:v,shift:a})
}
fn direct_record(name:&str,ps:&PathSum,y:u32,d:&Direct){
    let mut branches=Vec::new();
    for a in [false,true]{for b in [false,true]{
        let vals=[a,b];let omega=a&&b;let mut rhs=d.shift.clone();
        for (g,val) in d.guards.into_iter().zip(vals){
            let mut r=Anf::default();if val{r.insert(vec![]);}
            guard_sub(&mut rhs,ps,g,&r);
        }
        if omega{rhs.clear();}
        branches.push(format!("{{\"values\":{:?},\"rule\":{},\"pivot\":{},\"rhs\":{:?}}}",
            vals,if omega{1}else{2},if omega{"null".into()}else{d.pivot.to_string()},sorted(&rhs)));
    }}
    println!("CRR_DIRECT {{\"case\":\"{name}\",\"status\":\"candidate\",\"direct\":true,\"direct_pivot\":{},\"direct_shift\":{:?},\"y\":{y},\"guards\":{:?},\"before\":{},\"after\":{},\"branches\":[{}],\"hidden_before\":{},\"hidden_after\":{},\"terms_before\":{},\"terms_after\":{},\"incidence_before\":{},\"incidence_after\":{}}}",
        d.pivot,sorted(&d.shift),d.guards,ir(ps,None),ir(&d.ps,None),branches.join(","),
        internal(ps).len(),internal(&d.ps).len(),terms(ps),terms(&d.ps),incidence(ps),incidence(&d.ps));
}
#[test]
fn native_direct_mixed_pilot(){
    use super::conditional_trace::{route_encode,restore_count};
    use num_bigint::BigInt;
    use num_rational::BigRational as Rat;
    use num_traits::{Signed,ToPrimitive};
    use std::time::Duration;
    let mut synthetic=PathSum::new(2);
    let c=synthetic.v.get_fresh_var();let v=synthetic.v.get_fresh_var();let y=synthetic.v.get_fresh_var();
    synthetic.p.add_term(vec![y,v],PhaseCoeff::HALF);
    synthetic.p.add_term(vec![0,c,y],PhaseCoeff::QUARTER);
    synthetic.f.functions[0]=[vec![v]].into_iter().collect();
    synthetic.f.functions[1]=[vec![c],vec![1]].into_iter().collect();
    assert!((0..3).all(|r|!probe(&synthetic,y,r)));
    let direct=direct_mixed(&synthetic,y).expect("direct synthetic");
    direct_record("synthetic_original",&synthetic,y,&direct);
    let mut bad=synthetic.clone();bad.f.functions[0].insert(vec![y]);
    assert!(direct_mixed(&bad,y).is_err());
    let mut bad=synthetic.clone();bad.p.add_term(vec![y],PhaseCoeff::QUARTER);
    assert!(direct_mixed(&bad,y).is_err());
    println!("CRR_DIRECT_NEGATIVE output_dependency=reject wrong_quarter=reject");
    let source=std::env::var("CRR_SOURCE").expect("locked source");
    let target=std::env::var("CRR_TARGET").expect("locked target");
    let start=Instant::now();
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(&source).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(&target).unwrap()).unwrap();
    assert_eq!((n,m),(4,4));let parse_s=start.elapsed().as_secs_f64();
    let start=Instant::now();
    let options=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:0.0,
        timeout_secs:20,..VerificationOptions::default()};
    let result=check_equivalence_with_options(n,&a,&b,&options).unwrap();
    let rr_s=start.elapsed().as_secs_f64();
    assert!(!result.solver_invoked&&!result.rr_approximate);
    let p=result.final_pathsum();
    assert_eq!((result.equivalent(),internal(p).len(),terms(p)),("unknown",29,92));
    assert!((0..3).all(|r|!probe(p,87,r)));
    let d=direct_mixed(p,87).expect("locked target87");
    assert_eq!((d.guards,d.pivot),([3,67],103));
    direct_record("grover-noancilla_4",p,87,&d);
    println!("CRR_DIRECT_BASE {{\"parse_s\":{parse_s},\"rr_s\":{rr_s},\"hidden\":29,\"status\":\"unknown\"}}");
    for rep in 0..6{
        for k in 0..2{
            let old=(rep+k)%2==0;let start=Instant::now();
            let mut q=if old{stitch(p,None,87,[3,67]).expect("prior stitch").ps}
                else{direct_mixed(p,87).expect("direct").ps};
            let rewrite=start.elapsed().as_secs_f64();
            let start=Instant::now();q.full_reduce();let post=start.elapsed().as_secs_f64();
            assert!(!q.rr_approximate);
            println!("CRR_DIRECT_TIMING {{\"repeat\":{rep},\"arm\":\"{}\",\"rewrite_s\":{rewrite},\"post_rr_s\":{post},\"hidden\":{},\"terms\":{},\"incidence\":{},\"identity_shape\":{}}}",
                if old{"stitch"}else{"direct"},internal(&q).len(),terms(&q),incidence(&q),q.is_identity_up_to_phase());
        }
    }
    // Downstream diagnostic only: same pinned GPMC, 256-bit weights,
    // 90 printed digits and 8s deadline; reuse existing normalization.
    assert!(std::env::var_os("QUPRS_GPMC_PATH").is_some());
    let twice=(n+p.v.path_vars.len()) as i32;
    for rep in 0..2{
        let mut counts:[Option<_>;2]=[None,None];
        for k in 0..2{
            let idx=(rep+k)%2;let arm=if idx==0{"original"}else{"direct"};
            let start=Instant::now();
            let q=if idx==0{p.clone()}else{let mut q=direct_mixed(p,87).unwrap().ps;q.full_reduce();q};
            let rewrite=start.elapsed().as_secs_f64();
            assert!(!q.rr_approximate);
            let removed=p.v.path_vars.len()-q.v.path_vars.len();
            let start=Instant::now();let (mgr,vars,clauses)=route_encode(&q);let encode=start.elapsed().as_secs_f64();
            let start=Instant::now();
            let raw=mgr.solve_with_deadline_distance_printed_precision("gpmc",Some(start+Duration::from_secs(8)),90);
            let solve=start.elapsed().as_secs_f64();
            match raw{
                Ok(c)=>{
                    let (count,verdict)=restore_count(c,0,removed,twice);
                    println!("CRR_DIRECT_WMC {{\"repeat\":{rep},\"arm\":\"{arm}\",\"status\":\"complete\",\"verdict\":\"{:?}\",\"vars\":{vars},\"clauses\":{clauses},\"rewrite_s\":{rewrite},\"encode_s\":{encode},\"solve_s\":{solve},\"post_rr_total_s\":{},\"shared_prefix_total_s\":{},\"normalization_twice\":{twice},\"removed\":{removed}}}",
                        verdict,rewrite+encode+solve,parse_s+rr_s+rewrite+encode+solve);
                    counts[idx]=Some((count,verdict));
                }
                Err(e)=>{println!("CRR_DIRECT_WMC_ERROR {arm} {e:#}");
                    println!("CRR_DIRECT_WMC {{\"repeat\":{rep},\"arm\":\"{arm}\",\"status\":\"incomplete\",\"vars\":{vars},\"clauses\":{clauses},\"rewrite_s\":{rewrite},\"encode_s\":{encode},\"solve_s\":{solve}}}");}
            }
        }
        if let [Some((a,va)),Some((b,vb))]=counts{
            assert_eq!(std::mem::discriminant(&va),std::mem::discriminant(&vb));
            let scale=Rat::from_integer(BigInt::from(1u8)<<(twice as usize/2));
            let delta=((&a.real-&b.real).abs()+(&a.imag-&b.imag).abs())/scale;
            assert!(delta<=Rat::new(BigInt::from(1u8),BigInt::from(10u8).pow(50)));
            println!("CRR_DIRECT_PARITY {{\"repeat\":{rep},\"status\":\"matched\",\"normalized_l1_delta\":{:.5e}}}",delta.to_f64().unwrap_or(f64::INFINITY));
        }else{println!("CRR_DIRECT_PARITY {{\"repeat\":{rep},\"status\":\"incomplete\"}}");}
    }
}


// Known SOP remainder principle: summing an output-independent half-phase
// integrator annihilates Phi=1.  Keep its exact phase and domain intact.
// Simplify the other arithmetic and Boolean monomials on Phi=0 only.
// A bounded local support signature avoids Groebner basis/guard search.
fn remainder_trial(ps:&PathSum,y:u32)->Option<PathSum>{
    let ys=ps.p.extract_terms_with_var(y);
    if ys.is_empty()||ys.len()>8||ys.iter().any(|(_,c)|!c.is_pure_half()){return None;}
    let phi:Anf=ys.iter().map(|(m,_)|m.iter().copied().filter(|&v|v!=y).collect()).collect();
    let mut scope:Vec<u32>=phi.iter().flatten().copied().collect();scope.sort_unstable();scope.dedup();
    if scope.len()<2||scope.len()>6{return None;}
    let size=1usize<<scope.len();
    let mask=|m:&[u32]|->usize{m.iter().filter_map(|v|scope.binary_search(v).ok()).fold(0,|a,i|a|(1<<i))};
    let masks:Vec<_>=phi.iter().map(|m|mask(m)).collect();
    let allowed:Vec<_>=(0..size).filter(|k|masks.iter().filter(|m|k&**m==**m).count()%2==0).collect();
    if allowed.is_empty(){return None;}
    let sig=|m:usize|->u64{allowed.iter().enumerate().fold(0,|a,(j,k)|if k&m==m{a|(1u64<<j)}else{a})};
    let mut reps=std::collections::BTreeMap::<u64,usize>::new();
    let mut order:Vec<_>=(0..size).collect();order.sort_by_key(|m|(m.count_ones(),*m));
    for m in order{reps.entry(sig(m)).or_insert(m);}
    let rep=|m:&[u32]|->Option<Monomial>{
        let s=sig(mask(m));if s==0{return None;}
        let k=reps[&s];
        let mut result:Monomial=m.iter().copied().filter(|v|scope.binary_search(v).is_err()).collect();
        result.extend(scope.iter().enumerate().filter(|(i,_)|k&(1<<i)!=0).map(|(_,v)|*v));
        result.sort_unstable();Some(result)
    };
    let mut out=ps.clone();out.p=PhasePolynomial::new();
    for(m,c)in &ps.p.terms{
        if m.contains(&y){out.p.add_term(m.clone(),c.clone());}
        else if let Some(n)=rep(m){out.p.add_term(n,c.clone());}
    }
    for(dst,src)in out.f.functions.iter_mut().zip(&ps.f.functions){
        dst.clear();for m in src{if let Some(n)=rep(m){toggle(dst,n);}}
    }
    if incidence(&out)<incidence(ps)&&terms(&out)<=TERM_CAP{Some(out)}else{None}
}
#[test]
fn native_original_rr_cohort(){
    let case=std::env::var("CRR_CASE").expect("case");
    let source=std::env::var("CRR_SOURCE").expect("source");
    let target=std::env::var("CRR_TARGET").expect("target");
    let t=Instant::now();
    let(a,n)=parse_qasm_str(&std::fs::read_to_string(source).unwrap()).unwrap();
    let(b,m)=parse_qasm_str(&std::fs::read_to_string(target).unwrap()).unwrap();
    assert_eq!(n,m);
    let parse=t.elapsed().as_secs_f64();let t=Instant::now();
    let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
    let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
    let rr=t.elapsed().as_secs_f64();
    let p=r.final_pathsum();
    assert!(!r.solver_invoked);
    let status=r.equivalent();
    if r.rr_approximate||!p.v.continuous_vars.is_empty()||p.p.terms.values().any(|c|!c.symbols.is_empty())||terms(p)>TERM_CAP||matches!(status,"timeout"|"memory_out"){
        println!("CRR_COHORT {{\"case\":\"{}\",\"status\":\"not_admitted\"}}",case);
        return;
    }
    let t=Instant::now();
    let ids=p.get_reducible_vars();
    let mut direct=0;let mut rem=0;let mut useful=0;let mut tested=0;
    let mut best:Option<(u32,PathSum)>=None;
    // Existing source-locked cohort, target-local support only. Limit
    // scans to 96 targets; no guard assignments, no solver, no extra IR.
    for &y in ids.iter().take(96){
        tested+=1;
        if let Ok(d)=direct_mixed(p,y){
            direct+=1;
            direct_record(&case,p,y,&d);
            let mut q=d.ps.clone();q.full_reduce();
            if incidence(&q)<incidence(p)||internal(&q).len()+1<internal(p).len(){useful+=1;}
            println!("CRR_COHORT_DIRECT {{\"case\":\"{case}\",\"target\":{y},\"post_hidden\":{},\"post_incidence\":{},\"identity_shape\":{}}}",internal(&q).len(),incidence(&q),q.is_identity_up_to_phase());
        }
        if let Some(q)=remainder_trial(p,y){
            rem+=1;
            if best.as_ref().is_none_or(|(_,old)|incidence(&q)<incidence(old)){best=Some((y,q));}
        }
    }
    let mut h=internal(p).len();let mut cost=incidence(p);let mut identity=false;
    if let Some((y,mut q))=best{
        println!("CRR_REMAINDER {{\"case\":\"{case}\",\"y\":{y},\"before\":{},\"after\":{}}}",ir(p,None),ir(&q,None));
        q.full_reduce();h=internal(&q).len();cost=incidence(&q);identity=q.is_identity_up_to_phase()&&h==0;
    }
    println!("CRR_COHORT {{\"case\":\"{case}\",\"status\":\"complete\",\"native\":\"{status}\",\"eligible\":{},\"tested\":{tested},\"direct\":{direct},\"direct_useful\":{useful},\"remainder\":{rem},\"hidden_before\":{},\"hidden_after_rem\":{h},\"incidence_before\":{},\"incidence_after_rem\":{cost},\"identity_after_rem\":{identity},\"parse_s\":{parse},\"rr_s\":{rr},\"scan_s\":{}}}",
        ids.len(),internal(p).len(),incidence(p),t.elapsed().as_secs_f64());
}


// Vilmart ket-style coordinate normalization, adapted to original input
// labels. A singleton internal pivot in f_i=v XOR R is replaced by
// v XOR R in P and all f; this is an involution, no scale change.
// Try only if it exposes an original reduction, never enumerate guards.
#[test]
fn native_output_coordinate_cohort(){
    let case=std::env::var("CRR_CASE").expect("case");
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();
    assert_eq!(n,m);
    let t=Instant::now();
    let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
    let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
    let rr=t.elapsed().as_secs_f64();let p=r.final_pathsum();assert!(!r.solver_invoked);
    if r.rr_approximate||!p.v.continuous_vars.is_empty()||p.p.terms.values().any(|c|!c.symbols.is_empty())||terms(p)>TERM_CAP||matches!(r.equivalent(),"timeout"|"memory_out"){
        println!("CRR_KET {{\"case\":\"{case}\",\"status\":\"not_admitted\"}}");return;
    }
    println!("CRR_KET_RESIDUAL {{\"case\":\"{case}\",\"native\":\"{}\",\"ir\":{}}}",r.equivalent(),ir(p,None));
    let start=Instant::now();let mut probes=0;let mut exposed=0;let mut accepted=0;let mut cap_reject=0;
    let orig_candidates:FxHashSet<_>=p.get_reducible_vars().into_iter().collect();
    let mut best:Option<(usize,u32,Anf,PathSum,usize,usize)>=None;
    'output:for(i,f)in p.f.functions.iter().enumerate(){
        if f.len()<2||f.len()>5{continue;}
        let mut pivots:Vec<_>=f.iter().filter(|m|m.len()==1).map(|m|m[0])
            .filter(|v|(*v as usize)>=n&&p.v.path_vars.contains(v)&&f.iter().all(|m|m==&vec![*v]||!m.contains(v))).collect();
        pivots.sort_unstable();
        for v in pivots{
            if probes>=32{break 'output;}probes+=1;
            let affected=p.p.terms.keys().chain(p.f.functions.iter().flatten()).filter(|m|m.contains(&v)).count();
            if affected.saturating_mul(1usize<<f.len())>TERM_CAP{cap_reject+=1;continue;}
            let mut q=p.clone();
            q.p.substitute_var_with_poly(v,f);
            q.f.substitute_var_with_poly(v,f);
            assert_eq!(q.f.functions[i],[vec![v]].into_iter().collect::<Anf>());
            assert_eq!(q.v.path_vars,p.v.path_vars);
            if terms(&q)>TERM_CAP{cap_reject+=1;continue;}
            let unlocked=q.get_reducible_vars().into_iter().filter(|y|!orig_candidates.contains(y)).count();
            if unlocked==0{continue;}exposed+=1;
            let mut reduced=q.clone();reduced.full_reduce();
            if reduced.rr_approximate||internal(&reduced).len()>=internal(p).len(){continue;}
            accepted+=1;
            let h=internal(&reduced).len();let cost=incidence(&reduced);
            if best.as_ref().is_none_or(|(_,_,_,_,oldh,oldcost)|(h,cost)<(*oldh,*oldcost)){
                best=Some((i,v,f.clone(),q,h,cost));
            }
        }
    }
    let mut after_h=internal(p).len();let mut after_cost=incidence(p);
    if let Some((i,v,rhs,q,h,cost))=best{
        println!("CRR_KET_REWRITE {{\"case\":\"{case}\",\"output\":{i},\"pivot\":{v},\"rhs\":{:?},\"before\":{},\"after\":{}}}",sorted(&rhs),ir(p,None),ir(&q,None));
        after_h=h;after_cost=cost;
    }
    println!("CRR_KET {{\"case\":\"{case}\",\"status\":\"complete\",\"native\":\"{}\",\"probes\":{probes},\"exposed\":{exposed},\"accepted\":{accepted},\"cap_reject\":{cap_reject},\"hidden_before\":{},\"hidden_after\":{after_h},\"incidence_before\":{},\"incidence_after\":{after_cost},\"rr_s\":{rr},\"scan_s\":{}}}",r.equivalent(),internal(p).len(),incidence(p),start.elapsed().as_secs_f64());
}

// Compare the already recorded exact-fixpoint cohort against the
// existing per-request RR default. No new rule or tolerance change.
#[test]
fn native_default_rr_baseline(){
    let case=std::env::var("CRR_CASE").expect("case");
    let start=Instant::now();
    let(a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let(b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();
    assert_eq!(n,m);let parse_s=start.elapsed().as_secs_f64();
    let opts=VerificationOptions{method:VerificationMethod::ReductionRules,timeout_secs:20,..VerificationOptions::default()};
    assert_eq!(opts.rr_tolerance,1e-10);
    let start=Instant::now();
    let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
    let rr_s=start.elapsed().as_secs_f64();let p=r.final_pathsum();
    assert!(!r.solver_invoked);
    println!("CRR_DEFAULT_RR {{\"case\":\"{case}\",\"native\":\"{}\",\"approximate\":{},\"hidden\":{},\"incidence\":{},\"terms\":{},\"parse_s\":{parse_s},\"rr_s\":{rr_s},\"tolerance\":{},\"ir\":{}}}",r.equivalent(),r.rr_approximate,internal(p).len(),incidence(p),terms(p),opts.rr_tolerance,ir(p,None));
}
