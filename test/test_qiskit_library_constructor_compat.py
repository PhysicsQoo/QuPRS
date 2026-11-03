"""Version-bounded Qiskit 1.x / 2.x circuit library constructor compatibility.

These are semantic API controls, not package-metadata checks. The legacy
BlueprintCircuit constructor and the modern functional constructor must both
produce usable public circuit pairs without changing QuPRS verification logic.
"""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence
from QuPRS.utils.Qiskit_Circuit_Utils import pqc_generator


@pytest.mark.parametrize(
    "name",
    ["NLocal", "ExcitationPreserving", "RealAmplitudes", "EfficientSU2", "PauliTwoDesign"],
)
def test_generator_supported_on_qiskit_1_and_2(name):
    left, right, label = pqc_generator(qubit_num=2, reps=1, function_name=name)
    assert label == f"{name}_2_1"
    assert left.num_qubits == right.num_qubits == 2
    assert len(left.parameters) == len(right.parameters)
    assert left.size() > 0 and right.size() > 0

    # Bind the *same parameters by name*; independent floating operator
    # evaluation catches wire order, gate decomposition, and parameter order
    # defects without claiming rigorous symbolic equivalence.
    values = {name: (i + 1) / 17.0 for i, name in enumerate(
        sorted({p.name for p in left.parameters | right.parameters})
    )}
    bound_left = left.assign_parameters(
        {p: values[p.name] for p in left.parameters}
    )
    bound_right = right.assign_parameters(
        {p: values[p.name] for p in right.parameters}
    )
    assert np.allclose(
        Operator(bound_left).data, Operator(bound_right).data,
        atol=1e-10, rtol=0,
    ), (name, left, right)


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_core_verifier_not_regressed_by_qiskit_library_adapter(backend):
    ident = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    result = check_equivalence(
        ident, hh, method="reduction_rules", backend=backend, timeout=30
    )
    assert result.equivalent == "equivalent", result
