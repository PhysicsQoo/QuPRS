//! Research-only CRR-0 incidence. No new verifier verdict.
use quprs::{check_equivalence_with_options, PathSum, VerificationMethod, VerificationOptions};
use quprs::qasm::parse_qasm_str;
use rustc_hash::FxHashSet;
#[path="support/conditional_trace.rs"]
mod conditional_trace;
#[path="support/conditional_stitch.rs"]
mod conditional_stitch;
const TERM_CAP: usize = 4096;
const GUARD_CAP: usize = 8;
const TARGET_CAP: usize = 96;
const PAIR_GUARD_CAP: usize = 4;
fn terms(p: &PathSum) -> usize {
    p.p.terms.len() + p.f.functions.iter().map(|f| f.len()).sum::<usize>()
}
fn internal(p: &PathSum) -> Vec<u32> {
    let mut ids: Vec<_> = p.v.path_vars.iter().copied()
        .filter(|&v| v as usize >= p.v.num_qubits).collect();
    ids.sort_unstable(); ids
}
// Algebraic restriction only; never infer branch normalization or verdict.
fn restrict(p: &PathSum, guard: u32, value: bool) -> PathSum {
    assert!(p.v.path_vars.contains(&guard));
    let mut out = p.clone();
    let mut sub = FxHashSet::default();
    if value { sub.insert(Vec::<u32>::new()); }
    out.p.substitute_var_with_poly(guard, &sub);
    out.f.substitute_var_with_poly(guard, &sub);
    // Fixed input coordinates remain in the domain metadata; callers
    // must retain the external guard assignment. No amplitude verdict.
    if guard as usize >= p.v.num_qubits { assert!(out.v.path_vars.remove(&guard)); }
    assert!(out.p.terms.keys().all(|m| !m.contains(&guard)));
    assert!(out.f.functions.iter().flatten().all(|m| !m.contains(&guard)));
    out
}
// The primitive RR methods assume caller-side output independence.
 // Reconstruct the full native eligibility gate before trying any rule.
 fn probe(p: &PathSum, y: u32, rule: usize) -> bool {
    if !p.get_reducible_vars().contains(&y) { return false; }
    // Bound expansion before calling native HH/omega. HH is restricted
    // to internal pivots (input constraints are a separate research lane).
    let ys: Vec<_> = p.p.terms.iter().filter(|(m,_)| m.contains(&y)).collect();
    if rule != 0 && ys.len() > 8 { return false; }
    if rule == 2 {
        if ys.iter().any(|(_,c)| !c.is_pure_half()) { return false; }
        let phi: FxHashSet<Vec<u32>> = ys.iter()
            .map(|(m,_)| m.iter().copied().filter(|&v| v!=y).collect()).collect();
        let pivot = phi.iter().filter(|m| m.len()==1)
            .filter(|m| phi.iter().all(|q| q==*m || !q.contains(&m[0])))
            .map(|m| m[0]).max();
        if !pivot.is_some_and(|v| v as usize >= p.v.num_qubits && p.v.path_vars.contains(&v)) {
            return false;
        }
    }
    let mut trial = p.clone();
    let ok = match rule {
        0 => trial.try_reduce_elim(&[y]),
        1 => trial.try_reduce_omega(&[y]),
        2 => trial.try_reduce_hh(&[y]),
        _ => unreachable!(),
    };
    if ok {
        assert!(!trial.v.path_vars.contains(&y));
        assert_eq!(trial.v.path_vars.len() + if rule == 2 {2} else {1}, p.v.path_vars.len());
        assert!(!trial.rr_approximate);
        assert!(trial.f.functions.iter().flatten().all(|m| m.iter().all(|v| trial.v.path_vars.contains(v))));
        assert!(trial.p.terms.keys().all(|m| m.iter().all(|v| trial.v.path_vars.contains(v))));
        assert!(trial.v.path_vars.is_subset(&p.v.path_vars));
    }
    ok
}
// Rank by target-local output/phase incidence, not global ID order.
// External input guards are allowed but never integrated as path variables.
fn candidates(p: &PathSum, y: u32) -> Vec<u32> {
    let mut scores = std::collections::BTreeMap::<u32,(usize,usize)>::new();
    for m in p.f.functions.iter().flatten().filter(|m| m.contains(&y)) {
        for &g in m.iter().filter(|&&v|v!=y) { scores.entry(g).or_default().0+=1; }
    }
    for m in p.p.terms.keys().filter(|m| m.contains(&y)) {
        for &g in m.iter().filter(|&&v|v!=y) { scores.entry(g).or_default().1+=1; }
    }
    let mut ids:Vec<_>=scores.into_iter().filter(|(g,_)|p.v.path_vars.contains(g)).collect();
    ids.sort_unstable_by_key(|(g,(f,p))|(std::cmp::Reverse(*f),std::cmp::Reverse(*p),*g));
    ids.into_iter().take(GUARD_CAP).map(|(g,_)|g).collect()
}
fn mask(p:&PathSum,y:u32,before:[bool;3])->[bool;3] {
    if terms(p)>TERM_CAP {return [false;3];}
    std::array::from_fn(|r|!before[r]&&probe(p,y,r))
}
#[test]
fn exact_signed_guard_partition_and_cross_terms() {
    let mut checks = 0;
    for phase in 0u32..256 {
        for output in 0u32..256 {
            for z in 0..2 {
                let mut whole = 0i32;
                for row in 0..8 {
                    if ((output >> row) & 1) == z {
                        whole += if (phase >> row) & 1 == 0 { 1 } else { -1 };
                    }
                }
                for guard in 0..3 {
                    let mut a = [0i32;2];
                    for (g, sum) in a.iter_mut().enumerate() {
                        for row in 0..8 {
                            if ((row >> guard) & 1) == g && ((output >> row) & 1) == z {
                                *sum += if (phase >> row) & 1 == 0 { 1 } else { -1 };
                            }
                        }
                    }
                    assert_eq!(whole, a[0] + a[1]);
                    assert_eq!(whole*whole, a[0]*a[0]+a[1]*a[1]+2*a[0]*a[1]);
                    checks += 1;
                }
            }
        }
    }
    assert_eq!(checks, 393216);
    let (a,b) = (1i32,-1i32);
    assert_ne!((a+b)*(a+b), a*a+b*b);
    assert_ne!(a+b, a);
    assert_ne!(a+b, a+a+b);
    println!("CRR_EXACT_SIGNED_FIBERS checks={checks}");
}
#[test]
fn native_eq_residual_incidence() {
    let Ok(source) = std::env::var("CRR_SOURCE") else { return; };
    let target = std::env::var("CRR_TARGET").expect("target");
    let case = std::env::var("CRR_CASE").expect("case");
    let read = |p: &str| std::fs::read_to_string(p).expect("QASM bytes");
    let (a,n) = parse_qasm_str(&read(&source)).expect("source parse");
    let (b,m) = parse_qasm_str(&read(&target)).expect("target parse");
    assert_eq!(n,m);
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        rr_tolerance: 0.0, timeout_secs: 20,
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(n,&a,&b,&options).expect("native RR");
    assert!(!result.solver_invoked);
    let p = result.final_pathsum();
    let ids = internal(p);
    println!("CRR_BASE case={case} n={n} status={} approximate={} hidden={} terms={} baseline_s={}",
        result.equivalent(),result.rr_approximate,ids.len(),terms(p),result.verification_time);
    if result.rr_approximate || !p.v.continuous_vars.is_empty()
        || terms(p)>TERM_CAP || result.equivalent() == "timeout" {
        println!("CRR_SKIP case={case} reason=residual_admission"); return;
    }
    conditional_trace::profile(p,&case);
    if std::env::var_os("CRR_TRACE_ONLY").is_some(){
        println!("CRR_SKIP case={case} reason=trace_only_expanded");
        return;
    }
    let start=std::time::Instant::now();
    // Types: 0 internal singleton, 1 input singleton, 2 two guards.
    let mut probes=[[0usize;3];3];
    let mut hits=[[0usize;3];3];
    let mut unique=[[0usize;3];3];
    let mut pair_incremental=[0usize;3];
    let mut pair_incremental_targets=[0usize;3];
    let mut guardless=0;
    let mut tested=0;
    for &y in ids.iter().take(TARGET_CAP) {
        tested+=1;
        let before=std::array::from_fn(|r|probe(p,y,r));
        let gs=candidates(p,y);
        if gs.is_empty() {guardless+=1;continue;}
        let mut target_hit=[[false;3];3];
        let mut target_pair_incremental=[false;3];
        let mut single=Vec::new();
        for &g in &gs {
            let kind=if (g as usize)<p.v.num_qubits {1} else {0};
            let bs=[mask(&restrict(p,g,false),y,before),mask(&restrict(p,g,true),y,before)];
            for r in 0..3 {
                if before[r] {continue;}
                probes[kind][r]+=2;
                for v in 0..2 {
                    if bs[v][r] {
                        hits[kind][r]+=1;
                        target_hit[kind][r]=true;
                        println!("CRR_HIT case={case} kind={kind} rule={r} guard={g} value={v} target={y} baseline_other={}",before.iter().any(|&x|x));
                    }
                }
            }
            single.push(bs);
        }
        let top=gs.len().min(PAIR_GUARD_CAP);
        for i in 0..top {for j in i+1..top {
            let g=gs[i];let h=gs[j];
            for u in 0..2 {for v in 0..2 {
                let q=restrict(&restrict(p,g,u==1),h,v==1);
                let bs=mask(&q,y,before);
                for r in 0..3 {
                    if before[r] {continue;}
                    probes[2][r]+=1;
                    if bs[r] {
                        hits[2][r]+=1;
                        target_hit[2][r]=true;
                        // Distinguish true depth-two incremental hits from
                        // a hit already exposed by either component alone.
                        let incremental=!single[i][u][r]&&!single[j][v][r];
                        pair_incremental[r]+=incremental as usize;
                        target_pair_incremental[r]|=incremental;
                        println!("CRR_HIT case={case} kind=2 rule={r} guards={g},{h} values={u},{v} target={y} incremental={incremental} baseline_other={}",before.iter().any(|&x|x));
                    }
                }
            }}
        }}
        for k in 0..3 {for r in 0..3 {unique[k][r]+=target_hit[k][r] as usize;}}
        for r in 0..3 {pair_incremental_targets[r]+=target_pair_incremental[r] as usize;}
    }
    println!("CRR_INCIDENCE case={case} targets={tested} target_total={} guardless={guardless} probes={probes:?} hits={hits:?} unique_targets={unique:?} pair_incremental={pair_incremental:?} pair_incremental_targets={pair_incremental_targets:?} probe_s={} guard_cap={GUARD_CAP} pair_guard_cap={PAIR_GUARD_CAP} target_cap={TARGET_CAP}",ids.len(),start.elapsed().as_secs_f64());
}

