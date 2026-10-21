# Same-host Rust structural counter A/B/C (non-blocking research)

This separate source-pinned experiment does **not** alter production Rust
Reduction, solver selection, timeouts, numerical thresholds, or the required
CI gate. The workflow runs only for this diagnostic PR path or a manual
dispatch. GitHub Actions must run on **the same host in one job**; never
compare an unrelated release runner to another week's hosted-runner baseline.

- A: pinned `dev@e84f909b08e42872421a4a0b5835c44faf812384`, original
  PR #56 stage ledger, flag off.
- B: pinned `dev@8ce78bd95e9548a4efcdb17852c7b882a5ca2ce1`, after
  PR #57 Structural Counters, flag off.
- C: same **identical binary as B**, flag `QUPRS_STAGE_LEDGER=1`.

The fixed workload is the repository's two official MQTBench QASM pairs:
QAOA7 and QFT16, from `benchmarks/MQTBench` and its `h,ry,rz,cx`
subdirectory. QFT16 uses the reversed input order (as in
`test/test_MQT.py`). All groups use Rust-native `hybrid`,
`Proportional`, **one shared exact GPMC executable**, 60-second native
solver timeout and a 90-second outer hard timeout. Both separate Python
3.12 virtual environments have identical frozen runtime dependencies,
and A and B are compiled at the beginning of this same CI job.

For each case, warm up each group in three interleaved triplets and take
at least **30 valid fresh measurements per group**. The order of A/B/C
within each triplet is deterministically randomized, each sample uses
an independent Python process, and the entire experiment and GPMC solver
share a single permitted CPU using Linux affinity. There are **no automatic
performance regression cutoffs**. Invalid results, crashes or timeouts
fail closed, retaining original JSON and logs.

Measured fields:
- `ffi_wrapper_wall_seconds` measures the single Rust FFI call only.
  Qiskit import, QASM loading and Python startup are outside this timer.
- `native_total_seconds` uses Rust's built-in verification wall clock.
- `native_pathsum_seconds` measures the preexisting PathSum strategy
  interval, **not exclusive Reduction**.
- Only C yields `stage_ledger.exclusive_seconds.reduction`, the aggregate
  outermost (non-double-counted) Reduction time and the per-attempt
  `K/L/V/D/W_redundant_estimated` structural samples.

`B/A` estimates default-off overhead and `C/B` estimates diagnostic-on
overhead, conditional on this shared-host experiment. Raw per-run samples,
per-round paired ratios, seed, provenance, checksums and bootstrap
descriptive intervals are preserved. The paired bootstrap does **not**
remove clock/CPU jitter and is **not evidence of hardware-independent
causality or statistical equivalence**.

**Scientific limitation:** The existing Stage Ledger does not provide
per-Elim times. Two fixed input families also provide at most two
independent structural workloads (repeated trials are not new cost
structures). Thus the experiment can report aggregate reduction-time
and structural-work proxies but **cannot fit or validate a predictive
Reduction Cost Model**. Never regress 60 repeats as 60 structurally
independent observations. Additional distinct circuits and rule-level
exclusive timing require a separate reviewed project stage.

Run through `.github/workflows/rust-structural-cost-abc.yml`;
the original raw evidence and SHA256SUMS manifest are uploaded as a
non-public GitHub Actions artifact associated with the PR. Project
planning in Linear remains private and must not appear in public PRs.
