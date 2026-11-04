# QOO-13 — Mac mini WallTime environment diagnostics (read-only)

## Verified scope

- CodSpeed A1: `PhysicsQoo/QuPRS`, commit `79e975b0b21c0c650db7a76fe6e35b926c67c2c8`, `local`, WallTime benchmark `vqe4_gpmc-head`, official minimum `576.188 ms`, **one measured round**. Official issue: `CallgraphGenerationFailure (info)`; no flamegraph. **This is not an A/A repeatability result.**
- GPMC arithmetic precision: `PRECISION_UNVERIFIED`, as previously reported.
- Previous A/A trial stopped after A1, before A2, because `backupd` reached ~104.9% CPU. Its existing `576.19 ms` A1 must not be combined with an earlier `593.73 ms` single-upload smoke to claim A/A statistics.
- Actual local warning observed: `[ERROR] instrument-hooks: failed to write environment.json` and `RuntimeWarning: Failed to write environment data`. The underlying path and errno were not captured, so **root cause remains unverified**. The official WallTime upload is complete, but auxiliary environment metadata may be incomplete.
- On a separate 30-second read-only Mac sample (7 snapshots), `backupd=0%`, but CPU idle was 40.36%–61.89%, **3/7 samples below the 50% preflight stop threshold**. Swap-in increased 484 pages (7.562 MiB, about 0.252 MiB/s), swap-out was zero. The `pmset -g therm` output only reported that no status had been recorded; **there was no usable thermal data**. No new A/A should be inferred from this sample.

## Run directly from the QuPRS experiment branch (Codex; no manual download)

This tool is maintained in the independent QuPRS experiment branch
`experiment/qoo13-macos-walltime-diagnostics-20261104`, not `dev` or `main`.
Ask Codex to fetch the branch (or check out a temporary worktree) and run the
commands from `experiments/qoo13/mac-walltime-diagnostics/` using an existing
local A/A evidence folder. Do not copy the script into a separate download location.
Do not modify or reset any dirty worktree.

```bash
# Example when Codex has already checked out the experiment branch:
cd experiments/qoo13/mac-walltime-diagnostics
python3 -m unittest -v test_qoo13_mac_diagnostics.py

# Replace this path with your existing A/A evidence directory.
EVIDENCE='/absolute/path/to/existing/aa.laizf603'
python3 qoo13_mac_diagnostics.py --scan-only --evidence "$EVIDENCE" \
  --output "$HOME/qoo13-p0-$(date +%Y%m%d-%H%M%S).json"
python3 qoo13_mac_diagnostics.py --duration 30 --interval 5 \
  --evidence "$EVIDENCE" \
  --output "$HOME/qoo13-p1-$(date +%Y%m%d-%H%M%S).json"
```

The evidence path is mandatory, so no personal project paths are embedded in this
public research branch. Codex can find the existing evidence folder on the Mac;
the assistant's cloud sandbox cannot access it.

The `--evidence` path must point to the existing `aa.laizf603` evidence folder. It does **not** invoke macOS commands, benchmark, CodSpeed, GitHub or any API. It reads at most 60 candidate files and up to 768 KiB each from the head and tail of each large log; when the scanner skips middle bytes or reaches limits, `partial_scan=true`. It never overwrites an existing output. Review all redacted excerpts **before** forwarding them (redaction is best effort).

Look for `evidence_scan.codspeed_environment_write=ERROR_OBSERVED_CAUSE_UNDETERMINED` and the exact warning excerpts. The warning confirms a write failure but does **not** identify the actual directory or errno.

### Source-pinned investigation: the two log messages ARE the same native write path

