"""Only official CodSpeed measures d4 BiPe-configuration solve WallTime."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import pytest
from qoo157_bipe_options import CASES, OPTIONS, STATUS, run_one


@pytest.mark.parametrize("case,variant", [
    pytest.param(c, v, id=f"{c}-{v}")
    for c in CASES for v in OPTIONS
])
def test_qoo157_bipe_ablation_walltime(benchmark, case, variant):
    report = json.loads(Path(os.environ["QOO157_BIPE_REPORT"]).read_text())
    assert report["status"] == STATUS, "no timing before science admission"
    source = Path(os.environ["QOO157_BIPE_CNF_DIR"]) / (case + ".cnf")
    row = report["cases"][case]
    assert sha256(source.read_bytes()).hexdigest() == row["source_cnf_sha256"]
    if variant not in row["admitted"]:
        pytest.skip("CENSORED_SCIENCE_" + row["results"][variant]["status"])
    expected = row["results"][variant]
    observed = benchmark(run_one, os.environ["QOO157_BIPE_BINARY"], source, variant)
    assert (observed["real"], observed["imag"]) == (
        expected["real"], expected["imag"]
    ), "timed result disagrees with untimed scientific preflight"
    benchmark.extra_info.update({
        "research_id": "QOO-157", "case": case, "variant": variant,
        "source_cnf_sha256": row["source_cnf_sha256"],
        "d4_source_commit": report["d4_source_commit"],
        "d4_scratch_binary_sha256": report["d4_binary_sha256"],
        "effective_decimal_digits": 38,
        "actual_gmp_bits": 128,
        "binary_contains_output_only_BiPe_diagnostics": True,
        "native_before_after": expected["native_preprocessor"],
        "count_science": "COUNT_CONCORDANT_UNCERTIFIED",
        "benchmark_scope": "source_prepared_CNF_full_native_subprocess",
        "instrument": "CodSpeed_v5_WallTime",
        "interpretation": "WITHIN_D4_ONLY_HOSTED_OBSERVATION",
    })
