# Weighted-CNF boundary: experimental correctness and cost audit

Source base: PR #131 commit `f6ab474`. This is **experimental evidence only**,
not a change to the QuPRS verifier, solver executables, or release defaults.

## Two independent questions

1. Does each encoder preserve the weighted sum of *all* satisfying models,
   including paths not referenced by the output Boolean functions or phase?
2. Does the source-to-decimal complex-weight conversion retain enough precision
   to classify a projective distance of `1e-8`? For normalized overlap near
   one, the relevant magnitude defect is approximately `5e-17`.

## Source-level exact-enumeration control (not native Rust/Python execution)

An independent ten-case model of the source encoders used exact Gaussian-
integer weights for quarter-cycle phases and enumerated every satisfying
assignment. It covered identity, unused path variables, scalar phase,
phase-controlled paths, XOR, AND, constant output, and mixed Boolean/phase
cases. Results:

| Encoder model | Matched direct weighted enumeration |
|---|---:|
| Python pre-registering inputs and paths | 10/10 |
| Rust lazy registering only used variables | 8/10 |
| Rust with all source path variables reserved | 10/10 |

The two differences arose with *unused* path variables (one- and two-variable
cases). This does not demonstrate reachability from a real QASM verifier:
reductions may delete these variables before CNF creation. The experimental
Rust unit test `experiment_unused_path_variable_cnf_accounting` probes the
native encoder with an explicitly unused path variable. The proposed
reservation is limited to the test; there is no production encoder change.

## Weight-boundary arithmetic and cost (standalone Python proxy)

Fifteen representative `Rz`/phase angles were evaluated from their source
decimal text using high-precision arithmetic as a reference. The binary64
path computed trig functions in f64 and serialized with `{:.16e}`;
the higher-precision proxy computed with approximately 34 decimal digits.

| Measurement | Source-level proxy result |
|---|---:|
| Maximum complex absolute error, f64 serialized | 1.160e-16 |
| Maximum complex absolute error, ~34-digit serialized | 5.556e-35 |
| Maximum serialized f64 `|w|^2 - 1` | 1.067e-16 |
| Number of sampled f64 weights with positive unit drift | 8/15 |
| Approx. median time per angle, f64 proxy | 12.1 microseconds |
| Approx. median time per angle, 35-decimal-digit proxy | 22.7 microseconds |
| Approx. median time per angle, 90-decimal-digit proxy | 40.5 microseconds |

Timing is measured in a Python proxy, **not** in native Rust or production
GPMC. It cannot be used to predict end-to-end QuPRS walltime or CodSpeed
regressions. The source error is of the same order as the squared-magnitude
test boundary at `D_proj=1e-8`; it explains a plausible mechanism for
nonphysical WMC magnitude overshoot, but not its measured magnitude on large
Graphstate/QFT CNFs.

## Native capture correction

`src/QuPRS/interface/load_qiskit.py` resolves the packaged solver via
`from QuPRS.utils import WMC` under the environment lock and *overwrites*
`QUPRS_GPMC_PATH` just before calling Rust. Therefore a test that only
monkeypatches that environment variable cannot intercept a public Rust call.
The experimental test patches the **Python resource resolver** instead,
letting the Rust call execute the same GPMC once while copying the actual
CNF. No production source, solver binary, or extra WMC solve is involved.

## Narrow high-precision design candidate (not implemented)

Preserve the existing exact source rational angles and Path-sum phase terms
until `encode_phase_polynomial`. Only when the user selects GPMC and an
explicit high-resolution distance threshold, evaluate `2*pi*cycle +
2*source_radians` and its sine/cosine at 113--128 bits, then serialize
decimal real/imag strings directly. Avoid converting them to
`Complex<f64>` before the solver sees them.

Possible representation: a solver-neutral `WeightValue` enum with a legacy
`Complex<f64>` variant and an opt-in decimal-string variant. Measure the
cost of MPFR/Rug dependency, wheel/CI portability, conversion, CNF bytes,
walltime and RSS **before** selecting the implementation. Do not impose
high-precision trig on ordinary RR or the default legacy WMC path.

## Acceptance limits

Required for any production candidate: exact small weighted-CNF oracle
parity (including free-path cases), no false `equivalent` for known
out-of-threshold `Rz` rotations, Graphstate16/QFT16 positive checks,
Python/Rust verdict parity, fixed-runner benchmark comparison across
QFT16/QAOA7/Grover4/VQE4/GHZ32, and one WMC solve per verification.
Solver timeout/error remain separate from numerical `unknown`.
