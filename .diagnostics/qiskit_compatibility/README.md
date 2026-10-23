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
