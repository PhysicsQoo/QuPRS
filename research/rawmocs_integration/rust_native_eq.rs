//! Actual Rust EQ pipeline, with the release-pinned direct Rust library.
use anyhow::{ensure, Result};
use quprs::{check_equivalence_with_options, check_equivalence_with_native_counter,
    NativeCounterError, VerificationOptions, VerificationMethod, VerificationStrategy, EquivalenceStatus};
use quprs::precision_count::{rawmocs_count_from_parts, PrintedCount};
use rawmocs_mpfr::{solve_text, FailureKind, SolveOptions, Precision};
use std::{cell::Cell, time::Duration};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Signed;

fn solve(cnf: &str, budget: Duration) -> std::result::Result<PrintedCount, NativeCounterError> {
    let ms=budget.as_millis().min(86_400_000) as u64;
    if ms==0 { return Err(NativeCounterError::Timeout); }
    let r=solve_text(cnf,SolveOptions { precision: Precision::Digits30, timeout_ms: Some(ms), ..Default::default() })
        .map_err(|e| if e.kind==FailureKind::Timeout { NativeCounterError::Timeout }
                     else { NativeCounterError::Failure(e.into()) })?;
    let checked=(|| -> Result<PrintedCount> {
        ensure!(r.precision==Precision::Digits30);
        let count=rawmocs_count_from_parts(r.sat,&r.real,&r.imag)?;
        for (value,unit,b) in [(&count.real,&count.real_half_unit,r.real_mpfr().binary()),
                              (&count.imag,&count.imag_half_unit,r.imag_mpfr().binary())] {
            ensure!(b.precision_bits==100 && b.exponent2.unsigned_abs()<=16384);
            let n:BigInt=b.significand.parse()?;
            let shift=b.exponent2.unsigned_abs() as usize;
            let exact=if b.exponent2>=0 { BigRational::from_integer(n<<shift) }
                      else { BigRational::new(n,BigInt::from(1)<<shift) };
            ensure!((exact-value).abs()<=*unit);
        }
        Ok(count)
    })();
    checked.map_err(NativeCounterError::Failure)
}

fn main() -> Result<()> {
    let prefix="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n";
    let parse=|body:&str| quprs::qasm::parse_qasm_str(&format!("{prefix}{body}")).map(|v|v.0).map_err(|e|anyhow::anyhow!(e));
    let id=parse("")?;
    let eq=parse("h q[0];\nt q[0];\ntdg q[0];\nh q[0];\n")?;
    let neq=parse("h q[0];\n")?;
    let mut calls=0;
    for (name,gates,expected) in [("eq",&eq,EquivalenceStatus::Equivalent),("neq",&neq,EquivalenceStatus::NotEquivalent)] {
        for method in [VerificationMethod::WmcOnly,VerificationMethod::Hybrid,VerificationMethod::ReductionRules] {
            let mut opt=VerificationOptions { method, strategy:VerificationStrategy::Naive,timeout_secs:10,..Default::default() };
            let baseline=check_equivalence_with_options(2,&id,gates,&opt)?;
            let hit=Cell::new(0u32);
            let counter=|cnf:&str,budget:Duration| { hit.set(hit.get()+1); solve(cnf,budget) };
            opt.tool_name="rawmocs_rust_native".into();
            let native=check_equivalence_with_native_counter(2,&id,gates,&opt,&counter)?;
            ensure!(baseline.status==native.status,"{name} {method:?} parity");
            if method!=VerificationMethod::ReductionRules { ensure!(native.status==expected); }
            else if name=="neq" { ensure!(native.status==EquivalenceStatus::Unknown); }
            ensure!(baseline.solver_invoked==native.solver_invoked && hit.get()==u32::from(native.solver_invoked));
            let ledger=native.stage_ledger.as_ref().expect("stage ledger enabled");
            ensure!(ledger.solver_child_spawns==0 && ledger.calls.get("cnf_file_write").copied().unwrap_or(0)==0);
            calls+=hit.get();
            println!("R3_EQ {name} {method:?} {:?} invoked={} child_spawns={}",native.status,native.solver_invoked,ledger.solver_child_spawns);
        }
    }
    ensure!(calls>0);
    let opt=VerificationOptions { method:VerificationMethod::WmcOnly,tool_name:"rawmocs_rust_native".into(),..Default::default() };
    ensure!(check_equivalence_with_options(2,&id,&neq,&opt).is_err());
    let fail=|_:&str,_:Duration| Err(NativeCounterError::Failure(anyhow::anyhow!("injected native failure")));
    ensure!(check_equivalence_with_native_counter(2,&id,&neq,&opt,&fail).is_err());
    let timeout=|_:&str,_:Duration| Err(NativeCounterError::Timeout);
    ensure!(check_equivalence_with_native_counter(2,&id,&neq,&opt,&timeout)?.status==EquivalenceStatus::Timeout);
    ensure!(check_equivalence_with_native_counter(2,&id,&neq,&opt,&solve)?.status==EquivalenceStatus::NotEquivalent);
    println!("R3_DIRECT_RUST_EQ_PASS cases=6 failure_controls=3 reentry=1");
    Ok(())
}
