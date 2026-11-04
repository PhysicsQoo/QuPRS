//! QOO-156: real-QASM, solver-free, *mid-execution* cancellation controls.
 //! This is a functional timeout test, never a performance benchmark.
use pathsum::{
    check_equivalence_with_options, EquivalenceStatus, VerificationMethod,
    VerificationOptions, VerificationStrategy,
};
use pathsum::qasm::parse_qasm_str;
use pathsum::ir::QuantumOp;

fn expanded_source(qasm: &str, repeat: usize) -> (Vec<QuantumOp>, usize) {
    let (source, qubits) = parse_qasm_str(qasm).expect("source-pinned QuPRS paper fixture");
    assert!(!source.is_empty());
    let mut expanded = Vec::with_capacity(source.len() * repeat);
    for _ in 0..repeat {
        expanded.extend(source.iter().cloned());
    }
    assert!(expanded.len() > 20_000, "fixture should outlast one-second budget");
    (expanded, qubits)
}

fn assert_midflight_timeout(source: &[QuantumOp], qubits: usize) {
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        strategy: VerificationStrategy::Straightforward,
        timeout_secs: 1,
        rr_tolerance: 1e-10,
        ..VerificationOptions::default()
    };
    // The verification clock starts only inside this call, after input
    // parsing and source expansion. The test checks semantics, not duration.
    let result = check_equivalence_with_options(qubits, source, &[], &options)
        .expect("an expired native request returns a typed result");
    assert_eq!(
        result.status, EquivalenceStatus::Timeout,
        "large native input must cancel without a late EQ/NEQ verdict"
    );
    assert!(!result.solver_invoked, "RR-only must not invoke GPMC/Ganak");
}

#[test]
fn qft16_repeated_real_qasm_cancels_in_native_rr() {
    let (source, qubits) = expanded_source(include_str!(
        "../../../benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_16.qasm"
    ), 256);
    assert_eq!(qubits, 16);
    assert_midflight_timeout(&source, qubits);
}

#[test]
fn qpe_exact8_repeated_real_qasm_cancels_in_native_rr() {
    let (source, qubits) = expanded_source(include_str!(
        "../../../benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm"
    ), 600);
    assert_eq!(qubits, 8);
    assert_midflight_timeout(&source, qubits);
}
