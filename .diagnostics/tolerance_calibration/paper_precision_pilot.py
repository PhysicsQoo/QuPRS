"""Bounded paper-first numerical tolerance pilot; diagnostic only, no production changes.

Published TACAS paper: Table 2 (36 displayed rows, prose says 35), Table 3(b)
(37 injected rotation cases), and Figure 3(a) Feynman corpus (36 QASMs).
Only a stratified subset is EXECUTED below; all corpus identities are saved.
Not a literal recreation of 200 s results or original Azure host.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tolerance-calibration-results"
OUT.mkdir(parents=True, exist_ok=True)
BASEDIR = ROOT / "benchmarks" / "MQTBench"
FAMILIES = {
    "ghz32": "ghz_nativegates_ibm_qiskit_opt0_32.qasm",
    "graphstate16": "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "qft16": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
    "qft20": "qft_nativegates_ibm_qiskit_opt0_20.qasm",
    "qnn4": "qnn_nativegates_ibm_qiskit_opt0_4.qasm",
    "qpeexact8": "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "qpeinexact8": "qpeinexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "qwalk3": "qwalk-noancilla_nativegates_ibm_qiskit_opt0_3.qasm",
    "vqe4": "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
    "wstate4": "wstate_nativegates_ibm_qiskit_opt0_4.qasm",
}
WMC_ONLY_FOCUS = {"ghz32", "qft16", "qpeexact8", "qaoa7", "graphstate16"}
RR_FOCUS = {"ghz32", "qpeexact8", "graphstate16", "qft16"}
MAGS = (1e-6, 1e-8, 1e-10)
MAX_WORKER_SEC = 9
TOTAL_BUDGET_SEC = 900

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def corpus_manifest():
    normal = {x.name: sha(x) for x in BASEDIR.glob("*.qasm")}
    randoms = {x.name: sha(x) for x in (BASEDIR / "Random_Rotation").glob("*.qasm")}
    transpiled = {x.name: sha(x) for x in (BASEDIR / "h,ry,rz,cx").glob("*.qasm")}
    feyn = {x.name: sha(x) for x in (ROOT / "benchmarks" / "Feynman").glob("*.qasm")}
    # Published Table 2 visually has 36 case rows; wstate32 is in Table 3 but not Table 2.
    paper_table_2 = {k: v for k, v in normal.items() if not k.endswith("_wstate_32.qasm")
                     and k != "wstate_nativegates_ibm_qiskit_opt0_32.qasm"}
    assert len(normal) == 37, ("MQT source drift", len(normal))
    assert len(paper_table_2) == 36, ("Table 2 displayed rows", len(paper_table_2))
    assert len(randoms) == 45, ("Random_Rotation source list", len(randoms))
    assert len(feyn) == 36, ("Feynman source list", len(feyn))
    assert set(normal).issubset(randoms), "Missing random counterpart"
    assert set(normal).issubset(transpiled), "Missing transpiled counterpart"
    for family, filename in FAMILIES.items():
        assert filename in paper_table_2, ("Missing paper target", family, filename)
    manifest = {
        "published_prose_claim_table2": 35,
        "visually_counted_table2_rows": len(paper_table_2),
        "table3b_injected_instances": len(normal),
        "table3b_random_source_files_in_repo": len(randoms),
        "feynman_original_instances": len(feyn),
        "historical_git_source_commit": "e928abc47dd15926364ec77905eb0d5dc92ce8cc",
        "note": "Historical and candidate QASM Git blob SHAs independently compared beforehand; "
                "manifest preserves all current original input file SHA256.",
        "mqt_normal": normal, "mqt_paper_table2": paper_table_2,
        "mqt_h_ry_rz_cx": transpiled, "mqt_random_rotation": randoms,
        "feynman": feyn,
    }
    (OUT / "paper-tolerance-corpus-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def worker(family, variant, method, magnitude, reduction):
    from QuPRS import check_equivalence, config
    filename = FAMILIES[family]
    lhs = BASEDIR / filename
    targetdir = "Random_Rotation" if variant == "injected" else "h,ry,rz,cx"
    rhs = BASEDIR / targetdir / filename
    assert lhs.is_file() and rhs.is_file()
    config.set_tolerance(reduction)
    start = time.monotonic()
    result = check_equivalence(
        str(lhs), str(rhs), backend="python", method=method,
        strategy="Proportional", tool_name="gpmc",
        timeout=7, wmc_policy="legacy",
        wmc_magnitude_tolerance=magnitude, wmc_phase_tolerance=1e-8,
    )
    log_count = getattr(result, "log_wmc", None)
    expected = getattr(result, "expect", None)
    # Paper-era WMC policy rounds log2(|count|) to 3 decimals BEFORE testing
    # against source config.TOLERANCE=1e-10. Historical phase classification
    # cannot be inferred from these logs alone, so only record magnitude match.
    historical_mag_pass = None
    observed_defect = None
    try:
        if log_count is not None and expected is not None:
            a, b = float(log_count), float(expected)
            if math.isfinite(a) and math.isfinite(b):
                historical_mag_pass = abs(round(a, 3) - b) < 1e-10
                log_gap = (a - b) * math.log(2)
                if -500 < log_gap < 2:
                    observed_defect = -math.expm1(log_gap)
    except (ValueError, OverflowError, TypeError):
        pass
    obj = {
        "family": family, "variant": variant, "method": method,
        "rr_coefficient_tolerance": reduction, "wmc_magnitude_tolerance": magnitude,
        "wmc_phase_tolerance": 1e-8, "verdict": result.equivalent,
        "wall_seconds": time.monotonic() - start,
        "reduction_counts": result.Statistics.get_reduction_counts(),
        "wmc_solver_invoked": result.tool_time is not None,
        "solver_time": result.tool_time, "log_wmc": log_count,
        "expected_log2": expected, "normalized_magnitude_defect_estimate": observed_defect,
        "paper_rounded_log2_magnitude_test": historical_mag_pass,
        "source_sha256": (sha(lhs), sha(rhs)),
    }
    print("PAPER_PILOT_RESULT=" + json.dumps(obj, sort_keys=True, default=str), flush=True)

def rss_tree(pid):
    import psutil
    try:
        p = psutil.Process(pid)
        return sum(q.memory_info().rss for q in [p] + p.children(recursive=True)
                   if q.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0

def run_case(family, variant, method, magnitude, reduction):
    cmd = [sys.executable, "-u", __file__, "--worker", family, variant,
           method, str(magnitude), str(reduction)]
    start = time.monotonic()
    with tempfile.TemporaryFile(mode="w+t") as so, tempfile.TemporaryFile(mode="w+t") as se:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=so, stderr=se,
                             start_new_session=os.name == "posix")
        reason = None
        peak = 0
        while p.poll() is None:
            peak = max(peak, rss_tree(p.pid))
            if peak >= 2200 * 1048576:
                reason = "MEMORY_LIMIT_INCONCLUSIVE"
            elif time.monotonic() - start > MAX_WORKER_SEC:
                reason = "TIMEOUT_INCONCLUSIVE"
            if reason:
                if os.name == "posix":
                    os.killpg(p.pid, signal.SIGKILL)
                else:
                    p.kill()
                p.wait(timeout=5)
                break
            time.sleep(.04)
        so.seek(0); se.seek(0)
        stdout = so.read()
        stderr = se.read()
    data = stdout.split("PAPER_PILOT_RESULT=", 1)
    if len(data) > 1:
        try:
            record = json.loads(data[1].splitlines()[0])
        except (ValueError, IndexError):
            record = {}
    else:
        record = {}
    record.update({
        "family": family, "variant": variant, "method": method,
        "wmc_magnitude_tolerance": magnitude, "rr_coefficient_tolerance": reduction,
        "exit_code": p.returncode, "outer_elapsed_s": time.monotonic() - start,
        "peak_rss_mib": round(peak / 1048576, 3), "resource_limit": reason,
        "process_outcome": ("COMPLETED" if p.returncode == 0 and
                            not reason and "verdict" in record else
                            reason or "EXECUTION_ERROR"),
    })
    if record["process_outcome"] != "COMPLETED":
        record["stderr_tail"] = stderr[-1000:]
        record["stdout_tail"] = stdout[-350:]
    return record

def main():
    corpus = corpus_manifest()
    planned = []
    for family in FAMILIES:
        for tau in MAGS:
            planned.append((family, "normal", "hybrid", tau, 1e-10))
            planned.append((family, "injected", "hybrid", tau, 1e-10))
            if family in WMC_ONLY_FOCUS:
                planned.append((family, "normal", "wmc_only", tau, 1e-10))
        if family in RR_FOCUS:
            for rrtau in (1e-8, 1e-10):
                planned.append((family, "normal", "reduction_rules", 1e-8, rrtau))
    budget_deadline = time.monotonic() + TOTAL_BUDGET_SEC
    results = []
    for i, case in enumerate(planned):
        if time.monotonic() >= budget_deadline:
            results.append({"family": case[0], "variant": case[1], "method": case[2],
                            "wmc_magnitude_tolerance": case[3],
                            "rr_coefficient_tolerance": case[4],
                            "process_outcome": "SKIPPED_BUDGET"})
        else:
            results.append(run_case(*case))
        row = results[-1]
        with (OUT / "paper-tolerance-pilot.jsonl").open("a") as stream:
            stream.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        print("PAPER_PRECISION", json.dumps({k: row.get(k) for k in
              ("family", "variant", "method", "wmc_magnitude_tolerance",
               "rr_coefficient_tolerance", "verdict", "process_outcome")},
              default=str), flush=True)
    by_setting = []
    for variant in ("normal", "injected"):
        for magnitude in MAGS:
            subset = [r for r in results if r["variant"] == variant and
                      r["method"] == "hybrid" and r["wmc_magnitude_tolerance"] == magnitude]
            positive = {"equivalent", "equivalent*"}
            correct = sum((r.get("verdict") in positive if variant == "normal"
                          else r.get("verdict") == "not_equivalent") for r in subset
                          if r["process_outcome"] == "COMPLETED")
            completed = sum(r["process_outcome"] == "COMPLETED" for r in subset)
            by_setting.append({"variant": variant, "magnitude_tau": magnitude,
                               "planned": len(subset), "completed": completed,
                               "paper_expected_direction": correct,
                               "inconclusive": len(subset) - completed})
    outcome = {
        "paper_table_2_row_count": len(corpus["mqt_paper_table2"]),
        "paper_table3b_case_count": len(corpus["mqt_normal"]),
        "paper_feynman_case_count": len(corpus["feynman"]),
        "source_sha": os.getenv("GITHUB_SHA"),
        "planned_trials": len(planned),
        "completed": sum(r["process_outcome"] == "COMPLETED" for r in results),
        "timeout_or_error": sum(r["process_outcome"] != "COMPLETED" for r in results),
        "observations": by_setting,
        "statement": "Stratified 12-family short-deadline pilot only; not all paper "
                     "verdicts/timings reproduced. Original 200s paper limit and "
                     "Azure runner not reproduced. Numerical guard-band only.",
    }
    (OUT / "paper-tolerance-pilot-summary.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n")
    print("PAPER_PRECISION_SUMMARY=" + json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if len(results) == len(planned) else 2

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker(sys.argv[2], sys.argv[3], sys.argv[4],
               float(sys.argv[5]), float(sys.argv[6]))
    else:
        raise SystemExit(main())
