# Changelog

## v0.14.0 — Per-call reduction tolerance and projective-distance WMC (release candidate)

### Numerical verification

- **Breaking:** Default weighted-model-counting numerical acceptance now uses
  `approximate_distance_tolerance=1e-8` (projective Hilbert-Schmidt
  distance), for Python, PyO3 and native Rust. An explicit `None` also
  selects the same default, not another WMC classifier.
- Remove `wmc_magnitude_tolerance` from the public Python/PyO3 API and
  typed native Rust `VerificationOptions`; callers must use a physical
  projective-distance threshold. The obsolete
  `check_equivalence_with_tolerances` native Rust entry point and the
  magnitude-classifier branch are removed. This is an API-breaking change.
- Keep `phase_tolerance` (`wmc_phase_tolerance` remains an alias) independent
  of the local `rr_tolerance` and WMC projective-distance threshold.
  Per-verification Python reduction contexts and caches are isolated.
- Preserve numerical count provenance via `wmc_numerical_verdict`,
  `wmc_printed_verdict`, `wmc_precision_reason` and
  `wmc_solver_invoked`. A finite Solver count is **not** an
  unconditional equivalence certificate. Finite Solver counts use the
  common projective-distance classifier; printed uncertainty and
  nonphysical magnitude overshoot remain separate diagnostics.
- In the native Rust GPMC path, preserve source `PhaseCoeff` until
  high-resolution complex weights are evaluated using tolerance-adaptive
  MPFR (96-bit default for small residuals at projective tolerance `1e-8`,
  with additional guard bits and phase-term scaling), and serialize a
  corresponding number of decimal digits without an intermediate `f64`
  conversion. A singleton phase skips the expensive full-PhaseCoeff hash
  cache; repeated phases still reuse computed weights. No changes are made to GPMC or Ganak source,
  no implicit Solver fallback and no second GPMC solve.
- Remove the mutable Python `config.TOLERANCE`, `set_tolerance()`
  and `get_tolerance()` APIs, the `wmc_policy` selector and the
  redundant `decision_basis` result field.
- Rust accepts a per-call RR tolerance through a conservative aggregate
  upper bound for fully reduced diagonal residuals; exact HH/omega rules
  and source angles remain intact. Hybrid now executes the identical
  tolerance-aware RR stage as RR-only (no terminal proof probe) and
  directly converts its final residual PathSum into CNF/WMC when RR is
  inconclusive. No strict-RR replay or alternate residual is introduced.
  Approximation provenance is informational, and only one Solver
  invocation is permitted on WMC fallback.

### Compatibility and source semantics

- Support Qiskit **1.x and 2.x** with `qiskit>=1.0.0,<3.0` metadata, on
  the existing Python **3.11–3.13** and Linux x86_64/ARM64 and
  macOS 15+ Intel/Apple Silicon targets. The `pqc_generator`
  compatibility layer handles Qiskit constructor API differences.
  Qiskit 3.x, Python 3.14/3.14t and macOS 14 prebuilt wheels
  are not claimed as supported by this release.
- Add native Rust support for a **bounded OpenQASM 3.0 unitary subset**
  (including `stdgates.inc`, qubit declarations, supported gate angles
  and standalone `gphase(theta)`) without converting through QASM2.
  Measurement, reset, classical control, custom gate definitions and
  general OpenQASM 3 are explicitly rejected rather than ignored.
- Preserve Qiskit `QuantumCircuit.global_phase` through the Python
  source-miter path; the Python-to-Rust QASM2 bridge continues to reject
  unequal explicit phases it cannot faithfully transport. The
  Qiskit-object phase representation is floating-point, unlike native
  Rust source-literal angles.

### Testing, CI and packaging

- Validate independent near-boundary source oracles, final Hybrid RR
  residuals, Python/Rust × Ganak/GPMC conformance and a 20-circuit,
  two-backend register-partition Operator oracle regression matrix.
  An RR-only `unknown` is permitted; a Hybrid/WMC negative outcome
  must explicitly be `not_equivalent`, not Timeout or unknown.
- Consolidate CodSpeed into the five-shard design with the retained
  32 legacy Simulation identities and additional Qiskit 2.6.1-generated QASM cases,
  native CPU measurements, and 10 paired Solver-inclusive WallTime
  cases. Performance is observational, **not a fixed-percentage CI
  release gate**. Historical benchmark identities are preserved.
