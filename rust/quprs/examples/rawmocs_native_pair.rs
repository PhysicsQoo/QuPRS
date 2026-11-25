//! Experimental native verifier benchmark. The solver is an external process.
use quprs::{check_equivalence_with_options, qasm, VerificationOptions, VerificationStrategy};
fn main() -> anyhow::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    anyhow::ensure!(args.len() == 4, "usage: rawmocs_native_pair lhs rhs solver");
    anyhow::ensure!(matches!(args[3].as_str(), "gpmc" | "rawmocs"), "unsupported solver");
    let (a, n) = qasm::parse_file(std::path::Path::new(&args[1])).map_err(|e| anyhow::anyhow!("{e}"))?;
    let (b, m) = qasm::parse_file(std::path::Path::new(&args[2])).map_err(|e| anyhow::anyhow!("{e}"))?;
    anyhow::ensure!(n == m, "qubit mismatch");
    let options = VerificationOptions {
        tool_name: args[3].clone(), strategy: VerificationStrategy::Proportional,
        timeout_secs: 300, ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(n, &a, &b, &options)?;
    println!("NATIVE_VERDICT {} {}", result.equivalent(), result.solver_invoked);
    anyhow::ensure!(matches!(result.equivalent(), "equivalent" | "equivalent*") && result.solver_invoked,
                    "not a completed external-solver positive Hybrid case");
    Ok(())
}
