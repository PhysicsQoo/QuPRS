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


# Rust validates Ganak's native executable architecture and --version before
# launching it. An injected shell script cannot exercise the solver failure
# modes in that path; do not bypass or mock away the safety/provenance gate.
# Keep those fault-injection cases on Python/Ganak and both GPMC backends;
# Rust/Ganak missing-executable is separately observable at the public API.
FAILURE_CASES = (
    "timeout", "nonzero", "malformed", "nonfinite", "missing",
)
PROCESS_SCENARIOS = [
    (backend, solver, failure)
    for backend, solver in (
        ("python", "ganak"), ("python", "gpmc"), ("rust", "gpmc")
    )
    for failure in FAILURE_CASES
] + [("rust", "ganak", "missing")]


@pytest.mark.skipif(os.name != "posix", reason="Controlled POSIX solver executable")
@pytest.mark.parametrize("backend,solver,failure", PROCESS_SCENARIOS)
@pytest.mark.parametrize("distance_tolerance", [None, 2e-4])
def test_public_wmc_solver_failure_is_never_inequivalence(
    tmp_path, monkeypatch, backend, solver, failure, distance_tolerance
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
            approximate_distance_tolerance=distance_tolerance,
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


@pytest.mark.skipif(os.name != "posix", reason="Controlled POSIX solver executable")
def test_rust_ganak_rejects_non_native_override_before_solver_launch(
    tmp_path, monkeypatch,
):
    """Architecture/provenance verification must reject shell fault injectors."""
    import QuPRS.utils as resources

    fake = tmp_path / "not-a-native-ganak"
    fake.write_text("#!/bin/sh\nsleep 30\n")
    fake.chmod(0o700)

    @contextmanager
    def selected_resource(name):
        assert name == "ganak"
        yield fake

    monkeypatch.setattr(
        resources, "get_ganak_path",
        lambda verify=False: selected_resource("ganak"),
    )
    identity, hh = QuantumCircuit(1), QuantumCircuit(1)
    hh.h(0)
    hh.h(0)

    with pytest.raises(ValueError, match="Wrong Ganak architecture"):
        check_equivalence(
            identity, hh, backend="rust", method="wmc_only",
            tool_name="ganak", timeout=4,
        )
