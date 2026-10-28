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
mod solver_adapter;
mod wmc_problem;
pub mod solver_result;
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
    /// Requested projective-distance threshold, if the approximate mode ran.
    pub approximate_distance_tolerance: Option<f64>,
    /// Classification provenance; numerical verdicts are not exact proofs.
    pub decision_basis: &'static str,
    pub final_ps: PathSum, 
    /// Present only when QUPRS_STAGE_LEDGER=1, never populated in ordinary runs.
    pub stage_ledger: Option<ExclusiveLedger>,
}

/// Per-request verification configuration shared by native callers and the Python FFI.
///
/// This controls verification dispatch and WMC classification; it does not
/// alter the separate symbolic reduction rules. The projective-distance
/// criterion is separate from the magnitude threshold; an explicit distance
/// takes precedence only when the magnitude setting remains at its default.
#[derive(Debug, Clone)]
pub struct VerificationOptions {
    pub method: VerificationMethod,
    pub strategy: VerificationStrategy,
    pub tool_name: String,
    pub timeout_secs: u64,
    pub wmc_magnitude_tolerance: f64,
    pub wmc_phase_tolerance: f64,
    pub approximate_distance_tolerance: Option<f64>,
}

impl Default for VerificationOptions {
    fn default() -> Self {
        Self {
            method: VerificationMethod::Hybrid,
            strategy: VerificationStrategy::Difference,
            tool_name: "gpmc".to_string(),
            timeout_secs: 600,
            wmc_magnitude_tolerance: 1e-8,
            wmc_phase_tolerance: 1e-8,
            approximate_distance_tolerance: None,
        }
    }
}

/// Typed entry point for native callers. All entry points share the same
/// validation, Path-sum execution and WMC classification implementation.
pub fn check_equivalence_with_options(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    options: &VerificationOptions,
) -> Result<EquivalenceCheckResult> {
    check_equivalence_with_tolerances_mode(
        num_qubits, gates1, gates2, options.method, options.strategy,
        &options.tool_name, options.timeout_secs,
        options.wmc_magnitude_tolerance, options.wmc_phase_tolerance,
        options.approximate_distance_tolerance,
    )
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
    // Keep the legacy function signature, but use the same documented
    // v0.14.0 default thresholds as the Python and PyO3 entry points.
    check_equivalence_with_options(
        num_qubits, gates1, gates2,
        &VerificationOptions {
            method, strategy, tool_name: tool_name.to_owned(), timeout_secs,
            ..VerificationOptions::default()
        },
    )
}

/// WMC decision thresholds are per-request policy, not symbolic reduction rules.
/// This does not change the selected model counter or any PathSum transformation.
pub fn check_equivalence_with_tolerances(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    method: VerificationMethod,
    strategy: VerificationStrategy,
    tool_name: &str,
    timeout_secs: u64,
    wmc_magnitude_tolerance: f64,
    wmc_phase_tolerance: f64,
) -> Result<EquivalenceCheckResult> {
    check_equivalence_with_tolerances_mode(
        num_qubits, gates1, gates2, method, strategy, tool_name,
        timeout_secs, wmc_magnitude_tolerance, wmc_phase_tolerance, None,
    )
}

