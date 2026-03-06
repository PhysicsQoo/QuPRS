// rust-test/cli/src/display.rs

use colored::*;
use pathsum::{EquivalenceCheckResult, EquivalenceStatus};
use pathsum::stats::RuleStats;

/// Helper function to display the final equivalence checking results
pub fn display_summary(res: &EquivalenceCheckResult, quiet: bool) {
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

/// Helper function to format and print individual reduction rule statistics
pub fn print_rule_stat(name: &str, stats: &RuleStats) {
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