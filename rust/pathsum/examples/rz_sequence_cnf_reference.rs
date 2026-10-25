//! Research-only exporter for six source-RZ relative circuits on the existing Rust WMC trace encoder.
//!
//! This example does not modify the library or the solver. It emits exactly
//! WmcManager::to_dimacs_string(), alongside the Rust phase-coefficient source
//! used to produce each printed f64 weight. No production result is inferred.
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::Path;
use pathsum::{qasm, PathSum, VerificationStrategy, wmc::WmcManager};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args().skip(1);
    let dir = args.next().ok_or("Expected output directory")?;
    if args.next().is_some() { return Err("Unexpected argument".into()); }
    let folder = Path::new(&dir);
    fs::create_dir_all(folder)?;

    let cases = [
        ("positive_rotation", "rz(0.0002) q[0];\n"),
        ("negative_rotation", "rz(-0.0002) q[0];\n"),
        ("accumulated_rotation", "rz(0.0002) q[0];\nrz(0.0002) q[0];\n"),
        ("exact_cancellation", "rz(0.0002) q[0];\nrz(-0.0002) q[0];\n"),
        ("identical_paths", "rz(-0.0002) q[0];\nrz(0.0002) q[0];\n"),
        ("nearly_cancelled", "rz(0.0002) q[0];\nrz(-0.000199999) q[0];\n"),
    ];
    for (name, gates) in cases {
        let source = format!(
            "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{}",
            gates
        );
        fs::write(folder.join(format!("{name}.qasm")), source.as_bytes())?;
        let (ops, num_qubits) = qasm::parse_qasm_str(&source)?;
        if num_qubits != 1 { return Err("Unexpected qubit count".into()); }
        let mut base = PathSum::new(num_qubits);
        base.set_auto_reduce(false);
        // This is exactly the strategy call used by the Rust WMC-only path.
        let ps = VerificationStrategy::Naive.run(base, &[], &ops);
        let paths = ps.v.path_vars.len()
            .checked_sub(num_qubits)
            .ok_or("Rust path-variable count underflow")?;
        let mut manager = WmcManager::new(&ps);
        manager.encode_trace(&ps);

        // Reconstruct the phase variable ordering from the actual encoding
        // loop (weight variable first, then newly seen monomial variables).
        // The same ps object and iteration order are used to generate the
        // DIMACS content immediately below. Fail downstream on any mismatch.
        let mut var_map: HashMap<u32, i32> = HashMap::new();
        let mut next: i32 = 1;
        let mut phase_records = String::from(
            "weight_lit\tphase_numerator\tphase_denominator\tmonomial\n"
        );
        for (monomial, coefficient) in &ps.p.terms {
            if !coefficient.symbols.is_empty() {
                return Err("Symbolic phase coefficients require separate reference".into());
            }
            let weight_var = next;
            next += 1;
            for &path_var in monomial {
                if let std::collections::hash_map::Entry::Vacant(e) = var_map.entry(path_var) {
                    e.insert(next);
                    next += 1;
                }
            }
            let monomial_id = monomial.iter()
                .map(|v| v.to_string()).collect::<Vec<_>>().join(",");
            phase_records.push_str(&format!(
                "{weight_var}\t{}\t{}\t{monomial_id}\n",
                coefficient.constant.numer, coefficient.constant.denom
            ));
        }
        for tool in ["gpmc", "ganak"] {
            let content = manager.to_dimacs_string(tool);
            fs::write(folder.join(format!("{name}-{tool}.cnf")), content.as_bytes())?;
            fs::write(
                folder.join(format!("{name}-{tool}-phases.tsv")),
                phase_records.as_bytes()
            )?;
            println!(
                "RUST_RZ_SIX case={name} solver={tool} qubits={num_qubits} pathvars={paths} phase_terms={}",
                ps.p.terms.len()
            );
        }
    }
    Ok(())
}
