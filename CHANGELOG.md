# Changelog

Significant user-facing changes to QuPRS are summarized here. See [GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases) for published packages and release dates.

## 0.13.3 — Release candidate

### Fixed
- Correct Rust `wmc_only` equivalence decisions when a constrained trace CNF contains no additional path variables. These cases must still be solved: the prior shortcut could incorrectly report an inequivalent pair (for example, Identity versus X) as equivalent.
- Preserve independent Ganak/GPMC solver execution and typed Timeout/SolverError/Unknown results, with bounded external solver subprocess cleanup on supported POSIX systems.
- Handle disappearing Linux `/proc` tasks during solver process-tree inspection without weakening the assertions about surviving descendants.
- Align the documented minimum supported **macOS binary wheel** deployment target with actual artifact tags (macOS 15+); distinguish the macOS 14 source-build test evidence from wheel compatibility.

### Validation and release infrastructure
- Build and actually install candidate wheels on Linux x86_64/ARM64 and macOS Intel/Apple Silicon with Python 3.11–3.13, plus clean sdist installations on Linux and macOS. Check native-extension imports, package version, Ganak/GPMC independence and circuit-equivalence oracles on the installed archives.
- Verify benchmark shard completeness and integrity, including nonempty five-way CodSpeed coverage, and record provenance for benchmark reports.
- Run Python/Rust WMC regression tests across Ganak and GPMC, including equivalence, global phase, inequivalence, and failure handling. No solver fallback or relaxation of numerical correctness thresholds is introduced.
- Introduce a release candidate approval process that verifies required source/installed-artifact CI before authorizing a versioned `dev → main` Release PR, Annotated Tag and publication. The exact protection settings and CI evidence must be confirmed at publication time.

### Performance evidence
- Before integrating the WMC correctness fix to `dev`, same-runner paired ABBA measurements across QFT16, Grover4 and QAOA7 (Ganak/GPMC, Rust and selected Python cases) reported no significant unrelated regression among eight measured workloads. This does **not** establish a universal no-regression guarantee across other circuits, hosts or solvers; refer to the release acceptance record.

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
