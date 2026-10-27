"""Three TACAS source-QASM Hybrid/GPMC paper-timeout followups; evidence only."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks" / "MQTBench"
OUT = ROOT / "paper-timeout-followup-evidence"
CASES = {
    "qft20_normal": ("qft_nativegates_ibm_qiskit_opt0_20.qasm", "h,ry,rz,cx"),
    "qft20_injected": ("qft_nativegates_ibm_qiskit_opt0_20.qasm", "Random_Rotation"),
    "qpeexact8_injected": ("qpeexact_nativegates_ibm_qiskit_opt0_8.qasm", "Random_Rotation"),
}
INNER_TIMEOUT = 200
OUTER_TIMEOUT = 220
MEMORY_MIB = 5120

def pair(case):
    name, target = CASES[case]
    return CORPUS / name, CORPUS / target / name

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def worker(case):
    from QuPRS import check_equivalence, config
    config.set_tolerance(1e-10)
    a, b = pair(case)
    started = time.monotonic()
    try:
        result = check_equivalence(
            str(a), str(b), method="hybrid", strategy="Proportional",
            tool_name="gpmc", backend="python", timeout=INNER_TIMEOUT,
            wmc_policy="legacy", wmc_magnitude_tolerance=1e-8,
            wmc_phase_tolerance=1e-8,
        )
        stat = getattr(result, "Statistics", None)
        row = {
            "case": case, "verdict": str(result.equivalent),
            "wall_seconds": time.monotonic() - started,
            "verification_time": result.verification_time,
            "pathsum_time": result.pathsum_time,
            "solver_time": result.tool_time,
            "solver_invoked": result.tool_time is not None,
            "log_wmc": result.log_wmc, "expected_log2": result.expect,
            "reduction_counts": stat.get_reduction_counts() if stat else None,
        }
        print("PAPER_200S_RESULT=" + json.dumps(row, sort_keys=True, default=str), flush=True)
        return 0
    except Exception as exc:
        print("PAPER_200S_RESULT=" + json.dumps({
            "case": case, "verdict": "EXECUTION_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "wall_seconds": time.monotonic() - started,
        }), flush=True)
        return 2

def rss(pid):
    import psutil
    try:
        p = psutil.Process(pid)
        return sum(x.memory_info().rss for x in [p] + p.children(recursive=True)
                   if x.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
        return 0

def execute(case):
    start = time.monotonic()
    cmd = [sys.executable, "-u", __file__, "--worker", case]
    with tempfile.TemporaryFile(mode="w+t", encoding="utf8") as f_out, tempfile.TemporaryFile(mode="w+t", encoding="utf8") as f_err:
        proc = subprocess.Popen(
            cmd, cwd=ROOT, stdout=f_out, stderr=f_err,
            start_new_session=(os.name == "posix"),
        )
        peak, constraint = 0, None
        while proc.poll() is None:
            peak = max(peak, rss(proc.pid))
            if peak > MEMORY_MIB * 1024**2:
                constraint = "RESOURCE_MEMORY_CAP"
            elif time.monotonic() - start > OUTER_TIMEOUT:
                constraint = "OUTER_TIMEOUT"
            if constraint:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
                break
            time.sleep(0.1)
        f_out.seek(0)
        f_err.seek(0)
        stdout, stderr = f_out.read(), f_err.read()
    marker = "PAPER_200S_RESULT="
    row = {}
    if marker in stdout:
        try:
            row = json.loads(stdout.rsplit(marker, 1)[1].splitlines()[0])
        except (ValueError, IndexError):
            pass
    row.update({
        "case": case, "process_exit_code": proc.returncode,
        "outer_wall_seconds": round(time.monotonic() - start, 6),
        "sampled_peak_process_tree_rss_mib": round(peak / 1024**2, 3),
        "resource_constraint": constraint, "stderr_tail": stderr[-1200:],
        "stdout_tail": stdout[-600:] if not row.get("verdict") else "",
    })
    verdict = row.get("verdict")
    if constraint or proc.returncode != 0 or not verdict or verdict == "EXECUTION_ERROR":
        row["scientific_class"] = "EXECUTION_OR_RESOURCE_BLOCKED"
    elif verdict in ("Timeout", "MemoryOut", "unknown"):
        row["scientific_class"] = "INCONCLUSIVE"
    elif verdict in ("equivalent", "equivalent*", "not_equivalent"):
        row["scientific_class"] = "DETERMINATE"
    else:
        row["scientific_class"] = "UNEXPECTED_VERDICT"
    return row

def main():
    OUT.mkdir(exist_ok=True)
    identity = {}
    for name in CASES:
        a, b = pair(name)
        if not a.is_file() or not b.is_file():
            raise FileNotFoundError((name, a, b))
        identity[name] = {
            "left": str(a.relative_to(ROOT)), "left_sha256": sha(a),
            "right": str(b.relative_to(ROOT)), "right_sha256": sha(b),
        }
    manifest = {
        "source_sha": os.environ.get("GITHUB_SHA"),
        "source_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "original_paper_artifact_commit": "e928abc47dd15926364ec77905eb0d5dc92ce8cc",
        "python": sys.version, "platform": platform.platform(),
        "source_pairs": identity, "backend": "python", "method": "hybrid",
        "strategy": "Proportional", "solver": "gpmc", "wmc_policy": "legacy",
        "rr_tolerance": 1e-10, "wmc_magnitude_tolerance": 1e-8,
        "wmc_phase_tolerance": 1e-8,
        "solver_timeout_seconds": INNER_TIMEOUT,
        "worker_timeout_seconds": OUTER_TIMEOUT,
        "memory_limit_mib": MEMORY_MIB,
        "limitations": "GitHub hosted VM != paper Azure E8ads v5/64 GiB; three-case subset only",
    }
    (OUT / "provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rows = []
    for case in CASES:
        row = execute(case)
        rows.append(row)
        (OUT / f"{case}.json").write_text(
            json.dumps(row, indent=2, sort_keys=True, default=str) + "\n")
        print("PAPER_200S_OBSERVATION=" + json.dumps({
            key: row.get(key) for key in (
                "case", "verdict", "scientific_class",
                "outer_wall_seconds", "resource_constraint",
                "sampled_peak_process_tree_rss_mib",
            )
        }, sort_keys=True), flush=True)
    summary = {
        "source_sha": os.environ.get("GITHUB_SHA"),
        "planned": len(CASES), "observed": len(rows),
        "determinate": sum(r["scientific_class"] == "DETERMINATE" for r in rows),
        "inconclusive": sum(r["scientific_class"] == "INCONCLUSIVE" for r in rows),
        "execution_resource_blocked": sum(r["scientific_class"] == "EXECUTION_OR_RESOURCE_BLOCKED" for r in rows),
        "case_verdicts": {r["case"]: r.get("verdict") for r in rows},
        "full_paper_reproduction": False,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print("PAPER_200S_SUMMARY=" + json.dumps(summary, sort_keys=True), flush=True)
    return 2 if summary["execution_resource_blocked"] else 0

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        raise SystemExit(worker(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit("Usage: followup_200s.py [--worker CASE]")
    raise SystemExit(main())
