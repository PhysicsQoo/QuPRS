# Scoped native QASM3 / source safety CI consolidation (2026-11-04)

## Single built wheel, all scientific contracts intact

Normal dev pull requests previously triggered *both*
`native-qasm3-contract.yml` and `rust-qasm-source-guard.yml`
for Rust QASM parser changes. Each rebuilt the native extension and reran
`qasm::tests` across essentially the same Python 3.12 Linux runner.

The automatic scoped admission now uses **one source-pinned built wheel**
inside `native-qasm3-contract.yml`, with the **union of both original
path triggers**. Native compilation/source parser tests and independently
evaluated native P/U1 phase normalization tests execute before the wheel
artifact is installed in one clean dependency-resolved Python environment.
The public QASM3 FFI and global-phase contract, complete native fail-closed
gate rejection tests, P/U1 Python/Rust phase semantics, and independent
Graphstate16 Qiskit full-state oracle are retained as separate test steps
and separately archived JUnit/source logs. Tests are never silently marked
passed when a prerequisite stage fails.

`rust-qasm-source-guard.yml` is retained for **manual/research-branch
standalone provenance**, but its automatic dev PR trigger is disabled to
avoid a second recurring build. This does not remove any test source or
lower scientific precision/acceptance thresholds. The cross-platform 12
native jobs and release-ready matrices are unchanged. No GPMC/Ganak
solver implementation, RR, hybrid, WMC or benchmark semantics change.

A small static guard
`.github/scripts/test-native-qasm-gate-unification.cjs` checks the
original union of PR source paths, every retained scientific test family,
exactly one wheel build and available independent manual run.
