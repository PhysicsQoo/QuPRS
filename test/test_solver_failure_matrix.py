"""Public solver-failure classification across independent backends and solvers.

The executables below are synthetic fault injectors, not WMC solutions.
A process failure must never become a proof of circuit inequivalence.
"""
from contextlib import contextmanager
import os

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.utils.solver_process import SolverProcessError


@pytest.mark.skipif(os.name != "posix", reason="Controlled POSIX solver executable")
@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["ganak", "gpmc"])
@pytest.mark.parametrize(
    "failure",
    ["timeout", "nonzero", "malformed", "nonfinite", "missing"],
)
def test_public_wmc_solver_failure_is_never_inequivalence(
    tmp_path, monkeypatch, backend, solver, failure
):
    """Exercise the public API, actual subprocess policy and Rust FFI path."""
    executable = tmp_path / ("controlled-" + solver)
    scripts = {
        "timeout": "#!/bin/sh\nsleep 30\n",
        "nonzero": "#!/bin/sh\nprintf '%s\\n' 'c s exact quadruple float 4'\nexit 7\n",
        "malformed": "#!/bin/sh\nprintf '%s\\n' 'not a count'\n",
        "nonfinite": "#!/bin/sh\nprintf '%s\\n' 'c s exact quadruple float nan'\n",
    }
    if failure != "missing":
        executable.write_text(scripts[failure])
        executable.chmod(0o700)

    @contextmanager
    def selected_resource(name):
        assert name == solver, "Solver selection must not silently fall back"
        yield executable

    import QuPRS.utils as resources
    import QuPRS.interface.ps2wmc as python_adapter
    import QuPRS.utils.ganak_distribution as ganak_distribution

    monkeypatch.setattr(resources, "WMC", selected_resource)
    monkeypatch.setattr(python_adapter, "WMC", selected_resource)
    if solver == "ganak":
        # The Rust dispatcher requests this distribution entrypoint rather
        # than WMC("ganak"). Override only for the controlled test.
        monkeypatch.setattr(
            resources, "get_ganak_path",
            lambda verify=False: selected_resource("ganak"),
        )
        monkeypatch.setattr(
            ganak_distribution, "binary_diagnostics", lambda *_args, **_kwargs: {},
        )

    identity, hh = QuantumCircuit(1), QuantumCircuit(1)
    hh.h(0)
    hh.h(0)

    def invoke():
        return check_equivalence(
            identity, hh, backend=backend, method="wmc_only",
            tool_name=solver, timeout=4,
        )

    if failure == "timeout":
        result = invoke()
        assert result.equivalent == "Timeout"
        assert result.equivalent != "not_equivalent"
        return

    expected_error = (
        ValueError if backend == "rust"
        else SolverProcessError if failure == "missing"
        else RuntimeError if failure == "nonzero"
        else ValueError
    )
    with pytest.raises(expected_error) as error:
        invoke()
    assert "not_equivalent" not in str(error.value).lower()
