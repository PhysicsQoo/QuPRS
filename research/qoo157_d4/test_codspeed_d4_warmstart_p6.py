"""QOO-157 P6: source-matched d4 SAT warm-start overhead on official CodSpeed.

Native component decision counts were identical 8/8 on warm-start off/on;
29 limited SAT queries still have possible additional subprocess cost.
Never estimate time from decision counters. Only time WMC-qualified pairs.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest
from d4_warmstart_science import one
from gpmc_vs_td_factorial import close_enough

PAIRS = (
    ("grover4_eq", "auto"),
    ("qaoa7_neq", "auto"),
    ("qaoa7_neq", "none"),
    ("qpeexact8_eq", "auto"),
    ("qft16_eq", "auto"),
)
STATUS = "D4_WARMSTART_SCIENCE_PASS_16_OF_16"


@pytest.mark.parametrize("case,bipe,state", [
    pytest.param(case, bipe, state,
                 id=f"{case}-{bipe}-warm_{state}")
    for case,bipe in PAIRS for state in ("on","off")
])
def test_qoo157_d4_warmstart_only_walltime(benchmark, case, bipe, state):
    gate = json.loads(Path(os.environ["QOO157_P6_WARM_REPORT"]).read_text())
    assert gate["status"] == STATUS, "do not time a censored/failed native science"
    assert not gate["failures"] and not gate["censored"]
    pair = gate["cases"][case]["pairs"][bipe]
    assert pair["effects"]["status"] == "BOTH_WMC_CONCORDANT"
    assert pair["effects"]["native_stats_identical"]
    binary = Path(os.environ[f"QOO157_WARM_{state.upper()}"])
    digest = sha256(binary.read_bytes()).hexdigest()
    assert digest == gate[f"warm_{state}_binary_sha256"], "runtime binary not science-pinned"
    cnf = Path(os.environ["QOO157_P6_CNF_DIR"]) / f"{case}.cnf"
    assert sha256(cnf.read_bytes()).hexdigest() == (
        gate["cases"][case]["source_sha256"]
    ), "CNF changed after preflight"
    expected = pair["variants"][state]
    assert expected["status"] == "COUNT_CONCORDANT_UNCERTIFIED"
    observation = benchmark(one,binary,cnf,bipe)
    assert observation["status"] == "COUNT_PRESENT"
    got = tuple(Decimal(x) for x in observation["complex"])
    want = tuple(Decimal(x) for x in expected["complex"])
    ok,delta,bound = close_enough(got,want)
    assert ok, f"timed warm-start result WMC inconsistent: {delta}>{bound}"
    assert observation["native"] == expected["native"], (
        "Native search changed between science and CodSpeed; refuse attribution"
    )
    benchmark.extra_info.update({
        "research_issue": "QOO-157",
        "case": case,
        "bipe": bipe,
        "warm_start_enabled": state=="on",
        "cache_always_enabled": True,
        "source_commit": gate["source_commit"],
        "source_cnf_sha256": gate["cases"][case]["source_sha256"],
        "warm_on_binary_sha256": gate["warm_on_binary_sha256"],
        "warm_off_binary_sha256": gate["warm_off_binary_sha256"],
        "exact_run_call_patched_only_for_off": True,
        "native_decisions": expected["native"]["decisions"],
        "native_recursive_calls": expected["native"]["recursive_calls"],
        "source_real_imag_equal_to_other_warm_arm": (
            pair["effects"]["exact_printed_complex_equal"]
        ),
        "native_search_counters_identical_between_arms": True,
        "gmp_actual_bits": 128,
        "effective_decimal_digits": 38,
        "science": "COUNT_CONCORDANT_UNCERTIFIED",
        "method": "official_CodSpeed_v5_WallTime",
        "macro_runner_certified": False,
        "scope": "original_prepared_weighted_CNF_full_d4_subprocess_and_parse",
        "excluded_costs": "QASM_Path-sum_RR_CNF_generation",
        "interpretation": "HOSTED_OBSERVATION_ONLY_NOT_FIXED_MACRO_RUNNER_ABBA",
    })
