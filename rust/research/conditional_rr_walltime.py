"""Bounded, paired release-build native pipeline WallTime pilot.

Timing emitted by the Rust harness excludes cargo/test process startup but
includes QASM file reads, parse, independently executed native RR, admission,
encoding, external GPMC and classification. Never count censored pairs as speedup.
"""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
cases = {x["id"]: x for x in json.loads(
    (ROOT / "docs/development/paper-corpus-manifest.json").read_text()
)["cohorts"]["table2_mqt"]["cases"]}
# Fixed selection; 4 balanced repetitions for short cases, 2 for longer
# controls and QFT20. QFT24 is a single bounded censor probe, not a ratio.
COHORT = (
    ("qft_16", 4, 12), ("qft_20", 2, 60), ("qft_24", 1, 12),
    ("qpeexact_16", 4, 12), ("qpeexact_20", 4, 12),
    ("qpeinexact_20", 4, 12), ("qwalk-noancilla_4", 4, 12),
    ("wstate_8", 4, 12), ("vqe_8", 4, 12),
    ("grover-noancilla_5", 2, 12), ("qnn_8", 2, 12),
    ("ghz_32", 4, 12), ("graphstate_16", 4, 12),
)
failed = False
for case_id, repeats, solver_secs in COHORT:
    files, hashes = {}, {}
    for side in ("source", "transpiled"):
        entry = cases[case_id][side]
        p = ROOT / entry["path"]
        data = p.read_bytes()
        assert hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == entry["git_blob_sha1"]
        files[side] = str(p)
        hashes[side] = hashlib.sha256(data).hexdigest()
    paired = []
    for repeat in range(repeats):
        env = dict(os.environ, CRR_CASE=case_id, CRR_SOURCE=files["source"],
                   CRR_TARGET=files["transpiled"], CRR_REPEAT=str(repeat),
                   CRR_SOLVER_SECS=str(solver_secs))
        process_secs = 2 * (20 + solver_secs) + 25
        cmd = ["timeout", "--kill-after=3s", f"{process_secs}s", "cargo", "test",
               "--release", "--locked", "--manifest-path", "rust/Cargo.toml",
               "-p", "quprs", "--test", "conditional_rr_experiment",
               "conditional_trace::native_full_pipeline_paired", "--", "--exact", "--nocapture"]
        run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        records = [x for x in run.stdout.splitlines() if x.startswith("CRR_FULL_")]
        calls = [dict(t.split("=", 1) for t in x.split() if "=" in t)
                 for x in records if x.startswith("CRR_FULL_CALL ")]
        comp = [x for x in records if x.startswith("CRR_FULL_COMPARE ")]
        if run.returncode in (124, 137):
            status = "PROCESS_TIMEOUT"
        elif run.returncode or len(calls) != 2 or len(comp) != 1 or {c["arm"] for c in calls} != {"baseline", "lazy"}:
            status = "ERROR"
        elif all(c["status"] == "complete" for c in calls) and "status=matched " in comp[0]:
            status = "MATCHED"
        elif any(c["status"] != "complete" for c in calls) and "status=incomplete" in comp[0]:
            status = "INCOMPLETE"
        else:
            status = "ERROR"
        failed |= status == "ERROR"
        row = dict(case=case_id, repeat=repeat, order="AB" if repeat % 2 == 0 else "BA",
                   status=status, sha256=hashes, solver_secs=solver_secs,
                   process_secs=process_secs, returncode=run.returncode, records=records,
                   stderr=run.stderr[-3000:])
        print(json.dumps(row), flush=True)
        paired.append((status, calls))
    stats = {}
    for arm in ("baseline", "lazy"):
        entries = [c for _, calls in paired for c in calls if c["arm"] == arm and c["status"] == "complete"]
        values = [float(c["total_s"]) for c in entries]
        stats[arm] = dict(n=len(values), median_s=statistics.median(values) if values else None,
                          min_s=min(values) if values else None, max_s=max(values) if values else None,
                          solver_calls=sum(c.get("solver") == "true" for c in entries))
    matched = sum(st == "MATCHED" for st, _ in paired)
    print(json.dumps(dict(summary_case=case_id, scope="native_release_qasm_to_verdict",
                          planned_repeats=repeats, matched_repeats=matched,
                          statuses=[st for st, _ in paired], total_stats=stats,
                          median_total_ratio=(stats["baseline"]["median_s"] / stats["lazy"]["median_s"]
                                              if matched == repeats else None))), flush=True)
if failed:
    raise SystemExit(1)
