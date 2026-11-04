"""Official CodSpeed WallTime for isolated pinned GPMC TD-on/off comparison."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from gpmc_td_ablation import CASES, FLAGS, run_one


@pytest.mark.parametrize("case,variant", [
    pytest.param(case, variant, id=f"{case}-{variant}")
    for case in CASES for variant in FLAGS
])
def test_qoo157_gpmc_td_solver_inclusive(benchmark, case, variant):
    report = json.loads(Path(os.environ["QOO157_TD_PREFLIGHT"]).read_text())
    if report["status"] != "COMPLETED_COUNT_CONCORDANCE_UNCERTIFIED":
        pytest.skip("CENSORED_SCIENCE_PREFLIGHT_NOT_ADMITTED")
    entry = report["cases"][case]
    if entry["status"] != "COUNT_CONCORDANT_UNCERTIFIED":
        pytest.skip("CENSORED_DIFFERING_WMC")
    source = Path(os.environ["QOO157_TD_CNF_DIR"]) / (case + ".cnf")
    observed = benchmark(
        run_one, os.environ["QOO157_GPMC_BINARY"], source, variant
    )
    expected = entry["variants"][variant]
    assert (observed["real"], observed["imag"]) == (
        expected["real"], expected["imag"]
    ), "Timed solver count changed from scientific preflight"
    benchmark.extra_info.update({
        "research_id": "QOO-157",
        "case": case, "variant": variant,
        "source_cnf_sha256": entry["input_sha256"],
        "gpmc_binary_sha256": report["binary_sha256"],
        "gpmc_source_gitlink": report["gpmc_gitlink"],
        "mpfr_effective_decimal_digits": 38,
        "flowcutter_executed": expected["flowcutter_executed"],
        "td_skip_recorded": expected["td_skip_recorded"],
        "td_ignored_recorded": expected["td_ignored_recorded"],
        "includes_external_solver": True,
        "includes_qasm_rr_or_cnf_generation": False,
        "count_status": "COUNT_CONCORDANT_UNCERTIFIED",
        "instrument": "CodSpeed_v5_WallTime",
        "status": "HOSTED_OBSERVATION_ONLY_NOT_MACRO_RUNNER",
    })
