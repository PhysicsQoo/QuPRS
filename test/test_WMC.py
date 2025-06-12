from QuPRS import config
from QuPRS.pathsum import PathSum
from QuPRS.interface.ps2wmc import to_DIMACS, run_wmc
from QuPRS.utils.util import get_theta

import math
TOLERANCE = config.TOLERANCE
def test_CX_XT_CH_XTdg__2():
    qubit_num = 2
    circuit = PathSum.QuantumCircuit(qubit_num)

    circuit = circuit.cx(0,1)
    circuit = circuit.x(0)
    circuit = circuit.t(1)
    circuit = circuit.ch(0,1)
    circuit = circuit.x(0)
    circuit = circuit.tdg(1)
    circuit = circuit.cx(0,1)
    circuit = circuit.x(0)
    circuit = circuit.t(1)
    circuit = circuit.ch(0,1)
    circuit = circuit.x(0)
    circuit = circuit.tdg(1)
    circuit = circuit.reduction()
    
    to_DIMACS(circuit)
    complex_number = run_wmc()

    abs_num = math.sqrt(complex_number[0]**2 + complex_number[1]**2)
    log_wmc = math.log2(abs_num)
    expect = circuit.num_qubits+circuit.num_pathvar/2

    assert abs(log_wmc - expect) < TOLERANCE, "should be {}, but got {}".format(expect, log_wmc)
    
    theta = get_theta(complex_number[1]/abs_num, complex_number[0]/abs_num)
    
    assert abs(theta) < TOLERANCE, "should be 0, but got {}".format(theta)

def test_HH():
    PathSum.set_reduction_switch(False)
    circuit = PathSum.QuantumCircuit(1)
    circuit = circuit.h(0)
    circuit = circuit.h(0)

    to_DIMACS(circuit)
    complex_number = run_wmc()

    abs_num = math.sqrt(complex_number[0]**2 + complex_number[1]**2)
    log_wmc = math.log2(abs_num)
    expect = circuit.num_qubits+circuit.num_pathvar/2

    assert abs(log_wmc - expect) < TOLERANCE, "should be {}, but got {}".format(expect, log_wmc)
    
    theta = get_theta(complex_number[1]/abs_num, complex_number[0]/abs_num)
    
    assert abs(theta) < TOLERANCE, "should be 0, but got {}".format(theta)

