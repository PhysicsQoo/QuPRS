# Changelog

Significant user-facing changes to QuPRS are summarized here. See [GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases) for published packages and release dates.

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
