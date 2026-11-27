//! D1 structural census using the unchanged public native EQ implementation.
//! No new RR, encoder or solver. The returned PathSum is the actual final miter.
use anyhow::{ensure, Result};
use quprs::{QuantumCircuit, PathSum, VerificationOptions, VerificationMethod, VerificationStrategy};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, io::{BufWriter, Write}, path::Path};

fn snapshot(ps: &PathSum, path: &Path) -> Result<()> {
    let mut w = BufWriter::new(fs::File::create(path)?);
    let mut vars: Vec<_> = ps.v.path_vars.iter().copied().collect();
    vars.sort_unstable();
    let mut continuous: Vec<_> = ps.v.continuous_vars.iter().copied().collect();
    continuous.sort_unstable();
    writeln!(w, "n\t{}\nh\t{}\nvars\t{:?}\ncontinuous\t{:?}\nrr_approximate\t{}\nrr_tol_bits\t{:016x}",
        ps.v.num_qubits, vars.len().checked_sub(ps.v.num_qubits).ok_or_else(|| anyhow::anyhow!("invalid primary domain"))?,
        vars, continuous, ps.rr_approximate, ps.rr_tolerance.to_bits())?;
    let mut phase: Vec<_> = ps.p.terms.iter().collect();
    phase.sort_by(|a,b| a.0.cmp(b.0));
    for (m,c) in phase {
        // Explicit exact fields rather than floating weights or HashMap Debug order.
        writeln!(w, "p\t{:?}\t{}\t{}\t{:?}\t{:?}", m, c.constant.numer, c.constant.denom, c.radians, c.symbols)?;
    }
    for (i, f) in ps.f.functions.iter().enumerate() {
        writeln!(w, "output\t{i}")?;
        let mut terms: Vec<_> = f.iter().collect();
        terms.sort_unstable();
        for m in terms { writeln!(w, "f\t{i}\t{:?}", m)?; }
    }
    w.flush()?;
    Ok(())
}
fn census(ps: &PathSum) {
    let mut uses: BTreeMap<&[u32], (usize,usize)> = BTreeMap::new();
    let mut pdegree = BTreeMap::<usize,usize>::new();
    let mut fdegree = BTreeMap::<usize,usize>::new();
    let mut phase_classes = BTreeMap::<&str,usize>::new();
    let mut common_factor_outputs = 0;
    for (m,c) in &ps.p.terms {
        uses.entry(m.as_slice()).or_default().0 += 1;
        *pdegree.entry(m.len()).or_default() += 1;
        let kind = if !c.symbols.is_empty() { "symbolic" }
            else if c.radians.is_some() { "source_radians" }
            else if c.constant.denom <= 2 { "sign_or_identity" }
            else if c.constant.denom > 0 && 8 % c.constant.denom == 0 { "nonreal_z8" }
            else { "general_rational" };
        *phase_classes.entry(kind).or_default() += 1;
    }
    for f in &ps.f.functions {
        // Count variable incidences, not all pairs/subsets (bounded linear scan).
        let mut factors = BTreeMap::<u32,usize>::new();
        for m in f {
            uses.entry(m.as_slice()).or_default().1 += 1;
            *fdegree.entry(m.len()).or_default() += 1;
            for &v in m { *factors.entry(v).or_default() += 1; }
        }
        if factors.values().any(|&n| n >= 2) { common_factor_outputs += 1; }
    }
    let repeated = uses.iter().filter(|(m,(p,f))| m.len() >= 2 && p+f >= 2).count();
    let cross = uses.iter().filter(|(m,(p,f))| m.len() >= 2 && *p > 0 && *f > 0).count();
    let output_reuses: usize = uses.iter().filter(|(m,_)| m.len()>=2).map(|(_,(_,f))| f.saturating_sub(1)).sum();
    let output_terms: usize = fdegree.values().sum();
    println!("D1_METRICS\tphase_terms={}\toutput_terms={output_terms}\tunique_monomials={}\trepeated_nonlinear={repeated}\tphase_output_overlap={cross}\toutput_and_reuses={output_reuses}\tcommon_factor_outputs={common_factor_outputs}\tphase_degree={pdegree:?}\toutput_degree={fdegree:?}\tphase_classes={phase_classes:?}", ps.p.terms.len(), uses.len());
}
fn main() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    ensure!(a.len()==7, "left right mode strategy timeout snapshot");
    let left=QuantumCircuit::from_qasm_file(&a[1])?;
    let right=QuantumCircuit::from_qasm_file(&a[2])?;
    let method=match a[3].as_str() {"hybrid"=>VerificationMethod::Hybrid,"wmc_only"=>VerificationMethod::WmcOnly,_=>anyhow::bail!("invalid mode")};
    let strategy=match a[4].as_str() {"proportional"=>VerificationStrategy::Proportional,"naive"=>VerificationStrategy::Naive,"straightforward"=>VerificationStrategy::Straightforward,"difference"=>VerificationStrategy::Difference,_=>anyhow::bail!("invalid strategy")};
    let opts=VerificationOptions{method,strategy,timeout_secs:a[5].parse()?,..VerificationOptions::default()};
    let res=quprs::verification::check_equivalence(&left,&right,&opts)?;
    let ps=res.final_pathsum();
    println!("D1_RESULT\tverdict={}\tsolver_invoked={}\tpathsum_s={}\tverification_s={}\ttool_s={:?}\twmc_s={:?}\tserialize_s={:?}\trr_approximate={}\tprecision_reason={:?}",res.equivalent(),res.wmc_solver_invoked(),res.pathsum_time,res.verification_time,res.tool_time,res.wmc_time,res.to_dimacs_time,res.rr_approximate,res.wmc_precision_reason);
    snapshot(ps,Path::new(&a[6]))?;
    let mut hash = Sha256::new();
    let mut input = fs::File::open(&a[6])?;
    let mut buf = [0u8; 65536];
    loop {
        let n = std::io::Read::read(&mut input, &mut buf)?;
        if n == 0 { break; }
        hash.update(&buf[..n]);
    }
    println!("D1_SNAPSHOT\tsha256={:x}",hash.finalize());
    census(ps);
    Ok(())
}
