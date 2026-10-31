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
pub mod precision_count;
mod solver_adapter;
mod wmc_problem;
#[cfg(feature="high-precision-gpmc")]
mod precise_weight;
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
use num_traits::ToPrimitive;
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
    /// Distinguish printed solver evidence from end-to-end certified bounds.
    pub wmc_printed_verdict: Option<&'static str>,
    pub wmc_precision_reason: Option<&'static str>,
    /// Estimated projective-distance print granularity at this Ganak count;
    /// Some only when the requested distance is below the observed granularity.
    /// This is not an upper bound on the solver's arithmetic error.
    pub wmc_print_resolution_distance: Option<f64>,
    /// Requested projective-distance threshold for WMC verification.
    pub approximate_distance_tolerance: Option<f64>,
    /// RR-only/HYBRID used an analytic upper bound for a nonzero residual phase.
    /// This is a tolerance-bounded approximate result, NOT exact source identity.
    pub rr_approximate: bool,
    /// True only when an external weighted counter was invoked.
    pub solver_invoked: bool,
    pub final_ps: PathSum, 
    /// Present only when QUPRS_STAGE_LEDGER=1, never populated in ordinary runs.
    pub stage_ledger: Option<ExclusiveLedger>,
}

/// Per-request verification configuration shared by native callers and the Python FFI.
///
/// This controls verification dispatch and WMC classification; it does not
/// alter the separate symbolic reduction rules. A projective-distance
/// threshold is the sole WMC numerical acceptance metric.
#[derive(Debug, Clone)]
pub struct VerificationOptions {
    pub method: VerificationMethod,
    pub strategy: VerificationStrategy,
    pub tool_name: String,
    pub timeout_secs: u64,
    pub wmc_phase_tolerance: f64, // Compatibility alias for numerical WMC callers.
    pub rr_tolerance: f64,
    pub phase_tolerance: f64,
    pub approximate_distance_tolerance: Option<f64>,
    /// GPMC complex MPFR digits: 30 by default, explicitly 90 if requested.
    pub gpmc_precision_digits: u32,
}

