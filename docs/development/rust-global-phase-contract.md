# Explicit QuantumCircuit global-phase provenance across QASM2 Rust transport

The current Python→Rust bridge serializes Qiskit `QuantumCircuit`
objects using `qasm2.dumps`. In isolated Qiskit 1.4.6 and 2.6.1
comparisons, an explicitly set `QuantumCircuit.global_phase` was not
preserved by QASM2/QASM3 export/import: a circuit with an explicit
`global_phase=0.05` round-tripped with zero stored phase, changing the
full matrix even though equivalence *up to a global phase* was preserved.

The public QuPRS result distinguishes:
- `equivalent`: exact unitary equality;
- `equivalent*`: equal up to global phase;
- `not_equivalent` or `unknown`: other outcomes.

Dropping a relative input global phase can turn a scientifically correct
`equivalent*` result into a **false exact** `equivalent`, or a true
exact equality (when circuit gate phases cancel an explicit source
phase) into a misleading `equivalent*`.

## Conservative first-stage source contract

Before invoking the Rust backend, the Python interface inspects the
explicit `QuantumCircuit.global_phase` attached to each Qiskit input.
For raw QASM2 strings, the transport's independently expressible
global-phase scalar is taken as zero (QASM2 has no standalone
`gphase` statement). The current contract:

- If source scalar phases are equal as **finite bound numbers**, they
  cancel from the compared operators exactly, so existing unitary
  verification can proceed unchanged.
- If source scalar phases differ, fail closed with an explicit
  `ValueError` explaining that the QASM2 bridge cannot preserve
  the relative global phase. Do **not** issue a mathematically
  unsubstantiated exact-equivalence, up-to-global-phase or inequivalence
  verdict.
- If an input's phase is unbound symbolic or nonfinite, fail closed.
- The validation happens before the native Rust checker or any
  WMC solver is launched. No automatic transpiler rewrite or
  tolerance adjustment is used.

This is **not full global-phase metadata transmission** to the Rust
engine. In particular, different phases that physically cancel a
nontrivial gate-derived phase will conservatively raise rather than
return a precise exact-equality status. That is preferable to silently
dropping an observable distinction in the public classification.

## Future complete contract

A complete solution should pass a separately encoded and validated
global-phase coefficient into Rust's verification miter (or a
source-faithful IR), with phase algebra capable of representing
parameterized and nontrivial rational-pi angles. Both exact-unitary
equality and equality up to global phase must then be independently
tested against source-level mathematical oracles. It must not
treat arbitrary float or continued-fraction approximations as
rigorous source-angle proofs; `RZ(1e-12)` remains a separate numerical
precision issue.

This research Draft PR limits the first-stage guard to
`backend="rust"`, leaving the historical pure-Python method,
reduction-first Hybrid strategy, WMC thresholds and all solver
adapters unchanged. Python backend explicit-source-phase parity is
a separate scientific acceptance requirement before a broad exact
phase classification claim can be made. Qiskit 2.x package metadata
remains `qiskit<2` until independent resolver/platform gates pass.
