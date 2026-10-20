# Contributing to QuPRS

## Branches and pre-merge checks

Open feature, bug-fix and performance pull requests against `dev`. Versioned
release candidates advance from `dev` to protected `main` after the
separate Release-Ready acceptance gate. Avoid merging performance experiments
directly into `main`.

Every code-affecting PR runs the applicable correctness and performance CI.
The `CodSpeed` workflow tracks **Simulation** benchmarks on both `main` and
`dev` pushes, and on affected PRs. It checks five complete, nonempty shards,
but a green CI result by itself **does not prove there is no regression**.

## Performance review for feat/fix -> dev

For changes to quantum-circuit reductions, circuit encodings, Rust/Python
backends, solver integrations, or benchmarks:

1. Inspect the CodSpeed PR report, linking the measurement and recording
   the exact candidate and comparison SHAs. Prefer a recent **`dev`** run
   (the PR target) over `main` when the branches have diverged. CodSpeed
   comparisons may use a configured default baseline, so verify the
   *actual* base SHA instead of assuming it is `dev`.
2. Check missing/new benchmarks, shard coverage, skipped cases and the
   Simulation benchmark measurements. Record any runner CPU and runtime
   differences before interpreting percentage deltas.
3. Investigate a material or repeated regression, including changes outside
   the modified test's name. Do not treat an arbitrary 10% difference on a
   changing GitHub-hosted runner as automatic evidence of a code regression.
4. For Ganak/GPMC invocation, subprocess startup, I/O, precision validation
   and other external-solver-heavy paths, CodSpeed Simulation omits or
   underrepresents substantial syscall/walltime cost. When those paths may
   have changed, use an additional same-host, fixed-toolchain Walltime A/B
   with warm-ups, repeated and alternated base/candidate runs (for example,
   ABBA), consistent solver binaries and input circuits.
5. Before merging, record the finding: no substantiated regression within
   measured scope, an investigated fix, or an explicitly acknowledged
   trade-off with benchmark evidence. If the baseline is absent or not
   comparable, say **unverified**, not **no regression**.

Changes limited to documentation, release notes or unrelated metadata do not
need a CodSpeed run. We deliberately do **not** make a noisy 10% CodSpeed
threshold a branch-protection rule. The protected `main` branch instead
requires its independent `Release-Ready / Required` acceptance check.

## Reproducibility

Record the circuit/strategy/solver/backend combinations, exact commit SHAs,
Python/Rust environment, runner CPU, CodSpeed mode, and sources of skipped
tests. Do not compare CodSpeed Simulation modeled CPU time with Walltime
seconds as if they were the same metric. Preserve historical baselines when
benchmark coverage, solver versions or measurement environments change.
