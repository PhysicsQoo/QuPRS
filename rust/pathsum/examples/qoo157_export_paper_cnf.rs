//! QOO-157 bounded research-only source-QASM -> WMC-only paired CNF exporter.
//! The comparison solver receives EXACTLY the same CNF bytes, not a rewritten
//! source circuit or an independently serialized d4-specific interpretation.
use anyhow::{anyhow, bail, Result};
use pathsum::{PathSum, VerificationStrategy, wmc::WmcManager, qasm::parse_qasm_str};
use sha2::{Sha256, Digest};
use std::{fs, path::PathBuf};

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 4 { bail!("usage: qoo157_export_paper_cnf CASE FIRST.QASM SECOND.QASM OUTDIR"); }
    let (label, first, second, outdir) = (&args[0], PathBuf::from(&args[1]), PathBuf::from(&args[2]), PathBuf::from(&args[3]));
    if !label.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-') {
        bail!("invalid research case label");
    }
    let first_bytes = fs::read(&first)?;
    let second_bytes = fs::read(&second)?;
    let (ket, a) = parse_qasm_str(std::str::from_utf8(&first_bytes)?).map_err(|e| anyhow!(e))?;
    let (bra, b) = parse_qasm_str(std::str::from_utf8(&second_bytes)?).map_err(|e| anyhow!(e))?;
    if a != b || a == 0 { bail!("mismatched quantum register sizes"); }
    let mut ps = PathSum::new(a);
    ps.set_auto_reduce(false); // WMC-only: never bias one solver via RR.
    let miter = VerificationStrategy::Straightforward.run(ps, &ket, &bra);
    let mut counter = WmcManager::new(&miter);
    counter.encode_trace(&miter)?;
    let cnf = counter.to_dimacs_string("gpmc");
    if !cnf.starts_with("p cnf ") || !cnf.contains("c t wmc") {
        bail!("unexpected QuPRS complex-WMC CNF serialization");
    }
    if cnf.len() > 12_000_000 {
        bail!("source CNF over 12 MB, exclude resource-risk case from CodSpeed pilot");
    }
    fs::create_dir_all(&outdir)?;
    let file = outdir.join(format!("{label}.cnf"));
    fs::write(&file, &cnf)?;
    let digest = |bytes: &[u8]| -> String { format!("{:x}", Sha256::digest(bytes)) };
    println!(
        "QOO157_CNF_SOURCE case={label} qubits={a} ket_gates={} bra_gates={} input_a_sha={} input_b_sha={} cnf_sha={} cnf_bytes={}",
        ket.len(), bra.len(), digest(&first_bytes), digest(&second_bytes),
        digest(cnf.as_bytes()), cnf.len()
    );
    Ok(())
}
