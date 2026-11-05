# Controlled-phase lowering in the native Rust QASM2 parser

The restricted native parser supports `cp(theta)` using the exact
**algebraic decomposition relative to the parsed `Angle` value**.
The target two-qubit unitary is
`diag(1, 1, 1, exp(i theta))`.

In circuit execution order, the equivalent sequence is:

```qasm
p(theta / 2) control;
cx control,target;
p(-theta / 2) target;
cx control,target;
p(theta / 2) target;
```

The accumulated computational-basis phases are 0 for `|00>`,
`|01>` and `|10>`, and `theta` for `|11>`. No additional global
scalar is introduced by this decomposition.

The parser must not silently drop unsupported gates, collapse CP to
identity, or accept malformed/duplicate operands. Native gate-count
checks verify that the lowering produces all five operations.
The tests cover CP(pi) versus CZ, CP(pi/2), positive/negative
literal angles, and Qiskit dense-matrix cross-checks; the dense-matrix
checks are numerical controls, **not proofs of arbitrary source-angle
representation fidelity**.

Input decimal-angle provenance, explicit Qiskit-object global phase
and unsupported QASM constructs are **separate** contracts. Do not
infer that a correct CP matrix identity certifies all decimal-radian
parser conversions. See [exact input angles](exact-angle-representation.md),
[QASM2 source safety](rust-qasm-source-safety.md),
[global-phase transport](rust-global-phase-contract.md), and
[bounded QASM3 support](rust-qasm3-supported-subset.md).

Implementation and regression evidence are maintained with
`rust/pathsum/src/qasm.rs` and `test/test_rust_qasm_cp_exact.py`.
