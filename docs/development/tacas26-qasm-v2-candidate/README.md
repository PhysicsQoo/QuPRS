# MQTBench / TACAS26 QASM v2 — research candidate (not released)

This is a **new, separately versioned reference corpus**, not a rewrite
of the original TACAS26 artifact or its published results.

## Source identity and policy

The machine-readable [manifest](manifest.json) pins nine representative
TACAS26 MQTBench source pairs:

- Canonical unitary source: original archived QASM with final measurements
  removed, hash-checked and committed under
  `docs/development/tacas26-level0-quprs-cross/inputs/41562334781/`.
- Target: independently produced Qiskit **2.6.1** OpenQASM 2 with
  `basis_gates=['h','ry','rz','cx']`, `optimization_level=0`,
  `seed_transpiler=42`, `approximation_degree=1.0`, and a checked
  SHA256 in `docs/development/tacas26-qiskit-version-fidelity/`.
- Historical original and transpiled TACAS QASM are **not changed**.
  Qiskit 1.4.2 opt0 is separately retained for cross-version science.
  Aggressive opt3 transpilation remains a separate stress-test corpus,
  not silently relabeled strictly equivalent.

## Acceptance gates before promoting this as a formal benchmark

1. Expand the identity manifest from nine representatives to all relevant
   paper MQTBench cases, preserving historical input/output SHA256 and
   transpile settings for each case. A case with a non-unitary or
   unsupported QASM instruction must be explicitly excluded.
2. Validate QASM pair identity and numerical semantics independently.
   For <=8 qubits, check the full operator; for larger circuits, two sampled
   states are **not** a full projective-distance certificate.
3. Run QuPRS v0.14.0 **Python and Rust**, both Hybrid and WMC-only where
   feasible, with pinned GPMC, especially at strict
   `approximate_distance_tolerance=1e-8`. Preserve actual printed WMC
   counts, RR provenance and errors; Solver timeout means censored.
4. Preserve explicit NEQ controls (e.g. non-global Rz(0.05)) and require
   correct rejection. EQ agreement alone is not a sufficient acceptance gate.
5. Ganak 2.8.0 is **optional** and has limited output precision; its
   failure to resolve 1e-8 may be a solver resolution limitation, not
   source-circuit non-equivalence. Do not relax global distance for Ganak.
6. If an experimental source-corpus update changes a benchmark identity,
   create an explicit new QASM version. Never alter a historical QASM hash,
   published TACAS artifact or old benchmark in place.

## Status

**RESEARCH_CANDIDATE_NOT_CERTIFIED.** This manifest is a reference to
existing byte-identical QASM files; it does not make performance claims
or add a formal runtime benchmark. All timing/performance comparisons
must use CodSpeed, not ordinary GitHub Actions wall clock.

Evidence experiments:

- [Level0 original versus Python/Rust QuPRS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41562334781)
- [Strict 1e-8 GPMC/Ganak precision study](https://github.com/PhysicsQoo/QuPRS/actions/runs/41565429000)

Only the experimental branch may be updated by this research. Keep
`main`, `dev`, formal PR #131 and published TACAS sources unchanged
until review and acceptance.
