//! Narrow, read-only diagnostics for QASM source admission and strict unitary phase.
//! These experiments are intentionally separate from production verifier contracts.

use quprs::ir::QuantumOp;
use quprs::pathsum::PathSum;
use quprs::qasm::parse_qasm_str;

struct AdmissionCase {
    name: &'static str,
    source: &'static str,
    reference_valid: bool,
}

fn admission_cases() -> [AdmissionCase; 8] {
    [
        AdmissionCase {
            name: "qasm31_header_with_stdlib",
            source: "OPENQASM 3.1;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];",
            reference_valid: true,
        },
        AdmissionCase {
            name: "qasm30_h_without_stdlib",
            source: "OPENQASM 3.0;\nqubit[1] q;\nh q[0];",
            reference_valid: false,
        },
        AdmissionCase {
            name: "qasm30_uppercase_H",
            source: "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nH q[0];",
            reference_valid: false,
        },
        AdmissionCase {
            name: "qasm30_lowercase_u_without_stdlib",
            source: "OPENQASM 3.0;\nqubit[1] q;\nu(2*pi,0,0) q[0];",
            reference_valid: false,
        },
        AdmissionCase {
            name: "qasm30_u3_without_stdlib",
            source: "OPENQASM 3.0;\nqubit[1] q;\nu3(2*pi,0,0) q[0];",
            reference_valid: false,
        },
        AdmissionCase {
            name: "qasm30_builtin_uppercase_U",
            source: "OPENQASM 3.0;\nqubit[1] q;\nU(2*pi,0,0) q[0];",
            reference_valid: true,
        },
        AdmissionCase {
            name: "qasm30_h_with_stdlib",
            source: "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];",
            reference_valid: true,
        },
        AdmissionCase {
            name: "duplicate_control_and_target",
            source: "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\ncx q[0],q[0];",
            reference_valid: false,
        },
    ]
}

#[test]
fn observed_native_admission_trace() {
    let mut divergence_count = 0;
    for case in admission_cases() {
        let result = parse_qasm_str(case.source);
        let accepted = result.is_ok();
        if accepted != case.reference_valid {
            divergence_count += 1;
        }
        println!(
            "SOURCE_ADMISSION case={} reference_valid={} native_accepted={} agrees={}",
            case.name, case.reference_valid, accepted, accepted == case.reference_valid
        );
        match result {
            Ok((ops, n)) => println!(
                "SOURCE_IR case={} qubits={} operations={ops:?}",
                case.name, n
            ),
            Err(err) => println!("SOURCE_REJECT case={} reason={err}", case.name),
        }
    }
    println!("SOURCE_ADMISSION_DIVERGENCES={divergence_count}");
}

#[test]
fn observed_native_gate_order_and_cx_operand_direction() {
    let source = "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];";
    let (ops, n) = parse_qasm_str(source).expect("source must parse");
    assert_eq!(n, 2);
    assert_eq!(ops, vec![QuantumOp::H(0), QuantumOp::CX(0, 1)]);

    let reverse_source =
        "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\ncx q[1],q[0];";
    let (reverse_ops, reverse_n) =
        parse_qasm_str(reverse_source).expect("reverse source must parse");
    assert_eq!(reverse_n, 2);
    assert_eq!(reverse_ops, vec![QuantumOp::CX(1, 0)]);
    println!("CX_OPERAND_AND_GATE_ORDER_NATIVE_IR=AS_EXPECTED");
}

fn native_pathsum_of_source(source: &str) -> PathSum {
    let (ops, n) = parse_qasm_str(source).expect("source must parse for this diagnostic");
    assert_eq!(n, 1);
    assert_eq!(ops.len(), 1);
    let mut pathsum = PathSum::new(n);
    pathsum.set_auto_reduce(false);
    ops[0].apply(&mut pathsum, false);
    pathsum
}

fn phase_pair() -> (PathSum, PathSum) {
    let builtin =
        "OPENQASM 3.0;\nqubit[1] q;\nU(2*pi,0,0) q[0];";
    let compatibility =
        "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nu3(2*pi,0,0) q[0];";
    (native_pathsum_of_source(builtin), native_pathsum_of_source(compatibility))
}

fn phase_representations_differ(left: &PathSum, right: &PathSum) -> bool {
    left.p.terms != right.p.terms
        || left.f.functions != right.f.functions
        || left.v.path_vars != right.v.path_vars
}

