# QuPRS public API and documentation audit

**Historical audit (2026-10-20):** The inventory below is anchored at
`dev@320f9f92af938897753d4999bde6903871b75edb` and is preserved for
provenance. It is **not** the current public API signature or the current
scientific limitations of the v0.13.4 release candidate. The newer interface
adds per-call `wmc_policy`, `wmc_magnitude_tolerance`, and
`wmc_phase_tolerance`; Rust source-decimal representation and result contracts
also changed. Consult `src/QuPRS/interface/load_qiskit.py` and
`docs/development/wmc-evidence-policy.md` for current behavior.

**Reference snapshot:** `dev@320f9f92af938897753d4999bde6903871b75edb`
(2026-10-20). This is a source-anchored inventory and gap analysis, **not**
an API stability promise, a generated reference, or evidence that a document
build has passed. Re-audit source links when the integration branch changes.

## Scope and evidence

The repository currently documents installation, PathSum examples, selected
equivalence checks, solver reliability, and floating weighted counts in
[README.md](../../README.md). The source snapshot had **no `docs/` tree**
before this audit. [CONTRIBUTING.md](../../CONTRIBUTING.md) establishes
feature/fix -> dev -> main integration and distinguishes CodSpeed Simulation
from real solver walltime. There is no verified standalone documentation
generator, strict documentation CI job, or versioned documentation deployment
in this snapshot.

The inventory covers Python public exports, Qiskit/QASM conversion, PathSum
internals, numerical/solver integration, the Rust core and FFI, packaging,
tests, and automation. Link paths below are relative to this file.

## Public API contract: observed, not inferred

| Entry point | Observed contract | Source and current evidence |
| --- | --- | --- |
| `QuPRS.check_equivalence` | Exported primary function. Accepts two Qiskit `QuantumCircuit` objects, QASM source strings, or file-path inputs; returns an `EquivalenceCheckResult`. | [Package exports](../../src/QuPRS/__init__.py), [dispatcher](../../src/QuPRS/interface/load_qiskit.py), [README usage](../../README.md) |
| `QuPRS.__version__` and version aliases | `__version__`, `__version_tuple__`, `version`, `version_tuple` exported; development fallback emits a warning if the version file is absent. | [Package exports](../../src/QuPRS/__init__.py), [generated version](../../src/QuPRS/_version.py) |
| `load_circuit` (module-level helper) | Loads QASM 2/3 from text or a `.qasm` file, or passes through `QuantumCircuit`; not listed in package-level `__all__`. | [Qiskit loader](../../src/QuPRS/interface/load_qiskit.py) |
| `EquivalenceCheckResult` | Dataclass stores result status, circuit/gate counts, timings, pathsum/statistics, WMC and solver metadata. It is defined in a module, not exported in package-level `__all__`. | [Result definition](../../src/QuPRS/interface/load_qiskit.py) |
| `PathSum`, `Register` | Importable via `QuPRS.pathsum` and used in examples; generated `core.pyi` describes interfaces. Distinguish internal dynamic gate/reduction methods from stable supported API. | [PathSum package](../../src/QuPRS/pathsum/__init__.py), [core](../../src/QuPRS/pathsum/core.py), [stub](../../src/QuPRS/pathsum/core.pyi) |

At this snapshot the primary function has the following signature:

```python
check_equivalence(
    circuit1,
    circuit2,
    method="hybrid",
    strategy="Difference",
    tool_name="gpmc",
    timeout=600,
    safe_mode=False,
    backend="python",
)
```

The source supports `method` values `hybrid`, `reduction_rules`, and
`wmc_only`; strategies `Difference`, `Proportional`, `Naive`, and
`Straightforward`; `backend` values `python` and `rust`; and WMC tools
`gpmc` or `ganak`. The default method can return without invoking WMC
when reduction already resolves the case. The selected solver must not be
silently replaced by the other solver.

