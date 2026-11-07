//! API parity tests for supported Rust-native input and Python result names.
//! External WMC integration tests cover actual GPMC/Ganak execution.
use pathsum::{
    ir::QuantumOp,
    rational::{Angle, FreeRational},
    verification,
    EquivalenceStatus, QuantumCircuit, VerificationMethod, VerificationOptions,
};

fn rr_options() -> VerificationOptions {
    VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    }
}

#[test]
fn facade_matches_low_level_rr_without_copying_source_operations() {
    let mut left = QuantumCircuit::new(1);
    left.h(0).unwrap();
    let right = QuantumCircuit::from_ops(1, vec![QuantumOp::H(0)]).unwrap();
    let borrowed_ops = left.operations().as_ptr();
    let options = rr_options();
    let result = verification::check_equivalence(&left, &right, &options).unwrap();
    let low_level = pathsum::check_equivalence_with_options(
        1, left.operations(), right.operations(), &options
    ).unwrap();
    assert_eq!(left.operations().as_ptr(), borrowed_ops);
    assert_eq!(result.status, low_level.status);
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert_eq!(result.equivalent(), "equivalent");
    assert!(!result.wmc_solver_invoked());
    assert_eq!(result.gate_num(), 1);
    assert_eq!(result.final_pathsum().is_identity(), result.final_ps.is_identity());
    assert_eq!(result.method.as_str(), "reduction_rules");
    assert_eq!(result.method.to_string(), "reduction_rules");
}

#[test]
fn qasm_and_programmatic_ir_are_identical() {
    let src = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n";
    let parsed = QuantumCircuit::from_qasm_str(src).unwrap();
    let mut built = QuantumCircuit::new(2);
    built.h(0).unwrap().cx(0, 1).unwrap();
    assert_eq!(parsed, built);
    assert_eq!(parsed.len(), 2);
    assert!(!parsed.is_empty());
    assert_eq!(parsed.num_qubits(), 2);
    assert!(QuantumCircuit::from_qasm_str("OPENQASM 2.0;\nqreg q[1];\nmeasure q[0] -> c[0];").is_err());
}

#[test]
fn qasm_file_uses_the_same_parser() {
    let src = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nx q[0];\n";
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
    let file = std::env::temp_dir().join(format!(
        "quprs-api-parity-{}-{stamp}.qasm", std::process::id()
    ));
    std::fs::write(&file, src).unwrap();
    let parsed_file = QuantumCircuit::from_qasm_file(&file);
    std::fs::remove_file(file).unwrap();
    assert_eq!(parsed_file.unwrap(), QuantumCircuit::from_qasm_str(src).unwrap());
}

#[test]
fn invalid_wires_fail_before_mutating_the_circuit() {
    let mut c = QuantumCircuit::new(2);
    assert!(c.push(QuantumOp::SWAP(0, 2)).is_err());
    assert!(c.push(QuantumOp::SWAP(0, 0)).is_err());
    assert!(c.cx(0, 0).is_err());
    assert!(c.push(QuantumOp::U2(2, Angle::ZERO, Angle::ZERO)).is_err());
    assert!(c.push(QuantumOp::CCX(0, 1, 1)).is_err());
    assert!(c.push(QuantumOp::CCX(0, 1, 2)).is_err());
    assert!(c.is_empty());
    c.cx(0, 1).unwrap();
    assert_eq!(c.len(), 1);
}

#[test]
fn mismatched_circuit_widths_are_an_explicit_input_error() {
    let left = QuantumCircuit::new(1);
    let right = QuantumCircuit::new(2);
    let e = verification::check_equivalence(&left, &right, &rr_options()).unwrap_err();
    assert!(e.to_string().contains("circuit widths differ"));
}

#[test]
fn reduction_unknown_and_global_phase_have_python_spellings() {
    let mut h = QuantumCircuit::new(1);
    h.h(0).unwrap();
    let empty = QuantumCircuit::new(1);
    let unknown = verification::check_equivalence(&h, &empty, &rr_options()).unwrap();
    assert_eq!(unknown.status, EquivalenceStatus::Unknown);
    assert_eq!(unknown.equivalent(), "unknown");

    let theta = Angle::new_constant(FreeRational::new(1, 1000));
    let rz = QuantumCircuit::from_ops(1, vec![QuantumOp::RZ(0, theta.clone())]).unwrap();
    let p = QuantumCircuit::from_ops(1, vec![QuantumOp::P(0, theta)]).unwrap();
    let options = VerificationOptions {
        strategy: pathsum::VerificationStrategy::Naive,
        ..rr_options()
    };
    let result = verification::check_equivalence(&rz, &p, &options).unwrap();
    assert_eq!(result.status, EquivalenceStatus::EquivalentUpToGlobalPhase);
    assert_eq!(result.equivalent(), "equivalent*");
    assert!(!result.wmc_solver_invoked());
}

#[test]
fn methods_statuses_and_defaults_share_python_contract() {
    let o = VerificationOptions::default();
    assert_eq!(o.method.as_str(), "hybrid");
    assert_eq!(o.tool_name, "gpmc");
    assert_eq!(o.timeout_secs, 600);
    assert_eq!(o.rr_tolerance, 1e-10);
    assert_eq!(o.phase_tolerance, 1e-8);
    assert_eq!(o.wmc_phase_tolerance, 1e-8);
    assert_eq!(o.approximate_distance_tolerance, Some(1e-8));
    assert_eq!(o.gpmc_precision_digits, 30);
    for (status, text) in [
        (EquivalenceStatus::Equivalent, "equivalent"),
        (EquivalenceStatus::EquivalentUpToGlobalPhase, "equivalent*"),
        (EquivalenceStatus::NotEquivalent, "not_equivalent"),
        (EquivalenceStatus::Unknown, "unknown"),
        (EquivalenceStatus::Timeout, "Timeout"),
        (EquivalenceStatus::MemoryOut, "MemoryOut"),
    ] {
        assert_eq!(status.as_str(), text);
        assert_eq!(status.to_string(), text);
    }
}
