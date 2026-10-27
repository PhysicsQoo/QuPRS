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
static GPMC: GpmcAdapter = GpmcAdapter;
static GANAK: GanakAdapter = GanakAdapter;
pub(crate) fn adapter_for(id: &str) -> Result<&'static dyn SolverAdapter> {
    match id {
        "gpmc" => Ok(&GPMC),
        "ganak" => Ok(&GANAK),
        _ => Err(anyhow!(crate::solver_result::SolverFailure::new(
            crate::solver_result::SolverFailureKind::Unsupported,
            id,
            format!("Unsupported tool name: {}", id),
        ))),
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
    }
}
