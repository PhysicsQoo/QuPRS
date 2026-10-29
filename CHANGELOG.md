# Changelog

Significant user-facing changes to QuPRS are summarized here. See [GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases) for published packages and release dates.

## Unreleased

### Fixed
- Preserve nonzero phase coefficients at Python gate-to-PathSum construction time, independently of the tolerance used by Elim/HH/omega local reduction matching. This prevents large collections of individually tiny Rz rotations from disappearing before RR, Hybrid or WMC-only can account for their accumulated effect.
- Invalidate cached tolerance-dependent Python reductions when `config.set_tolerance()` changes its value; reject non-finite, Boolean and nonpositive settings.

### API and compatibility (v0.14.0 work in progress)
- Remove the public `wmc_policy` argument and result field; passing the old keyword now raises `TypeError`. The `wmc_numerical_verdict` diagnostic remains observable when WMC is invoked.
- Add native Rust `VerificationOptions` and `check_equivalence_with_options()`, preserving existing Rust signatures. Rust crate and PyO3 WMC magnitude/phase defaults now match the Python public defaults (`1e-8` each); direct Rust callers relying on the old `1e-6` defaults should pass them explicitly.
- Rust FFI rejects `safe_mode=True` instead of silently ignoring it; Python backend safe mode is unchanged.
- Add opt-in `approximate_distance_tolerance` to Python, PyO3 and typed Rust options. Stable projective-distance conversion with a fixed empirical 3e-9 guard returns `unknown` near unresolved numerical boundaries; this is not a certified solver error bound.
- In approximate mode RR strict source inequivalence need not imply distance beyond epsilon: RR-only can be inconclusive and Hybrid may fall through to WMC; symbolic positive RR fast paths stay unchanged.
- `config.set_tolerance()` remains a process-global Python RR setting, not a Rust per-call knob; external weighted Solver evidence is not a universal exact-equivalence proof.

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
