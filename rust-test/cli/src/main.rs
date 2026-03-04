// rust-test/cli/src/main.rs
use clap::{Parser, ValueEnum};
use std::fs;
use std::path::PathBuf;
use std::time::Instant;
use std::time::Duration;
use anyhow::{Context, Result};
use colored::*;
use log::{info, LevelFilter};
use env_logger::Builder;
use indicatif::{ProgressBar, ProgressStyle};

use pathsum::pathsum::PathSum;
use pathsum::strategy::VerificationStrategy;
use pathsum::qasm;

/// QuPRS: Quantum Path-sum Reduction System
#[derive(Parser, Debug)]
#[command(name = "QuPRS")]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[arg(value_name = "CIRCUIT_1")]
    file1: PathBuf,

    #[arg(value_name = "CIRCUIT_2")]
    file2: PathBuf,

    #[arg(short, long, value_enum, default_value_t = StrategyMode::Difference)]
    strategy: StrategyMode,

    #[arg(short='Q', long)]
    qubits: Option<usize>,

    /// Verbosity level (-v, -vv, -vvv)
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,
    
    #[arg(short, long, conflicts_with = "verbose")]
    quiet: bool,
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
        println!("{}", ">> [QuPRS] Initializing...".bold().cyan());
    }

    let (ops1, num_qubits1) = parse_circuit(&cli.file1)?;
    let (ops2, num_qubits2) = parse_circuit(&cli.file2)?;

    info!("   ├─ Circuit 1: {} gates ({} qubits)", ops1.len(), num_qubits1);
    info!("   └─ Circuit 2: {} gates ({} qubits)", ops2.len(), num_qubits2);

    let system_qubits = cli.qubits.unwrap_or_else(|| std::cmp::max(num_qubits1, num_qubits2));
    
    if system_qubits == 0 {
        eprintln!("{}", "❌ Error: Qubit count is 0.".red());
        std::process::exit(1);
    }

    let ps = PathSum::new(system_qubits);

    let strategy = match cli.strategy {
        StrategyMode::Naive => VerificationStrategy::Naive,
        StrategyMode::Straightforward => VerificationStrategy::Straightforward,
        StrategyMode::Proportional => VerificationStrategy::Proportional,
        StrategyMode::Difference => VerificationStrategy::Difference,
    };

    if !cli.quiet {
        println!(">> Strategy: {}", format!("{:?}", cli.strategy).yellow());
    }

    // Execute verification with spinner
    let start_time = Instant::now();

    // Show spinner only in quiet mode with no verbose output
    let pb = if !cli.quiet && cli.verbose == 0 {
        let pb = ProgressBar::new_spinner();
        pb.set_style(ProgressStyle::default_spinner()
            .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
            .template("{spinner:.green} {msg} {elapsed}")
            .unwrap());
        pb.set_message("Reducing quantum paths...");
        pb.enable_steady_tick(Duration::from_millis(80)); 
        Some(pb)
    } else {
        None
    };

    let final_ps = strategy.run(ps, &ops1, &ops2);

    if let Some(pb) = pb {
        pb.finish_and_clear();
    }

    let duration = start_time.elapsed();
    if !cli.quiet {
        println!("   └─ Finished in {:.2?}", duration);
    }

    // Display statistics
    if final_ps.stats.total_attempts() > 0 && !cli.quiet {
        println!("\n>> Reduction Statistics:");
        print_rule_stat("HH Rule", &final_ps.stats.hh);
        print_rule_stat("Omega Rule", &final_ps.stats.omega);
        print_rule_stat("Elim Rule", &final_ps.stats.elim);
        println!("   └─ Total:      {} reductions", final_ps.stats.total_successes().to_string().bold());
    }

    // Display result
    if !cli.quiet {
        println!("\n>> Result:");
    }

    if final_ps.is_identity_up_to_phase() {
        println!("{}", "✅ EQUIVALENT".bold().green());
        if !cli.quiet {
            if let Some(phase_coeff) = final_ps.get_global_phase() {
                let pi_coeff = phase_coeff.constant * 2;
                if pi_coeff.is_zero() {
                    println!("   (Global phase: 0)");
                } else if pi_coeff.numer == 1 && pi_coeff.denom == 1 {
                    println!("   (Global phase: π)");
                } else if pi_coeff.numer == -1 && pi_coeff.denom == 1 {
                    println!("   (Global phase: -π)");
                } else {
                    println!("   (Global phase: {} π)", pi_coeff);
                }
            }
        }
    } else {
        println!("{}", "❌ NOT EQUIVALENT".bold().red());
        if !cli.quiet && cli.verbose > 0 {
            println!("\n--- Remaining State ---");
        }
    }

    Ok(())
}

// Print rule statistics
fn print_rule_stat(name: &str, stats: &pathsum::stats::RuleStats) {
    let rate = if stats.attempts > 0 {
        (stats.successes as f64 / stats.attempts as f64) * 100.0
    } else {
        0.0
    };
    
    let rate_str = if rate > 50.0 {
        format!("{:.1}%", rate).green()
    } else if rate > 10.0 {
        format!("{:.1}%", rate).yellow()
    } else {
        format!("{:.1}%", rate).dimmed()
    };

    println!(
        "   ├─ {:<10} {:>5} / {:>5} scans ({})", 
        name, 
        stats.successes, 
        stats.attempts, 
        rate_str
    );
}

// Parse QASM circuit file
fn parse_circuit(path: &PathBuf) -> Result<(Vec<pathsum::ir::QuantumOp>, usize)> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read file '{}'", path.display()))?;
    
    let ops = qasm::parse_qasm_str(&content)
        .map_err(|e| anyhow::anyhow!("QASM Parse Error in '{}': {}", path.display(), e))?;

    use pathsum::ir::QuantumOp;
    let max_idx = ops.iter().map(|op| match op {
        QuantumOp::H(q) | QuantumOp::X(q) | QuantumOp::Y(q) | QuantumOp::Z(q) |
        QuantumOp::RX(q, _) | QuantumOp::RY(q, _) | QuantumOp::RZ(q, _) |
        QuantumOp::U3(q, _, _, _) => *q,
        QuantumOp::CX(c, t) | QuantumOp::CZ(c, t) => std::cmp::max(*c, *t),
        QuantumOp::CCX(c1, c2, t) => *t.max(c1).max(c2),
        _ => 0,
    }).max().unwrap_or(0);

    let count = if ops.is_empty() { 0 } else { max_idx + 1 };

    Ok((ops, count))
}
