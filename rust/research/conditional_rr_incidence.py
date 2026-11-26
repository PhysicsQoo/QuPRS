"""Source-locked CRR-0 pilot; each original pair receives a process timeout."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
IDS = ("grover-noancilla_4", "qwalk-noancilla_3", "qwalk-noancilla_4",
       "qpeexact_8", "wstate_4", "qnn_4", "vqe_4", "ghz_32")
EXPANDED_IDS = ("qft_16", "qft_20", "qpeexact_16", "qpeinexact_8",
                "qpeinexact_16", "qwalk-noancilla_5", "wstate_8", "wstate_16",
                "grover-noancilla_5", "qaoa_7", "qnn_8", "vqe_8", "graphstate_16")
manifest = json.loads((ROOT / "docs/development/paper-corpus-manifest.json").read_text())
cases = {x["id"]: x for x in manifest["cohorts"]["table2_mqt"]["cases"]}
failed = False
rows = []
import statistics
# Fixed cohort selected from CRR-2A before this run. Three cyclic
# orders balance each arm's position, not all six permutations.
REPEAT_IDS = ("qft_16", "qft_20", "qpeexact_16", "qpeinexact_16",
              "wstate_8", "grover-noancilla_5", "qnn_8", "vqe_8",
              "qaoa_7", "ghz_32")
for case_id, repeat in ((c, r) for c in REPEAT_IDS for r in range(3)):
    expanded = case_id in EXPANDED_IDS
    solver_secs = 60 if case_id == "qft_20" else 12
    process_secs = 210 if case_id == "qft_20" else 65
    case = cases[case_id]
    paths = {}
    hashes = {}
    for side in ("source", "transpiled"):
        entry = case[side]
        p = ROOT / entry["path"]
        data = p.read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        assert blob == entry["git_blob_sha1"], (case_id, side, blob)
        paths[side] = str(p)
        hashes[side] = hashlib.sha256(data).hexdigest()
    env = dict(os.environ, CRR_CASE=case_id, CRR_SOURCE=paths["source"],
               CRR_TARGET=paths["transpiled"])
    env["CRR_SOLVER_SECS"] = str(solver_secs)
    env["CRR_TRACE_ONLY"] = "1"
    env["CRR_REPEAT"] = str(repeat)
    cmd = ["timeout", "--kill-after=3s", f"{process_secs}s", "cargo", "test", "--locked",
           "--manifest-path", "rust/Cargo.toml", "-p", "quprs",
           "--test", "conditional_rr_experiment", "native_eq_residual_incidence",
           "--", "--exact", "--nocapture"]
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    records = [l for l in run.stdout.splitlines() if l.startswith("CRR_")]
    status = "COMPLETE" if run.returncode == 0 and sum(l.startswith("CRR_BASE ") for l in records) == 1 and sum(l.startswith(("CRR_INCIDENCE ", "CRR_SKIP ")) for l in records) == 1 else (
        "TIMEOUT" if run.returncode in (124, 137) else "ERROR")
    trace = [l for l in records if l.startswith("CRR_TRACE ")]
    compare = [l for l in records if l.startswith("CRR_COMPARE ")]
    calls = [l for l in records if l.startswith("CRR_GPMC ")]
    cnfs = [l for l in records if l.startswith("CRR_CNF ")]
    complete_calls = sum(" status=complete " in l for l in calls)
    # Process completion and solver evidence are separate. Never turn
    # an unsupported/censored case into a matched numerical result.
    if status != "COMPLETE":
        solver_status = "PROCESS_" + status
    elif not trace or any("status=unsupported" in l or "status=term_cap" in l for l in trace):
        solver_status = "NOT_ADMITTED"
    elif not os.environ.get("CRR_GPMC_COMPARE"):
        solver_status = "NOT_REQUESTED"
    elif len(compare) != 1 or len(calls) != 3 or len(cnfs) != 3:
        solver_status = "MISSING_EVIDENCE"
        status = "ERROR"
    elif "status=matched " in compare[0] and complete_calls == 3:
        solver_status = "MATCHED"
    elif "status=incomplete" in compare[0] and complete_calls < 3:
        solver_status = "INCOMPLETE"
    else:
        solver_status = "INCONSISTENT_EVIDENCE"
        status = "ERROR"
    failed |= status == "ERROR"
    row = dict(case=case_id, repeat=repeat, cohort="repeat_pilot",
                          status=status, solver_status=solver_status,
                          complete_calls=complete_calls, solver_secs=solver_secs,
                          process_secs=process_secs, returncode=run.returncode,
                          sha256=hashes, records=records,
                          stderr=run.stderr[-3000:], stdout_tail=run.stdout[-1500:])
    rows.append(row)
    print(json.dumps(row), flush=True)
# Explicitly retain all incomplete runs; summarize only completed calls,
# never turn censored baseline time into an exact speedup.
for case_id in REPEAT_IDS:
    group = [r for r in rows if r["case"] == case_id]
    by_arm = {a: [] for a in ("baseline", "conditioned", "iterated")}
    for row in group:
        for line in row["records"]:
            if line.startswith("CRR_GPMC "):
                fields = dict(t.split("=", 1) for t in line.split() if "=" in t)
                if fields["status"] == "complete":
                    by_arm[fields["arm"]].append(float(fields["call_s"]))
    stats = {a: dict(n=len(v), median_s=statistics.median(v) if v else None,
                     min_s=min(v) if v else None, max_s=max(v) if v else None)
             for a, v in by_arm.items()}
    matched = sum(r["solver_status"] == "MATCHED" for r in group)
    speedup = (stats["baseline"]["median_s"] / stats["iterated"]["median_s"]
               if matched == 3 else None)
    print(json.dumps(dict(summary_case=case_id, matched_repeats=matched,
                          statuses=[r["solver_status"] for r in group],
                          call_stats=stats, median_call_ratio=speedup)), flush=True)
if failed:
    raise SystemExit(1)