**Status semantics need dedicated formal documentation.** The result field
`equivalent` can contain `"equivalent"` (exact), `"equivalent*"` (up to
nonzero global phase), `"not_equivalent"`, `"unknown"`, `"Timeout"`, or
`"MemoryOut"`. Some process, parser, or other solver errors propagate as
exceptions; do **not** document them as `"not_equivalent"`. In
`reduction_rules`, `"unknown"` means that the procedure did not decide the
case, not that the circuits are inequivalent. The configured `timeout` is
not a strict wall-clock bound for every in-process computation or every
platform/thread. See [dispatcher](../../src/QuPRS/interface/load_qiskit.py)
and [README reliability notes](../../README.md).

## Architecture and code ownership map

| Layer | Source of truth | Evidence/tests | Documentation work still required |
| --- | --- | --- | --- |
| Input and gate translation | [load_qiskit.py](../../src/QuPRS/interface/load_qiskit.py), [gate_library.py](../../src/QuPRS/interface/gate_library.py), [qasm2qc.py](../../src/QuPRS/interface/qasm2qc.py) | [Register partition tests](../../test/test_issue21_register_partitions.py) | Supported gate list, QASM2/QASM3 limitations and register layouts |
| Python PathSum state, gates, reductions | [core.py](../../src/QuPRS/pathsum/core.py), [gates/](../../src/QuPRS/pathsum/gates), [pattern_match.py](../../src/QuPRS/pathsum/pattern_match.py), [reduction.py](../../src/QuPRS/pathsum/reduction.py), [statistics.py](../../src/QuPRS/pathsum/statistics.py) | [Reduction tests](../../test/test_RR.py) | State notation, path variables, Elim/HH/Omega preconditions, incompleteness |
| Python strategies | [strategy.py](../../src/QuPRS/utils/strategy.py) | [Feynman](../../test/test_Feynman.py), [MQT](../../test/test_MQT.py) | Gate order, strategy policy, intermediate trace semantics |
| Python WMC and subprocess | [ps2wmc.py](../../src/QuPRS/interface/ps2wmc.py), [wmc_solvers.py](../../src/QuPRS/utils/wmc_solvers.py), [solver_process.py](../../src/QuPRS/utils/solver_process.py), [ganak_distribution.py](../../src/QuPRS/utils/ganak_distribution.py) | [WMC numerics](../../test/test_wmc_numerics.py), [solver adapters](../../test/test_wmc_solver_adapters.py), [process lifecycle](../../test/test_solver_process_lifecycle.py), [distribution](../../test/test_ganak_distribution.py) | CNF/weight grammar, failure types, timeout/provenance, precision assumptions |
| Rust PathSum and reduction | [Rust IR](../../rust/pathsum/src/ir.rs), [reduction](../../rust/pathsum/src/reduction.rs), [strategies](../../rust/pathsum/src/strategy.rs), [QASM](../../rust/pathsum/src/qasm.rs) | Rust unit/integration tests in `rust/`, Python/Rust WMC fixtures | Reduction rule definitions, QASM frontend differences and backend parity |
| Rust WMC process | [wmc.rs](../../rust/pathsum/src/wmc.rs), [solver_process.rs](../../rust/pathsum/src/solver_process.rs) | [WMC numeric tests](../../test/test_wmc_numerics.py) | Exact solver boundary and native error surface |
| Python/Rust interface | [ffi/api.rs](../../rust/python_ffi/src/api.rs), [ffi/lib.rs](../../rust/python_ffi/src/lib.rs), [load_qiskit.py](../../src/QuPRS/interface/load_qiskit.py) | [Cross-backend register tests](../../test/test_issue21_register_partitions.py) | Ownership, supported input, exception/status translation |
| Packaging and version | [pyproject.toml](../../pyproject.toml), [Python publishing](../../.github/workflows/python-publish.yml), [artifact CI](../../.github/workflows/release-artifact-ci.yml) | [macOS wheel tests](../../test/test_macos_wheel_support.py) | Wheel versus sdist compatibility and release archive reproducibility |
| CI and performance | [pytest](../../.github/workflows/pytest.yml), [CodSpeed](../../.github/workflows/codspeed.yml), [release gate](../../.github/workflows/release-ready-main.yml), [benchmark CI](../../.github/workflows/benchmarks.yml), [Docker CI](../../.github/workflows/docker-build.yml) | [Benchmark report integrity](../../test/test_benchmark_report_integrity.py), [CONTRIBUTING](../../CONTRIBUTING.md) | Document which jobs are required, informational, tag-only, and platform-specific |

