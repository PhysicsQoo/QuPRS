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


// One bounded, source-locked Grover candidate identified by the exact
// Walsh-kernel receipt audit. No general search or production change.
// Run the existing HH primitive, including its deterministic max pivot.
#[test]
fn native_walsh_hh_pilot(){
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();
    assert_eq!((n,m),(4,4));
    for (policy,tolerance,expected_inc) in [("strict",0.0,263usize),("default",1e-10,235usize)]{
        let t=Instant::now();
        let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:tolerance,timeout_secs:20,..VerificationOptions::default()};
        let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
        let baseline_s=t.elapsed().as_secs_f64();let p=r.final_pathsum();
        assert!(!r.solver_invoked&&!r.rr_approximate);
        assert_eq!((r.equivalent(),internal(p).len(),incidence(p)),("unknown",29,expected_inc));
        assert!(p.v.continuous_vars.is_empty()&&p.p.terms.values().all(|c|c.symbols.is_empty()));
        let inherited=p.rr_approximate;
        if policy=="strict"{assert!(!inherited);}
        let start=Instant::now();let mut q=p.clone();
        // Exact trial even on the default-prefix residual. Restore neither
        // near-grid snapping nor approximate matches during the added pass.
        q.rr_tolerance=0.0;
        let y=103u32;
        assert!([91,93,103,111,62,110].iter().all(|v|p.get_reducible_vars().contains(v)));
        for v in [91u32,93,111]{
            let rhs:Anf=[vec![v],vec![y]].into_iter().collect();
            q.p.substitute_var_with_poly(v,&rhs);
            q.f.substitute_var_with_poly(v,&rhs);
            assert!(terms(&q)<=TERM_CAP);
        }
        assert_eq!(q.v.path_vars,p.v.path_vars);
        assert_eq!(q.f.functions,p.f.functions);
        let reparam_s=start.elapsed().as_secs_f64();
        let dep=q.p.extract_terms_with_var(y);
        assert!(!dep.is_empty()&&dep.iter().all(|(_,c)|c.is_pure_half()));
        let phi:Anf=dep.iter().map(|(m,_)|m.iter().copied().filter(|v|*v!=y).collect()).collect();
        let v=phi.iter().filter(|m|m.len()==1&&phi.iter().all(|n|n==*m||!n.contains(&m[0]))).map(|m|m[0]).max().unwrap();
        assert_eq!(v,110);
        let rhs:Anf=phi.into_iter().filter(|m|m!=&vec![v]).collect();
        assert!(rhs.len()<=8);
        let affected=q.p.terms.keys().chain(q.f.functions.iter().flatten()).filter(|m|m.contains(&v)).count();
        assert!(affected.saturating_mul(1usize<<rhs.len())<=TERM_CAP);
        let transformed=q.clone();
        let start=Instant::now();assert!(q.try_reduce_hh(&[y]));let hh_s=start.elapsed().as_secs_f64();
        let mut live=p.v.path_vars.clone();live.remove(&y);live.remove(&v);
        assert_eq!(q.v.path_vars,live);assert_eq!(q.rr_approximate,inherited);
        assert!(terms(&q)<=TERM_CAP);
        println!("CRR_WALSH_HH {{\"policy\":\"{policy}\",\"y\":{y},\"pivot\":{v},\"shift\":[91,93,111],\"rhs\":{:?},\"before\":{},\"transformed\":{},\"after\":{},\"scale_exponent_delta\":-2,\"inherited_rr_approximate\":{inherited},\"after_rr_approximate\":{}}}",sorted(&rhs),ir(p,None),ir(&transformed,None),ir(&q,None),q.rr_approximate);
        let hh_inc=incidence(&q);
        let start=Instant::now();q.full_reduce();let post_s=start.elapsed().as_secs_f64();
        assert_eq!(q.rr_approximate,inherited);
        let h=internal(&q).len();let inc=incidence(&q);
        let identity=h==0&&q.is_identity_up_to_phase();
        let useful=identity||(h<29&&inc<expected_inc);
        println!("CRR_WALSH_RESULT {{\"policy\":\"{policy}\",\"baseline_s\":{baseline_s},\"reparam_s\":{reparam_s},\"hh_s\":{hh_s},\"post_rr_s\":{post_s},\"before_hidden\":29,\"hh_hidden\":27,\"post_hidden\":{h},\"before_incidence\":{expected_inc},\"hh_incidence\":{hh_inc},\"post_incidence\":{inc},\"identity_shape\":{identity},\"structurally_useful\":{useful},\"production_admitted\":false,\"inherited_rr_approximate\":{inherited},\"post_rr_approximate\":{},\"post\":{}}}",q.rr_approximate,ir(&q,None));
    }
}


