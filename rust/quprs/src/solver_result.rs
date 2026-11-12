//! Explicit numeric solver observations and fail-closed error categories.
//!
//! These types intentionally do not interpret native floating counts as
//! independently certified weighted-model-counting proofs.
use num_complex::Complex;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SolverFailureKind {
    Unsupported,
    NonzeroExit,
    MissingCount,
    MalformedCount,
}

#[derive(Debug)]
pub struct SolverFailure {
    pub kind: SolverFailureKind,
    pub solver_id: String,
    pub details: String,
}

impl SolverFailure {
    pub(crate) fn new(
        kind: SolverFailureKind,
        solver_id: &str,
        details: impl Into<String>,
    ) -> Self {
        Self { kind, solver_id: solver_id.to_string(), details: details.into() }
    }
}
impl std::fmt::Display for SolverFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Keep existing diagnostic content visible in error messages.
        write!(f, "{}", self.details)
    }
}
impl std::error::Error for SolverFailure {}

#[derive(Debug, Clone)]
pub struct SolverObservation {
    pub solver_id: String,
    pub arguments: Vec<String>,
    pub count: Complex<f64>,
    pub exit_code: i32,
    pub elapsed_seconds: f64,
    /// A native floating-point observation is not an exact certificate.
    pub exact_count_certificate: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn observation_and_failure_types_cannot_imply_exact_certificate() {
        let result = SolverObservation {
            solver_id: "ganak".into(), arguments: vec!["--mode=6".into()],
            count: Complex::new(1.5, -0.25),
            exit_code: 0, elapsed_seconds: 0.1,
            exact_count_certificate: false,
        };
        assert_eq!(result.count, Complex::new(1.5, -0.25));
        assert!(!result.exact_count_certificate);
        let error=SolverFailure::new(
            SolverFailureKind::MissingCount, "ganak", "ganak Error!"
        );
        assert_eq!(error.kind, SolverFailureKind::MissingCount);
        assert_eq!(error.solver_id, "ganak");
        assert!(error.to_string().contains("Error!"));
    }
}
