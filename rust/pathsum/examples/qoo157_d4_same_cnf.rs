//! QOO-157 same-byte-input Python/Rust d4 printed-count parity pilot.
//! Research-only, requires --features experimental-d4.
use anyhow::{anyhow, Result};
use pathsum::{PathSum, wmc::WmcManager};
use sha2::{Digest, Sha256};
use std::{fs, path::Path, time::{Duration, Instant}};

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 6 {
        return Err(anyhow!("expected exactly six SHA-pinned QuPRS emitted CNF paths"));
    }
    let ps = PathSum::new(0);
    let manager = WmcManager::new(&ps);
    for file in args {
        let path = Path::new(&file);
        let content = fs::read_to_string(path)?;
        let digest = format!("{:x}", Sha256::digest(content.as_bytes()));
        let count = manager.experimental_d4_count_prepared_cnf(
            &content, Some(Instant::now() + Duration::from_secs(30)),
        )?;
        let name = path.file_name().ok_or_else(|| anyhow!("empty CNF name"))?
            .to_str().ok_or_else(|| anyhow!("non UTF-8 CNF name"))?;
        println!(
            "QOO157_RUST_SAME_CNF\t{name}\t{digest}\t{}\t{}\t{}\t{}",
            count.real, count.imag, count.real_half_unit, count.imag_half_unit,
        );
    }
    Ok(())
}