// Known exact single-wire rotation algebra, not a new conditional RR.
// Measure this separately to isolate any subsequent algorithmic contribution.
fn early_rotation_lower(ops:&[quprs::ir::QuantumOp])->(Vec<quprs::ir::QuantumOp>,usize){
    use quprs::{ir::QuantumOp::*,rational::Angle};
    let half=Angle::from_qasm_str("pi/2").unwrap();
    let three=Angle::from_qasm_str("3*pi").unwrap();
    let pi=Angle::from_qasm_str("pi").unwrap();
    let mut result=Vec::with_capacity(ops.len());let mut i=0;let mut hits=0;
    while i<ops.len(){
        if let Some([RZ(q,z),RX(a,x),RZ(b,theta),RX(c,y),RZ(d,end)])=ops.get(i..i+5){
            if q==a&&q==b&&q==c&&q==d&&z==&Angle::ZERO&&x==&half&&y==&half&&end==&three&&theta.symbols.is_empty(){
                result.push(RY(*q,theta.clone()-pi.clone()));hits+=1;i+=5;continue;
            }
        }
        result.push(ops[i].clone());i+=1;
    }
    (result,hits)
}
#[test]
fn native_early_rotation_pilot(){
    let case=std::env::var("CRR_CASE").unwrap();
    let variant=std::env::var("CRR_VARIANT").unwrap();
    let source=std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap();
    let target=std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap();
    let expected=match case.as_str(){"qnn_4"=>8,"vqe_4"=>12,_=>panic!("scope")};
    // Six order-balanced pairs per policy, same parsed input and native RR.
    // Time includes parse, candidate scan and verification; excludes file IO.
    for (policy,tolerance) in [("strict",0.0),("default",1e-10)]{
        for rep in 0..6{
            for k in 0..2{
                let lower=(rep+k)%2==1;
                let start=Instant::now();
                let(a,n)=parse_qasm_str(&source).unwrap();let(b,m)=parse_qasm_str(&target).unwrap();
                assert_eq!((n,m),(4,4));let before=a.len();
                let parse_s=start.elapsed().as_secs_f64();
                let tick=Instant::now();
                let (a,hits)=if lower{early_rotation_lower(&a)}else{(a,0)};
                if lower{assert_eq!(hits,expected);assert_eq!(a.len(),before-4*expected);}
                let lower_s=tick.elapsed().as_secs_f64();
                let tick=Instant::now();
                let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:tolerance,timeout_secs:20,..VerificationOptions::default()};
                let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
                let verify_s=tick.elapsed().as_secs_f64();let p=r.final_pathsum();
                assert!(!r.solver_invoked);
                println!("CRR_ROTATION {{\"case\":\"{case}\",\"variant\":\"{variant}\",\"policy\":\"{policy}\",\"repeat\":{rep},\"lower\":{lower},\"hits\":{hits},\"gates_before\":{before},\"gates_after\":{},\"native\":\"{}\",\"public_rr_approximate\":{},\"residual_rr_approximate\":{},\"hidden\":{},\"incidence\":{},\"terms\":{},\"parse_s\":{parse_s},\"lower_s\":{lower_s},\"verify_s\":{verify_s},\"total_s\":{}}}",a.len(),r.equivalent(),r.rr_approximate,p.rr_approximate,internal(p).len(),incidence(p),terms(p),start.elapsed().as_secs_f64());
            }
        }
    }
}


