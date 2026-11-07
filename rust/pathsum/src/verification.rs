//! Python-aligned facade that calls the existing native verification core.
//! The borrowed gate slices do not incur a copy or an extra solver invocation.
use crate::{check_equivalence_with_options, EquivalenceCheckResult, QuantumCircuit, VerificationOptions};
use anyhow::{bail, Result};

/// Compare two native Rust circuits using the same verification engine as
/// the CLI and PyO3 extension. A circuit-width mismatch is a typed input
/// error, not a fabricated final PathSum (Python's mismatch convention differs).
pub fn check_equivalence(
    circuit1: &QuantumCircuit,
    circuit2: &QuantumCircuit,
    options: &VerificationOptions,
) -> Result<EquivalenceCheckResult> {
    if circuit1.num_qubits() != circuit2.num_qubits() {
        bail!(
            "circuit widths differ: {} vs {} qubits",
            circuit1.num_qubits(),
            circuit2.num_qubits()
        );
    }
    check_equivalence_with_options(
        circuit1.num_qubits(),
        circuit1.operations(),
        circuit2.operations(),
        options,
    )
}
