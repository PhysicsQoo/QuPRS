# Upgrading from QuPRS v0.13.4 to v0.14.0

**Status:** v0.14.0 public upgrade contract. The official
[v0.14.0 GitHub release](https://github.com/PhysicsQoo/QuPRS/releases/tag/v0.14.0)
was published on **2026-11-04**. This page describes the versioned
interface and does not replace the supported-platform or package-artifact
acceptance conditions.

## Supported environment and input

The v0.14.0 package declares Python **3.11–3.13** and
`qiskit>=1.0.0,<3.0` (Qiskit **1.x/2.x**). Qiskit 3.x and
Python 3.14/3.14t have not been admitted to this release. Wheels are
targeted to Linux x86_64/ARM64 and macOS 15+ Intel/Apple Silicon.
Historical macOS 14 sdist experiments do not imply a supported 14.x
prebuilt wheel. The existing recurring CI no longer reinstalls each of
four old Qiskit versions on every PR; the original admission evidence is
preserved in [Qiskit 1.x/2.x admission](qiskit-1x-2x-admission.md).

The **native Rust** verifier accepts supported OpenQASM 2 and an
explicitly limited **OpenQASM 3.0 unitary subset**, including
`qubit` declarations, `stdgates.inc`, source decimal/pi angles and
standalone `gphase(theta)`. Unsupported dynamic/measurement/reset/
classical features, custom gates or symbolic parameter expressions
fail closed. See [QASM3 supported subset](rust-qasm3-supported-subset.md).
A Python Qiskit `QuantumCircuit` carries a floating-point
`global_phase`; native source-literal QASM angles have different
provenance. The existing Python→Rust QASM2 bridge rejects unequal
explicit phases it cannot preserve, rather than returning a false
exact- or up-to-global-phase classification.

## API changes (breaking)

| v0.13.4 interface or behavior | v0.14.0 action |
| --- | --- |
| `wmc_magnitude_tolerance` / normalized trace-magnitude defect | **Removed.** Choose a physical projective `approximate_distance_tolerance` instead. The numeric values are not interchangeable. |
| `wmc_policy="legacy"/"conservative"` | **Removed.** No second exactness selector. Use the single numeric distance verdict plus precision/source diagnostics. |
| `config.TOLERANCE`, `set_tolerance()`, `get_tolerance()` | **Removed.** Pass `rr_tolerance` per `check_equivalence()` call; use `0` to disable approximate reduction. |
| Rust `check_equivalence_with_tolerances` | **Removed.** Use the supported verifier and its per-call typed options. |
| `wmc_phase_tolerance` | Still accepted as an alias for `phase_tolerance`; do not specify conflicting values for both. |
| `equivalent`, `equivalent*`, `not_equivalent` | Still numeric classifications; `equivalent*` is an up-to-global-phase label. RR-only can return `unknown`; a timeout or solver error is **not** proof of `not_equivalent`. |

The three distinct default thresholds are:

| Keyword | Default | Unit and meaning |
| --- | --- | --- |
| `rr_tolerance` | `1e-10` | Phase-polynomial **cycles** for local RR matching and bounded reduced residual |
| `phase_tolerance` | `1e-8` | **Radians** for labeling a global phase as negligible |
| `approximate_distance_tolerance` | `1e-8` | Dimensionless projective Hilbert–Schmidt **distance** |

The distance is

```text
D_proj(U,V) = sqrt(1 - |Tr(U† V)|² / 4^n)
```

For context, a *magnitude defect* of `1e-8` is **not** equivalent
to a projective distance of `1e-8` (the corresponding distance would
be about `1.4e-4` for a normalized magnitude of `1 - 1e-8`).
Select the new tolerance based on the desired physical distance,
not by copying the old numeric magnitude threshold.

```python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    backend="rust",
    method="hybrid",
    tool_name="gpmc",
    rr_tolerance=1e-10,                   # independent local reduction
    phase_tolerance=1e-8,                 # radians, global-phase label
    approximate_distance_tolerance=1e-8, # projective circuit distance
    gpmc_precision_digits=30,
)
print(result.equivalent)
print(result.wmc_solver_invoked, result.wmc_precision_reason)
```

When a **source-level** distance decision is important, use
`rr_tolerance=0` or `method="wmc_only"`; Hybrid deliberately
passes the **final RR-reduced PathSum** to WMC. An approximate RR
step can move its residual distance across the original source
threshold; the warning and `rr_approximate` provenance remain
informational rather than a second veto.

## Solver results, precision, and error handling

- GPMC supports the default **30-decimal-digit** complex solver mode
  and explicit `gpmc_precision_digits=90`, with tolerance-adaptive
  Rust MPFR *input-weight* precision. Neither is an all-input
  certified bound on Solver arithmetic.
- Ganak 2.8.0 mode 6 emits about **nine significant printed digits**
  (`%.8Re`). Increasing internal MPFR precision does not increase
  its fixed printed resolution. At `approximate_distance_tolerance=1e-8`,
  inspect `wmc_print_resolution_distance` and
  `wmc_precision_reason`: a finite center-point verdict may be
  determinate even if `wmc_printed_verdict="unknown"`.
- `wmc_numerical_verdict`, `wmc_printed_verdict`,
  `wmc_precision_reason` and `wmc_solver_invoked` distinguish a
  numerical result from source/solver provenance. None provides a
  general mathematical proof of exact equivalence.
- Correctness and coverage remain separate: wrong verdicts, invalid
  source proof or malformed Solver results fail; `Timeout`,
  `MemoryOut`, `INCONCLUSIVE_RESOURCE` and planned benchmark skips
  do **not** certify either equivalence or inequivalence. A full
  benchmark-performance cohort may be required explicitly, not as
  an automatic scientific-error gate.

For precise numerical semantics consult
[per-call tolerances](per-call-tolerance.md),
[WMC projective distance](wmc-numerical-tolerance.md),
[RR-to-WMC final residual](rr-hybrid-residual-contract.md)
and [release validation](release-compatibility.md).

## Release and installed-artifact verification

The v0.14.0 public release is recorded at
[GitHub Releases](https://github.com/PhysicsQoo/QuPRS/releases/tag/v0.14.0).
When validating an installation, distinguish source-level CI from the
actual distributed wheel or sdist installed in a supported environment.
Release compatibility, provenance and publication rules are defined by
[platform and release acceptance](release-compatibility.md). Historical
release-candidate experiments remain in Git and CI history; they are not
current pending conditions for a release that has already been published.
