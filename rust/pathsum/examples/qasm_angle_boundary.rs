//! Source-scoped research diagnostic for Rust QASM decimal-angle collapse.
//!
//! This invokes the unmodified production qasm parser, Angle representation,
//! and PathSum construction. It does not use WMC tolerance or native solvers.
use std::{env, error::Error, fs, path::Path};
use pathsum::{ir::QuantumOp, qasm, PathSum, VerificationStrategy};

const CASES: &[(&str, &str)] = &[
    ("zero", "0"),
    ("tiny_positive_1e12", "0.000000000001"),
    ("tiny_negative_1e12", "-0.000000000001"),
    ("tiny_positive_1e10", "0.0000000001"),
    ("above_epsilon_below_denom", "0.0000000004"),
    ("denominator_boundary", "0.000000001"),
    ("retained_small", "0.00000001"),
    ("retained_reference", "0.001"),
];

fn main() -> Result<(), Box<dyn Error>> {
    let mut argv = env::args().skip(1);
    let folder = argv.next().ok_or("Expected output directory")?;
    if argv.next().is_some() {
        return Err("Unexpected argument".into());
    }
    let output = Path::new(&folder);
    fs::create_dir_all(output)?;

    for &(label, angle_token) in CASES {
        let qasm_text = format!(
            "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz({angle_token}) q[0];\n"
        );
        fs::write(output.join(format!("{label}.qasm")), qasm_text.as_bytes())?;
        let (ops, num_qubits) = qasm::parse_qasm_str(&qasm_text)?;
        if num_qubits != 1 {
            return Err("RZ boundary fixture changed its qubit count".into());
        }
        let (num, denom) = match ops.as_slice() {
            [QuantumOp::RZ(0, angle)] if angle.symbols.is_empty() => {
                (angle.constant.numer, angle.constant.denom)
            }
            _ => return Err("Parsed Rust QASM circuit was not exactly one RZ".into()),
        };

        let mut ps = PathSum::new(num_qubits);
        ps.set_auto_reduce(false);
        // WmcOnly uses this interleaving to construct the unmodified miter;
        // this is only a pre-WMC semantic probe, with no count or solver call.
        let result = VerificationStrategy::Naive.run(ps, &[], &ops);
        let identity_after_pathsum = result.is_identity();
        let phase_terms = result.p.terms.len();
        if denom <= 0 {
            return Err("Invalid Rust Angle denominator".into());
        }
        println!(
            "ANGLE_BOUNDARY\t{label}\t{angle_token}\t{num}\t{denom}\t{num_qubits}\t{phase_terms}\t{identity_after_pathsum}"
        );
    }
    Ok(())
}