#[test]
fn exact_native_output_eligibility_controls() {
    use quprs::rational::PhaseCoeff;
    let mut p=PathSum::new(1);
    p.rr_tolerance=0.0;
    let g=p.v.get_fresh_var();
    let y=p.v.get_fresh_var();
    // Output depends on y unless g=0. Direct primitive Elim without
    // eligibility would incorrectly remove a live output variable.
    p.f.functions[0].clear();
    p.f.functions[0].insert(vec![g,y]);
    assert!(!probe(&p,y,0));
    assert!(probe(&restrict(&p,g,false),y,0));
    assert!(!probe(&restrict(&p,g,true),y,0));
    // HH: cubic half phase becomes a bilinear half phase at g=1.
    let mut h=PathSum::new(1);
    h.rr_tolerance=0.0;
    let g=h.v.get_fresh_var(); let y=h.v.get_fresh_var(); let z=h.v.get_fresh_var();
    h.p.add_term(vec![g,y,z],PhaseCoeff::HALF);
    assert!(!probe(&h,y,2));
    assert!(probe(&restrict(&h,g,true),y,2));
    assert!(probe(&restrict(&h,g,false),y,0));
    // Omega: non-half interaction blocks it until g=0.
    let mut o=PathSum::new(1);
    o.rr_tolerance=0.0;
    let g=o.v.get_fresh_var(); let y=o.v.get_fresh_var();
    o.p.add_term(vec![y],PhaseCoeff::QUARTER);
    o.p.add_term(vec![g,y],PhaseCoeff::QUARTER);
    assert!(!probe(&o,y,1));
    assert!(probe(&restrict(&o,g,false),y,1));
    assert!(!probe(&restrict(&o,g,true),y,1));
    println!("CRR_NATIVE_ELIGIBILITY controls=3");
}

