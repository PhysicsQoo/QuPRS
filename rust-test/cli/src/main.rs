// rust-test/cli/src/main.rs
use clap::{Parser, ValueEnum};
use std::fs;
use std::path::PathBuf;
use std::time::Instant;
use anyhow::{Context, Result};
use colored::*;

use pathsum::pathsum::PathSum;
use pathsum::strategy::VerificationStrategy;
use pathsum::qasm;

/// QuPRS: Quantum Path-sum Reduction System
/// An efficient quantum circuit compilation and verification tool based on path integral formalism.
#[derive(Parser, Debug)]
#[command(name = "QuPRS")]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// First circuit file path (reference circuit / Ket)
    #[arg(value_name = "CIRCUIT_1")]
    file1: PathBuf,

    /// Second circuit file path (circuit to verify / Bra)
    #[arg(value_name = "CIRCUIT_2")]
    file2: PathBuf,

    /// Verification strategy mode
    #[arg(short, long, value_enum, default_value_t = StrategyMode::Difference)]
    strategy: StrategyMode,

    /// Number of qubits (auto-detected from circuit if not specified)
    #[arg(short, long)]
    qubits: Option<usize>,

    /// Show detailed reduction process
    #[arg(short, long)]
    verbose: bool,
}

/// CLI enum mapping to pathsum::strategy::VerificationStrategy
#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum StrategyMode {
    /// Naive strategy: interleaved execution
    Naive,
    /// Straightforward strategy: complete Bra, then Ket
    Straightforward,
    /// Proportional strategy: mixed by length ratio
    Proportional,
    /// Difference strategy: only compute differing parts (most efficient)
    Difference,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    println!("{}", ">> [QuPRS] Initializing Verification Pipeline...".bold().cyan());

    let (ops1, num_qubits1) = parse_circuit(&cli.file1)?;
    let (ops2, num_qubits2) = parse_circuit(&cli.file2)?;

    println!("   ├─ Circuit 1: {} gates ({} qubits detected)", ops1.len(), num_qubits1);
    println!("   └─ Circuit 2: {} gates ({} qubits detected)", ops2.len(), num_qubits2);

    // Determine total qubits (max of both, or use user-specified value)
    let system_qubits = cli.qubits.unwrap_or_else(|| std::cmp::max(num_qubits1, num_qubits2));
    
    if system_qubits == 0 {
        eprintln!("{}", "❌ Error: Qubit count is 0. Please check your QASM files or use --qubits.".red());
        std::process::exit(1);
    }

    println!("   └─ System initialized with {} qubits.", system_qubits);
    
    let ps = PathSum::new(system_qubits);

    // Convert CLI enum to library enum
    let strategy = match cli.strategy {
        StrategyMode::Naive => VerificationStrategy::Naive,
        StrategyMode::Straightforward => VerificationStrategy::Straightforward,
        StrategyMode::Proportional => VerificationStrategy::Proportional,
        StrategyMode::Difference => VerificationStrategy::Difference,
    };

    println!("\n>> Running Strategy: {}", format!("{:?}", cli.strategy).yellow());
    let start_time = Instant::now();

    // Execute core computation: ps = Circuit2† * Circuit1
    let final_ps = strategy.run(ps, &ops1, &ops2);

    let duration = start_time.elapsed();
    println!("   └─ Computation finished in {:.2?}", duration);

    println!("\n>> Verifying Equivalence...");

    if final_ps.is_identity_up_to_phase() {
        println!("{}", "✅ EQUIVALENT".bold().green());
        println!("   The two circuits are functionally identical (up to global phase).");
        
        if let Some(phase) = final_ps.get_global_phase() {
             println!("   Note: Global phase difference detected: {:?}", phase);
        }
    } else {
        println!("{}", "❌ NOT EQUIVALENT".bold().red());
        println!("   The circuits produce different quantum states.");
        
        if cli.verbose {
            println!("\n--- Debug Info: Remaining State ---");
            final_ps.print_status();
        }
    }

    Ok(())
}

/// Parse QASM file and return (operations, detected qubit count)
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
