# Changelog

## Unreleased — v0.16.0 candidate: Python 3.14 and native Rust modernization

This is an in-development release candidate. The changelog entry and source
version do not establish a published Python package, Rust crate or GitHub
Release.

### Supported Python versions and packaging

- Qualify standard CPython 3.11–3.14 across Linux x86-64/ARM64 and
  macOS 15+ Intel/Apple Silicon, with full source and installed-wheel smoke
  coverage. Python 3.14 uses Qiskit 2.x; Qiskit 1.x is not claimed for
  Python 3.14. Free-threaded Python 3.14t is not supported.
- Modernize the native extension to PyO3 0.30.1 and the CPython 3.11 stable
  ABI (`cp311-abi3`) while retaining the public
  `QuPRS._pathsum_rust` module.
- Move the Rust core source directory from `rust/pathsum` to
  `rust/quprs`, preserving the published `quprs` crate name and Rust
  API, existing Python entry points and native verification methods.
- Maintain independently resolved Rust workspace and standalone crate
  lockfiles, reproducible packaging and native GMP/MPFR build qualification.

### Compatibility and scientific correctness

- Preserve the TACAS-oriented Path-sum reduction and residual WMC methods,
  independent GPMC/Ganak adapters, source-angle provenance, existing
  per-call numerical tolerance contracts and distinct
  Equivalent/Not Equivalent/Unknown/Error outcomes.
- Do not introduce a third production WMC solver, change the default solver,
  or claim certified performance gains from hosted-runner measurements.
- Continue publishing supported-platform wheels, an sdist and the Rust
  crate through verified independent registry workflows.

## v0.15.1 — Solver distribution and release reliability

