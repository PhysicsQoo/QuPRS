#!/usr/bin/env python3
"""Experimental QuPRS Python transport and circuit-level comparison.

The long lane uses the current checkout's Rust CNF exporter, then the actual
Python run_wmc API for both solvers. The short lane uses check_equivalence.
Neither lane replaces the default solver or claims certified circuit equivalence.
"""
import argparse
from contextlib import nullcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

from QuPRS import check_equivalence
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process
from QuPRS.utils.solver_adapter import get_solver_adapter
from qiskit import QuantumCircuit
from rawmocs_quprs import registered_rawmocs
from release_native_paired import parse
from release_transfer import CASES, check_count
from regenerate_release import SOURCE, DIGITS

ARMS = ("gpmc", "rawmocs")
LIMIT = 120
AS_BYTES = 3221225472


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(path, report):
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def bounded(argv, seconds):
    return subprocess.run(
        ["timeout", "-k", "2s", str(seconds), "prlimit",
         f"--as={AS_BYTES}", "--", *map(str, argv)],
        capture_output=True, text=True, timeout=seconds + 5,
    )


def measure(arm, digits, raw, gpmc, prefix, action, *, analytic_unsat_control=False):
    """Observe the actual QuPRS runner; supervise both arms identically."""
    row = {"arm": arm, "digits": digits, "status": "IN_PROGRESS"}
    original = solver_process.run
    captures = []

    def observed(command, timeout):
        if captures:
            raise AssertionError("unexpected second solver call")
        cnf = Path(command[-1])
        evidence = prefix.with_suffix(".cnf")
        evidence.write_bytes(cnf.read_bytes())
        row["cnf_sha256"] = digest(evidence)
        row["command"] = command
        assert Path(command[0]).resolve() == (raw if arm == "rawmocs" else gpmc)
        rss = prefix.with_suffix(".rss")
        started = time.monotonic()
        try:
            proc = original(["prlimit", f"--as={AS_BYTES}", "--",
                             "/usr/bin/time", "-f", "%M", "-o", str(rss),
                             *command], timeout=min(timeout, LIMIT))
        finally:
            row["solver_wall_s"] = time.monotonic() - started
        captures.append(proc)
        prefix.with_suffix(".stdout").write_text(proc.stdout)
        prefix.with_suffix(".stderr").write_text(proc.stderr)
        row["exit_code"] = proc.returncode
        if rss.exists():
            try:
                row["peak_rss_kib"] = int(rss.read_text().strip().splitlines()[-1])
            except (ValueError, IndexError):
                pass
        return proc

    ctx = (registered_rawmocs(raw, digits=digits, timeout_ms=LIMIT * 1000,
                              address_space_bytes=None)
           if arm == "rawmocs" else nullcontext())
    started = time.monotonic()
    try:
        with ctx, patch.object(solver_process, "run", observed):
            result = action(arm)
        row.update(result)
        if not captures:
            row["status"] = "NOT_INVOKED" if row.get("verdict") not in ("Timeout", "MemoryOut") else "CENSORED"
        else:
            proc, = captures
            if proc.returncode:
                row["status"] = "CENSORED_EXIT"
            else:
                row.update(parse(proc.stdout, arm))
                if arm == "rawmocs":
                    m, = re.findall(r"^RAWMOCS_COMPLETE route=(\w+) digits=(\d+) bits=(\d+) ", proc.stderr, re.M)
                    assert int(m[1]) == digits
                    assert int(m[2]) == {30: 100, 60: 200, 100: 333, 130: 432}[digits]
                    row["route"], row["bits"] = m[0], int(m[2])
                else:
                    precision = re.findall(r"^c o precision (\d+)\s*$", proc.stdout, re.M)
                    # GPMC can terminate on a Boolean contradiction before
                    # initializing MPFR or printing its precision header. Only
                    # the independently known UNSAT-zero fixture may admit
                    # this omission; do not relax any measured SAT case.
                    if analytic_unsat_control and not precision:
                        assert row["sat"] is False and Fraction(row["real"]) == Fraction(row["imag"]) == 0
                        row["precision_evidence"] = "NOT_APPLICABLE_ANALYTIC_UNSAT"
                    else:
                        assert precision == [str(digits)], (precision, digits)
                        row["precision_evidence"] = "REPORTED"
                assert row.get("peak_rss_kib", 0) > 0
                if "transport_real" in row:
                    assert Fraction(row["transport_real"]) == Fraction(row["real"])
                    assert Fraction(row["transport_imag"]) == Fraction(row["imag"])
                row["status"] = "COMPLETED"
    except solver_process.SolverTimeout as exc:
        row.update(status="CENSORED_TIMEOUT", error=str(exc))
    except Exception as exc:
        code = row.get("exit_code")
        status = ("CENSORED_INTERNAL_TIMEOUT" if arm == "rawmocs" and code == 4 else
                  "RESOURCE_LIMIT" if arm == "rawmocs" and code == 5 else
                  "EXIT_OR_SIGNAL_FAILURE" if code not in (None, 0) else "ERROR")
        row.update(status=status, error=f"{type(exc).__name__}: {str(exc)[:2000]}")
    finally:
        row["end_to_end_s"] = time.monotonic() - started
        save(prefix.with_suffix(".json"), row)
        print("QUPRS_RAWMOCS_ROW", json.dumps(row, sort_keys=True), flush=True)
    return row


