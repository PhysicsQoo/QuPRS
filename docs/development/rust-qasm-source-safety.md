# Native Rust QASM source-safety contract

The native Rust verifier accepts **restricted unitary** subsets of OpenQASM 2.0 and
OpenQASM 3.0. Unsupported source is rejected instead of silently dropping
an operation or treating it as an identity. This applies to both equivalence
checks and direct native circuit loading.

## Supported source boundary

- OpenQASM 2.0 accepts supported `qreg` declarations, `qelib1.inc`,
  optional legacy `creg` metadata, and the unitary gate whitelist in
  [the native parser](../../rust/pathsum/src/qasm.rs).
- OpenQASM 3.0 accepts the separately documented
  [unitary subset](rust-qasm3-supported-subset.md): `qubit` declarations,
  optional `stdgates.inc`, static unitary gates and standalone
  `gphase(theta)`. It is not a general QASM3 interpreter.
- Supported unitary gates include `p`, `cp`, `u1`, `u2`, `u3`, `u`,
  `sx`, `sxdg`, `swap`, and the basic Clifford/rotation gates
  listed in the QASM3 reference. Gate arity, parameters, target indices
  and distinct multi-qubit operands are checked.
- `id` and `barrier` are validated unitary no-ops. Measurement, reset,
  classical control, unsupported includes, custom declarations and
  unknown instructions are not unitary inputs and fail closed.

The parser implements exact supported source-angle operations rather than
approximating or discarding unknown gates. In particular, `cp(theta)`
is lowered using the algebraic controlled-phase decomposition, and
`sx`/`sxdg` use the Clifford `H S H`/`H Sdg H` identities. The
native `P(theta)` and `U1(theta)` phase-polynomial coefficients use
`theta/(2*pi)` cycles for the ket side and the conjugate sign for bra.

## Failure and numerical semantics

Unsupported gates, malformed source, invalid operands or unsupported
parameter syntax raise a parser error; the Python-facing native path
reports an exception rather than a positive or negative equivalence
classification. `unknown` is not a substitute for invalid input.

The Python Qiskit-object-to-Rust QASM2 path has a separate
[explicit global-phase contract](rust-global-phase-contract.md):
unequal source `QuantumCircuit.global_phase` values that the QASM2
bridge cannot transport fail closed. The Python backend can process
supported numeric Qiskit phases, but Qiskit-supplied floating parameters
are not equivalent to exact source-literal decimal provenance.

Supported source syntax does **not** by itself certify the finite-precision
complex WMC result. See [equivalence semantics](equivalence-semantics.md)
and [WMC numerical evidence](wmc-evidence-policy.md) for that boundary.
