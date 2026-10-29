"""Bounded, report-only investigation of the public v0.14.0 WMC boundary.

Run against an explicitly pinned dev *source snapshot* installed by the
experimental CI; never substitute research-branch public verifier results for
the dev behavior under review.

There are deliberate extra solver invocations here solely to inspect raw
stdout. None of these are production replay/fallback policy.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from QuPRS import check_equivalence
from QuPRS.utils import WMC
from QuPRS.utils.precision_count import (
    parse_printed_solver_output, classify_observed_distance,
)
from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata
from QuPRS.utils.gpmc_distance_budget import classify_gpmc_single_count
from QuPRS.utils.solver_adapter import get_solver_adapter
from QuPRS.interface import ps2wmc

HERE = Path.cwd()
HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
EPSILON = 1e-8
RECORDS = []


def emit(**fields):
    row = {"trial": len(RECORDS), **fields}
    RECORDS.append(row)
    print("BOUNDARY_OBSERVATION " + json.dumps(row, sort_keys=True, default=str),
          flush=True)
    return row


def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def direct_gpmc(cnf, label, out, *, timeout=30):
    """Research-only second solve to inspect GPMC's exact stdout bytes."""
    path = out / (label + ".cnf")
    path.write_text(cnf, encoding="utf-8")
    args = [*get_solver_adapter("gpmc").arguments, "-prec=90", str(path)]
    with WMC("gpmc") as exe:
        proc = subprocess.run([str(exe), *args], capture_output=True,
                              text=True, timeout=timeout, check=False)
    (out / (label + ".stdout.txt")).write_text(proc.stdout)
    (out / (label + ".stderr.txt")).write_text(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"native GPMC {label} failed: {proc.returncode}")
    counted = parse_printed_solver_output(proc.stdout)
    counts = [line.strip() for line in proc.stdout.splitlines()
              if line.startswith("c s exact")]
    return {
        "raw_count_lines": counts,
        "real": str(counted.real), "imag": str(counted.imag),
        "real_print_half_unit": str(counted.real_print_half_unit),
        "imag_print_half_unit": str(counted.imag_print_half_unit),
        "format_name": counted.format_name,
    }, counted


def inspect_cnf(label, cnf, out, *,
                norm_exponent=0, eps=EPSILON, exact=None):
    raw, count = direct_gpmc(cnf, label, out)
    n, weights, max_squared = gpmc_cnf_budget_metadata(cnf)
    budget = classify_gpmc_single_count(
        count, expected_twice_log2=norm_exponent,
        distance_tolerance=eps, phase_tolerance=1e-8,
        cnf_vars=n, number_of_weights=weights,
        maximum_weight_magnitude_squared=max_squared,
        precision_digits=90,
    )
    record = {
        "case": label, "family": "GPMC_PRINTED_BOUNDARY",
        "cnf_sha256": hashlib.sha256(cnf.encode()).hexdigest(),
        "nvars": n, "number_of_weights": weights,
        "solver_runs_research": 1, "raw": raw,
        "printed_verdict": budget.printed_status,
        "model_verdict": budget.status,
        "model_reason": budget.reason,
        "conditional_component_error": budget.component_error,
        "arithmetic_certified": budget.solver_arithmetic_certified,
    }
    if exact is not None:
        record["independent_exact_printed_cnf_count"] = exact
        assert count.real == Fraction(exact[0]) and count.imag == Fraction(exact[1]), record
    emit(**record)
    return record


def forced_single_solution(out):
    for n in (12, 128, 160, 512):
        cnf = (f"p cnf {n} {n}\nc t wmc\n"
               "c p weight 1 1.0 0.0 0\n"
               "c p weight -1 1.0 0.0 0\n"
               + "".join(f"{k} 0\n" for k in range(1, n+1)))
        inspect_cnf(f"forced_unit_{n}", cnf, out, exact=(1,0))


@contextmanager
def record_one_public_solver():
    original_encode = ps2wmc.to_DIMACS
    original_run = ps2wmc.run_wmc
    state = {"cnf": None, "count": None, "calls": 0}
    def capture_encode(*args, **kwargs):
        state["cnf"] = original_encode(*args, **kwargs)
        return state["cnf"]
    def capture_run(*args, **kwargs):
        state["calls"] += 1
        assert kwargs.get("preserve_count") is True
        assert kwargs.get("precision_digits") == 90
        state["count"] = original_run(*args, **kwargs)
        return state["count"]
    ps2wmc.to_DIMACS, ps2wmc.run_wmc = capture_encode, capture_run
    try:
        yield state
    finally:
        ps2wmc.to_DIMACS, ps2wmc.run_wmc = original_encode, original_run


