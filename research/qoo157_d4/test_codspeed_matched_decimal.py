"""Official CodSpeed WallTime for same-target-decimal d4/GPMC on same CNF.

Four source-pinned circuit families × two decimal budgets × two solvers.
Each timed operation calls a supervised external native solver on identical
prepared CNF, includes startup/IO/parse and avoids source generator/RR cost.
D4 source binary SHA is verified once before timed calls, not each time.

All measurements are hosted-runner observation only, not a Macro Runner gate.
"""
from __future__ import annotations

from contextlib import ExitStack
from fractions import Fraction
import json
import os
from pathlib import Path

import pytest
from QuPRS.utils.solver_adapter import registered_solver_adapter

from codspeed_choice_preflight import PAPER_CANDIDATES
from matched_precision_adapter import matched_adapter
from matched_precision_preflight import DIGITS, run_mode


MODES = [
    pytest.param(case, digits, solver, id=f"{case}-{digits}digits-{solver}")
    for case in PAPER_CANDIDATES
    for digits in DIGITS
    for solver in ("gpmc", "d4")
]


@pytest.mark.parametrize("case,digits,solver", MODES)
def test_qoo157_matched_decimal_solver_walltime(benchmark, case, digits, solver):
    report = json.loads(Path(os.environ["QOO157_MATCHED_REPORT"]).read_text())
    if report.get("complete") is not True:
        raise AssertionError("matched-precision preflight not complete")
    entry = report["cases"][case]["precision_pairs"][str(digits)]
    if entry["status"] != "COUNT_CONCORDANT_UNCERTIFIED":
        pytest.skip("QOO157_CENSORED_NO_PERFORMANCE_PAIR: " + entry["status"])
    filename = Path(os.environ["QOO157_CNF_DIR"]) / (case + ".cnf")
    if entry["source_cnf_sha256"] != report["cases"][case]["same_cnf_sha256"]:
        raise AssertionError("case CNF provenance disagreement")
    mode = f"{solver}-{digits}"
    with ExitStack() as stack:
        if solver == "d4":
            adapter = matched_adapter(
                Path(os.environ["QOO157_BIN_DIR"]) / str(digits) / "counter",
                Path(os.environ["QOO157_EVIDENCE_DIR"]) / f"d4-matched-{digits}.json",
                digits,
            )
            stack.enter_context(registered_solver_adapter(adapter))
        observed = benchmark(run_mode, mode, filename)
    reference = entry["observations"][mode]
    assert (str(observed.real), str(observed.imag)) == (reference["real"], reference["imag"]), (
        "timed solver observation changed from untimed scientific preflight"
    )
    benchmark.extra_info.update({
        "research_id": "QOO-157",
        "source_sha": os.environ.get("GITHUB_SHA"),
        "case": case, "solver": solver,
        "target_decimal_digits": digits,
        "same_input_cnf_sha256": entry["source_cnf_sha256"],
        "gpmc_mpfr_bits": entry["requested_mpfr_bits"],
        "d4_requested_gmp_bits": entry["requested_d4_gmp_bits"],
        "d4_actual_gmp_bits": entry["actual_d4_gmp_bits"],
        "matched_output_digits": digits,
        "working_bits_identical": (
            entry["requested_mpfr_bits"] == entry["actual_d4_gmp_bits"]
        ),
        "numerical_screen_only": "COUNT_CONCORDANT_UNCERTIFIED",
        "includes_external_solver": True,
        "includes_qasm_parsing_or_cnf_generation": False,
        "codspeed_instrument": "WallTime",
        "comparison_status": "OBSERVATION_ONLY_OUTSIDE_MACRO_RUNNER",
    })
