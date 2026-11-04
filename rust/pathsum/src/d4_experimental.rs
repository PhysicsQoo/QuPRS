//! QOO-157 research-only native d4 transport. Not part of the default build.
//! Requires --features experimental-d4 and a deliberately supplied external
//! executable; the feature MUST NOT be enabled for release wheels.
use anyhow::{anyhow, bail, Context, Result};
use num_complex::Complex;
use num_traits::ToPrimitive;
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::Path;
use std::time::Instant;

use crate::precision_count::{self, PrintedCount};
use crate::solver_adapter::{SolverAdapter, SolverCapabilities, WeightGrammar};

pub(crate) struct D4ExperimentalAdapter;
pub(crate) static D4: D4ExperimentalAdapter = D4ExperimentalAdapter;
const UPSTREAM_SHA: &str = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690";
const PREFIX_FLOAT: &str = "c s exact arb float";
const PREFIX_INT: &str = "c s exact arb int";

fn result_line(line: &str) -> Result<Option<PrintedCount>> {
    let kind_and_tail = [(PREFIX_FLOAT, false), (PREFIX_INT, true)]
        .into_iter()
        .find_map(|(prefix, integer)| {
            line.strip_prefix(prefix)
                .filter(|tail| tail.starts_with(char::is_whitespace))
                .map(|tail| (prefix, integer, tail))
        });
    let Some((prefix, integer, raw)) = kind_and_tail else {
        if line.starts_with("c s exact arb") {
            bail!("Unsupported d4 count dialect");
        }
        return Ok(None);
    };
    let clean: String = raw.chars().filter(|c| !c.is_whitespace()).collect();
    if clean.len() > 512 || clean.is_empty() || clean.contains('/') {
        bail!("Malformed or oversized d4 decimal count");
    }
    if integer && !{
        let digits = clean.strip_prefix('-')
            .or_else(|| clean.strip_prefix('+')).unwrap_or(&clean);
        !digits.is_empty() && digits.bytes().all(|c| c.is_ascii_digit())
    } {
        bail!("Malformed d4 integer count");
    }
    let mut parsed = precision_count::parse_line(&format!(
        "c s exact octuple float {clean}"
    ))?.ok_or_else(|| anyhow!("Unrecognized d4 count format"))?;
    if integer && parsed.imag != num_rational::BigRational::from_integer(0.into()) {
        bail!("d4 integer output contains nonzero imaginary component");
    }
    parsed.format_name = prefix.to_string();
    Ok(Some(parsed))
}

fn parse_d4_stdout(stdout: &str) -> Result<Option<PrintedCount>> {
    if stdout.len() > 1_048_576 {
        bail!("d4 stdout exceeds transport limit");
    }
    let mut found: Option<PrintedCount> = None;
    for line in stdout.lines() {
        if let Some(value) = result_line(line)? {
            if let Some(previous) = found.as_mut() {
                if previous.real != value.real || previous.imag != value.imag {
                    bail!("Conflicting d4 weighted model counts");
                }
                if previous.real_half_unit < value.real_half_unit {
                    previous.real_half_unit = value.real_half_unit;
                }
                if previous.imag_half_unit < value.imag_half_unit {
                    previous.imag_half_unit = value.imag_half_unit;
                }
            } else {
                found = Some(value);
            }
        }
    }
    Ok(found)
}

fn check_deadline(deadline: Option<Instant>) -> Result<()> {
    if deadline.is_some_and(|instant| Instant::now() >= instant) {
        return Err(anyhow!(crate::solver_process::SolverTimeout));
    }
    Ok(())
}

