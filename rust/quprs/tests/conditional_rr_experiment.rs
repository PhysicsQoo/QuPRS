//! Research-only CRR-0 incidence. No new verifier verdict.
use quprs::{check_equivalence_with_options, PathSum, VerificationMethod, VerificationOptions};
use quprs::qasm::parse_qasm_str;
use rustc_hash::FxHashSet;
const TERM_CAP: usize = 4096;
const GUARD_CAP: usize = 8;
const TARGET_CAP: usize = 32;
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
    assert!(guard as usize >= p.v.num_qubits && p.v.path_vars.contains(&guard));
    let mut out = p.clone();
    let mut sub = FxHashSet::default();
    if value { sub.insert(Vec::<u32>::new()); }
    out.p.substitute_var_with_poly(guard, &sub);
    out.f.substitute_var_with_poly(guard, &sub);
    assert!(out.v.path_vars.remove(&guard));
    assert!(out.p.terms.keys().all(|m| !m.contains(&guard)));
    assert!(out.f.functions.iter().flatten().all(|m| !m.contains(&guard)));
    out
}
fn elim(p: &PathSum, y: u32) -> bool {
    if !p.v.path_vars.contains(&y) { return false; }
    let mut trial = p.clone();
    let ok = trial.try_reduce_elim(&[y]);
    if ok {
        assert!(!trial.v.path_vars.contains(&y));
        assert_eq!(trial.v.path_vars.len() + 1, p.v.path_vars.len());
        assert!(trial.v.path_vars.is_subset(&p.v.path_vars));
    }
    ok
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
    let mut probes = 0;
    let mut additional = [0usize;2];
    let mut both = 0;
    let mut eligible_guards = 0;
    for &g in ids.iter().take(GUARD_CAP) {
        let l=restrict(p,g,false);
        let r=restrict(p,g,true);
        if terms(&l)>TERM_CAP || terms(&r)>TERM_CAP { continue; }
        eligible_guards += 1;
        for &y in ids.iter().filter(|&&v| v!=g).take(TARGET_CAP) {
            if elim(p,y) { continue; }
            let x=elim(&l,y); let z=elim(&r,y);
            probes+=1;
            additional[0]+=x as usize;
            additional[1]+=z as usize;
            both+=(x&&z) as usize;
        }
    }
    println!("CRR_INCIDENCE case={case} guards={eligible_guards} target_probes={probes} branch0_new={} branch1_new={} both_new={both} guard_cap={GUARD_CAP} target_cap={TARGET_CAP}",
        additional[0],additional[1]);
}
