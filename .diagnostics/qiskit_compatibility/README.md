# Qiskit 1.4.6 → 2.6.1 compatibility investigation

This is an **isolated, opt-in** comparison against the current QuPRS
source. No dependencies, default transpiler behavior, Python/Rust gate
implementations, weighted model counting, reduction rules or existing CI
requirements are changed.

## Versions and controlled environment

Matrix: Python 3.12 / Qiskit 1.4.6 or 2.6.1 / Ubuntu 24.04, with pinned
`qiskit-qasm3-import==0.6.0`, random seed 42, and the same
`basis_gates=['rz','sx','x','cx']`. Different jobs are different hosts,
therefore the observed compilation walltimes are **not fixed-host
performance evidence**.

QuPRS project metadata currently requires `qiskit<2.0,>=1.0.0`.
For the Qiskit 2.6.1 trial, its standard package is built once, then
Qiskit is replaced **in the isolated environment only** with an explicit
`pip --no-deps` override. The resulting intentionally unsatisfied
QuPRS metadata is captured using `pip check`. Passing import and
functional tests in this environment would **not** yet establish
installable Qiskit 2.x support. A separate release metadata, full dependency
resolution and multiplatform gate is mandatory.

## Core cases and acceptance

Ten input circuits: Identity, a strict nonzero RZ at 1e-12 and 0.001,
P+S+T, H/H, Bell, register partitions, small QFT and graph state, and an
explicit nonzero global-phase circuit. Each case runs the unmodified
Qiskit transpiler at `optimization_level=0,1,2,3`,
`approximation_degree=1.0` and fixed seed. Capture pre-/post- gate count,
depth, global phase, compilation wall time and floating operator diagnostics.
Compare OpenQASM2/OpenQASM3 roundtrips independently, including retained
quantum register partitions and phase. Probe bound symbolic parameters
and the current QuPRS **Python** reduction-only H-H control, keeping it
separate from external GPMC/Ganak numeric classification.

An independent exact rational-radian cosine upper bound proves
`I` and nonzero tiny `RZ(1e-12)` are **mathematically non-equivalent
up to global phase**, but floating matrix norm/fidelity cannot certify
preservation of tiny angles. Transpilation and QuPRS's own
`div_pi` plus coefficient tolerance are separate pipeline stages.
Record numerical losses rather than silently treating them as evidence
of quantum-circuit equivalence.

The primary CI gate tests installation/import, a real Reduction-only
control, correct broad-circuit floating operator semantics and the absence
of transpiler exceptions. Unsupported or changed QASM features are
recorded by exact source/version. This is a first-stage exploratory gate,
not an endorsement of automatic approximate transpilation for rigorous
equivalence or certification of all Qiskit 2.x functionality.

## Follow-up before changing official dependency metadata

1. Review any specific API or QASM regression exposed by the two
   source-pinned observations.
2. Enforce relevant exact global phase, register layout and tiny-angle
   conditions using independent mathematics, not only `np.allclose`.
3. Compare representative QuPRS Python/Rust Hybrid, Reduction and WMC
   solver cases using independently selected solvers, on both Qiskit
   versions and supported Python/OS architectures.
4. Run a true resolver/install matrix and determine whether to support
   Qiskit 1.x + 2.x simultaneously or set an intentional new minimum.
5. Add release documentation and a regression gate **before** changing
   `qiskit<2.0` in production metadata.


## First exact-head observations (and tightened QASM2 gate)

The initial `1.4.6`/`2.6.1` source-pinned runs successfully
imported QuPRS and transpiled all ten circuits at all four levels.
Both versions emit raw `p(...)` and `cp(...)` from `qasm2.dumps`
which cannot be read back by the basic `qasm2.loads` with standard
`qelib1.inc`. Raw QASM2 mismatch is **recorded as a failure of the raw
serialization round-trip**, not as a new Qiskit 2.x regression.

The updated study additionally verifies an explicit **`u3,cx` legacy
basis** transpilation bridge against the source operator. This is an
observable transformation and cannot be used to claim the unmodified
QASM2 exporter can round-trip arbitrary Qiskit gates.

Both QASM2 and QASM3 export/import of a circuit with an explicit
nonzero `QuantumCircuit.global_phase` lose the exact scalar phase in
these runs, even though matrix comparison *up to global phase* can
still look equivalent. The audit preserves exact-unitary matrix
Frobenius error and the original/imported phase separately. Such QASM
paths require a source-phase provenance policy in QuPRS, especially
for distinguishing exact equality from equality up to global phase.

Both versions also drop `RZ(1e-12)` at transpiler levels 2 and 3,
while preserving it at levels 0 and 1. This illustrates that fixed
`approximation_degree=1.0` means no deliberate approximation beyond
floating precision, **not** an exact real-number semantic guarantee.

The legacy `u3/cx` path can preserve the operation **up to global
phase** while losing a constant Euler-decomposition phase on QASM2
serialization. For this reason the audit saves both raw exact-unitary
Frobenius deviation and phase-aligned Frobenius deviation; only the
latter is accepted as a *floating non-phase* gate-synthesis check.
A passing phase-aligned check does **not** claim the original exact
unitary scalar survived, nor is it a rigorous proof of equivalence.
