# Python API

The primary supported Python import is:

```python
from QuPRS import check_equivalence
```

The generated signatures below come from the Python source tree. Only explicitly selected API entry points are documented; Python implementation helpers and private Rust worker modules are not part of this API reference.

## Circuit equivalence

::: QuPRS.interface.load_qiskit.check_equivalence
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: false

## Verification result

`check_equivalence()` returns an `EquivalenceCheckResult` object. The result type is defined in `QuPRS.interface.load_qiskit` and is not currently re-exported by `QuPRS.__all__`.

::: QuPRS.interface.load_qiskit.EquivalenceCheckResult
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: false

## Numerical results

The `equivalent` field can report `equivalent`, `equivalent*`, `not_equivalent`, `unknown`, `Timeout`, or `MemoryOut`. An inconclusive or resource-limited result is not a proof of circuit inequivalence.

`rr_tolerance`, `wmc_phase_tolerance` (or its `phase_tolerance` alias), and `approximate_distance_tolerance` control distinct parts of verification. See [Verification](verification.md) and the [equivalence semantics](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/equivalence-semantics.md).
