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
/// RR tolerance controls approximate non-global phase normalization and
/// HH/Omega matching. Phase and projective-distance tolerances are separate.
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
    if !options.rr_tolerance.is_finite() || options.rr_tolerance < 0.0 {
        return Err(anyhow::anyhow!("rr_tolerance must be finite and non-negative"));
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
/// HH/Omega matching use the per-request RR tolerance.
/// Enclose pi using Machin's formula with exact alternating arctan series.
/// Calculated only when a QASM source phase contains exact decimal radians;
/// pure Clifford/rational phases retain the allocation-free fast path.
fn certified_pi_interval() -> &'static (num_rational::BigRational, num_rational::BigRational) {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use num_traits::Zero;
    use std::sync::OnceLock;
    static PI: OnceLock<(BigRational, BigRational)> = OnceLock::new();
    PI.get_or_init(|| {
        let atan_interval = |denom: i64| {
            let x = BigRational::new(BigInt::from(1), BigInt::from(denom));
            let x_sq = x.clone() * x.clone();
            let mut power = x;
            let mut sum = BigRational::zero();
            const TERMS: usize = 40; // error < 1e-55 at x=1/5
            for k in 0..TERMS {
                let term = power.clone()
                    / BigRational::from_integer(BigInt::from((2 * k + 1) as u64));
                if k % 2 == 0 { sum += term; } else { sum -= term; }
                power *= x_sq.clone();
            }
            let remainder = power
                / BigRational::from_integer(BigInt::from((2 * TERMS + 1) as u64));
            // TERMS is even: the omitted alternating term is positive.
            (sum.clone(), sum + remainder)
        };
        let (a_lo, a_hi) = atan_interval(5);
        let (b_lo, b_hi) = atan_interval(239);
        let sixteen = BigRational::from_integer(BigInt::from(16));
        let four = BigRational::from_integer(BigInt::from(4));
        // pi = 16 atan(1/5) - 4 atan(1/239).
        (sixteen.clone() * a_lo - four.clone() * b_hi,
         sixteen * a_hi - four * b_lo)
    })
}

/// A rigorous upper bound on the distance of c + r/pi to an integer.
/// Unlike |c| + |r|/3, the interval retains cancellation between source
/// decimal radians and exact rational multiples of pi.
/// Enclose the distance, in phase cycles, from a source coefficient to
/// a requested Clifford target.  The rational source coefficients are never
/// converted to binary64 or rounded to a target during matching.
/// A narrow, rigorously enclosing pi interval with a compact denominator.
/// The expensive Machin interval is computed once, then rounded outwards.
/// This bounds the common RR matches without repeated huge-denominator GCDs.
fn compact_pi_interval() -> &'static (num_rational::BigRational, num_rational::BigRational) {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use std::sync::OnceLock;
    static COMPACT_PI: OnceLock<(BigRational, BigRational)> = OnceLock::new();
    COMPACT_PI.get_or_init(|| {
        // 40 decimal digits leave substantial resolution below default RR
        // and phase tolerances; exact fallback handles tighter boundaries.
        let scale = BigInt::from(10_u8).pow(40);
        let scaled = BigRational::from_integer(scale.clone());
        let (lo, hi) = certified_pi_interval();
        let lower = (lo.clone() * scaled.clone()).to_integer();
        let upper = (hi.clone() * scaled).to_integer() + BigInt::from(1);
        (BigRational::new(lower, scale.clone()),
         BigRational::new(upper, scale))
    })
}

