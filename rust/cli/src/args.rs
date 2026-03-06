// rust-test/cli/src/args.rs

use clap::{Parser, ValueEnum};
use std::path::PathBuf;

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