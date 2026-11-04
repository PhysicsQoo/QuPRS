# QOO-157 — original binary implication SCC audit against native GPMC EE

A bounded **source-only** double-entry audit of original four QuPRS weighted
CNFs. From source DIMACS binary clauses `(a ∨ b)`, construct implications
`¬a→b` and `¬b→a`. Compute strongly connected components on the
2n-literal graph, group variables equivalent modulo negation, count how many
could be merged by binary-only literal equivalence, and how many source-weighted
variables occur in nontrivial groups.

For QAOA7/QFT16 only, compare independent source SCC reduction count with
source-identical [GPMC verbose native EE-stage](GPMC_NATIVE_STAGE_TRACE.md)
at the same pinned source CNF SHA, **without running or modifying solvers**.
Exact agreement provides a strong mechanism hypothesis; it does not by
itself prove per-variable native mapping, WMC arithmetic precision, or the
complete causal source of GPMC-versus-d4 performance.

CI is zero-build, reuses original archived source CNFs and immutable native
trace, and performs **no performance measurement**. Do not use elapsed CI
time for ranking. Coupled native and source evidence can guide future
weight-preserving binary-equivalence preprocessor experiments, but no solver
replacement is approved by this audit.
