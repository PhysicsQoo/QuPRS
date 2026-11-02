"""Source-only coverage; never spawn historical GPMC in unit tests."""
from collections import Counter
from pathlib import Path
import pytest
from scripts.tacas26_paper_matrix import matrix,SMOKE_IDS,pinned
ROOT=Path(__file__).resolve().parents[1]
def test_paper_matrix_has_all_real_historical_identities():
    rows=matrix(ROOT)
    assert len(rows)==187
    assert Counter(x["suite"] for x in rows)=={"table2":108,"table3_positive":1,
                                                "table3_negative":74,"figure3":4}
    assert len({x["id"] for x in rows})==187
    assert len(SMOKE_IDS)==10
    assert set(SMOKE_IDS)<=set(x["id"] for x in rows)
def test_wstate32_and_all_negative_pairs_are_retained():
    rows=matrix(ROOT)
    assert "table3_negative:wstate32:negative:wmc_only" in {x["id"] for x in rows}
    assert all(x["b"].startswith("benchmarks/MQTBench/Random_Rotation/")
               for x in rows if x["suite"]=="table3_negative")
def test_historical_oracle_not_invented():
    rows=matrix(ROOT)
    assert {x["paper_expected"] for x in rows}=={"NOT_YET_TRANSCRIBED","equivalent*"}
    assert sum(x["paper_expected"]=="equivalent*" for x in rows)==1
def test_source_blob_mismatch_fail_closed(tmp_path):
    p=tmp_path/"a.qasm";p.write_text("OPENQASM 2.0;")
    with pytest.raises(ValueError,match="Pinned QASM"):
        pinned(tmp_path,"a.qasm","0"*40)

def test_paper_hybrid_full_run_excluding_proven_smoke_has_68_entries():
    rows=matrix(ROOT)
    hybrid=[r for r in rows if r["method"]=="hybrid"]
    assert len(hybrid)==74
    remaining=[r for r in hybrid if r["id"] not in SMOKE_IDS]
    assert len(remaining)==68
    assert len({r["id"] for r in remaining})==68

def test_all_remaining_non_hybrid_modes_have_109_cases():
    rows=matrix(ROOT)
    rem=[r for r in rows if r["method"]!="hybrid" and r["id"] not in SMOKE_IDS]
    assert len(rem)==109
    assert sum(r["suite"]=="table2" for r in rem)==70
    assert sum(r["suite"]=="table3_negative" for r in rem)==36
    assert sum(r["suite"]=="figure3" for r in rem)==3
