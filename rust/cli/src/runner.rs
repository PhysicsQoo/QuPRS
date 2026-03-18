// rust-test/cli/src/runner.rs

use anyhow::{Context, Result};
use std::time::Instant;
use colored::*;
use indicatif::{ProgressBar, ProgressStyle};

use pathsum::{
    check_equivalence,
    VerificationMethod,
    VerificationStrategy,
    PathSum,
};

use crate::args::{Cli, MethodArg, StrategyMode};
use crate::display::{display_summary, print_rule_stat};

/// Executes the dual-circuit equivalence checking mode (Mode A)
pub fn run_dual_circuit_mode(cli: &Cli, file2_path: &std::path::Path) -> Result<()> {
    let (ops1, num_qubits1) = pathsum::qasm::parse_file(&cli.file1)
        .map_err(|e| anyhow::anyhow!("{}", e))?;
    let (ops2, num_qubits2) = pathsum::qasm::parse_file(file2_path)
        .map_err(|e| anyhow::anyhow!("{}", e))?;

    let system_qubits = cli.qubits.unwrap_or_else(|| std::cmp::max(num_qubits1, num_qubits2));
    
    if !cli.quiet {
        println!("   ├─ Circuit 1: {} gates ({} qubits)", ops1.len(), num_qubits1);
        println!("   ├─ Circuit 2: {} gates ({} qubits)", ops2.len(), num_qubits2);
        println!("   ├─ Qubits:    {}", system_qubits.to_string().yellow());
        println!("   ├─ Method:    {}", format!("{:?}", cli.method).yellow());
        println!("   └─ Strategy:  {}", format!("{:?}", cli.strategy).yellow());
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
        &cli.tool,
        cli.timeout,
    ).context("Core verification engine failed")?;

    if let Some(pb) = pb {
        pb.finish_and_clear();
    }

    let final_ps = &result.final_ps;
    
    if cli.verbose >= 2 {
        log::debug!(target: "pathsum", "Fixed-point reached. {}", final_ps.print_status());
    }

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

    display_summary(&result, cli.quiet);
    Ok(())
}

/// Executes the single-circuit reduction mode (Mode B)
pub fn run_single_circuit_mode(cli: &Cli) -> Result<()> {
    let (ops1, num_qubits1) = pathsum::qasm::parse_file(&cli.file1)
        .map_err(|e| anyhow::anyhow!("{}", e))?;

    let system_qubits = cli.qubits.unwrap_or(num_qubits1);

    if !cli.quiet {
        println!("   ├─ Circuit:   {} gates ({} qubits)", ops1.len(), num_qubits1);
        println!("   └─ Mode:      {}", "Single Circuit Reduction".bold().magenta());
    }

    let strategy = match cli.strategy {
        StrategyMode::Naive => VerificationStrategy::Naive,
        StrategyMode::Straightforward => VerificationStrategy::Straightforward,
        StrategyMode::Proportional => VerificationStrategy::Proportional,
        StrategyMode::Difference => VerificationStrategy::Difference,
    };

    let start = Instant::now();
    let mut ps = PathSum::new(system_qubits);
    ps.set_auto_reduce(true);
    
    let mut ps = strategy.run(ps, &ops1, &[]);
    ps.full_reduce();
    let duration = start.elapsed();

    println!("{}", "\n>> Reduced PathSum State:".bold().green());
    println!("{}", ps.print_status());

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
    
    Ok(())
}