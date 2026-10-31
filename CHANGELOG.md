# Changelog

## v0.14.0 — Per-call reduction tolerance and projective-distance WMC

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
- Keep `wmc_phase_tolerance` / `phase_tolerance` independent for
  global-phase labels. `rr_tolerance` independently governs Python
  reduction matching, with per-verification contexts and cache isolation.
- Preserve numerical count provenance via `wmc_numerical_verdict`,
  `wmc_printed_verdict`, `wmc_precision_reason` and
  `wmc_solver_invoked`. A finite Solver count is **not** an
  unconditional equivalence certificate. Finite Solver counts use the
  common projective-distance classifier; printed uncertainty and
  nonphysical magnitude overshoot remain separate diagnostics.
- In the native Rust GPMC path, preserve source `PhaseCoeff` until
  high-resolution complex weights are evaluated using 192-bit MPFR,
  then serialize 48 significant decimal digits without an intermediate
  `f64` conversion. No changes are made to GPMC or Ganak source,
  no implicit Solver fallback and no second GPMC solve.
- Remove the mutable Python `config.TOLERANCE`, `set_tolerance()`
  and `get_tolerance()` APIs, the `wmc_policy` selector and the
  redundant `decision_basis` result field.
- Rust accepts a per-call RR tolerance through a conservative aggregate
  upper bound for fully reduced diagonal residuals; exact HH/omega rules
  and source angles remain intact. Hybrid stays RR-first and uses one
  WMC Solver invocation only when RR is inconclusive.

### Testing and packaging

- Validate exact source-angle transport, independent near-boundary rotation
  oracles and public Python/Rust × Ganak/GPMC conformance.
- Retain CodSpeed v5 Simulation for in-process CPU work, WallTime for
  external Solver latency, and 5-shard performance coverage.
- Correct Docker wheel builder to install `patchelf`; macOS repaired
  wheel runs with bundled GMP/MPFR dependencies.
- **Release note:** the new default is much stricter than the prior
  magnitude-based numerical acceptance. Existing pipelines may receive
  determinate yet explicitly uncertified numerical verdicts when
  printed precision is inadequate; diagnostics must remain visible.
  Do not interpret a numerical result as source-exact proof.

Significant user-facing changes to QuPRS are summarized here. See
[GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases)
for published packages and release dates.

## 0.13.4 (unreleased)

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

**Release status:** RC preparation only. This section does not indicate that the final cross-platform source, installed wheel/sdist, Docker or publish gates have run on the release candidate.

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
