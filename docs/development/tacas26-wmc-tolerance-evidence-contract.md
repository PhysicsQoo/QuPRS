# TACAS 2026 Artifact CI reproduction and WMC numerical evidence contract

Status: **HISTORICAL_REPRODUCTION_QUALIFIED; NUMERIC_ARCHIVE_IN_PROGRESS**.
Scope: **original QuPRS v0.9.1 and bundled GPMC only**, never a performance
comparison against contemporary dev/PR #131 or external verifiers.

## Primary tolerance acceptance: binary equivalence boundary (2026-11-02)

**Primary question:** which v0.14.0 `approximate_distance_tolerance`
reproduces the TACAS paper's **equivalent OR equivalent*** versus
**not_equivalent** classifications? A transition between
`equivalent` and `equivalent*` is a *secondary phase-label diagnostic*,
not a failure of the primary compatibility goal. This is independent
of optimizing runtime or reproducing historical wall-clock timing.

A reproducible offline scanner is
`scripts/tacas26_tolerance_replay.py`. It consumes the Git-tracked
`wmc-evidence.json` (101 captured, determinate original GPMC complex
counts) and uses exact-rational squared magnitude comparison matching
the v0.14.0 printed-count classifier. It does **not** execute either
v0.9.1 or v0.14.0, nor change current production settings.

The observed candidate is
`approximate_distance_tolerance=2e-5`, with **101/101 binary
historical-label matches** on the same original printed counts, versus
**79/101** at the contemporary default `1e-8`. The required
historical *printed-count* numerical window is approximately

`1.37729954e-5 <= epsilon < 0.24656716`.

The lower edge is the maximum accepted original
`table2:qpeinexact24:positive:hybrid` distance estimate;
the upper edge is the minimum rejected
`table3_negative:qaoa11:negative:hybrid` estimate.
The conservative working candidate `2e-5` is chosen to exceed the
observed positive edge without approaching the negative edge;
these values are **not certified Solver error bounds**.

**Do not turn the 101/101 printed-count replay into a claim of full
v0.14.0 reproduction.** There are 83 other direct calls with no
replayable WMC count, some resolved by RR and some censored or missing.
The current v0.14.0 pipeline can change RR, PathSum/CNF construction,
weight precision and WMC output. Next, independently verify the
difficult original positive cases and smallest-distance negative cases
using the same paper QASM with a pinned v0.14.0 backend and unchanged
200-second scientific limit. Track *binary verdict only* as the main
pass/fail outcome. In the new tests explicitly distinguish RR-only,
RR-terminated Hybrid, WMC-entered Hybrid, and WMC-only. Test both Python
and Rust when feasible, with a separate source-run provenance record.

The old classifier rounded `log2(|WMC|)` to three decimal places
before applying its `1e-10` comparison. A worst-case accepted
normalized magnitude deficit within a half-unit of that decimal
rounding corresponds to an idealized distance of roughly `0.0263`,
not `1e-10`. This is a *coarse theoretical legacy decision bound*;
the observed corpus instead has its much smaller `1.38e-5` positive
edge. Neither bound justifies a universal modern default change,
especially given independently known circuit-equivalence safety goals.

The original small negative-angle phase near `2*pi` caused five
`equivalent*` versus `equivalent` label differences after
modern phase wrapping. **These are not binary verdict failures.**
Do not recreate the old phase-label issue merely to make exact
three-label matches. For binary classification, vary distance tolerance
and treat phase tolerance as independent metadata.

Store results under
`tacas26-results/tolerance-offline-v0140/` with two separate scores:
`binary_match` (**primary**) and `exact_match` (**secondary**).
Use `.github/workflows/tacas26-binary-calibration.yml` to regenerate
the offline sweep directly from **Git-committed data** with no Artifacts
download and no Solver invocation; this avoids the previously observed
external HTTP 503 artifact-egress limitation.

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
