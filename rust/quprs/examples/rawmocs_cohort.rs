//! Bounded full native Hybrid cohort; distinguish RR-only, timeout and numerical result.
use quprs::{check_equivalence_with_options,qasm,VerificationOptions,VerificationStrategy};
fn main() -> anyhow::Result<()> {
    let a: Vec<_> = std::env::args().collect();
    anyhow::ensure!(a.len()==5,"usage: rawmocs_cohort lhs rhs solver timeout");
    anyhow::ensure!(matches!(a[3].as_str(),"gpmc"|"rawmocs"),"unknown solver");
    let (lhs,n)=qasm::parse_file(std::path::Path::new(&a[1])).map_err(|e|anyhow::anyhow!("{e}"))?;
    let (rhs,m)=qasm::parse_file(std::path::Path::new(&a[2])).map_err(|e|anyhow::anyhow!("{e}"))?;
    anyhow::ensure!(n==m,"qubit mismatch");
    let opt=VerificationOptions {tool_name:a[3].clone(),strategy:VerificationStrategy::Proportional,timeout_secs:a[4].parse()?,..VerificationOptions::default()};
    let r=check_equivalence_with_options(n,&lhs,&rhs,&opt)?;
    let norm_twice = n.checked_add(r.final_ps.v.path_vars.len()).ok_or_else(||anyhow::anyhow!("normalization overflow"))?;
    println!("COHORT_RESULT {}\t{}\t{:.9}\t{:.9}\t{:.9}\t{:.9}\t{}",r.equivalent(),r.solver_invoked,r.verification_time,r.pathsum_time,r.to_dimacs_time.unwrap_or(-1.),r.tool_time.unwrap_or(-1.),norm_twice);
    Ok(())
}