// Cost-aware HH pivot choice at the original online reduction checkpoints.
// Exact-only experiment: same Difference schedule, same Elim/Omega priority,
// same first eligible HH integrator, no approximate input-pivot extension.
// Only trial one alternative internal pivot, bounded eight trials per miter.
#[derive(Default)]
struct PivotAudit {
    trials:usize, accepted:usize, peak_incidence:usize, rows:Vec<String>,
}
fn pivot_saturate(ps:&mut PathSum,audit:&mut PivotAudit,record:bool){
    assert_eq!(ps.rr_tolerance,0.0);
    loop {
        if audit.trials>=8||terms(ps)>TERM_CAP {
            ps.full_reduce();break;
        }
        let ids=ps.get_reducible_vars();
        if ids.is_empty(){break;}
        if ps.try_reduce_elim(&ids)||ps.try_reduce_omega(&ids){continue;}
        // Build a sparse incidence index only for this HH pass, not a
        // separate symbolic IR. Preserve the original descending integrator.
        let mut index=std::collections::BTreeMap::<u32,Option<Anf>>::new();
        for &y in &ids{index.insert(y,Some(Anf::default()));}
        for (m,c) in &ps.p.terms{
            for &y in m{
                if let Some(slot)=index.get_mut(&y){
                    if !c.is_pure_half(){*slot=None;}
                    else if let Some(phi)=slot{
                        toggle(phi,m.iter().copied().filter(|v|*v!=y).collect());
                    }
                }
            }
        }
        let mut hit=false;
        for &y in &ids{
            let Some(Some(phi))=index.get(&y) else{continue;};
            let mut pivots:Vec<u32>=phi.iter().filter(|m|m.len()==1&&phi.iter().all(|n|n==*m||!n.contains(&m[0]))).map(|m|m[0]).collect();
            pivots.sort_unstable();
            let Some(&v)=pivots.last() else{continue;};
            hit=true;
            if pivots.len()<2||v<(ps.v.num_qubits as u32)||phi.len()>5{
                assert!(ps.try_reduce_hh(&[y]));break;
            }
            let score=|v:u32|ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).filter(|m|m.contains(&v)&&!m.contains(&y)).map(|m|1+m.len()).sum::<usize>();
            let alt=pivots.iter().copied().filter(|z|*z!=v&&*z>=ps.v.num_qubits as u32&&ps.v.path_vars.contains(z)).min_by_key(|z|(score(*z),*z));
            let Some(w)=alt else{assert!(ps.try_reduce_hh(&[y]));break;};
            if score(w)>=score(v)||score(w).saturating_mul(1usize<<(phi.len()-1))>TERM_CAP{
                assert!(ps.try_reduce_hh(&[y]));break;
            }
            audit.trials+=1;
            let mut native=ps.clone();
            assert!(native.try_reduce_hh(&[y]));
            let mut rhs=phi.clone();rhs.remove(&vec![w]);
            let mut cand=ps.clone();
            cand.p.terms.retain(|m,_|!m.contains(&y));
            cand.p.substitute_var_with_poly(w,&rhs);
            cand.f.substitute_var_with_poly(w,&rhs);
            cand.v.path_vars.remove(&y);cand.v.path_vars.remove(&w);
            assert_eq!(internal(&native).len(),internal(&cand).len());
            assert!(!cand.rr_approximate&&!native.rr_approximate);
            assert!(cand.p.terms.keys().chain(cand.f.functions.iter().flatten()).flatten().all(|v|cand.v.path_vars.contains(v)));
            let ni=incidence(&native);let ci=incidence(&cand);
            if ci<ni&&terms(&cand)<=TERM_CAP{
                audit.accepted+=1;
                if record{
                    audit.rows.push(format!("{{\"y\":{y},\"pivot\":{w},\"native_pivot\":{v},\"rhs\":{:?},\"before\":{},\"after\":{},\"native_after\":{},\"native_incidence\":{ni},\"candidate_incidence\":{ci},\"scale_exponent_delta\":-2}}",sorted(&rhs),ir(ps,None),ir(&cand,None),ir(&native,None)));
                }
                *ps=cand;
            }else{*ps=native;}
            break;
        }
        audit.peak_incidence=audit.peak_incidence.max(incidence(ps));
        if !hit{
            assert!(!ps.try_reduce_hh(&ids));break;
        }
    }
}
fn pivot_replay(n:usize,a:&[quprs::ir::QuantumOp],b:&[quprs::ir::QuantumOp],adaptive:bool,record:bool)->(PathSum,PivotAudit){
    use quprs::ir::QuantumOp::*;
    use similar::{Algorithm,DiffOp};
    let mut ps=PathSum::quantum_circuit(&[quprs::pathsum::Register::new("q",n)],None);
    let mut audit=PivotAudit::default();
    let mut apply=|ps:&mut PathSum,op:&quprs::ir::QuantumOp,bra:bool|{
        if !adaptive{op.apply(ps,bra);return;}
        ps.set_auto_reduce(false);op.apply(ps,bra);ps.set_auto_reduce(true);
        if matches!(op,H(_)|RX(..)|RY(..)|U2(..)|U3(..)|U(..)){
            pivot_saturate(ps,&mut audit,record);
        }
        audit.peak_incidence=audit.peak_incidence.max(incidence(ps));
    };
    for op in similar::capture_diff_slices(Algorithm::Myers,a,b){
        match op{
            DiffOp::Equal{old_index,new_index,len}=>for i in 0..len{apply(&mut ps,&a[old_index+i],false);apply(&mut ps,&b[new_index+i],true);},
            DiffOp::Delete{old_index,old_len,..}=>for i in 0..old_len{apply(&mut ps,&a[old_index+i],false);},
            DiffOp::Insert{new_index,new_len,..}=>for i in 0..new_len{apply(&mut ps,&b[new_index+i],true);},
            DiffOp::Replace{old_index,old_len,new_index,new_len}=>{
                for i in 0..old_len{apply(&mut ps,&a[old_index+i],false);}
                for i in 0..new_len{apply(&mut ps,&b[new_index+i],true);}
            }
        }
    }
    drop(apply);
    if adaptive{pivot_saturate(&mut ps,&mut audit,record);}else{ps.full_reduce();}
    (ps,audit)
}
#[test]
fn native_cost_aware_pivot_pilot(){
    let case=std::env::var("CRR_CASE").unwrap();
    let variant=std::env::var("CRR_VARIANT").unwrap();
    let source=std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap();
    let target=std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap();
    let(a,n)=parse_qasm_str(&source).unwrap();let(b,m)=parse_qasm_str(&target).unwrap();assert_eq!(n,m);
    let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
    let baseline=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
    assert!(!baseline.solver_invoked&&!baseline.final_pathsum().rr_approximate);
    let p=baseline.final_pathsum();
    let (control,_)=pivot_replay(n,&a,&b,false,false);
    assert_eq!(ir(p,None),ir(&control,None),"original Difference replay mismatch");
    let(q,audit)=pivot_replay(n,&a,&b,true,true);
    assert!(!q.rr_approximate);
    for row in &audit.rows{println!("CRR_PIVOT_STEP {row}");}
    let h=internal(&q).len();let original_h=internal(p).len();
    let shape=if h!=0{"unknown"}else if q.is_identity_up_to_phase(){"identity_up_to_phase"}else{"nonidentity_zero_hidden"};
    println!("CRR_PIVOT_CASE {{\"case\":\"{case}\",\"variant\":\"{variant}\",\"original_native\":\"{}\",\"original_hidden\":{original_h},\"candidate_hidden\":{h},\"original_incidence\":{},\"candidate_incidence\":{},\"candidate_shape\":\"{shape}\",\"trials\":{},\"accepted\":{},\"candidate_peak_sampled_incidence\":{},\"baseline\":{},\"candidate\":{}}}",baseline.equivalent(),incidence(p),incidence(&q),audit.trials,audit.accepted,audit.peak_incidence,ir(p,None),ir(&q,None));
    // Repeat balanced order only for small bounded miter diagnostic.
    // Timings include replay/selection, not receipt JSON serialization.
    for rep in 0..3{for k in 0..2{
        let adaptive=(rep+k)%2==1;
        let start=Instant::now();let(r,z)=pivot_replay(n,&a,&b,adaptive,false);
        let elapsed=start.elapsed().as_secs_f64();
        assert_eq!(ir(&r,None),ir(if adaptive{&q}else{p},None));
        println!("CRR_PIVOT_TIME {{\"case\":\"{case}\",\"variant\":\"{variant}\",\"repeat\":{rep},\"adaptive\":{adaptive},\"elapsed_s\":{elapsed},\"trials\":{},\"accepted\":{}}}",z.trials,z.accepted);
    }}
}


