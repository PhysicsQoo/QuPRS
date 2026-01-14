import math
import tempfile
import pytest

from QuPRS import config
from QuPRS.interface.ps2wmc import run_wmc, to_DIMACS
from QuPRS.pathsum import PathSum
from QuPRS.utils.util import get_theta

TOLERANCE = config.TOLERANCE


def generte_test(circuit, tool_name):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".cnf") as temp_file:
        temp_name = temp_file.name
        to_DIMACS(circuit, temp_name, tool_name=tool_name)
        complex_number = run_wmc(temp_name, tool_name)
    abs_num = math.sqrt(complex_number[0] ** 2 + complex_number[1] ** 2)
    log_wmc = math.log2(abs_num)
    expect = circuit.num_qubits + circuit.num_pathvar / 2
    assert abs(log_wmc - expect) < TOLERANCE, "should be {}, but got {}".format(
        expect, log_wmc
    )
    return complex_number, abs_num

@pytest.mark.parametrize("tool_name", ["gpmc", "ganak"])
def test_CX_XT_CH_XTdg__2(tool_name):
    qubit_num = 2
    circuit = PathSum.QuantumCircuit(qubit_num)

    circuit = circuit.cx(0, 1)
    circuit = circuit.x(0)
    circuit = circuit.t(1)
    circuit = circuit.ch(0, 1)
    circuit = circuit.x(0)
    circuit = circuit.tdg(1)
    circuit = circuit.cx(0, 1)
    circuit = circuit.x(0)
    circuit = circuit.t(1)
    circuit = circuit.ch(0, 1)
    circuit = circuit.x(0)
    circuit = circuit.tdg(1)
    circuit = circuit.reduction()

    complex_number, abs_num = generte_test(circuit, tool_name=tool_name)
    theta = get_theta(complex_number[1] / abs_num, complex_number[0] / abs_num)
    assert abs(theta) < TOLERANCE or abs(2*math.pi-theta) < TOLERANCE, "should be 0, but got {}".format(theta)

@pytest.mark.parametrize("tool_name", ["gpmc", "ganak"])
def test_HH(tool_name):
    circuit = PathSum.QuantumCircuit(1)
    circuit.set_reduction_switch(False)
    circuit = circuit.h(0)
    circuit = circuit.h(0)

    complex_number, abs_num = generte_test(circuit, tool_name=tool_name)
    theta = get_theta(complex_number[1] / abs_num, complex_number[0] / abs_num)
    assert abs(theta) < TOLERANCE or abs(2*math.pi-theta) < TOLERANCE, "should be 0, but got {}".format(theta)
