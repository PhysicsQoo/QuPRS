# QOO-13 — Codex Mac handoff (P1 archived-monitor admission)

**Scope: one read-only evaluation of existing Mac pilot evidence.** P0 metadata
forensics are concluded: `ROOT_CAUSE_NOT_RECOVERABLE_FROM_EXISTING_LOGS`.
Do not restart P0 or use CodSpeed just to create a new errno.

## Source of truth

- Linear: https://linear.app/qoogohome/issue/QOO-13/codspeed-simulation-baseline-runner-stability-and-workflow-triggers
- Repo: `PhysicsQoo/QuPRS`.
- Branch: `experiment/qoo13-macos-walltime-diagnostics-20261104`.
- Reviewed P1 source/test/doc state: `f9d4a0eb4e9c1a0b97f71549ddf9116baf7ab388`. This is
  the revision containing the verified 27 synthetic tests; this handoff
  document was committed afterward. Read Linear's most recent pinned HEAD for
  the overall branch state.
- Primary files: `qoo13_mac_diagnostics.py` (P0 v4; 13 tests, previously
  Mac-verified), `qoo13_p1_admission.py` (P1 standalone read-only evaluator;
  14 synthetic tests), `test_qoo13_mac_diagnostics.py`,
  `test_qoo13_p1_admission.py`, `P1_ADMISSION.md`.
- Previously saved Mac P1 pilot evidence: the **existing**
  `qoo13-diagnostics/p1-monitor.json` under the Codex project's
  `deliverables` directory. Locate and inspect it; **do not invent or
  regenerate** it.

## Step 1: verify Mac worktree and offline tests

Use the **existing isolated experiment worktree**. Verify its clean status
before switching; preserve the dirty primary `main` worktree. Fetch the
branch and pin the checkout to the exact HEAD recorded in Linear; reject a
mismatch rather than silently resetting. No build or package installation.

Run from `experiments/qoo13/mac-walltime-diagnostics/`:

```bash
python3 -m unittest -v test_qoo13_mac_diagnostics.py test_qoo13_p1_admission.py
```

Expect **27 tests**. Save its real stdout/stderr and the worktree SHA in a
new evidence directory, not in the source evidence directory.

## Step 2: evaluate only the existing Mac P1 JSON

Confirm the actual input file and hash, then run:

```bash
python3 qoo13_p1_admission.py \
  --input "$P1_MONITOR_JSON" \
  --output "$NEW_EVIDENCE_DIR/admission.json"
```

Requirements: `P1_MONITOR_JSON` must be a verified existing regular
`p1-monitor.json`; `NEW_EVIDENCE_DIR` must be entirely outside the input's
parent directory and must not exist as an old report target. The evaluator
does not execute host commands or benchmarks.

Check: `input_sha256`, `sample_count`, `sample_span_seconds`,
`verdict`, `stop_reasons`, `evidence_gaps`, `observations`,
`thermal_certified=false`, `authorizes_benchmark=false`,
`PERFORMANCE_UNQUALIFIED`, and `PRECISION_UNVERIFIED`.

Known pilot facts: 30 s, 7 samples, 3 samples with CPU idle below 50%,
`backupd=0%`, swap-in 484 pages (7.562 MiB) and no swap-out; thermal
telemetry was unavailable. Thus **expect** `ABSTAIN` including
`CPU_IDLE_BELOW_50_PCT`. If the result differs, check input identity/schema
first and investigate truthfully; never revise thresholds to obtain a
quiet-looking outcome.

## Step 3: preserve evidence and update one Linear Issue

Create an independent `findings.md` describing whether the existing file
was accepted, actual sample span/count, all stop/gap statuses, and whether
the tool behaved as expected. Keep the original JSON untouched; record the
new report's SHA-256 and the exact Git SHA. Update **existing QOO-13**,
do not create duplicate issues.

When the real pilot is `ABSTAIN`, mark P1 archival-data screening complete
but **Mac runner admission NOT_MET**. Do not schedule or perform A/A or ABBA.
A later naturally quiet window is a separate experiment decision, not a
retroactive amendment of this pilot.

## Hard prohibitions

No CodSpeed run/upload, no GPMC or QuPRS solver, no new macOS monitoring,
no Rust wheel rebuild, no fresh A/A/ABBA or other performance tests.
Do not stop `backupd`, adjust CPU/thermal settings, touch dirty
`main`, change `dev`, merge or modify formal GitHub workflows.
Never claim numerical precision certified or quote 576.188 ms as an A/A
stability result. If the existing input is inaccessible, report the
blocker and stop rather than fabricating it.
