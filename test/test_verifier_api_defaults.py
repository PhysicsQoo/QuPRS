"""Python public, PyO3 and native crate default-contract regression.

The Rust crate's typed/legacy function parity is tested by Rust unit tests.
The direct PyO3 tests use real solvers rather than mocking its return values.
"""
from contextlib import contextmanager
import inspect
import os

import pytest
from qiskit import QuantumCircuit

from QuPRS import _pathsum_rust, check_equivalence, config
from QuPRS.utils import WMC
from QuPRS.utils.solver_process import SOLVER_ENV_LOCK


PREFIX = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
IDENTITY = PREFIX
RZ_NOT_WITHIN_DEFAULT = PREFIX + "rz(0.001) q[0];\n"


@contextmanager
def native_solver(solver):
    key = f"QUPRS_{solver.upper()}_PATH"
    with SOLVER_ENV_LOCK:
        old = os.environ.get(key)
        with WMC(solver) as executable:
            os.environ[key] = str(executable)
            try:
                yield
            finally:
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old


@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_direct_pyo3_defaults_use_1e8_not_historical_1e6(solver):
    with native_solver(solver):
        current = _pathsum_rust.check_equivalence(
            IDENTITY, RZ_NOT_WITHIN_DEFAULT,
            method="wmc_only", strategy="Naive", tool_name=solver, timeout=45,
        )
        historical = _pathsum_rust.check_equivalence(
            IDENTITY, RZ_NOT_WITHIN_DEFAULT,
            method="wmc_only", strategy="Naive", tool_name=solver, timeout=45,
            wmc_magnitude_tolerance=1e-6, wmc_phase_tolerance=1e-6,
        )
    assert current["status"] == "Not Equivalent"
    assert historical["status"] in {"Equivalent", "Equivalent (Up to Global Phase)"}
    assert current.get("wmc_solver_time_sec") is not None
    assert historical.get("wmc_solver_time_sec") is not None


def test_rust_ffi_rejects_unsupported_safe_mode():
    with pytest.raises(ValueError, match="safe_mode is not supported"):
        _pathsum_rust.check_equivalence(
            IDENTITY, IDENTITY, method="reduction_rules", safe_mode=True,
        )


def test_public_rust_api_does_not_claim_safe_mode():
    one = QuantumCircuit(1)
    with pytest.raises(ValueError, match="safe_mode is not supported"):
        check_equivalence(
            one, one, method="reduction_rules", backend="rust", safe_mode=True,
        )


def test_python_public_api_retains_two_independent_wmc_defaults():
    params = inspect.signature(check_equivalence).parameters
    assert "wmc_policy" not in params
    assert params["wmc_magnitude_tolerance"].default is None
    assert params["wmc_phase_tolerance"].default is None
    assert params["rr_tolerance"].default is None
    assert params["phase_tolerance"].default is None
    assert not hasattr(config, "TOLERANCE")
    assert not hasattr(config, "set_tolerance")
    assert not hasattr(config, "get_tolerance")
    assert config.WMC_MAGNITUDE_TOLERANCE == 1e-8
    assert config.WMC_PHASE_TOLERANCE == 1e-8
    one = QuantumCircuit(1)
    observed = check_equivalence(one, one, method="reduction_rules")
    assert observed.equivalent == "equivalent"
    assert observed.tool_time is None
    assert observed.wmc_numerical_verdict is None
    assert observed.wmc_magnitude_tolerance == 1e-8
    assert observed.wmc_phase_tolerance == 1e-8