impl Default for VerificationOptions {
    fn default() -> Self {
        Self {
            method: VerificationMethod::Hybrid,
            strategy: VerificationStrategy::Difference,
            tool_name: "gpmc".to_string(),
            timeout_secs: 600,
            wmc_phase_tolerance: 1e-8,
            rr_tolerance: 1e-10,
            phase_tolerance: 1e-8,
            approximate_distance_tolerance: Some(1e-8),
            gpmc_precision_digits: 30,
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
    if options.gpmc_precision_digits != 30 && options.gpmc_precision_digits != 90 {
        return Err(anyhow::anyhow!("gpmc_precision_digits must be 30 or 90"));
    }
    if options.tool_name != "gpmc" && options.gpmc_precision_digits != 30 {
        return Err(anyhow::anyhow!("gpmc_precision_digits=90 only applies to GPMC"));
    }
    if !options.rr_tolerance.is_finite() || options.rr_tolerance <= 0.0 {
        return Err(anyhow::anyhow!("rr_tolerance must be finite and positive"));
    }
    if !options.phase_tolerance.is_finite() || options.phase_tolerance <= 0.0
        || options.phase_tolerance >= 1.0 {
        return Err(anyhow::anyhow!("phase_tolerance must be finite in (0, 1) radians"));
    }
    if options.phase_tolerance != 1e-8 && options.wmc_phase_tolerance != 1e-8
        && options.phase_tolerance != options.wmc_phase_tolerance {
        return Err(anyhow::anyhow!("phase_tolerance conflicts with wmc_phase_tolerance"));
    }
    let effective_phase = if options.phase_tolerance != 1e-8 {
        options.phase_tolerance
    } else {
        options.wmc_phase_tolerance
    };
    check_equivalence_with_distance_mode(
        num_qubits, gates1, gates2, options.method, options.strategy,
        &options.tool_name, options.timeout_secs,
        effective_phase,
        options.rr_tolerance,
        options.approximate_distance_tolerance,
        options.gpmc_precision_digits,
    )
}

/// Conservatively bound a reduced diagonal residual's non-global phase,
/// in *cycles*. A monomial evaluates to 0 or 1. For c in [0,1):
///   |1-exp(2*pi*i*(c+r/pi))| <= 2*pi*min(c,1-c) + 2*|r|.
/// Since pi>3, sum(min(c,1-c)+|r|/3) is a rigorous
/// upper bound in cycles; no f64 PhaseCoeff truncation is performed.
/// This applies ONLY when all path variables have been eliminated and
/// the Boolean output is structurally the identity. Source phases and
/// HH/Omega matching remain exact.
fn rr_residual_upper_cycles(ps: &PathSum) -> Option<num_rational::BigRational> {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use num_traits::{Signed, Zero};
    if ps.v.path_vars.iter().any(|&v| (v as usize) >= ps.v.num_qubits) {
        return None;
    }
    if ps.f.functions.iter().enumerate().any(|(qubit, poly)| {
        poly.len() != 1 || !poly.contains(&vec![qubit as u32])
    }) {
        return None;
    }
    let mut upper = BigRational::zero();
    for (monomial, coeff) in &ps.p.terms {
        if monomial.is_empty() { continue; } // global phase is irrelevant
        if !coeff.symbols.is_empty() { return None; }
        let numer = BigInt::from(coeff.constant.numer);
        let denom = BigInt::from(coeff.constant.denom);
        let nearest = if &numer * 2 <= denom {
            numer
        } else {
            &denom - &numer
        };
        upper += BigRational::new(nearest, denom);
        if let Some(radians) = &coeff.radians {
            // The source stores exact radians; |r|/pi <= |r|/3.
            upper += radians.abs() / BigRational::from_integer(BigInt::from(3));
        }
    }
    Some(upper)
}

/// Compare a non-global residual against the per-call RR tolerance.
/// RR-only and Hybrid use the SAME RR acceptance criterion. The
/// independent projective-distance tolerance only applies if WMC runs.
fn rr_within_tolerance(ps: &PathSum, rr_tolerance: f64) -> bool {
    use num_rational::BigRational;
    use num_traits::Zero;
    let Some(upper) = rr_residual_upper_cycles(ps) else { return false };
    if upper.is_zero() { return false; }
    let Some(cap) = BigRational::from_float(rr_tolerance) else { return false };
    upper < cap
}

/// Classify an exact (possibly nonzero) residual global phase against
/// the user's *numerical* zero-phase threshold, in physical radians.
/// A symbolic unbound phase cannot be compared against a numeric epsilon.
/// Source coefficients are preserved; this only changes the output label.
fn phase_within_tolerance(coeff: &PhaseCoeff, epsilon_rad: f64) -> bool {
    if coeff.is_zero() { return true; }
    if !coeff.symbols.is_empty() { return false; }

    let source_radians_over_pi = match &coeff.radians {
        Some(r) => match r.to_f64() {
            Some(x) if x.is_finite() => x,
            _ => return false,
        },
        None => 0.0,
    };
    let rational_cycles = coeff.constant.numer as f64 / coeff.constant.denom as f64;
    let cycles = (rational_cycles
        + source_radians_over_pi / std::f64::consts::PI).rem_euclid(1.0);
    if !cycles.is_finite() { return false; }
    let rad = std::f64::consts::TAU * cycles.min(1.0 - cycles);
    rad < epsilon_rad
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

fn check_equivalence_with_distance_mode(
    num_qubits: usize,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    method: VerificationMethod,
    strategy: VerificationStrategy,
    tool_name: &str,
    timeout_secs: u64,
    wmc_phase_tolerance: f64,
    rr_tolerance: f64,
    approximate_distance_tolerance: Option<f64>,
    gpmc_precision_digits: u32,
) -> Result<EquivalenceCheckResult> {
    if !rr_tolerance.is_finite() || rr_tolerance <= 0.0 {
        return Err(anyhow::anyhow!("rr_tolerance must be finite and positive"));
    }
    if !wmc_phase_tolerance.is_finite() || wmc_phase_tolerance <= 0.0
        || wmc_phase_tolerance >= 1.0 {
        return Err(anyhow::anyhow!("WMC phase tolerance must be finite in (0, 1)"));
    }
    let eps = approximate_distance_tolerance.unwrap_or(1e-8);
    if !eps.is_finite() || eps <= 0.0 || eps >= 1.0 {
        return Err(anyhow::anyhow!(
            "approximate_distance_tolerance must be finite and in (0, 1)"
        ));
    }
    let approximate_distance_tolerance = Some(eps);
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
    let mut rr_approximate = false;

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
                // The up-to-global-phase relation is established by RR.
                // phase_tolerance intentionally controls the *equivalent*
                // label even for a provably nonzero but sufficiently small
                // phase; the residual source representation stays intact.
                if phase_coeff.is_zero() {
                    status = EquivalenceStatus::Equivalent;
                } else if phase_within_tolerance(&phase_coeff, wmc_phase_tolerance) {
                    status = EquivalenceStatus::Equivalent;
                } else {
                    status = EquivalenceStatus::EquivalentUpToGlobalPhase;
                    log::debug!("Residual global phase: {} cycles", phase_coeff);
                }
            }
        } else {
            // First allow a conservative, per-request approximate RR success
            // for a *diagonal* residual with exact Boolean identity.
            // The source phase polynomial is NEVER rounded or rewritten.
            if rr_within_tolerance(&ps_miter, rr_tolerance) {
                rr_approximate = true;
                let global = ps_miter.p.terms.get(&Vec::new())
                    .cloned().unwrap_or(PhaseCoeff::ZERO);
                status = if phase_within_tolerance(&global, wmc_phase_tolerance) {
                    EquivalenceStatus::Equivalent
                } else {
                    EquivalenceStatus::EquivalentUpToGlobalPhase
                };
            } else {
                let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
                if method == VerificationMethod::ReductionRules && num_active_vars == 0 {
                    // Strict source-negative, without claiming D>epsilon.
                    status = EquivalenceStatus::NotEquivalent;
                } else {
                    status = EquivalenceStatus::Unknown;
                }
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
    let mut solver_invoked = false;
    let mut wmc_printed_verdict: Option<&'static str> = None;
    let mut wmc_precision_reason: Option<&'static str> = None;
    let mut wmc_print_resolution_distance: Option<f64> = None;

    if status != EquivalenceStatus::Timeout && (method == VerificationMethod::WmcOnly || (method == VerificationMethod::Hybrid && status == EquivalenceStatus::Unknown)) {
        let _wmc_scope = diagnostics::span("wmc_total");
        let wmc_start = Instant::now();
        
        let mut wmc_mgr = WmcManager::new(&ps_miter);
        // High-precision source weights are selected only for GPMC's
        // projective-distance mode. All other modes retain their fast path.
        #[cfg(feature="high-precision-gpmc")]
        if tool_name == "gpmc" {
            wmc_mgr.enable_precise_gpmc_weights();
        }

        {
            let _encode_scope = diagnostics::span("cnf_encode");
            wmc_mgr.encode_trace(&ps_miter)?;
        }

        let dimacs_start = Instant::now();
        let _cnf_string = wmc_mgr.to_dimacs_string(tool_name);
        to_dimacs_time = Some(dimacs_start.elapsed().as_secs_f64());

        let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;

        let tool_start = Instant::now();
        // No path variables alone does NOT prove identity (Tr(X) = 0).
        // Prove the encoded WMC exactly: an unweighted tautological CNF
        // has 2^variables satisfying assignments, which must equal the
        // expected unnormalized trace. Never use a floating shortcut.
        let expected_twice_log2 = num_qubits.checked_mul(2)
            .and_then(|twice_n| twice_n.checked_add(num_active_vars))
            .ok_or_else(|| anyhow::anyhow!("WMC normalization overflow"))?;
        let analytic_identity =
            wmc_mgr.has_exact_unweighted_tautology(expected_twice_log2);
        let mut printed_count = None;
        if !analytic_identity {
            solver_invoked = true;
            match wmc_mgr.solve_with_deadline_distance_printed_precision(
                tool_name, deadline, gpmc_precision_digits,
            ) {
                Ok(value) => { printed_count = Some(value); }
                Err(error) if error.downcast_ref::<crate::solver_process::SolverTimeout>().is_some() => {
                    status = EquivalenceStatus::Timeout;
                }
                Err(error) => return Err(error),
            }
        }
        tool_time = solver_invoked.then(|| tool_start.elapsed().as_secs_f64());

        if let Some(count) = &printed_count {
            use num_rational::BigRational;
            use num_traits::{Signed, ToPrimitive, Zero};
            // Printed-output numerical classification only. The former
            // input-error allowance was a conjectural estimate, not a
            // bound on native solver arithmetic or weight conversion.
            let twice = num_qubits.checked_mul(2)
                .and_then(|v| v.checked_add(num_active_vars))
                .ok_or_else(|| anyhow::anyhow!("WMC normalization overflow"))?;
            let twice: i32 = twice.try_into()
                .map_err(|_| anyhow::anyhow!("WMC normalization outside exact transport range"))?;
            let observed = crate::precision_count::classify_with_uncertainty(
                count, twice, &eps.to_string(), &BigRational::zero(),
            )?;
            let printed = observed;
            if tool_name == "ganak" {
                wmc_print_resolution_distance =
                    crate::precision_count::ganak_print_resolution_distance(
                        count, twice, &eps.to_string(),
                    )?;
            }
            use crate::precision_count::PrintedVerdict;
            wmc_printed_verdict = Some(match printed {
                PrintedVerdict::Equivalent => "equivalent",
                PrintedVerdict::NotEquivalent => "not_equivalent",
                PrintedVerdict::UnknownResolution => "unknown",
                PrintedVerdict::UnknownOvershoot => "unknown",
            });
            wmc_precision_reason = Some(match observed {
                PrintedVerdict::UnknownResolution if tool_name == "ganak" =>
                    "ganak_point_estimate_resolution_limited",
                PrintedVerdict::UnknownResolution => "insufficient_printed_resolution",
                PrintedVerdict::UnknownOvershoot => "nonphysical_printed_magnitude",
                _ => "printed_count_uncertified_solver_arithmetic",
            });
            // Print-only uncertainty does not replace the user's selected
            // Ganak numerical estimate with a third inconclusive verdict.
            // Preserve the raw interval result and a separate resolution
            // warning; nonphysical overshoots remain inconclusive.
            let numeric = if tool_name == "ganak" {
                crate::precision_count::ganak_midpoint_verdict(
                    count, twice, &eps.to_string(), observed,
                )?
            } else { observed };
            status = match numeric {
                PrintedVerdict::NotEquivalent => EquivalenceStatus::NotEquivalent,
                PrintedVerdict::Equivalent => {
                    let r = count.real.clone();
                    let i = count.imag.clone();
                    let scale = r.abs() + i.abs();
                    if scale.is_zero() { EquivalenceStatus::Unknown } else {
                        let x = (r / &scale).to_f64();
                        let y = (i / &scale).to_f64();
                        match (x, y) {
                            (Some(re), Some(im)) if re.is_finite() && im.is_finite() => {
                                if im.atan2(re).abs() < wmc_phase_tolerance {
                                    EquivalenceStatus::Equivalent
                                } else { EquivalenceStatus::EquivalentUpToGlobalPhase }
                            }
                            _ => EquivalenceStatus::Unknown,
                        }
                    }
                }
                PrintedVerdict::UnknownResolution | PrintedVerdict::UnknownOvershoot =>
                    EquivalenceStatus::Unknown,
            };
            wmc_time = Some(wmc_start.elapsed().as_secs_f64());
        } else if analytic_identity {
            // This is an exact count proof, not a finite-precision observation.
            let _classification_scope = diagnostics::span("classification");
            wmc_time = Some(wmc_start.elapsed().as_secs_f64());
            status = EquivalenceStatus::Equivalent;
            wmc_precision_reason = Some("analytic_unweighted_tautology");
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
        wmc_printed_verdict,
        wmc_precision_reason,
        wmc_print_resolution_distance,
        approximate_distance_tolerance,
        rr_approximate,
        solver_invoked,
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
        assert_eq!(options.wmc_phase_tolerance, 1e-8);
        assert_eq!(options.approximate_distance_tolerance, Some(1e-8));
        assert_eq!(options.gpmc_precision_digits, 30);
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
    fn typed_approximate_distance_preserves_rr_fast_path_and_strict_negative() {
        use crate::ir::QuantumOp;
        use crate::rational::{Angle, FreeRational};
        let opts = VerificationOptions {
            method: VerificationMethod::ReductionRules,
            strategy: VerificationStrategy::Naive,
            approximate_distance_tolerance: Some(2e-4),
            ..VerificationOptions::default()
        };
        let exact = check_equivalence_with_options(1, &[], &[], &opts).unwrap();
        assert_eq!(exact.status, EquivalenceStatus::Equivalent);
        assert!(exact.wmc_time.is_none());
        assert!(exact.tool_time.is_none());
        // RR-only reports source-exact inequivalence; it does not infer
        // projective-distance separation from that strict verdict.
        // Hybrid/WMC-only retain the independent distance predicate.
        let rotated = vec![QuantumOp::RZ(
            0, Angle::new_constant(FreeRational::new(1, 20_000)),
        )];
        let unresolved = check_equivalence_with_options(
            1, &[], &rotated, &opts,
        ).unwrap();
        assert_eq!(unresolved.status, EquivalenceStatus::NotEquivalent);
        assert!(unresolved.wmc_time.is_none());
        assert!(unresolved.tool_time.is_none());
    }

    #[test]
    fn custom_rr_tolerance_changes_near_identity_without_mutating_source() {
        use crate::ir::QuantumOp;
        use crate::rational::{Angle, FreeRational};
        // Source-exact Rz(pi/1e9) is not the identity, but has a
        // non-global phase residual much smaller than a 1e-8 cycle
        // RR coefficient threshold.
        let near = vec![QuantumOp::RZ(
            0, Angle::new_constant(FreeRational::new(1, 1_000_000_000)),
        )];
        let mut settings = VerificationOptions {
            method: VerificationMethod::ReductionRules,
            strategy: VerificationStrategy::Naive,
            rr_tolerance: 1e-8,
            ..VerificationOptions::default()
        };
        let accepted = check_equivalence_with_options(1, &[], &near, &settings).unwrap();
        assert_eq!(accepted.status, EquivalenceStatus::Equivalent);
        assert!(accepted.rr_approximate);
        assert!(!accepted.solver_invoked);
        assert!(accepted.tool_time.is_none());
        assert!(!accepted.final_ps.p.terms.is_empty(),
                "RR must not discard exact source residual phases");
        settings.rr_tolerance = 1e-12;
        let strict = check_equivalence_with_options(1, &[], &near, &settings).unwrap();
        assert_eq!(strict.status, EquivalenceStatus::NotEquivalent);
        assert!(!strict.rr_approximate);
        assert!(!strict.solver_invoked);
    }

    #[test]
    fn rr_residual_aggregate_bound_is_shared_by_rr_only_and_hybrid() {
        use crate::rational::Rational;
        let mut ps = PathSum::new(2);
        let coeff = PhaseCoeff::new_constant(Rational::new(1, 100_000_000));
        ps.p.add_term(vec![0], coeff.clone());
        ps.p.add_term(vec![1], coeff);
        assert!(!rr_within_tolerance(&ps, 1.5e-8),
                "sum of two 1e-8 cycle terms must exceed 1.5e-8");
        assert!(rr_within_tolerance(&ps, 3e-8),
                "RR uses its own aggregate bound, independent of the WMC distance");
        assert!(!rr_within_tolerance(&ps, 1.9e-8),
                "RR must reject aggregate phase bounds above its tolerance");
        ps.p.add_term(
            vec![0, 1], PhaseCoeff::new_symbolic(42, crate::rational::FreeRational::new(1, 10))
        );
        assert!(rr_residual_upper_cycles(&ps).is_none(),
                "unbound symbolic phase must fail closed");
    }

    #[test]
    fn typed_approximate_distance_rejects_conflicting_inputs() {
        let invalid = VerificationOptions {
            approximate_distance_tolerance: Some(f64::NAN),
            ..VerificationOptions::default()
        };
        assert!(check_equivalence_with_options(1, &[], &[], &invalid).is_err());
        let defaulted = VerificationOptions {
            approximate_distance_tolerance: None,
            ..VerificationOptions::default()
        };
        let result = check_equivalence_with_options(1, &[], &[], &defaulted).unwrap();
        assert_eq!(result.approximate_distance_tolerance, Some(1e-8));
    }

    #[test]
    fn typed_options_reject_invalid_thresholds_before_solver() {
        let bad = VerificationOptions {
            wmc_phase_tolerance: 0.0,
            ..VerificationOptions::default()
        };
        assert!(check_equivalence_with_options(1, &[], &[], &bad).is_err());
    }
}