fn check_equivalence_with_tolerances_mode(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    method: VerificationMethod,
    strategy: VerificationStrategy,
    tool_name: &str,
    timeout_secs: u64,
    wmc_magnitude_tolerance: f64,
    wmc_phase_tolerance: f64,
    approximate_distance_tolerance: Option<f64>,
) -> Result<EquivalenceCheckResult> {
    if !wmc_magnitude_tolerance.is_finite() || wmc_magnitude_tolerance <= 0.0
        || wmc_magnitude_tolerance >= 1.0
        || !wmc_phase_tolerance.is_finite() || wmc_phase_tolerance <= 0.0
        || wmc_phase_tolerance >= 1.0
    {
        return Err(anyhow::anyhow!(
            "WMC magnitude and phase tolerances must be finite in (0, 1)"
        ));
    }
    let distance_defect_threshold = if let Some(eps) = approximate_distance_tolerance {
        if !eps.is_finite() || eps <= 0.0 || eps >= 1.0 {
            return Err(anyhow::anyhow!(
                "approximate_distance_tolerance must be finite and in (0, 1)"
            ));
        }
        if wmc_magnitude_tolerance != 1e-8 {
            return Err(anyhow::anyhow!(
                "approximate_distance_tolerance conflicts with nondefault wmc_magnitude_tolerance"
            ));
        }
        let sq = eps * eps;
        Some(sq / (1.0 + (1.0 - sq).sqrt()))
    } else { None };
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
                // The phase polynomial stores exact cycles modulo 2*pi.
                // Floating sin/cos tolerances cannot prove that a nonzero
                // rational or symbolic scalar is *exactly* identity.
                if phase_coeff.is_zero() {
                    status = EquivalenceStatus::Equivalent;
                } else {
                    status = EquivalenceStatus::EquivalentUpToGlobalPhase;
                    log::debug!("Residual global phase: {} cycles", phase_coeff);
                }
            }
        } else {
            // If the state is not Identity, but there are no internal path variables left,
            // it means it reduced to a definitive non-equivalent Boolean state.
            let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
            if num_active_vars == 0 && approximate_distance_tolerance.is_none() {
                status = EquivalenceStatus::NotEquivalent;
            } else {
                // A strict source residual is not proof of D > epsilon.
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
            wmc_mgr.encode_trace(&ps_miter)?;
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
        // The guard reflects observed solver precision, NOT a certified error bound.
        const APPROX_MAG_GUARD: f64 = 3e-9;
        if let Some(threshold) = distance_defect_threshold {
            let defect = 1.0 - norm;
            status = if !norm.is_finite() || defect < -APPROX_MAG_GUARD
                || (defect - threshold).abs() <= APPROX_MAG_GUARD
            {
                EquivalenceStatus::Unknown
            } else if defect > threshold + APPROX_MAG_GUARD {
                EquivalenceStatus::NotEquivalent
            } else {
                let theta = final_amplitude.im.atan2(final_amplitude.re);
                if theta.abs() < wmc_phase_tolerance {
                    EquivalenceStatus::Equivalent
                } else {
                    EquivalenceStatus::EquivalentUpToGlobalPhase
                }
            };
        } else if (norm - 1.0).abs() < wmc_magnitude_tolerance {
            let theta = final_amplitude.im.atan2(final_amplitude.re);
            info!(target: "wmc", "Final amplitude phase: {:.4} rad", theta);
            if theta.abs() < wmc_phase_tolerance {
                status = EquivalenceStatus::Equivalent;
            } else {
                status = EquivalenceStatus::EquivalentUpToGlobalPhase;
            }
        } else {
            debug!("WMC Normalization Failed. Expected norm: 1.0, Got: {:.4}", norm);
            status = EquivalenceStatus::NotEquivalent;
        }
        }
    }

    let total_time = global_start.elapsed().as_secs_f64();

    let decision_basis = if status == EquivalenceStatus::Unknown {
        "inconclusive"
    } else if wmc_time.is_some() && approximate_distance_tolerance.is_some() {
        "numerical_approximate"
    } else if wmc_time.is_some() {
        "numerical_legacy"
    } else if status == EquivalenceStatus::Timeout || status == EquivalenceStatus::MemoryOut {
        "execution_limit"
    } else { "symbolic" };
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
        approximate_distance_tolerance,
        decision_basis,
        final_ps: ps_miter,
        stage_ledger: stage_session.as_ref().map(|session| session.snapshot(total_time, ps_time)),
    })
}
mod ganak_distribution;
mod solver_process;

#[cfg(test)]
mod exact_global_phase_verdict_tests {
    use super::*;
    use crate::ir::QuantumOp;
    use crate::rational::{Angle, FreeRational};