def global_phase_and_rz(out):
    cases = (
        ("sxsx_global_phase", "s q[0];\nx q[0];\ns q[0];\nx q[0];\n", "equivalent*"),
        ("rz_inside", "rz(0.00032) q[0];\n", "equivalent"),
        ("rz_outside", "rz(0.00048) q[0];\n", "not_equivalent"),
    )
    for label, op, expected in cases:
        with record_one_public_solver() as state:
            answer = check_equivalence(
                HEADER, HEADER + op, method="wmc_only",
                strategy="Naive", backend="python", tool_name="gpmc",
                timeout=45, approximate_distance_tolerance=2e-4,
            )
        assert state["calls"] == 1, (label, state["calls"])
        count = state["count"]
        assert count is not None and state["cnf"] is not None
        raw, direct_count = direct_gpmc(state["cnf"], "public_" + label, out)
        assert (count.real, count.imag) == (direct_count.real, direct_count.imag)
        cnf_vars, weights, weight_sq = gpmc_cnf_budget_metadata(state["cnf"])
        record = emit(
            case=label, family="PUBLIC_COUNT_AND_RAW_STDOUT",
            production_solver_calls=1, extra_research_solver_calls=1,
            production_result=answer.equivalent,
            expected_analytic_label=expected,
            production_precision_reason=answer.wmc_precision_reason,
            printed_verdict=answer.wmc_printed_verdict,
            production_numeric_model_bound=answer.wmc_numeric_model_bound,
            parsed_count=[str(count.real), str(count.imag)],
            raw_stdout=raw,
            nvars=cnf_vars, number_of_weights=weights,
            weight_magnitude_squared=str(weight_sq),
            cnf_sha256=hashlib.sha256(state["cnf"].encode()).hexdigest(),
        )
        # Printed count cannot assert a universal source or solver proof;
        # scientific near-boundary unknown is an inconclusive outcome.
        assert record["production_result"] in ("equivalent", "equivalent*",
                                                "not_equivalent", "unknown")


def qpeexact8(out):
    corpus = HERE / "benchmarks" / "MQTBench"
    first = corpus / "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm"
    second = corpus / "h,ry,rz,cx" / "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm"
    assert first.is_file() and second.is_file()
    hashes = [source_hash(first), source_hash(second)]
    for backend in ("python", "rust"):
        started = time.monotonic()
        try:
            answer = check_equivalence(
                str(first), str(second),
                backend=backend, method="hybrid", strategy="proportional",
                tool_name="gpmc", timeout=75,
                approximate_distance_tolerance=EPSILON,
            )
            emit(
                case="qpeexact8", family="FIXED_CORPUS_BACKEND_PAIR",
                backend=backend, qasm_sha256=hashes,
                wall_seconds=round(time.monotonic()-started,4),
                verdict=answer.equivalent,
                decision_basis=answer.decision_basis,
                solver_invoked=answer.wmc_solver_invoked,
                wmc_printed_verdict=answer.wmc_printed_verdict,
                wmc_precision_reason=answer.wmc_precision_reason,
                wmc_numeric_model_bound=answer.wmc_numeric_model_bound,
                final_reduced_pathsum_sha256=hashlib.sha256(
                    str(answer.final_pathsum).encode()).hexdigest()
                    if answer.final_pathsum is not None else None,
            )
        except Exception as exc:
            emit(case="qpeexact8", family="FIXED_CORPUS_BACKEND_PAIR",
                 backend=backend, qasm_sha256=hashes,
                 error=f"{type(exc).__name__}: {exc}",
                 wall_seconds=round(time.monotonic()-started,4))


def f64_alias():
    a=Decimal("0.000000020000000000000000000000")
    b=Decimal("0.000000020000000000000000000001")
    assert a != b and float(a) == float(b)
    emit(case="f64_source_phase_alias", family="REPRESENTABILITY_NOT_VERIFIER_PROOF",
         exact_distinct=True, f64_alias=True,
         exact_difference=str(b-a), binary64_value=repr(float(a)))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--expected-dev-sha", required=True)
    args=p.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    # CI installs the pinned dev archive from its own repository source, not
    # from the experiment checkout. Preserve this separation in the artifact.
    source_sha=(HERE/"PUBLIC_DEV_BASELINE_SHA.txt").read_text().strip()
    if source_sha != args.expected_dev_sha:
        raise ValueError("Installed public dev baseline does not match")
    emit(case="source_identity",family="PROVENANCE",dev_sha=source_sha,
         experiment_sha=os.environ.get("GITHUB_SHA"),
         reference_note="experiment owns the study, dev owns the tested API")
    forced_single_solution(out)
    global_phase_and_rz(out)
    qpeexact8(out)
    f64_alias()
    (out/"boundary-observations.json").write_text(
        json.dumps(RECORDS,sort_keys=True,indent=2,default=str)+"\n")
    assert any(r.get("case")=="sxsx_global_phase" for r in RECORDS)
    assert len([r for r in RECORDS if r.get("case")=="qpeexact8"])==2
    print("EXPERIMENT_ONLY_BOUNDARY_STUDY_COMPLETE",flush=True)


if __name__=="__main__":
    main()