#[test]
fn exact_structural_input_and_depth_two_controls() {
    let mut p=PathSum::new(1);
    p.rr_tolerance=0.0;
    let y=p.v.get_fresh_var();
    let h=p.v.get_fresh_var();
    p.f.functions[0].clear();
    p.f.functions[0].insert(vec![0,y]);
    assert_eq!(candidates(&p,y),vec![0]);
    assert!(!probe(&p,y,0));
    let q=restrict(&p,0,false);
    assert!(q.v.path_vars.contains(&0));
    assert!(probe(&q,y,0));
    assert!(!probe(&restrict(&p,0,true),y,0));
    // y*(x XOR h): neither singleton assignment removes y.
    p.f.functions[0].insert(vec![y,h]);
    let gs=candidates(&p,y);
    assert_eq!(gs,vec![0,h]);
    for g in [0,h] {for v in [false,true] {assert!(!probe(&restrict(&p,g,v),y,0));}}
    for u in [false,true] {for v in [false,true] {
        assert_eq!(probe(&restrict(&restrict(&p,0,u),h,v),y,0),u==v);
    }}
    println!("CRR_STRUCTURAL_GUARD controls=2");
}

// Standalone research runner shares the exact native checkpoint implementation.
#[cfg(not(test))]
pub fn cpr_native_run() { conditional_stitch::native_growth_checkpoint(); }
