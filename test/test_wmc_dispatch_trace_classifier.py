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
