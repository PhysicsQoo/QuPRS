//! End-to-end native regressions for exact source-decimal angle identities.
//! These are production QASM -> IR -> gate -> PhasePolynomial -> reduction,
//! not a standalone reference-model implementation.
use pathsum::{check_equivalence, EquivalenceStatus, VerificationMethod};
use pathsum::qasm::parse_qasm_str;
use pathsum::rational::Angle;
use pathsum::strategy::VerificationStrategy;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Zero;

fn qasm(gates: &str) -> String {
    format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{}", gates)
}

fn check(lhs: &str, rhs: &str) -> EquivalenceStatus {
    let (ops1, n1) = parse_qasm_str(&qasm(lhs)).unwrap();
    let (ops2, n2) = parse_qasm_str(&qasm(rhs)).unwrap();
    assert_eq!(n1, n2);
    check_equivalence(
        n1, &ops1, &ops2, VerificationMethod::ReductionRules,
        VerificationStrategy::Naive, "gpmc", 30,
    ).unwrap().status
}

#[test]
fn exact_source_radians_cancel_before_any_solver() {
    assert_eq!(
        check("rz(-2.5802058126763807) q[0];\nrz(-2.5802058126763807) q[0];",
              "rz(-5.1604116253527614) q[0];"),
        EquivalenceStatus::Equivalent,
    );
    assert_eq!(
        check("rz(1.6198837120072371) q[0];\nrz(-2.5802058126763807) q[0];",
              "rz(-0.9603221006691436) q[0];"),
        EquivalenceStatus::Equivalent,
    );
}

#[test]
fn decimal_rational_has_exact_source_provenance() {
    let a = Angle::from_qasm_str("1.2345678901234567").unwrap();
    assert_eq!(a.constant.numer, 0);
    assert_eq!(
        a.radians,
        Some(BigRational::new(
            BigInt::from(12345678901234567_i64),
            BigInt::from(10000000000000000_i64),
        )),
    );
}

#[test]
fn tiny_nonzero_exact_radians_are_not_identity() {
    assert_eq!(
        check("", "rz(0.0000000001) q[0];"),
        EquivalenceStatus::NotEquivalent,
    );
    assert_eq!(
        check("", "rz(0.001) q[0];"),
        EquivalenceStatus::NotEquivalent,
    );
}

#[test]
fn pi_and_literal_decimal_are_distinct_source_domains() {
    let pi = Angle::from_qasm_str("pi/8").unwrap();
    let decimal = Angle::from_qasm_str("0.39269908169872414").unwrap();
    assert!(pi.radians.is_none());
    assert!(decimal.radians.is_some());
    assert_ne!(pi, decimal);
    assert_eq!(
        check("rz(pi/8) q[0];\nrz(pi/8) q[0];", "rz(pi/4) q[0];"),
        EquivalenceStatus::Equivalent,
    );
}

#[test]
fn exact_input_limits_reject_instead_of_approximate() {
    assert!(Angle::from_qasm_str("pi/100000000000000000000000000").is_err());
    assert!(Angle::from_qasm_str("pi*pi").is_err());
    assert!(Angle::from_qasm_str("1e1000000").is_err());
}

#[test]
fn graphstate_rounded_complements_are_not_symbolic_pi_identities() {
    // These finite QASM decimal literals occur in Graphstate16's translated
    // source. This is an exact *one-qubit* subexpression witness and does
    // NOT by itself certify inequivalence of the entire 16-qubit circuits.
    let first = "rz(2.0330832984526417) q[0];\nrz(1.1085093551371514) q[0];";
    let second = "rz(2.8600220891857973) q[0];\nrz(0.2815705644039938) q[0];";
    let symbolic_pi = "rz(pi) q[0];";

    let first_a = Angle::from_qasm_str("2.0330832984526417").unwrap();
    let first_b = Angle::from_qasm_str("1.1085093551371514").unwrap();
    let second_a = Angle::from_qasm_str("2.8600220891857973").unwrap();
    let second_b = Angle::from_qasm_str("0.2815705644039938").unwrap();
    let symbolic = Angle::from_qasm_str("pi").unwrap();
    let first_sum = first_a.radians.unwrap() + first_b.radians.unwrap();
    let second_sum = second_a.radians.unwrap() + second_b.radians.unwrap();
    assert_ne!(first_sum, second_sum);
    assert!(symbolic.radians.is_none());
    assert_eq!(
        check(first, symbolic_pi),
        EquivalenceStatus::NotEquivalent,
    );
    assert_eq!(
        check(second, symbolic_pi),
        EquivalenceStatus::NotEquivalent,
    );
}

#[test]
fn exact_source_radians_are_canonical_when_multiplied_by_zero() {
    let zero = Angle::from_qasm_str("0.0002").unwrap() * 0;
    assert_eq!(zero, Angle::ZERO);
    assert!(zero.to_phase_coeff().is_zero());
}

#[test]
fn near_cancelled_decimal_source_retains_one_nanosecond_radian_residual() {
    let delta = Angle::from_qasm_str("0.0002").unwrap()
        - Angle::from_qasm_str("0.000199999").unwrap();
    assert_eq!(delta.radians, Some(BigRational::new(
        BigInt::from(1), BigInt::from(1_000_000_000_u64))));
    assert_eq!(check("rz(0.0002) q[0];\nrz(-0.000199999) q[0];",
                     "rz(0.000000001) q[0];"),
               EquivalenceStatus::Equivalent);
    assert_eq!(check("", "rz(0.000000001) q[0];"),
               EquivalenceStatus::NotEquivalent);
}

#[test]
fn symbolic_pi_remains_distinct_from_finite_decimal_approximation() {
    assert_eq!(check("rz(pi/8) q[0];",
                     "rz(0.39269908169872414) q[0];"),
               EquivalenceStatus::NotEquivalent);
}

#[test]
fn small_rz_and_p_rotation_differ_only_by_nonzero_global_phase() {
    assert_eq!(check("rz(0.000000001) q[0];",
                     "p(0.000000001) q[0];"),
               EquivalenceStatus::EquivalentUpToGlobalPhase);
}

#[test]
fn wmc_boundary_rejects_unrepresentable_nonzero_source_radians() {
    use pathsum::ir::QuantumOp;
    use pathsum::wmc::WmcManager;
    use pathsum::PathSum;

    // Supported exact-rational source notation is not permission to
    // round a nonzero phase into a zero WMC complex weight.
    for value in ["1e-512", "-1e-512", "1e512"] {
        let angle = Angle::from_qasm_str(value).unwrap();
        assert!(angle.radians.as_ref().is_some_and(|r| !r.numer().is_zero()));
        let mut pathsum = PathSum::new(1);
        pathsum.set_auto_reduce(false);
        QuantumOp::RZ(0, angle).apply(&mut pathsum, false);
        let mut solver = WmcManager::new(&pathsum);
        assert!(
            solver.encode_trace(&pathsum).is_err(),
            "WMC accepted unrepresentable nonzero source angle {value}",
        );
    }
    // Representable small angles still reach the ordinary floating solver.
    let mut pathsum = PathSum::new(1);
    pathsum.set_auto_reduce(false);
    QuantumOp::RZ(0, Angle::from_qasm_str("1e-100").unwrap())
        .apply(&mut pathsum, false);
    let mut solver = WmcManager::new(&pathsum);
    solver.encode_trace(&pathsum).unwrap();
}
