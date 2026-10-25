//! Isolated exact-source decimal ingress canary for the pinned Rust candidate.
//! Does not classify native GPMC/Ganak floats as exact equivalence.
use num_bigint::BigInt;
use num_rational::BigRational;
use pathsum::ir::QuantumOp;
use pathsum::{qasm, PathSum, VerificationStrategy};

fn ratio(n: i64, d: i64) -> BigRational {
    BigRational::new(BigInt::from(n), BigInt::from(d))
}

fn qasm_text(body: &str) -> String {
    format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{body}")
}

fn run_rz(body: &str) -> (Vec<BigRational>, Vec<(Vec<u32>, BigRational)>) {
    let (ops, qubits) = qasm::parse_qasm_str(&qasm_text(body)).expect("exact QASM ingress");
    assert_eq!(qubits, 1);
    let mut angles = Vec::new();
    for op in &ops {
        match op {
            QuantumOp::RZ(0, angle) => {
                assert_eq!(angle.constant.numer, 0, "decimal radian was coerced to pi units");
                assert!(angle.symbols.is_empty(), "unexpected symbolic phase");
                angles.push(angle.radians.clone().unwrap_or_else(|| ratio(0,1)));
            }
            _ => panic!("the constrained source consists only of RZ on q[0]"),
        }
    }
    let mut initial = PathSum::new(1);
    initial.set_auto_reduce(false);
    let result = VerificationStrategy::Naive.run(initial, &[], &ops);
    let mut phases = Vec::new();
    for (monomial, coeff) in &result.p.terms {
        assert_eq!(coeff.constant.numer, 0, "unexpected pi-rational phase");
        assert!(coeff.symbols.is_empty(), "symbolic phase not allowed");
        let rad = coeff.radians.clone().unwrap_or_else(|| ratio(0,1));
        if rad != ratio(0,1) {
            phases.push((monomial.clone(), rad));
        }
    }
    phases.sort_by(|a,b| a.0.cmp(&b.0));
    (angles, phases)
}

fn assert_bra_trace_coefficients(body: &str, expected: BigRational) {
    let (_,phases) = run_rz(body);
    if expected == ratio(0,1) {
        assert!(phases.is_empty(), "exactly cancelled RZ leaves nonzero source phase");
        return;
    }
    assert_eq!(phases.len(), 2, "expected source 1Q constant and bit monomials");
    assert_eq!(phases[0].0, Vec::<u32>::new(), "constant monomial absent");
    assert_eq!(phases[1].0, vec![0], "source bit monomial absent");
    assert_eq!(phases[0].1, &expected / BigInt::from(4),
        "constant bra phase must be +delta/4 radians in 2pi exponent");
    assert_eq!(phases[1].1, -(&expected / BigInt::from(2)),
        "bit bra phase must be -delta/2 radians in 2pi exponent");
    println!("EXACT_INGRESS_RZ_BRA delta={expected} constant={} bit={}",
        phases[0].1, phases[1].1);
}

#[test]
fn preserves_individual_signed_decimal_radians_without_pi_approximation() {
    let (angles,_) = run_rz("rz(0.0002) q[0];\nrz(-0.000199999) q[0];\n");
    assert_eq!(angles, vec![ratio(1,5000),ratio(-199999,1000000000)]);
    let sum = angles.iter().cloned().fold(ratio(0,1),|acc,angle|acc+angle);
    assert_eq!(sum, ratio(1,1_000_000_000));
}

#[test]
fn preserves_the_one_nanosecond_angle_residual_in_the_actual_phase_polynomial() {
    // This is a 10^-9 radian angle (not a time).
    assert_bra_trace_coefficients(
        "rz(0.0002) q[0];\nrz(-0.000199999) q[0];\n",
        ratio(1,1_000_000_000)
    );
}

#[test]
fn exact_inverse_pairs_cancel_in_actual_phase_polynomial() {
    assert_bra_trace_coefficients(
        "rz(0.0002) q[0];\nrz(-0.0002) q[0];\n",
        ratio(0,1)
    );
    // Relative unitary for identical source paths is RZ(-a)RZ(a).
    assert_bra_trace_coefficients(
        "rz(-0.0002) q[0];\nrz(0.0002) q[0];\n",
        ratio(0,1)
    );
}

#[test]
fn negative_angle_and_doubled_rotation_have_correct_signs() {
    assert_bra_trace_coefficients("rz(0.0002) q[0];\n",ratio(1,5000));
    assert_bra_trace_coefficients("rz(-0.0002) q[0];\n",ratio(-1,5000));
    assert_bra_trace_coefficients(
        "rz(0.0002) q[0];\nrz(0.0002) q[0];\n",ratio(1,2500));
}

#[test]
fn decimal_source_and_symbolic_pi_remain_distinct_types() {
    let (dec,_) = qasm::parse_qasm_str(&qasm_text("rz(0.5) q[0];\n")).unwrap();
    let (symbolic,_) = qasm::parse_qasm_str(&qasm_text("rz(pi/2) q[0];\n")).unwrap();
    let decimal = match &dec[0] { QuantumOp::RZ(_,a) => a, _ => unreachable!() };
    let exact_pi = match &symbolic[0] { QuantumOp::RZ(_,a) => a, _ => unreachable!() };
    assert_eq!(decimal.radians,Some(ratio(1,2)));
    assert_eq!(decimal.constant.numer,0);
    assert!(exact_pi.radians.is_none());
    assert_eq!(exact_pi.constant.numer,1);
    assert_eq!(exact_pi.constant.denom,2);
}
