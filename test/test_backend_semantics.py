"""Independent dense-operator semantic oracle for the public QuPRS API.

These fixtures deliberately use only QASM2-supported gates. They test semantic
outcomes rather than reduction traces, rule counts, or numerical speed. This
module is separate from experimental reduction-scheduling test branches.
"""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


CASES = (
    ("cancellation", "equivalent"),
    ("controlled_x", "equivalent"),
    ("non_clifford", "equivalent"),
    ("global_phase", "equivalent*"),
    ("inequivalent", "not_equivalent"),
)
STRATEGIES = ("Naive", "Straightforward", "Proportional", "Difference")
METHODS = ("reduction_rules", "hybrid", "wmc_only")
BACKENDS = ("python", "rust")
SOLVERS = ("ganak", "gpmc")
DECIDED = {"equivalent", "equivalent*", "not_equivalent"}


def _make_pair(case):
    """Give each circuit a common nonempty prefix and an independent suffix."""
    n = 2 if case == "controlled_x" else 1
    left, right = QuantumCircuit(n), QuantumCircuit(n)
    for circuit in (left, right):
        circuit.h(0)
        circuit.h(0)

    if case == "cancellation":
        left.h(0)
        left.h(0)
    elif case == "controlled_x":
        left.cx(0, 1)
        right.h(1)
        right.cz(0, 1)
        right.h(1)
    elif case == "non_clifford":
        for circuit in (left, right):
            circuit.t(0)
            circuit.h(0)
            circuit.s(0)
    elif case == "global_phase":
        # X and Z anticommute, so XZXZ = -I (not exact equality).
        for gate in ("x", "z", "x", "z"):
            getattr(left, gate)(0)
    elif case == "inequivalent":
        left.x(0)
    else:
        raise ValueError(f"Unknown oracle case: {case}")
    return left, right


def _operator_status(left, right):
    """Classify the exact matrix relation independently of PathSum and WMC."""
    u, v = Operator(left), Operator(right)
    # This oracle tolerance validates the fixture matrices; it is NOT the
    # 1e-6 normalized-magnitude/phase threshold used by floating WMC counts.
    if np.allclose(u.data, v.data, atol=1e-10, rtol=0):
        return "equivalent"
    if u.equiv(v, atol=1e-10, rtol=0):
        return "equivalent*"
    return "not_equivalent"


@pytest.mark.parametrize("case,expected", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("method", METHODS)
def test_public_result_matches_independent_operator(
    case, expected, backend, solver, strategy, method
):
    left, right = _make_pair(case)
    oracle_status = _operator_status(left, right)
    assert oracle_status == expected, (
        f"Fixture {case} disagrees with its independent operator oracle: "
        f"{oracle_status} != {expected}"
    )

    result = check_equivalence(
        left,
        right,
        method=method,
        strategy=strategy,
        tool_name=solver,
        backend=backend,
        timeout=60,
    )
    # Reduction has a structural proof obligation and remains decisive.
    # WMC-only can return Unknown for an exact identity when its floating
    # count lacks a separate positive certificate. This is explicit,
    # scientifically conservative incompleteness, not a timeout/error.
    if method == "wmc_only":
        assert result.equivalent in DECIDED | {"unknown"}
    else:
        assert result.equivalent in DECIDED, (
            "Reduction/hybrid fixture must remain decidable: "
            f"{case}, {backend}, {solver}, {strategy}, {method}"
        )
    assert (result.equivalent == oracle_status or
            (method == "wmc_only" and result.equivalent == "unknown")), (
        f"{case}: {backend}/{solver}/{method}/{strategy}: "
        f"expected {oracle_status}, got {result.equivalent}"
    )
    if method == "wmc_only":
        # Ensure a green solver-specific WMC case actually exercised the
        # selected solver, instead of only reporting a reduction result.
        assert result.tool_name == solver
        assert result.tool_time is not None
