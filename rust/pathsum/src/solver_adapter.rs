//! Independent WMC transport contract. No implicit cross-solver fallback.
use anyhow::{anyhow, Result};
use num_complex::Complex;
use std::path::Path;
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum WeightGrammar { Pair, ComplexI }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SolverCapabilities {
    pub complex_weights: bool,
    pub exact_count_certificate: bool,
    pub grammar: WeightGrammar,
}
pub(crate) trait SolverAdapter: Sync {
    fn id(&self) -> &'static str;
    fn arguments(&self) -> &'static [&'static str];
    fn capabilities(&self) -> SolverCapabilities;
    fn executable_path(&self) -> String;
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String);
    fn preflight(&self, _path: &str, _deadline: Option<Instant>) -> Result<()> { Ok(()) }
    fn parse_count(&self, stdout: &str) -> Result<Option<Complex<f64>>> {
        let mut count = None;
        for line in stdout.lines() {
            if let Some(value) = crate::wmc::parse_count_line(line)? {
                if count.is_some_and(|previous| previous != value) {
                    return Err(anyhow!("{} WMC output contains conflicting counts", self.id()));
                }
                count = Some(value);
            }
        }
        Ok(count)
    }
}
pub(crate) struct GpmcAdapter;
pub(crate) struct GanakAdapter;
#[cfg(feature = "experimental-d4")]
pub(crate) struct D4ResearchAdapter;
/// Optional 90-digit GPMC arithmetic; default complex GPMC uses 30 digits.
pub(crate) struct GpmcDistanceHighPrecisionAdapter;
static GPMC: GpmcAdapter = GpmcAdapter;
static GANAK: GanakAdapter = GanakAdapter;
#[cfg(feature = "experimental-d4")]
static D4_RESEARCH: D4ResearchAdapter = D4ResearchAdapter;
static GPMC_DISTANCE_HIGH: GpmcDistanceHighPrecisionAdapter = GpmcDistanceHighPrecisionAdapter;
pub(crate) fn adapter_for(id: &str) -> Result<&'static dyn SolverAdapter> {
    match id {
        "gpmc" => Ok(&GPMC),
        "ganak" => Ok(&GANAK),
        #[cfg(feature = "experimental-d4")]
        "d4-poc" => Ok(&D4_RESEARCH),
        _ => Err(anyhow!(crate::solver_result::SolverFailure::new(
            crate::solver_result::SolverFailureKind::Unsupported,
            id,
            format!("Unsupported tool name: {}", id),
        ))),
    }
}
/// GPMC works at its effective 30-digit default unless 90 is requested.
pub(crate) fn distance_adapter_for(id: &str, digits: u32) -> Result<&'static dyn SolverAdapter> {
    match (id, digits) {
        ("gpmc", 30) => Ok(&GPMC),
        ("gpmc", 90) => Ok(&GPMC_DISTANCE_HIGH),
        ("gpmc", _) => Err(anyhow!("gpmc_precision_digits must be 30 or 90")),
        (_, 30) => adapter_for(id),
        _ => Err(anyhow!("gpmc_precision_digits=90 only applies to GPMC")),
    }
}
impl SolverAdapter for GpmcDistanceHighPrecisionAdapter {
    fn id(&self) -> &'static str { "gpmc" }
    fn arguments(&self) -> &'static [&'static str] { &["-mode=1", "-prec=90"] }
    fn capabilities(&self) -> SolverCapabilities { GpmcAdapter.capabilities() }
    fn executable_path(&self) -> String { GpmcAdapter.executable_path() }
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
        GpmcAdapter.weight_lines(var, weight)
    }
}
impl SolverAdapter for GpmcAdapter {
    fn id(&self) -> &'static str { "gpmc" }
    fn arguments(&self) -> &'static [&'static str] { &["-mode=1"] }
    fn capabilities(&self) -> SolverCapabilities {
        SolverCapabilities { complex_weights: true, exact_count_certificate: false, grammar: WeightGrammar::Pair }
    }
    fn executable_path(&self) -> String {
        if let Ok(path) = std::env::var("QUPRS_GPMC_PATH") { return path; }
        if let Some(path) = option_env!("GPMC_BIN_PATH") {
            if Path::new(path).exists() { return path.to_string(); }
        }
        if cfg!(windows) { "gpmc.exe" } else { "gpmc" }.to_string()
    }
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
        (format!("c p weight {} {:.16e} {:.16e} 0\n", var, weight.re, weight.im),
         format!("c p weight -{} 1.0 0.0 0\n", var))
    }
}
impl SolverAdapter for GanakAdapter {
    fn id(&self) -> &'static str { "ganak" }
    fn arguments(&self) -> &'static [&'static str] { &["--mode=6"] }
    fn capabilities(&self) -> SolverCapabilities {
        SolverCapabilities { complex_weights: true, exact_count_certificate: false, grammar: WeightGrammar::ComplexI }
    }
    fn executable_path(&self) -> String {
        if let Ok(path) = std::env::var("QUPRS_GANAK_PATH") { return path; }
        if let Some(path) = option_env!("GANAK_BIN_PATH") {
            if Path::new(path).exists() { return path.to_string(); }
        }
        if cfg!(windows) { "ganak.exe" } else { "ganak" }.to_string()
    }
    fn preflight(&self, path: &str, deadline: Option<Instant>) -> Result<()> {
        let detail = crate::ganak_distribution::diagnostics_with_deadline(
            Path::new(path), std::env::var_os("QUPRS_GANAK_PATH").is_some(), deadline
        ).map_err(|e| if e.starts_with("SolverTimeout:") {
            anyhow!(crate::solver_process::SolverTimeout)
        } else { anyhow!(e) })?;
        log::info!(target:"wmc", "{}", detail);
        Ok(())
    }
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
        let sign = if weight.im >= 0.0 { "+" } else { "-" };
        (format!("c p weight {} {:.16e} {} {:.16e}i 0\n", var, weight.re, sign, weight.im.abs()),
         format!("c p weight -{} 1.0 + 0.0i 0\n", var))
    }
}