This entry describes the v0.15.1 maintenance-release source and distribution
contents. Confirm availability from the official
[GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases),
[PyPI](https://pypi.org/project/QuPRS/), and
[crates.io](https://crates.io/crates/quprs/versions). A changelog entry in a
source checkout is not proof that a distribution has been published.

### Solver distribution and installation

- Remove the GPMC Git submodule and bundled third-party source checkout.
  QuPRS source checkouts now provision the pinned **GPMC v1.0.2** CLI release
  using a source-identity, platform, archive and executable digest check.
  Provisioning uses an authenticated release artifact or a verified local cache;
  the installed Rust crate still relies on explicitly available external solvers.
- Pin GPMC v1.0.2 across Linux, macOS and Windows x86-64/ARM64 artifacts to
  one upstream source commit. An explicit `QUPRS_GPMC_PATH` override remains
  authoritative, with missing overrides failing rather than silently falling back.
- Preserve the existing `manylinux_2_28` wheel portability contract by
  building GPMC from the *same pinned upstream source* against the wheel's
  native toolchain. The published Ubuntu 22.04 GPMC CLI has a newer glibc
  baseline and is **not** repackaged directly into older manylinux wheels.
  Source builds using the released native CLI require compatible GMP/MPFR
  runtime libraries; the platform pin is not a promise of universal portability.

### Verification and release engineering

- Build and smoke-test release wheels as independent per-platform pipelines
  rather than waiting for all platforms' wheel builds to finish. Retain the
  full four-platform, three-Python-version installed-wheel smoke requirement,
  source-distribution smokes, Rust crate preflight and fail-closed Release-Ready.
- Eliminate obsolete recursive submodule checkout from the shared release
  builder and its paired read-only validation/publishing workflows.
- Validate generated Codecov XML before upload, reduce redundant Rust-core
  execution across Python versions, and avoid duplicate CodSpeed runs on PR
  description edits.
- Add Path-sum operator-level regressions for internal variable capture
  during composition and bound-variable renaming under native reduction.
- Keep GPMC's native release and ABI qualification in its own repository.
  QuPRS retains opt-in consumer integration checks plus routine adapter
  correctness tests; it does not rerun upstream release qualification on
  every PR.

### Compatibility

- No intentional changes to public Python/Rust verification API contracts,
  default solver selection, tolerance semantics or Path-sum algorithms.
- The **source-build solver provisioning path changes**: users who relied on
  the removed GPMC git submodule must use the pinned release provisioning or
  supply an explicitly selected solver executable.
- As in v0.15.0, Python 3.11–3.13 and Qiskit 1.x–2.x remain the stated Python
  compatibility range. Windows release-asset pins do not imply a new Windows
  Python-wheel support commitment.


## v0.15.0 — Process supervision, public API typing and versioned docs

This entry describes the v0.15.0 source and distribution contents. Confirm
official availability using the matching [GitHub Release](https://github.com/PhysicsQoo/QuPRS/releases),
[PyPI distribution](https://pypi.org/project/QuPRS/), and
[Rust crate version](https://crates.io/crates/quprs/versions).
A source checkout or preview is not a published package.
Versioned documentation is published separately from the Python package.

### Python/Rust execution

- Add opt-in process-supervised Rust verification via
  `check_equivalence(..., backend="rust", safe_mode=True)`. The default
  `safe_mode=False` retains the existing in-process PyO3 behavior. Safe mode
  executes the same verifier and returns the existing result type; it does
  **not** silently switch Python calls to the standalone `QuPRS_cli`.
- Bound supervised-worker lifetime and propagate failures without converting
  timeouts or resource-limit errors into equivalence verdicts. Memory and
  process-tree enforcement depend on the operating system and supported
  mechanisms; see the [Python/Rust isolation guide](docs/python_rust_isolation.md).

### Public API, examples and documentation

- Provide source-derived Python class and dynamically mounted PathSum gate
  references alongside native Rustdoc through the Zensical documentation site.
  The generated `core.pyi` and packaged `py.typed` expose the public typing
  contract for installed wheel/sdist consumers.
- Add runnable installed-package examples for equivalence, inequivalence,
  global phase, explicit solver selection and optional supervised execution.
- Document Elim, HH and Omega with their preconditions, phase/output-map
  witnesses, normalization factors and termination boundaries. These algebraic
  witnesses do not imply verifier completeness or byte-identical Python/Rust
  internal IR representations.
- Prepare immutable versioned documentation beginning with **v0.15.0** plus
  independently updated `dev` and `stable` aliases. Publication of
  `/docs/v0.15.0/` and the stable alias occurs only after the official tag;
  v0.14.x documentation is not retroactively backfilled.

### Numerical correctness, solver integration and release checks

- Expand independent direct weighted-CNF regression coverage for GPMC and
  Ganak using exact rational-complex Boolean model enumeration, including
  satisfiable and unsatisfiable CNFs, conjunctions of clauses, signed complex
  weights, conjugate pairs and cancellation.
- Preserve solver-specific observations, `unknown` and failure provenance.
  Neither floating Complex WMC output nor a tolerance-dependent reduction is
  an unconditional exact-equivalence certificate; no new solver fallback or
  default solver is introduced.
- Check generated public API signatures, installed artifact behavior and
  source/scientific-documentation consistency. Native Rust release checks
  verify that the locked archive matches its preflight checksum before Cargo
  publication; Python and Rust publish independently after shared verification,
  and the GitHub Release follows only after both succeed.
  They also test standalone solver-free consumers with optional native features disabled.
  The full cross-platform
  source and wheel/sdist matrices remain mandatory at formal Release-Ready;
  ordinary documentation PRs do not repeat those expensive matrices.

### Compatibility and migration

- Retain Python **3.11–3.13**, Qiskit **1.x–2.x**
  (`qiskit>=1.0.0,<3.0`), Linux x86-64/ARM64 and macOS **15+**
  Intel/Apple Silicon release targets. This version does not claim
  Python 3.14/3.14t, Qiskit 3.x, macOS 14 wheels, or full Ubuntu 26.04
  qualification.
- Preserve the public `check_equivalence` entry point, default solver
  selection behavior and independent RR, phase and projective-distance
  tolerances. Experimental d4 integration and a certified Complex WMC solver
  are **not** production features of v0.15.0.

See the [v0.15.0 upgrade guide](docs/development/v0150-migration.md)
for supported-platform details and upgrade guidance.

## v0.14.1 — Rust CLI resource supervision and maintenance

### Rust CLI reliability and resource controls

- Supervise each native CLI invocation in a separate worker process with an
  end-to-end timeout covering input parsing, verification and worker cleanup.
  The default timeout remains 600 seconds.
- Add an optional Linux delegated-cgroup-v2 worker-tree physical-memory limit
  (`--max-memory-mib`) and an independent Unix virtual address-space limit
  (`--max-address-space-mib`). Unsupported or unenforceable requested limits
  fail closed; the address-space limit is not an RSS limit.
- Bound stdout and stderr capture independently, clean up worker temporary
  files, and suppress partial equivalence verdicts on timeout, cancellation,
  output-limit or resource-supervision failure. Document exit statuses and
  platform limitations in the [Rust CLI resource guide](docs/rust_cli_resource_limits.md).
- These controls are for trusted local execution and are not a sandbox
  against a malicious external solver. They introduce process-supervision
  overhead; no cross-platform or solver-inclusive speedup is claimed.

### Verification, tooling and documentation

- Tighten native CLI regression checks so `not_equivalent` cannot satisfy an
  `equivalent` test through substring matching; preserve solver and
  scientific verdict semantics.
- Improve CodSpeed source-impact classification and paired
  solver-inclusive benchmark evidence. The measurements remain observational
  rather than a fixed-percentage release gate.
- Consolidate public documentation for installation, supported QASM inputs,
  solver adapters and numerical behavior. Remove obsolete documentation
  references from six opt-in workflow source-file manifests while preserving
  the functional verification jobs.

### Compatibility and distribution

- No change to the public Python equivalence API, RR/WMC algorithms,
  GPMC/Ganak source, default numerical tolerances or existing Python
  3.11–3.13 / Qiskit 1.x–2.x compatibility claims.
- The `QuPRS_cli` program is built from the Rust workspace; do not assume a
  standalone executable is installed by the `QuPRS` PyPI wheel. Wheel/sdist
  validation still covers the Python package and native Python extension.

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

**Released:** 2026-11-04 ([v0.14.0](https://github.com/PhysicsQoo/QuPRS/releases/tag/v0.14.0)).

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