fn phase_cycles_upper_target_with_pi(
    coeff: &PhaseCoeff,
    target: crate::rational::Rational,
    pi: &(num_rational::BigRational, num_rational::BigRational),
) -> num_rational::BigRational {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use num_traits::Signed;

    let c = BigRational::new(
        BigInt::from(coeff.constant.numer), BigInt::from(coeff.constant.denom)
    ) - BigRational::new(
        BigInt::from(target.numer), BigInt::from(target.denom)
    );
    let (lo, hi) = if let Some(r) = &coeff.radians {
        let a = c.clone() + r.clone() / pi.0.clone();
        let b = c + r.clone() / pi.1.clone();
        if a <= b { (a, b) } else { (b, a) }
    } else {
        (c.clone(), c)
    };

    let two = BigRational::from_integer(BigInt::from(2));
    let midpoint_integer = ((lo.clone() + hi.clone()) / two).to_integer();
    // Integer truncation may differ from rounding for a negative midpoint;
    // checking its immediate neighbours covers the nearest integer.
    let mut best: Option<BigRational> = None;
    for offset in -1_i64..=1_i64 {
        let integer = BigRational::from_integer(
            midpoint_integer.clone() + BigInt::from(offset)
        );
        let low_distance = (lo.clone() - integer.clone()).abs();
        let high_distance = (hi.clone() - integer).abs();
        let bound = if low_distance > high_distance { low_distance } else { high_distance };
        if best.as_ref().is_none_or(|old| &bound < old) {
            best = Some(bound);
        }
    }
    best.expect("nearest-integer candidates are nonempty")
}

/// Full-strength exact source-radian interval for residual diagnostics.
pub(crate) fn phase_cycles_upper_target(
    coeff: &PhaseCoeff,
    target: crate::rational::Rational,
) -> num_rational::BigRational {
    phase_cycles_upper_target_with_pi(coeff, target, certified_pi_interval())
}

/// The common fast acceptance path is still a mathematical upper bound:
/// the compact pi interval encloses the true value. A near-boundary case
/// falls back to the original full Machin interval, preserving semantics.
pub(crate) fn phase_cycles_within_tolerance(
    coeff: &PhaseCoeff,
    target: crate::rational::Rational,
    tolerance: &num_rational::BigRational,
) -> bool {
    if coeff.radians.is_some()
        && phase_cycles_upper_target_with_pi(coeff, target, compact_pi_interval()) <= *tolerance
    {
        return true;
    }
    phase_cycles_upper_target(coeff, target) <= *tolerance
}