def e2e(args, report):
    identity = QuantumCircuit(2)
    eq = QuantumCircuit(2)
    eq.h(0); eq.t(0); eq.tdg(0); eq.h(0)
    neq = QuantumCircuit(2)
    neq.h(0)
    # Short known EQ and NEQ examples. Actual public check_equivalence call.
    for name, circuit, expected in (("eq", eq, "equivalent"), ("neq", neq, "not_equivalent")):
        for method in ("wmc_only", "hybrid"):
            group = {"case": name, "method": method, "expected": expected, "rows": {}}
            report["groups"].append(group)
            for arm in ARMS:
                def action(selected):
                    result = check_equivalence(identity, circuit, method=method,
                        strategy="Naive", backend="python", tool_name=selected,
                        timeout=LIMIT, safe_mode=False, gpmc_precision_digits=30)
                    return {"verdict": result.equivalent,
                            "solver_invoked": result.wmc_solver_invoked,
                            "reported_verification_s": result.verification_time,
                            "pathsum_s": result.pathsum_time,
                            "cnf_s": result.to_DIMACS_time, "tool_s": result.tool_time,
                            "normalization_twice_log2": int(round(2 * result.expect)) if result.expect is not None else None}
                group["rows"][arm] = measure(arm, 30, args.raw, args.gpmc,
                    args.out / f"{name}-{method}-{arm}", action)
                save(args.out / "report.json", report)
            g, r = (group["rows"][a] for a in ARMS)
            group["pass"] = (
                g["verdict"] == r["verdict"] == expected
                and g["status"] == r["status"] in ("COMPLETED", "NOT_INVOKED")
                and g.get("solver_invoked") == r.get("solver_invoked")
                and g.get("cnf_sha256") == r.get("cnf_sha256")
                and (g["status"] != "COMPLETED" or g["sat"] == r["sat"])
            ) if all("verdict" in x for x in (g, r)) else False
            if group["pass"] and g["status"] == "COMPLETED":
                scale = max(Fraction(1), *(abs(Fraction(row[k])) for row in (g, r) for k in ("real", "imag")))
                delta = max(abs(Fraction(g[k]) - Fraction(r[k])) for k in ("real", "imag")) / scale
                group["normalized_component_delta"] = str(delta)
                group["pass"] = delta <= Fraction(1, 10**24)
                for row in (g, r):
                    norm = Fraction(2) ** row["normalization_twice_log2"]
                    squared = (Fraction(row["real"])**2 + Fraction(row["imag"])**2) / norm
                    expected_squared = Fraction(1) if expected == "equivalent" else Fraction(0)
                    group["pass"] &= abs(squared - expected_squared) <= Fraction(1, 10**24)
            save(args.out / "report.json", report)
    return all(g["pass"] for g in report["groups"]) and any(
        g["rows"]["rawmocs"]["status"] == "COMPLETED" for g in report["groups"])


