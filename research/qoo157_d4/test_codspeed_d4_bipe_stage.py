"""QOO-157 P8 official CodSpeed: preproc+parsing only vs full native solve.

Hosted observation, not fixed Macro Runner ABBA, and no formal subtraction
of unpaired medians into an algorithmic cost or solver recommendation.
"""
import json,os,hashlib
from pathlib import Path
import pytest
from qoo157_d4_preproc_only_science import CASE,OPTIONS_P8,PASSED,execute

@pytest.mark.parametrize("variant,scope",[
    pytest.param(v,scope,id=f"{CASE}-{v}-{scope}")
    for v in OPTIONS_P8 for scope in ("preproc_only","full")
])
def test_qoo157_bipe_stage_cost_walltime(benchmark,variant,scope):
    gate=json.loads(Path(os.environ["QOO157_P8_SCIENCE"]).read_text())
    assert gate["status"]==PASSED
    src=Path(os.environ["QOO157_P8_CNF"])
    assert hashlib.sha256(src.read_bytes()).hexdigest()==gate["original_cnf_sha256"]
    binary=Path(os.environ["QOO157_P8_BINARY"])
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==gate["d4_binary_sha256"]
    assert gate["variants"][variant]["full"]["source_p7_raw_sha_match"]
    assert gate["variants"][variant]["preproc_only"]["source_p7_raw_sha_match"]
    benchmark(execute,binary,src,variant,scope)
    benchmark.extra_info.update({
        "issue":"QOO-157","case":CASE,"option":variant,
        "scope":scope,"binary_sha256":gate["d4_binary_sha256"],
        "source_cnf_sha256":gate["original_cnf_sha256"],
        "raw_residual_sha256":gate["variants"][variant]["full"]["raw_residual_sha256"],
        "full_wmc_count_status":"COUNT_CONCORDANT_UNCERTIFIED",
        "precision_effective_decimal_digits":38,"actual_gmp_bits":128,
        "time_instrument":"official_CodSpeed_v5_WallTime",
        "scope_preproc_only":"native CNF parser, BiPe, launcher; skip counter() after preproc",
        "scope_full":"native parser, BiPe, d4 counter, stdout parsing",
        "run_admission":"HOSTED_OBSERVATION_ONLY_NOT_MACRO_RUNNER_ABBA",
        "not_end_to_end":"QASM_RR_CNF_generation",
    })