fn rr_residual_upper_cycles(ps: &PathSum) -> Option<num_rational::BigRational> {
    use num_rational::BigRational;
    use num_traits::Zero;
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
        if monomial.is_empty() { continue; } // scalar phase is classified separately
        if !coeff.symbols.is_empty() { return None; }
        // A mixed exact-decimal/pi coefficient needs a joint interval,
        // otherwise the triangle bound loses nearly all cancellation.
        let term = if coeff.radians.is_some() {
            phase_cycles_upper_target(coeff, crate::rational::Rational::ZERO)
        } else {
            // The interval is never built for pure rational/Clifford cases.
            let c = num_rational::BigRational::new(
                num_bigint::BigInt::from(coeff.constant.numer),
                num_bigint::BigInt::from(coeff.constant.denom),
            );
            let one = BigRational::from_integer(num_bigint::BigInt::from(1));
            if c <= one.clone() - c.clone() { c } else { one - c }
        };
        upper += term;
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
    if !rr_tolerance.is_finite() || rr_tolerance < 0.0 {
        return Err(anyhow::anyhow!("rr_tolerance must be finite and non-negative"));
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
    ps.rr_tolerance = rr_tolerance;

    let mut status = EquivalenceStatus::Unknown;
    let mut rr_approximate = false;

    // 2. Build the Miter Circuit (C1 * C2^\dagger)
    let pathsum_start = Instant::now();
    let mut ps_miter = strategy.run(ps, gates1, gates2);
    ps_miter.rr_tolerance = rr_tolerance;
    
    // Prepare the initial state |0...0> to form the transition amplitude <0|M|0>
    
    if reduction_enabled {
        ps_miter.full_reduce();
    }

    rr_approximate |= ps_miter.rr_approximate;
    let mut ps_time = pathsum_start.elapsed().as_secs_f64();
    
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
        // RR tolerance may have removed near-zero terms or accepted near-Clifford
        // rule coefficients.  If RR did not settle Hybrid, reconstruct the
        // exact-source PathSum for WMC so the solver never receives a rounded
        // RR working polynomial.  No extra solver invocation is introduced.
        if method == VerificationMethod::Hybrid && ps_miter.rr_approximate {
            let mut exact_ps = PathSum::quantum_circuit(&regs, None);
            exact_ps.set_auto_reduce(true);
            // PathSum defaults to rr_tolerance=0: exact HH/Omega/Elim only.
            let replay_start = Instant::now();
            ps_miter = strategy.run(exact_ps, gates1, gates2);
            ps_miter.full_reduce();
            // Account exact-source replay as PathSum work, not solver time.
            ps_time += replay_start.elapsed().as_secs_f64();
        }

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
                PrintedVerdict::UnknownDistanceRange => "unknown",
            });
            wmc_precision_reason = Some(match observed {
                PrintedVerdict::UnknownResolution if tool_name == "ganak" =>
                    "ganak_point_estimate_resolution_limited",
                PrintedVerdict::UnknownResolution => "insufficient_printed_resolution",
                PrintedVerdict::UnknownDistanceRange => "distance_interval_outside_tolerance",
                _ => "printed_count_uncertified_solver_arithmetic",
            });
            // Printed-rounding intervals are only diagnostics. Both GPMC
            // and Ganak use the same projective-distance decision based on
            // their finite printed count's center value. An overshoot or
            // coarse stdout can warn, but cannot override the distance.
            // Keep observed for wmc_printed_verdict and precision provenance.
            let numeric = crate::precision_count::observed_distance_verdict(
                count, twice, &eps.to_string(),
            )?;
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
                PrintedVerdict::UnknownResolution | PrintedVerdict::UnknownDistanceRange =>
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
    fn compact_pi_interval_is_certified_and_strictly_bounded() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        let (full_lo, full_hi) = certified_pi_interval();
        let (fast_lo, fast_hi) = compact_pi_interval();
        assert!(fast_lo <= full_lo && full_hi <= fast_hi);
        assert!(fast_hi - fast_lo < BigRational::new(BigInt::from(1), BigInt::from(10_u8).pow(39)));
    }

    #[test]
    fn compact_rr_decision_matches_full_pi_near_and_below_threshold() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        use crate::rational::Rational;
        let phases = [
            (1_i64, 1_000_000_000_i64),
            (1, 100_000_000_000),
            (-1, 10_000_000_000),
            (1, 10_000_000_000_000),
        ];
        for (numer, denom) in phases {
            let coeff = PhaseCoeff {
                constant: Rational::QUARTER,
                radians: Some(BigRational::new(BigInt::from(numer), BigInt::from(denom))),
                symbols: Default::default(),
            };
            for eps in [1e-8_f64, 1e-12, 1e-16, 1e-20, 1e-30, 1e-45] {
                let tolerance = BigRational::from_float(eps).unwrap();
                let full = phase_cycles_upper_target(&coeff, Rational::QUARTER) <= tolerance;
                let compact = phase_cycles_within_tolerance(&coeff, Rational::QUARTER, &tolerance);
                assert_eq!(full, compact, "failed phase {numer}/{denom} at epsilon {eps}");
            }
        }
    }

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
    fn zero_rr_tolerance_is_valid_and_retains_exact_clifford_identity() {
        let mut options = VerificationOptions {
            method: VerificationMethod::ReductionRules,
            strategy: VerificationStrategy::Naive,
            rr_tolerance: 0.0,
            ..VerificationOptions::default()
        };
        let exact = check_equivalence_with_options(1, &[], &[], &options)
            .expect("zero RR tolerance must be accepted");
        assert_eq!(exact.status, EquivalenceStatus::Equivalent);
        assert!(!exact.rr_approximate);
        assert!(!exact.solver_invoked);
        options.rr_tolerance = -1e-10;
        assert!(check_equivalence_with_options(1, &[], &[], &options).is_err());
        options.rr_tolerance = f64::NAN;
        assert!(check_equivalence_with_options(1, &[], &[], &options).is_err());
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
        assert!(accepted.final_ps.p.terms.keys().all(|monomial| monomial.is_empty()),
                "Approximate RR may discard non-global working terms, not scalar phase");
        assert!(accepted.final_ps.p.terms.contains_key(&Vec::new()),
                "Rz global phase must remain unrounded");
        settings.rr_tolerance = 1e-12;
        let strict = check_equivalence_with_options(1, &[], &near, &settings).unwrap();
        assert_eq!(strict.status, EquivalenceStatus::NotEquivalent);
        assert!(!strict.rr_approximate);
        assert!(!strict.solver_invoked);
    }

    #[test]
    fn hybrid_fallback_wmc_uses_unrounded_source_after_approximate_rr() {
        use crate::ir::QuantumOp;
        use crate::rational::{Angle, FreeRational};
        let source = vec![
            QuantumOp::RZ(0, Angle::new_constant(FreeRational::new(1, 1_000_000_000))),
            QuantumOp::X(0),
        ];
        let mut settings = VerificationOptions {
            method: VerificationMethod::Hybrid,
            strategy: VerificationStrategy::Naive,
            rr_tolerance: 1e-8,
            ..VerificationOptions::default()
        };
        let hybrid = check_equivalence_with_options(1, &[], &source, &settings)
            .expect("Hybrid one-qubit fallback");
        settings.method = VerificationMethod::WmcOnly;
        let exact = check_equivalence_with_options(1, &[], &source, &settings)
            .expect("WMC-only source reference");
        assert!(hybrid.rr_approximate, "RR must record removal of a tiny phase");
        assert!(hybrid.solver_invoked, "unresolved Hybrid must invoke WMC");
        assert_eq!(hybrid.final_ps.p.terms, exact.final_ps.p.terms,
            "WMC fallback cannot use the approximately rounded RR polynomial");
        assert_eq!(hybrid.final_ps.f.functions, exact.final_ps.f.functions);
        assert_eq!(hybrid.status, exact.status);
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
    fn source_radian_pi_cancellation_uses_certified_rr_interval() {
        use crate::rational::{Angle, Rational};
        let mut ps = PathSum::new(16);
        // Four terms each for the two exact decimal literals in the
        // Qiskit-transpiled Graphstate16 source contract.
        for (i, literal) in [
            "3.1415926535897931", "3.1415926535897911"
        ].into_iter().cycle().take(8).enumerate() {
            let angle = Angle::from_qasm_str(literal).expect("exact decimal source");
            let rad = angle.radians.expect("decimal radian coefficient")
                / num_rational::BigRational::from_integer(num_bigint::BigInt::from(-2));
            let coeff = PhaseCoeff {
                constant: Rational::HALF,
                radians: Some(rad),
                symbols: Default::default(),
            };
            ps.p.add_term(vec![i as u32], coeff);
        }
        assert!(rr_within_tolerance(&ps, 1e-10),
                "source-exact pi cancellation is below the public RR tolerance");
        assert!(!rr_within_tolerance(&ps, 1e-18),
                "nonzero source residual must not be classified as exact");
        let mut outside = PathSum::new(1);
        let angle = Angle::from_qasm_str("3.1415936535897931").unwrap();
        outside.p.add_term(vec![0], PhaseCoeff {
            constant: Rational::HALF,
            radians: angle.radians.map(|r| -r / num_rational::BigRational::from_integer(
                num_bigint::BigInt::from(2)
            )),
            symbols: Default::default(),
        });
        assert!(!rr_within_tolerance(&outside, 1e-10),
                "a genuine 1e-6 radian mismatch cannot pass the RR guard");
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
