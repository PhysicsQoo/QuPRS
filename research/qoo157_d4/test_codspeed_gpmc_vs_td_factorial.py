"""Official CodSpeed WMC external GPMC 2x2 vs/td experiment, 8 identities."""
from __future__ import annotations
from decimal import Decimal
import json
import os
from pathlib import Path

import pytest
from gpmc_vs_td_factorial import CASES, VARIANTS, STATUS, close_enough, run_one


@pytest.mark.parametrize("case,variant", [
    pytest.param(case, variant, id=f"{case}-{variant}")
    for case in CASES for variant in VARIANTS
])
def test_qoo157_vs_td_factorial_walltime(benchmark, case, variant):
    report = json.loads(Path(os.environ["QOO157_FACTORIAL_PREFLIGHT"]).read_text())
    assert report["status"] == STATUS, "refuse timing without science admission"
    entry = report["cases"][case]
    assert entry["status"] == "COUNT_CONCORDANT_UNCERTIFIED"
    source = Path(os.environ["QOO157_FACTORIAL_CNF_DIR"]) / (case + ".cnf")
    from hashlib import sha256
    assert sha256(source.read_bytes()).hexdigest() == entry["cnf_sha256"]
    result = benchmark(run_one, os.environ["QOO157_GPMC_BINARY"], source, variant)
    expected = entry["variants"][variant]
    assert (result["real"], result["imag"]) == (expected["real"], expected["imag"]), (
        "count changed between untimed preflight and measured run"
    )
    benchmark.extra_info.update({
        "research_issue": "QOO-157", "case": case, "variant": variant,
        "gpmc_source_gitlink": report["gpmc_gitlink"],
        "gpmc_binary_sha256": report["binary_sha256"],
        "original_cnf_sha256": entry["cnf_sha256"],
        "working_effective_decimal_digits": 38,
        "uses_td": variant.endswith("_td"),
        "branch_heuristic": 0 if variant.startswith("vs0_") else 1,
        "flowcutter_executed": expected["flowcutter_executed"],
        "science_status": "COUNT_CONCORDANT_UNCERTIFIED",
        "instrument": "CodSpeed_v5_WallTime",
        "instrument_scope": "prepared_CNF_process_parse_preprocess_search",
        "statistical_status": "OBSERVATION_ONLY_NOT_MACRO_RUNNER_ABBA",
    })
