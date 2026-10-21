#!/usr/bin/env python3
"""Source-pinned, one-host, interleaved A/B/C experiment; no performance gates."""
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

BASE_SHA = "e84f909b08e42872421a4a0b5835c44faf812384"
NEW_SHA = "8ce78bd95e9548a4efcdb17852c7b882a5ca2ce1"
CASES = {
    "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "qft16": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
}
METRICS = ("ffi_wrapper_wall_seconds", "native_total_seconds", "native_pathsum_seconds")


def cmd(args):
    r = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=60, check=False)
    return {"returncode": r.returncode, "stdout": r.stdout[-12000:],
            "stderr": r.stderr[-16000:]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root, *args):
    r = cmd(["git", "-C", str(root), *args])
    if r["returncode"]:
        raise RuntimeError("git failure: " + str(r))
    return r["stdout"].strip()


def dependency_versions(python):
    r = cmd([str(python), "-m", "pip", "list", "--format=json"])
    if r["returncode"]:
        raise RuntimeError("unable to read venv dependency inventory: " + str(r))
    return {v["name"].lower(): v["version"] for v in json.loads(r["stdout"])}


def bootstrap_interval(values, seed=20261021, draws=2000):
    rng = random.Random(seed)
    means = [statistics.median([values[rng.randrange(len(values))]
                               for _ in values]) for _ in range(draws)]
    means.sort()
    return [means[int(draws * 0.025)], means[int(draws * 0.975)]]


