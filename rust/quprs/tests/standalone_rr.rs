// RR-only verification is selected by method, not a compile-time Cargo feature.
// These tests intentionally require no installed WMC solver.
use quprs::{check_equivalence_with_options, EquivalenceStatus, VerificationMethod, VerificationOptions};
use quprs::ir::QuantumOp;

#[test]
fn standalone_rr_identity_has_no_solver_invocation() {
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(1, &[], &[], &options).unwrap();
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert!(!result.solver_invoked);
    assert!(result.wmc_printed_verdict.is_none());
}

#[test]
fn standalone_rr_cannot_mislabel_an_x_gate_as_identity() {
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(1, &[QuantumOp::X(0)], &[], &options).unwrap();
    assert_ne!(result.status, EquivalenceStatus::Equivalent);
    assert_ne!(result.status, EquivalenceStatus::EquivalentUpToGlobalPhase);
    assert!(!result.solver_invoked);
}

#[test]
fn hybrid_identity_can_finish_without_an_external_solver() {
    let result = check_equivalence_with_options(
        1, &[], &[], &VerificationOptions::default()
    ).unwrap();
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert!(!result.solver_invoked);
}

#[test]
fn standalone_rr_leaves_irreducible_h_as_unknown() {
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(
        1, &[QuantumOp::H(0)], &[], &options,
    ).unwrap();
    assert_eq!(result.status, EquivalenceStatus::Unknown);
    assert!(!result.solver_invoked);
    assert!(result.wmc_printed_verdict.is_none());
}


// A direct semantic negative control: (1/sqrt(2)) sum_y (-1)^(xy)|x><x|
// is sqrt(2)|0><0|, NOT I. This is a general PathSum fixture, not a unitary
// source circuit. An HH rewrite must not drop the constraint x=0.
#[test]
fn hh_external_target_must_preserve_free_input() {
    use quprs::{PathSum};
    use quprs::pathsum::PhaseCoeff;
    let mut ps=PathSum::new(1);
    ps.set_auto_reduce(false);
    let y=ps.v.get_fresh_var();
    ps.p.add_term(vec![0,y],PhaseCoeff::HALF);
    let before=ps.clone();
    let candidates=ps.get_reducible_vars();
    assert!(!ps.try_reduce_hh(&candidates));
    assert_eq!(ps.p.terms,before.p.terms);
    assert_eq!(ps.f.functions,before.f.functions);
    assert_eq!(ps.v.path_vars,before.v.path_vars);
}

// Original source pair, no transformed fixture, no solver dependence.
#[test]
fn hh_feynman_grover_source_pair_rr_and_hybrid() {
    use quprs::{QuantumCircuit,VerificationStrategy};
    use std::path::Path;
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../../benchmarks/Feynman");
    let a=QuantumCircuit::from_qasm_file(root.join("grover_5.qasm")).unwrap();
    let b=QuantumCircuit::from_qasm_file(root.join("h,y,z,t,tdg,cx/grover_5.qasm")).unwrap();
    assert_eq!((a.num_qubits(),b.num_qubits()),(9,9));
    assert_eq!((a.operations().len(),b.operations().len()),(351,854));
    for method in [VerificationMethod::ReductionRules,VerificationMethod::Hybrid] {
        let opts=VerificationOptions{method,strategy:VerificationStrategy::Proportional,rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
        let r=quprs::verification::check_equivalence(&a,&b,&opts).unwrap();
        assert_eq!(r.status,EquivalenceStatus::EquivalentUpToGlobalPhase);
        assert!(!r.solver_invoked);
        assert!(!r.rr_approximate);
        let ps=r.final_pathsum();
        assert_eq!(ps.v.path_vars.len(),9);
        assert!(ps.is_identity_up_to_phase());
        assert_eq!(ps.p.terms.len(),1);
    }
}
