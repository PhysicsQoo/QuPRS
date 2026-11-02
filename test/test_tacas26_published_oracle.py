"""Published-reference paper matrix is complete, no Solver invocation."""
import json
from pathlib import Path
from scripts.tacas26_paper_matrix import matrix
from scripts.tacas26_compare_paper import expected
ROOT=Path(__file__).resolve().parents[1]
def test_reference_has_all_36_table2_rows_and_two_negative_oracles():
    j=json.loads((ROOT/"docs/development/tacas26-paper-verdict-oracle.json").read_text())
    m=matrix(ROOT)
    assert len(j["table2"])==36
    assert set(j["table2"])=={x["case"] for x in m if x["suite"]=="table2"}
    assert {expected(j,x) for x in m if x["suite"]=="table2"}
    assert sum(expected(j,x)=="not_equivalent" for x in m if x["suite"]=="table3_negative")==56
    assert sum(expected(j,x)=="Timeout" for x in m if x["suite"]=="table3_negative")==17
    assert sum(expected(j,x)=="MemoryOut" for x in m if x["suite"]=="table3_negative")==1
def test_paper_qpe20_and_wstate32_reference_are_covered():
    j=json.loads((ROOT/"docs/development/tacas26-paper-verdict-oracle.json").read_text())
    rows={x["id"]:x for x in matrix(ROOT)}
    assert expected(j,rows["table2:qpeinexact20:positive:hybrid"])=="equivalent*"
    assert expected(j,rows["table2:qpeinexact20:positive:wmc_only"])=="Timeout"
    assert expected(j,rows["table3_negative:wstate32:negative:hybrid"])=="Timeout"
    assert expected(j,rows["table3_negative:grover6:negative:hybrid"])=="MemoryOut"

def test_external_watchdog_timeout_is_not_false_verdict_mismatch():
    from scripts.tacas26_compare_paper import expected
    j=json.loads((ROOT/"docs/development/tacas26-paper-verdict-oracle.json").read_text())
    assert expected(j,{"suite":"table3_positive","case":"wstate32","method":"hybrid"})=="Timeout"
    # Distinguish observed censored timeout (no Solver verdict) from
    # observed normal 'not_equivalent': they are never the same result.
    assert expected(j,{"suite":"table3_negative","case":"wstate32","method":"hybrid"})=="Timeout"
