"""P5 opt-in true one-round CodSpeed ABBA report unit tests, no real Solver."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("true_abba_report", ROOT / "scripts/report_qoo170_real_abba.py")
REPORT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(REPORT)
BASE, HEAD = "b"*40, "a"*40

def fixture():
    metrics={"instrument":{"type":"walltime"},"benchmarks":[]}
    science=[]
    warmups=[{"kind":"prewarm","method":m,"revision":r,
              "verdict":"not_equivalent","precision_contract":"public_per_call_pinned"}
             for m in REPORT.METHODS for r in ("base","head")]
    for method in REPORT.METHODS:
        for block,(_,seq) in enumerate(REPORT.BLOCKS):
            for pos in seq:
                rev="base" if pos.startswith("A") else "head"
                metrics["benchmarks"].append({
                    "uri":"benchmarks/codspeed/test_qoo170_real_abba.py::"
                          f"test_qoo170_real_single_position[{method}-block{block}-{pos}]",
                    "stats":{"rounds":1,"iter_per_round":1,"warmup_iters":0,
                             "median_ns":7e8+block*1e7}})
                science.append({
                    "method":method,"block":block,"position":pos,"revision":rev,
                    "revision_sha":BASE if rev=="base" else HEAD,
                    "fixture_sha":HEAD,"source_sha256":"c"*64,"target_sha256":"d"*64,
                    "real_solver_calls":1,"target_calls":2,
                    "observation":{"solver_invoked":True,"verdict":"not_equivalent",
                                   "method":method,"solver":"gpmc","effective_gpmc_digits":90}})
    return metrics,science,warmups

def test_complete_real_abba_is_observational_only():
    m,s,w=fixture()
    r=REPORT.produce(m,s,w,BASE,HEAD)
    assert r["official_measured_positions"]==32
    assert r["real_measured_solver_calls"]==32
    assert r["prewarm_real_solver_calls"]==4
    assert r["performance_status"]=="OBSERVATIONAL_NOT_CERTIFIED"
    assert r["no_fixed_regression_gate"] is True
    assert len(r["cases"])==2 and all(len(x["blocks"])==4 and not x["formal_regression_claim"] for x in r["cases"])

@pytest.mark.parametrize("field,value",[("rounds",2),("iter_per_round",2),("warmup_iters",1)])
def test_extra_measured_round_rejected(field,value):
    m,s,w=fixture()
    m["benchmarks"][0]["stats"][field]=value
    with pytest.raises(ValueError,match="not precisely one official"):
        REPORT.produce(m,s,w,BASE,HEAD)

def test_duplicate_solver_call_rejected():
    m,s,w=fixture()
    s[0]["real_solver_calls"]=2
    with pytest.raises(ValueError,match="unmeasured duplicate real Solver"):
        REPORT.produce(m,s,w,BASE,HEAD)

def test_mismatched_input_or_science_rejected():
    m,s,w=fixture()
    s[0]["target_sha256"]="e"*64
    with pytest.raises(ValueError,match="QASM source/target mutated"):
        REPORT.produce(m,s,w,BASE,HEAD)
    s[0]["target_sha256"]="d"*64
    s[0]["observation"]["verdict"]="equivalent"
    with pytest.raises(ValueError,match="wrong science"):
        REPORT.produce(m,s,w,BASE,HEAD)

def test_missing_position_and_prewarm_rejected():
    m,s,w=fixture()
    with pytest.raises(ValueError,match="provenance execution order"):
        REPORT.produce(m,s[:-1],w,BASE,HEAD)
    with pytest.raises(ValueError,match="missing or duplicated non-timed prewarm"):
        REPORT.produce(m,s,w[:-1],BASE,HEAD)

def test_same_sha_and_duplicate_official_uri_rejected():
    m,s,w=fixture()
    with pytest.raises(ValueError,match="two different"):
        REPORT.produce(m,s,w,BASE,BASE)
    m["benchmarks"].append(copy.deepcopy(m["benchmarks"][0]))
    with pytest.raises(ValueError,match="duplicate official"):
        REPORT.produce(m,s,w,BASE,HEAD)
