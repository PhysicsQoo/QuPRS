# TACAS 2026 Artifact CI reproduction and WMC numerical evidence contract

Status: **HISTORICAL_REPRODUCTION_QUALIFIED; NUMERIC_ARCHIVE_IN_PROGRESS**.
Scope: **original QuPRS v0.9.1 and bundled GPMC only**, never a performance
comparison against contemporary dev/PR #131 or external verifiers.

## Primary purpose (in priority order)

1. **Demonstrate whether the original TACAS Artifact is reproducible in CI**
   using original QuPRS v0.9.1 (`e928abc47dd15926364ec77905eb0d5dc92ce8cc`),
   original paper artifact (`d8d3e7da555e9e20bdec6f3abe4a13ad899af62b`),
   pinned benchmark QASM and original GPMC executable SHA256.
   Label scientific verdicts, Solver Timeout vs watchdog censoring,
   `MemoryOut`, missing output, and actual CI environment.
   The observed 184-call cohort is **SUBSTANTIALLY_REPRODUCED**; it is not
   necessary to force all 184 cases to finish. The 37 positive RR cells
   are derived from those same Hybrid invocations, not extra calls.
2. **Permanently preserve the original WMC numerical outputs**, not merely
   the final equivalence labels. The raw text and numerical interpretation
   will be used as a frozen reference for future work on separate
   RR, phase and distance tolerance APIs.
3. **Evaluate classifier hypotheses offline**, without recomputing the
   original circuits or modifying the original Solver. Comparisons to
   modern v0.14.0 need separate mathematical justification and should not
   be described as equivalent to an original v0.9.1 decision.
4. **Optional**: dedicated historical CodSpeed WallTime study only if
   historical performance becomes a separate goal. CodSpeed is not a
   prerequisite to (1)-(3). Existing modern performance results must not
   be mixed into the original paper dataset.

## Frozen numerical evidence

The authoritative Git archive consists of:

- `tacas26-results/results.json`: full raw evidence, repeated calls,
  original `solver_calls[].stdout` / `stderr`, original parsed
  `complex_counts[]` and source/GPMC/input hashes.
- `tacas26-results/wmc-evidence.csv`: 184 case-indexed records with
  original scientific verdicts and GPMC printed real/imag values, raw
  `c s exact double prec-sci` line, original binary64 converted values,
  `expected_log2`, `rounded_log2`, `raw_log2_abs_wmc`,
  `original_phase_rad`, and `v091_replayed_verdict`.
- `tacas26-results/wmc-evidence.json`: the above plus the original
  GPMC calls, full stdout/stderr and all recorded complex-count values.
- `tacas26-results/results.csv`: case verdicts, QuPRS method,
  historical paper reference seconds and *explicitly missing* newer
  CI execution-stage times.
- `tacas26-results/derived_rr.csv`: same-Hybrid-derived RR column.

The source-only extractor `scripts/tacas26_wmc_evidence.py` consumes the
already committed `results.json`. It **never runs GPMC or CodSpeed**.
The opt-in archive CI regenerates all data deterministically from the
previously archived Actions results.

Important: the raw GPMC output format `-mode=1` is
`c s exact double prec-sci`. This label and printed decimal digits
do **not** certify higher-precision mathematical values or error bounds.
The source v0.9.1 subsequently calls Python `float` on real and
imaginary components, uses `round(log2(abs(WMC)), 3)`,
compares to the expected logarithm with historical global tolerance
`1e-10`, and examines global phase. Keep **three separate fields**:
original decimal stdout, parsed float64, and derived old-classifier
quantities. Never overwrite the raw decimal strings with recomputed
higher-precision-looking values or pretend that digits beyond the output
precision were measured.

If the experiment terminated during RR, never report a WMC value.
If the source timed out, or watchdog killed the process, retain whatever
partial stdout was actually captured and mark count fields missing.
`null` is not zero and is not sufficient to classify an equivalent
circuit. Do not infer precision or phase from a `Timeout` label.

## Future tolerance research

For a candidate numerical policy, create a **separate offline replay**
dataset keyed to original `id`, historical source SHA, input hashes,
GPMC binary hash, stdout SHA and original solver mode. Each replay must
record candidate phase/distance tolerances, normalization assumptions,
rounding rules, precision of input evidence, decision, and uncertainty.

Only compare alternative decision policies at the precision supported
by the saved GPMC decimal output. Cases where a candidate decision lies
inside a plausible printing/rounding uncertainty band are
`INDETERMINATE_FROM_HISTORICAL_OUTPUT`, **not** numerical evidence of
the candidate policy's correctness or failure. A projective distance
`sqrt(1 - |Tr(U†V)|² / 4^n)` must not be computed from a raw WMC
count without independently validating the PathSum/CNF count-to-trace
normalization and phase conventions.

A future high-precision diagnostic may selectively recompute a few
boundary cases with independently justified precision (e.g. MPFR),
but its results must be stored under a **new source/solver/precision**
identity rather than altering the v0.9.1 evidence.

## CI acceptance and resource limits

Archive verification should test canonical 184 original-call identities,
37 derived RR identities, raw-output source provenance, no duplicated
case IDs, exact printed digits, no fabricated values, and preserved
watchdog/Timeout distinctions. A majority of original published
verdicts has been reproduced; partial scientifically censored cases
remain evidence with explicit limitations.

The original QuPRS `timeout=200` controls scientific verification.
The external 215-second process-group watchdog is a separate safety
measure. Neither is CodSpeed measurement scheduling. Do not resubmit
all 184 cases simply to fill missing elapsed-time columns; historic
performance and source numerical evidence are separate concerns.

**Success is a preserved and replayable scientific reference corpus,
not a modern speedup percentage or full completion of every hard case.**