- Make source-aware CI routing avoid unrelated repeat builds and
  expensive measurements. Ordinary PRs are not an occasion to run
  every Qiskit 1.x/2.x installer matrix or the entire release
  wheel/sdist admission. Required `dev → main` Release-Ready
  continues to require complete cross-platform source and installed
  archive matrices, version checks and fail-closed policy tests.
- Report `INCONCLUSIVE_RESOURCE` or planned benchmark SKIP as
  **unverified coverage**, neither PASS nor a demonstrated wrong
  scientific verdict. Definite incorrect results, solver errors,
  missing case identities and invalid pinned source evidence still
  fail. An optional complete performance cohort must be requested
  separately.
- Correct Docker wheel builder to install `patchelf`; macOS repaired
  wheel runs with bundled GMP/MPFR dependencies.
- **Migration note:** removed `wmc_magnitude_tolerance`,
  `wmc_policy`, mutable `config.TOLERANCE` and deprecated Rust
  `check_equivalence_with_tolerances` entry points must be replaced
  by the documented per-call options. The old magnitude-defect and
  new distance thresholds are **not numerically interchangeable**;
  see [v0.14.0 migration](docs/development/v0140-migration.md).
  Printed Solver precision can yield a determinate numerical point
  estimate with a separate `unknown` printed-interval diagnostic.
  Do not call this a source-exact proof or claim complete Ganak
  internal-arithmetic certification.

**Release status:** this 0.14.0 section describes the integrated
release candidate, not a published package. Publication is conditional
on final `dev → main` source, wheel/sdist and tag-time acceptance.

Significant user-facing changes to QuPRS are summarized here. See
[GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases)
for published packages and release dates.

## 0.13.4 (2026-10-27)

### Scientific semantics and correctness
- Preserve supported OpenQASM 2 literal decimal-radian angles separately from symbolic multiples of pi in Rust PathSum/phase operations; prevent lossy rational-pi substitution of exact source values. Unsupported input remains fail-closed. Distinguish source-literal semantics from floating-point Qiskit parameters.
- Strengthen Rust gate semantics and QASM safety, including controlled phase, U2, SX, global-phase transport and unsupported-gate validation. Source-exact comparisons may legitimately differ from prior numerically approximated verdicts; approximate transpilation equivalence is a separate predicate, not strict equality.
- Add independent small matrix oracles, Graphstate16 source/provenance controls, QPE-focused tests, paper-corpus integrity checks and cross-backend solver/result regressions.

### WMC and solver reliability
- Expose independent, validated per-call WMC magnitude/phase numerical tolerances (public Python defaults 1e-8). Symbolic reduction tolerance remains independent. A smaller threshold does **not** certify exact mathematical equivalence.
- Add opt-in `wmc_policy="conservative"`: uncertified external floating WMC verdicts return `unknown` while retaining a numerical diagnostic; default `legacy` mode remains a numerical heuristic for compatibility.
- Separate Python/Rust Ganak and GPMC solver adapters, supervised error/result contracts, weighted-CNF representation, incompatible output and unsupported-solver rejection. No implicit cross-solver fallback.

### Performance and engineering
- Reduce redundant exact-angle rational arithmetic in the Rust hot path and reuse Python reduction coefficient work; retain the original Reduction-first Hybrid behavior and explicit Solver selection.
- Migrate CodSpeed Simulation to v5, verify the 5-shard/32-benchmark corpus, improve dev/native/benchmark gating, and add reproducible opt-in same-job walltime/RSS and cost-attribution diagnostics. CodSpeed simulated cycles and sampled process-tree RSS are **not** native solver-PID runtime or exact memory peaks.
- Improve source-first compatibility checks and scientific benchmark outcome reporting without adding a hosted-runner percentage regression hard gate.

### Compatibility and known limits
- Retain the v0.13.3 declared installation targets (Python 3.11–3.13, Qiskit 1.x, Linux x86_64/ARM64 and macOS 15+ x86_64/ARM64 wheel targets). Qiskit 2.x, Python 3.14, Ubuntu 26.04 and macOS 14 wheel support are not newly guaranteed.
- Legacy finite-tolerance WMC may accept near-identity but strictly inequivalent circuits. For proof-sensitive numerical WMC paths, request `wmc_policy="conservative"` and treat `unknown` as inconclusive. No general certified error enclosure for arbitrary external solver outputs is claimed.
- Some historical transpiled-QASM benchmark pairs, including Graphstate16, are extremely close in numerical projective distance yet not strictly equal as source-decimal operators. Strict and approximate outcomes must not be conflated.

