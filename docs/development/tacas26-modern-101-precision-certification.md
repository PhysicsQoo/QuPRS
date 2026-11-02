# TACAS 2026 — Modern QuPRS 101-case arithmetic certification contract

Scope: only `experiment/tacas26-paper-reproduction`. **Not** a production
verdict change, benchmark speed comparison, or formal PR #131 modification.

## Experiments, source identity, and evidence

- Original evidence: QuPRS v0.9.1 at
  `e928abc47dd15926364ec77905eb0d5dc92ce8cc`, original GPMC stdout,
  QASM SHA256 and source results in
  `docs/development/tacas26-results/wmc-evidence.json`.
- Precisely 101 comparable **actual source GPMC calls**: 45
  `equivalent|equivalent*`, 56 `not_equivalent`; 44 hybrid, 57 WMC-only.
  `Timeout`/`unknown`/`MemoryOut`/watchdog censoring is **not** evidence
  of `not_equivalent` or an acceptable binary match.
- Source-pinned modern `approximate_distance_tolerance=2e-5`,
  `rr_tolerance=1e-10`, `wmc_phase_tolerance=1e-8`, GPMC work/print
  digits 30; all original QASM pair hashes fixed.
- First complete test run: [Actions 41481701901](https://github.com/PhysicsQoo/QuPRS/actions/runs/41481701901),
  fixed SHA `ff4d3032a83c0ae18ba3a7d195cb1b1a8804492f`, 24 shards each
  for Python and Rust (202 modern calls).
- Independent precision convergence: [Actions 41482585459](https://github.com/PhysicsQoo/QuPRS/actions/runs/41482585459),
  fixed SHA `6b2b281c546e3369abb5061af74896bb50c48c3b`, Python GPMC
  90 digits on same 101 cases. Script, worker, historical archive have
  identical Git blob SHAs across these two science runs.
- The two workflows use isolated explicit push markers and do **not**
  run in formal PR CI or change QuPRS defaults. Neither can certify timing
  performance; only CodSpeed is acceptable for that purpose.

## Two independent mandatory gates

### Gate A — source-pinned binary reproducibility

A case passes only when a new actual QuPRS verifier returns determinate
`equivalent`, `equivalent*` or `not_equivalent`, and its binary EQ/NEQ
label exactly matches the archived original label. A passing job does
**not** mean the case passed: inspect the individual JSONL rows. Count
unique case IDs, backend identity, exact source SHA and input hashes,
method, output stage, normalized WMC value, precision provenance,
timeouts, and watchdog. Report separately Python and Rust totals and
concordance. Expected full run: 101 distinct cases × 2 backends.

### Gate B — **actual** solver arithmetic error certification

A parsed GPMC complex count and MPFR 30/90 digit agreements do **not**
provide a mathematical upper bound on accumulated Solver numerical
error. The GPMC output prefix `c s exact double prec-sci` is an output
format label, **not** a validated exact WMC certificate. In current
QuPRS `SolverCapabilities.exact_count_certificate=False`, and
`precision_count.classify_printed_distance` explicitly certifies
**printed decimal representation uncertainty only**.

For an intended true complex trace count `Z`, the normalized squared
magnitude decision compares against

```
M² = 2**(normalization_twice_log2)
T² = M² * (1 - epsilon**2)
|Z|² >= T²  => EQ magnitude region
|Z|² <  T²  => NEQ magnitude region
```

Let `C` be the parsed decimal complex point, `eta_r` and `eta_i`
its proven per-component formatting half-unit. The representation
error budget is `eta_print = hypot(eta_r, eta_i)`. A **conditional**
sufficient gap for the binary EQ/NEQ decision is

```
gap_count = abs(abs(C) - sqrt(T²)) - eta_print
```

provided `gap_count > 0` and an **independently certified**
`delta_solver_total < gap_count`. `delta_solver_total` must cover
input phase/weight error, cancellation, MPFR rounding accumulated across
CNF preprocessing/weighted model counting, normalization, and any
RR source-distance approximation. Merely increasing `-prec=90` does
not establish this upper bound. A verified proof must also justify
`PathSum -> CNF -> trace` identity and the relevant original source
QASM/angle fidelity.

Current source-pinned Python JSONL records:

- `observed_solver_calls[].cnf_sha256` (must match when comparing precisions);
- original GPMC printed decimal real/imaginary counts, `c o precision`
  header, and `stdout_sha256`;
- exact-rational representation interval and classification, plus
  conditional `gap_count` and normalized gap (calculated with high
  decimal precision, not a source-truth certificate);
- `solver_arithmetic_error_bound: null`,
  `solver_arithmetic_certificate: ABSENT`,
  `certified_solver_arithmetic: false`.

Rust internal GPMC stdout is not intercepted by this Python-only hook.
It supplies verifier numerical metadata and binary results; separate
verified Rust CNF/stdout provenance is necessary for a formal Rust error
certificate.

**Do not set `CERTIFIED` on any case until an independent interval /
exact-rational WMC of the same verified CNF, or a defensible proved GPMC
arithmetic error bound, supplies the actual `delta_solver_total`.**
If such a proof remains unavailable, state `NOT_CERTIFIED` in the final
report despite source binary agreement or 30/90 convergence.

## Scientific follow-up without editing GPMC or Ganak

1. Require a source-pinned, independently checkable CNF construction and
   normalization witness (including RR-final residual for Hybrid).
2. For hard near-boundary cases, use a validated exact-rational /
   directed-rounding interval WMC evaluator. An optional d-DNNF export
   is only an intermediate representation; its relation to the *original*
   CNF and any preprocessing global weight multiplier must be verified
   independently before using it as a proof.
3. Bound the source transcendental gate-weight evaluations; use certified
   interval endpoints rather than copying the 30- or 90-digit printout.
4. Prove end-to-end error budget and compare against each case's stored
   conditional allowable count error.
5. Refuse arithmetic certification if any required bound/source witness
   is missing, regardless of how many precision settings agree.

All research changes stay on the one experiment branch. Formal PR #131
remains Draft/unmerged; production tolerance and 32 legacy benchmark
identities are unchanged.
