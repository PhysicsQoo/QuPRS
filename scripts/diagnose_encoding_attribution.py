#!/usr/bin/env python3
"""Classify GHZ32/Graphstate16 hybrid routing and 9/17-digit Ganak encoding cost.

Diagnostics only. Uses the pinned QuPRS Ganak 2.8.0 --mode=6 binary throughout.
Creates no baseline and never changes release gates or production settings.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "MQTBench"
CASES = [
    ("ghz32", "ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
    ("graphstate16", "graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def circuit_inputs(filename, switch):
    original = BENCH / filename
    decomposed = BENCH / "h,ry,rz,cx" / filename
    return (decomposed, original) if switch else (original, decomposed)


def verify_case(case, call_diagnostics):
    from QuPRS import check_equivalence
    import QuPRS.utils.ganak_distribution as distribution

    name, filename, strategy, switch = case
    original = distribution.binary_diagnostics
    calls = []

    def intercept(*args, **kwargs):
        started = time.perf_counter_ns()
        try:
            if call_diagnostics:
                return original(*args, **kwargs)
            return {"diagnostic_bypassed_for_measurement": True}
        finally:
            calls.append((time.perf_counter_ns() - started) / 1e6)

    circuit_a, circuit_b = circuit_inputs(filename, switch)
    distribution.binary_diagnostics = intercept
    start = time.perf_counter_ns()
    try:
        result = check_equivalence(
            str(circuit_a), str(circuit_b), method="hybrid",
            strategy=strategy, backend="rust", tool_name="ganak",
            timeout=90)
    finally:
        distribution.binary_diagnostics = original
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    return {
        "elapsed_ms": elapsed_ms,
        "python_binary_diagnostics_ms": sum(calls),
        "python_binary_diagnostics_calls": len(calls),
        "wmc_time": result.wmc_time,
        "tool_time": result.tool_time,
        "status": result.equivalent,
        "pathsum_time": result.pathsum_time,
        "diagnostics_enabled": call_diagnostics,
    }


def classify(case, rounds):
    # Alternating order avoids conflating warm caches with the instrumentation.
    verify_case(case, True)  # warmup
    samples = {"enabled": [], "disabled": []}
    for r in range(rounds):
        for enabled in ((True, False) if r % 2 == 0 else (False, True)):
            s = verify_case(case, enabled)
            samples["enabled" if enabled else "disabled"].append(s)
    all_samples = samples["enabled"] + samples["disabled"]
    if any(s["status"] not in ("equivalent", "equivalent*") for s in all_samples):
        raise RuntimeError("Hybrid equivalence result changed")
    if any(s["python_binary_diagnostics_calls"] != 1 for s in all_samples):
        raise RuntimeError("Expected one Python packaged Ganak diagnostics call")
    return {
        "samples": samples,
        "wmc_called": any(s["wmc_time"] is not None for s in all_samples),
        "medians_ms": {
            k: statistics.median(s["elapsed_ms"] for s in values)
            for k, values in samples.items()
        },
        "median_diagnostics_ms": statistics.median(
            s["python_binary_diagnostics_ms"] for s in samples["enabled"]),
    }


def capture_worker(case, directory):
    from QuPRS import check_equivalence

    name, filename, strategy, switch = case
    circuit_a, circuit_b = circuit_inputs(filename, switch)
    try:
        check_equivalence(
            str(circuit_a), str(circuit_b), method="wmc_only",
            strategy=strategy, backend="rust", tool_name="ganak",
            timeout=60)
    except Exception as exc:
        if "DIAGNOSTIC_CAPTURE_COMPLETE" not in str(exc):
            raise
    captures = sorted(Path(directory).glob("ganak_*.cnf"))
    if len(captures) != 1:
        raise RuntimeError(f"Expected exactly one forced-WMC CNF; got {len(captures)}")
    print(f"Captured forced-WMC CNF: {captures[0]}", flush=True)


def capture(case, decimals, folder, timeout):
    folder.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "QUPRS_DIAG_CAPTURE_DIR": str(folder.resolve()),
        "QUPRS_DIAG_CAPTURE_ONLY": "1",
        "QUPRS_DIAG_GANAK_DECIMALS": str(decimals),
    })
    proc = subprocess.run(
        [sys.executable, __file__, "--worker",
         case[0], "--worker-dir", str(folder.resolve())],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    files = list(folder.glob("ganak_*.cnf"))
    if proc.returncode != 0 or len(files) != 1:
        raise RuntimeError(
            f"{case[0]} capture {decimals} failed: rc={proc.returncode} "
            f"n_cnfs={len(files)} stdout={proc.stdout[-1500:]} stderr={proc.stderr[-1500:]}")
    target = folder.parent / f"{case[0]}_ganak_{decimals}dec.cnf"
    files[0].replace(target)
    return target


WEIGHT = re.compile(r"^c p weight (-?\d+) (.*)$")


def analyze_cnf(path):
    weights, clauses, header = {}, [], None
    with path.open() as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("p cnf "):
                header = line
            elif line.startswith("c p weight "):
                match = WEIGHT.fullmatch(line)
                if not match:
                    raise ValueError("Invalid weight: " + line)
                literal, payload = match.groups()
                if literal in weights:
                    raise ValueError("Duplicate weight: " + literal)
                body = payload.removesuffix(" 0").replace(" ", "").replace("i", "j")
                body = body.replace("+-", "-")
                weights[literal] = {
                    "text": payload,
                    "real": complex(body).real,
                    "imag": complex(body).imag,
                }
            elif line and not line.startswith("c "):
                clauses.append(line)
    if header is None:
        raise RuntimeError("Missing DIMACS header")
    return {"header": header, "clauses": sorted(clauses), "weights": weights}


def compare_cnfs(old, new):
    a, b = analyze_cnf(old), analyze_cnf(new)
    literals_a, literals_b = set(a["weights"]), set(b["weights"])
    common = sorted(literals_a & literals_b, key=int)
    deltas, changed_text, changed_numeric = [], 0, 0
    for lit in common:
        w, v = a["weights"][lit], b["weights"][lit]
        diff = abs(complex(w["real"], w["imag"]) - complex(v["real"], v["imag"]))
        changed_text += (w["text"] != v["text"])
        changed_numeric += (diff != 0)
        if diff:
            deltas.append({"literal": lit, "absolute_delta": diff,
                           "old": w, "new": v})
    return {
        "old_sha256": sha256(old),
        "new_sha256": sha256(new),
        "header_equal": a["header"] == b["header"],
        "clauses_equal_sorted": a["clauses"] == b["clauses"],
        "weight_literals_equal": literals_a == literals_b,
        "n_clauses": len(a["clauses"]),
        "n_weights_old": len(literals_a),
        "n_weights_new": len(literals_b),
        "weight_text_changed": changed_text,
        "weight_values_changed": changed_numeric,
        "max_weight_abs_delta": max((x["absolute_delta"] for x in deltas), default=0.0),
        "changed_numeric_examples": deltas[:8],
        "canonical_structure_equal": a["header"] == b["header"] and
          a["clauses"] == b["clauses"] and literals_a == literals_b,
        "notes": [
            "Weights are sorted by literal and clauses by exact text because Rust HashMap order may change.",
            "Both variants are serialized from PR #24's identical encoder state; 9 digits reproduce main serializer.",
            "This isolates serialization precision, not every possible baseline build/dependency difference."
        ],
    }


def run_solver(binary, cnf, timeout):
    from QuPRS.utils.wmc_solvers import parse_count_line
    t = time.perf_counter()
    try:
        result = subprocess.run(
            [str(binary), "--mode=6", str(cnf)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"elapsed_sec": time.perf_counter() - t, "timeout": True}
    val, line = None, None
    for candidate in result.stdout.splitlines():
        if candidate.startswith("c s exact"):
            line = candidate
            try:
                parsed = parse_count_line(candidate)
                val = [parsed.real, parsed.imag] if parsed is not None else None
            except Exception as exc:
                line += " [parse error: " + str(exc) + "]"
            break
    return {
        "elapsed_sec": time.perf_counter() - t, "returncode": result.returncode,
        "count": val, "count_line": line,
        "stderr_tail": result.stderr[-500:],
    }


def solver_comparison(binary, old, new, rounds, timeout):
    cases = {"9": old, "17": new}
    values = {"9": [], "17": []}
    for r in range(rounds):
        for decimals in (("9", "17") if r % 2 == 0 else ("17", "9")):
            observation = run_solver(binary, cases[decimals], timeout)
            values[decimals].append(observation)
            print(f"round={r+1} precision={decimals} "
                  f"seconds={observation['elapsed_sec']:.6f} "
                  f"returncode={observation.get('returncode')}", flush=True)
    summary = {}
    for d, records in values.items():
        completed = [x for x in records if x.get("returncode") == 0 and x.get("count") is not None]
        summary[d] = {
            "ok": len(completed), "total": len(records),
            "median_seconds": statistics.median(x["elapsed_sec"] for x in completed) if completed else None,
            "count": completed[0]["count"] if completed else None,
            "timeouts": sum(bool(x.get("timeout")) for x in records),
        }
    c9, c17 = summary["9"]["count"], summary["17"]["count"]
    rel = None
    if c9 is not None and c17 is not None:
        z9, z17 = complex(*c9), complex(*c17)
        rel = abs(z9-z17)/max(abs(z17), 1.0)
    return {"samples": values, "summary": summary, "relative_count_difference": rel}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("attribution-report/report.json"))
    p.add_argument("--samples", type=int, default=5)
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--capture-timeout", type=int, default=90)
    p.add_argument("--worker")
    p.add_argument("--worker-dir")
    args = p.parse_args()
    os.chdir(ROOT)
    if args.worker:
        case = next(x for x in CASES if x[0] == args.worker)
        capture_worker(case, args.worker_dir)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    from QuPRS.utils import WMC
    print("First classify real hybrid routing before any forced-WMC measurement.", flush=True)
    route = {}
    for case in CASES:
        route[case[0]] = classify(case, args.samples)
        print(case[0], "wmc_called=", route[case[0]]["wmc_called"],
              "median_ms=", route[case[0]]["medians_ms"], flush=True)
    report = {
        "experiment": "Ganak 2.8.0 fixed: hybrid routing, Rust weight precision 9 vs 17, wrapper diagnostics",
        "head_sha": os.getenv("GITHUB_SHA"),
        "python": sys.version,
        "platform": platform.platform(),
        "cpu": platform.processor(),
        "hybrid": route,
        "cases": {},
        "limitations": [
            "The forced wmc_only phase is separate from the hybrid benchmark path.",
            "Only serializer precision is varied; source-level comparison shows reductions and clauses unchanged.",
            "Walltimes are subject to host noise. Syscall/provenance overhead is separately sampled.",
        ],
    }
    with WMC("ganak") as resource:
        binary = Path(resource).resolve()
        report["ganak_executable_sha256"] = sha256(binary)
        version = subprocess.run(
            [str(binary), "--version"], text=True, capture_output=True, timeout=12)
        report["ganak_version_output"] = (version.stdout + version.stderr)[-1200:]
        if version.returncode != 0:
            raise RuntimeError("Ganak --version failed")
        for case in CASES:
            name = case[0]
            print(f"Capturing {name} 9 and 17 decimal inputs", flush=True)
            cnfs = {}
            for decimals in (9, 17):
                cnfs[str(decimals)] = capture(
                    case, decimals, args.output.parent / f"tmp-{name}-{decimals}",
                    args.capture_timeout)
            structural = compare_cnfs(cnfs["9"], cnfs["17"])
            solving = solver_comparison(
                binary, cnfs["9"], cnfs["17"], args.samples, args.timeout)
            report["cases"][name] = {
                "input_sha256": {str(p): sha256(p) for p in circuit_inputs(case[1], case[3])},
                "cnfs": {str(k): {"path": str(v), "sha256": sha256(v),
                                  "size": v.stat().st_size} for k, v in cnfs.items()},
                "comparison": structural, "solver": solving,
            }
            args.output.write_text(json.dumps(report, indent=2) + "\n")
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("FINAL_SUMMARY", json.dumps({
        case: {
            "hybrid_calls_wmc": route[case]["wmc_called"],
            "wrapper_medians_ms": route[case]["medians_ms"],
            "cnf_structure_equal": report["cases"][case]["comparison"]["canonical_structure_equal"],
            "weights_changed": report["cases"][case]["comparison"]["weight_values_changed"],
            "solver_medians": report["cases"][case]["solver"]["summary"],
        } for case in route
    }), flush=True)


if __name__ == "__main__":
    main()
