#![cfg(feature = "standalone-rr")]
// This consumer-facing target intentionally needs no installed WMC solver.
use pathsum::{check_equivalence_with_options, EquivalenceStatus, VerificationMethod, VerificationOptions};
use pathsum::ir::QuantumOp;

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