    // Rz(theta) = exp(-i*theta/2) P(theta), as complete 2x2 unitaries.
    // A nonzero rational multiple of pi is exactly nonzero mod 2*pi;
    // using floating sin/cos acceptance to call it exactly equal is unsound.
    #[test]
    fn red_near_nonzero_global_phase_is_not_exact_equality() {
        for denom in [1000_i64, 10_000_000_i64] {
            let theta = Angle::new_constant(FreeRational::new(1, denom));
            let rz = vec![QuantumOp::RZ(0, theta.clone())];
            let p_gate = vec![QuantumOp::P(0, theta)];
            for (left, right, direction) in [
                (&rz, &p_gate, "RZ_vs_P"),
                (&p_gate, &rz, "P_vs_RZ"),
            ] {
                let r = check_equivalence(
                    1, left, right,
                    VerificationMethod::ReductionRules,
                    VerificationStrategy::Naive,
                    "gpmc", 30,
                ).unwrap();
                assert!(
                    r.final_ps.is_identity_up_to_phase(),
                    "{direction} must be scalar equivalent: {denom}"
                );
                let phase = r.final_ps.get_global_phase().unwrap();
                assert!(!phase.is_zero(),
                        "exact nonzero phase must not disappear: {denom} {direction}");
                assert_eq!(
                    r.status, EquivalenceStatus::EquivalentUpToGlobalPhase,
                    "{direction} at pi/{denom} must not be labeled exactly equal"
                );
                assert!(r.tool_time.is_none(), "Reduction solved; do not run WMC");
            }
        }
    }

    #[test]
    fn exact_phase_zero_clifford_controls_preserved() {
        let theta = Angle::new_constant(FreeRational::new(1, 8));
        let same = vec![QuantumOp::P(0, theta)];
        let r = check_equivalence(
            1, &same, &same,
            VerificationMethod::ReductionRules,
            VerificationStrategy::Naive,
            "gpmc", 30,
        ).unwrap();
        assert!(r.final_ps.get_global_phase().unwrap().is_zero());
        assert_eq!(r.status, EquivalenceStatus::Equivalent);
        assert!(r.tool_time.is_none());
    }
}

#[cfg(test)]
mod verification_options_contract_tests {
    use super::*;

    #[test]
    fn native_default_thresholds_match_python_public_defaults() {
        let options = VerificationOptions::default();
        assert_eq!(options.method, VerificationMethod::Hybrid);
        assert_eq!(options.strategy, VerificationStrategy::Difference);
        assert_eq!(options.tool_name, "gpmc");
        assert_eq!(options.timeout_secs, 600);
        assert_eq!(options.wmc_magnitude_tolerance, 1e-8);
        assert_eq!(options.wmc_phase_tolerance, 1e-8);
    }

    #[test]
    fn legacy_and_typed_native_entrypoints_share_reduction_results() {
        let old = check_equivalence(
            1, &[], &[], VerificationMethod::ReductionRules,
            VerificationStrategy::Naive, "gpmc", 20,
        ).expect("legacy native verification");
        let typed = check_equivalence_with_options(
            1, &[], &[],
            &VerificationOptions {
                method: VerificationMethod::ReductionRules,
                strategy: VerificationStrategy::Naive,
                timeout_secs: 20,
                ..VerificationOptions::default()
            },
        ).expect("typed native verification");
        assert_eq!(old.status, EquivalenceStatus::Equivalent);
        assert_eq!(typed.status, old.status);
        assert!(old.tool_time.is_none());
        assert!(typed.tool_time.is_none());
    }

    #[test]
    fn typed_options_reject_invalid_thresholds_before_solver() {
        let bad = VerificationOptions {
            wmc_magnitude_tolerance: f64::NAN,
            ..VerificationOptions::default()
        };
        assert!(check_equivalence_with_options(1, &[], &[], &bad).is_err());
        let bad = VerificationOptions {
            wmc_phase_tolerance: 0.0,
            ..VerificationOptions::default()
        };
        assert!(check_equivalence_with_options(1, &[], &[], &bad).is_err());
    }
}
