# Explicit global-phase handling through the Rust QASM2 bridge

A Qiskit `QuantumCircuit` can carry an explicit `global_phase`.
The Python-to-Rust OpenQASM2 bridge cannot transport that independent
scalar as a standalone OpenQASM2 instruction. Silently stripping a
*difference* between the circuits' source global phases can therefore
misclassify strict `equivalent` versus `equivalent*` results.

For the Rust backend's QASM2 input path, the interface validates
the source phase scalars **before** native QASM conversion or WMC:

- Two identical, finite, bound source phase scalars cancel and normal
  verification proceeds.
- Unequal source scalars fail closed with `ValueError`, rather than
  publishing an ungrounded scientific verdict.
- An unbound symbolic or non-finite source phase fails closed.
- An OpenQASM2 string has no independent standalone `gphase` value;
  Qiskit-object-to-QASM2 transport must not silently invent one.

This deliberately conservative QASM2 rule can reject a comparison that
would otherwise be exactly equal after accounting for gate-derived
global phase. Rejection is preferable to a false exact-equivalence result.

This is **not** a limitation on all supported native source formats:
the [bounded native OpenQASM3 unitary subset](rust-qasm3-supported-subset.md)
includes a standalone `gphase(theta)` statement with its own parser
and provenance contract. Nor does this QASM2 guard by itself imply
complete cross-backend global-phase or arbitrary parameterized-angle
certification.

Scientific regression examples: `test/test_rust_global_phase_qasm_contract.py`
and `test/test_qasm3_python_global_phase.py`.
For supported Qiskit versions consult
[Qiskit compatibility](qiskit-1x-2x-admission.md); for exact/unitary
classification consult [equivalence semantics](equivalence-semantics.md)
and [v0.14.0 migration](v0140-migration.md).
