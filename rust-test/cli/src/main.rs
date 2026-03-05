// rust-test/cli/src/main.rs

use clap::{Parser, ValueEnum};
use std::fs;
use std::path::PathBuf;
use std::time::Instant;
use anyhow::{Context, Result};
use colored::*;
use log::LevelFilter;
use env_logger::Builder;
use indicatif::{ProgressBar, ProgressStyle};

// Import core functionalities from the pathsum library
use pathsum::{
    check_equivalence, 
    VerificationMethod, 
    VerificationStrategy, 
    EquivalenceStatus,
    ir::QuantumOp,
    qasm,
    PathSum,
};

/// QuPRS: Quantum Path-sum Reduction System (Rust Core)
#[derive(Parser, Debug)]
#[command(name = "QuPRS-CLI")]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Path to the first QASM circuit file
    #[arg(value_name = "CIRCUIT_1")]
    file1: PathBuf,

    /// Path to the second QASM circuit file (Optional for single circuit mode)
    #[arg(value_name = "CIRCUIT_2")]
    file2: Option<PathBuf>,

    /// Verification method (consistent with Python API)
    #[arg(short, long, value_enum, default_value_t = MethodArg::Hybrid)]
    method: MethodArg,

    /// Interleaving strategy to maximize cancellation (Dual-circuit mode only)
    #[arg(short, long, value_enum, default_value_t = StrategyMode::Difference)]
    strategy: StrategyMode,

    /// Total number of qubits (auto-detected if not specified)
    #[arg(short='Q', long)]
    qubits: Option<usize>,

    /// Timeout in seconds (default: 600s)
    #[arg(short, long, default_value_t = 600)]
    timeout: u64,

    /// Verbosity level (-v: stats, -vv: debug state, -vvv: raw trace)
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,
    
    /// Suppress all output except the final verification result
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

    // 1. Initialize the logging system based on the verbosity level
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

    if !cli.quiet {
        println!("{}", ">> [QuPRS] Verification Engine Starting...".bold().cyan());
    }

    // 2. Parse the primary circuit file (always required)
    let (ops1, num_qubits1) = parse_circuit(&cli.file1)?;

    // 3. Map CLI arguments to core library enums (HOISTED to be available in both modes)
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

    // 4. Determine execution mode based on the presence of the second file
    if let Some(file2_path) = cli.file2 {
        // ==========================================
        // Mode A: Dual-Circuit Equivalence Checking
        // ==========================================
        let (ops2, num_qubits2) = parse_circuit(&file2_path)?;
        
        let system_qubits = cli.qubits.unwrap_or_else(|| std::cmp::max(num_qubits1, num_qubits2));
        
        if !cli.quiet {
            println!("   ├─ Circuit 1: {} gates ({} qubits)", ops1.len(), num_qubits1);
            println!("   ├─ Circuit 2: {} gates ({} qubits)", ops2.len(), num_qubits2);
            println!("   ├─ Qubits:    {}", system_qubits.to_string().yellow());
            println!("   ├─ Method:    {}", format!("{:?}", cli.method).yellow());
            println!("   └─ Strategy:  {}", format!("{:?}", cli.strategy).yellow());
        }

        // Initialize progress bar for standard execution (level 0)
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

        // Invoke the core equivalence checking engine
        let result = check_equivalence(
            system_qubits,
            &ops1,
            &ops2,
            method,
            strategy,
            cli.timeout,
        ).context("Core verification engine failed")?;

        if let Some(pb) = pb {
            pb.finish_and_clear();
        }

        let final_ps = &result.final_ps;
        
        // [-vv] Print the residual algebraic state at the fixed point
        if cli.verbose >= 2 {
            log::debug!(target: "pathsum", "Fixed-point reached. {}", final_ps.print_status());
        }

        // [-v] Print detailed reduction statistics
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

        // Display the final verification summary
        display_summary(&result, cli.quiet);

    } else {
        // ==========================================
        // Mode B: Single Circuit Reduction
        // ==========================================
        let system_qubits = cli.qubits.unwrap_or(num_qubits1);

        if !cli.quiet {
            println!("   ├─ Circuit:   {} gates ({} qubits)", ops1.len(), num_qubits1);
            println!("   └─ Mode:      {}", "Single Circuit Reduction".bold().magenta());
        }

        let start = Instant::now();
        let mut ps = PathSum::new(system_qubits);
        
        // Enable automatic rule application
        ps.set_auto_reduce(true);
        
        // By passing an empty slice `&[]` as the second circuit, the strategy 
        // applies `ops1` forward (Side::Left) and skips the backward operations.
        let mut ps = strategy.run(ps, &ops1, &[]);
        
        // Ensure the algebraic state reaches a strict fixed point
        ps.full_reduce();
        let duration = start.elapsed();

        // In single-circuit mode, the residual state is the primary output.
        println!("{}", "\n>> Reduced PathSum State:".bold().green());
        println!("{}", ps.print_status());

        // Print reduction statistics if applicable
        if !cli.quiet && ps.stats.total_attempts() > 0 {
            println!("\n{}", ">> Reduction Statistics:".bold().cyan());
            print_rule_stat("HH Rule", &ps.stats.hh);
            print_rule_stat("Omega Rule", &ps.stats.omega);
            print_rule_stat("Elim Rule", &ps.stats.elim);
            println!(
                "   └─ Total:      {} reductions", 
                ps.stats.total_successes().to_string().bold()
            );
            println!("   └─ Time:       {:.3} s", duration.as_secs_f64());
        }
    }
    Ok(())
}

/// Helper function to format and print individual reduction rule statistics
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

/// Helper function to display the final equivalence checking results
fn display_summary(res: &pathsum::EquivalenceCheckResult, quiet: bool) {
    if quiet {
        // Output strictly the enum variant string for parsing by external scripts
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

    // Display WMC metrics if the fallback solver was triggered
    if let Some(wmc_t) = res.wmc_time {
        println!("   ├─ WMC Total:      {:.3} s", wmc_t);
        println!("   │  ├─ DIMACS:      {:.3} s", res.to_dimacs_time.unwrap_or(0.0));
        println!("   │  └─ GPMC Solver: {:.3} s", res.tool_time.unwrap_or(0.0));
    }

    println!("   └─ Status:         {}", res.status.to_string().dimmed());
    println!();
}

/// Helper function to parse QASM strings and heuristically determine the required qubits
fn parse_circuit(path: &PathBuf) -> Result<(Vec<QuantumOp>, usize)> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read QASM file '{}'", path.display()))?;
    
    let ops = qasm::parse_qasm_str(&content)
        .map_err(|e| anyhow::anyhow!("QASM Parse Error in '{}': {}", path.display(), e))?;

    // Find the maximum qubit index referenced in the quantum operations
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