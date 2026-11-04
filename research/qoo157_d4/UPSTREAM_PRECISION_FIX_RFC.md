# QOO-157 — upstream d4 precision-fix proposal (research draft)

This is an upstream-maintainer proposal, **not** an approved upstream
change or a QuPRS release integration. Upstream remains pinned to
`jm62300/d4@be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`.

## Source-level defect

At the pinned commit, `c++/counter/src/Counter.cpp` calls
`T result = counter->run();` and **then** `mpf_set_default_prec(426)`
inside the output-format branches. GMP `mpf_class` objects created for
complex weights/operations before this change retain their already
established limited precision. Changing the default after computation
cannot restore a lost small nonzero weighted-count residual.

The minimal verified research control adds
`mpf_set_default_prec(426)` at the start of
`c++/counter/src/Main.cpp::main()`, before DIMACS parsing, semiring
weight construction or counter execution. This is an **ephemeral local
CI patch** in `precision_variant.py`, not a change to the pinned
upstream repository.

For a maintained fix, ask upstream to:

1. Set the precision **before parsing or allocating GMP float values**.
   Eliminate the late precision setting or clarify its output-only scope.
2. Expose and verify the *effective GMP precision* in run provenance;
   distinguish requested bits from GMP limb-rounded bits. Reject invalid
   precision settings rather than silently using a misleading default.
3. Keep source weight-string parsing decimal and avoid intermediate
   `double` conversions. Return finite complex weights with stable
   `arb float`/integer output and an identifiable arithmetic mode.
4. Add a regression test where the correct complex count is a tiny
   *nonzero* 1e-40 or 1e-60 after cancellation; never use an absolute
   1e-15 threshold to declare zero correct.
5. Document that GMP `mpf` finite precision and 50 printed significant
   digits **do not provide a rigorous cumulative arithmetic error bound**.
   A correct printed value on one fixture is not a certified interval for
   arbitrary circuits.

## Reproducible scientific controls

- Unmodified counter vs early-precision patch:
  [CI 41808891018](https://github.com/PhysicsQoo/QuPRS/actions/runs/41808891018),
  two successful jobs, archived original/experimental binary SHA, exact
  QuPRS CNF bytes and 16 tiny real/imaginary cancellation cases.
- Same-host precision sweep 64/128/256/426 bits:
  [CI 41807878156](https://github.com/PhysicsQoo/QuPRS/actions/runs/41807878156)
  (baseline 12/16 small nonzero residual controls; 256 and 426: 16/16).
- Frozen QuPRS f64/MPFR256 source-CNF comparison:
  [CI 41808946607](https://github.com/PhysicsQoo/QuPRS/actions/runs/41808946607)
  (baseline 1/6 strict 1e-25 count screens; corrected >=128: 6/6).
  This is empirical native arithmetic **not** QuPRS EQ/NEQ boundary proof.
- Python opt-in SolverAdapter on the same six CNFs:
  [CI 41810985081](https://github.com/PhysicsQoo/QuPRS/actions/runs/41810985081)
  (6/6 strict pilot; source and binary provenance retained).
- Rust opt-in SolverAdapter is tracked on the separate
  `experiment/qoo157-d4-rust-adapter-poc` branch.

## Distribution/licensing blocker: maintainer confirmation required

At the pinned upstream revision:

- Repository `LICENSE`: GNU LGPL v2.1 text.
- `c++/counter/src/Main.cpp`, `Counter.cpp`,
  `c++/semirings/MpzComplexSemiring.hpp`: file headers explicitly state
  GPL version 3 or later, despite a later boilerplate reference to GNU
  Lesser GPL. These statements are not interchangeable.
- `rust/Cargo.toml`: `license = "GPL-3.0-or-later"`.

A legal/license owner must resolve which license(s), copyright notices,
dependency redistribution obligations, and linking/bundling conditions
apply to each compiled counter variant. The QuPRS research experiment
builds the d4 executable from source in CI but **does not publish or
redistribute that executable in QuPRS wheels, containers, release assets,
or application packages**.

Only after a maintained upstream fix, scoped conformance and licensing
review should QuPRS consider an optional user-selected external solver.
No default switch, no automatic GPMC/Ganak fallback, no release PR yet.
