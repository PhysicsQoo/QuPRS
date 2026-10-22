#!/usr/bin/env python3
"""Bounded, isolated RSS/wall-time measurements for existing CI examples.

Examples (opt-in; do not run inside CodSpeed's timed measurements):

  python scripts/profile_benchmark_resources.py --case grover4 --output grover4.json
  python scripts/profile_benchmark_resources.py --case qaoa7 --output qaoa7.json
  python scripts/profile_benchmark_resources.py --case qft16 --output qft16.json
  python scripts/profile_benchmark_resources.py --case tof3 --output tof3.json

The peak is *sampled aggregate process-tree RSS*, not an exact instantaneous
peak or a certified upper bound. Short-lived solver processes can be missed.
Use these observations only alongside CI runner, source, and solver identity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))

# Every case is taken from the current benchmark catalog; there is no new
# untested large-circuit workload and no paper-wide Cartesian product.
_CASE_NAMES = {
    "grover4": ("mqt", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"),
    "qaoa7": ("mqt", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"),
    "qft16": ("mqt", "qft_nativegates_ibm_qiskit_opt0_16.qasm"),
    "vqe4": ("mqt", "vqe_nativegates_ibm_qiskit_opt0_4.qasm"),
    "tof3": ("feynman", "tof_3.qasm"),
}


def resolve_case(name: str) -> dict:
    from _benchmark_cases import FEYNMAN_CASES, MQT_CASES

    cohort, basename = _CASE_NAMES[name]
    cases = MQT_CASES if cohort == "mqt" else FEYNMAN_CASES
    matched = [row for row in cases if row[0] == basename]
    if len(matched) != 1:
        raise ValueError(f"Missing or duplicated CI benchmark: {name}")
    filename, strategy, switch = matched[0]
    folder = ROOT / "benchmarks" / ("MQTBench" if cohort == "mqt" else "Feynman")
    basis = "h,ry,rz,cx" if cohort == "mqt" else "h,y,z,t,tdg,cx"
    source, transpiled = folder / filename, folder / basis / filename
    if switch:
        source, transpiled = transpiled, source
    return dict(
        case=name, cohort=cohort, source=str(source), transpiled=str(transpiled),
        strategy=strategy, method="hybrid" if cohort == "mqt" else "reduction_rules",
    )


def sample_tree_rss(pid: int) -> int:
    """Best-effort sum of live parent/descendant RSS at one instant."""
    import psutil

    try:
        parent = psutil.Process(pid)
        processes = [parent] + parent.children(recursive=True)
    except psutil.Error:
        return 0
    total = 0
    for process in processes:
        try:
            total += process.memory_info().rss
        except psutil.Error:
            continue
    return total


def stop_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait(timeout=5)


def run_limited(command: list[str], *, deadline: float, rss_cap: int,
                sample_seconds: float) -> dict:
    """Run an isolated worker with independent time/RSS bounds."""
    if deadline <= 0 or rss_cap <= 0 or sample_seconds <= 0:
        raise ValueError("Resource limits and sample interval must be positive")
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                   start_new_session=os.name == "posix")
        begin = time.monotonic()
        max_rss = 0
        reason = None
        try:
            while process.poll() is None:
                max_rss = max(max_rss, sample_tree_rss(process.pid))
                if max_rss > rss_cap:
                    reason = "rss_limit_exceeded"
                    break
                if time.monotonic() - begin > deadline:
                    reason = "walltime_limit_exceeded"
                    break
                time.sleep(sample_seconds)
            max_rss = max(max_rss, sample_tree_rss(process.pid))
        finally:
            if reason is not None or process.poll() is None:
                stop_group(process)
        elapsed = time.monotonic() - begin
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read()[-2000:]
        errors = stderr.read()[-2000:]
        return dict(
            exit_code=process.returncode, elapsed_seconds=round(elapsed, 6),
            sampled_peak_tree_rss_bytes=max_rss,
            sampled_peak_tree_rss_mib=round(max_rss / (1024**2), 3),
            resource_limit_status=reason,
            stdout_tail=output, stderr_tail=errors,
        )


def worker(name: str, solver_timeout: int) -> int:
    from QuPRS import check_equivalence

    case = resolve_case(name)
    kwargs = dict(method=case["method"], backend="python",
                  strategy=case["strategy"], timeout=solver_timeout)
    if case["method"] != "reduction_rules":
        kwargs["tool_name"] = "gpmc"
    result = check_equivalence(case["source"], case["transpiled"], **kwargs)
    status = str(result.equivalent)
    print("BENCH_RESOURCE_RESULT=" + json.dumps({
        "status": status, "accepted_positive": status in {"equivalent", "equivalent*"},
        "solver_time": getattr(result, "tool_time", None),
    }, default=str), flush=True)
    return 0 if status in {"equivalent", "equivalent*"} else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(_CASE_NAMES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--walltime-seconds", type=int, default=90)
    parser.add_argument("--solver-timeout-seconds", type=int, default=45)
    parser.add_argument("--memory-limit-mib", type=int, default=3072)
    parser.add_argument("--sample-interval-ms", type=int, default=100)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.walltime_seconds < 10 or args.solver_timeout_seconds < 1:
        parser.error("Wall-time must be >=10s and solver timeout >=1s")
    if args.solver_timeout_seconds >= args.walltime_seconds:
        parser.error("Solver timeout must be less than wall-time budget")
    if args.memory_limit_mib < 64 or args.sample_interval_ms < 10:
        parser.error("Memory limit >=64 MiB and interval >=10 ms required")
    if args.worker:
        return worker(args.case, args.solver_timeout_seconds)
    case = resolve_case(args.case)
    command = [sys.executable, str(Path(__file__).resolve()),
               "--case", args.case, "--output", str(args.output),
               "--walltime-seconds", str(args.walltime_seconds),
               "--solver-timeout-seconds", str(args.solver_timeout_seconds),
               "--memory-limit-mib", str(args.memory_limit_mib),
               "--sample-interval-ms", str(args.sample_interval_ms), "--worker"]
    result = run_limited(command, deadline=args.walltime_seconds,
                         rss_cap=args.memory_limit_mib * 1024**2,
                         sample_seconds=args.sample_interval_ms / 1000)
    tail = result.pop("stdout_tail")
    for line in tail.splitlines():
        if line.startswith("BENCH_RESOURCE_RESULT="):
            try:
                result["verdict"] = json.loads(line.split("=", 1)[1])
            except json.JSONDecodeError:
                pass
    result["stderr_tail"] = result["stderr_tail"][:600]
    result.update({
        "case": case, "source_revision": os.getenv("GITHUB_SHA"),
        "hostname_platform": platform.platform(), "python": platform.python_version(),
        "runner_os": os.getenv("RUNNER_OS"), "runner_arch": os.getenv("RUNNER_ARCH"),
        "runner_image": os.getenv("ImageOS"),
        "runner_image_version": os.getenv("ImageVersion"),
        "cpu_count": os.cpu_count(),
        "rss_limit_mib": args.memory_limit_mib,
        "deadline_seconds": args.walltime_seconds,
        "solver_timeout_seconds": args.solver_timeout_seconds,
        "sample_interval_ms": args.sample_interval_ms,
        "complete": result["resource_limit_status"] is None and
                    result["exit_code"] == 0 and
                    result.get("verdict", {}).get("accepted_positive") is True,
        "measurement_note": "sampled process-tree RSS, not precise instantaneous peak",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": args.case, "complete": result["complete"],
                      "elapsed_seconds": result["elapsed_seconds"],
                      "sampled_peak_tree_rss_mib": result["sampled_peak_tree_rss_mib"],
                      "resource_limit_status": result["resource_limit_status"]}, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())