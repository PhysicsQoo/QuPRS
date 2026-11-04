"""QOO-98 conditional Ganak/GPMC 127-bit requested-MPFR source-CNF CodSpeed.

NOT an equal output-precision rank: Ganak mode6 prints only nine digits.
Benchmark's scope: subprocess solver call on prepared, semantically same
Boolean CNF + exact literal weights in native dialects. No exporter time.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json, os

import pytest
from qoo98_ganak_native_mode6_admission import native, compare
from signed_scc_reduction_count_gate import native_count
from gpmc_vs_td_factorial import close_enough

CASES=("grover4_eq","qaoa7_neq","qpeexact8_eq","qft16_eq")

@pytest.mark.parametrize("case,solver",[
    pytest.param(c,s,id=f"{c}-{s}")
    for c in CASES for s in ("gpmc127","ganak127")
])
def test_conditional_same_requested_bits_solver_inclusive(benchmark,case,solver):
    gate=json.loads(Path(os.environ["QOO98_NATIVE_REPORT"]).read_text())
    original=json.loads(Path(os.environ["QOO98_SOURCE_SCIENCE"]).read_text())
    assert gate["status"]=="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED"
    assert gate["fair_38d_output_ranking"]=="NOT_COMPARABLE_FOR_38D_OUTPUT"
    assert gate["pinned_ganak_sha"]=="b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281"
    row=gate["source_cases"][case]
    assert row["native"]["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
    source=Path(os.environ["QOO98_SOURCE_CNF_DIR"])/(case+".cnf")
    semantic_sha=sha256(source.read_bytes()).hexdigest()
    assert semantic_sha==row["source_sha256"]
    assert semantic_sha==original["cases"][case]["same_cnf_sha256"]
    ganak_file=Path(os.environ["QOO98_GANAK_CNF_DIR"])/("original_"+case+".cnf")
    assert sha256(ganak_file.read_bytes()).hexdigest()==row["serialization"]["ganak_dialect_sha256"]
    # Proof of syntactic transport is in source-exact native admission,
    # not a claim of byte-identical CNFs between solver dialects.
    if solver=="ganak127":
        binary=Path(os.environ["QOO98_GANAK_BIN"])
        assert sha256(binary.read_bytes()).hexdigest()==gate["official_binary_sha256"]
        result=benchmark(native,str(binary),ganak_file,127)
        assert result["status"]=="COMPLETED"
        expected=(Decimal(row["native"]["real"]),Decimal(row["native"]["imag"]))
        assert compare(result,expected,large=True)["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
        printed_digits=9
    else:
        binary=Path(os.environ["QOO98_GPMC_BIN"])
        result=benchmark(native_count,"gpmc",str(binary),source)
        obs=original["cases"][case]["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec=100
            reference=tuple(Decimal(Fraction(obs[k]).numerator)/Decimal(Fraction(obs[k]).denominator)
                            for k in ("real","imag"))
        assert close_enough(result,reference)[0]
        printed_digits=38
    benchmark.extra_info.update({
        "issue":"QOO-98","source_case":case,"solver":solver,
        "shared_original_boolean_weight_semantic_sha256":semantic_sha,
        "native_dialect_sha256":semantic_sha if solver=="gpmc127" else row["serialization"]["ganak_dialect_sha256"],
        "native_binary_sha256":sha256(binary.read_bytes()).hexdigest(),
        "requested_MPFR_bits":127,
        "printed_effective_digits":printed_digits,
        "ganak_print_concordance":"PRINT_CONCORDANT_UNCERTIFIED",
        "fair_equal_output_precision":False,
        "performance_scope":"conditional_same_requested_bits_only",
        "scope":"native_prepared_CNF_child_subprocess",
        "official_instrument":"CodSpeed_v5_WallTime_hosted_observational",
        "macro_runner_certified":False,
        "internal_arithmetic_certified":False,
    })
