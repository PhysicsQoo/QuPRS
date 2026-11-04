"""QOO-157 P4: qualified GPMC cache-cap effect — official CodSpeed ONLY.

Science preflight on this same compiled binary tests 12 variants. The timed
cohort deliberately keeps 2 cases x TD on/off x cache 16/64 MiB (8 IDs).
Source 64 vs 4000 MiB had identical native search without eviction; omit
redundant high-cap timed arm, retain zero-eviction negative control.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from gpmc_cache_capacity_science import inspect
from gpmc_vs_td_factorial import close_enough

CASES = ("grover4_eq", "qft16_eq")
TDS = (True, False)
CAPS = (16, 64)
STATUS = "CACHE_CAPACITY_SCIENCE_PASS_12_OF_12"


@pytest.mark.parametrize(
    "case,td,cap_mib",
    [pytest.param(case, td, cap,
                  id=f"{case}-{'td' if td else 'no_td'}-cs{cap}")
     for case in CASES for td in TDS for cap in CAPS],
)
def test_cache_cap_source_paired_official_codspeed(benchmark, case, td, cap_mib):
    gate = json.loads(Path(os.environ["QOO157_CAP_PREFLIGHT"]).read_text())
    assert gate["status"] == STATUS, "refuse time without fresh science PASS"
    src = json.loads(Path(os.environ["QOO157_SOURCE_REPORT"]).read_text())
    assert src["complete"] is True
    cnf = Path(os.environ["QOO157_CAP_CNF_DIR"]) / f"{case}.cnf"
    row = gate["cases"][case]
    assert sha256(cnf.read_bytes()).hexdigest() == row["source_cnf_sha256"]
    binpath = Path(os.environ["QOO157_GPMC_CAP_BINARY"])
    assert sha256(binpath.read_bytes()).hexdigest() == gate["binary_sha256"]
    key = f"{'td_on' if td else 'td_off'}_cap_{cap_mib}"
    control = row["variants"][key]
    assert control["status"] == "PASS", "no native-count admission"
    result = benchmark(inspect, binpath, cnf, cap_mib, td)
    assert result["status"] == "NATIVE_COUNT_PRESENT"
    reference = src["cases"][case]["precision_pairs"]["38"]["observations"]["gpmc-38"]
    with localcontext() as ctx:
        ctx.prec = 110
        oracle = tuple(Decimal(Fraction(reference[k]).numerator) /
                       Decimal(Fraction(reference[k]).denominator)
                       for k in ("real", "imag"))
    ok, delta, threshold = close_enough(result["count"], oracle)
    assert ok, f"count after timing disagreed: {case}/{key}, {delta}>{threshold}"
    # The native structural intervention must actually be the admitted one.
    assert result["counters"] == control["counters"], (
        f"native search changed between science and timed {case}/{key}"
    )
    benchmark.extra_info.update({
        "research_issue": "QOO-157",
        "case": case, "td_enabled": td,
        "cache_limit_mib": cap_mib,
        "cache_reduce_native": control["counters"]["Cache reduce"],
        "native_decisions": control["counters"]["decisions"],
        "native_cache_hits": control["counters"]["Cache hit"],
        "source_cnf_sha256": row["source_cnf_sha256"],
        "gpmc_binary_sha256": gate["binary_sha256"],
        "source_gitlink": gate["gpmc_gitlink"],
        "precision_effective_decimal_digits": 38,
        "precision_mpfr_bits": 127,
        "science": "COUNT_CONCORDANT_UNCERTIFIED",
        "instrument": "official_CodSpeed_v5_WallTime",
        "measurement_scope": "prepared_weighted_CNF_subprocess_inclusive",
        "not_measured": "QASM_RR_CNF_generation",
        "interpretation": "hosted_observation_only_not_fixed_macro_runner_ABBA",
    })
