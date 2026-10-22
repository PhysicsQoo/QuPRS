//! Strict source-exact Clifford SX support: the exact Qiskit global phase
//! matters when returning Equivalent versus EquivalentUpToGlobalPhase.
use pathsum::{check_equivalence, EquivalenceStatus, VerificationMethod};
use pathsum::qasm::parse_qasm_str;
use pathsum::strategy::VerificationStrategy;

fn qasm(ops: &str) -> String {
    format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{ops}")
}
fn result(left: &str, right: &str) -> EquivalenceStatus {
    let (a, nq) = parse_qasm_str(&qasm(left)).unwrap();
    let (b, _) = parse_qasm_str(&qasm(right)).unwrap();
    check_equivalence(
        nq, &a, &b, VerificationMethod::ReductionRules,
        VerificationStrategy::Naive, "gpmc", 30,
    ).unwrap().status
}
#[test]
fn sx_squared_is_exactly_x_not_merely_phase_equivalent() {
    assert_eq!(result("sx q[0];\nsx q[0];", "x q[0];"), EquivalenceStatus::Equivalent);
}
#[test]
fn sx_followed_by_sxdg_is_identity() {
    assert_eq!(result("sx q[0];\nsxdg q[0];", ""), EquivalenceStatus::Equivalent);
}
#[test]
fn sx_and_rx_pi_over_two_differ_by_provable_global_phase() {
    assert_eq!(result("sx q[0];", "rx(pi/2) q[0];"), EquivalenceStatus::EquivalentUpToGlobalPhase);
}