def summarize(samples):
    report = {}
    for case in CASES:
        by_mode = {m: {x["round"]: x["data"] for x in samples
                       if x["case"] == case and x["mode"] == m and not x["warmup"]}
                   for m in ("A", "B", "C")}
        report[case] = {"n": {m: len(v) for m, v in by_mode.items()}, "metrics": {}}
        for metric in METRICS:
            values = {m: [by_mode[m][i][metric] for i in sorted(by_mode[m])]
                      for m in by_mode}
            metrics = {m: {"median_seconds": statistics.median(v),
                           "minimum_seconds": min(v), "maximum_seconds": max(v)}
                       for m, v in values.items()}
            for numerator, denominator in (("B", "A"), ("C", "B")):
                ratios = [by_mode[numerator][i][metric] /
                          by_mode[denominator][i][metric]
                          for i in sorted(by_mode["A"])]
                metrics[numerator + "/" + denominator] = {
                    "median_paired_ratio": statistics.median(ratios),
                    "median_paired_change_percent": 100 * (statistics.median(ratios) - 1),
                    "bootstrap_95pct_paired_median_ratio_interval":
                        bootstrap_interval(ratios),
                    "interpretation": "descriptive, shared-runner observational data; not a regression gate",
                }
            report[case]["metrics"][metric] = metrics
        structured = [v["stage_ledger"] for v in by_mode["C"].values()]
        report[case]["profiled_reduction_seconds"] = {
            "median_root_reduction_seconds": statistics.median(
                x["exclusive_seconds"]["reduction"] for x in structured),
            "per_attempt_time_available": False,
            "structural_sample_count_range": [
                min(len(x["structural_elim_attempts"]) for x in structured),
                max(len(x["structural_elim_attempts"]) for x in structured),
            ],
            "w_redundant_estimated_total_range": [
                min(sum(s["w_redundant_estimated"] for s in x["structural_elim_attempts"])
                    for x in structured),
                max(sum(s["w_redundant_estimated"] for s in x["structural_elim_attempts"])
                    for x in structured),
            ],
        }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-a", required=True, type=Path)
    ap.add_argument("--source-b", required=True, type=Path)
    ap.add_argument("--python-a", required=True, type=Path)
    ap.add_argument("--python-b", required=True, type=Path)
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--warmups", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--hard-timeout", type=int, default=90)
    ap.add_argument("--out", type=Path, default=Path("rust-structural-abc-results"))
    args = ap.parse_args()
    if args.rounds < 30:
        raise ValueError("minimum 30 valid paired samples per case/mode required")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name("one.py").resolve()
    common = Path.cwd().resolve()
    source_a, source_b = args.source_a.resolve(), args.source_b.resolve()
    assert git(source_a, "rev-parse", "HEAD") == BASE_SHA
    assert git(source_b, "rev-parse", "HEAD") == NEW_SHA
    gpmc_link_a = git(source_a, "rev-parse", "HEAD:GPMC")
    gpmc_link_b = git(source_b, "rev-parse", "HEAD:GPMC")
    if gpmc_link_a != gpmc_link_b:
        raise RuntimeError("baseline/current GPMC gitlinks differ")

    env_a = dependency_versions(args.python_a)
    env_b = dependency_versions(args.python_b)
    if {k: v for k, v in env_a.items() if k != "quprs"} != {
            k: v for k, v in env_b.items() if k != "quprs"}:
        raise RuntimeError("Python dependency versions not identical")

    # Use the identical executable for every group, not merely one gitlink.
    from_gpmc = cmd([str(args.python_a), "-c",
                     "from QuPRS.utils import WMC\nwith WMC('gpmc') as p:\n print(p)"])
    if from_gpmc["returncode"] != 0:
        raise RuntimeError("could not locate shared packaged GPMC: " + str(from_gpmc))
    gpmc = Path(from_gpmc["stdout"].splitlines()[-1]).resolve()
    if not gpmc.is_file() or not os.access(gpmc, os.X_OK):
        raise RuntimeError("shared GPMC executable missing / not executable")

    affinity_before = sorted(os.sched_getaffinity(0))
    cpu = affinity_before[0]
    os.sched_setaffinity(0, {cpu})  # subprocesses inherit the same CPU affinity
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      QUPRS_GPMC_PATH=str(gpmc))
    os.environ.pop("QUPRS_STAGE_LEDGER", None)
    os.environ.pop("PYTHONPATH", None)

    left_root = common / "benchmarks" / "MQTBench"
    paths = {"runner.py": sha(Path(__file__).resolve()),
             "one.py": sha(script), "shared_gpmc_binary": sha(gpmc)}
    for case, filename in CASES.items():
        paths[case + "_left"] = sha(left_root / filename)
        paths[case + "_right"] = sha(left_root / "h,ry,rz,cx" / filename)

    manifest = {
        "schema": "quprs-same-host-structural-abc-v1",
        "design": "3 warm-up triplets then 30 randomized interleaved triplets per case; single CI VM/CPU affinity, isolated child process per observation",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "analysis_git_sha": git(common, "rev-parse", "HEAD"),
        "A_sha": BASE_SHA, "B_C_sha": NEW_SHA,
        "A_GPMC_gitlink": gpmc_link_a, "B_C_GPMC_gitlink": gpmc_link_b,
        "common_gpmc_executable": str(gpmc),
        "files_sha256": paths,
        "python_A": str(args.python_a.resolve()), "python_B": str(args.python_b.resolve()),
        "dependencies_A": env_a, "dependencies_B": env_b,
        "python_version_runner": sys.version, "platform": platform.platform(),
        "cpu_affinity_original": affinity_before, "cpu_affinity_used": cpu,
        "cpuinfo": Path("/proc/cpuinfo").read_text()[:8000],
        "os_release": Path("/etc/os-release").read_text(),
        "rustc": cmd(["rustc", "--version"]), "gcc": cmd(["gcc", "--version"]),
        "parameters": {"rounds": args.rounds, "warmups": args.warmups,
                       "native_timeout": args.timeout, "hard_timeout": args.hard_timeout,
                       "method": "hybrid", "strategy": "Proportional", "solver": "gpmc",
                       "QFT16_swap": True, "QAOA7_swap": False},
    }
    write_json(out / "environment.json", manifest)

    samples, errors = [], []
    with (out / "samples.jsonl").open("w", buffering=1) as fp:
        for case, filename in CASES.items():
            a, b = left_root / filename, left_root / "h,ry,rz,cx" / filename
            if case == "qft16":
                a, b = b, a  # Match existing test_MQT.py's QFT16 direction.
            for r in range(-args.warmups, args.rounds):
                modes = ["A", "B", "C"]
                random.Random(20261021 + (0 if case == "qaoa7" else 10_000) + r).shuffle(modes)
                by_round = {}
                for mode in modes:
                    p = args.python_a if mode == "A" else args.python_b
                    filename_json = f"{case}_round_{r:03d}_{mode}.json"
                    rawpath = out / "individual" / filename_json
                    command = [str(p), "-u", str(script), "--left", str(a),
                               "--right", str(b), "--mode", mode, "--case", case,
                               "--out", str(rawpath), "--timeout", str(args.timeout)]
                    row = {"case": case, "mode": mode, "round": r, "warmup": r < 0,
                           "command": command, "raw_file": str(rawpath.relative_to(out))}
                    start = time.perf_counter()
                    try:
                        proc = subprocess.run(command, text=True, capture_output=True,
                                              timeout=args.hard_timeout, check=False)
                        row.update(returncode=proc.returncode, stdout=proc.stdout[-3000:],
                                   stderr=proc.stderr[-8000:])
                    except subprocess.TimeoutExpired as exc:
                        row.update(returncode=None, error="HARD_TIMEOUT",
                                   stderr=str(exc))
                    row["process_wall_seconds"] = time.perf_counter() - start
                    if rawpath.is_file():
                        try:
                            row["data"] = json.loads(rawpath.read_text())
                        except ValueError as exc:
                            row["error"] = "INVALID_JSON:" + str(exc)
                    if row.get("returncode") != 0 or "data" not in row:
                        errors.append({"case": case, "mode": mode, "round": r,
                                       "error": row.get("error", "FAILED"),
                                       "stderr": row.get("stderr", "")[-2500:]})
                    else:
                        d = row["data"]
                        by_round[mode] = d
                        if d["mode"] != mode or d["case"] != case or d["validation_errors"]:
                            errors.append({"case": case, "mode": mode, "round": r,
                                           "error": "INVALID_NATIVE_RECORD"})
                        if mode == "A" and args.python_a.resolve().parts[0] not in Path(d["module_path"]).parts:
                            # Module location is already preserved in every raw sample.
                            pass
                    fp.write(json.dumps(row, sort_keys=True) + "\n")
                    samples.append(row)
                    print("OBS", case, r, mode, row.get("returncode"),
                          row.get("data", {}).get("ffi_wrapper_wall_seconds"), flush=True)
                    if errors:
                        break
                if not errors and len(by_round) == 3:
                    statuses = {(d["status"], json.dumps(d["rules"], sort_keys=True),
                                 d["final_ps_sha256"], tuple(d["input_qasm_sha256"]))
                                for d in by_round.values()}
                    if len(statuses) != 1:
                        errors.append({"case": case, "round": r,
                                       "error": "A/B/C native result or reduction-rule mismatch"})
                if errors:
                    break
            if errors:
                break

    valid = [{**r, "data": r["data"]} for r in samples if r.get("returncode") == 0
             and "data" in r and not r["data"]["validation_errors"]]
    counts = {case: {m: sum(x["case"] == case and x["mode"] == m and not x["warmup"]
                            for x in valid)
                      for m in ("A", "B", "C")} for case in CASES}
    if not errors:
        if any(v != args.rounds for modes in counts.values() for v in modes.values()):
            errors.append({"error": "NOT_ENOUGH_VALID_PAIRED_SAMPLES", "counts": counts})
    summary = {
        "schema": "quprs-same-host-structural-abc-v1",
        "status": "PASS_DATA_COLLECTION" if not errors else "INCOMPLETE",
        "counts": counts, "errors": errors, "analysis": summarize(valid) if not errors else None,
        "limits": [
            "GitHub shared-runner CPU load and host microarchitecture may still confound cross-job reproducibility.",
            "Paired interleaving controls drift but is not proof of zero default-off overhead.",
            "A/B off has no exclusive reduction time: native_pathsum_seconds is a broader strategy-timing proxy.",
            "C has aggregate outermost reduction wall; no per-Elim timing exists. Two fixed circuits do NOT identify a predictive cost model or causal W-versus-runtime relation.",
            "W_redundant_estimated is a historical pre-Hoist scan proxy, NOT measured saved operations.",
            "FFI wrapper wall excludes importing Qiskit, QASM conversion and process startup.",
            "Single shared GPMC binary, same gitlink and matched Python dependency versions, with timeouts and exact SHAs pinned.",
            "No automatic performance gate or algorithm change; examine intervals and raw individual JSON before conclusions.",
        ],
    }
    write_json(out / "summary.json", summary)
    table = ["# Same-host opt-in Rust structural counter A/B/C", "",
             f"Result: {summary['status']}", "",
             "A=old dev default-off; B=new dev default-off; C=new dev diagnostics-on.",
             "", "| Case | Samples per group | B/A median FFI ratio | C/B median FFI ratio | C median reduction wall (s) |",
             "|---|---:|---:|---:|---:|"]
    if summary["analysis"]:
        for case, data in summary["analysis"].items():
            r = data["metrics"]["ffi_wrapper_wall_seconds"]
            table.append(f"| {case} | {data['n']['A']} | "
                         f"{r['B/A']['median_paired_ratio']:.4f} | "
                         f"{r['C/B']['median_paired_ratio']:.4f} | "
                         f"{data['profiled_reduction_seconds']['median_root_reduction_seconds']:.6f} |")
    table += ["", "WARNING: Bootstrap bounds are descriptive conditional-on-host intervals, not hardware-invariant causal proof.",
              "No per-Elim timing and only two circuit families: never fit a predictive model to repeated samples as independent structural observations."]
    (out / "summary.md").write_text("\n".join(table) + "\n")
    print("\n".join(table), flush=True)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