#[cfg(feature = "experimental-d4")]
pub(crate) fn parse_d4_printed_optional(
    stdout: &str,
) -> Result<Option<crate::precision_count::PrintedCount>> {
    let mut found: Option<crate::precision_count::PrintedCount> = None;
    let mut saw_sat = false;
    let mut saw_unsat = false;
    for line in stdout.lines() {
        match line.trim() {
            "s SATISFIABLE" => saw_sat = true,
            "s UNSATISFIABLE" => saw_unsat = true,
            _ => {}
        }
        let (dialect, raw, int_mode) =
            if let Some(raw) = line.strip_prefix("c s exact arb float ") {
                ("c s exact arb float", raw, false)
            } else if let Some(raw) = line.strip_prefix("c s exact arb int ") {
                ("c s exact arb int", raw, true)
            } else {
                continue;
            };
        let value = raw.trim();
        if value.len() > 8192 || value.is_empty() {
            return Err(anyhow!("d4 printed count outside bounded token range"));
        }
        let shadow = if int_mode {
            let body = if value.starts_with('+') || value.starts_with('-') {
                &value[1..]
            } else { value };
            if body.is_empty() || !body.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(anyhow!("invalid d4 exact-integer format"));
            }
            // Existing Fraction transport yields zero printed rounding-unit.
            format!("c s exact arb frac {value}/1")
        } else {
            // Preserve original decimal digits under an existing *formatting*
            // interval parser. This is NOT a GMP arithmetic-error certificate.
            format!("c s exact octuple float {value}")
        };
        let mut parsed = crate::precision_count::parse_line(&shadow)?
            .ok_or_else(|| anyhow!("d4 count parser rejected its normalized count"))?;
        parsed.format_name = dialect.to_string();
        if let Some(ref mut previous) = found {
            if previous.real != parsed.real || previous.imag != parsed.imag {
                return Err(anyhow!("d4 output contains conflicting weighted counts"));
            }
            if parsed.real_half_unit > previous.real_half_unit {
                previous.real_half_unit = parsed.real_half_unit;
            }
            if parsed.imag_half_unit > previous.imag_half_unit {
                previous.imag_half_unit = parsed.imag_half_unit;
            }
        } else {
            found = Some(parsed);
        }
    }
    if saw_sat && saw_unsat {
        return Err(anyhow!("d4 output contains conflicting SAT status lines"));
    }
    if saw_unsat && found.as_ref().is_some_and(|count| {
        use num_traits::Zero;
        !count.real.is_zero() || !count.imag.is_zero()
    }) {
        return Err(anyhow!("d4 UNSAT status contradicts nonzero count"));
    }
    Ok(found)
}

