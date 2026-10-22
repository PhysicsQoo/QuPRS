"""Pure resource aggregation tests; no solver runs or performance CI."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fixed_host_resource_repeats.py"
SPEC = spec_from_file_location("fixed_host_resource_repeats", SCRIPT)
module = module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def trial(t, r):
    return {
        "warmup": False,
        "report": {
            "complete": True, "resource_limit_status": None,
            "exit_code": 0, "verdict": {
                "accepted_positive": True, "solver_time": 0.02,
            },
            "elapsed_seconds": t,
            "sampled_peak_tree_rss_mib": r,
        },
    }


def test_median_and_peak_are_different_measures():
    result = module.summarize(
        [trial(2.0, 125), trial(2.2, 140), trial(1.9, 135)], 3,
    )
    assert result["status"] == "COMPLETE"
    assert result["n"] == 3
    assert result["walltime_median_seconds"] == 2.0
    assert result["sampled_tree_rss_median_mib"] == 135
    assert result["sampled_tree_rss_max_observed_mib"] == 140


def test_inconclusive_resource_is_not_a_performance_sample():
    rows = [trial(2, 100), trial(2, 101), trial(2, 102)]
    rows[1]["report"]["complete"] = False
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_missing_repetitions_are_not_complete():
    assert module.summarize([trial(1, 10)], 3)["status"] == "INCONCLUSIVE"

def test_warmup_failure_is_preserved_as_inconclusive():
    rows = [trial(1.2, 120), trial(2, 100), trial(2, 101), trial(2, 102)]
    rows[0]["warmup"] = True
    rows[0]["report"]["complete"] = False
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_cross_solver_or_backend_measurement_is_inconclusive():
    rows = [trial(2, 100), trial(2, 101), trial(2, 102)]
    for row in rows:
        report = row["report"]
        report["case"] = {"case": "grover4"}
        report["tool_name"] = "gpmc"
        report["backend"] = "python"
        report["verdict"]["tool_name"] = "gpmc"
        report["verdict"]["backend"] = "python"
        report["input_sha256"] = {"source": "a" * 64, "transpiled": "b" * 64}
    assert module.summarize(
        rows, 3, expected_case="grover4",
        expected_solver="gpmc", expected_backend="python",
    )["status"] == "COMPLETE"
    rows[1]["report"]["tool_name"] = "ganak"
    assert module.summarize(
        rows, 3, expected_case="grover4",
        expected_solver="gpmc", expected_backend="python",
    )["status"] == "INCONCLUSIVE"


def test_input_hash_change_prevents_cross_input_comparison():
    rows = [trial(2, 100), trial(2, 101), trial(2, 102)]
    for row in rows:
        report = row["report"]
        report.update({
            "case": {"case": "grover4"}, "tool_name": "gpmc",
            "backend": "python", "input_sha256": {
                "source": "a" * 64, "transpiled": "b" * 64,
            },
        })
        report["verdict"].update({"tool_name": "gpmc", "backend": "python"})
    rows[1]["report"]["input_sha256"]["source"] = "c" * 64
    assert module.summarize(
        rows, 3, expected_case="grover4",
        expected_solver="gpmc", expected_backend="python",
    )["status"] == "INCONCLUSIVE"
