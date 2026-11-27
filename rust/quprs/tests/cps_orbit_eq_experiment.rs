//! Research-only original EQ covariance pilot. No new RR/WMC or production API.
//! Embedded unmodified QASM from AutoQ 7eed39ad7ba5615a87c3f532a24f866e08967c12.
//! Each process runs one arm. See environment contract in the test.
//! Numeric WMC verdict is not an exact certificate. Unknown/timeout is censored.
use quprs::{check_equivalence_with_options, EquivalenceStatus, VerificationMethod,
    VerificationOptions, VerificationStrategy};
use quprs::ir::QuantumOp;

const SOURCES: &[(&str, usize, &str, &str)] = &[
    ("03", 3, "4a5cc0a405f2c67172de5a7fe2ca16fcfac77bdc", r###"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[8];
x qubits[7];

x qubits[0];
x qubits[1];
x qubits[2];
h qubits[3];
h qubits[4];
h qubits[5];
h qubits[7];

cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[3];
x qubits[4];
x qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
x qubits[3];
x qubits[4];
x qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[7];

cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[3];
x qubits[4];
x qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
x qubits[3];
x qubits[4];
x qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[7];

x qubits[0];
x qubits[1];
x qubits[2];
h qubits[7];
"###),
    ("04", 4, "56e26972835eb604ee7ffd005ae0f10cdd081697", r###"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[11];
x qubits[10];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[10];
"###),
    ("05", 5, "bb7399ca0341c60457a741540fdb595ea022f375", r###"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[14];
x qubits[13];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
x qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
h qubits[13];

cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[13];

cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[13];

cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[13];

cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
cx qubits[0], qubits[5];
cx qubits[1], qubits[6];
cx qubits[2], qubits[7];
cx qubits[3], qubits[8];
cx qubits[4], qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
ccx qubits[5], qubits[6], qubits[10];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[11], qubits[8], qubits[12];
cz qubits[12], qubits[9];
ccx qubits[11], qubits[8], qubits[12];
ccx qubits[10], qubits[7], qubits[11];
ccx qubits[5], qubits[6], qubits[10];
x qubits[5];
x qubits[6];
x qubits[7];
x qubits[8];
x qubits[9];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[8];
h qubits[9];
x qubits[13];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
x qubits[4];
h qubits[13];
"###),
];

#[test]
#[ignore = "bounded opt-in research arm; use a separate process hard timeout"]
fn original_eq_covariance_arm() {
    let size = std::env::var("CPS_ORBIT_SIZE").expect("03,04,05");
    let j: usize = std::env::var("CPS_ORBIT_GEN").expect("generator index").parse().unwrap();
    let method = match std::env::var("CPS_ORBIT_MODE").expect("rr,wmc,hybrid").as_str() {
        "rr" => VerificationMethod::ReductionRules,
        "wmc" => VerificationMethod::WmcOnly,
        "hybrid" => VerificationMethod::Hybrid,
        _ => panic!("unknown mode"),
    };
    let variant = std::env::var("CPS_ORBIT_VARIANT").expect("source,wrong-output");
    assert!(variant == "source" || variant == "wrong-output");
    let seconds: u64 = std::env::var("CPS_ORBIT_SECONDS").expect("positive solver seconds").parse().unwrap();
    assert!(seconds > 0);
    let (_, w, blob, qasm) = SOURCES.iter().find(|r| r.0 == size.as_str()).unwrap();
    assert!(j < *w);
    let start = std::time::Instant::now();
    let (ops, n) = quprs::qasm::parse_qasm_str_source_pinned(qasm).expect("source admission");
    assert_eq!(n, 3 * *w - 1);
    assert!(ops.iter().all(|g| matches!(g, QuantumOp::H(_) | QuantumOp::X(_) |
        QuantumOp::Z(_) | QuantumOp::CX(..) | QuantumOp::CZ(..) | QuantumOp::CCX(..))));
    // Source-locked reference certificates, not a benchmark-name solver shortcut:
    // U X_j Z_(w+j) = X_j X_(w+j) U, strict on these sources.
    // Rightmost acts first, native gate list is chronological.
    let mut lhs = vec![QuantumOp::X(j), QuantumOp::Z(*w+j)];
    lhs.extend(ops.iter().cloned());
    let mut rhs = ops;
    rhs.push(QuantumOp::X(j));
    if variant == "source" { rhs.push(QuantumOp::X(*w+j)); }
    let options = VerificationOptions {
        method, strategy: VerificationStrategy::Difference,
        tool_name: "gpmc".to_owned(), timeout_secs: seconds,
        rr_tolerance: 0.0, gpmc_precision_digits: 30,
        ..VerificationOptions::default()
    };
    println!("CPS_ORBIT_START size={size} generator={j} variant={variant} method={} source_blob={blob} n={n}",
        options.method.as_str());
    match check_equivalence_with_options(n, &lhs, &rhs, &options) {
        Ok(r) => {
            let ps = &r.final_ps;
            let h = ps.v.path_vars.iter().filter(|&&id| id as usize >= ps.v.num_qubits).count();
            println!("CPS_ORBIT_RESULT status={} solver_invoked={} rr_approximate={} h={} phase_terms={} elim={}/{} hh={}/{} omega={}/{} pathsum_s={} dimacs_s={:?} wmc_s={:?} tool_s={:?} wall_s={} printed={:?} precision_reason={:?}",
                r.status.as_str(), r.solver_invoked, r.rr_approximate, h, ps.p.terms.len(),
                ps.stats.elim.successes, ps.stats.elim.attempts,
                ps.stats.hh.successes, ps.stats.hh.attempts,
                ps.stats.omega.successes, ps.stats.omega.attempts,
                r.pathsum_time, r.to_dimacs_time, r.wmc_time, r.tool_time,
                start.elapsed().as_secs_f64(), r.wmc_printed_verdict, r.wmc_precision_reason);
            if variant == "source" {
                assert_ne!(r.status, EquivalenceStatus::NotEquivalent, "contradicts exact reference");
            } else {
                assert!(!matches!(r.status, EquivalenceStatus::Equivalent | EquivalenceStatus::EquivalentUpToGlobalPhase),
                    "wrong output Pauli differs by a non-scalar X");
            }
            assert!(!r.rr_approximate, "RR matching must be strict");
        }
        Err(e) => {
            println!("CPS_ORBIT_ERROR error={e:?} wall_s={}", start.elapsed().as_secs_f64());
            panic!("execution error, not a non-equivalence verdict");
        }
    }
}
