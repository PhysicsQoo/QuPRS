#!/usr/bin/env python3
"""Six distinct MQTBench families: exact-head Rust Elim rule-body timing pilot.

One build, two opt-in levels. Source, solver, inputs and raw JSON are preserved.
The pilot collects measurements; it does NOT certify a predictive model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

from QuPRS import _pathsum_rust
from QuPRS.utils import WMC

CASES = {
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "Proportional", False),
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "Proportional", True),
    "grover4": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", True),
    "vqe4": ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", False),
    "graphstate16": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "Naive", False),
    "ghz32": ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "Straightforward", True),
}
MODES = ("structural", "timed")
WARMUPS, ROUNDS = 1, 8
BENCH = Path("benchmarks/MQTBench").resolve()
OUT = Path("rust-elim-cost-pilot-results").resolve()


def h(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run_cmd(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=40)
    return {"exit": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-8000:]}


def input_paths(case):
    filename, strategy, reverse = CASES[case]
    files = (BENCH / filename, BENCH / "h,ry,rz,cx" / filename)
    if not all(x.is_file() for x in files):
        raise FileNotFoundError(str(files))
    return (files[::-1] if reverse else files), strategy


def one(case, mode):
    paths, strategy = input_paths(case)
    os.environ["QUPRS_STAGE_LEDGER"] = "1"
    if mode == "timed":
        os.environ["QUPRS_ELIM_TIMING"] = "1"
    else:
        os.environ.pop("QUPRS_ELIM_TIMING", None)
    with WMC("gpmc") as binary:
        if binary.resolve() != Path(os.environ["QUPRS_GPMC_PATH"]).resolve():
            raise RuntimeError("solver executable identity differs")
        start = time.perf_counter_ns()
        raw = _pathsum_rust.check_equivalence(
            str(paths[0]), str(paths[1]),
            method="hybrid", strategy=strategy, tool_name="gpmc", timeout=60)
        wrapper_ns = time.perf_counter_ns() - start
    stage = raw.get("stage_ledger")
    errs = []
    if raw["status"] not in ("Equivalent", "Equivalent (Up to Global Phase)"):
        errs.append("undecided/incorrect result")
    if not isinstance(stage, dict):
        errs.append("missing stage")
        features, timings = [], None
    else:
        features = stage["structural_elim_attempts"]
        timings = stage.get("elim_attempt_timings")
        if stage["has_stage_overlap"] or abs(stage["closure_error_seconds"]) > 1e-6:
            errs.append("stage closure error or overlapping stages")
        if mode == "structural":
            if timings is not None:
                errs.append("unexpected per-Elim timer without second opt-in")
        elif not isinstance(timings, list) or len(timings) != len(features):
            errs.append("per-Elim timing count mismatch")
        else:
            for i, t in enumerate(timings):
                if (set(t) != {"structural_index", "elapsed_ns", "success"}
                    or t["structural_index"] != i or type(t["elapsed_ns"]) is not int
                    or t["elapsed_ns"] < 0 or type(t["success"]) is not bool):
                    errs.append("invalid timing-to-feature index/type")
                    break
            if sum(t["elapsed_ns"] for t in timings) / 1e9 > (
                stage["exclusive_seconds"]["reduction"] + 1e-5
            ):
                errs.append("nested Elim duration exceeds root Reduction span")
    for x in features:
        if (set(x) != {"k_r", "l_r", "v_r", "d_r", "w_redundant_estimated"}
            or x["w_redundant_estimated"] != max(0, x["k_r"] - 1) * x["l_r"]):
            errs.append("invalid structural feature schema")
            break
    return {
        "case": case, "mode": mode, "status": raw["status"],
        "input_sha256": [h(x) for x in paths],
        "rules": raw["stats"], "final_ps_sha256": hashlib.sha256(
            raw["final_ps"].encode()).hexdigest(),
        "ffi_wrapper_ns": wrapper_ns,
        "native_wall_sec": raw["verification_time_sec"],
        "pathsum_strategy_sec": raw["pathsum_time_sec"],
        "extension_path": str(Path(_pathsum_rust.__file__).resolve()),
        "stage_ledger": stage, "errors": errs,
    }


def boot(values):
    rng = random.Random(112060)
    sims = sorted(statistics.median([rng.choice(values) for _ in values])
                  for _ in range(2000))
    return [sims[49], sims[1949]]


def pilot():
    OUT.mkdir(parents=True, exist_ok=True)
    affinities = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinities[0]})
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    with WMC("gpmc") as binary:
        binary = binary.resolve()
        if not binary.is_file():
            raise FileNotFoundError("packaged GPMC missing")
        os.environ["QUPRS_GPMC_PATH"] = str(binary)
        manifest = {
            "schema": "quprs-six-family-elim-cost-v1", "git": run_cmd(["git","rev-parse","HEAD"]),
            "gpmc_gitlink": run_cmd(["git","rev-parse","HEAD:GPMC"]),
            "platform": platform.platform(), "python": sys.version,
            "dependencies": run_cmd([sys.executable,"-m","pip","freeze"]),
            "cpu": run_cmd(["lscpu"]), "affinity_original": affinities,
            "affinity_used": affinities[0], "gpmc_binary_sha256": h(binary),
            "runner_sha256": h(Path(__file__).resolve()),
            "design": {"cases": list(CASES), "modes": MODES,
                       "warmups": WARMUPS, "rounds": ROUNDS,
                       "solver": "gpmc", "timeout_seconds": 60},
            "qasm_sha256": {k: [h(x) for x in input_paths(k)[0]] for k in CASES},
        }
        dump(OUT / "environment.json", manifest)
        obs, errors = [], []
        with (OUT / "samples.jsonl").open("w", buffering=1) as fp:
            for case in CASES:
                for r in range(-WARMUPS, ROUNDS):
                    modes = list(MODES)
                    random.Random(112060 + r + list(CASES).index(case) * 100).shuffle(modes)
                    paired = {}
                    for mode in modes:
                        dest = OUT / "individual" / f"{case}_{r:03d}_{mode}.json"
                        child = [sys.executable, "-u", str(Path(__file__).resolve()),
                                 "--one", "--case", case, "--mode", mode]
                        row = {"case": case, "round": r, "mode": mode, "warmup": r < 0,
                               "path": str(dest.relative_to(OUT))}
                        try:
                            p = subprocess.run(child, capture_output=True, text=True,
                                               env=os.environ.copy(), timeout=100)
                            row.update(exit=p.returncode, stderr=p.stderr[-4000:])
                            if p.returncode == 0:
                                item = json.loads(p.stdout)
                                dump(dest, item)
                                row["data"] = item
                                paired[mode] = item
                            else:
                                row["stdout"] = p.stdout[-4000:]
                                errors.append({"case":case, "mode":mode, "round":r,
                                               "error":p.stderr[-1000:]})
                        except (subprocess.TimeoutExpired, ValueError) as exc:
                            errors.append({"case":case, "mode":mode, "round":r,
                                           "error":repr(exc)})
                        obs.append(row)
                        fp.write(json.dumps(row, sort_keys=True) + "\n")
                        print("ELIM_SAMPLE", case, r, mode, row.get("exit"), flush=True)
                        if errors:
                            break
                    if not errors and len(paired) == 2:
                        a, b = (paired[m] for m in MODES)
                        if (any(a[k] != b[k] for k in ("status","rules","input_sha256","final_ps_sha256"))
                            or a["stage_ledger"]["structural_elim_attempts"]
                               != b["stage_ledger"]["structural_elim_attempts"]
                            or a["errors"] or b["errors"]):
                            errors.append({"case":case, "round":r, "error":"NATIVE_PARITY_FAILURE"})
                    if errors:
                        break
                if errors:
                    break
    summary = {"schema": manifest["schema"], "status": "INCOMPLETE",
               "errors":errors, "families":{}}
    for case in CASES:
        paired_rows = [x for x in obs if x["case"] == case and not x["warmup"]]
        pairs = {r: {x["mode"]: x["data"] for x in paired_rows if x["round"] == r
                     and "data" in x} for r in range(ROUNDS)}
        valid = [v for v in pairs.values() if set(v) == set(MODES)]
        d = {"paired_valid": len(valid)}
        if len(valid) == ROUNDS:
            ratios = [pair["timed"]["ffi_wrapper_ns"] /
                      pair["structural"]["ffi_wrapper_ns"] for pair in valid]
            example = valid[0]["timed"]["stage_ledger"]
            f = example["structural_elim_attempts"]
            d.update(
                median_paired_ffi_ratio=statistics.median(ratios),
                bootstrap_95pct_descriptive_interval=boot(ratios),
                structural_sample_count=len(f),
                distinct_feature_vectors=len({(v["k_r"],v["l_r"],v["v_r"],v["d_r"])
                                              for v in f}),
                median_root_reduction_sec=statistics.median(
                    pair["timed"]["stage_ledger"]["exclusive_seconds"]["reduction"]
                    for pair in valid),
                median_sum_nested_elim_sec=statistics.median(
                    sum(v["elapsed_ns"] for v in pair["timed"]["stage_ledger"]
                        ["elim_attempt_timings"]) / 1e9 for pair in valid),
            )
        summary["families"][case] = d
    if not errors and all(v["paired_valid"] == ROUNDS for v in summary["families"].values()):
        summary["status"] = "PASS_DATA_COLLECTION"
    summary["scientific_limits"] = [
        "Elapsed Elim time excludes structural feature snapshot but includes Instant overhead.",
        "Elim times are nested within root Reduction time and cannot be added to it.",
        "Eight repeats are not eight independent circuit structures.",
        "Six families permit preliminary structure-versus-timing exploration only.",
        "Do not fit a production predictive scheduler to this exploratory pilot.",
    ]
    dump(OUT / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "families":summary["families"]},
                     sort_keys=True), flush=True)
    return 0 if summary["status"] == "PASS_DATA_COLLECTION" else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--one", action="store_true")
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--mode", choices=MODES)
    a = parser.parse_args()
    if a.one:
        result = one(a.case, a.mode)
        print(json.dumps(result, sort_keys=True))
        return 0 if not result["errors"] else 2
    return pilot()


if __name__ == "__main__":
    raise SystemExit(main())
