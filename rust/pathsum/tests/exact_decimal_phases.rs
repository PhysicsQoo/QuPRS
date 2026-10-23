//! End-to-end native regressions for exact source-decimal angle identities.
//! These are production QASM -> IR -> gate -> PhasePolynomial -> reduction,
//! not a standalone reference-model implementation.
use pathsum::{check_equivalence, EquivalenceStatus, VerificationMethod};
use pathsum::qasm::parse_qasm_str;
use pathsum::rational::Angle;
use pathsum::strategy::VerificationStrategy;
use num_bigint::BigInt;
use num_rational::BigRational;

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
