"""PyO3 boundary regressions for stable-ABI upgrades.

Exercise owned result conversion, PyRefMut gate chaining, and early-return
dictionary construction without involving an external WMC solver.
"""
from QuPRS import _pathsum_rust

QASM_ONE = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
QASM_TWO = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'


def test_native_pyo3_returns_owned_result_dictionary():
    result = _pathsum_rust.check_equivalence(
        QASM_ONE, QASM_ONE, method="reduction_rules", timeout=15
    )
    assert type(result) is dict
    assert result["status"] == "Equivalent"
    assert type(result["stats"]) is dict
    assert result["wmc_solver_invoked"] is False


def test_native_pyo3_pyrefmut_circuit_chain_and_extraction():
    circuit = _pathsum_rust.QuantumCircuit(1)
    assert circuit.h(0) is circuit
    assert circuit.x(0) is circuit
    result = _pathsum_rust.check_equivalence(
        circuit, circuit, method="reduction_rules", timeout=15
    )
    assert result["status"] == "Equivalent"
    assert result["gates1"] == result["gates2"] == 2


def test_native_pyo3_width_mismatch_early_return():
    result = _pathsum_rust.check_equivalence(
        QASM_ONE, QASM_TWO, method="reduction_rules", timeout=15
    )
    assert type(result) is dict
    assert result["status"] == "Not Equivalent"
    assert result["wmc_solver_invoked"] is False
    assert type(result["stats"]) is dict
