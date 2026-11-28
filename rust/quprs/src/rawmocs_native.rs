//! Optional registry-pinned RaWMoCS library transport.
use anyhow::{ensure, Result};
use crate::{NativeCounterError, precision_count::{rawmocs_count_from_parts, PrintedCount}};
use rawmocs_mpfr::{solve_text, FailureKind, SolveOptions, Precision};
use std::time::Duration;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Signed;

pub(crate) fn solve(cnf: &str, budget: Duration) -> std::result::Result<PrintedCount, NativeCounterError> {
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

