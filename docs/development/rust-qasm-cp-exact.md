# Exact controlled-phase (CP) lowering for the restricted Rust QASM2 parser

This research-only stacked change is based on the strict native input parser
in the preceding Draft PR. It supplies the `cp(theta)` two-qubit gate that
Qiskit's native QASM2 exporter emits, without silently dropping it or invoking
a floating-point transpiler.

The phase action of CP(theta) is the diagonal unitary
`diag(1, 1, 1, exp(i theta))`. The following sequence is **exact as a
matrix identity** (operations in execution order):

```qasm
p(theta / 2) control;
cx control,target;
p(-theta / 2) target;
cx control,target;
p(theta / 2) target;
```

On the four computational-basis states, the accumulated phases are:
`|00>:0`, `|01>: -theta/2 + theta/2 = 0`,
`|10>: theta/2 - theta/2 = 0`,
`|11>: theta/2 + theta/2 = theta`. No additional global scalar phase
is introduced.

In Rust, the intermediate `Angle` supports rational division by two
and subtraction, so the above decomposition is exact **relative to the
parsed Angle value**. This is not the same as certifying that
`Angle::from_qasm_str` preserves every exact non-pi decimal source
angle: that parser currently uses `f64` followed by rational
approximation. Extremely small angles remain a separate correctness
issue, and are **not** solved by this PR.

The independent test corpus includes CP(pi) versus CZ, CP(pi/2),
small positive/negative CP, an exact Qiskit matrix check, valid native
parser five-gate expansion, and malformed/duplicate-operand/error
controls. The real compiled Rust FFI must count the full five operations,
never silently turn CP into identity, and preserve a source
CP(pi)→CZ equivalence case. The Qiskit matrix checks use numerical
matrices only as *cross-validation* of the algebraic identity, not
as a substitute for the source-angle precision proof.

## Outstanding migration contract

- Qiskit 1.x/2.x `QuantumCircuit.global_phase` can be dropped by
  QASM2/QASM3 export, and the exact-versus-up-to-global-phase distinction
  must be preserved through the Python→Rust API. CP lowering by itself
  does not address this.
- Direct QASM3, custom QASM declarations, classical control and other
  unsupported gates must continue to fail closed rather than bypass
  the source parser.
- The broader native cross-platform matrix and default production
  Qiskit requirement `qiskit<2` remain unchanged.

The opt-in workflow records exact source, native build and both Qiskit
1.4.6/2.6.1 tests, plus raw output and SHA256 manifests. This PR
must stay Draft until its source-pinned CI and parent parser-safety
change are accepted.
