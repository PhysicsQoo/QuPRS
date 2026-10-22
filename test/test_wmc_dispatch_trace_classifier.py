"""Native WMC dispatch classification: --version is not model-counting work."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "probe_wmc_dispatch_controls.py"
SPEC = spec_from_file_location("probe_wmc_dispatch_controls", MODULE_PATH)
module = module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_ganak_version_probe_is_not_model_counting():
    binary = "/tmp/ganak"
    trace = '500 execve("/tmp/ganak", ["/tmp/ganak", "--version"], 0x1) = 0'
    assert module.native_solver_work_execve(trace, binary, "ganak") is False


def test_ganak_mode_six_cnf_invocation_is_model_counting():
    binary = "/tmp/ganak"
    trace = (
        '500 execve("/tmp/ganak", ["/tmp/ganak", "--version"], 0x1) = 0\n'
        '501 execve("/tmp/ganak", ["/tmp/ganak", "--mode=6", "/tmp/input.cnf"], 0x1) = 0'
    )
    assert module.native_solver_work_execve(trace, binary, "ganak") is True


def test_gpmc_mode_one_cnf_invocation_is_model_counting():
    trace = '500 execve("/tmp/gpmc", ["/tmp/gpmc", "-mode=1", "/tmp/input.cnf"], 0x1) = 0'
    assert module.native_solver_work_execve(trace, "/tmp/gpmc", "gpmc") is True


def test_mismatched_binary_or_failed_exec_is_not_model_counting():
    trace = (
        '500 execve("/tmp/other", ["/tmp/other", "--mode=6", "/tmp/input.cnf"], 0x1) = 0\n'
        '501 execve("/tmp/ganak", ["/tmp/ganak", "--mode=6", "/tmp/input.cnf"], 0x1) = -1 ENOENT'
    )
    assert module.native_solver_work_execve(trace, "/tmp/ganak", "ganak") is False


def test_successful_hybrid_equivalence_without_wmc_is_valid_for_any_case():
    # QFT can also become RR-only after valid reductions. Its name must never
    # force a native WMC process.
    report = module.classify_hybrid_execution(
        "equivalent*", None, "", "/tmp/gpmc", "gpmc"
    )
    assert report["execution_path"] == "rr_only"
    assert report["native_model_count_execve"] is False
    assert report["tool_time_numeric"] is False
    assert report["native_time_consistent"] is True


def test_hybrid_native_work_is_observed_not_presumed():
    trace = '501 execve("/tmp/ganak", ["/tmp/ganak", "--mode=6", "/tmp/input.cnf"], 0x1) = 0'
    report = module.classify_hybrid_execution(
        "equivalent*", 0.2, trace, "/tmp/ganak", "ganak"
    )
    assert report["execution_path"] == "native_wmc"
    assert report["native_time_consistent"] is True


def test_version_only_and_positive_equivalence_remain_reduction_only():
    trace = '501 execve("/tmp/ganak", ["/tmp/ganak", "--version"], 0x1) = 0'
    report = module.classify_hybrid_execution(
        "equivalent", None, trace, "/tmp/ganak", "ganak"
    )
    assert report["execution_path"] == "rr_only"


def test_numeric_tool_time_without_native_exec_is_inconclusive_not_rr_only():
    report = module.classify_hybrid_execution(
        "equivalent", 0.2, "", "/tmp/gpmc", "gpmc"
    )
    assert report["execution_path"] == "unverified_native_dispatch"
    assert report["native_time_consistent"] is False
