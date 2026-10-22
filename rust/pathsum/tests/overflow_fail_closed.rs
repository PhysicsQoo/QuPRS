//! End-to-end fail-closed acceptance for rational coefficients larger than i64.
//! Exercises the actual gate -> phase polynomial -> reduction -> verification path.
//! No fake solver output and no tolerance-based interpretation.
use pathsum::{check_equivalence, EquivalenceStatus, VerificationMethod};
use pathsum::ir::QuantumOp;
use pathsum::rational::{Angle, FreeRational};
use pathsum::strategy::VerificationStrategy;

fn independent_denominators() -> Vec<QuantumOp> {
    [4_294_967_291_i64, 4_294_967_279_i64]
        .iter()
        .map(|&den| QuantumOp::P(
            0, Angle::new_constant(FreeRational::new(1, den)),
        ))
        .collect()
}

#[test]
fn arithmetic_exceeding_i64_cannot_certify_inequality_from_reduction() {
    let operations = independent_denominators();
    let result = check_equivalence(
        1, &operations, &[], VerificationMethod::ReductionRules,
        VerificationStrategy::Naive, "gpmc", 30,
    ).unwrap();
    assert_eq!(result.status, EquivalenceStatus::Unknown);
    assert!(result.tool_time.is_none());
}

#[test]
fn arithmetic_exceeding_i64_cannot_generate_wmc_proof_or_solver_call() {
    let operations = independent_denominators();
    let result = check_equivalence(
        1, &operations, &[], VerificationMethod::WmcOnly,
        VerificationStrategy::Naive, "ganak", 30,
    ).unwrap();
    assert_eq!(result.status, EquivalenceStatus::Unknown);
    assert!(result.tool_time.is_none());
}

#[test]
fn independent_verification_resets_arithmetic_taint() {
    let operations = independent_denominators();
    let inconclusive = check_equivalence(
        1, &operations, &[], VerificationMethod::ReductionRules,
        VerificationStrategy::Naive, "gpmc", 30,
    ).unwrap();
    assert_eq!(inconclusive.status, EquivalenceStatus::Unknown);
    let clean = check_equivalence(
        1, &[], &[], VerificationMethod::ReductionRules,
        VerificationStrategy::Naive, "gpmc", 30,
    ).unwrap();
    assert_eq!(clean.status, EquivalenceStatus::Equivalent);
}