#[cfg(feature = "experimental-d4")]
impl SolverAdapter for D4ResearchAdapter {
    fn id(&self) -> &'static str { "d4-poc" }
    fn arguments(&self) -> &'static [&'static str] { &["-i"] }
    fn capabilities(&self) -> SolverCapabilities {
        SolverCapabilities {
            complex_weights: true,
            exact_count_certificate: false,
            grammar: WeightGrammar::Pair,
        }
    }
    fn executable_path(&self) -> String {
        // No executable discovery or packaged-binary fallback in research mode.
        std::env::var("QUPRS_D4_PATH").unwrap_or_default()
    }
    fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
        GpmcAdapter.weight_lines(var, weight)
    }
    fn preflight(&self, path: &str, deadline: Option<Instant>) -> Result<()> {
        use sha2::{Digest, Sha256};
        use std::io::Read;
        if path.is_empty() || !Path::new(path).is_file() {
            return Err(anyhow!("d4-poc requires an explicit external binary"));
        }
        if std::env::var("QUPRS_D4_UPSTREAM_SHA").as_deref()
            != Ok("be15f91f3e9769e1f5cb175fa27e3eca3a1ea690") {
            return Err(anyhow!("d4-poc upstream source provenance missing"));
        }
        let bits: u32 = std::env::var("QUPRS_D4_GMP_PREPARSE_BITS")
            .map_err(|_| anyhow!("d4-poc preparse GMP bits missing"))?
            .parse()?;
        if !(256..=2048).contains(&bits) {
            return Err(anyhow!("d4-poc requires >=256-bit preparse GMP research mode"));
        }
        let expected = std::env::var("QUPRS_D4_BINARY_SHA256")
            .map_err(|_| anyhow!("d4-poc external binary SHA256 missing"))?;
        if expected.len() != 64 || !expected.bytes().all(|ch| ch.is_ascii_hexdigit()) {
            return Err(anyhow!("d4-poc binary SHA256 is malformed"));
        }
        let mut file = std::fs::File::open(path)?;
        if file.metadata()?.len() > 256 * 1024 * 1024 {
            return Err(anyhow!("d4-poc binary exceeds bounded provenance limit"));
        }
        let mut digest = Sha256::new();
        let mut buffer = [0u8; 16 * 1024];
        loop {
            if deadline.is_some_and(|end| Instant::now() >= end) {
                return Err(anyhow!(crate::solver_process::SolverTimeout));
            }
            let n = file.read(&mut buffer)?;
            if n == 0 { break; }
            digest.update(&buffer[..n]);
        }
        let actual: String = digest.finalize().iter()
            .map(|byte| format!("{byte:02x}")).collect();
        if !actual.eq_ignore_ascii_case(&expected) {
            return Err(anyhow!("d4-poc external binary SHA256 mismatch"));
        }
        Ok(())
    }
    fn parse_count(&self, stdout: &str) -> Result<Option<Complex<f64>>> {
        use num_traits::ToPrimitive;
        let Some(count) = parse_d4_printed_optional(stdout)? else { return Ok(None); };
        let re = count.real.to_f64().ok_or_else(|| anyhow!("d4 count outside f64"))?;
        let im = count.imag.to_f64().ok_or_else(|| anyhow!("d4 count outside f64"))?;
        if !re.is_finite() || !im.is_finite() {
            return Err(anyhow!("non-finite d4 count"));
        }
        Ok(Some(Complex::new(re, im)))
    }
}

#[cfg(all(test, feature = "experimental-d4"))]
mod d4_poc_tests {
    use super::*;
    use num_traits::ToPrimitive;

    #[test]
    fn d4_poc_is_explicit_and_preserves_incumbent_contract() {
        let selected = adapter_for("d4-poc").unwrap();
        assert_eq!(selected.id(), "d4-poc");
        assert_eq!(selected.arguments(), &["-i"]);
        assert_eq!(selected.capabilities().grammar, WeightGrammar::Pair);
        assert!(!selected.capabilities().exact_count_certificate);
        assert_eq!(selected.weight_lines(1, Complex::new(0.5,-0.125)),
                   GpmcAdapter.weight_lines(1,Complex::new(0.5,-0.125)));
        assert_eq!(adapter_for("gpmc").unwrap().arguments(), &["-mode=1"]);
        assert_eq!(adapter_for("ganak").unwrap().arguments(), &["--mode=6"]);
    }

