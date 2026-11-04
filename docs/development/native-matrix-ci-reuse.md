# Native PR → dev 12-platform evidence reuse admission

## Controlled research result (2026-11-04)

Representative [native pre-merge PR #135 run](https://github.com/PhysicsQoo/QuPRS/actions/runs/41739717641)
and [dev integration run](https://github.com/PhysicsQoo/QuPRS/actions/runs/41742485999)
had matching `git tree = 19558883e8ad7c30e6a592cfb4fbe312db9bcf07`,
the same Python 3.11/3.12/3.13 × four OS job identities, and 12/12
successful scientific test jobs each. This **does not certify identical
environments**. From actual Python-3.12 per-platform GitHub job logs:

| Slot | Pre-merge runner image | Post-merge runner image | Result |
| --- | --- | --- | --- |
| ubuntu-latest / 3.12 | ubuntu26/20261025.179 | ubuntu26/20261101.186 | **Different** |
| ubuntu-24.04-arm / 3.12 | ubuntu24-arm64/20261025.165 | ubuntu24-arm64/20261025.165 | Same image |
| macos-15-intel / 3.12 | macos-15/20260824.0482 | macos-15/20260824.0482 | Same image |
| macos-15 / 3.12 | macos-15-arm64/20261028.0489 | macos-15-arm64/20261028.0489 | Same image |

Even when Python/Qiskit and Rust package versions appear identical,
hosted runner images are rolling and packages are resolved at runtime.
Therefore **automatic matrix reuse is NOT_CERTIFIED** and the complete
12-job dev-push validation remains in force.

## Implemented report-only provenance and safety policy

`pytest.yml` now adds `native-matrix-evidence.json` to each already
existing per-slot XML artifact; no additional matrix/build jobs are added.
The witness records actual Git tree, submodule status hash, pytest
workflow hash, runner image ID/version (or unknown), OS and architecture,
Python/Rust version and pip freeze hash, GMP/MPFR versions and the
test-step status. The CI-included negative policy tests require all
12 slots, successful statuses, all source and environment fields,
nonduplicate slot IDs, and complete equality. It fails closed on
unknown image IDs and any drift.

The policy module is **report-only**, not connected to a CI skip control.
In particular a stored JSON value cannot be trusted as job success without
authenticating its GitHub workflow run, commit, per-job conclusion,
artifact identity and head/base provenance. The new evidence is a
prerequisite for a future safely justified reuse optimization, not a
claim that a successful PR is sufficient to eliminate dev integration CI.

Do not alter Release-Ready main's independent 12-platform acceptance,
nor replace scientific test results with benchmark or CodSpeed wall time.