### Compatibility statements to preserve

- [pyproject.toml](../../pyproject.toml) requires Python `>=3.11` and
  constrains `qiskit>=1.0.0,<2.0`. A broad metadata lower bound does **not**
  establish Python 3.14 or Qiskit 2.x support. The current CI matrix tests
  Python 3.11, 3.12, and 3.13.
- The published macOS **wheel** baseline is macOS 15+ on Intel and Apple
  Silicon; the README separately reports only narrowly tested macOS 14
  Apple Silicon **source-install** behavior. A source-build smoke does not
  make macOS 14 a supported wheel platform.
- Ganak 2.8.0 is invoked in `--mode=6`, GPMC in `-mode=1`. The solvers
  are independent, and floating weighted model counts are not a universal
  exact-arithmetic certificate. Normalized WMC magnitude and phase decision
  tolerances are `1e-6`, distinct from Python symbolic reduction tolerance
  `1e-10`; numerical boundaries need independent verification.

## Verification inventory and identified gaps

The snapshot has 13 Python test files under `test/`, seven workflow files
under `.github/workflows/`, the `benchmarks/Feynman` and
`benchmarks/MQTBench` corpora, and no pre-existing `docs/` tree.
Do not claim a historical `test/test_backend_semantics.py` exists at this
reference SHA: it was absent when the audit was made. An independent semantic
oracle suite is being developed in a **separate test-only branch**. Likewise,
a green performance Simulation job does not establish solver end-to-end
walltime parity.

| Documentation deliverable | Status at reference SHA | Gate for completion |
| --- | --- | --- |
| Source/API inventory (this page) | First pass drafted | Review ownership, links and scope in a dedicated documentation PR |
| MkDocs or equivalent nav/site setup | Not delivered | Config, navigation, local build, warning/error policy |
| Formal exact/global-phase/inequivalent/unknown semantics | Not delivered | Mathematical definitions, independent matrix oracles, solver error contract |
| Python generated API reference | Not delivered | Stable exports defined and checked against code signatures |
| Rust API and architectural decisions | Not delivered | Rustdoc or equivalent plus explicit Python/FFI boundary |
| Copy-paste installation and API examples | README examples exist, unverified as docs tests | CI executes examples against supported package |
| Versioned dev/main docs and deployment | Not delivered | Protected release/docs workflow and versioned URLs |
| Documentation governance and release checklist | Contributor guidance exists | Explicit review/checklist with source ownership and version parity |

## Proposed documentation information architecture

1. **Getting Started:** supported installation platforms, minimal verified
   `QuantumCircuit` example, expected outcomes, troubleshooting.
2. **Concepts:** formal semantics, global phase, PathSum state and reduction
   rules, independent WMC solver contracts and error taxonomy.
3. **Guides:** choose verification method/strategy/backend, parse QASM, interpret
   statistics, understand numerical precision and timeout bounds.
4. **API Reference:** Python public surface, typed result dataclass, PathSum
   secondary interface and explicitly labeled Rust/FFI internal API.
5. **Development:** architectural decisions, testing matrix, benchmark and
   release provenance, reproducible build/release workflow.

## Review checklist for this audit

- [ ] Verify every relative source/test/workflow link on the PR head.
- [ ] Have maintainers review which importable helpers are **supported
      public API** rather than accidentally promising all internal symbols.
- [ ] Validate supported-gate/exception details against the exact source.
- [ ] Confirm the tests/CI inventory still matches the PR merge base.
- [ ] Merge this documentation-only audit into `dev` after scoped review.
- [ ] Implement generated API docs, executable examples and site/tooling in
      **separate** changes; do not treat this inventory as their completion.

No solver, QASM, numerical, branch-protection, or release behavior is changed
by this document.
