// rust-test/cli/src/main.rs
use clap::{Parser, ValueEnum};
use std::fs;
use std::path::PathBuf;
use anyhow::{Context, Result};
use colored::*;
use log::{info, LevelFilter};
use env_logger::Builder;
use indicatif::{ProgressBar, ProgressStyle};

use pathsum::{
    check_equivalence, 
    VerificationMethod, 
    VerificationStrategy, 
    EquivalenceStatus,
    ir::QuantumOp,
    qasm,
};

/// QuPRS: Quantum Path-sum Reduction System (Rust Core)
#[derive(Parser, Debug)]
#[command(name = "QuPRS-CLI")]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Path to the first QASM circuit file
    #[arg(value_name = "CIRCUIT_1")]
    file1: PathBuf,

    /// Path to the second QASM circuit file
    #[arg(value_name = "CIRCUIT_2")]
    file2: PathBuf,

    /// Verification method (consistent with Python API)
    #[arg(short, long, value_enum, default_value_t = MethodArg::Hybrid)]
    method: MethodArg,

    /// Interleaving strategy to maximize cancellation
    #[arg(short, long, value_enum, default_value_t = StrategyMode::Difference)]
    strategy: StrategyMode,

    /// Total number of qubits (auto-detected if not specified)
    #[arg(short='Q', long)]
    qubits: Option<usize>,

    /// Timeout in seconds (default: 600s)
    #[arg(short, long, default_value_t = 600)]
    timeout: u64,

    /// Verbosity level (-v, -vv, -vvv)
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,
    
    /// Suppress all output except the final result
    #[arg(short, long, conflicts_with = "verbose")]
    quiet: bool,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum MethodArg {
    Hybrid,
    ReductionRules,
    WmcOnly,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum StrategyMode {
    Naive,
    Straightforward,
    Proportional,
    Difference,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize logger
    let log_level = if cli.quiet {
        LevelFilter::Off
    } else {
        match cli.verbose {
            0 => LevelFilter::Warn,
            1 => LevelFilter::Info,
            2 => LevelFilter::Debug,
            _ => LevelFilter::Trace,
        }
    };

    Builder::new()
        .filter_level(log_level)
        .format_timestamp(None)
        .init();

    // Parse QASM files
    if !cli.quiet {
        println!("{}", ">> [QuPRS] Verification Engine Starting...".bold().cyan());
    }

    let (ops1, num_qubits1) = parse_circuit(&cli.file1)?;
    let (ops2, num_qubits2) = parse_circuit(&cli.file2)?;

    info!("   ├─ Circuit 1: {} gates ({} qubits)", ops1.len(), num_qubits1);
    info!("   └─ Circuit 2: {} gates ({} qubits)", ops2.len(), num_qubits2);

    let system_qubits = cli.qubits.unwrap_or_else(|| std::cmp::max(num_qubits1, num_qubits2));
    
    if !cli.quiet {
        println!("   ├─ Qubits:   {}", system_qubits.to_string().yellow());
        println!("   ├─ Method:   {}", format!("{:?}", cli.method).yellow());
        println!("   └─ Strategy: {}", format!("{:?}", cli.strategy).yellow());
    }

    let method = match cli.method {
        MethodArg::Hybrid => VerificationMethod::Hybrid,
        MethodArg::ReductionRules => VerificationMethod::ReductionRules,
        MethodArg::WmcOnly => VerificationMethod::WmcOnly,
    };

    let strategy = match cli.strategy {
        StrategyMode::Naive => VerificationStrategy::Naive,
        StrategyMode::Straightforward => VerificationStrategy::Straightforward,
        StrategyMode::Proportional => VerificationStrategy::Proportional,
        StrategyMode::Difference => VerificationStrategy::Difference,
    };

    let pb = if !cli.quiet && cli.verbose == 0 {
        let pb = ProgressBar::new_spinner();
        pb.set_style(ProgressStyle::default_spinner()
            .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
            .template("{spinner:.green} {msg} [{elapsed_precise}]")
            .unwrap());
        pb.set_message("Computing quantum paths...");
        pb.enable_steady_tick(std::time::Duration::from_millis(80)); 
        Some(pb)
    } else {
        None
    };
    let result = check_equivalence(
        system_qubits,
        &ops1,
        &ops2,
        method,
        strategy,
        cli.timeout,
    ).context("Core verification engine failed")?;

    let final_ps = &result.final_ps;
    if cli.verbose >= 1 && !cli.quiet && final_ps.stats.total_attempts() > 0 {
        println!("\n{}", ">> Reduction Statistics:".bold().cyan());
        print_rule_stat("HH Rule", &final_ps.stats.hh);
        print_rule_stat("Omega Rule", &final_ps.stats.omega);
        print_rule_stat("Elim Rule", &final_ps.stats.elim);
        println!(
            "   └─ Total:      {} reductions", 
            final_ps.stats.total_successes().to_string().bold()
        );
    }
    
    if cli.verbose >= 2 {
        log::debug!(target: "pathsum", "Fixed-point reached. {}", final_ps.print_status());
    }

    if let Some(pb) = pb {
        pb.finish_and_clear();
    }

    display_summary(&result, cli.quiet);

    Ok(())
}

fn print_rule_stat(name: &str, stats: &pathsum::stats::RuleStats) {
    let rate = if stats.attempts > 0 {
        (stats.successes as f64 / stats.attempts as f64) * 100.0
    } else {
        0.0
    };
    println!(
        "   ├─ {:<12} {:>5} / {:>5} hits ({:.1}%)", 
        name, stats.successes, stats.attempts, rate
    );
}

fn display_summary(res: &pathsum::EquivalenceCheckResult, quiet: bool) {
    if quiet {
        println!("{}", res.status);
        return;
    }

    println!("\n{}", ">> Verification Summary:".bold());
    println!("   ├─ Result:         {}", match res.status {
        EquivalenceStatus::Equivalent => "✅ EQUIVALENT".bold().green(),
        EquivalenceStatus::EquivalentUpToGlobalPhase => "✅ EQUIVALENT (Up to Global Phase)".bold().green(),
        EquivalenceStatus::NotEquivalent => "❌ NOT EQUIVALENT".bold().red(),
        _ => "❓ UNKNOWN / TIMEOUT".bold().yellow(),
    });
    
    println!("   ├─ Total Time:     {:.3} s", res.verification_time);
    println!("   ├─ PathSum Time:   {:.3} s", res.pathsum_time);

    if let Some(wmc_t) = res.wmc_time {
        println!("   ├─ WMC Total:      {:.3} s", wmc_t);
        println!("   │  ├─ DIMACS:      {:.3} s", res.to_dimacs_time.unwrap_or(0.0));
        println!("   │  └─ GPMC Solver: {:.3} s", res.tool_time.unwrap_or(0.0));
    }

    println!("   └─ Status:         {}", res.status.to_string().dimmed());
    println!();
}

fn parse_circuit(path: &PathBuf) -> Result<(Vec<QuantumOp>, usize)> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read file '{}'", path.display()))?;
    
    let ops = qasm::parse_qasm_str(&content)
        .map_err(|e| anyhow::anyhow!("QASM Parse Error in '{}': {}", path.display(), e))?;

    let max_idx = ops.iter().map(|op| match op {
        QuantumOp::H(q) | QuantumOp::X(q) | QuantumOp::Y(q) | QuantumOp::Z(q) | QuantumOp::S(q) | QuantumOp::T(q) |
        QuantumOp::SDG(q) | QuantumOp::TDG(q) |
        QuantumOp::RX(q, _) | QuantumOp::RY(q, _) | QuantumOp::RZ(q, _) | QuantumOp::P(q, _) |
        QuantumOp::U3(q, _, _, _) => *q,
        QuantumOp::CX(c, t) | QuantumOp::CZ(c, t) => std::cmp::max(*c, *t),
        QuantumOp::CCX(c1, c2, t) => *t.max(c1).max(c2),
        _ => 0,
    }).max().unwrap_or(0);

    let count = if ops.is_empty() { 0 } else { max_idx + 1 };
    Ok((ops, count))
}