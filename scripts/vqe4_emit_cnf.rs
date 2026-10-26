//! Opt-in VQE4 actual miter CNF export, matching Hybrid proportional strategy.
use pathsum::{qasm, pathsum::Register, PathSum, VerificationStrategy, wmc::WmcManager};
use std::{env, fs, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 3 { return Err("Expected: output_dir left.qasm right.qasm".into()); }
    let output = PathBuf::from(&args[0]);
    fs::create_dir_all(&output)?;
    let (left, n) = qasm::parse_file(std::path::Path::new(&args[1]))?;
    let (right, other_n) = qasm::parse_file(std::path::Path::new(&args[2]))?;
    if n != other_n || n != 4 { return Err("VQE4 inputs must share exactly four qubits".into()); }
    let regs = vec![Register::new("q", n)];
    let mut ps = PathSum::quantum_circuit(&regs, None);
    ps.set_auto_reduce(true);
    let mut miter = VerificationStrategy::Proportional.run(ps, &left, &right);
    miter.full_reduce();
    let mut coeffs: Vec<String> = miter.p.terms.iter().map(|(mono, coeff)| {
        let mut canonical_mono = mono.clone();
        canonical_mono.sort_unstable();
        format!("{:?}\t{}", canonical_mono, coeff)
    }).collect();
    coeffs.sort();
    fs::write(output.join("phase-signatures.tsv"), coeffs.join("\n") + "\n")?;
    let metadata = format!(
        "qubits\t{}\nleft_gates\t{}\nright_gates\t{}\npathvars\t{}\nphase_terms\t{}\nreduced_identity_up_to_phase\t{}\n",
        n, left.len(), right.len(), miter.v.path_vars.len(),
        miter.p.terms.len(), miter.is_identity_up_to_phase()
    );
    fs::write(output.join("miter-metadata.tsv"), metadata)?;
    let mut manager = WmcManager::new(&miter);
    manager.encode_trace(&miter)?;
    for solver in ["ganak", "gpmc"] {
        let cnf = manager.to_dimacs_string(solver);
        fs::write(output.join(format!("vqe4-{solver}.cnf")), cnf.as_bytes())?;
        println!("VQE4_CNF solver={solver} bytes={}", cnf.len());
    }
    Ok(())
}