#[test]
fn observed_native_u_and_u3_strict_phase_trace() {
    let (u, u3) = phase_pair();
    println!("NATIVE_BUILTIN_U_PHASE={:?}", u.p.terms);
    println!("NATIVE_COMPAT_U3_PHASE={:?}", u3.p.terms);
    let distinct = phase_representations_differ(&u, &u3);
    println!("NATIVE_U_U3_PATHSUM_DISTINCT={distinct}");
    assert!(
        !distinct,
        "the current implementation is expected to route U3 and U to the same operation"
    );
}

#[test]
fn strict_contract_source_admission() {
    let mut mismatches = Vec::new();
    for case in admission_cases() {
        let observed = parse_qasm_str(case.source).is_ok();
        if observed != case.reference_valid {
            mismatches.push(case.name);
            println!(
                "STRICT_ADMISSION_MISMATCH case={} expected_valid={} observed_valid={}",
                case.name, case.reference_valid, observed
            );
        }
    }
    println!("STRICT_ADMISSION_MISMATCH_COUNT={}", mismatches.len());
    assert!(
        mismatches.is_empty(),
        "strict source admission differs from reference for: {}",
        mismatches.join(",")
    );
}

#[test]
fn strict_contract_u_and_u3_phase_must_be_distinct() {
    // At theta = 2*pi, the OpenQASM builtin U is I while the
    // standard-library compatibility u3 is -I as a strict matrix.
    let (u, u3) = phase_pair();
    let distinct = phase_representations_differ(&u, &u3);
    println!("STRICT_U_U3_DISTINCT_REQUIRED=true NATIVE_OBSERVED_DISTINCT={distinct}");
    assert!(
        distinct,
        "strict source semantics require U(2*pi,0,0) and u3(2*pi,0,0) to differ"
    );
}


#[test]
fn strict_source_pinned_admission_and_phase_lowering() {
    use quprs::qasm::parse_qasm_str_source_pinned;
    for case in admission_cases() {
        let result=parse_qasm_str_source_pinned(case.source);
        assert_eq!(result.is_ok(),case.reference_valid,
            "version-pinned source gate mismatch: {}",case.name);
    }
    // Version 3.1 supports the same admitted finite unitary profile:
    // the original version is not silently changed in proof evidence.
    for version in ["3.0","3.1"] {
        let builtin=format!("OPENQASM {version};\nqubit[1] q;\nU(2*pi,0,0) q[0];\n");
        let (ops,n)=parse_qasm_str_source_pinned(&builtin).unwrap();
        assert_eq!(n,1);
        assert_eq!(ops.len(),2);
        assert!(matches!(ops[0],QuantumOp::U(0,_,_,_)));
        assert!(matches!(ops[1],QuantumOp::GlobalPhase(_)));
        let compat=format!(
            "OPENQASM {version};\ninclude \"stdgates.inc\";\nqubit[1] q;\nu3(2*pi,0,0) q[0];\n");
        let (ops,n)=parse_qasm_str_source_pinned(&compat).unwrap();
        assert_eq!(n,1);
        assert_eq!(ops.len(),2);
        assert!(matches!(ops[0],QuantumOp::U3(0,_,_,_)));
        assert!(matches!(ops[1],QuantumOp::GlobalPhase(_)));
    }
    let qasm2="OPENQASM 2.0;\nqreg q[1];\nU(2*pi,0,0) q[0];\n";
    assert_eq!(parse_qasm_str_source_pinned(qasm2).unwrap().0.len(),2);
    // Fail-closed: controlled phases must not be hoisted as global phases;
    // every source rejected here would need a separate scoped proof rule.
    for body in [
        "ctrl @ U(2*pi,0,0) q[0];",
        "H q[0];",
        "U(2*pi,0,0) q[0]; U(0,0,0) q[0];",
        "gphase(pi/4); gphase(pi/4);",
    ] {
        let source=format!("OPENQASM 3.1;\nqubit[1] q;\n{body}\n");
        assert!(parse_qasm_str_source_pinned(&source).is_err(),"{body}");
    }
    println!(
        "STRICT_PINNED_SOURCE_ADMISSION cases=8 versions=2_u3_and_U \
         qasm2_builtin=true controlled_fail_closed=true"
    );
}