**Release status:** v0.13.4 was published on 2026-10-27; the historical RC preparation notes above refer to the prepublication source tree, not to v0.14.0 acceptance.

## 0.13.3

### Fixed
- Fix a Rust `wmc_only` false-equivalence result when the trace CNF has no additional path variables but still contains constraints. Previously, a zero path-variable count could skip a necessary solver call and incorrectly mark inequivalent circuits (such as Identity versus X) as equivalent.

### Validation and release infrastructure
- Add Rust/Python regression tests for zero-path-variable WMC cases (Identity versus Identity, X and Z) with both Ganak and GPMC, including Qiskit operator oracles.
- Add a fail-closed `dev → main` Release-Ready gate. It requires the complete source correctness matrix, actual installed Wheel and sdist smoke tests, workflow parity and policy-negative checks before reporting success.
- Build and install candidate Wheels across Linux x86_64/ARM64 and macOS Intel/Apple Silicon for Python 3.11–3.13, plus clean sdist installs on Linux and macOS. Validate installed native extensions, Python metadata, solver selection and equivalence decisions.
- Extend Benchmark and Docker PR checks to target `dev` as well as `main`.

### Compatibility
- The prebuilt macOS Wheels remain targeted at macOS 15+; macOS 14 source-build evidence is documented separately. This is a clarification of existing packaging support, not a new minimum-version change in v0.13.3.

### Performance evidence
- Same-host, paired ABBA measurements of the WMC correctness fix across eight selected QFT16, Grover4 and QAOA7 configurations (Rust/Python and Ganak/GPMC as applicable) did not show a significant unrelated regression. These samples do not establish a universal performance guarantee.

## 0.13.2

### Changed
- Upgrade the bundled Ganak solver from 2.5.2 to the pinned upstream 2.8.0 distribution, with verified archive and executable SHA256, architecture, and embedded-version diagnostics for supported platforms.
- Use Ganak complex floating-point weighted counting (`--mode=6`) while keeping GPMC independently configured with `-mode=1`.
- Parse complex and fractional weighted counts more defensively in Python and Rust; reject non-finite or malformed results and unsuccessful solver exits rather than treating them as valid counts.
- Defer redundant Python-side Ganak verification for Rust reduction-only and hybrid paths that do not invoke WMC. Rust still checks Ganak before actual WMC execution; Python WMC retains its validation.
- Add solver-format, numerical-boundary, provenance, and lazy-validation regression coverage. Document floating-point counting limitations in the README.
- Preserve binary64 weights across Rust-to-Ganak/GPMC DIMACS input via 17-significant-digit scientific notation, eliminating GPMC's nine-decimal input truncation; evaluate Python symbolic weights at explicit 113-bit precision.
- Align Python WMC decision thresholds with Rust's unrounded normalized-count and phase policies (1e-6 each), handle cancellation/zero/large counts without squared-magnitude overflow, and distinguish solver numerics from symbolic reduction tolerance.

### Compatibility and numerical notes
- No solver fallback between Ganak and GPMC is introduced. GPMC DIMACS decimal formatting is upgraded without changing its independent solver selection or WMC mode.
- Ganak mode 6 emits rounded complex counts; neither solver yields an exact-arithmetic equivalence certificate. Python WMC now shares Rust's 1e-6 normalized magnitude/phase thresholds, replacing Python's prior rounded-log decision rule. Near-boundary results require independent validation.
- Pre-release CI verified Python 3.11–3.13 on Linux x86_64/ARM64 and macOS Intel/Apple Silicon, Docker AMD64/ARM64, and the existing benchmark comparison gate. Consult the corresponding commit's GitHub Actions runs for exact evidence and runner details.

## Earlier releases

- [v0.13.1](https://github.com/PhysicsQoo/QuPRS/releases/tag/v0.13.1) and [older releases](https://github.com/PhysicsQoo/QuPRS/releases).
