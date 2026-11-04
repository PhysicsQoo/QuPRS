//! QOO-157 research-only Rust source-to-CNF fixture generator.
//!
//! Run with: cargo run --locked --manifest-path rust/Cargo.toml -p pathsum
//!   --example qoo157_emit_complex_cnf -- /tmp/qoo157-export
//!
//! This calls QuPRS' actual WmcManager/GPMC paired-weight serializer, without
//! changing public solver registration, default selection, or production API.

use anyhow::{anyhow, Result};
use pathsum::ir::QuantumOp;
use pathsum::pathsum::PathSum;
use pathsum::strategy::VerificationStrategy;
use pathsum::wmc::WmcManager;
use std::fs;
use std::path::Path;

fn emit(
    root: &Path,
    name: &str,
    nqubits: usize,
    ket: &[QuantumOp],
    bra: &[QuantumOp],
) -> Result<()> {
    let mut ps = PathSum::new(nqubits);
    ps.set_auto_reduce(false); // WMC-only source: no RR before encoding.
    let miter = VerificationStrategy::Straightforward.run(ps, ket, bra);
    let mut counter = WmcManager::new(&miter);
    counter.encode_trace(&miter)?;
    let weighted_cnf = counter.to_dimacs_string("gpmc");
    if !weighted_cnf.starts_with("p cnf ") || !weighted_cnf.contains("c t wmc") {
        return Err(anyhow!("QuPRS WMC emitted an unexpected weighted-CNF header"));
    }
    let file = root.join(format!("{name}.cnf"));
    fs::write(&file, weighted_cnf.as_bytes())?;
    println!("QOO157_SOURCE_CNF {name} {}", file.display());
    Ok(())
}

fn main() -> Result<()> {
    let target = std::env::args_os().nth(1)
        .ok_or_else(|| anyhow!("pass an explicit output directory"))?;
    let root = Path::new(&target);
    fs::create_dir_all(root)?;

    emit(
        root, "quprs_identity1", 1,
        &[QuantumOp::H(0)], &[QuantumOp::H(0)],
    )?;
    emit(
        root, "quprs_t1_miter", 1,
        &[QuantumOp::H(0), QuantumOp::T(0), QuantumOp::H(0)],
        &[QuantumOp::H(0)],
    )?;
    emit(
        root, "quprs_bell_t_miter", 2,
        &[QuantumOp::H(0), QuantumOp::CX(0, 1), QuantumOp::T(1)],
        &[QuantumOp::H(0), QuantumOp::CX(0, 1)],
    )?;
    Ok(())
}
