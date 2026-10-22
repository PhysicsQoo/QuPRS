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


def test_cleanup_requested_after_worker_exit_invalidates_sample():
    rows = [trial(2.0, 100), trial(2.1, 101), trial(2.2, 102)]
    rows[1]["cleanup_needed"] = True
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_outer_timeout_invalidates_otherwise_positive_report():
    rows = [trial(2.0, 100), trial(2.1, 101), trial(2.2, 102)]
    rows[1]["outer_timed_out"] = True
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_cleanup_error_invalidates_otherwise_positive_report():
    rows = [trial(2.0, 100), trial(2.1, 101), trial(2.2, 102)]
    rows[1]["cleanup_error"] = "worker_not_reaped"
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_bounded_trial_rejects_invalid_deadline():
    import pytest
    with pytest.raises(ValueError, match="positive"):
        module.run_bounded_trial(["unused"], 0)


def test_outer_worker_timeout_reaps_mock_solver_descendant(tmp_path):
    """The child models a native solver and must not outlive Python."""
    import os
    import sys
    import time

    import psutil
    import pytest

    if os.name != "posix":
        pytest.skip("Process-group supervision requires POSIX")
    pid_path = tmp_path / "solver.pid"
    script = (
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    outcome = module.run_bounded_trial([sys.executable, "-c", script], 2.0)
    assert outcome["outer_timed_out"] is True
    assert outcome["cleanup_needed"] is True
    assert outcome["cleanup_error"] is None
    assert pid_path.is_file(), "Mock solver was never started"
    pid = int(pid_path.read_text())
    for _ in range(100):
        try:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.02)
    else:
        pytest.fail("Mock native solver remained alive after outer timeout")


def test_early_worker_exit_does_not_leave_mock_solver_behind(tmp_path):
    """A successful Python wrapper exit cannot leave a live solver running."""
    import os
    import sys
    import time

    import psutil
    import pytest

    if os.name != "posix":
        pytest.skip("Process-group supervision requires POSIX")
    pid_path = tmp_path / "solver.pid"
    script = (
        "import pathlib, subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
    )
    outcome = module.run_bounded_trial([sys.executable, "-c", script], 5.0)
    assert outcome["exit_code"] == 0
    assert outcome["outer_timed_out"] is False
    assert outcome["cleanup_needed"] is True
    assert outcome["cleanup_error"] is None
    assert pid_path.is_file()
    pid = int(pid_path.read_text())
    for _ in range(100):
        try:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.02)
    else:
        pytest.fail("Mock native solver remained alive after wrapper exit")
