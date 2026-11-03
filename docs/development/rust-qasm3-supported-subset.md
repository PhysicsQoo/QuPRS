# QOO-168 — native Rust OpenQASM 3 unitary subset

QuPRS accepts a **bounded, explicitly versioned OpenQASM 3 subset** directly
as a string or file for the Rust verifier. The source is parsed into native
Rust `QuantumOp`/`Angle` operations and is **not** converted to OpenQASM 2
or passed through Qiskit transpilation. This contract does not imply support
for all OpenQASM 3 syntax, arbitrary circuits, or quantum instruments.

## Accepted syntax (one statement per line)

- `OPENQASM 3.0;`, optional `include "stdgates.inc";` (no custom includes).
- `qubit[N] register;` or `qubit scalar;`, where `N` is a positive
  compile-time integer. Distinct declarations map to wires in declaration
  order. Indexed operands `register[i]` and scalar operands `scalar` are
  accepted; a whole multi-qubit register is **not** broadcast as a gate target.
- Existing native unitary whitelist:
  `h, x, y, z, s, sdg, t, tdg, sx, sxdg, id, cx, cz, swap, ccx, rx,
  ry, rz, p, cp, u1, u2, u3, u, barrier`; gate arity and operand validation
  remains mandatory.
- Supported angles include exact rational multiples of `pi` and
  source decimal radians via the Rust `Angle::from_qasm_str` path, with no
  lossy QASM2 intermediate.
- `gphase(theta);`: a standalone static scalar operation held in
  `QuantumOp::GlobalPhase(Angle)`. The PathSum constant phase receives
  `theta/(2*pi)` for ket and the negative for bra. Opposite scalar
  phases and complete `2*pi` cycles cancel exactly.

## Fail-closed boundary

The parser rejects unknown gates and parameters, nonconstant expressions
outside the supported angle grammar, declarations for classical `bit`,
`measure`, `reset`, dynamic control flow, gate modifiers, aliases,
nonstandard include files, custom declarations, arbitrary slices, and
broadcasts. It never silently erases unsupported operations.

The Python verifier also rejects Qiskit `measure` and `reset` rather than
treating them as identity operations. It transports `QuantumCircuit.global_phase`
through `build_circuit` and the public RR/Hybrid/WMC miter, but the value
has **already been interpreted by Qiskit** as a floating numeric scalar.
Therefore Python-level source-literal exactness is **not** equivalent to the
native Rust `Angle` provenance. Unbound/nonfinite scalars are rejected.
The existing Qiskit-object-to-Rust QASM2 bridge continues to fail closed on
unequal explicit `QuantumCircuit.global_phase` values.

Global phase uses the existing `phase_tolerance` verdict contract:
`gphase(1e-12)` can return `equivalent` under the default tolerance while
returning `equivalent*` under a stricter threshold. This is not an RR or
distance-tolerance change.

Named quantum-register **partition metadata** is not reconstructed in a
public `PathSum`. Wire ordering is preserved, but complete partition
provenance and arbitrary Qiskit-generated OpenQASM3 are not promised.

## Focused verification evidence

- Native parser, exact scalar/bra behavior and public Rust fail-closed:
  [Actions #41729279162](https://github.com/PhysicsQoo/QuPRS/actions/runs/41729279162),
  Qiskit 1.4.6/2.6.1, each 16 native and 25 FFI tests passed.
- Python source `gphase(pi/2)` propagation defect first reproduced:
  [Actions #41730220598](https://github.com/PhysicsQoo/QuPRS/actions/runs/41730220598).
- Corrected Python numeric scalar and WMC-only behavior:
  [Actions #41731014720](https://github.com/PhysicsQoo/QuPRS/actions/runs/41731014720),
  8/8 controls per version.
- Python/Rust phase, unequal rotations, measurement/reset fail-closed and
  WMC-only comparison: [Actions #41732324256](https://github.com/PhysicsQoo/QuPRS/actions/runs/41732324256),
  21/21 per Qiskit version.

The above results are from a research branch, not the formal integration
commit. The integration PR must certify its **own exact HEAD** and source
against `dev`, and maintain an independent package-install CI. Benchmark
performance comparisons must use CodSpeed; no speedup is claimed.

This is **not** general OpenQASM 3 support. Future acceptance of
source-exact Python phases, complete register partitions, symbolic
parameters, measurements, classical control and custom gate definitions
requires separate semantic specifications and evidence.
