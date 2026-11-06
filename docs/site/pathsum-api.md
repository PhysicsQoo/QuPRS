# Python API: Advanced Path-sum

The `QuPRS.pathsum` subpackage exposes symbolic circuit and Boolean
output-state primitives. This lower-level interface is useful for studying
reduction rules and constructing Path-sums directly. It is distinct from
the recommended high-level [verification API](python-api.md).

```python
from QuPRS.pathsum import PathSum, Register, F, support_gate_set

q = Register(2, "q")
circuit = PathSum.QuantumCircuit(q)
circuit = circuit.h(0)
circuit = circuit.cx(0, 1)
assert {"h", "cx"}.issubset(support_gate_set())
```

Gate methods return a `PathSum` object; use the returned object instead
of assuming in-place mutation. Gate parameters use the actual source-level
signature and numerical phase conventions described by their implementation.

## PathSum

The central object stores a phase polynomial, Boolean output mapping and
summation variables. The methods `h`, `cx`, `rz`, `mcx` and other
supported gates are **attached dynamically** from Gate classes. This
reference reads their committed, source-generated `core.pyi` signatures
and docstrings through Griffe's static stub merge. It does not import
QuPRS or execute gate implementations while rendering the site.

::: QuPRS.pathsum.core.PathSum
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: true
      filters:
        - "!^_"

### Dynamic gate signature sources

The public gate-method names and signatures are built from Gate subclasses'
`gate_name`, `__init__`, and `apply` declarations. The
`scripts/generate_stubs.py` generator produces `core.pyi`, and the
documentation CI checks that every source Gate has a matching stub method
and that Griffe can discover it without runtime inspection.

The generated signatures include single-qubit methods such as `h` and
`rz(theta, qubit, is_bra=False)`, controlled methods such as
`cx(control_qubit, target_qubit, is_bra=False)`, and multi-qubit
methods such as `mcx(*qubits, is_bra=False)`. Some specialized names
are case-sensitive (for example `CRk`).

## Register

::: QuPRS.pathsum.core.Register
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: true
      filters:
        - "!^_"

## Boolean output mapping: F

::: QuPRS.pathsum.core.F
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: true
      filters:
        - "!^_"

Boolean output-state expressions and phase-polynomial coefficients belong
to different algebraic domains. A Boolean substitution uses ANF/GF(2)
semantics; do not apply `mod 2` to the original phase polynomial when
writing reductions. See [Path-sum and reduction](path-sum.md) for the
Elim, HH, and omega preconditions and ket-preserving identities.

## Reduction statistics

`StatisticsManager` is exposed through `PathSum.stats` and the
high-level result's `Statistics` field. Its counters are diagnostic,
not proof certificates; this class is not a top-level `QuPRS` export.

::: QuPRS.pathsum.statistics.StatisticsManager
    options:
      allow_inspection: false
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members: true
      filters:
        - "!^_"

## Gate discovery helpers

These helpers are exports of `QuPRS.pathsum`. They describe what is
currently implemented; they are not a promise that unimplemented gates
will be silently approximated or substituted.

::: QuPRS.pathsum.gates.support_gate_set
    options:
      allow_inspection: false
      show_source: false
      members: false

::: QuPRS.pathsum.gates.get_gates_by_type
    options:
      allow_inspection: false
      show_source: false
      members: false

::: QuPRS.pathsum.gates.get_all_gates
    options:
      allow_inspection: false
      show_source: false
      members: false

::: QuPRS.pathsum.gates.list_supported_gates
    options:
      allow_inspection: false
      show_source: false
      members: false

## API stability

`PathSum`, `Register`, `F`, and gate-discovery functions are exposed
by `QuPRS.pathsum.__all__`. This does not automatically guarantee
backwards compatibility for every internal implementation detail. For
SolverAdapter and weighted-CNF implementation classes, consult
[Weighted model counting](weighted-model-counting.md); those are not
promoted to stable public Python APIs by this reference.