def long_case(args, report):
    label, _, _, historical_hash, bits = next(c for c in CASES if c[0] == args.case)
    digits, target = DIGITS[bits]
    family = label.rsplit("-", 1)[0]
    case, selector = SOURCE[family]
    root = Path.cwd().resolve()
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"],
                                    text=True).splitlines()
    if selector.startswith("benchmarks/"):
        rel = selector
        assert rel in paths
    else:
        rel, = [p for p in paths if p.startswith("benchmarks/MQTBench/")
                and p.endswith(".qasm") and sha256(p.encode()).hexdigest()[:12] == selector]
    started = time.monotonic()
    result = bounded([args.exporter, case, root, args.out, rel], 60)
    (args.out / "export.stdout").write_text(result.stdout)
    (args.out / "export.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stderr[-2000:]
    report["export_wall_s"] = time.monotonic() - started
    cnf = args.out / f"{case}-gpmc.cnf"
    source_hash = digest(cnf)
    assert (args.out / f"{case}.qasm").read_bytes() == (root / rel).read_bytes()
    report.update(source=rel, qasm_sha256=digest(root / rel), cnf_sha256=source_hash,
                  historical_cnf_match=source_hash == historical_hash,
                  bits=bits, digits=digits, target_digits=target)
    save(args.out / "report.json", report)
    ref = None
    for script in ("original_exact_prejoin.py", "original_fixed_interval.py"):
        result = bounded([sys.executable, args.oracle / script, cnf, source_hash], 190)
        (args.out / (script + ".stdout")).write_text(result.stdout)
        (args.out / (script + ".stderr")).write_text(result.stderr)
        if result.returncode == 0:
            ref = json.loads(result.stdout)
            if script == "original_fixed_interval.py":
                assert ref.get("order_policy") in ("fill-reverse", "degree-reverse")
                ref["status"] = "INDEPENDENT_FIXED_INTERVAL_COMPLETE"
            break
    assert ref is not None, "independent witness unavailable"
    assert ref["source_sha256"] == source_hash and ref["bits"] == 550
    assert ref["status"] in ("INDEPENDENT_INTERVAL_COMPLETE", "INDEPENDENT_FIXED_INTERVAL_COMPLETE")
    assert ref["width"] <= 19 and ref["work"] <= 40000000 and ref["peak"] <= 2000000
    if ref["status"] == "INDEPENDENT_FIXED_INTERVAL_COMPLETE":
        assert ref["order_policy"] in ("fill-reverse", "degree-reverse")
    save(args.out / "reference.json", ref)
    report["reference_sha256"] = digest(args.out / "reference.json")
    for trial in range(3):
        group = {"trial": trial, "rows": {}, "order": list(ARMS if trial % 2 == 0 else ARMS[::-1])}
        report["groups"].append(group)
        for arm in group["order"]:
            assert digest(cnf) == source_hash
            def action(selected):
                value = run_wmc(str(cnf), selected, timeout=LIMIT, preserve_count=True,
                                precision_digits=digits if selected == "gpmc" else None)
                return {"transport_real": str(value.real), "transport_imag": str(value.imag)}
            row = measure(arm, digits, args.raw, args.gpmc,
                          args.out / f"trial-{trial}-{arm}", action)
            if row["status"] == "COMPLETED":
                try:
                    assert row["cnf_sha256"] == source_hash
                    row["witness_upper"] = check_count(row, ref, target)
                except (AssertionError, ValueError) as exc:
                    row.update(status="NUMERIC_INCONCLUSIVE", error=str(exc))
            group["rows"][arm] = row
            save(args.out / "report.json", report)
    if not all(row["status"] == "COMPLETED" for group in report["groups"] for row in group["rows"].values()):
        return False
    for arm in ARMS:
        rows = [g["rows"][arm] for g in report["groups"]]
        report[arm] = {"solver_p50_s": statistics.median(r["solver_wall_s"] for r in rows),
                       "transport_p50_s": statistics.median(r["end_to_end_s"] for r in rows),
                       "median_peak_rss_kib": statistics.median(r["peak_rss_kib"] for r in rows)}
    report["gpmc_over_rawmocs_p50"] = report["gpmc"]["solver_p50_s"] / report["rawmocs"]["solver_p50_s"]
    return True


def main():
    ap = argparse.ArgumentParser()
    for name in ("raw", "gpmc", "out", "exporter", "oracle"):
        ap.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=name in ("raw", "gpmc", "out"))
    ap.add_argument("--case", required=True, choices=["e2e", "qpeinexact22-432", "grover6-432", "gf2-7-333"])
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ["QUPRS_GPMC_PATH"] = str(args.gpmc)
    default = get_solver_adapter("gpmc")
    report = {"status": "IN_PROGRESS", "case": args.case, "groups": [],
              "quprs_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "rawmocs_binary_sha256": digest(args.raw), "gpmc_binary_sha256": digest(args.gpmc),
              "limit_s": LIMIT, "address_space_bytes": AS_BYTES}
    save(args.out / "report.json", report)
    try:
        ok = e2e(args, report) if args.case == "e2e" else long_case(args, report)
        assert get_solver_adapter("gpmc") is default
        try:
            get_solver_adapter("rawmocs")
        except ValueError:
            pass
        else:
            raise AssertionError("scoped adapter leaked")
        report["status"] = "PASS" if ok else "INCONCLUSIVE"
    except Exception as exc:
        report.update(status="ERROR", error=f"{type(exc).__name__}: {str(exc)[:2000]}")
        raise
    finally:
        save(args.out / "report.json", report)
        print("QUPRS_RAWMOCS_FINAL", report["status"], args.case, flush=True)
    if not ok:
        raise SystemExit("integration or comparison inconclusive")


if __name__ == "__main__":
    main()
