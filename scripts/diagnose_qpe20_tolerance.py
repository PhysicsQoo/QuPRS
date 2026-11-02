"""QPE-inexact20 sensitivity study: classify observed thresholds, not runtimes.

Independent P0 source-state sampling already showed a nonzero mismatch. This
sweep DOES NOT demonstrate full-unitary equivalence and is never a CodSpeed
performance comparison. Only explicitly overridden public API tolerances vary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

NAME = "qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm"
FIELDS = ("status", "verdict", "wmc_numerical_verdict", "wmc_printed_verdict",
          "wmc_precision_reason", "wmc_print_resolution_distance",
          "wmc_numeric_model_bound", "wmc_log_wmc", "wmc_expected_log2",
          "rr_approximate", "solver_invoked", "effective_rr_tolerance",
          "effective_distance_tolerance", "effective_phase_tolerance",
          "effective_gpmc_digits")
MARKER = "QUPRS_WALLTIME_RESULT "

# Default RR policy and 30-digit GPMC precision; vary ONE dimension per lane.
# QCEC 2e-8 is a diagnostic comparator, not a requirement to force pass.
PROBES = (
    ("rust_d1e-9", "rust", "transpiled", "1e-9", None, None, None),
    ("rust_default_d1e-8", "rust", "transpiled", "1e-8", None, None, None),
    ("rust_qcec_reference_d2e-8", "rust", "transpiled", "2e-8", None, None, None),
    ("rust_d1e-7", "rust", "transpiled", "1e-7", None, None, None),
    ("rust_d1e-6", "rust", "transpiled", "1e-6", None, None, None),
    ("rust_d3e-6", "rust", "transpiled", "3e-6", None, None, None),
    ("rust_d5e-6", "rust", "transpiled", "5e-6", None, None, None),
    ("rust_d1e-5", "rust", "transpiled", "1e-5", None, None, None),
    ("rust_rr_exact", "rust", "transpiled", "1e-8", "0", None, None),
    ("rust_rr_1e-7", "rust", "transpiled", "1e-8", "1e-7", None, None),
    ("rust_mpfr90", "rust", "transpiled", "1e-8", None, None, "90"),
    ("rust_phase_1e-6", "rust", "transpiled", "1e-5", None, "1e-6", None),
    ("python_default", "python", "transpiled", "1e-8", None, None, None),
    ("python_qcec_reference", "python", "transpiled", "2e-8", None, None, None),
    ("python_d1e-5", "python", "transpiled", "1e-5", None, None, None),
    ("rust_rotation_control", "rust", "random_rotation", "1e-5", None, None, None),
)

def source_pair_sha(root: Path) -> dict:
    folder = root / "benchmarks" / "MQTBench"
    paths = {
        "original": folder / NAME,
        "transpiled": folder / "h,ry,rz,cx" / NAME,
        "random_rotation": folder / "Random_Rotation" / NAME,
    }
    return {k: hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()}

def run_one(root: Path, spec: tuple, timeout: int = 15, watchdog: int = 28):
    name, backend, pair, dist, rr, phase, precision = spec
    cmd = [sys.executable, str(root / "benchmarks/codspeed/solver_case.py"),
           str(root), NAME, "proportional", "gpmc", backend, "0", pair, "hybrid"]
    env = dict(os.environ)
    env["QUPRS_CROSS_METHOD_SOLVER_TIMEOUT"] = str(timeout)
    env["QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE"] = dist
    if rr is not None:
        env["QUPRS_DIAGNOSTIC_RR_TOLERANCE"] = rr
    if phase is not None:
        env["QUPRS_DIAGNOSTIC_PHASE_TOLERANCE"] = phase
    if precision is not None:
        env["QUPRS_DIAGNOSTIC_GPMC_DIGITS"] = precision
    proc = subprocess.Popen(cmd, cwd=root, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=watchdog)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return {"id": name, "status": "WATCHDOG_TIMEOUT",
                "requested_distance": dist, "backend": backend}
    output = [row[len(MARKER):] for row in stdout.splitlines()
              if row.startswith(MARKER)]
    if proc.returncode or len(output) != 1:
        return {"id": name, "status": "PROCESS_ERROR",
                "exit_code": proc.returncode,
                "stderr_tail": stderr[-1000:], "requested_distance": dist}
    try:
        response = json.loads(output[0])
    except json.JSONDecodeError:
        return {"id": name, "status": "INVALID_OUTPUT"}
    return {"id": name, "status": "COMPLETED", "exit_code": proc.returncode,
            **{key: response.get(key) for key in FIELDS}}

def classify(records: list) -> dict:
    by_id = {row["id"]: row for row in records}
    baseline = by_id.get("rust_default_d1e-8", {})
    qcec = by_id.get("rust_qcec_reference_d2e-8", {})
    complete = [r for r in records if r.get("status") == "COMPLETED"]
    sensitivity = [
        r for r in complete if r["id"].startswith("rust_d")
        and r["id"] != "rust_default_d1e-8"
    ] + ([baseline] if baseline.get("status") == "COMPLETED" else [])
    sweep = sorted(sensitivity, key=lambda r:r["effective_distance_tolerance"])
    labels = [(r["effective_distance_tolerance"],r["verdict"]) for r in sweep]
    first_equivalent = next((t for t,v in labels if v in {"equivalent","equivalent*"}),None)
    last_nonequivalent = next((t for t,v in reversed(labels)
                              if v == "not_equivalent"
                              and (first_equivalent is None or t < first_equivalent)), None)
    return {
        "baseline_verdict": baseline.get("verdict"),
        "qcec_2e-8_verdict": qcec.get("verdict"),
        "first_equivalent_at_requested_tolerance": first_equivalent,
        "last_nonequivalent_before_transition": last_nonequivalent,
        "observed_threshold_bracket_is_not_certified_projective_distance": True,
        "all_probe_statuses": {r["id"]:r["status"] for r in records},
        "source_equivalence_certified": False,
        "wmc_solver_arithmetic_certified": False,
        "performance_measurement": False,
    }

def execute(root: Path, sha: str) -> dict:
    rows = [run_one(root, spec) for spec in PROBES]
    return {
        "schema": "quprs-qpe20-tolerance-sensitivity-v1", "sha": sha,
        "source_qasm_sha256": source_pair_sha(root),
        "model": {"projective_distance_tolerance_default": 1e-8,
                  "rr_tolerance_default": 1e-10,
                  "wmc_phase_tolerance_default": 1e-8,
                  "gpmc_default_digits": 30},
        "method": "Hybrid", "solver": "GPMC",
        "observations": rows, "interpretation": classify(rows),
        "time": "NO_TIMING_COLLECTED_NO_PERFORMANCE_CLAIM",
        "science_status": "TOLERANCE_DIAGNOSTIC_UNCERTIFIED",
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture-root",required=True,type=Path)
    parser.add_argument("--sha",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    result=execute(args.fixture_root,args.sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result["interpretation"],sort_keys=True))
    if result["interpretation"]["baseline_verdict"] is None:
        raise SystemExit("No valid baseline tolerance diagnosis")

if __name__=="__main__":
    main()
