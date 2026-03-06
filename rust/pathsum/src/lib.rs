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

pub use pathsum::PathSum;
pub use rational::{Rational, PhaseCoeff};
pub use strategy::VerificationStrategy;
use ir::QuantumOp;
use wmc::WmcManager;
use num_complex::Complex;
use anyhow::Result;
use std::time::Instant;

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
}

/// Main entry point for equivalence checking with strategy optimization and WMC fallback
pub fn check_equivalence(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    method: VerificationMethod,
    strategy: VerificationStrategy,
    _timeout_secs: u64, // To be implemented with threads if strict abort is needed
) -> Result<EquivalenceCheckResult> {
    let global_start = Instant::now();
    
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

    // 4. WMC Fallback (if method is wmc_only, or hybrid returned unknown)
    let mut to_dimacs_time = None;
    let mut tool_time = None;
    let mut wmc_time = None;

    if method == VerificationMethod::WmcOnly || (method == VerificationMethod::Hybrid && status == EquivalenceStatus::Unknown) {
        let wmc_start = Instant::now();
        
        let mut wmc_mgr = WmcManager::new(&ps_miter);
        wmc_mgr.encode_boolean_state_to_zero(&ps_miter);

        let dimacs_start = Instant::now();
        let cnf_string = wmc_mgr.to_dimacs_string();
        to_dimacs_time = Some(dimacs_start.elapsed().as_secs_f64());

        let tool_start = Instant::now();
        let raw_amplitude = if cnf_string.contains("p cnf 0 0") || ps_miter.v.path_vars.len() == num_qubits {
            Complex::new(1.0, 0.0)
        } else {
            wmc_mgr.solve_with_gpmc()?
        };
        tool_time = Some(tool_start.elapsed().as_secs_f64());

        // Normalize the raw amplitude from GPMC
        let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
        let normalization_factor = 1.0 / 2.0_f64.powf((num_active_vars as f64) / 2.0);
        let final_amplitude = raw_amplitude * normalization_factor;

        wmc_time = Some(wmc_start.elapsed().as_secs_f64());

        // Amplitude validation
        let norm = final_amplitude.norm();
        if (norm - 1.0).abs() < 1e-6 {
            // Check global phase theta
            let theta = final_amplitude.im.atan2(final_amplitude.re);
            if theta.abs() < 1e-6 {
                status = EquivalenceStatus::Equivalent;
            } else {
                status = EquivalenceStatus::EquivalentUpToGlobalPhase;
            }
        } else {
            status = EquivalenceStatus::NotEquivalent;
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
        tool_name: "gpmc".to_string(),
        final_ps: ps_miter,
    })
}