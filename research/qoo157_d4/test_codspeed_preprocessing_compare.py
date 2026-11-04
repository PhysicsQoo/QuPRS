"""CodSpeed within-solver GPMC EE and d4 BiPe ablation, science-gated."""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest
from qoo157_preprocess_compare import CASES, FLAGS, TARGET_STATUS, run_one

@pytest.mark.parametrize("case,variant", [
    pytest.param(case, variant, id=f"{case}-{variant}")
    for case in CASES for variant in FLAGS
])
def test_qoo157_preprocessing_walltime(benchmark, case, variant):
    report = json.loads(Path(os.environ["QOO157_PP_PREFLIGHT"]).read_text())
    assert report["status"] == TARGET_STATUS
    entry = report["cases"][case]
    source = Path(os.environ["QOO157_PP_CNF_DIR"]) / (case + ".cnf")
    assert sha256(source.read_bytes()).hexdigest() == entry["cnf_sha256"]
    solver = "gpmc" if variant.startswith("gpmc_") else "d4"
    if solver not in entry["admitted_solvers"]:
        pytest.skip("PREPROCESS_PAIR_CENSORED_" + solver)
    expected = entry["variants"][variant]
    result = benchmark(
        run_one, os.environ["QOO157_GPMC_BINARY"],
        os.environ["QOO157_D4_BINARY"], source, variant
    )
    assert (result["real"], result["imag"]) == (
        expected["real"], expected["imag"]
    ), "timed WMC changed from science admission"
    benchmark.extra_info.update({
        "research_issue": "QOO-157",
        "case": case, "variant": variant,
        "same_cnf_sha256": entry["cnf_sha256"],
        "gpmc_binary_sha256": report["gpmc_sha256"],
        "d4_research_binary_sha256": report["d4_scratch_binary_sha256"],
        "gpmc_mpfr_bits": 127, "d4_gmp_bits": 128,
        "same_effective_decimal_digits": 38,
        "native_preprocess": expected["native_preprocess"],
        "timed_scope": "prepared_CNF_solver_inclusive",
        "instrument": "official_CodSpeed_v5_WallTime",
        "comparability": "WITHIN_SOLVER_ABLATION_ONLY",
        "status": "OBSERVATION_ONLY_NOT_MACRO_RUNNER",
    })
