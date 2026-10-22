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
    """Kill an actual three-level tree whose solver descendants call setsid."""
    import sys
    import time

    import psutil
    import pytest

    if sys.platform != "linux":
        pytest.skip("Subreaper supervision requires Linux")
    pid_path = tmp_path / "grandchild.pid"
    mock_solver = tmp_path / "mock_solver.py"
    mock_solver.write_text(
        "import pathlib, subprocess, sys, time\n"
        "grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)\n"
        f"pathlib.Path({str(pid_path)!r}).write_text(str(grandchild.pid))\n"
        "time.sleep(60)\n"
    )
    script = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, {str(mock_solver)!r}], start_new_session=True)\n"
        "time.sleep(60)\n"
    )
    outcome = module.run_bounded_trial([sys.executable, "-c", script], 3.0)
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
    """Capture a detached solver orphaned before the Python wrapper exits."""
    import sys
    import time

    import psutil
    import pytest

    if sys.platform != "linux":
        pytest.skip("Subreaper supervision requires Linux")
    pid_path = tmp_path / "solver.pid"
    script = (
        "import pathlib, subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)\n"
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


def test_normal_worker_exit_requires_no_cleanup():
    """A clean trial must remain admissible after Linux subreaper supervision."""
    import sys
    import pytest

    if sys.platform != "linux":
        pytest.skip("Subreaper supervision requires Linux")
    outcome = module.run_bounded_trial(
        [sys.executable, "-c", "print('done')"], 5.0
    )
    assert outcome["exit_code"] == 0
    assert outcome["outer_timed_out"] is False
    assert outcome["cleanup_needed"] is False
    assert outcome["cleanup_error"] is None
    assert outcome["stdout_tail"].strip() == "done"


def test_rr_only_is_valid_positive_hybrid_end_to_end_measurement():
    rows = [trial(1.2, 140), trial(1.3, 145), trial(1.1, 135)]
    for row in rows:
        row["report"]["verdict"]["solver_time"] = None
    summary = module.summarize(rows, 3)
    assert summary["status"] == "COMPLETE"
    assert summary["execution_path"] == "RR_ONLY_REPORTED"
    assert summary["walltime_median_seconds"] == 1.2
    assert summary["sampled_tree_rss_median_mib"] == 140
    assert summary["native_solver_execution_verified"] is False
    assert summary["solver_only_performance_certified"] is False


def test_numeric_solver_time_is_metadata_not_native_execution_proof():
    summary = module.summarize([trial(2, 110), trial(2.1, 120), trial(2.2, 130)], 3)
    assert summary["status"] == "COMPLETE"
    assert summary["execution_path"] == "WMC_TIME_REPORTED"
    assert summary["native_solver_execution_verified"] is False
    assert summary["solver_only_performance_certified"] is False


def test_mixed_rr_and_wmc_is_valid_hybrid_but_not_solver_only_comparison():
    rows = [trial(2.0, 120), trial(2.2, 140), trial(2.1, 130)]
    rows[1]["report"]["verdict"]["solver_time"] = None
    summary = module.summarize(rows, 3)
    assert summary["status"] == "COMPLETE"
    assert summary["execution_path"] == "MIXED_HYBRID_PATHS"
    assert summary["numeric_solver_time_trials"] == 2
    assert summary["solver_only_performance_certified"] is False


def test_invalid_solver_time_still_rejected_not_relabelled_as_rr_only():
    for value in (-0.5, float("nan"), float("inf"), True, "unknown"):
        rows = [trial(2, 100), trial(2.1, 110), trial(2.2, 120)]
        rows[0]["report"]["verdict"]["solver_time"] = value
        assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_missing_solver_time_field_is_not_accepted_as_rr_only():
    rows = [trial(2, 100), trial(2.1, 110), trial(2.2, 120)]
    del rows[0]["report"]["verdict"]["solver_time"]
    assert module.summarize(rows, 3)["status"] == "INCONCLUSIVE"


def test_fixed_host_balanced_four_round_schedule():
    plan = module.comparison_schedule(
        ("grover4", "qft16"), ("gpmc", "ganak"),
        ("python", "rust"), warmups=1, repeats=4,
    )
    assert len(plan) == 40
    assert [point["trial_index"] for point in plan] == list(range(40))
    blocks = [[p for p in plan if p["round"] == r] for r in range(5)]
    for case in ("grover4", "qft16"):
        for solver in ("gpmc", "ganak"):
            for backend in ("python", "rust"):
                trial_rows = [p for p in plan if (p["case"], p["solver"], p["backend"]) ==
                              (case, solver, backend)]
                assert len(trial_rows) == 5
                assert sum(p["warmup"] for p in trial_rows) == 1
                assert [p["repetition"] for p in trial_rows if not p["warmup"]] == [0, 1, 2, 3]
    assert [(x["case"], x["solver"], x["backend"]) for x in blocks[2]] == list(reversed(
        [(x["case"], x["solver"], x["backend"]) for x in blocks[1]]
    ))
    assert [(x["case"], x["solver"], x["backend"]) for x in blocks[3]] == list(reversed(
        [(x["case"], x["solver"], x["backend"]) for x in blocks[1]]
    ))
    assert [(x["case"], x["solver"], x["backend"]) for x in blocks[4]] == [
        (x["case"], x["solver"], x["backend"]) for x in blocks[1]
    ]


def test_fixed_host_rejects_unbalanced_repetition_counts():
    import pytest

    for n in (0, 3, 5, 6):
        with pytest.raises(ValueError, match="multiple of four"):
            module.comparison_schedule(
                ("grover4",), ("gpmc", "ganak"),
                ("python",), warmups=1, repeats=n,
            )


def test_fixed_host_schedule_no_warmups_is_supported():
    plan = module.comparison_schedule(
        ("grover4",), ("gpmc", "ganak"), ("rust",),
        warmups=0, repeats=4,
    )
    assert len(plan) == 8
    assert not any(p["warmup"] for p in plan)