impl SolverAdapter for D4ExperimentalAdapter {
    fn id(&self) -> &'static str { "d4" }
    fn arguments(&self) -> &'static [&'static str] { &["-i"] }
    fn capabilities(&self) -> SolverCapabilities {
        SolverCapabilities {
            complex_weights: true,
            exact_count_certificate: false,
            grammar: WeightGrammar::Pair,
        }
    }
    fn executable_path(&self) -> String {
        std::env::var("QUPRS_D4_PATH").unwrap_or_default()
    }
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
        crate::solver_adapter::GpmcAdapter.weight_lines(var, weight)
    }
    fn preflight(&self, path: &str, deadline: Option<Instant>) -> Result<()> {
        check_deadline(deadline)?;
        if path.trim().is_empty() {
            bail!("QUPRS_D4_PATH must explicitly identify an external binary");
        }
        if std::env::var("QUPRS_D4_UPSTREAM_SHA").as_deref() != Ok(UPSTREAM_SHA) ||
           std::env::var("QUPRS_D4_SOURCE_PATCH_ACK").as_deref() != Ok("1") {
            bail!("d4 pinned source and research-only precision patch not acknowledged");
        }
        let bits: u32 = std::env::var("QUPRS_D4_PREPARSE_BITS")
            .context("Missing external d4 GMP preparse bits")?.parse()?;
        if !(128..=2048).contains(&bits) {
            bail!("d4 GMP preparse precision is not accepted");
        }
        let expected = std::env::var("QUPRS_D4_SHA256")
            .context("Missing expected external d4 SHA-256")?;
        if expected.len() != 64 || !expected.bytes().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()) {
            bail!("Malformed expected external d4 SHA-256");
        }
        let executable = Path::new(path);
        let mut source = std::fs::File::open(executable)
            .with_context(|| format!("Cannot open external d4 binary: {path}"))?;
        let mut hash = Sha256::new();
        let mut buffer = [0_u8; 32768];
        loop {
            check_deadline(deadline)?;
            let count = source.read(&mut buffer)?;
            if count == 0 { break; }
            hash.update(&buffer[..count]);
        }
        check_deadline(deadline)?;
        let actual = format!("{:x}", hash.finalize());
        if actual != expected { bail!("d4 external binary SHA-256 mismatch"); }
        Ok(())
    }
    fn parse_count(&self, stdout: &str) -> Result<Option<Complex<f64>>> {
        let Some(count) = parse_d4_stdout(stdout)? else { return Ok(None); };
        let real = count.real.to_f64().ok_or_else(|| anyhow!("d4 real count outside f64"))?;
        let imag = count.imag.to_f64().ok_or_else(|| anyhow!("d4 imag count outside f64"))?;
        if !real.is_finite() || !imag.is_finite() {
            bail!("Non-finite d4 projected count");
        }
        Ok(Some(Complex::new(real, imag)))
    }
    fn parse_printed_count(&self, stdout: &str) -> Result<Option<PrintedCount>> {
        parse_d4_stdout(stdout)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use num_rational::BigRational;

    #[test]
    fn d4_only_optin_and_complex_pair_grammar() {
        let adapter = crate::solver_adapter::adapter_for("d4").unwrap();
        assert_eq!(adapter.id(), "d4");
        assert_eq!(adapter.arguments(), &["-i"]);
        assert_eq!(adapter.capabilities().grammar, WeightGrammar::Pair);
        assert!(!adapter.capabilities().exact_count_certificate);
        assert!(adapter.weight_lines(1, Complex::new(0.5, -0.25)).0.contains(" -2.5000000000000000e-1 0"));
    }

    #[test]
    fn decimal_transport_preserves_small_complex_values_without_f64_rounding() {
        let text = "c s exact arb float 1.000000000000000000000000000000000000001e-40-2.5e-60i\n";
        let count = D4.parse_printed_count(text).unwrap().unwrap();
        assert_eq!(count.format_name, PREFIX_FLOAT);
        assert!(count.real > BigRational::from_integer(0.into()));
        assert!(count.imag < BigRational::from_integer(0.into()));
        assert!(count.real_half_unit > BigRational::from_integer(0.into()));
        assert!(!D4.capabilities().exact_count_certificate);
    }

    #[test]
    fn int_real_duplicate_and_malformed_counts_fail_closed() {
        let found = D4.parse_printed_count("c s exact arb int 8\n").unwrap().unwrap();
        assert_eq!(found.real, BigRational::from_integer(8.into()));
        assert_eq!(found.imag, BigRational::from_integer(0.into()));
        for invalid in [
            "c s exact arb float NaN+0i",
            "c s exact arb int 8.0",
            "c s exact arb float 1/2+0i",
            "c s exact arb float 1e9999+0i",
            "c s exact arb cpx 1+0i",
            "c s exact arb int 8\nc s exact arb int 9",
        ] {
            assert!(D4.parse_printed_count(invalid).is_err(), "Accepted {invalid:?}");
        }
        assert!(D4.parse_printed_count("no count").unwrap().is_none());
    }
}
