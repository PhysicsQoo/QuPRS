// rust-test/pathsum/src/lib.rs

pub mod pathsum;
pub mod gates;
pub mod qasm;
pub mod ir;
pub mod rational; 
pub mod reduction;
pub mod strategy;
pub mod stats;    
pub mod wmc;
mod diagnostics;
pub use diagnostics::ExclusiveLedger;

pub use pathsum::PathSum;
pub use rational::{Rational, PhaseCoeff};
pub use strategy::VerificationStrategy;
use ir::QuantumOp;
use wmc::WmcManager;
use anyhow::Result;
use std::time::Instant;
use log::{info, debug};
/// Verification Method Selection
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerificationMethod {
    Hybrid,
    ReductionRules,
    WmcOnly,
}

/// The result status of the equivalence check
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EquivalenceStatus {
    Equivalent,
    EquivalentUpToGlobalPhase, // Python's "equivalent*"
    NotEquivalent,
    Unknown,
    Timeout,
    MemoryOut,
}

impl std::fmt::Display for EquivalenceStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Self::Equivalent => "equivalent",
            Self::EquivalentUpToGlobalPhase => "equivalent*",
            Self::NotEquivalent => "not_equivalent",
            Self::Unknown => "unknown",
            Self::Timeout => "Timeout",
            Self::MemoryOut => "MemoryOut",
        };
        write!(f, "{}", s)
    }
}

/// Comprehensive result object matching the Python Dataclass
#[derive(Debug)]
pub struct EquivalenceCheckResult {
    pub qubit_num: usize,
    pub gate_num1: usize,
    pub gate_num2: usize,
    pub method: VerificationMethod,
    pub strategy: VerificationStrategy,
    pub status: EquivalenceStatus,
    pub verification_time: f64,
    pub pathsum_time: f64,
    pub to_dimacs_time: Option<f64>,
    pub tool_time: Option<f64>,
    pub wmc_time: Option<f64>,
    pub tool_name: String,
    pub final_ps: PathSum, 
    /// Present only when QUPRS_STAGE_LEDGER=1, never populated in ordinary runs.
    pub stage_ledger: Option<ExclusiveLedger>,
}

