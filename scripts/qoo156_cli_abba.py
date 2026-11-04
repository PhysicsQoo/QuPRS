#!/usr/bin/env python3
"""Interim QOO-156 hosted ABBA CLI overhead measurement, NOT CodSpeed Macro."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import random
import signal
import statistics as stats
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CASES = {
    "single_h": ("benchmarks/qoo156/single_h.qasm",),
    "dual_ghz32": ("benchmarks/MQTBench/ghz_nativegates_ibm_qiskit_opt0_32.qasm",) * 2,
    "dual_qpe8": ("benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",) * 2,
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(binary: Path, inputs: list[Path], case: str) -> dict:
    cmd = [str(binary), *(str(x) for x in inputs), "--timeout", "30", "--quiet"]
    if case != "single_h":
        cmd.extend(["--method", "reduction-rules", "--strategy", "straightforward"])
    started = time.perf_counter_ns()
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError(f"Timed out: {case}")
    elapsed = time.perf_counter_ns() - started
    if process.returncode:
        raise RuntimeError(f"{case}: rc={process.returncode}, stderr={err[-900:]!r}")
    expected = b"Reduced PathSum State" if case == "single_h" else b"equivalent"
    if expected.lower() not in out.lower():
        raise AssertionError(f"Scientific output missing or unexpected: {case}")
    return {"elapsed_ns": elapsed, "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest(), "stdout_bytes": len(out)}

def interval(values: list[float]) -> list[float]:
    rng = random.Random(156)
    medians = sorted(stats.median(rng.choices(values, k=len(values))) for _ in range(4000))
    return [medians[100], medians[3899]]

def measure(case: str, base: Path, head: Path, root: Path, rounds: int,
            budget: float, jitter_budget: float) -> dict:
    sources = [root / x for x in CASES[case]]
    for item in sources:
        if not item.is_file():
            raise FileNotFoundError(f"Missing benchmark fixture: {item}")
    provenance = {str(path.relative_to(root)): digest(path) for path in sources}
    reference = None
    warmups = []
    for n in range(8):
        variant = ("base", "head")[n % 2]
        result = run(base if variant == "base" else head, sources, case)
        reference = reference or result["stdout_sha256"]
        if result["stdout_sha256"] != reference:
            raise AssertionError(f"Base/HEAD scientific output disagrees for {case}")
        warmups.append({"variant": variant, **result})
    trials, paired, base_jitter, head_jitter = [], [], [], []
    for n in range(rounds):
        order = ("base", "head", "head", "base") if n % 2 == 0 else (
            "head", "base", "base", "head")
        samples = []
        for name in order:
            observation = run(base if name == "base" else head, sources, case)
            if observation["stdout_sha256"] != reference:
                raise AssertionError(f"Scientific output changed in {case} round {n}")
            samples.append({"variant": name, **observation})
        a = [x["elapsed_ns"] for x in samples if x["variant"] == "base"]
        b = [x["elapsed_ns"] for x in samples if x["variant"] == "head"]
        delta = (stats.mean(b) - stats.mean(a)) / 1e6
        paired.append(delta)
        base_jitter.append(abs(a[0] - a[1]) / 1e6)
        head_jitter.append(abs(b[0] - b[1]) / 1e6)
        trials.append({"round": n + 1, "order": list(order),
                       "observations": samples, "paired_delta_ms": delta})
    lo, hi = interval(paired)
    jitter = max(stats.median(base_jitter), stats.median(head_jitter))
    if jitter > jitter_budget:
        verdict = "INCONCLUSIVE_NOISY_RUNNER"
    elif lo > budget:
        verdict = "OVER_FIXED_COST_BUDGET"
    elif hi <= budget:
        verdict = "WITHIN_PROVISIONAL_FIXED_COST_BUDGET"
    else:
        verdict = "INCONCLUSIVE_CI_OVERLAPS_BUDGET"
    a_ms = [x["elapsed_ns"] / 1e6 for t in trials for x in t["observations"]
            if x["variant"] == "base"]
    b_ms = [x["elapsed_ns"] / 1e6 for t in trials for x in t["observations"]
            if x["variant"] == "head"]
    return {"case": case, "status": verdict, "qasm_sha256": provenance,
            "scientific_stdout_sha256": reference, "warmups": warmups,
            "trials": trials, "base_median_ms": stats.median(a_ms),
            "head_median_ms": stats.median(b_ms),
            "paired_delta_median_ms": stats.median(paired),
            "paired_delta_bootstrap_ci95_ms": [lo, hi],
            "median_control_jitter_ms": jitter, "budget_ms": budget,
            "max_control_jitter_ms": jitter_budget}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "head", "workspace", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--rounds", type=int, default=30)
    p.add_argument("--budget-ms", type=float, default=3.0)
    p.add_argument("--jitter-ms", type=float, default=1.5)
    opt = p.parse_args()
    if not 10 <= opt.rounds <= 100 or opt.budget_ms <= 0 or opt.jitter_ms <= 0:
        p.error("Expected 10..100 paired blocks and positive budgets")
    base, head, root = opt.base.resolve(), opt.head.resolve(), opt.workspace.resolve()
    for binary in (base, head):
        if not binary.is_file():
            raise FileNotFoundError(binary)
    # Whole harness and every child inherit the same CPU affinity (Linux only).
    affinity_error = None
    if hasattr(os, "sched_getaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        try:
            os.sched_setaffinity(0, {allowed[0]})
        except OSError as exc:
            affinity_error = repr(exc)
    affinity = (sorted(os.sched_getaffinity(0))
                if hasattr(os, "sched_getaffinity") else None)
    result = {"schema": "qoo156-hosted-paired-v1",
              "kind": "hosted_elapsed_not_codspeed_macro",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "base_sha": opt.base_sha, "head_sha": opt.head_sha,
              "base_binary_sha256": digest(base), "head_binary_sha256": digest(head),
              "runner": {"name": os.getenv("RUNNER_NAME"), "os": os.getenv("RUNNER_OS"),
                         "arch": os.getenv("RUNNER_ARCH"), "platform": platform.platform(),
                         "cpu_count": os.cpu_count(), "affinity": affinity,
                         "affinity_error": affinity_error, "python": sys.version},
              "rounds": opt.rounds, "budget_ms": opt.budget_ms,
              "jitter_ms": opt.jitter_ms, "cases": {}}
    unsuccessful = []
    try:
        for case in CASES:
            value = measure(case, base, head, root, opt.rounds,
                            opt.budget_ms, opt.jitter_ms)
            result["cases"][case] = value
            if value["status"] != "WITHIN_PROVISIONAL_FIXED_COST_BUDGET":
                unsuccessful.append(case)
            print(f"{case}: {value['status']}, paired overhead "
                  f"{value['paired_delta_median_ms']:+.3f}ms, "
                  f"CI95={value['paired_delta_bootstrap_ci95_ms']}, "
                  f"jitter={value['median_control_jitter_ms']:.3f}ms", flush=True)
    except Exception as error:
        result["error"] = repr(error)
        raise
    finally:
        opt.output.parent.mkdir(parents=True, exist_ok=True)
        opt.output.write_text(json.dumps(result, indent=2) + "\n")
        lines = [
            "## QOO-156 hosted same-runner ABBA (not CodSpeed Macro)",
            f"Base {opt.base_sha[:12]} / HEAD {opt.head_sha[:12]}, "
            f"{opt.rounds} alternating ABBA/BAAB blocks per case.",
            f"Provisional additive overhead budget: {opt.budget_ms:.1f}ms. "
            "PASS allows bounded overhead, NOT zero regression.",
            "| Case | Base ms | HEAD ms | Paired extra ms | 95% bootstrap CI ms | Jitter ms | Status |",
            "|---|---:|---:|---:|---|---:|---|",
        ]
        for value in result["cases"].values():
            lo, hi = value["paired_delta_bootstrap_ci95_ms"]
            lines.append(f"| {value['case']} | {value['base_median_ms']:.3f} | "
                         f"{value['head_median_ms']:.3f} | "
                         f"{value['paired_delta_median_ms']:+.3f} | "
                         f"[{lo:+.3f}, {hi:+.3f}] | "
                         f"{value['median_control_jitter_ms']:.3f} | {value['status']} |")
        lines.append("Hosted/shared-runner host-to-host drift remains unbounded. "
                     "Raw samples and source hashes are preserved in JSON. "
                     "Never present these results as a CodSpeed Macro certificate.")
        report = "\n".join(lines) + "\n"
        opt.output.with_suffix(".md").write_text(report)
        summary = os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as stream:
                stream.write(report)
    if unsuccessful:
        print("QOO156_HOSTED_ABBA_GATE=NOT_MET", flush=True)
        return 2
    print("QOO156_HOSTED_ABBA_PROVISIONAL_BUDGET=PASS", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
