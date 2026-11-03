# QuPRS GitHub Actions execution inventory and parallelism

Pre-merge CI cleanup reviewed on 2026-11-03 against PR #131 source `a3009801d4143656d2186c36b8dc8db41442c553`, latest `dev@2dd451edeaab4e7c80ea19203e36cc22f3548d85`, and the **measured** CodSpeed base `dev@55e78c7597966617c1a193b89056ff4e99c3ddfb`. The newer dev commit adds a separate Qiskit 2.6.1 Level-0 QASM corpus; an earlier-base measurement must not be mislabeled as a new-base measurement.

## Policy

1. Run correctness, numerical evidence, performance, container, and native-platform checks as **independent parallel workflows**. Their scientific scopes differ; do not suppress a failing check merely because another suite passed.
2. Never insert a cross-workflow dependency solely to force a serial build. The first shard of CodSpeed checks five-shard union/disjointness and paper inputs before running its own benchmark; the other four shards begin concurrently.
3. Use per-workflow, per-PR `concurrency` cancellation for *superseded commits* only; do not serialize jobs of the same commit and never cancel protected main/dev push acceptance.
4. Retain all 12 distinct native platform/Python combinations for solver-sensitive dev PRs and dev/main pushes. Matrix entries are concurrent; actual allocation of scarce GitHub-hosted macOS Intel runners is controlled by GitHub and **cannot be guaranteed by YAML**.
5. Long source-pinned research cohorts run on demand, outside mandatory PR checks. A PR `paths:` filter matches the cumulative PR diff, not just the newest commit; the shared incremental evidence resolver must independently validate same-source reuse.
6. The final `Release-Ready / Required` aggregate remains fail-closed: it must see all 12 source-platform jobs and the expected wheel/sdist build and smoke matrix, even though these suites now start independently.
7. All timing and regression judgments must use CodSpeed, with Simulation syscall-exclusion and non-Macro WallTime caveats stated explicitly. Don't silently replace a solver-inclusive measurement with a solver-excluding estimate.

## Default PR-to-dev lanes (separate checks)

| Workflow | Scope | Why not fold into another job? |
| --- | --- | --- |
| `dev-fast.yml` | Native/Rust smoke and comprehensive Python correctness, representative evidence | Fast feedback; needs only one Linux environment |
| `benchmarks.yml` | Legacy PR benchmark reporting is label-opt-in (`ci-legacy-benchmark`); main push retains baseline publication | The default PR run only validates impact/provenance and does not duplicate CodSpeed measurement |
| `codspeed.yml` | Five Simulation shards (32 immutable historical + 24 Qiskit261 Level-0 new IDs, shard-0 source/identity check), seven source-pinned paired Solver-inclusive WallTime cases, native Rust CPU, same-SHA evidence audit | CodSpeed performance authority; all timing claims distinguish simulated CPU from solver-inclusive WallTime |
| `native-cross-platform-pr.yml` | Reuses `pytest.yml` for 12 OS/Python cells | Actual platform/ABI coverage; independent matrix jobs |
| `docker-build.yml` | Tester-stage Docker build matrix | Installed/container artifacts are not source pytest |
| `wmc-conservative-policy.yml` | WMC numerical and phase classification contract | Independent physics/precision gate |
| `solver-cross-backend-conformance.yml` | Cross-backend, same-CNF GPMC/Ganak contract | Different scientific coverage than general pytest |
| `rust-qasm-source-guard.yml` | Qiskit 1.x/2.x source parsing and failure semantics | Qiskit version-specific checks |

The `codspeed.yml` separate `verify_shard_coverage` runner was eliminated. Proof moved to **shard 0**, before its CodSpeed measurement, so failure still fails the matrix without delaying four other shards.

## Pre-merge retirement of PR-number-specific diagnostics (2026-11-03)

The two PR-#131-only workflow files `pr131-paired-walltime.yml` and
`pr131-qft-diagnostic.yml` were **added solely on this feature PR** and
are removed from its final tree before integration into `dev`.
They were label/manual-triggered, not part of the required PR-to-dev
science or benchmark matrix. Their definitions remain retrievable in
[the immutable pre-cleanup source](https://github.com/PhysicsQoo/QuPRS/tree/a3009801d4143656d2186c36b8dc8db41442c553/.github/workflows)
and their historical measurement artifacts remain associated with the
original Actions runs. Removing a workflow from the integration tree
does not erase an earlier run or certify its numerical results.

Do **not** reinstate per-PR experiment workflow files on `dev` or
`main`. For repeatability studies and source-pinned experimental
diagnostics, prefer the isolated research branch and existing
`workflow_dispatch`/bounded experiment infrastructure. The standard
`codspeed.yml` still contains compatibility opt-in research jobs;
they are not default release gates and should be relocated only in a
separate, focused CI migration with its own contract tests, not by
silently deleting historic benchmark identities.

### Exact-HEAD evidence before integration

- [CI on PR HEAD a300980](https://github.com/PhysicsQoo/QuPRS/actions/runs/41582565268):
  five Simulation shards, seven paired Solver-inclusive WallTime
  cases (14 measured base/head identities), native Rust CPU, and
  cross-instrument provenance all completed successfully.
- [CodSpeed Performance Analysis](https://github.com/PhysicsQoo/QuPRS/runs/125743839069):
  check SUCCESS; 20 improved, 12 unchanged, 39 new and 102 skipped
  identities **against measured dev@55e78c7**, with hardware and
  syscall warnings. Check SUCCESS is not an unconditional end-to-end
  solver-speed guarantee or proof that every case improved.
- [Second evidence-reuse workflow](https://github.com/PhysicsQoo/QuPRS/actions/runs/41582663166):
  source-verified incremental reuse succeeded; expensive jobs skipped
  deliberately. Reuse references previous exact-source evidence and
  never creates a measurement for a new SHA.
- WMC numerical, Python/Rust Solver Conformance, QASM 1.x/2.x,
  full Dev Fast, 12 native platform cells and both Docker test
  architectures also completed successfully on a300980.
- P5 is observation-only: no fixed percentage threshold or automated
  performance veto. Ganak near-boundary verdict differences remain
  separately qualified and cannot be used as science PASS.

The later `dev@2dd451e` contains the separately merged, versioned
MQTBench QASM corpus. Verify its source-impact and benchmark identity
before merging #131; do not claim the older CodSpeed base already
measured this commit, or rerun unrelated expensive suites without a
scientific/workflow input change.

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
