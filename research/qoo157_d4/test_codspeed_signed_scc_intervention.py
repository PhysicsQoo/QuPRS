"""QOO-157 P0 causal intervention: same solver original versus shared SCC quotient.

CodSpeed v5 subprocess-inclusive only; never cross-run median arithmetic.
Reuses passed science artifact, exact original/reduced CNF sha and pinned
38-effective-digit native solver binaries.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

from signed_scc_reduction_count_gate import native_count
from gpmc_vs_td_factorial import close_enough

CASES=("grover4_eq","qaoa7_neq","qpeexact8_eq","qft16_eq")
SOLVERS=("gpmc","d4")
MODES=("original","reduced")
STATUS="ORIGINAL_REDUCED_FOUR_CASE_TWO_SOLVER_COUNT_SCREEN_PASS"


@pytest.mark.parametrize(
    "case,solver,mode",[
        pytest.param(c,s,m,id=f"{c}-{s}-{m}")
        for c in CASES for s in SOLVERS for m in MODES
    ])
def test_p0_causal_quotient_solver_inclusive(benchmark,case,solver,mode):
    gate=json.loads(Path(os.environ["QOO157_P0_SCREEN"]).read_text())
    manifest=json.loads(Path(os.environ["QOO157_P0_MANIFEST"]).read_text())
    assert gate["status"]==STATUS
    assert manifest["status"]=="SOURCE_EXACT_REDUCTION_READY_FOR_SOLVER_COUNT_SCREEN"
    anchor=gate["cases"][case]["observations"][f"{solver}_{mode}"]
    assert anchor["screen_pass"] is True
    directory=Path(os.environ["QOO157_P0_ORIGINAL"] if mode=="original"
                   else os.environ["QOO157_P0_REDUCED"])
    cnf=directory/(case+".cnf")
    expected_sha=manifest["cases"][case][
        "source_sha256" if mode=="original" else "reduced_sha256"]
    assert sha256(cnf.read_bytes()).hexdigest()==expected_sha
    binary=os.environ["QOO157_GPMC" if solver=="gpmc" else "QOO157_D4"]
    expected_bin=gate["gpmc_binary_sha256" if solver=="gpmc"
                      else "d4_scratch_binary_sha256"]
    assert sha256(Path(binary).read_bytes()).hexdigest()==expected_bin
    observed=benchmark(native_count,solver,binary,cnf)
    ok,delta,bound=close_enough(
        observed,(Decimal(anchor["real"]),Decimal(anchor["imag"])))
    assert ok,(case,solver,mode,delta,bound)
    benchmark.extra_info.update({
        "research_issue":"QOO-157","source_measured_sha":os.environ["GITHUB_SHA"],
        "case":case,"solver":solver,"cnf_variant":mode,
        "original_cnf_sha256":manifest["cases"][case]["source_sha256"],
        "reduced_cnf_sha256":manifest["cases"][case]["reduced_sha256"],
        "actual_cnf_sha256":expected_sha,
        "native_solver_sha256":expected_bin,
        "merged_variables":manifest["cases"][case]["merged_variables"],
        "source_vars":manifest["cases"][case]["source_vars"],
        "reduced_vars":manifest["cases"][case]["reduced_vars"],
        "effective_decimal_digits":38,
        "actual_precision_bits":127 if solver=="gpmc" else 128,
        "count_screen":"COUNT_CONCORDANT_UNCERTIFIED",
        "timed_scope":"prepared_cnf_native_subprocess_inclusive",
        "comparison_scope":"within_solver_original_to_shared_reduced_CNF",
        "codspeed":"official_v5_WallTime_hosted_observation",
        "d4_precision":"research_only_patched_preparse_GMP",
        "macro_runner_certified":False,
    })
