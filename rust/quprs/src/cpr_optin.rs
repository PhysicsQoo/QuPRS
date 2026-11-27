//! Experimental strict native CPR request/stop contract.
use super::*;

/// Machine-readable experimental error context, downcastable from anyhow.
/// Not an equivalence verdict; no partially constructed residual escapes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CprErrorKind {
    Unsupported,
    InvalidRequest,
    BuildDeadline,
    TermLimit,
    LiftLimit,
    UntrackedNormalization,
    ApproximateReduction,
    InvalidResidual,
    Normalization,
    NativeFailure,
}

impl std::fmt::Display for CprErrorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "experimental CPR: {self:?}")
    }
}
impl std::error::Error for CprErrorKind {}

fn build_error(stop: cpr::BuildStop) -> anyhow::Error {
    use cpr::BuildStop::*;
    let kind = match stop {
        Deadline => CprErrorKind::BuildDeadline,
        TermCap => CprErrorKind::TermLimit,
        LiftCap => CprErrorKind::LiftLimit,
        UntrackedElim => CprErrorKind::UntrackedNormalization,
        Approximate => CprErrorKind::ApproximateReduction,
        InvalidResidual => CprErrorKind::InvalidResidual,
    };
    anyhow::Error::new(kind).context(format!("construction stopped: {stop:?}"))
}

fn handoff_error(error: anyhow::Error) -> anyhow::Error {
    let kind = if error.downcast_ref::<cpr::NormalizationError>().is_some() {
        CprErrorKind::Normalization
    } else {
        CprErrorKind::NativeFailure
    };
    error.context(kind)
}

fn numeric(op: &QuantumOp) -> bool {
    use QuantumOp::*;
    match op {
        GlobalPhase(a) | P(_,a) | RX(_,a) | RY(_,a) | RZ(_,a) | U1(_,a) =>
            a.symbols.is_empty(),
        U2(_,a,b) => a.symbols.is_empty() && b.symbols.is_empty(),
        U3(_,a,b,c) | U(_,a,b,c) =>
            a.symbols.is_empty() && b.symbols.is_empty() && c.symbols.is_empty(),
        H(_) | X(_) | Y(_) | Z(_) | S(_) | SDG(_) | T(_) | TDG(_) |
        CX(_,_) | CZ(_,_) | SWAP(_,_) | CCX(_,_,_) => true,
    }
}

