"""RR-only incompleteness must not leak into Hybrid or WMC-only results.

Use actual, selected GPMC/Ganak subprocesses. A single Hadamard is an
unreduced path-sum with a live path variable, while the independent
1-qubit matrix oracle has trace zero against identity. This is a normal
RR-only unknown, not a failure of the WMC numerical classifier.
"""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
def test_rr_unknown_hybrid_and_wmc_only_decide_same_source(backend, solver):
    identity = QuantumCircuit(1)
    hadamard = QuantumCircuit(1)
    hadamard.h(0)

    # Independent source-operator oracle: |Tr(H)|/2 = 0, D_proj = 1.
    overlap = np.trace(Operator(identity).data.conj().T @
                       Operator(hadamard).data) / 2
    assert np.isclose(abs(overlap), 0, atol=1e-14, rtol=0)
    assert np.isclose(np.sqrt(1 - abs(overlap) ** 2), 1, atol=1e-14)

    kwargs = dict(
        backend=backend,
        tool_name=solver,
        strategy="Naive",
        timeout=60,
        rr_tolerance=1e-10,
        approximate_distance_tolerance=1e-8,
    )
    rr = check_equivalence(identity, hadamard, method="reduction_rules", **kwargs)
    hybrid = check_equivalence(identity, hadamard, method="hybrid", **kwargs)
    wmc = check_equivalence(identity, hadamard, method="wmc_only", **kwargs)

    # RR-only may be inconclusive without taking an external WMC step.
    assert rr.equivalent == "unknown", (backend, solver, rr.equivalent)
    assert rr.wmc_solver_invoked is False
    assert rr.tool_time is None
    assert rr.wmc_numerical_verdict is None

    # Both WMC paths use the same source-distance result; RR's unknown
    # is a stage result only and may not be the final Hybrid verdict.
    for name, result in (("hybrid", hybrid), ("wmc_only", wmc)):
        assert result.equivalent == "not_equivalent", (
            backend, solver, name, result.equivalent
        )
        assert result.wmc_solver_invoked is True
        assert result.tool_time is not None
        assert result.wmc_numerical_verdict == result.equivalent
        assert result.rr_approximate is False
