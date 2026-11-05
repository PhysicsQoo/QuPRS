# Incremental CI evidence reuse

The shared `.github/scripts/ci-impact-reuse.cjs` source classifier and its
regression tests in `.github/scripts/test-ci-impact-reuse.cjs` determine whether
an affected pull-request workflow must run its costly jobs again.

Prior evidence is reusable **only** when the previous workflow was successful,
the PR has the same base SHA, the prior measured HEAD is an ancestor of the
current HEAD (or identical), and all changes since that measurement are in
the narrow non-executable Markdown allowlist. Missing jobs, skipped required
checks, inaccessible run metadata, untrusted diff history, source or fixture
changes, solver gitlinks, lockfiles, benchmark files and workflow-policy
changes invalidate reuse and fail conservatively to a full run.

The inexpensive impact job records `run_heavy`, `reused_run_id` and
`measured_head_sha`. If expensive jobs are skipped, **the new commit has
not received new benchmark measurements**: downstream reports must cite the
original source-qualified run, not relabel old values with the new SHA.

The classifier is used by source-sensitive CodSpeed, Dev Fast, native,
Docker, WMC, Solver Conformance and QASM guard workflows. Their current
triggers and required job inventories are defined by their own
`.github/workflows/` files; do not assume all workflows run on every PR.
A cumulative three-dot PR diff alone cannot distinguish docs-only HEAD
changes after code has already been verified.

Release acceptance (`dev` to `main`) remains independent. PR evidence
reuse does **not** bypass source compatibility, release artifacts, wheel
or sdist installation, or tagged publication checks.

When changing the impact policy, test positive same-base Markdown-only reuse
and negative cases for code, QASM/JSON, benchmarks, workflows, missing
evidence, fork/base changes and failed required jobs. Never whitelist
entire research or test directories solely to avoid CI cost.
