//! QOO-157: source-to-verdict native Rust WMC-only d4 research control.
//! This example compiles only with --features experimental-d4.
use anyhow::{bail, Result};
use pathsum::ir::QuantumOp;
use pathsum::rational::Angle;
use pathsum::{
    check_equivalence_with_options, EquivalenceStatus, VerificationMethod,
    VerificationOptions, VerificationStrategy,
};

fn main() -> Result<()> {
    let examples: [(&str, usize, Vec<QuantumOp>, Vec<QuantumOp>, bool); 3] = [
        ("identity_h", 1, vec![QuantumOp::H(0)], vec![QuantumOp::H(0)], true),
        ("t_gate_difference", 1,
            vec![QuantumOp::H(0), QuantumOp::T(0), QuantumOp::H(0)],
            vec![QuantumOp::H(0)], false),
        ("bell_t_difference", 2,
            vec![QuantumOp::H(0), QuantumOp::CX(0, 1), QuantumOp::T(1)],
            vec![QuantumOp::H(0), QuantumOp::CX(0, 1)], false),
    ];
    let mut invoked = 0usize;
    for (name, n, first, second, equivalent) in examples {
        let options = VerificationOptions {
            method: VerificationMethod::WmcOnly,
            strategy: VerificationStrategy::Straightforward,
            tool_name: "d4".to_owned(),
            timeout_secs: 30,
            approximate_distance_tolerance: Some(1e-8),
            ..Default::default()
        };
        let result = check_equivalence_with_options(n, &first, &second, &options)?;
        let is_eq = matches!(
            result.status,
            EquivalenceStatus::Equivalent | EquivalenceStatus::EquivalentUpToGlobalPhase
        );
        if is_eq != equivalent {
            bail!(
                "QOO157_RUST_D4_VERDICT_MISMATCH case={name} observed={} expected_equivalent={equivalent}",
                result.status
            );
        }
        if result.solver_invoked { invoked += 1; }
        println!(
            "QOO157_D4_RUST case={name} status={} solver_invoked={} printed={} certified_solver_bound=false",
            result.status, result.solver_invoked,
            result.wmc_printed_verdict.unwrap_or("none"),
        );
    }
    if invoked < 2 {
        bail!("QOO157_RUST_D4_NOT_SOLVER_INCLUSIVE: only {invoked} external solver calls");
    }
    println!("QOO157_RUST_D4_SOLVER_INCLUSIVE_PASS={invoked}");
    // For a single-qubit P(theta) compared against identity,
    // projective distance is |sin(theta/2)|. At tolerance 1e-8:
    // theta=1e-8 is below and theta=4e-8 is above the boundary.
    // Source angle stays exact-decimal until phase-weight evaluation.
    for (label, theta, expected_equivalent) in [
        ("distance_below", "0.00000001", true),
        ("distance_above", "0.00000004", false),
    ] {
        let angle = Angle::from_qasm_str(theta)
            .map_err(anyhow::Error::msg)?;
        for solver in ["gpmc", "d4"] {
            let options = VerificationOptions {
                method: VerificationMethod::WmcOnly,
                strategy: VerificationStrategy::Straightforward,
                tool_name: solver.to_owned(),
                timeout_secs: 30,
                approximate_distance_tolerance: Some(1e-8),
                ..Default::default()
            };
            let result = check_equivalence_with_options(
                1, &[QuantumOp::P(0, angle.clone())], &[], &options,
            )?;
            let equivalent = matches!(
                result.status,
                EquivalenceStatus::Equivalent | EquivalenceStatus::EquivalentUpToGlobalPhase
            );
            println!(
                "QOO157_D4_BOUNDARY case={label} theta={theta} solver={solver} status={} invoked={} printed={}",
                result.status, result.solver_invoked,
                result.wmc_printed_verdict.unwrap_or("none"),
            );
            if equivalent != expected_equivalent {
                bail!("QOO157_D4_BOUNDARY_VERDICT_MISMATCH solver={solver} theta={theta} status={}", result.status);
            }
            if !result.solver_invoked {
                bail!("QOO157_D4_BOUNDARY_NOT_SOLVER_INCLUSIVE solver={solver} theta={theta}");
            }
        }
    }
    Ok(())
}
