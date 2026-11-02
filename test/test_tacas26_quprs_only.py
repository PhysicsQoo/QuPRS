"""Source-only audit of the submitted 184-call QuPRS-only reproduction."""
from pathlib import Path
from types import SimpleNamespace

from scripts.tacas26_paper_matrix import matrix as exploratory
from scripts.tacas26_quprs_only import matrix, pending_with_rr_recapture

ROOT = Path(__file__).resolve().parents[1]

def test_official_direct_calls_are_184_without_competitor_executions():
    rows = matrix(ROOT)
    assert len(rows) == 184
    assert len({r["id"] for r in rows}) == 184
    assert len([r for r in rows if r["method"] == "hybrid"]) == 74
    assert len([r for r in rows if r["method"] == "wmc_only"]) == 74
    assert len([r for r in rows if r["method"] == "reduction_rules"]) == 36
    assert set(r["method"] for r in rows) == {
        "hybrid", "wmc_only", "reduction_rules"
    }
    assert not any(r["suite"] == "table2" and r["method"] == "reduction_rules"
                   for r in rows)
    assert "table3_positive:wstate32:positive:wmc_only" in {r["id"] for r in rows}
    assert len([r for r in rows if r["suite"] == "figure3"]) == 36

def test_continuation_excludes_existing_historical_source_calls():
    rows = pending_with_rr_recapture(ROOT)
    assert len(rows) == 144
    assert len({r["id"] for r in rows}) == 144
    assert sum(r["kind"] == "positive" and r["method"] == "hybrid"
               for r in rows) == 37
    assert sum(r["method"] == "wmc_only" for r in rows) == 72
    assert sum(r["suite"] == "figure3" for r in rows) == 35
    assert not any(r["method"] == "hybrid" and r["kind"] == "negative" for r in rows)
    assert "table2:ghz32:positive:wmc_only" not in {r["id"] for r in rows}
    assert "table3_negative:ghz32:negative:wmc_only" not in {r["id"] for r in rows}
    assert "figure3:tof_3:positive:reduction_rules" not in {r["id"] for r in rows}

def test_old_187_registry_kept_separate_from_official_matrix():
    assert len(exploratory(ROOT)) == 187
    assert len(matrix(ROOT)) == 184

def test_paper_rr_column_uses_hybrid_termination_not_independent_rr():
    # Structural contract: the capture logic must not spawn another invocation.
    from scripts.tacas26_paper_matrix import run_one
    import inspect
    source = inspect.getsource(run_one)
    assert 'data.to_DIMACS_time is None' in source
    assert '"SAME_HYBRID_INVOCATION"' in source
    assert 'result["derived_rr"]' in source
    assert source.count("check_equivalence(") == 1


def test_solver_workflow_executes_reproducer_as_module():
    workflow = (ROOT / ".github/workflows/tacas26-quprs-only.yml").read_text()
    assert "python -m scripts.tacas26_quprs_only \\" in workflow
    assert "python scripts/tacas26_quprs_only.py" not in workflow
