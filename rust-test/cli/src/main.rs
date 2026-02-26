// rust-test/cli/src/main.rs
use clap::Parser;
use std::fs;
use std::path::PathBuf;

use pathsum::PathSum; 


#[derive(Parser, Debug)]
#[command(name = "QuPRS")]
#[command(author = "Your Name <your.email@example.com>")]
#[command(version = "0.1.0")]
#[command(about = "A high-performance quantum circuit compiler based on the Path-Sum formalism.", long_about = None)]
struct Cli {
    #[arg(short, long, value_name = "FILE")]
    input: PathBuf,

    #[arg(long, action = clap::ArgAction::SetTrue)]
    no_reduce: bool,

    #[arg(short, long, value_name = "STATE")]
    state: Option<String>,
}

fn main() {
    let cli = Cli::parse();

    println!(">> [QuPRS CLI] Reading QASM file: {}", cli.input.display());

    let qasm_str = match fs::read_to_string(&cli.input) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("❌ Error reading file '{}': {}", cli.input.display(), e);
            std::process::exit(1);
        }
    };

    let initial_state_bytes = cli.state.map(|s| {
        s.chars().map(|c| {
            match c {
                '0' => 0,
                '1' => 1,
                _ => {
                    eprintln!("❌ Error: Initial state must consist only of '0' and '1'. Found: {}", c);
                    std::process::exit(1);
                }
            }
        }).collect::<Vec<u8>>()
    });

    let state_ref = initial_state_bytes.as_ref().map(|v| v.as_slice());
    
    match PathSum::load_from_qasm_str(&qasm_str, state_ref) {
        Ok(mut ps) => {
            println!(">> [QuPRS CLI] Circuit loaded successfully.");

            if cli.no_reduce {
                println!(">> [QuPRS CLI] Auto-reduction disabled by user.");
            } else {
                println!(">> [QuPRS CLI] Starting full reduction pipeline...");
                ps.full_reduce(); 
            }

            println!("\n=== Final System State ===");
            ps.print_status();
        }
        Err(e) => {
            eprintln!("❌ Failed to parse QASM circuit: {}", e);
            std::process::exit(1);
        }
    }
}