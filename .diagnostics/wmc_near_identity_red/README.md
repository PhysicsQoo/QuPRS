# Near-identity WMC strict-equivalence RED

This isolated diagnostic checks an independently justified one-qubit
counterexample without modifying numerical tolerances, solvers, the public API,
or the Path-sum reduction-to-residual-WMC algorithm.

For `I` versus `RZ(0.001)`, the relative eigenphases differ by 0.001 rad:
the operators are **not** equivalent even up to a global phase. Their ideal
normalized trace magnitude is `cos(0.0005) = 0.9999998750000026...`. The
distance from one, about `1.25e-7`, lies within the currently configured
`1e-6` magnitude acceptance band, so a strict positive answer is unsound.
This is a semantic expectation, not an instruction to lower the tolerance.

Run the source-pinned opt-in diagnostic on an installed, native QuPRS build:

```sh
python -m pytest -q \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_independent_dense_operator_controls \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_count_policy_controls_and_true_negative

python -m pytest -vv -ra \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_near_identity_count_must_not_certify_equivalence_red \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_selected_native_wmc_near_identity_red
```

The first command should pass independent operator/reference controls. The
second command deliberately fails when a strict positive status is returned
for a genuinely inequivalent circuit, across Python/Rust and independently
selected GPMC/Ganak under `wmc_only`. A conservative unknown/nonpositive
result satisfies the no-false-positive claim but is not automatically a
certified inequivalence proof.

The tests live outside the normal `testpaths=["test"]` suite: the existing
tests of **current approximate numeric policy** remain untouched, whereas
this diagnostic tests **strict mathematical equivalence**. Never mark
scientific failures `xfail`/`skip`, loosen the oracle, or report a failing
scientific diagnostic as a passed correctness gate.

The opt-in workflow saves JUnit, raw test output, environment provenance,
source SHA and checksums even if the scientific test fails. Those artifacts
are diagnostic evidence, not the maintained CI baseline. Solver agreement
alone is not a proof certificate, and reported `tool_time` does not by
itself prove native model-counting execution.

A prior wider source-pinned WMC numeric study is archived separately; this
minimal regression is not a replacement for a full cross-solver science
review or an interval-certified implementation.