The `pytest-codspeed v5.0.3` Git tree pins the `instrument-hooks` submodule at **[`b9ddb5bc654b2e6fa13eb18efcd3a45e7ecda0bb`](https://github.com/CodSpeedHQ/instrument-hooks/blob/b9ddb5bc654b2e6fa13eb18efcd3a45e7ecda0bb/src/environment/root.zig)** (verified via the `v5.0.3` Git tree, not an assumption based on current upstream `main`). The pinned `Environment.writeEnvironment(pid)` constructs `$CODSPEED_PROFILE_FOLDER/environment-<pid>.json` in a 512-byte path buffer and then invokes `fs.createFileAbsolute(path)` followed by `file.writeAll(json)`.

**Both** the create and write failure branches emit the same literal message `instrument-hooks: failed to write environment.json`; thus the suffix in the log is a **generic logger message**, not the literal on-disk filename. Path-buffer overflow and serialization failure use **different** messages. The exact logged failure narrows the failure to **file creation or file content write**, but without an OS error/path in the historical log it **cannot select between those two branches or establish why it failed**. This reasoning assumes the installed 5.0.3 native library matches the documented source; the historical binary itself has not been inspected.

CodSpeed CLI [v5.4.2 profile-folder implementation](https://github.com/CodSpeedHQ/codspeed/blob/v5.4.2/src/executor/helpers/profile_folder.rs) creates a temporary directory with `std::fs::create_dir_all`; its injected environment supplies `CODSPEED_PROFILE_FOLDER`. This makes an initially absent folder less likely for a successfully completed local run but does **not** rule out a wrong resolved path, a runtime write/access failure, or later folder lifecycle changes.

The v4 scanner now reports `evidence_scan.native_environment_write_triage.status=NATIVE_CREATE_OR_WRITE_FAILED_STAGE_UNDETERMINED` with source version and explicit uncertainty. No fresh CodSpeed measurement or filesystem write is required to produce this mapping.

**Optional existing profile directory inspection (never creates/writes):**

```bash
python3 qoo13_mac_diagnostics.py --scan-only --evidence "$EVIDENCE" \
  --profile-folder '/path/to/preserved/codspeed-profile-folder' \
  --output "$HOME/qoo13-profile-$(date +%Y%m%d-%H%M%S).json"
```

The optional `codspeed_profile_folder` report includes existing `environment.json` and `environment-<pid>.json` filenames, sizes and JSON top-level keys only. Missing files or a missing profile directory **do not by themselves establish why the old write failed**. Never invent a path from a warning that did not print one. Do not rerun CodSpeed simply to chase an auxiliary metadata warning.

### P1: Observe a quiet period without running any benchmark

Use the second command in the experiment-branch example above.

The sampler calls read-only commands including `vm_stat`, `ps`, `top`, `sysctl -n vm.swapusage`, `memory_pressure -Q`, and `pmset -g therm`. It records timestamps, CPU idle, top CPU-using processes, `backupd` CPU %, load averages, cumulative swap usage, *changes* in swap-in/out page counters over the observation window, and whether **numeric CPU-limit fields**, rather than only a successful `pmset` command or a “no status recorded” note, were observed. Unavailable OS measurements are reported as unavailable; even numeric CPU-limit fields **do not certify absence of thermal throttling**.

The v3 `sample_window` adds `min_cpu_idle_pct` and `cpu_idle_below_50_pct_count`. Its preflight status abstains if `backupd>100%` **or** any observed CPU idle is below 50%. The 50% threshold is a conservative screening heuristic from this pilot, not proof of a stable CPU or a calibrated performance threshold.

`sample_window.contention_preflight` reports a reason to abstain if `backupd` exceeds 100% CPU or any sampled CPU idle is below 50%, but **does not certify a quiet machine** when neither is observed. A single process using 100% of one CPU is not the same as the entire 8-core Mac being fully loaded.

### Offline self-tests (optional)

```bash
python3 -m unittest -v test_qoo13_mac_diagnostics.py
```

The tests use synthetic log files and mock sampled counters. They do not use the network or launch CodSpeed. The thirteen tests have been tested in a Linux container; this **does not** constitute macOS runtime validation.

## P1: offline screening of an EXISTING Mac observation report

P0 historical environment-write diagnostics have concluded:
`ROOT_CAUSE_NOT_RECOVERABLE_FROM_EXISTING_LOGS`. No more P0 probing or
CodSpeed runs are authorized merely to obtain a clearer error message.

For P1, use [P1_ADMISSION.md](P1_ADMISSION.md) and the standalone
`qoo13_p1_admission.py`. It reads an **existing** `p1-monitor.json`,
does not gather new samples, and never launches CodSpeed or a solver.
The synthetic offline tests are in `test_qoo13_p1_admission.py`.

```bash
python3 -m unittest -v test_qoo13_mac_diagnostics.py test_qoo13_p1_admission.py
python3 qoo13_p1_admission.py --input '/existing/p1-monitor.json' \
  --output '/separate/directory/qoo13-p1-assessment.json'
```

The hardened P1 evaluator rejects NaN/Infinity, inconsistent monitor summaries,
invalid process telemetry, mismatched swap page sizes, and assessment output
inside the original evidence directory. These are **fail-closed evidence-quality
checks**, not new measured performance thresholds. P0 + P1 now have 27
synthetic offline tests in total; the P0 diagnostic source itself is unchanged.

The previously reported 7-sample Mac pilot (3 CPU idle samples below 50%)
must classify `ABSTAIN`, even though `backupd` was idle. A passing
observation window is at most a `QUIET_CANDIDATE_ONLY_NOT_CERTIFIED`, **not**
permission to run A/A or ABBA. Thermal absence is never a certificate of
normal operation. Preserve `PERFORMANCE_UNQUALIFIED / PRECISION_UNVERIFIED`.

## Stop conditions and next scientific step

Do not rerun the old A1, or perform ABBA, to patch missing A2–A4. Only after reviewing the actual metadata warning and observing a naturally quiet host should a **new independent** A/A session be considered, using the exact same source, QASM, solver, precision, extension and instrument, with a maximum of four separate CodSpeed samples and no existing-sample reuse. Keep `PERFORMANCE_UNQUALIFIED` until sufficiently stable independent data exist.
