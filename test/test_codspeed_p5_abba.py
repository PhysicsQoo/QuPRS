"""P5 ABBA verifies exact CodSpeed block coverage, time, science, and drift."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "abba_report", ROOT / "scripts" / "report_codspeed_p5_abba.py")
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)
BASE = "b"*40
HEAD = "a"*40


def input_fixture():
    metric = {"instrument": {"type": "walltime"}, "benchmarks": []}
    witness = []
    for case in REPORT.SELECTED:
        for block in REPORT.BLOCKS:
            for position, revision in REPORT.POSITIONS.items():
                metric["benchmarks"].append({
                    "uri": f"benchmarks/codspeed/test_p5_abba.py::"
                           f"test_codspeed_p5_abba[{case}-block{block}-{position}]",
                    "stats": {
                        "rounds": 5, "iter_per_round": 1,
                        "min_ns": 700e6, "median_ns": 800e6 + block*1e6,
                        "mean_ns": 801e6, "stdev_ns": 8e6
                    }
                })
                witness.append({
                    "case": case, "block": block, "position": position,
                    "revision": revision,
                    "sha": BASE if revision == "base" else HEAD,
                    "fixture_sha": HEAD,
                    "qasm_sha256": ["a"*64, "b"*64],
                    "method": "hybrid", "backend": "rust",
                    "solver": "gpmc", "strategy": "proportional",
                    "reverse": False, "invocations": 6,
                    "science_status": "CONSISTENT_WITHIN_POSITION",
                    "observations": [{"verdict": "equivalent",
                                      "solver_invoked": True} for _ in range(6)],
                })
    return metric, witness


def test_complete_three_block_abba_is_diagnostic_not_release_go():
    metric, witness = input_fixture()
    report = REPORT.produce(metric, witness, BASE, HEAD)
    assert report["performance_status"] == "NOT_CERTIFIED"
    assert report["default_regression_threshold"] is None
    assert report["provenance_complete"]
    assert len(report["cases"]) == 4
    assert all(x["blocks"] == 3 and len(x["baseline_a1_a2_drift_percent"]) == 3
               for x in report["cases"])


def test_missing_codspeed_round_rejected():
    metric, witness = input_fixture()
    metric["benchmarks"][0]["stats"]["rounds"] = 4
    with pytest.raises(ValueError, match="missing 5"):
        REPORT.produce(metric, witness, BASE, HEAD)


def test_missing_block_or_duplicate_uri_rejected():
    metric, witness = input_fixture()
    metric["benchmarks"].pop()
    with pytest.raises(ValueError, match="incomplete ABBA"):
        REPORT.produce(metric, witness, BASE, HEAD)


def test_wrong_sha_or_solver_stage_rejected():
    metric, witness = input_fixture()
    witness[0]["sha"] = "c"*40
    with pytest.raises(ValueError, match="invalid Solver/science/sha"):
        REPORT.produce(metric, witness, BASE, HEAD)
    witness[0]["sha"] = BASE
    witness[0]["observations"][0]["solver_invoked"] = False
    with pytest.raises(ValueError, match="invalid Solver/science/sha"):
        REPORT.produce(metric, witness, BASE, HEAD)


def test_verdict_change_inside_block_rejected():
    metric, witness = input_fixture()
    witness[0]["observations"][-1]["verdict"] = "equivalent*"
    with pytest.raises(ValueError, match="changed verdict"):
        REPORT.produce(metric, witness, BASE, HEAD)