/// Strict numeric Hybrid/Difference/GPMC opt-in; available on native
/// targets only with the non-default experimental-cpr Cargo feature.
/// BuildDeadline, TermLimit, LiftLimit and untracked normalization are
/// errors without a partial verdict; a complete native handoff may instead
/// return the ordinary Timeout status. Native solver errors remain errors.
/// Limits are cooperative, not hard per-operation bounds. No auto fallback.
/// The default API and Python API never select CPR.
pub fn check_equivalence_cpr_experimental(
    num_qubits: usize, gates1: &[QuantumOp], gates2: &[QuantumOp],
    options: &VerificationOptions,
) -> Result<EquivalenceCheckResult> {
    if options.method != VerificationMethod::Hybrid
        || options.strategy != VerificationStrategy::Difference
        || options.tool_name != "gpmc" || options.rr_tolerance != 0.0 {
        return Err(anyhow::Error::new(CprErrorKind::Unsupported)
            .context("requires strict Hybrid/Difference/GPMC"));
    }
    #[cfg(feature="browser-transport")]
    if crate::browser_transport::active() {
        return Err(anyhow::Error::new(CprErrorKind::Unsupported)
            .context("CPR is native-only; browser capture/replay not admitted"));
    }
    let phase = validate_verification_options(options)
        .map_err(|e| e.context(CprErrorKind::InvalidRequest))?;
    let eps = options.approximate_distance_tolerance.unwrap_or(1e-8);
    if !(phase.is_finite() && phase > 0.0 && phase < 1.0 &&
         eps.is_finite() && eps > 0.0 && eps < 1.0 && options.timeout_secs > 0) {
        return Err(anyhow::Error::new(CprErrorKind::InvalidRequest)
            .context("invalid effective phase, distance or timeout"));
    }
    // The initial identity already contains one Boolean term per wire.
    // Reject the existing term-cap violation before allocating it.
    if num_qubits > cpr::TERM_CAP {
        return Err(build_error(cpr::BuildStop::TermCap));
    }
    let start = Instant::now();
    let deadline = start.checked_add(crate::clock::Duration::from_secs(options.timeout_secs))
        .ok_or_else(|| anyhow::Error::new(CprErrorKind::InvalidRequest)
            .context("timeout duration cannot be represented"))?;
    let build_deadline = deadline.min(start + crate::clock::Duration::from_secs(15));
    // Reuse existing circuit validation without cloning the gate slices.
    let circuit = QuantumCircuit::new(num_qubits);
    for gate in gates1.iter().chain(gates2) {
        if Instant::now() >= build_deadline {
            return Err(build_error(cpr::BuildStop::Deadline));
        }
        circuit.validate(gate).map_err(|e| e.context(CprErrorKind::InvalidRequest))?;
        if !numeric(gate) {
            return Err(anyhow::Error::new(CprErrorKind::Unsupported)
                .context("unbound symbolic angle"));
        }
    }
    let session = diagnostics::Session::from_environment();
    let build_start = Instant::now();
    let built = cpr::build_difference(num_qubits, gates1, gates2, build_deadline)
        .map_err(build_error)?;
    if gates1.len().checked_add(gates2.len()) != Some(built.gates_applied) {
        return Err(anyhow::Error::new(CprErrorKind::InvalidResidual)
            .context("incomplete CPR stream"));
    }
    finish_native_verification(
        built.residual, num_qubits, gates1.len(), gates2.len(), options.method,
        options.strategy, &options.tool_name, phase, options.rr_tolerance,
        eps, options.gpmc_precision_digits, start, build_start, Some(deadline),
        session.as_ref(), Some(&built.pairs), true,
    ).map_err(handoff_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rational::{Angle, FreeRational};

    fn options() -> VerificationOptions {
        VerificationOptions { rr_tolerance: 0.0, timeout_secs: 27,
            gpmc_precision_digits: 90, ..VerificationOptions::default() }
    }
    fn assert_kind(result: Result<EquivalenceCheckResult>, kind: CprErrorKind) {
        let Err(error) = result else { panic!("expected error {kind:?}") };
        assert_eq!(error.downcast_ref::<CprErrorKind>(), Some(&kind), "{error:#}");
    }

    #[test]
    fn optin_request_and_rr_first_contract() {
        use CprErrorKind::*;
        let mut o = options();
        let check = |o: &VerificationOptions| check_equivalence_cpr_experimental(1,&[],&[],o);
        o.method = VerificationMethod::ReductionRules;
        assert_kind(check(&o), Unsupported);
        o = options(); o.strategy = VerificationStrategy::Naive;
        assert_kind(check(&o), Unsupported);
        o = options(); o.tool_name = "ganak".into();
        assert_kind(check(&o), Unsupported);
        o = options(); o.rr_tolerance = 1e-10;
        assert_kind(check(&o), Unsupported);
        o = options(); o.timeout_secs = 0;
        assert_kind(check(&o), InvalidRequest);
        o = options(); o.gpmc_precision_digits = 60;
        assert_kind(check(&o), InvalidRequest);
        o = options(); o.approximate_distance_tolerance = Some(f64::NAN);
        assert_kind(check(&o), InvalidRequest);
        o = options(); o.phase_tolerance = 1e-7; o.wmc_phase_tolerance = 1e-6;
        assert_kind(check(&o), InvalidRequest);
        o = options(); o.wmc_phase_tolerance = f64::NAN;
        assert_kind(check(&o), InvalidRequest);
        o = options();
        assert_kind(check_equivalence_cpr_experimental(1,&[QuantumOp::H(1)],&[],&o), InvalidRequest);
        assert_kind(check_equivalence_cpr_experimental(2,&[QuantumOp::SWAP(0,0)],&[],&o), InvalidRequest);
        let angle = Angle::new_symbolic(0,FreeRational::HALF);
        assert_kind(check_equivalence_cpr_experimental(1,&[QuantumOp::RZ(0,angle)],&[],&o), Unsupported);
        assert_kind(check_equivalence_cpr_experimental(cpr::TERM_CAP+1,&[],&[],&o), TermLimit);
        let r = check(&o).unwrap();
        assert_eq!(r.status,EquivalenceStatus::Equivalent);
        assert!(!r.solver_invoked);
        let r = check_equivalence_cpr_experimental(1,&[QuantumOp::H(0),QuantumOp::H(0)],&[],&o).unwrap();
        assert_eq!(r.status,EquivalenceStatus::Equivalent);
        assert!(!r.solver_invoked);
    }

    #[test]
    fn stop_and_native_failure_classification() {
        use cpr::BuildStop::*;
        for (stop, kind) in [
            (Deadline,CprErrorKind::BuildDeadline),(TermCap,CprErrorKind::TermLimit),
            (LiftCap,CprErrorKind::LiftLimit),(UntrackedElim,CprErrorKind::UntrackedNormalization),
            (Approximate,CprErrorKind::ApproximateReduction),(InvalidResidual,CprErrorKind::InvalidResidual),
        ] {
            assert_eq!(build_error(stop).downcast_ref::<CprErrorKind>(),Some(&kind));
        }
        let error = handoff_error(anyhow::anyhow!("test failure").context(cpr::NormalizationError));
        assert_eq!(error.downcast_ref::<CprErrorKind>(),Some(&CprErrorKind::Normalization));
        let error = handoff_error(anyhow::anyhow!("native failure"));
        assert_eq!(error.downcast_ref::<CprErrorKind>(),Some(&CprErrorKind::NativeFailure));
    }

    #[cfg(feature="browser-transport")]
    #[test]
    fn browser_capture_is_not_native_optin() {
        let (result,job) = crate::browser_transport::capture(||
            check_equivalence_cpr_experimental(1,&[],&[],&options()));
        assert_kind(result,CprErrorKind::Unsupported);
        assert!(job.is_none());
    }
}
