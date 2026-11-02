# Incremental CI impact routing (Phase A/B)

This change augments the existing source-aware workflow triggers without altering
QuPRS algorithms, its 32 historical CodSpeed benchmark identities, five shards,
CodSpeed instruments, or release-ready acceptance.

## Decision and provenance

The `ci-impact` job is cheap and always executes *when its workflow is triggered*.
It may reuse a prior successful **same PR, same base SHA** workflow run when:

1. The previous run completed successfully and all explicitly required matrix
   jobs completed with `success` (not `skipped`).
2. The old commit is an ancestor of the current HEAD, or the SHA is identical.
3. Every changed path between those two commits is in the narrow Markdown-only
   allowlist. Source, solver gitlinks, QASM/JSON fixtures, benchmark and CI
   scripts, lock files, and workflows are never considered docs-only.
4. GitHub's diff, run provenance, and job inventory are available and complete.

The job exports `run_heavy`, `reused_run_id`, and `measured_head_sha`;
ordinary heavy jobs run only if `run_heavy == 'true'`. When it is false,
the new commit **did not receive a new measurement**. The job summary cites
its original successful run and SHA. API failures, missing evidence, changed
base, modified CI policy, and unknown changes fall back to the original full
workload. The bounded history search is deliberately conservative.

The routing source and regression contracts are
`.github/scripts/ci-impact-reuse.cjs` and
`.github/scripts/test-ci-impact-reuse.cjs`. These scripts appear in affected
workflow paths so an edit triggers new verification. The evaluator uses a
read-only GitHub token. No performance threshold is added; CodSpeed P5 remains
observational, while science, source identity and shard completeness stay
fail-closed.

## Covered workflows

- `codspeed.yml`: original five Simulation shards, same-SHA native Rust,
  seven paired GPMC/Ganak WallTime cases, and cross-instrument aggregation.
  Manual opt-in experiments retain their existing independent triggers.
- `dev-fast.yml`: the single fast source-correctness job.
- `native-cross-platform-pr.yml`: all 12 native source matrix jobs.
- `docker-build.yml`: two PR tester builds; tag publishing is unchanged.
- `benchmarks.yml`: the explicitly labeled legacy PR benchmark job;
  main baseline publication and resource pilots retain their original rules.
- `wmc-conservative-policy.yml`: numeric evidence and WMC classification contracts.
- `solver-cross-backend-conformance.yml`: real Python/Rust/GPMC/Ganak solver conformance.
- `rust-qasm-source-guard.yml`: both Qiskit source-parsing matrix variants.

The shared classifier also recognizes modifications to *other independent workflow
files* as irrelevant to the measured lane. A change to a workflow's own YAML,
shared CI-impact scripts, or a called reusable workflow (notably
`native-cross-platform-pr.yml` -> `pytest.yml`) still invalidates evidence.
New, unknown source or executable file types fail closed.

Existing PR `paths` filters are not sufficient alone: GitHub PR three-dot
comparisons still include earlier code changes on the same PR. Conversely,
workflow-level `paths-ignore` on a required check may leave it pending.

## Release behavior and further qualification

`dev -> main` retains the existing `Release-Ready / Required` check and full
release source/wheel/sdist matrix. Automatic reuse of release artifact evidence
requires an additional independently tested exact merge-tree and package-input
fingerprint and is **not** enabled by this first integration. No required
status checks are renamed or made optional.

The routing contract test deliberately covers docs-only, source/registry edits,
previous FAIL/SKIP, base changes, inaccessible API, non-descendant commits,
first PR opens and manual/push events. After merge to `dev`, validate a
subsequent PR with a successful code run followed by a docs-only commit, as
well as a source-changing negative test, before treating skip efficiency as
production-proven. This implementation does not claim to reuse CodSpeed data
for a new SHA; it only cites the older measured source that remains identical.

## Documentation-only PR synchronize smoke test

An isolated documentation-only follow-up commit is used to test actual
GitHub Actions evidence reuse. Its source, benchmark identity, solver
submodule and workflow files remain unchanged. Acceptance requires the
impact jobs to cite the earlier successful run and to skip expensive jobs;
no new CodSpeed measurement should be reported for this documentation SHA.

## Live proof: documentation-only update on code-bearing PR #131

After exact HEAD `f85b16e` succeeded in all eight GitHub Actions workflows,
the **sole changed file** in follow-up commit [`700f240`](https://github.com/PhysicsQoo/QuPRS/commit/700f240924babbd6a0cc05cee6831ec2f59f62a9)
was this Markdown document. The PR still contained all earlier program changes.

GitHub Actions confirmed:

| Workflow | Run | Impact decision | Actual heavy jobs |
| --- | --- | --- | --- |
| CodSpeed | [41469637797](https://github.com/PhysicsQoo/QuPRS/actions/runs/41469637797) | REUSE | 5 Simulation shards, native Rust CPU, paired WallTime, cross-instrument all SKIPPED |
| Dev Fast | [41469637737](https://github.com/PhysicsQoo/QuPRS/actions/runs/41469637737) | REUSE | Source correctness SKIPPED |
| Native | [41469637745](https://github.com/PhysicsQoo/QuPRS/actions/runs/41469637745) | REUSE | 12-platform source matrix SKIPPED |
| Docker | [41469637818](https://github.com/PhysicsQoo/QuPRS/actions/runs/41469637818) | REUSE | AMD64 and ARM64 tester SKIPPED |

All four impact jobs completed SUCCESS; their logs reported `CI impact REUSE`
and the 12 original contract tests passed. These are authentic GitHub-hosted
CI executions, not a local prediction. The earlier measured SHA and run remain
the evidence; **no new CodSpeed timings are claimed for `700f240`**.

WMC, Solver Conformance and QASM Guard were still running on this docs-only
commit because their earlier YAML had not yet integrated the common resolver.
This second integration implements those remaining lanes; the workflow changes
must undergo their own first-run validation before any future documentation-only
reuse can be claimed for them.
