//! Private attribution executable; never part of the production PR.
use pathsum::{check_equivalence, VerificationMethod, VerificationStrategy};
use std::{env, path::PathBuf, time::Instant};
fn opt(v: Option<f64>) -> String { v.map(|x| format!("{x:.12}")).unwrap_or("null".into()) }
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<String> = env::args().collect();
    let case = a.get(1).ok_or("case argument required")?;
    let solver = a.get(2).ok_or("solver argument required")?;
    if solver != "ganak" && solver != "gpmc" { return Err("solver must be ganak or gpmc".into()); }
    let warmups: usize = a.get(3).map(|x| x.parse()).transpose()?.unwrap_or(1);
    let (file, strategy, switch) = match case.as_str() {
        "qft16" => ("qft_nativegates_ibm_qiskit_opt0_16.qasm", VerificationStrategy::Proportional, true),
        "qaoa7" => ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", VerificationStrategy::Proportional, false),
        "ghz32" => ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", VerificationStrategy::Straightforward, true),
        "graphstate16" => ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", VerificationStrategy::Naive, false),
        "grover4" => ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", VerificationStrategy::Proportional, true),
        _ => return Err("unknown case".into()),
    };
    let root = PathBuf::from(env::var("QUPRS_CASE_ROOT")?);
    let p1 = root.join(file); let p2 = root.join("h,ry,rz,cx").join(file);
    let (p1,p2) = if switch { (p2,p1) } else { (p1,p2) };
    let (g1,n1) = pathsum::qasm::parse_file(&p1)?;
    let (g2,n2) = pathsum::qasm::parse_file(&p2)?;
    if n1 != n2 { return Err("different circuit widths".into()); }
    // Explicitly suppress trace output during warmup, then restore only for measured call.
    let trace = env::var_os("QUPRS_TRACE_PATH"); env::remove_var("QUPRS_TRACE_PATH");
    for _ in 0..warmups { let r = check_equivalence(n1,&g1,&g2,VerificationMethod::Hybrid,strategy,solver,999999)?; if !matches!(r.status, pathsum::EquivalenceStatus::Equivalent | pathsum::EquivalenceStatus::EquivalentUpToGlobalPhase) { return Err(format!("warmup status {}", r.status).into()); } }
    if let Some(p) = trace { env::set_var("QUPRS_TRACE_PATH", p); }
    let rss_reset = std::fs::write("/proc/self/clear_refs", "5").is_ok();
    let start = Instant::now();
    let r = check_equivalence(n1,&g1,&g2,VerificationMethod::Hybrid,strategy,solver,999999)?;
    let outer = start.elapsed().as_secs_f64();
    let rss = std::fs::read_to_string("/proc/self/status").ok().and_then(|s| s.lines().find(|l| l.starts_with("VmHWM:")).and_then(|l| l.split_whitespace().nth(1)).and_then(|x| x.parse::<u64>().ok()));
    let rss = rss.map(|x| x.to_string()).unwrap_or("null".into());
    let overhead = r.wmc_time.map(|x| x-r.to_dimacs_time.unwrap_or(0.0)-r.tool_time.unwrap_or(0.0));
    println!("{{\"case\":\"{}\",\"solver\":\"{}\",\"status\":\"{}\",\"qubits\":{},\"ket_gates\":{},\"bra_gates\":{},\"strategy_seconds\":{:.12},\"dimacs_seconds\":{},\"solver_seconds\":{},\"wmc_seconds\":{},\"wmc_encoding_and_management_seconds\":{},\"engine_total_seconds\":{:.12},\"outer_seconds\":{:.12},\"process_peak_rss_kib\":{},\"rss_reset_after_warmup\":{},\"final_path_vars\":{},\"final_terms\":{}}}",case,solver,r.status,n1,g1.len(),g2.len(),r.pathsum_time,opt(r.to_dimacs_time),opt(r.tool_time),opt(r.wmc_time),opt(overhead),r.verification_time,outer,rss,rss_reset,r.final_ps.v.path_vars.len(),r.final_ps.p.terms.len());
    if !matches!(r.status, pathsum::EquivalenceStatus::Equivalent | pathsum::EquivalenceStatus::EquivalentUpToGlobalPhase) { std::process::exit(2); }
    Ok(())
}
