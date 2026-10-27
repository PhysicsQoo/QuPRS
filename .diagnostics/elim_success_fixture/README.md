# Synthetic success/failure Elim factorial experiment

Standalone scientific fixture, defined under Rust `#[cfg(test)]`, using the
**existing** `try_reduce_elim` implementation and the opt-in Stage Ledger +
single-Elim timing guards. This is not a production scheduler change.

For each combination K=1/2/4/8, D=8/16/32 and monomial degree=1/2/4,
generate a synthetic PathSum with V=64 active internal variables and
L=D×degree. Compare:

- failed Elim: all K candidate IDs occur within phase monomials;
- successful Elim: one candidate no longer appears in phase, replaced by
  another still-active noncandidate ID, so Elim removes exactly one variable.

Each pair has identical K/L/V/D, and the same monomial length distribution.
There are 36 independent matched designs, each with two outcomes and 24
randomly ordered, in-process measurements (1728 total raw records). The
synthetic fixture calls `try_reduce_elim(&candidates)` directly and **does
not include** candidate discovery, HH/Omega or realistic circuit generation.

The scoped workflow runs an optimized Rust test on one GitHub Actions
Ubuntu CPU, captures all original stdout, independently validates sample
counts, K/L/V/D/W and success/removal invariants, and archives a JSONL,
factor-level medians, environment, SHA256 manifest and raw test log. Failures
are explicitly INCOMPLETE and do not masquerade as positive performance data.

The timed rule body excludes feature snapshot computation, but includes
`Instant` and RAII measurement overhead. Cache and clock granularity can
dominate very short operations, so this microbenchmark can test qualitative
work scaling but cannot prove causal runtime savings in real circuits. V
is fixed, but L and D are mathematically related by the chosen degree;
avoid claiming independent regression coefficients without identifiability
analysis. A later experiment should separately measure candidate discovery,
HH and Omega before proposing a unified Reduction Cost Model.