    #[test]
    fn d4_poc_retains_tiny_decimal_before_f64_and_detects_bad_output() {
        let printed = parse_d4_printed_optional(
            "s SATISFIABLE\nc s exact arb float 1.000000000000000000e-40-2.000e-50i\n"
        ).unwrap().unwrap();
        assert_eq!(printed.format_name, "c s exact arb float");
        assert!(printed.real.to_f64().unwrap() > 0.0);
        assert!(printed.imag.to_f64().unwrap() < 0.0);
        assert!(printed.real_half_unit.to_f64().unwrap() > 0.0);
        let numeric = adapter_for("d4-poc").unwrap().parse_count(
            "c s exact arb float 1e-40-2e-50i\n"
        ).unwrap().unwrap();
        assert!((numeric.re - 1e-40).abs() < 1e-54);
        for stdout in [
            "c s exact arb float nan+0i",
            "c s exact arb float 1+0i\nc s exact arb float 2+0i",
            "s UNSATISFIABLE\nc s exact arb int 1",
            "s SATISFIABLE\ns UNSATISFIABLE\nc s exact arb int 0",
        ] {
            assert!(parse_d4_printed_optional(stdout).is_err(), "{stdout}");
        }
        let int_count = parse_d4_printed_optional(
            "s UNSATISFIABLE\nc s exact arb int 0\n"
        ).unwrap().unwrap();
        assert_eq!(int_count.format_name, "c s exact arb int");
        assert_eq!(int_count.real.to_f64().unwrap(), 0.0);
        assert_eq!(int_count.real_half_unit.to_f64().unwrap(), 0.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pathsum::PathSum;
    use crate::wmc::WmcManager;
    use std::time::Duration;
    #[test]
    fn independent_dialects_and_unknown_solver() {
        let a = adapter_for("gpmc").unwrap();
        let b = adapter_for("ganak").unwrap();
        assert_eq!(a.arguments(), &["-mode=1"]);
        assert_eq!(b.arguments(), &["--mode=6"]);
        assert_eq!(distance_adapter_for("gpmc", 30).unwrap().arguments(), &["-mode=1"]);
        assert_eq!(distance_adapter_for("gpmc", 90).unwrap().arguments(), &["-mode=1", "-prec=90"]);
        assert_eq!(distance_adapter_for("ganak", 30).unwrap().arguments(), &["--mode=6"]);
        assert!(distance_adapter_for("gpmc", 60).is_err());
        assert!(distance_adapter_for("ganak", 90).is_err());
        assert_eq!(a.capabilities().grammar, WeightGrammar::Pair);
        assert_eq!(b.capabilities().grammar, WeightGrammar::ComplexI);
        assert!(a.capabilities().complex_weights && b.capabilities().complex_weights);
        assert!(!a.capabilities().exact_count_certificate && !b.capabilities().exact_count_certificate);
        assert!(adapter_for("not-a-solver").is_err());
        let w = Complex::new(0.5, -0.125);
        assert!(a.weight_lines(1, w).0.contains(" -1.2500000000000000e-1 0\n"));
        assert!(b.weight_lines(1, w).0.contains(" - 1.2500000000000000e-1i 0\n"));
        assert!(a.parse_count("missing count").unwrap().is_none());
        assert!(b.parse_count("c s exact quadruple float inf").is_err());
    }
    #[test]
    fn conflicting_count_lines_fail_closed_for_both_solvers() {
        let one = "c s exact arb frac 3/2 + 1/4i";
        let two = "c s exact arb frac 7/2 + 1/4i";
        for solver in ["gpmc", "ganak"] {
            let adapter = adapter_for(solver).unwrap();
            assert_eq!(adapter.parse_count(one).unwrap(), Some(Complex::new(1.5,0.25)));
            assert_eq!(adapter.parse_count(&format!("{one}\\n{one}").replace("\\n", "\n")).unwrap(), Some(Complex::new(1.5,0.25)));
            for candidate in [format!("{one}\\n{two}"), format!("{two}\\n{one}")] {
                assert!(adapter.parse_count(&candidate.replace("\\n", "\n"))
                    .unwrap_err().to_string().contains("conflicting counts"));
            }
        }
    }
    struct MockAdapter;
    impl SolverAdapter for MockAdapter {
        fn id(&self) -> &'static str { "mock" }
        fn arguments(&self) -> &'static [&'static str] {
            &["-c", "printf 'c s exact quadruple float 3 + 4i\\n'"]
        }
        fn capabilities(&self) -> SolverCapabilities {
            SolverCapabilities { complex_weights: true, exact_count_certificate: false, grammar: WeightGrammar::Pair }
        }
        fn executable_path(&self) -> String { "sh".into() }
        fn weight_lines(&self, var: i32, weight: Complex<f64>) -> (String, String) {
            GpmcAdapter.weight_lines(var, weight)
        }
    }
    #[test]
    #[cfg(unix)]
    fn third_adapter_runs_via_existing_supervisor() {
        let manager = WmcManager::new(&PathSum::new(0));
        assert!(manager.to_dimacs_with_adapter(&MockAdapter).starts_with("p cnf 0 0\nc t wmc\n"));
        let got = manager.solve_with_adapter(
            &MockAdapter, Some(Instant::now() + Duration::from_secs(15)),
        ).unwrap();
        assert_eq!(got, Complex::new(3.0, 4.0));
        let precise = manager.solve_with_adapter_printed(
            &MockAdapter, Some(Instant::now() + Duration::from_secs(15)),
        ).unwrap();
        assert_eq!(precise.real.to_string(), "3");
        assert_eq!(precise.imag.to_string(), "4");
    }
}
