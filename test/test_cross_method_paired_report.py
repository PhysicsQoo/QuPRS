"""Unit tests: compare identical request cost without falsifying solver verdicts."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/report_cross_method_paired.py"
spec = importlib.util.spec_from_file_location("cross_method_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def fixture(instrument="simulation"):
    # Load the source-pinned experimental matrix by file path: pytest and
    # Docker run with different sys.path roots; no package install is needed.
    from runpy import run_path
    case_file = Path(__file__).resolve().parents[1] / (
        "benchmarks/codspeed/test_cross_method_paired.py"
    )
    matrix = run_path(str(case_file))
    CASES, CPU_CASES = matrix["CASES"], matrix["CPU_CASES"]
    cases = CPU_CASES if instrument == "simulation" else CASES
    records = []
    for case in cases:
        for revision in ("base", "head"):
            records.append({
                "case": case[0], "revision": revision,
                "instrument": instrument,
                "sha": revision, "fixture_sha": "head",
                "qasm_sha256": ["a" * 64, "b" * 64],
                "method": "hybrid", "strategy": case[2], "reverse": case[3],
                "solver": case[4], "backend": case[5],
                "solver_invoked": True, "verdict": "equivalent*",
            })
    return records


def test_ganak_verdict_mismatch_still_comparable_as_execution_only():
    records = fixture()
    head = next(r for r in records
                if r["case"] == "vqe4_ganak_rust" and r["revision"] == "head")
    head["verdict"] = "not_equivalent"
    result = report.inspect(records, "base", "head", "simulation")
    assert result["status"] == "PASS"
    row = next(r for r in result["pairs"] if r["case"] == "vqe4_ganak_rust")
    assert row["request_execution_cost_comparable"]
    assert row["solver_work_cost_comparable"]
    assert row["scientific_verdict_parity"] == "MISMATCHED"
    assert row["performance_scope"] == "execution_only_not_verified_speedup"


def test_solver_stage_change_blocks_solver_stage_but_not_request_cost():
    records = fixture()
    head = next(r for r in records
                if r["case"] == "qaoa7_gpmc_rust" and r["revision"] == "head")
    head["solver_invoked"] = False
    result = report.inspect(records, "base", "head", "simulation")
    row = next(r for r in result["pairs"] if r["case"] == "qaoa7_gpmc_rust")
    assert row["request_execution_cost_comparable"]
    assert not row["solver_work_cost_comparable"]


def test_missing_pair_or_modified_qasm_fails():
    records = fixture()
    records[0]["qasm_sha256"] = ["c" * 64, "b" * 64]
    records.pop()
    result = report.inspect(records, "base", "head", "simulation")
    assert result["status"] == "FAIL"
    assert any("input mismatch qasm_sha256" in x for x in result["errors"])
    assert any("missing base/head" in x for x in result["errors"])


def test_full_walltime_coverage_is_six_families_four_methods():
    result = report.inspect(fixture("walltime"), "base", "head", "walltime")
    assert result["status"] == "PASS"
    assert result["expected_pairs"] == 24
    assert result["observed_pairs"] == 24
