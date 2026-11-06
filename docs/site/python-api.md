# Python API: General

QuPRS provides a high-level Python entry point for comparing quantum circuits.
For symbolic circuit construction, gate methods, and reductions, see the
[Advanced Path-sum API](pathsum-api.md). These are separate import surfaces:
`QuPRS` and `QuPRS.pathsum` respectively.

```python
from QuPRS import check_equivalence

result = check_equivalence("first.qasm", "second.qasm", method="hybrid")
print(result.equivalent)
```

The input filenames above are illustrative; provide existing OpenQASM files or
Qiskit `QuantumCircuit` objects. The generated signatures and descriptions
below are taken from the version-matched Python source, without importing the
package into the documentation builder.

## Circuit equivalence

::: QuPRS.interface.load_qiskit.check_equivalence
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: false

`method` selects `hybrid`, `reduction_rules`, or `wmc_only`. The
`backend` argument selects the Python or Rust implementation; the solver
`tool_name` is independently selected when WMC is reached. A timeout request
is not always an end-to-end hard deadline for in-process symbolic work: see
the `safe_mode` contract in the function's source-generated reference and
the [Architecture](architecture.md) guide.

## Verification result

The function returns
`QuPRS.interface.load_qiskit.EquivalenceCheckResult`. It is a concrete
result dataclass, **not** currently an export of `QuPRS.__all__`.

::: QuPRS.interface.load_qiskit.EquivalenceCheckResult
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: true
      filters:
        - "!^_"

Important result fields include:

| Field | Meaning |
| --- | --- |
| `equivalent` | Verification verdict string; see the states below. |
| `final_pathsum` | Residual symbolic `PathSum`; consult the [advanced reference](pathsum-api.md). |
| `Statistics` | Reduction diagnostic object (`StatisticsManager`). |
| `rr_approximate` | An accepted RR-based result used tolerance-dependent reduction. |
| `wmc_solver_invoked` | Whether a real WMC solver process was called (when supplied). |
| `wmc_printed_verdict` / `wmc_precision_reason` | Solver-output interpretation and diagnostic provenance, not a mathematical error certificate. |
| `approximate_distance_tolerance` / `wmc_phase_tolerance` | Effective numerical thresholds recorded in the result. |

### Verdicts and numerical meaning

`equivalent` can report `equivalent`, `equivalent*`,
`not_equivalent`, `unknown`, `Timeout`, or `MemoryOut`.
`equivalent*` denotes equivalence up to global phase under the
configured numerical policy. Neither `unknown` nor a resource-limited or
solver-error result proves inequivalence. Numerical WMC output granularity
is not an exact solver error bound.

The independent `rr_tolerance`, `wmc_phase_tolerance` (alias
`phase_tolerance`), and `approximate_distance_tolerance` parameters
must not be conflated. For their scientific interpretation, see
[Verification](verification.md) and
[Equivalence semantics](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/equivalence-semantics.md).
