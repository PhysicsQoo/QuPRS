# QOO-168 — bounded native OpenQASM 3 subset (research candidate)

The native Rust entrypoint now *tentatively* recognizes an explicitly versioned
`OPENQASM 3.0;` program without converting it to OpenQASM 2 or invoking Qiskit
transpilation. The original QASM2 parser remains a separate versioned path.

## Accepted grammar (one statement per line)

- `OPENQASM 3.0;`, optionally `include "stdgates.inc";` (no custom files).
- `qubit[N] identifier;` and `qubit identifier;` (one qubit); unique names,
  nonzero static sizes, declaration-order register-to-wire mapping.
- Existing strict unitary gate whitelist: `h,x,y,z,s,sdg,t,tdg,sx,sxdg,id,
  cx,cz,swap,ccx,rx,ry,rz,p,cp,u1,u2,u3,u,barrier` with already validated
  number of operands and numeric parameters. A bare named operand is accepted
  only for a scalar `qubit q;`; indexed `q[i]` works for declared qubits.
- Rational multiples of `pi` and source decimal-radian angles retain the
  same Rust `Angle::from_qasm_str` representation and rejection thresholds as
  existing QASM2. No conversion via double-precision transpilation is added.

## Intentionally unsupported (errors, not ignored)

`gphase` (including zero), measured/classical `bit`, measurement, reset,
conditional/loop statements, `input` parameters, opaque/custom gates or
declarations, gate modifiers (`ctrl @`, `inv @`), aliases/slices, custom
includes, hardware qubits, broadcasting and complex OpenQASM3 expressions.

Crucially, `QuantumOp` cannot yet carry an independent scalar `gphase`.
Silently dropping it would corrupt the distinction between exact equality
and equality up to global phase. Therefore *every* gphase statement is
rejected. The parser preserves physical wire ordering via declaration-order
offsets; it does **not** yet round-trip named register metadata through
`PathSum`. QOO-16 owns the broader register-partition proof obligations.

## Validation boundary

- Native Rust unit tests cover 2/3 dual-format equivalent gate IR, multiple
  registers, standalone scalar qubits, exact decimal source, malformed sizes,
  and fail-closed unsupported control.
- Public FFI pytest covers direct QASM3 text, a `.qasm3` file, Python/Rust
  positive controls, a negative Solver-invoking control, source-small-angle
  RR and nonzero relative scalar classification. Unsupported programs must
  raise `ValueError` **before** solver invocation.
- Qiskit 1.4.6 and 2.6.1 are research-source controls only, not an installed
  support declaration; QOO-169 owns release metadata and resolver evidence.
- If native CI or any independent oracle fails, this branch is not admissible.
  No performance claim is made (CodSpeed is the only performance authority).

This is not a general-purpose OpenQASM 3 parser. Remaining semantic gaps,
especially gphase, aliases, register metadata, and full generator-emitted
custom gates, require separate bounded acceptance before release.
