#!/usr/bin/env python3
"""Bounded same-runner coefficient-overlap attribution with sealed raw evidence.

Counts probe only the real Omega and HH P_expanded.coeff(yo) call sites. Runs
in separate subprocesses to avoid mutating an installed QuPRS interpreter.
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time

CASES = ("qaoa7", "grover4")
MODES = ("plain", "probe")
BLOCKS = 2
TIMEOUT = 90
OUT = Path("qoo112-coeff-overlap-results").resolve()
ROOT = Path("benchmarks/MQTBench").resolve()
SCRIPT = Path(".diagnostics/qoo112/coeff_overlap_case.py").resolve()
FILES = {
    "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summary(xs):
    if not xs:
        return None
    mid = statistics.median(xs)
    return {"n": len(xs), "median": mid,
            "mad": statistics.median(abs(v - mid) for v in xs),
            "values": xs}


def run(case, mode, block, pos, warmup):
    command = [sys.executable, "-u", str(SCRIPT),
               "--case", case, "--case-root", str(ROOT), "--timeout", "60"]
    if mode == "probe":
        command.append("--probe")
    rec = {"case": case, "mode": mode, "block": block, "position": pos,
           "warmup": warmup, "command": command,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    start = time.perf_counter()
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=TIMEOUT)
        rec.update(exit_code=proc.returncode, stderr=proc.stderr[-14000:],
                   stdout=proc.stdout[-2000:])
        try:
            rec["data"] = json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            rec["error"] = "NO_JSON_LAST_LINE"
    except subprocess.TimeoutExpired as exc:
        rec.update(exit_code=None, error="PROCESS_TIMEOUT",
                   stderr=str(exc)[-3000:])
    rec["process_wall_seconds"] = time.perf_counter() - start
    print(case, mode, "warmup" if warmup else "sample", block, pos,
          rec.get("data", {}).get("status", rec.get("error", "MISSING")),
          round(rec["process_wall_seconds"], 3), flush=True)
    return rec


def successful(row):
    value = row.get("data", {})
    return (row.get("exit_code") == 0
            and value.get("status") in ("equivalent", "equivalent*")
            and value.get("status") == value.get("operator_oracle"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = [SCRIPT, Path(__file__).resolve()]
    for case in CASES:
        filename = FILES[case]
        inputs.extend((ROOT / filename, ROOT / "h,ry,rz,cx" / filename))
    for f in inputs:
        if not f.exists():
            raise FileNotFoundError(f)
    affinity_before = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinity_before[0]})
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    def command(args):
        x = subprocess.run(args, text=True, capture_output=True)
        return {"status": x.returncode, "stdout": x.stdout[:25000], "stderr": x.stderr[-5000:]}
    manifest = {
        "schema": 1, "kind": "no-modification-coefficient-overlap",
        "source": command(["git", "rev-parse", "HEAD"]),
        "python": platform.python_version(), "platform": platform.platform(),
        "pip_freeze": command([sys.executable, "-m", "pip", "freeze"]),
        "cpu_affinity_before": affinity_before,
        "cpu_affinity_used": [affinity_before[0]],
        "case_root": str(ROOT), "cases": CASES, "solver": "gpmc",
        "backend": "python", "method": "hybrid", "strategy": "Proportional",
        "blocks": BLOCKS, "timeout_seconds": TIMEOUT,
        "files_sha256": {str(p): sha(p) for p in inputs},
    }
    (OUT / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    rows, failures = [], []
    with (OUT / "samples.jsonl").open("w", buffering=1) as file:
        for case in CASES:
            for mode in MODES:
                item = run(case, mode, -1, 0, True)
                rows.append(item)
                file.write(json.dumps(item) + "\n")
                if not successful(item):
                    failures.append({"case": case, "stage": "warmup",
                                     "mode": mode, "error": item.get("error"),
                                     "stderr": item.get("stderr")})
            if failures:
                continue
            for block in range(BLOCKS):
                order = ("plain", "probe", "probe", "plain") if block % 2 == 0 else ("probe", "plain", "plain", "probe")
                for pos, mode in enumerate(order):
                    item = run(case, mode, block, pos, False)
                    rows.append(item)
                    file.write(json.dumps(item) + "\n")
                    if not successful(item):
                        failures.append({"case": case, "stage": "measure",
                                         "mode": mode, "block": block,
                                         "error": item.get("error"),
                                         "stderr": item.get("stderr")})
                        break
                if failures:
                    break
    cases = []
    for case in CASES:
        observed = [r["data"] for r in rows if not r["warmup"] and successful(r) and r["case"] == case]
        probed = [r for r in observed if r["probe"]]
        plain = [r for r in observed if not r["probe"]]
        rates = [r["overlap"]["hits"] / r["counts"]["hh"]["calls"] for r in probed if r["counts"]["hh"]["calls"]]
        upper = [r["overlap"]["hit_hh_coefficient_time_ns"] / 1e9 for r in probed]
        comparisons = []
        for block in range(BLOCKS):
            p = [r["data"]["elapsed_seconds"] for r in rows if successful(r) and not r["warmup"]
                 and r["case"] == case and r["block"] == block and r["mode"] == "plain"]
            d = [r["data"]["elapsed_seconds"] for r in rows if successful(r) and not r["warmup"]
                 and r["case"] == case and r["block"] == block and r["mode"] == "probe"]
            if len(p) == len(d) == 2:
                comparisons.append(statistics.median(d) / statistics.median(p))
        if len(comparisons) != BLOCKS:
            failures.append({"case": case, "error": "MISSING_ABBA_BAAB_BLOCKS"})
        if not probed:
            failures.append({"case": case, "error": "NO_VALID_COEFF_PROFILE"})
        mismatch = sum(r["overlap"]["different_value"] for r in probed)
        misses = sum(r["overlap"]["misses"] for r in probed)
        if mismatch:
            failures.append({"case": case, "error": "OMEGA_HH_COEFFICIENT_MISMATCH",
                             "count": mismatch})
        details = {
            "case": case,
            "outcome": sorted({r["status"] for r in observed}),
            "samples": len(observed),
            "overlap": {
                "fraction": summary(rates), "hh_reused_ns": summary([x * 1e9 for x in upper]),
                "misses_all": misses, "mismatches_all": mismatch,
                "omega_calls": summary([r["counts"]["omega"]["calls"] for r in probed]),
                "hh_calls": summary([r["counts"]["hh"]["calls"] for r in probed]),
                "hh_coeff_wall_seconds": summary([r["counts"]["hh"]["time_ns"]/1e9 for r in probed]),
                "omega_coeff_wall_seconds": summary([r["counts"]["omega"]["time_ns"]/1e9 for r in probed]),
                "reduction_attempts": summary([r["attempts"]["total"] for r in probed]),
                "omega_then_hh_attempts": summary([r["attempts"]["omega_then_hh"] for r in probed]),
            },
            "plain_wall_seconds": summary([r["elapsed_seconds"] for r in plain]),
            "probe_wall_seconds": summary([r["elapsed_seconds"] for r in probed]),
            "observer_ratio": summary(comparisons),
        }
        cases.append(details)
    result = {"schema": 1, "verdict": "PASS" if not failures else "INCOMPLETE",
              "cases": cases, "failures": failures,
              "interpretation": "Repeated HH coeff timing is an instrumented upper bound, not a measured cache speedup."}
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    md = ["# Omega→HH coeff() attempt-local overlap", "",
          "| Case | HH coeff calls | Reused fraction | HH coeff total (ms) | Potential skipped (ms) | Probe/off ratio |",
          "|---|---:|---:|---:|---:|---:|"]
    def val(obj):
        return 0.0 if obj is None else obj["median"]
    for item in cases:
        v = item["overlap"]
        md.append("| %s | %.0f | %.3f | %.3f | %.3f | %.3f |" %
                  (item["case"], val(v["hh_calls"]), val(v["fraction"]),
                   1000*val(v["hh_coeff_wall_seconds"]), val(v["hh_reused_ns"])/1e6,
                   val(item["observer_ratio"])))
    md.extend(("", "Verdict: " + result["verdict"],
               "All values are counts/cost of *actual* coeff calls on dev; this tool NEVER substitutes stored results.",
               "Interpret potential skipped time as an upper bound before dictionary/call overhead."))
    (OUT / "summary.md").write_text("\n".join(md)+"\n")
    print("\n".join(md), flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
