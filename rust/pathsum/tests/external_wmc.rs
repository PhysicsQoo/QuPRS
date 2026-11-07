#![cfg(feature = "external-wmc")]
// Installed external solvers are passed via QUPRS_GPMC_PATH / QUPRS_GANAK_PATH.
// All cases exercise the packaged Rust library, never the Python wheel.
use pathsum::{
    check_equivalence_with_options, EquivalenceStatus, VerificationMethod,
    VerificationOptions,
};
use pathsum::ir::QuantumOp;

fn verify(method: VerificationMethod, tool: &str, digits: u32, gates: &[QuantumOp]) -> pathsum::EquivalenceCheckResult {
    let options = VerificationOptions {
        method,
        tool_name: tool.to_owned(),
        gpmc_precision_digits: digits,
        timeout_secs: 30,
        ..VerificationOptions::default()
    };
    check_equivalence_with_options(1, gates, &[], &options).unwrap()
}

#[test]
fn hybrid_identity_stays_reduction_only() {
    let result = verify(VerificationMethod::Hybrid, "gpmc", 30, &[]);
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert!(!result.solver_invoked);
}

#[test]
fn hybrid_irreducible_h_uses_real_gpmc() {
    let result = verify(VerificationMethod::Hybrid, "gpmc", 30, &[QuantumOp::H(0)]);
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert!(result.solver_invoked);
    assert!(result.wmc_printed_verdict.is_some());
}

#[test]
fn wmc_only_x_uses_real_gpmc() {
    let result = verify(VerificationMethod::WmcOnly, "gpmc", 30, &[QuantumOp::X(0)]);
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert!(result.solver_invoked);
}

#[test]
fn wmc_only_x_uses_real_ganak() {
    let result = verify(VerificationMethod::WmcOnly, "ganak", 30, &[QuantumOp::X(0)]);
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert!(result.solver_invoked);
}

#[test]
fn explicit_gpmc_90_precision_is_supported() {
    let result = verify(VerificationMethod::WmcOnly, "gpmc", 90, &[QuantumOp::X(0)]);
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert!(result.solver_invoked);
}

#[test]
#[ignore = "requires QUPRS_GPMC_PATH to be an intentionally invalid absolute path"]
fn missing_solver_fails_closed() {
    let path = std::env::var("QUPRS_GPMC_PATH").expect("explicit missing solver path required");
    assert!(!std::path::Path::new(&path).exists());
    let options = VerificationOptions {
        method: VerificationMethod::WmcOnly,
        tool_name: "gpmc".to_owned(),
        timeout_secs: 10,
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(1, &[QuantumOp::X(0)], &[], &options);
    assert!(result.is_err(), "an unavailable GPMC must never produce a scientific verdict");
}


#[test]
fn public_facade_hybrid_uses_real_gpmc_and_retains_python_result_names() {
    let mut source = pathsum::QuantumCircuit::new(1);
    source.h(0).unwrap();
    let reference = pathsum::QuantumCircuit::new(1);
    let result = pathsum::verification::check_equivalence(
        &source, &reference, &VerificationOptions::default()
    ).unwrap();
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert_eq!(result.equivalent(), "not_equivalent");
    assert!(result.wmc_solver_invoked());
}
