// Version-pinned Qiskit 2.6.1 Miter + RR CPU Simulation, no Python or WMC.
// Included at crate root from core.rs to share its Cargo CodSpeed build.
// QASM parsing and science validation are outside the instrumented span.
use pathsum::EquivalenceStatus;
use pathsum::qasm::parse_qasm_str;

struct QasmPair {
    source: Vec<QuantumOp>,
    target: Vec<QuantumOp>,
    qubits: usize,
}
fn parsed(source: &str, target: &str) -> QasmPair {
    let (source, q1) = parse_qasm_str(source).expect("canonical source QASM2");
    let (target, q2) = parse_qasm_str(target).expect("Qiskit261 level0 QASM2");
    assert_eq!(q1, q2, "source/target qubit count mismatch");
    assert!(q1 > 0);
    QasmPair { source, target, qubits: q1 }
}
macro_rules! versioned_pair {
    ($name:ident, $source:literal, $target:literal) => {
        fn $name() -> &'static QasmPair {
            static ONCE: OnceLock<QasmPair> = OnceLock::new();
            ONCE.get_or_init(|| parsed(include_str!($source), include_str!($target)))
        }
    };
}

versioned_pair!(ghz32,
    "../../MQTBench/ghz_nativegates_ibm_qiskit_opt0_32.qasm",
    "../../MQTBench/qiskit-2.6.1-opt0/h,ry,rz,cx/ghz_nativegates_ibm_qiskit_opt0_32.qasm");
versioned_pair!(graphstate16,
    "../../MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "../../MQTBench/qiskit-2.6.1-opt0/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm");
versioned_pair!(qft16,
    "../../MQTBench/qft_nativegates_ibm_qiskit_opt0_16.qasm",
    "../../MQTBench/qiskit-2.6.1-opt0/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_16.qasm");
versioned_pair!(qpeexact8,
    "../../MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "../../MQTBench/qiskit-2.6.1-opt0/h,ry,rz,cx/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm");
versioned_pair!(vqe4,
    "../../MQTBench/vqe_nativegates_ibm_qiskit_opt0_4.qasm",
    "../../MQTBench/qiskit-2.6.1-opt0/h,ry,rz,cx/vqe_nativegates_ibm_qiskit_opt0_4.qasm");

// Miter construction and *all native RR* are measured. This is not an
// isolated HH/Elim rule microbenchmark: see separate rust_core rule benches.
// Source parsing, Python startup and external WMC are all excluded.
fn verify(pair: &QasmPair, strategy: VerificationStrategy, reverse: bool) -> EquivalenceStatus {
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        strategy,
        rr_tolerance: 1e-10,
        approximate_distance_tolerance: Some(1e-8),
        ..VerificationOptions::default()
    };
    let (left, right) = if reverse {
        (pair.target.as_slice(), pair.source.as_slice())
    } else {
        (pair.source.as_slice(), pair.target.as_slice())
    };
    let result = check_equivalence_with_options(pair.qubits,
        divan::black_box(left), divan::black_box(right), &options)
        .expect("native RR verifier");
    assert!(!result.solver_invoked, "native RR must never invoke WMC");
    assert!(matches!(result.status, EquivalenceStatus::Equivalent
        | EquivalenceStatus::EquivalentUpToGlobalPhase),
        "Qiskit261 positive source must terminate as RR EQ/EQ*: {:?}", result.status);
    result.status
}


fn q261_preload_and_validate() {
    for (pair, strategy, reverse) in [
        (ghz32(), VerificationStrategy::Straightforward, true),
        (graphstate16(), VerificationStrategy::Naive, false),
        (qft16(), VerificationStrategy::Proportional, true),
        (qpeexact8(), VerificationStrategy::Proportional, false),
        (vqe4(), VerificationStrategy::Proportional, false),
    ] {
        let _ = verify(pair, strategy, reverse);
    }
}

#[divan::bench]
fn q261_rr_ghz32_positive() {
    divan::black_box(verify(ghz32(), VerificationStrategy::Straightforward, true));
}
#[divan::bench]
fn q261_rr_graphstate16_positive() {
    divan::black_box(verify(graphstate16(), VerificationStrategy::Naive, false));
}
#[divan::bench]
fn q261_rr_qft16_positive() {
    divan::black_box(verify(qft16(), VerificationStrategy::Proportional, true));
}
#[divan::bench]
fn q261_rr_qpeexact8_positive() {
    divan::black_box(verify(qpeexact8(), VerificationStrategy::Proportional, false));
}
#[divan::bench]
fn q261_rr_vqe4_positive() {
    divan::black_box(verify(vqe4(), VerificationStrategy::Proportional, false));
}