/// Main entry point for equivalence checking with strategy optimization and WMC fallback
pub fn check_equivalence(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    method: VerificationMethod,
    strategy: VerificationStrategy,
    tool_name: &str,
    timeout_secs: u64, // Solver subprocess deadline; strategy-stage abort remains cooperative
) -> Result<EquivalenceCheckResult> {
    let global_start = Instant::now();
    let stage_session = diagnostics::Session::from_environment();
    if timeout_secs == 0 {
        return Err(anyhow::anyhow!("timeout must be a positive number of seconds"));
    }
    let deadline = Some(
        global_start.checked_add(std::time::Duration::from_secs(timeout_secs))
            .ok_or_else(|| anyhow::anyhow!("timeout duration cannot be represented"))?
    );
    
    // 1. Initialize PathSum state
    let regs = vec![crate::pathsum::Register::new("q", num_qubits)];
    let mut ps = PathSum::quantum_circuit(&regs, None);
    let reduction_enabled = method != VerificationMethod::WmcOnly;
    ps.set_auto_reduce(reduction_enabled);

    let mut status = EquivalenceStatus::Unknown;

    // 2. Build the Miter Circuit (C1 * C2^\dagger)
    let pathsum_start = Instant::now();
    let mut ps_miter = strategy.run(ps, gates1, gates2);
    
    // Prepare the initial state |0...0> to form the transition amplitude <0|M|0>
    
    if reduction_enabled {
        ps_miter.full_reduce();
    }

    let ps_time = pathsum_start.elapsed().as_secs_f64();
    
    // 3. Reduction Rules Check
    if method != VerificationMethod::WmcOnly {
        if ps_miter.is_identity_up_to_phase() {
            if let Some(phase_coeff) = ps_miter.get_global_phase() {
                let phase_val = (phase_coeff.constant.numer as f64) / (phase_coeff.constant.denom as f64);
                let angle = phase_val * std::f64::consts::PI; 
                let cos_val = angle.cos();
                let sin_val = angle.sin();
                if (cos_val - 1.0).abs() < 1e-6 && sin_val.abs() < 1e-6 {
                    status = EquivalenceStatus::Equivalent;
                } else {
                    status = EquivalenceStatus::EquivalentUpToGlobalPhase;
                    log::debug!("Residual Global Phase detected: {} radians", angle);
                }
            }
        } else {
            // If the state is not Identity, but there are no internal path variables left,
            // it means it reduced to a definitive non-equivalent Boolean state.
            let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
            if num_active_vars == 0 {
                status = EquivalenceStatus::NotEquivalent;
            } else {
                status = EquivalenceStatus::Unknown;
            }
        }
    }

    // A strategy may overrun its budget; it must never launch an unbounded solver.
    if deadline.is_some_and(|limit| Instant::now() >= limit) {
        status = EquivalenceStatus::Timeout;
    }

    // 4. WMC Fallback (if method is wmc_only, or hybrid returned unknown)
    let mut to_dimacs_time = None;
    let mut tool_time = None;
    let mut wmc_time = None;

    if status != EquivalenceStatus::Timeout && (method == VerificationMethod::WmcOnly || (method == VerificationMethod::Hybrid && status == EquivalenceStatus::Unknown)) {
        let _wmc_scope = diagnostics::span("wmc_total");
        let wmc_start = Instant::now();
        
        let mut wmc_mgr = WmcManager::new(&ps_miter);
        
        {
            let _encode_scope = diagnostics::span("cnf_encode");
            wmc_mgr.encode_trace(&ps_miter);
        }

        let dimacs_start = Instant::now();
        let cnf_string = wmc_mgr.to_dimacs_string(tool_name);
        to_dimacs_time = Some(dimacs_start.elapsed().as_secs_f64());

        let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
        let expected_log2 = (num_qubits as f64) + (num_active_vars as f64) / 2.0;

        let tool_start = Instant::now();
        // No extra path variables does NOT imply the trace is tautologically
        // satisfiable: e.g. Tr(X) = 0 imposes contradictory CNF clauses.
        // Bypass the solver only for a genuinely empty zero-variable CNF.
        let raw_amplitude = if cnf_string.contains("p cnf 0 0") {
            Some(num_complex::Complex::new(2.0_f64.powf(expected_log2), 0.0))
        } else {
            match wmc_mgr.solve_with_deadline(tool_name, deadline) {
                Ok(value) => Some(value),
                Err(error) if error.downcast_ref::<crate::solver_process::SolverTimeout>().is_some() => {
                    status = EquivalenceStatus::Timeout;
                    None
                }
                Err(error) => return Err(error),
            }
        };
        tool_time = Some(tool_start.elapsed().as_secs_f64());

        if let Some(raw_amplitude) = raw_amplitude {
        let _classification_scope = diagnostics::span("classification");
        let normalization_factor = 1.0 / 2.0_f64.powf(expected_log2);
        let final_amplitude = raw_amplitude * normalization_factor;
        info!(target: "wmc", "{} log2 result : {:.4}", tool_name, raw_amplitude.norm().log2());
        info!(target: "wmc", "Expected log2 {:.4}", expected_log2);
        wmc_time = Some(wmc_start.elapsed().as_secs_f64());

        let norm = final_amplitude.norm();
        let theta = final_amplitude.im.atan2(final_amplitude.re);
        debug!(
            "Uncertified WMC trace result (diagnostic only): normalized norm={:.16e}, phase={:.16e} rad; no verified count enclosure",
            norm, theta
        );
        // Numerical closeness, including an exactly rounded 1.0, cannot
        // certify equality. A difference without a rigorous true-trace
        // bound cannot certify inequality either. Ganak/GPMC currently
        // expose no end-to-end certificate, so WMC is fail-closed.
        // Symbolically proven reduction verdicts above remain authoritative.
        status = EquivalenceStatus::Unknown;

        // Independent *structural* certificate for exact discrete gates.
        // No numerical WMC result is used to establish either verdict.
        // With no internal path variables the Boolean ANF is a deterministic
        // truth function. Different output ANFs prove inequivalence; an
        // identical output with an input-independent phase proves equivalence
        // up to that exactly represented phase. Parameterized gate angles
        // are deliberately excluded until the exact source-angle migration.
        let exact_discrete = gates1.iter().chain(gates2.iter()).all(|op| matches!(
            op,
            QuantumOp::H(_) | QuantumOp::X(_) | QuantumOp::Y(_) |
            QuantumOp::Z(_) | QuantumOp::S(_) | QuantumOp::SDG(_) |
            QuantumOp::T(_) | QuantumOp::TDG(_) | QuantumOp::CX(_, _) |
            QuantumOp::CZ(_, _) | QuantumOp::SWAP(_, _) |
            QuantumOp::CCX(_, _, _)
        ));
        let no_internal_paths = ps_miter.v.path_vars.iter()
            .all(|&id| (id as usize) < num_qubits);
        if exact_discrete && no_internal_paths {
            if ps_miter.is_identity_up_to_phase() {
                if let Some(phase) = ps_miter.get_global_phase() {
                    status = if phase.is_zero() {
                        EquivalenceStatus::Equivalent
                    } else {
                        EquivalenceStatus::EquivalentUpToGlobalPhase
                    };
                }
            } else {
                // Boolean ANF for the identity is exactly the singleton
                // variable x_i on every output. No internal paths means a
                // differing ANF is a valid computational-basis witness.
                let differing_boolean_output = ps_miter.f.functions.iter()
                    .enumerate().any(|(i, poly)| {
                        poly.len() != 1 || !poly.contains(&vec![i as u32])
                    });
                if differing_boolean_output {
                    status = EquivalenceStatus::NotEquivalent;
                } else if ps_miter.p.terms.keys().any(|mono| !mono.is_empty()) {
                    // On a deterministic identity Boolean mapping, a
                    // nonconstant reduced multilinear phase polynomial over
                    // exact discrete coefficients witnesses a relative
                    // basis phase. The monomial basis is independent over
                    // Boolean inputs (Möbius inversion), modulo a constant.
                    status = EquivalenceStatus::NotEquivalent;
                }
            }
        }
        }
    }

    let total_time = global_start.elapsed().as_secs_f64();

    Ok(EquivalenceCheckResult {
        qubit_num: num_qubits,
        gate_num1: gates1.len(),
        gate_num2: gates2.len(),
        method,
        strategy,
        status,
        verification_time: total_time,
        pathsum_time: ps_time,
        to_dimacs_time,
        tool_time,
        wmc_time,
        tool_name: tool_name.to_string(),
        final_ps: ps_miter,
        stage_ledger: stage_session.as_ref().map(|session| session.snapshot(total_time, ps_time)),
    })
}
mod ganak_distribution;
mod solver_process;
