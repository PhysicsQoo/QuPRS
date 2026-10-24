//! Emit source-tagged native weighted-CNF fixtures and run each named solver.
use std::{env, fs, path::Path};
use pathsum::{qasm, wmc::WmcManager, PathSum, VerificationStrategy};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args().skip(1);
    let folder = args.next().ok_or("Expected output directory")?;
    if args.next().is_some() { return Err("Unexpected argument".into()); }
    let dir = Path::new(&folder);
    fs::create_dir_all(dir)?;
    let cases = [
        ("hh", "h q[0];\nh q[0];\n"),
        ("x", "x q[0];\n"),
        ("t", "t q[0];\n"),
    ];
    for (name, gates) in cases {
        let qasm = format!(
            "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{}",
            gates
        );
        fs::write(dir.join(format!("{name}.qasm")), qasm.as_bytes())?;
        let (ops, n) = qasm::parse_qasm_str(&qasm)?;
        if n != 1 { return Err("Unexpected qubit count".into()); }
        let mut ps = PathSum::new(n);
        ps.set_auto_reduce(false);
        let source = VerificationStrategy::Naive.run(ps, &[], &ops);
        let mut manager = WmcManager::new(&source);
        manager.encode_trace(&source);
        for solver in ["gpmc", "ganak"] {
            let cnf = manager.to_dimacs_string(solver);
            fs::write(dir.join(format!("{name}-{solver}.cnf")), cnf.as_bytes())?;
            let native = manager.solve(solver)?;
            if !native.re.is_finite() || !native.im.is_finite() {
                return Err("Non-finite native count".into());
            }
            println!(
                "WMC_CONFORMANCE\t{name}\t{solver}\t{:.17e}\t{:.17e}",
                native.re, native.im,
            );
        }
    }
    Ok(())
}
