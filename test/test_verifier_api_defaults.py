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
def test_direct_pyo3_defaults_use_projective_distance(solver):
    with native_solver(solver):
        current = _pathsum_rust.check_equivalence(
            IDENTITY, RZ_NOT_WITHIN_DEFAULT,
            method="wmc_only", strategy="Naive", tool_name=solver, timeout=45,
        )
        explicitly_loose = _pathsum_rust.check_equivalence(
            IDENTITY, RZ_NOT_WITHIN_DEFAULT,
            method="wmc_only", strategy="Naive", tool_name=solver, timeout=45,
            approximate_distance_tolerance=1e-3,
        )
    assert current["status"] == "Not Equivalent"
    assert explicitly_loose["status"] in {"Equivalent", "Equivalent (Up to Global Phase)"}
    assert current.get("wmc_solver_time_sec") is not None
    assert explicitly_loose.get("wmc_solver_time_sec") is not None


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


def test_python_public_api_has_single_distance_metric_and_phase_default():
    params = inspect.signature(check_equivalence).parameters
    assert "wmc_policy" not in params
    assert "wmc_magnitude_tolerance" not in params
    assert params["approximate_distance_tolerance"].default == 1e-8
    assert params["wmc_phase_tolerance"].default is None
    assert params["rr_tolerance"].default is None
    assert params["phase_tolerance"].default is None
    assert not hasattr(config, "TOLERANCE")
    assert not hasattr(config, "set_tolerance")
    assert not hasattr(config, "get_tolerance")
    assert not hasattr(config, "WMC_MAGNITUDE_TOLERANCE")
    assert config.DEFAULT_DISTANCE_TOLERANCE == 1e-8
    assert config.WMC_PHASE_TOLERANCE == 1e-8
    one = QuantumCircuit(1)
    observed = check_equivalence(one, one, method="reduction_rules")
    assert observed.equivalent == "equivalent"
    assert observed.tool_time is None
    assert observed.wmc_numerical_verdict is None
    assert observed.approximate_distance_tolerance == 1e-8
    assert not hasattr(observed, 'wmc_magnitude_tolerance')
    assert observed.wmc_phase_tolerance == 1e-8

def test_legacy_magnitude_argument_is_not_a_second_policy():
    one = QuantumCircuit(1)
    with pytest.raises(TypeError):
        check_equivalence(one, one, method="reduction_rules",
                          wmc_magnitude_tolerance=1e-8)
    with pytest.raises(TypeError):
        _pathsum_rust.check_equivalence(
            IDENTITY, IDENTITY, method="reduction_rules",
            wmc_magnitude_tolerance=1e-8
        )
