//! Read-only public API timing adapter, copied verbatim to pinned main checkout.
use quprs::{check_equivalence_with_options, qasm::parse_qasm_str, VerificationOptions, VerificationMethod, VerificationStrategy};
use std::time::Instant;

#[cfg_attr(test,test)]
pub fn cpr_public_hybrid() {
    let start = Instant::now();
    let (a,n)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_SOURCE").unwrap()).unwrap()).unwrap();
    let (b,m)=parse_qasm_str(&std::fs::read_to_string(std::env::var("CRR_TARGET").unwrap()).unwrap()).unwrap();
    assert_eq!(n,m);
    let parse=start.elapsed().as_secs_f64();
    let opts=VerificationOptions {
        method:VerificationMethod::Hybrid, strategy:VerificationStrategy::Difference,
        tool_name:"gpmc".into(), timeout_secs:27, rr_tolerance:0.0,
        phase_tolerance:1e-8, wmc_phase_tolerance:1e-8,
        approximate_distance_tolerance:Some(1e-8), gpmc_precision_digits:90,
    };
    match check_equivalence_with_options(n,&a,&b,&opts) {
        Ok(r)=>println!("CPR_PUBLIC status={:?} total_s={} parse_s={} verify_s={} construct_s={} prepare_s={:?} solve_s={:?} wmc_s={:?} solver={} rr_approximate={} precision_reason={:?}",
            r.status,start.elapsed().as_secs_f64(),parse,r.verification_time,r.pathsum_time,r.to_dimacs_time,r.tool_time,r.wmc_time,r.solver_invoked,r.rr_approximate,r.wmc_precision_reason),
        Err(e)=>println!("CPR_PUBLIC_ERROR {e:#}"),
    }
}
