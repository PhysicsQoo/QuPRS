# Strict Rust QASM source-gate handling

The native Rust backend previously treated unrecognized QASM gates as no-ops
during parsing. This is unsafe for quantum equivalence: a circuit containing
a nontrivial gate such as `sx`, `cp`, `measure` or `reset`
could be passed to the verification engine as a different circuit.

## Source-safety contract

The parser now **fails closed** on unsupported QASM gates, non-QASM2
headers, malformed operation signatures, out-of-bounds qubit references,
duplicate multi-qubit operands and incomplete gate statements. A
`PyValueError` is raised by the real Rust extension before the
verification engine begins if the source cannot be represented faithfully.
`Unknown` is reserved for a valid, supported circuit whose equivalence
remains unresolved; unsupported source must not be labeled equivalent,
inequivalent, or merely unknown.

Additional gates already represented by Rust `QuantumOp` and the gate
implementation are mapped explicitly: `p`, `u1`, `u2`, `u3`,
`u` and `swap`. `sx` and `sxdg` are expanded with **exact**
Clifford identities `SX = H S H` and `SXdg = H Sdg H`, retaining
their global phases without approximate rotation synthesis. This also
preserves the previously present register-partition fixture that uses SX.
Identity `id` and barrier are treated as
unitary no-ops with validated operands; **measurement and reset are not
unitary operations** and must be rejected.

The parser remains a **restricted OpenQASM 2.0 implementation**, not a
general QASM2 parser, nor a QASM3 parser. Custom gate declarations, unknown
instructions, conditional classical control, and unsupported gates should
fail clearly rather than be approximated or discarded. The supported
QASM2 parser grammar and physical gate semantics require continued audits
of other source-stage limitations.

## Qiskit 1.x/2.x study implications

The standalone compatibility research found that `qasm2.dumps` emits
`p` and `cp`, which the standard QASM2 `qelib1.inc` parser
cannot round-trip directly. The **native Rust parser is independent**:
this change accepts `p` because its IR already implements the phase
gate, while `cp` remains an explicit unsupported error. Do **not**
automatically transpile every `cp` via floating approximate
optimization; that would require independent source-semantic and phase
evidence, including fixed parameter and gate constraints.

The current Python entrypoint transfers `QuantumCircuit` inputs to
Rust using `qasm2.dumps`; an explicitly assigned circuit
`global_phase` can be lost during this serialization on both Qiskit
1.4.6 and 2.6.1. **This PR does not resolve that scalar global-phase
provenance contract**, nor the previously discovered tiny-angle
precision issues in Python or Rust. The general exact-vs-up-to-global-phase
classification, source-angle representation, and supported input types
must be reviewed independently before widening official Qiskit support.

## Acceptance and compatibility limits

Tests exercise genuine native Rust parser units and real public Python
`backend="rust"` entrypoints in separate pinned Qiskit 1.4.6 and
2.6.1 Linux/Python 3.12 Jobs. The 2.x job deliberately overrides the
current package's `qiskit<2` metadata only within the isolated CI
environment, and records `pip check` rather than claiming officially
resolvable package support.

This is a deliberate **fail-closed behavior change**, not a cosmetic
refactor. Existing applications which depended on unsupported gates being
silently erased will now see a clear exception. The change is kept in a
Draft PR until the affected benchmark/test corpus is audited for legitimate
unitary cases requiring additional explicit Rust gate support.


## Phase normalization correctness (P/U1)

The strict parser makes the already present native P/U1 implementations
reachable through QASM. An independent CP(theta) follow-up discovered
a **factor-of-two phase normalization error** in the old Rust gate
implementation: `Angle` stores theta/pi but `PathSum` polynomial
coefficients are normalized to 2*pi.

The mathematically required P(theta) input-bit coefficient is
`Angle(theta)/2`, not the complete `Angle(theta)`. The conjugated
bra-side gate has the corresponding **negative half** coefficient.
Native P and U1 now share the corrected `apply_p` calculation;
`P(pi/2) = S`, `P(pi) = Z`, `U1(pi/2) = S`, including exact
relative and constant phase. The older native unit test which expected
`P(pi/4)` to contribute a quarter cycle was itself incorrect;
its correct expected coefficient is **1/8**.

The source input phase representation issue remains separate:
`Angle::from_qasm_str` uses `f64` and continued-fraction
approximation, so fixing the P factor does not certify arbitrary tiny
decimal-radian source angles. The original published Python-only
research implementation is not affected by this post-publication
Rust fix.

This was found by a genuine CP(pi) versus CZ regression: the old P
implementation could wrongly treat the five-gate CP(pi) expansion as
Identity. The CP decomposition remains independently staged until both
native phase normalization and the complete comparison pass.

