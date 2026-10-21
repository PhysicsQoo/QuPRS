#!/usr/bin/env python3
"""Pinned, interleaved A/B/C Rust FFI experiment. No causal speedup claims."""
import argparse
from datetime import datetime, timezone
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

A_SHA = "e84f909b08e42872421a4a0b5835c44faf812384"
B_SHA = "8ce78bd95e9548a4efcdb17852c7b882a5ca2ce1"
CIRCUITS = {
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", False),
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", True),
}
ARMS = ("A", "B", "C")
EQUIVALENT = {"Equivalent", "Equivalent (Up to Global Phase)"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cmd(*args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return {"returncode": p.returncode, "out": p.stdout.strip(),
            "stderr": p.stderr[-1000:]}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def circuits(root, case):
    name, reverse = CIRCUITS[case]
    files = [Path(root) / name, Path(root) / "h,ry,rz,cx" / name]
    if reverse:
        files.reverse()
    if not all(p.is_file() for p in files):
        raise FileNotFoundError(str(files))
    return files


def once(a):
    from QuPRS import _pathsum_rust
    p1, p2 = circuits(a.bench, a.case)
    if a.arm == "C":
        os.environ["QUPRS_STAGE_LEDGER"] = "1"
    else:
        os.environ.pop("QUPRS_STAGE_LEDGER", None)
    start = time.perf_counter_ns()
    raw = _pathsum_rust.check_equivalence(str(p1), str(p2), method="hybrid",
                                          strategy="Proportional", tool_name="gpmc",
                                          timeout=75)
    wall = time.perf_counter_ns() - start
    led = raw.get("stage_ledger")
    assert (led is not None) == (a.arm == "C")
    assert raw["status"] in EQUIVALENT, raw["status"]
    if led:
        assert not led["has_stage_overlap"], "overlapping stages"
        assert abs(led["closure_error_seconds"]) < 1e-6
        for s in led["structural_elim_attempts"]:
            assert s["k_r"] <= s["v_r"]
            assert s["w_redundant_estimated"] == max(s["k_r"] - 1, 0) * s["l_r"]
    print(json.dumps({
        "arm": a.arm, "case": a.case, "classification": raw["status"],
        "ffi_wall_ns": wall, "native_wall_s": raw.get("verification_time_sec"),
        "native_pathsum_s": raw.get("pathsum_time_sec"),
        "native_wmc_s": raw.get("wmc_time_sec"), "stage_ledger": led,
        "extension_path": str(_pathsum_rust.__file__)}, sort_keys=True))


def boot_paired(samples, case, denominator, numerator):
    round_keys = sorted(set(s["round"] for s in samples if
                            s["case"] == case and not s["warmup"]))
    ratios = []
    for r in round_keys:
        group = {s["arm"]: s["data"] for s in samples if
                 s["case"] == case and s["round"] == r and
                 not s["warmup"] and "data" in s}
        if denominator in group and numerator in group:
            if group[denominator]["classification"] == group[numerator]["classification"]:
                ratios.append(group[numerator]["ffi_wall_ns"] /
                              group[denominator]["ffi_wall_ns"])
    if not ratios:
        return {"pairs": 0, "status": "INCOMPLETE"}
    rnd = random.Random(112057)
    resampled = sorted(statistics.median([ratios[rnd.randrange(len(ratios))]
                                         for _ in ratios]) for _ in range(2000))
    return {"pairs": len(ratios), "median_ratio": statistics.median(ratios),
            "bootstrap_95_percent": [resampled[49], resampled[1949]],
            "ratio_definition": numerator + "/" + denominator}


def run(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = {
        "schema": "quprs-structural-overhead-abc-v0",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "a_expected": A_SHA, "b_expected": B_SHA,
        "a_git": cmd("git", "-C", a.source_a, "rev-parse", "HEAD"),
        "b_git": cmd("git", "-C", a.source_b, "rev-parse", "HEAD"),
        "runner_git": cmd("git", "-C", a.checkout, "rev-parse", "HEAD"),
        "a_gpmc_gitlink": cmd("git", "-C", a.source_a, "rev-parse", "HEAD:GPMC"),
        "b_gpmc_gitlink": cmd("git", "-C", a.source_b, "rev-parse", "HEAD:GPMC"),
        "solver": str(Path(a.solver).resolve()), "solver_sha256": sha256(a.solver),
        "python_a": cmd(a.python_a, "--version"),
        "python_b": cmd(a.python_b, "--version"),
        "pip_freeze_a": cmd(a.python_a, "-m", "pip", "freeze"),
        "pip_freeze_b": cmd(a.python_b, "-m", "pip", "freeze"),
        "platform": platform.platform(), "lscpu": cmd("lscpu"),
        "cpu_count": os.cpu_count(), "python": sys.version,
        "rounds": a.rounds, "warmups": a.warmup,
        "method": "hybrid", "strategy": "Proportional", "solver_name": "gpmc",
        "backend": "rust", "solver_timeout_seconds": 75,
        "hard_call_timeout": a.hard_timeout, "case_budget": a.case_budget,
        "case_input_sha256": {
            k: [{"file": str(p), "sha256": sha256(p)} for p in circuits(a.bench, k)]
            for k in CIRCUITS},
    }
    write_json(out / "environment.json", env)
    if env["a_git"]["out"] != A_SHA or env["b_git"]["out"] != B_SHA:
        raise RuntimeError("wrong source revision")
    if env["a_gpmc_gitlink"]["out"] != env["b_gpmc_gitlink"]["out"]:
        raise RuntimeError("GPMC source gitlink differs")
    if env["python_a"]["out"] != env["python_b"]["out"]:
        raise RuntimeError("Python interpreter versions differ")
    freeze_a = [x for x in env["pip_freeze_a"]["out"].splitlines()
                if not x.lower().startswith("quprs==")]
    freeze_b = [x for x in env["pip_freeze_b"]["out"].splitlines()
                if not x.lower().startswith("quprs==")]
    if freeze_a != freeze_b:
        raise RuntimeError("installed package set differs")
    affinity = sorted(os.sched_getaffinity(0))
    if affinity:
        os.sched_setaffinity(0, {affinity[0]})
        env["fixed_cpu_affinity"] = affinity[0]
        write_json(out / "environment.json", env)

    rng = random.Random(112057)
    samples, failures = [], []
    with (out / "samples.jsonl").open("w", buffering=1) as raw:
        for case in CIRCUITS:
            started = time.monotonic()
            for round_no in range(-a.warmup, a.rounds):
                if time.monotonic() - started >= a.case_budget:
                    failures.append({"case": case, "reason": "CASE_BUDGET_EXCEEDED"})
                    break
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    executable = a.python_a if arm == "A" else a.python_b
                    command = [executable, str(Path(__file__).resolve()), "--one",
                               "--arm", arm, "--case", case, "--bench", a.bench]
                    childenv = dict(os.environ)
                    childenv["QUPRS_GPMC_PATH"] = str(Path(a.solver).resolve())
                    childenv["QUPRS_STAGE_LEDGER"] = "1" if arm == "C" else "0"
                    row = {"case": case, "round": round_no,
                           "warmup": round_no < 0, "arm": arm,
                           "utc": datetime.now(timezone.utc).isoformat()}
                    start = time.perf_counter()
                    try:
                        p = subprocess.run(command, cwd="/tmp", env=childenv,
                                           text=True, capture_output=True,
                                           timeout=a.hard_timeout)
                        row.update(exit=p.returncode,
                                   process_wall_s=time.perf_counter()-start,
                                   stderr_tail=p.stderr[-3000:])
                        if p.returncode == 0:
                            row["data"] = json.loads(p.stdout)
                            assert row["data"]["arm"] == arm
                        else:
                            row["error"] = "FAILED_PROCESS"
                            row["stdout_tail"] = p.stdout[-1500:]
                    except subprocess.TimeoutExpired:
                        row.update(error="HARD_TIMEOUT", exit=None,
                                   process_wall_s=time.perf_counter()-start)
                    except Exception as e:
                        row.update(error="INVALID_RAW_DATA", detail=repr(e))
                    raw.write(json.dumps(row, sort_keys=True) + "\n")
                    samples.append(row)
                    print("ABC", case, round_no, arm,
                          "OK" if "data" in row else row.get("error"), flush=True)
                    if "data" not in row:
                        failures.append({key: row.get(key) for key in
                                         ("case", "round", "arm", "error", "stderr_tail")})
                if failures:
                    break
            if failures:
                break

    by_case = {}
    complete = not failures
    lines = ["# Structural Probe A/B/C Native Rust Timing", "",
             "| Case | A | B | C | B/A median (bootstrap CI) | C/B median (bootstrap CI) |",
             "|---|---:|---:|---:|---|---|"]
    for case in CIRCUITS:
        relevant = [s for s in samples if s["case"] == case and
                    not s["warmup"] and "data" in s]
        counts = {arm: sum(s["arm"] == arm for s in relevant) for arm in ARMS}
        classifications = {s["data"]["classification"] for s in relevant}
        if any(counts[arm] != a.rounds for arm in ARMS) or len(classifications) != 1:
            complete = False
        pairs_ab = boot_paired(samples, case, "A", "B")
        pairs_bc = boot_paired(samples, case, "B", "C")
        c_stage = [s["data"]["stage_ledger"] for s in relevant if s["arm"] == "C"]
        by_case[case] = {"count_by_arm": counts, "classifications": sorted(classifications),
                         "B_over_A": pairs_ab, "C_over_B": pairs_bc,
                         "opt_in_structural_samples": [{
                             "elim_attempts": len(x["structural_elim_attempts"]),
                             "total_W_redundant_estimated": sum(
                                 y["w_redundant_estimated"] for y in x["structural_elim_attempts"]),
                             "root_reduction_seconds": x["exclusive_seconds"]["reduction"]
                         } for x in c_stage]}
        def render(d):
            if not d.get("pairs"):
                return "INCOMPLETE"
            low, high = d["bootstrap_95_percent"]
            return f'{d["median_ratio"]:.4f} ({low:.4f}, {high:.4f})'
        lines.append(f'| {case} | {counts["A"]} | {counts["B"]} | {counts["C"]} | {render(pairs_ab)} | {render(pairs_bc)} |')
    summary = {"schema": env["schema"],
               "status": "COMPLETE_EXPLORATORY" if complete else "INCOMPLETE",
               "failures": failures, "cases": by_case,
               "limitations": [
                   "Same machine and interleaved order, but hosted-CPU noise remains.",
                   "Wall metric is around native FFI call, excludes new Python process startup.",
                   "A and B differ only in PR #57; B and C use the same Rust binary.",
                   "Only C has detailed root reduction timer; no per-Elim elapsed time.",
                   "Two fixed workloads are insufficient to fit a structural predictive model.",
                   "Estimated W does not equal measured saved work or speedup.",
               ]}
    write_json(out / "summary.json", summary)
    lines += ["", "Status: " + summary["status"], "",
              "Raw observations including optional Rust stage ledger are in samples.jsonl.",
              "This exploratory run cannot establish causality or prove zero overhead."]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    return 0 if complete else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--one", action="store_true")
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--case", choices=CIRCUITS)
    parser.add_argument("--bench")
    parser.add_argument("--source-a")
    parser.add_argument("--source-b")
    parser.add_argument("--checkout")
    parser.add_argument("--python-a")
    parser.add_argument("--python-b")
    parser.add_argument("--solver")
    parser.add_argument("--out")
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--hard-timeout", type=int, default=95)
    parser.add_argument("--case-budget", type=int, default=1080)
    args = parser.parse_args()
    try:
        sys.exit(once(args) if args.one else run(args))
    except Exception as exc:
        if args.out and not args.one:
            Path(args.out).mkdir(parents=True, exist_ok=True)
            write_json(Path(args.out) / "fatal.json",
                       {"status": "INCOMPLETE", "error": repr(exc)})
        raise
