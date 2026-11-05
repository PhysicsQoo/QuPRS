"""Official CodSpeed only: paired d4 native cache-on/off after fresh WMC gates.

Not a GPMC-vs-d4 speed comparison; censors never become a benchmark.
"""
from __future__ import annotations
from decimal import Decimal
from hashlib import sha256
import json, os
from pathlib import Path

import pytest
from d4_cache_bipe_science import native, discover
from gpmc_vs_td_factorial import close_enough

PAIRS = (("qaoa7_neq", "auto"), ("qaoa7_neq", "none"), ("qft16_eq", "auto"))
MODES = (True, False)
STATUS = ("D4_CACHE_SCIENCE_PASS_8_OF_8",
          "D4_CACHE_SCIENCE_WITH_CENSORING")

@pytest.mark.parametrize("case,bipe,enabled", [
    pytest.param(case, bipe, enabled,
                 id=f"{case}-{bipe}-cache_{'on' if enabled else 'off'}")
    for case, bipe in PAIRS for enabled in MODES
])
def test_qoo157_native_d4_cache_only(benchmark, case, bipe, enabled):
    gate = json.loads(Path(os.environ["QOO157_D4_CACHE_REPORT"]).read_text())
    assert gate["status"] in STATUS, "No timing before scientific admission"
    assert not gate["scientific_failures"]
    pair = [case, bipe]
    if pair not in gate["admitted_pairs"]:
        pytest.skip("CENSORED_CACHE_OFF_NO_VALID_NUMERIC_PAIRED_SCIENCE")
    binary = Path(os.environ["QOO157_D4_CACHE_BINARY"])
    assert sha256(binary.read_bytes()).hexdigest() == gate["binary_sha256"]
    source = Path(os.environ["QOO157_D4_CACHE_CNF_DIR"]) / f"{case}.cnf"
    row = gate["cases"][case]
    assert sha256(source.read_bytes()).hexdigest() == row["source_cnf_sha256"]
    opt = gate["native_cache_flag"]
    verified_opt, help_hash = discover(binary)
    assert (opt, help_hash) == (verified_opt, gate["native_help_sha256"])
    mode = "on" if enabled else "off"
    expected = row["variants"][f"{bipe}_cache_{mode}"]
    assert expected["status"] == "PASS"
    measured = benchmark(native, binary, source, opt, bipe, enabled)
    assert measured["status"] == "NATIVE_COMPLETED"
    count = tuple(Decimal(x) for x in measured["value"])
    anchor = tuple(Decimal(x) for x in expected["value"])
    ok, delta, bound = close_enough(count, anchor)
    assert ok, f"Measured-run d4 complex WMC drift: {delta} > {bound}"
    if not enabled:
        assert measured["native_stats"]["positive_hits"] == 0
        assert measured["native_stats"]["negative_hits"] == 0
    benchmark.extra_info.update({
        "research_issue": "QOO-157",
        "d4_pinned_upstream": gate["d4_source_pin"],
        "d4_scratch_binary_sha256": gate["binary_sha256"],
        "source_cnf_sha256": row["source_cnf_sha256"],
        "effective_decimal_digits": 38,
        "actual_gmp_bits": 128,
        "case": case,
        "bipe": bipe,
        "cache_enabled": enabled,
        "native_recursive_calls": expected["native_stats"]["recursive_calls"],
        "native_decisions": expected["native_stats"]["decisions"],
        "native_cache_positive_hits": expected["native_stats"]["positive_hits"],
        "native_cache_negative_hits": expected["native_stats"]["negative_hits"],
        "science_status": "COUNT_CONCORDANT_UNCERTIFIED",
        "benchmark_scope": "original_prepared_weighted_CNF_native_subprocess",
        "instrument": "official_CodSpeed_v5_WallTime",
        "macro_runner_certified": False,
        "warm_start_unmodified_default": True,
        "comparability": "within_d4_same_BiPe_source_and_binary_only",
    })
