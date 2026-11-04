"""One-shot source-pinned CodSpeed WallTime for prepared-CNF solver-inclusive calls.

Not a full QuPRS verification timing, not a statistical performance gate.
Each test must actually invoke a child solver; no cached counts or RR paths.
All scientific eligibility is decided *before* measurement by the pilot
preflight. The exact same source CNF is used for all three solver modes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from QuPRS.utils.solver_adapter import registered_solver_adapter
from codspeed_choice_preflight import PAPER_CANDIDATES, SOLVERS, run_one
from d4_solver_adapter_poc import external_research_adapter

PARAMS = [
    pytest.param(case, solver, id=f"{case}-{solver}")
    for case in PAPER_CANDIDATES
    for solver in SOLVERS
]


@pytest.mark.parametrize("case,solver", PARAMS)
def test_qoo157_solver_choice_walltime(benchmark, case, solver):
    report = json.loads(Path(os.environ["QOO157_PREFLIGHT"]).read_text())
    if report.get("complete") is not True:
        raise RuntimeError("Incomplete native scientific preflight")
    if case not in report["eligible_cases"]:
        pytest.skip("QOO157_CENSORED_NOT_PERFORMANCE_COMPARABLE: "
                    + report["cases"][case]["status"])
    input_file = Path(os.environ["QOO157_CNF_DIR"]) / (case + ".cnf")
    if not input_file.is_file():
        raise FileNotFoundError(str(input_file))
    adapter = external_research_adapter(
        Path(os.environ["QOO157_D4_BINARY"]),
        Path(os.environ["QOO157_D4_PROVENANCE"]),
    )
    with registered_solver_adapter(adapter):
        observed = benchmark(run_one, solver, input_file, 15)
    expectation = report["cases"][case]["solver_observations"][solver]
    assert [str(observed.real), str(observed.imag)] == expectation["count"], (
        "not a valid comparable CodSpeed sample: differing printed WMC count"
    )
    benchmark.extra_info.update({
        "case": case,
        "solver": solver,
        "method": "QuPRS_WMC_only_prepared_CNF_solver_inclusive",
        "d4_source_bits": "426_preparse" if solver == "d4_426" else "not_applicable",
        "gpmc_precision_digits": (
            90 if solver == "gpmc90" else 30 if solver == "gpmc30" else None
        ),
        "input_sha256": report["cases"][case]["source_cnf_sha256"],
        "input_bytes": report["cases"][case]["source_cnf_bytes"],
        "d4_binary_sha256": report["d4_binary_sha256"],
        "numerical_concordance": "UNCERTIFIED",
        "same_runner_pairing": "same_job_non_ABBA_observational_pilot",
        "performance_gate": "OBSERVATION_ONLY_NOT_CERTIFIED",
        "instrument": "CodSpeed_WallTime",
    })
