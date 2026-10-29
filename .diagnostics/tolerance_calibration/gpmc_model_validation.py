"""Bounded, report-only GPMC numerical-model stress study.

Research only. Measure *observed* errors, not universal MPFR/circuit error
certificates. Works on the existing QuPRS experimental branch, without
changing production RR, Hybrid, or WMC verdicts.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
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
from unittest.mock import patch

import mpmath as mp
import sympy as sp
from qiskit import QuantumCircuit
from QuPRS import check_equivalence, config
from QuPRS.interface.ps2wmc import P_to_wlogi, run_wmc
from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata
from exact_gpmc_cnf_oracle import (
    count_printed_cnf_exact, exact_count_distance_classification,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "focused-tolerance-evidence"
CASES = (
    ("rz_far", "identity", 1, 2 * math.pi * 1e-7, False),
    ("rz_near_inside", "identity", 1, 1.96e-8, False),
    ("rz_near_outside", "identity", 1, 2.04e-8, False),
    ("rz_cancel", "identity", 1, 2 * math.pi * 1e-7, True),
    ("qft_style_2", "qft", 2, 2 * math.pi * 1e-7, False),
    ("qpe_style_2", "qpe", 2, 6e-4, False),
    ("graph_style_3", "graph", 3, 6e-4, False),
    ("qft_style_identity_2", "qft", 2, 0.0, False),
)
PER_CASE_SEC = 45


def make_base(style, n):
    qc = QuantumCircuit(n)
    if style == "identity":
        return qc
    if style == "qft":
        # QFT-style controlled phase decomposed into supported H/CX/Rz,
        # not asserted equivalent to the full QFT benchmark decomposition.
        for j in range(n):
            qc.h(j)
            for k in range(j + 1, n):
                angle = math.pi / (2 ** (k - j + 1))
                qc.rz(angle / 2, k)
                qc.cx(j, k)
                qc.rz(-angle / 2, k)
                qc.cx(j, k)
    elif style == "qpe":
        # Tiny phase-kickback / phase-estimation-shaped Clifford/Rz circuit.
        for j in range(n - 1):
            qc.h(j)
        qc.h(n - 1)
        for j in range(n - 1):
            qc.cx(j, n - 1)
            qc.rz(math.pi / (2 ** (j + 2)), n - 1)
            qc.cx(j, n - 1)
        for j in range(n - 1):
            qc.h(j)
    elif style == "graph":
        for j in range(n):
            qc.h(j)
        for j in range(n - 1):
            qc.h(j + 1)
            qc.cx(j, j + 1)
            qc.h(j + 1)
    else:
        raise ValueError(style)
    return qc


def m(value):
    return mp.mpf(value.numerator) / value.denominator


def source_weight_audit(pathsum, cnf):
    """Evaluate the actual phase polynomial's numeric coefficients anew.

    Sympy/mpmath is a separate numerical implementation; both still use
    the same parsed PathSum phases and do not reconstruct input text.
    """
    phases = P_to_wlogi(pathsum.P)
    weights = []
    for line in cnf.splitlines():
        if line.startswith("c p weight "):
            tokens = line.split()
            if int(tokens[3]) > 0:
                weights.append(tokens)
    if len(phases) != len(weights):
        return {"status": "shape_mismatch",
                "phase_count": len(phases), "weight_count": len(weights)}
    errors = []
    with mp.workdps(105):
        for (phase, _), tokens in zip(phases, weights):
            symbolic = sp.sympify(str(phase), locals={"pi": sp.pi})
            angle = mp.mpf(str(sp.N(2 * sp.pi * symbolic, 110)))
            reference = mp.mpc(mp.cos(angle), mp.sin(angle))
            printed = mp.mpc(mp.mpf(tokens[4]), mp.mpf(tokens[5]))
            errors.append(abs(reference - printed))
        return {
            "status": "observed",
            "phase_count": len(phases),
            "max_phase_weight_abs_error": mp.nstr(max(errors, default=mp.mpf(0)), 48),
            "sum_phase_weight_abs_error": mp.nstr(mp.fsum(errors), 48),
            "oracle_scope": "same parsed PathSum phases; independent sympy/mpmath trig",
            "source_text_accuracy_certified": False,
        }


def compute_case(case):
    name, style, n, theta, cancellation = case
    prev = config.get_tolerance()
    try:
        config.set_tolerance(1e-10)
        left = make_base(style, n)
        right = left.copy()
        if cancellation:
            for _ in range(8):
                right.rz(1.5e-5, 0)
                right.rz(-1.5e-5, 0)
        if theta:
            right.rz(theta, 0)
        start = time.monotonic()
        if name == "qft_style_identity_2":
            # Retain exact source CNF on a failing identity control, before
            # either metadata validation or Solver parse can obscure it.
            from QuPRS.interface import ps2wmc
            original = ps2wmc.to_DIMACS

            def preserve_identity_cnf(pathsum, filename="wmc.cnf", tool_name="gpmc"):
                payload = original(pathsum, filename, tool_name)
                OUT.mkdir(exist_ok=True)
                (OUT / "gpmc-model-qft-style-identity-input.cnf").write_text(
                    payload, encoding="utf-8"
                )
                return payload

            with patch.object(ps2wmc, "to_DIMACS", side_effect=preserve_identity_cnf):
                result = check_equivalence(
                    left, right, backend="python", method="wmc_only",
                    strategy="Naive", tool_name="gpmc", timeout=20,
                    approximate_distance_tolerance=1e-8,
                )
        else:
            result = check_equivalence(
                left, right, backend="python", method="wmc_only",
                strategy="Naive", tool_name="gpmc", timeout=20,
                approximate_distance_tolerance=1e-8,
            )
        api_sec = time.monotonic() - start
        cnf = result.CNF
        if not cnf or not result.wmc_solver_invoked:
            raise AssertionError("WMC-only did not produce a native GPMC CNF")
        variables, weights, max_weight_sq = gpmc_cnf_budget_metadata(cnf)
        with mp.workdps(105):
            true_magnitude = abs(mp.cos(mp.mpf(repr(theta)) / 2))
            true_distance = abs(mp.sin(mp.mpf(repr(theta)) / 2))
            norm = mp.power(2, mp.mpf(str(result.expect)))
            normalization_twice = int(round(2 * result.expect))
            assert abs(normalization_twice - 2 * result.expect) < 1e-8

        weight = source_weight_audit(result.final_pathsum, cnf)
        # An independent exact-rational reference for the *printed* CNF.
        # This does not use the solver or reparse the input quantum circuit.
        independent = count_printed_cnf_exact(cnf)
        rows = []
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as f:
            cnfpath = f.name
            f.write(cnf)
        try:
            count120 = None
            for precision in (30, 60, 90, 120):
                t = time.monotonic()
                count = run_wmc(
                    cnfpath, "gpmc", timeout=12,
                    preserve_count=True, precision_digits=precision,
                )
                if precision == 120:
                    count120 = count
                with mp.workdps(105):
                    real = m(count.real)
                    imag = m(count.imag)
                    mag = abs(mp.mpc(real, imag)) / norm
                    normalized_error = abs(mag - true_magnitude)
                rows.append({
                    "digits": precision,
                    "wall_seconds": round(time.monotonic() - t, 6),
                    "normalized_trace_magnitude": mp.nstr(mag, 100),
                    "normalized_oracle_abs_error": mp.nstr(normalized_error, 55),
                    "real_count": str(count.real),
                    "imag_count": str(count.imag),
                    "print_half_unit_real": str(count.real_print_half_unit),
                    "print_half_unit_imag": str(count.imag_print_half_unit),
                })
        finally:
            os.unlink(cnfpath)
        with mp.workdps(105):
            norm_errors = [mp.mpf(x["normalized_oracle_abs_error"]) for x in rows]
            score = max(norm_errors)
            count_30_to_120 = abs(
                mp.mpf(rows[0]["normalized_trace_magnitude"]) -
                mp.mpf(rows[-1]["normalized_trace_magnitude"])
            )
            budget = getattr(result, "wmc_numeric_model_bound", None)
            cnf_reference = {
                "status": independent["status"],
                "scope": "exact rational of printed CNF; not source-unitary exact",
            }
            if independent["status"] == "observed":
                cnf_reference.update({
                    "enumerated_assignments": independent["assignments_visited"],
                    "satisfying_assignments": independent["satisfying_assignments"],
                    "real_rational": str(independent["real"]),
                    "imag_rational": str(independent["imag"]),
                    "threshold_classification": exact_count_distance_classification(
                        independent["real"], independent["imag"],
                        normalization_twice, 1e-8,
                    ),
                })
                reference_count = mp.mpc(m(independent["real"]), m(independent["imag"]))
                actual_count = mp.mpc(m(count120.real), m(count120.imag))
                cnf_reference["gpmc_120_count_complex_abs_error"] = mp.nstr(
                    abs(actual_count - reference_count), 80,
                )
                cnf_reference["exact_printed_cnf_normalized_defect"] = mp.nstr(
                    1 - abs(reference_count) / norm, 80,
                )
            else:
                cnf_reference["reason"] = independent.get("reason")
                cnf_reference["variables"] = independent.get("variables")
            # The model is a componentwise unnormalized-count allowance.
            budget_normalized = (
                mp.sqrt(2) * m(Fraction(budget)) / norm
                if budget is not None else None
            )
            ratio = (
                score / budget_normalized
                if budget_normalized is not None and budget_normalized > 0 else None
            )
            summary = {
                "max_observed_normalized_oracle_error": mp.nstr(score, 50),
                "replay_30_to_120_normalized_gap": mp.nstr(count_30_to_120, 50),
                "assumed_model_normalized_error_allowance": (
                    mp.nstr(budget_normalized, 50)
                    if budget_normalized is not None else None),
                "observed_error_to_conditional_model_ratio": (
                    mp.nstr(ratio, 40) if ratio is not None else None),
                "conditional_model_exceeded_observationally": (
                    bool(ratio > 1) if ratio is not None else None),
            }
            return {
                "case": name, "style": style, "qubits": n,
                "theta_source_float_repr": repr(theta),
                "cancellation_pairs": 8 if cancellation else 0,
                "rr_tolerance": 1e-10,
                "distance_tolerance": 1e-8,
                "analytic_distance": mp.nstr(true_distance, 90),
                "analytic_normalized_trace": mp.nstr(true_magnitude, 90),
                "source_head": os.environ.get("GITHUB_SHA"),
                "cnf_sha256": hashlib.sha256(cnf.encode()).hexdigest(),
                "cnf_variables": variables,
                "weighted_phase_literals": weights,
                "max_weight_modulus_squared": str(max_weight_sq),
                "api_verdict": result.equivalent,
                "api_reason": getattr(result, "wmc_precision_reason", None),
                "api_model_bound": budget,
                "api_elapsed_seconds": round(api_sec, 6),
                "final_path_variables": result.final_pathsum.num_pathvar,
                "source_phase_weight_audit": weight,
                "printed_cnf_exact_reference": cnf_reference,
                "precision_replay": rows,
                "observations": summary,
                "certificate": False,
                "limitations": [
                    "MPFR precision replays are empirical convergence, not an arithmetic proof",
                    "Qiskit source angles are binary64; oracle uses their repr values",
                    "Sympy/mpmath weight oracle shares the parsed PathSum phase",
                    "Per-case source/operator trace uses analytic final Rz invariance",
                ],
            }
    finally:
        config.set_tolerance(prev)


def worker(name):
    case = next(item for item in CASES if item[0] == name)
    try:
        record = compute_case(case)
        record["execution_status"] = "observed"
    except Exception as error:
        record = {
            "case": name, "execution_status": "execution_error",
            "error": f"{type(error).__name__}: {error}"[:700],
            "source_head": os.environ.get("GITHUB_SHA"),
        }
        if name == "qft_style_identity_2":
            saved = OUT / "gpmc-model-qft-style-identity-input.cnf"
            if saved.exists():
                text = saved.read_text()
                record["captured_identity_cnf_sha256"] = hashlib.sha256(
                    text.encode()
                ).hexdigest()
                record["all_positive_weight_lines"] = [
                    line[:260] for line in text.splitlines()
                    if line.startswith("c p weight ") and
                    not line.startswith("c p weight -")
                ][:40]
                record["identity_cnf_retained"] = saved.name
    print("GPMC_MODEL_CASE=" + json.dumps(record, sort_keys=True, default=str),
          flush=True)


def outer():
    OUT.mkdir(exist_ok=True)
    all_results = []
    for name, *_ in CASES:
        t = time.monotonic()
        cmd = [sys.executable, "-u", __file__, "--worker", name]
        p = subprocess.Popen(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=(os.name == "posix"))
        try:
            stdout, stderr = p.communicate(timeout=PER_CASE_SEC)
            status = None
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
            stdout, stderr = p.communicate()
            status = "resource_timeout"
        entries = [line.split("GPMC_MODEL_CASE=", 1)[1]
                   for line in stdout.splitlines()
                   if line.startswith("GPMC_MODEL_CASE=")]
        rec = json.loads(entries[-1]) if entries else {
            "case": name, "execution_status": status or "missing_result",
        }
        rec["child_returncode"] = p.returncode
        rec["child_stderr_tail"] = stderr[-800:]
        rec["observed_wall_seconds"] = round(time.monotonic()-t, 5)
        all_results.append(rec)
        print("GPMC_MODEL_RESEARCH " + json.dumps({
            "case": name, "status": rec.get("execution_status"),
            "api_verdict": rec.get("api_verdict"),
            "cnf_variables": rec.get("cnf_variables"),
            "wall_seconds": rec["observed_wall_seconds"],
            "error": rec.get("error", "")[:180],
        }, sort_keys=True), flush=True)
    path = OUT / "gpmc-model-stress.json"
    path.write_text(json.dumps({
        "source": os.environ.get("GITHUB_SHA"),
        "case_limit_seconds": PER_CASE_SEC,
        "cases": all_results,
        "count": len(all_results),
        "science_scope": "REPORT ONLY, NO CERTIFIED WMC ERROR BOUND",
    }, indent=2, sort_keys=True)+"\n")
    assert len(all_results) == len(CASES)
    # The Rz core is independently checked by exact-rational CNF counting.
    # Larger representative circuits may exceed bounded resources.
    core = [r for r in all_results if r["case"] in (
        "rz_far", "rz_near_inside", "rz_near_outside", "rz_cancel"
    )]
    assert all(r["execution_status"] == "observed" for r in core), core
    assert all(len(r["precision_replay"]) == 4 for r in core)
    assert all(
        r.get("printed_cnf_exact_reference", {}).get("status") == "observed"
        for r in core
    ), core
    assert all(
        r["printed_cnf_exact_reference"]["threshold_classification"]
        == ("not_equivalent" if r["api_verdict"] == "not_equivalent"
            else "inside_threshold")
        for r in core
    ), core
    print("GPMC_MODEL_STRESS_CORE_PASS=4", flush=True)

    # The exact two-qubit QFT-style identity was an original source encoder
    # regression. Treat successful numeric weights as a required smoke gate,
    # even though large-case arithmetic convergence remains report-only.
    identity = next(r for r in all_results
                    if r["case"] == "qft_style_identity_2")
    assert identity["execution_status"] == "observed", identity
    assert identity["source_phase_weight_audit"]["status"] == "observed"
    captured = OUT / "gpmc-model-qft-style-identity-input.cnf"
    assert captured.is_file(), "Missing retained identity CNF"
    data = captured.read_text()
    assert "cos(" not in data and "sin(" not in data, (
        "Non-numeric phase weight leaked into GPMC CNF"
    )
    print("GPMC_MODEL_IDENTITY_WEIGHT_GATE_PASS=1", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", choices=[x[0] for x in CASES])
    args = ap.parse_args()
    if args.worker:
        worker(args.worker)
    else:
        outer()
