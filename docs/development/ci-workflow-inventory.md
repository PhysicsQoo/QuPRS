# QuPRS GitHub Actions execution inventory and parallelism

Reviewed against PR #131 source `90c7da78a81caf8e86b92809970f7519410634e4` and `dev@55e78c7597966617c1a193b89056ff4e99c3ddfb` on 2026-11-01.

## Policy

1. Run correctness, numerical evidence, performance, container, and native-platform checks as **independent parallel workflows**. Their scientific scopes differ; do not suppress a failing check merely because another suite passed.
2. Never insert a cross-workflow dependency solely to force a serial build. The first shard of CodSpeed checks five-shard union/disjointness and paper inputs before running its own benchmark; the other four shards begin concurrently.
3. Use per-workflow, per-PR `concurrency` cancellation for *superseded commits* only; do not serialize jobs of the same commit and never cancel protected main/dev push acceptance.
4. Retain all 12 distinct native platform/Python combinations for solver-sensitive dev PRs and dev/main pushes. Matrix entries are concurrent; actual allocation of scarce GitHub-hosted macOS Intel runners is controlled by GitHub and **cannot be guaranteed by YAML**.
5. Long source-pinned PR #131 diagnostic cohorts run **on demand only** (see labels below), not on every synchronization. A PR `paths:` filter matches the cumulative PR diff, not just the newest commit.
6. The final `Release-Ready / Required` aggregate remains fail-closed: it must see all 12 source-platform jobs and the expected wheel/sdist build and smoke matrix, even though these suites now start independently.
7. All timing and regression judgments must use CodSpeed, with Simulation syscall-exclusion and non-Macro WallTime caveats stated explicitly. Don't silently replace a solver-inclusive measurement with a solver-excluding estimate.

## Default PR-to-dev lanes (separate checks)

| Workflow | Scope | Why not fold into another job? |
| --- | --- | --- |
| `dev-fast.yml` | Native/Rust smoke and comprehensive Python correctness, representative evidence | Fast feedback; needs only one Linux environment |
| `benchmarks.yml` | Paper benchmark reporting and evidence contract | Benchmark report/coverage output and source provenance differ from pytest correctness |
| `codspeed.yml` | Five parallel simulation shards, one collection/integrity audit on shard 0 | Performance profiling and canonical CodSpeed publication |
| `native-cross-platform-pr.yml` | Reuses `pytest.yml` for 12 OS/Python cells | Actual platform/ABI coverage; independent matrix jobs |
| `docker-build.yml` | Tester-stage Docker build matrix | Installed/container artifacts are not source pytest |
| `wmc-conservative-policy.yml` | WMC numerical and phase classification contract | Independent physics/precision gate |
| `solver-cross-backend-conformance.yml` | Cross-backend, same-CNF GPMC/Ganak contract | Different scientific coverage than general pytest |
| `rust-qasm-source-guard.yml` | Qiskit 1.x/2.x source parsing and failure semantics | Qiskit version-specific checks |

The `codspeed.yml` separate `verify_shard_coverage` runner was eliminated. Proof moved to **shard 0**, before its CodSpeed measurement, so failure still fails the matrix without delaying four other shards.

## PR #131 deep diagnostics (explicit request only)

These workflows no longer execute automatically on `opened/synchronize/reopened`; they run on `pull_request:labeled` for PR #131, or `workflow_dispatch` from a branch containing the workflow.

| Workflow | Explicit PR label | Purpose |
| --- | --- | --- |
| `codspeed-solver-cpu-pilot.yml` | `ci-solver-cpu-pilot` | Process-inclusive CPU diagnostic, subject to syscall-exclusion caveat |
| `pr131-paired-walltime.yml` | `ci-pr131-walltime` | Source-pinned main/dev/PR same-host walltime, non-Macro exploratory |
| `pr131-qft-diagnostic.yml` | `ci-pr131-qft` | QFT16 source, solver, and feature-flag diagnosis |

To rerun, remove and re-add the corresponding label, or dispatch manually after the workflow is present on the default branch. The active PR's pinned prior results are retained in GitHub Actions and CodSpeed; a successful old SHA is not acceptance of a changed source SHA.

## Integration pushes, main release, and publication

- `pytest.yml`: existing `workflow_call` reusable 12-platform suite plus push to `dev`/`main`; PR wrapper invokes exactly the same implementation, not an independent duplicate test definition.
- `release-ready-main.yml`: main-targeted PR only. Source-correctness and installed-artifact validation start concurrently; four-way final aggregator still checks every mandatory child job with fail-closed completion.
- `release-artifact-ci.yml`: reusable wheel/sdist build and smoke checks; distinct from source-only tests, not a publishing workflow.
- `python-publish.yml`: tag/publishing workflow. Do not conflate package delivery with dev PR validation.
- `benchmarks.yml`: canonical main benchmark reporting on push.
- `codspeed.yml`: ongoing push baselines for `dev` and `main`.

## The remaining opt-in research suite

The following workflows are **not ordinary PR-to-dev lanes**. Their manual or specific research-branch triggers already avoid normal PR runner contention:

- Reduction/stage/resource diagnostics: `exclusive-stage-ledger-pilot.yml`, `ffi-phase-solver-attribution.yml`, `fixed-host-solver-validation.yml`, `hosted-solver-comparison.yml`, `hosted-solver-expanded-cohort.yml`, `python-reduction-profile-paired.yml`, `rust-elim-cost-model-audit.yml`, `rust-elim-success-fixtures.yml`, `rust-native-stage-attribution.yml`, `rust-per-elim-cost-pilot.yml`, `rust-solver-adapter-ab.yml`.
- Scientific and QASM oracles: `paper-python-fidelity.yml`, `qiskit-2x-compatibility.yml`, `qoo134-semantic-red.yml`, `rust-cp-two-qubit-oracle.yml`, `rust-global-phase-exact.yml`, `rust-global-phase-source-contract.yml`, `rust-one-qubit-matrix-oracle.yml`, `rust-qasm-cp-exact.yml`, `rust-u2-semantics.yml`, `wmc-interval-reference.yml`.

## Capacity and follow-up

- Parallel jobs request independent runners immediately, but no source-level YAML change can ensure *zero waiting* when GitHub's shared runners or account concurrency limits are saturated.
- Native macOS Intel cells may remain the long pole. Do not remove OS/Python coverage merely to show a green aggregate earlier.
- Caching across independently spawned workflows is possible only for compatible build inputs (Python, Rust flags, platform, GPMC commit). Sharing an unversioned solver binary cache risks incorrect scientific/performance results.
- The dev PR gate and the protected main release gate have different obligations; optimize their DAGs separately. Do not launch Docker publication from pre-merge PRs.
