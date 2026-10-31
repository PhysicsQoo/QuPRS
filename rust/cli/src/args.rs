// rust-test/cli/src/args.rs

use clap::{Parser, ValueEnum};
use std::path::PathBuf;

fn parse_gpmc_precision(text: &str) -> Result<u32, String> {
    match text {
        "30" => Ok(30),
        "90" => Ok(90),
        _ => Err("gpmc precision must be 30 or 90".to_string()),
    }
}

/// QuPRS: Quantum Path-sum Reduction System (Rust Core)
#[derive(Parser, Debug)]
#[command(name = "QuPRS-CLI")]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    /// Path to the first QASM circuit file
    #[arg(value_name = "CIRCUIT_1")]
    pub file1: PathBuf,

    /// Path to the second QASM circuit file (Optional for single circuit mode)
    #[arg(value_name = "CIRCUIT_2")]
    pub file2: Option<PathBuf>,

    /// Verification method (consistent with Python API)
    #[arg(short, long, value_enum, default_value_t = MethodArg::Hybrid)]
    pub method: MethodArg,

    /// Interleaving strategy to maximize cancellation (Dual-circuit mode only)
    #[arg(short, long, value_enum, default_value_t = StrategyMode::Difference)]
    pub strategy: StrategyMode,

    /// Total number of qubits (auto-detected if not specified)
    #[arg(short='Q', long)]
    pub qubits: Option<usize>,

    /// Timeout in seconds (default: 600s)
    #[arg(short, long, default_value_t = 600)]
    pub timeout: u64,

    /// Verbosity level (-v: stats, -vv: debug state, -vvv: raw trace)
    #[arg(short, long, action = clap::ArgAction::Count)]
    pub verbose: u8,

    /// WMC Solver tool (gpmc or ganak)
    #[arg(long, default_value = "gpmc")]
    pub tool: String,

    /// Projective Hilbert-Schmidt distance epsilon (default: 1e-8).
    /// This is the only WMC numerical acceptance metric.
    #[arg(long = "approximate-distance-tolerance", visible_alias = "distance-tolerance",
          value_name = "EPSILON")]
    pub approximate_distance_tolerance: Option<f64>,

    /// GPMC MPFR arithmetic digits: 30 default or 90 explicitly.
    #[arg(long = "gpmc-precision", value_name = "DIGITS", value_parser = parse_gpmc_precision)]
    pub gpmc_precision_digits: Option<u32>,

    /// RR residual-phase tolerance in cycles, independent of WMC (default 1e-10).
    #[arg(long = "rr-tolerance", value_name = "CYCLES")]
    pub rr_tolerance: Option<f64>,

    /// Global-phase labeling tolerance, in radians (default: 1e-8).
    #[arg(long = "phase-tolerance", visible_alias = "wmc-phase-tolerance",
          value_name = "RADIANS")]
    pub phase_tolerance: Option<f64>,
    
    /// Suppress all output except the final verification result
    #[arg(short, long, conflicts_with = "verbose")]
    pub quiet: bool,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
pub enum MethodArg {
    Hybrid,
    ReductionRules,
    WmcOnly,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
pub enum StrategyMode {
    Naive,
    Straightforward,
    Proportional,
    Difference,
}
#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn cli_defaults_inherit_typed_verifier_defaults() {
        let cli = Cli::try_parse_from(["QuPRS-CLI", "a.qasm", "b.qasm"]).unwrap();
        assert_eq!(cli.tool, "gpmc");
        assert_eq!(cli.method, MethodArg::Hybrid);
        assert_eq!(cli.approximate_distance_tolerance, None);
        assert_eq!(cli.phase_tolerance, None);
        assert_eq!(cli.rr_tolerance, None);
        assert_eq!(cli.gpmc_precision_digits, None);
    }

    #[test]
    fn cli_exposes_only_distance_and_phase_overrides() {
        let cli = Cli::try_parse_from([
            "QuPRS-CLI", "a.qasm", "b.qasm", "--method", "wmc-only",
            "--tool", "ganak",
            "--approximate-distance-tolerance", "2e-4",
            "--phase-tolerance", "1e-6",
            "--rr-tolerance", "1e-9",
        ]).unwrap();
        assert_eq!(cli.method, MethodArg::WmcOnly);
        assert_eq!(cli.tool, "ganak");
        assert_eq!(cli.approximate_distance_tolerance, Some(2e-4));
        assert_eq!(cli.phase_tolerance, Some(1e-6));
        assert_eq!(cli.rr_tolerance, Some(1e-9));

        let alias = Cli::try_parse_from([
            "QuPRS-CLI", "a.qasm", "b.qasm",
            "--distance-tolerance", "1e-8",
            "--wmc-phase-tolerance", "1e-8",
        ]).unwrap();
        assert_eq!(alias.approximate_distance_tolerance, Some(1e-8));
        assert_eq!(alias.phase_tolerance, Some(1e-8));
    }

    #[test]
    fn explicit_gpmc_precision_flag() {
        let cli = Cli::try_parse_from([
            "QuPRS-CLI", "a.qasm", "b.qasm", "--gpmc-precision", "90",
        ]).unwrap();
        assert_eq!(cli.gpmc_precision_digits, Some(90));
        assert!(Cli::try_parse_from([
            "QuPRS-CLI", "a.qasm", "b.qasm", "--gpmc-precision", "15",
        ]).is_err());
    }

    #[test]
    fn obsolete_magnitude_flag_is_not_accepted() {
        assert!(Cli::try_parse_from([
            "QuPRS-CLI", "a.qasm", "b.qasm",
            "--wmc-magnitude-tolerance", "1e-6",
        ]).is_err());
    }
}
