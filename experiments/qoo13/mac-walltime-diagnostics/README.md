# QOO-13 — Mac mini WallTime environment diagnostics (read-only)

## Verified scope

- CodSpeed A1: `PhysicsQoo/QuPRS`, commit `79e975b0b21c0c650db7a76fe6e35b926c67c2c8`, `local`, WallTime benchmark `vqe4_gpmc-head`, official minimum `576.188 ms`, **one measured round**. Official issue: `CallgraphGenerationFailure (info)`; no flamegraph. **This is not an A/A repeatability result.**
- GPMC arithmetic precision: `PRECISION_UNVERIFIED`, as previously reported.
- Previous A/A trial stopped after A1, before A2, because `backupd` reached ~104.9% CPU. Its existing `576.19 ms` A1 must not be combined with an earlier `593.73 ms` single-upload smoke to claim A/A statistics.
- Exact local CodSpeed **environment metadata warning** has not been supplied. The official platform exposes successful WallTime, but this does not prove every local auxiliary metadata file was written.

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

Find the `evidence_scan.warnings` entries tagged `metadata_or_environment`, including the original failing file/path and error code if present. The root cause remains `UNVERIFIED` until a concrete local warning is inspected.

### P1: Observe a quiet period without running any benchmark

Use the second command in the experiment-branch example above.

The sampler calls read-only commands including `vm_stat`, `ps`, `top`, `sysctl -n vm.swapusage`, `memory_pressure -Q`, and `pmset -g therm`. It records timestamps, CPU idle, top CPU-using processes, `backupd` CPU %, load averages, cumulative swap usage, *changes* in swap-in/out page counters over the observation window, and whether thermal data were available. Unavailable OS measurements are reported as unavailable; they are **not** evidence that thermal throttling or contention is absent.

`sample_window.contention_preflight` reports a reason to abstain if `backupd` exceeds 100% CPU in a sample, but **does not certify a quiet machine** when it does not. A single process using 100% of one CPU is not the same as the entire 8-core Mac being fully loaded.

### Offline self-tests (optional)

```bash
python3 -m unittest -v test_qoo13_mac_diagnostics.py
```

The tests use synthetic log files and mock sampled counters. They do not use the network or launch CodSpeed. They have been tested in a Linux container; this **does not** constitute macOS runtime validation.

## Stop conditions and next scientific step

Do not rerun the old A1, or perform ABBA, to patch missing A2–A4. Only after reviewing the actual metadata warning and observing a naturally quiet host should a **new independent** A/A session be considered, using the exact same source, QASM, solver, precision, extension and instrument, with a maximum of four separate CodSpeed samples and no existing-sample reuse. Keep `PERFORMANCE_UNQUALIFIED` until sufficiently stable independent data exist.
