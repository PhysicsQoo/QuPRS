# Near-identity WMC strict-equivalence RED

## Status after the 1e-8 numerical default

The original source-pinned study on 2026-10-23 used the legacy default
1e-6: identity versus RZ(0.001) yielded 5 deliberate strict-equivalence
RED failures. That original commit and CI evidence remain immutable.

Current public Python API defaults (merged via PR #112) are WMC magnitude and
phase tolerance **1e-8**, which rejects the old RZ(0.001) case in the four
actual Python/Rust x GPMC/Ganak implementations. This is an empirical
numerical-policy improvement, NOT a general soundness theorem.

The **new strict RED case** is identity versus RZ(0.0002).
Its ideal normalized trace unit defect is about 5e-9, less than 1e-8.
The two operators are still provably not equal up to any global phase:
the relative eigenphases differ by 0.0002 radians. The current numeric
heuristic may nevertheless report equivalent. An opt-in conservative WMC
policy returns Unknown on uncertified model counts.

The original RZ(0.001) behavior at 1e-6 remains replayable via explicit
per-call thresholds; source-pinned original research evidence is not
relabelled, erased or mistaken for the current default.

---

This isolated diagnostic checks an independently justified one-qubit
counterexample without modifying numerical tolerances, solvers, the public API,
or the Path-sum reduction-to-residual-WMC algorithm.

For `I` versus `RZ(0.0002)`, the relative eigenphases differ by
0.0002 radians: the operators are **not** equal even up to global phase.
The normalized trace is `cos(0.0001)`, whose defect from one is
`~5e-9`, below the currently configured `1e-8` magnitude threshold.
Numerical acceptance must not be promoted to a strict mathematical proof.
The original `RZ(0.001)` at explicit `1e-6` is a preserved historical
policy control, rather than a new default RED.

Run the source-pinned opt-in diagnostic on an installed, native QuPRS build:

```sh
python -m pytest -q \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_independent_dense_operator_controls \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_count_policy_controls_and_true_negative \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_default_threshold_rejects_historical_counterexample \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_explicit_historical_tolerance_retains_numeric_acceptance \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_conservative_mode_does_not_claim_small_angle_proof \
  .diagnostics/wmc_near_identity_red/test_near_identity.py::test_two_numerical_thresholds_are_not_equivalence_proofs

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