// Exact known Clifford lowering, isolated as a construction ablation.
// Retain the scalar phase: source Rz(pi/2) Rx(pi/2) Rz(pi/2)=-iH;
// target Ry(-pi/2) Rz(-pi)=iH, Ry(-pi/2) Rz(pi)=-iH.
fn exact_h_lower(ops:&[quprs::ir::QuantumOp])->(Vec<quprs::ir::QuantumOp>,usize,i64){
    use quprs::{ir::QuantumOp::*,rational::Angle};
    let half=Angle::from_qasm_str("pi/2").unwrap();
    let neg_half=Angle::from_qasm_str("-pi/2").unwrap();
    let pi=Angle::from_qasm_str("pi").unwrap();
    let neg_pi=Angle::from_qasm_str("-pi").unwrap();
    let mut out=Vec::with_capacity(ops.len());let mut i=0;let mut hits=0;let mut phase=0i64;
    while i<ops.len(){
        if let Some([RZ(a,x),RX(b,y),RZ(c,z)])=ops.get(i..i+3){
            if a==b&&b==c&&x==&half&&y==&half&&z==&half{
                out.push(H(*a));hits+=1;phase-=1;i+=3;continue;
            }
        }
        if let Some([RY(a,x),RZ(b,z)])=ops.get(i..i+2){
            if a==b&&x==&neg_half&&(z==&pi||z==&neg_pi){
                out.push(H(*a));hits+=1;phase+=if z==&neg_pi{1}else{-1};i+=2;continue;
            }
        }
        out.push(ops[i].clone());i+=1;
    }
    (out,hits,phase)
}
// The two sides' common input prefix may be removed exactly. Only
// wire-disjoint commutation and equal parsed operations are allowed;
// no common suffix (which would conjugate the miter), no angle snapping.
fn common_frontier(a:&mut Vec<quprs::ir::QuantumOp>,b:&mut Vec<quprs::ir::QuantumOp>,n:usize)->usize{
    use quprs::ir::QuantumOp::*;
    fn ready(g:&[quprs::ir::QuantumOp],n:usize)->Vec<usize>{
        let mut blocked=vec![false;n];let mut out=Vec::new();
        for(i,op)in g.iter().enumerate(){
            let wires=match op{
                H(q)|X(q)|Y(q)|Z(q)|S(q)|SDG(q)|T(q)|TDG(q)|RX(q,_)|RY(q,_)|RZ(q,_)|P(q,_)|U1(q,_)|U2(q,_,_)|U3(q,_,_,_)|U(q,_,_,_)=>vec![*q],
                CX(a,b)|CZ(a,b)|SWAP(a,b)=>vec![*a,*b],
                CCX(a,b,c)=>vec![*a,*b,*c],
                GlobalPhase(_)=>break,
            };
            if wires.iter().all(|q|!blocked[*q]){out.push(i);}
            for q in wires{blocked[q]=true;}
        }
        out
    }
    let mut matched=0;
    loop{
        let ar=ready(a,n);let br=ready(b,n);
        let mut aa=FxHashSet::default();let mut bb=FxHashSet::default();
        for i in ar{
            if let Some(j)=br.iter().copied().find(|j|!bb.contains(j)&&a[i]==b[*j]){
                aa.insert(i);bb.insert(j);
            }
        }
        if aa.is_empty(){break;}
        matched+=aa.len();
        let mut i=0;a.retain(|_|{let keep=!aa.contains(&i);i+=1;keep});
        let mut j=0;b.retain(|_|{let keep=!bb.contains(&j);j+=1;keep});
    }
    matched
}
#[test]
fn native_frontier_pilot(){
    use quprs::{ir::QuantumOp,rational::Angle};
    let case=std::env::var("CRR_CASE").unwrap();
    let variant=std::env::var("CRR_VARIANT").unwrap();
    let arm=std::env::var("CRR_ARM").unwrap();
    let policy=std::env::var("CRR_POLICY").unwrap();
    let mode=std::env::var("CRR_MODE").unwrap();
    let t=Instant::now();
    let(a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let(b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();assert_eq!(n,m);
    let parse=t.elapsed().as_secs_f64();let counts=(a.len(),b.len());
    let tick=Instant::now();
    let (mut a,ha,pa,mut b,hb,pb)=if arm=="original"{(a,0,0,b,0,0)}else{
        let(a,ha,pa)=exact_h_lower(&a);let(b,hb,pb)=exact_h_lower(&b);(a,ha,pa,b,hb,pb)
    };
    let matched=if arm=="frontier"{common_frontier(&mut a,&mut b,n)}else{0};
    let half=Angle::from_qasm_str("pi/2").unwrap();
    if pa!=0{a.push(QuantumOp::GlobalPhase(half.clone()*pa));}
    if pb!=0{b.push(QuantumOp::GlobalPhase(half*pb));}
    let lower=tick.elapsed().as_secs_f64();
    println!("CRR_FRONTIER_PREP {{\"case\":\"{case}\",\"variant\":\"{variant}\",\"arm\":\"{arm}\",\"policy\":\"{policy}\",\"mode\":\"{mode}\",\"source_before\":{},\"target_before\":{},\"source_after\":{},\"target_after\":{},\"source_h\":{ha},\"target_h\":{hb},\"phase_a\":{pa},\"phase_b\":{pb},\"matched_prefix\":{matched},\"parse_s\":{parse},\"lower_s\":{lower}}}",counts.0,counts.1,a.len(),b.len());
    let opts=VerificationOptions{
        method:if mode=="hybrid"{VerificationMethod::Hybrid}else{VerificationMethod::ReductionRules},
        rr_tolerance:if policy=="strict"{0.0}else{1e-10},gpmc_precision_digits:90,timeout_secs:15,..VerificationOptions::default()
    };
    let r=check_equivalence_with_options(n,&a,&b,&opts).unwrap();let p=r.final_pathsum();
    if policy=="strict"{assert!(!p.rr_approximate);}
    println!("CRR_FRONTIER_RESULT {{\"case\":\"{case}\",\"variant\":\"{variant}\",\"arm\":\"{arm}\",\"policy\":\"{policy}\",\"mode\":\"{mode}\",\"native\":\"{}\",\"hidden\":{},\"terms\":{},\"incidence\":{},\"rr_approximate\":{},\"residual_rr_approximate\":{},\"solver_invoked\":{},\"rr_s\":{},\"dimacs_s\":{:?},\"solver_s\":{:?},\"total_s\":{}}}",r.equivalent(),internal(p).len(),terms(p),incidence(p),r.rr_approximate,p.rr_approximate,r.solver_invoked,r.pathsum_time,r.to_dimacs_time.unwrap_or(0.0),r.tool_time.unwrap_or(0.0),t.elapsed().as_secs_f64());
}


// Original online RR trajectory, stopped at the first bounded residual
// blow-up. Diagnostic only: no partial miter is classified as EQ/NEQ.
#[test]
fn native_growth_checkpoint(){
    use quprs::ir::QuantumOp::*;
    use similar::{Algorithm,DiffOp};
    let case=std::env::var("CRR_CASE").unwrap();
    let variant=std::env::var("CRR_VARIANT").unwrap();
    let policy=std::env::var("CRR_POLICY").unwrap();
    let schedule=std::env::var("CRR_SCHEDULE").unwrap();
    let(a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let(b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();assert_eq!(n,m);
    let mut order=Vec::new();
    if schedule=="difference"{
        for op in similar::capture_diff_slices(Algorithm::Myers,&a,&b){
            match op{
                DiffOp::Equal{old_index,new_index,len}=>for i in 0..len{order.push((false,old_index+i));order.push((true,new_index+i));},
                DiffOp::Delete{old_index,old_len,..}=>for i in 0..old_len{order.push((false,old_index+i));},
                DiffOp::Insert{new_index,new_len,..}=>for i in 0..new_len{order.push((true,new_index+i));},
                DiffOp::Replace{old_index,old_len,new_index,new_len}=>{
                    for i in 0..old_len{order.push((false,old_index+i));}
                    for i in 0..new_len{order.push((true,new_index+i));}
                }
            }
        }
    }else{
        assert_eq!(schedule,"naive");
        for i in 0..a.len().max(b.len()){
            if i<a.len(){order.push((false,i));}
            if i<b.len(){order.push((true,i));}
        }
    }
    let mut ps=PathSum::quantum_circuit(&[quprs::pathsum::Register::new("q",n)],None);
    ps.rr_tolerance=if policy=="strict"{0.0}else{1e-10};
    let start=Instant::now();
    let mut peak=0;let mut done=0;let mut ka=0;let mut kb=0;
    for (bra,i) in order.iter().copied(){
        let op=if bra{&b[i]}else{&a[i]};
        let before=terms(&ps);let h=internal(&ps).len();
        let t=Instant::now();
        // Log first risky step before applying it; preserve evidence if
        // an individual native gate exceeds the external watchdog.
        if before>=1024||done%32==0{
            println!("CRR_GROWTH_BEGIN step={done} ket={ka} bra={kb} side_bra={bra} index={i} terms={before} hidden={h} gate={op:?}");
        }
        if std::env::var_os("CRR_LIFT_CHECKPOINT").is_some() && !bra && i==528 {
            assert_eq!(policy,"strict");assert_eq!(schedule,"difference");
            let RZ(q,theta)=op else{panic!("historical gate changed")};
            assert_eq!(*q,1);
            if let Ok(arm)=std::env::var("CRR_LIFT_POLICY"){
                policy_continue(&mut ps,&a,&b,&order[done..],&case,&variant,&arm,start.elapsed().as_secs_f64());
                return;
            }
            let mut direct=ps.clone();
            let t=Instant::now();op.apply(&mut direct,false);let direct_s=t.elapsed().as_secs_f64();
            let mut lifted=ps.clone();let anf=lifted.f.functions[*q].len();
            let t=Instant::now();let (u,z)=lift_output(&mut lifted,*q);op.apply(&mut lifted,false);
            let lift_s=t.elapsed().as_secs_f64();
            let mut roundtrip=lifted.clone();let t=Instant::now();
            assert!(roundtrip.get_reducible_vars().contains(&z));
            assert!(roundtrip.try_reduce_hh(&[z]));
            assert!(!roundtrip.v.path_vars.contains(&u)&&!roundtrip.v.path_vars.contains(&z));
            assert_eq!(ir(&roundtrip,None),ir(&direct,None),"inverse HH phase/outputs/live mismatch");
            let inverse_s=t.elapsed().as_secs_f64();
            println!("CRR_LIFT_LOCAL case={case} variant={variant} index={i} angle={theta:?} anf={anf} before_terms={before} direct_terms={} lifted_terms={} direct_incidence={} lifted_incidence={} direct_hidden={} lifted_hidden={} direct_s={direct_s} lifted_s={lift_s} inverse_s={inverse_s} exact_native_roundtrip=true",terms(&direct),terms(&lifted),incidence(&direct),incidence(&lifted),internal(&direct).len(),internal(&lifted).len());
            // Fixed bounded continuation, not a whole-circuit verdict. The
            // direct arm already crossed the same TERM_CAP at this coordinate.
            let mut audit=LiftAudit::default();let mut peak=terms(&lifted);
            let start=Instant::now();let mut advanced=0;let mut stop="horizon";
            for (bra,j) in order.iter().copied().skip(done+1).take(64){
                if start.elapsed().as_secs_f64()>8.0{stop="wall_budget";break;}
                let gate=if bra{&b[j]}else{&a[j]};
                lifted.set_auto_reduce(false);
                if !bra{
                    if let RZ(q,_)|P(q,_)|S(q)|SDG(q)|T(q)|TDG(q)|RX(q,_)|RY(q,_)|U1(q,_)|U2(q,_,_)|U3(q,_,_,_)|U(q,_,_,_)=gate{
                        // Conservative policy: compress a long output ANF
                        // before any potentially non-half phase addition.
                        if lifted.f.functions[*q].len()>=12 {
                            if audit.lifts>=16{stop="lift_budget";break;}
                            lift_output(&mut lifted,*q);audit.lifts+=1;
                        }
                    }
                }
                println!("CRR_LIFT_BEGIN advanced={advanced} side_bra={bra} index={j} terms={} gate={gate:?}",terms(&lifted));
                gate.apply(&mut lifted,bra);
                lifted.set_auto_reduce(true);
                advanced+=1;peak=peak.max(terms(&lifted));
                if terms(&lifted)>TERM_CAP{stop="term_cap";break;}
                // Bounded strict RR. Original rule methods are reused;
                // acceptance is a representation-cost policy, not new
                // legality. No approximate matching or input pivots.
                lift_saturate(&mut lifted,&mut audit);
                peak=peak.max(terms(&lifted));
                if terms(&lifted)>TERM_CAP{stop="term_cap";break;}
            }
            println!("CRR_LIFT_HORIZON case={case} variant={variant} stop={stop} advanced={advanced} terms={} incidence={} hidden={} peak={peak} trials={} accepts={} rejects={} extra_lifts={} elapsed_s={}",terms(&lifted),incidence(&lifted),internal(&lifted).len(),audit.trials,audit.accepts,audit.rejects,audit.lifts,start.elapsed().as_secs_f64());
            return;
        }
        op.apply(&mut ps,bra);
        done+=1;if bra{kb+=1;}else{ka+=1;}
        let after=terms(&ps);peak=peak.max(after);
        if after>=1024||done%32==0||t.elapsed().as_millis()>20{
            let degree=ps.p.terms.keys().map(|m|m.len()).max().unwrap_or(0);
            let out_terms=ps.f.functions.iter().map(|f|f.len()).sum::<usize>();
            println!("CRR_GROWTH_STEP step={done} ket={ka} bra={kb} hidden={} terms={after} phase_terms={} output_terms={out_terms} max_degree={degree} before={before} elapsed_s={} rule_successes={} rr_approximate={}",internal(&ps).len(),ps.p.terms.len(),t.elapsed().as_secs_f64(),ps.stats.total_successes(),ps.rr_approximate);
        }
        if after>TERM_CAP{
            println!("CRR_GROWTH_STOP reason=term_cap step={done} total={} ket={ka} bra={kb} hidden={} terms={after} peak={peak} elapsed_s={}",order.len(),internal(&ps).len(),start.elapsed().as_secs_f64());
            return;
        }
    }
    ps.full_reduce();
    let opts=VerificationOptions{method:VerificationMethod::ReductionRules,rr_tolerance:ps.rr_tolerance,timeout_secs:15,
        strategy:if schedule=="difference"{quprs::VerificationStrategy::Difference}else{quprs::VerificationStrategy::Naive},..VerificationOptions::default()};
    let original=check_equivalence_with_options(n,&a,&b,&opts).unwrap();
    assert_eq!(ir(&ps,None),ir(original.final_pathsum(),None),"checkpoint replay drift");
    println!("CRR_GROWTH_COMPLETE case={case} variant={variant} policy={policy} schedule={schedule} step={done} hidden={} terms={} incidence={} peak={peak} native={} elapsed_s={}",internal(&ps).len(),terms(&ps),incidence(&ps),original.equivalent(),start.elapsed().as_secs_f64());
}


// Exact inverse HH: 1/2 sum_{u,z} (-1)^{z(u XOR f)} = 1
// with u replacing f in the output. Fresh u,z add two balanced paths.
fn lift_output(ps:&mut PathSum,q:usize)->(u32,u32){
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
#[derive(Default)]
struct LiftAudit{trials:usize,accepts:usize,rejects:usize,lifts:usize,elim_removed:usize,hh:usize,omega:usize,preflight_defer:usize}
fn lift_saturate(ps:&mut PathSum,audit:&mut LiftAudit){
    assert_eq!(ps.rr_tolerance,0.0);
    for _ in 0..16{
        let ids=ps.get_reducible_vars();
        if ids.is_empty(){return;}
        let old_hidden=internal(ps).len();
        if ps.try_reduce_elim(&ids){audit.elim_removed+=old_hidden-internal(ps).len();continue;}
        let mut changed=false;let mut local_trials=0;
        for rule in [1,2]{
            for &y in &ids{
                if local_trials>=8{break;}
                let ys:Vec<_>=ps.p.terms.iter().filter(|(m,_)|m.contains(&y)).collect();
                if ys.is_empty(){continue;}
                if rule==1{
                    // Upper bound quadratic expansion of omega; cap
                    // discovery work before invoking the original method.
                    if ys.len()>24||!ys.iter().any(|(m,c)|m.len()==1&&(c.is_pure_quarter()||c.is_pure_fraction(3,4)))||
                        ys.iter().any(|(m,c)|m.len()>1&&!c.is_pure_half()){continue;}
                }else{
                    if ys.len()>12||ys.iter().any(|(_,c)|!c.is_pure_half()){continue;}
                    let phi:Anf=ys.iter().map(|(m,_)|m.iter().copied().filter(|v|*v!=y).collect()).collect();
                    let Some(v)=phi.iter().filter(|m|m.len()==1&&phi.iter().all(|r|r==*m||!r.contains(&m[0]))).map(|m|m[0]).max() else{continue;};
                    if v<ps.v.num_qubits as u32||!ps.v.path_vars.contains(&v){continue;}
                    let affected=ps.p.terms.keys().chain(ps.f.functions.iter().flatten()).filter(|m|m.contains(&v)&&!m.contains(&y)).count();
                    if affected.saturating_mul(1usize<<(phi.len()-1))>TERM_CAP{audit.preflight_defer+=1;continue;}
                }
                local_trials+=1;audit.trials+=1;
                let mut trial=ps.clone();
                let ok=if rule==1{trial.try_reduce_omega(&[y])}else{trial.try_reduce_hh(&[y])};
                if !ok{audit.rejects+=1;continue;}
                assert!(!trial.rr_approximate);
                assert_eq!(internal(&trial).len()+if rule==1{1}else{2},internal(ps).len());
                if terms(&trial)<=TERM_CAP&&incidence(&trial)<=incidence(ps){
                    *ps=trial;audit.accepts+=1;if rule==1{audit.omega+=1;}else{audit.hh+=1;}changed=true;break;
                }
                audit.rejects+=1;
            }
            if changed||local_trials>=8{break;}
        }
        if !changed{return;}
    }
}


// Bound the number of subsets visited by native arithmetic expansion.
// Saturation is conservative, not a prediction of distinct merged terms.
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
fn phase_gate_bound(op:&quprs::ir::QuantumOp,ps:&PathSum)->Option<(usize,usize)>{
    use quprs::ir::QuantumOp::*;
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
fn policy_continue(ps:&mut PathSum,a:&[quprs::ir::QuantumOp],b:&[quprs::ir::QuantumOp],
    remaining:&[(bool,usize)],case:&str,variant:&str,arm:&str,prefix_s:f64){
    assert!(matches!(arm,"static"|"adaptive"));
    let start=Instant::now();
    let mut audit=LiftAudit::default();let mut pairs=Vec::new();
    let mut peak=terms(ps);let mut max_inc=incidence(ps);
    let mut done=0;let mut stop="complete";
    let mut skipped=0;let mut bound_peak=0;
    for (bra,j) in remaining.iter().copied(){
        if start.elapsed().as_secs_f64()>15.0{stop="wall_budget";break;}
        let gate=if bra{&b[j]}else{&a[j]};
        ps.set_auto_reduce(false);
        if !bra{
            if let Some((q,work))=phase_gate_bound(gate,ps){
                let s=ps.f.functions[q].len();bound_peak=bound_peak.max(work);
                let should_lift=if arm=="static"{s>=12}else{
                    // Avoid over-lifting low-order Clifford phases.
                    // Count predicted expansion attempts, including repeated
                    // unions; require substantial separation from lift cost.
                    work>2048&&work>8*(s+2)
                };
                if should_lift{
                    if pairs.len()>=32{stop="lift_budget";break;}
                    let (u,z)=lift_output(ps,q);pairs.push((u,z));audit.lifts+=1;
                    println!("CRR_POLICY_LIFT arm={arm} step={done} source_index={j} anf={s} expansion_bound={work} u={u} z={z} terms={}",terms(ps));
                }else if s>=12{skipped+=1;}
            }
        }
        if done%32==0||terms(ps)>=3000{
            println!("CRR_POLICY_BEGIN arm={arm} step={done} bra={bra} index={j} terms={} hidden={} gate={gate:?}",terms(ps),internal(ps).len());
        }
        gate.apply(ps,bra);ps.set_auto_reduce(true);
        done+=1;peak=peak.max(terms(ps));max_inc=max_inc.max(incidence(ps));
        if terms(ps)>TERM_CAP{stop="term_cap";break;}
        lift_saturate(ps,&mut audit);
        peak=peak.max(terms(ps));max_inc=max_inc.max(incidence(ps));
        if terms(ps)>TERM_CAP{stop="term_cap";break;}
    }
    let gone=pairs.iter().filter(|(u,z)|!ps.v.path_vars.contains(u)&&!ps.v.path_vars.contains(z)).count();
    let partial=pairs.iter().filter(|(u,z)|ps.v.path_vars.contains(u)!=ps.v.path_vars.contains(z)).count();
    let both=pairs.len()-gone-partial;
    let elapsed=start.elapsed().as_secs_f64();
    println!("CRR_POLICY_SUMMARY case={case} variant={variant} arm={arm} stop={stop} advanced={done} remaining={} terms={} incidence={} hidden={} peak={peak} max_inc={max_inc} lifts={} both_live={both} partial_live={partial} both_gone={gone} skipped_large_anf={skipped} bound_peak={bound_peak} trials={} accepts={} rejects={} omega={} hh={} elim_removed={} preflight_defer={} prefix_s={prefix_s} continuation_s={elapsed}",remaining.len(),terms(ps),incidence(ps),internal(ps).len(),audit.lifts,audit.trials,audit.accepts,audit.rejects,audit.omega,audit.hh,audit.elim_removed,audit.preflight_defer);
    // No verdict on partial state; no new solver lane or tolerance change.
    // If all gates finish, report native shape only. Existing strict
    // residual/source-trust gates must precede any count/verdict claim.
    if stop=="complete"{
        println!("CRR_POLICY_COMPLETE case={case} variant={variant} arm={arm} identity_shape={} hidden={} rr_approximate={}",ps.is_identity_up_to_phase(),internal(ps).len(),ps.rr_approximate);
    }
}
#[test]
fn lift_policy_bounds(){
    assert_eq!(expansion_bound(20,5,1_000_000),21699);
    assert_eq!(expansion_bound(82,5,2048),2048);
    assert_eq!(expansion_bound(70,1,2048),70);
    assert_eq!(expansion_bound(12,2,2048),78);
    assert_eq!(expansion_bound(0,5,2048),0);
    assert_eq!(expansion_bound(12,0,2048),0);
}
