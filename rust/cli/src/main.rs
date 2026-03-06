// rust-test/cli/src/main.rs

mod args;
mod display;
mod runner;

use clap::Parser;
use anyhow::Result;
use colored::*;
use log::LevelFilter;
use env_logger::Builder;

use crate::args::Cli;

fn main() -> Result<()> {
    let cli = Cli::parse();

    // 1. Initialize Logger
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

    // 2. Delegate to the appropriate runner based on arguments
    if let Some(file2_path) = &cli.file2 {
        runner::run_dual_circuit_mode(&cli, file2_path)?;
    } else {
        runner::run_single_circuit_mode(&cli)?;
    }

    Ok(())
}