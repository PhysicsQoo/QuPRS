from QuPRS.pathsum import PathSum


def test_HH():

    circuit1 = PathSum.QuantumCircuit(1)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.reduction()

    circuit2 = PathSum.QuantumCircuit(1)
    assert circuit1 == circuit2, "\ncircuit1: {},\n circuit2: {}".format(
        circuit1, circuit2
    )


def test_HXH():

    circuit1 = PathSum.QuantumCircuit(1)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.x(0)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.reduction()

    circuit2 = PathSum.QuantumCircuit(1)
    circuit2 = circuit2.z(0)
    assert circuit1 == circuit2, "\ncircuit1: {},\n circuit2: {}".format(
        circuit1, circuit2
    )


def test_HCXH():

    circuit1 = PathSum.QuantumCircuit(2)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.cx(1, 0)
    circuit1 = circuit1.h(0)
    circuit1 = circuit1.reduction()

    circuit2 = PathSum.QuantumCircuit(2)
    circuit2 = circuit2.cz(1, 0)
    assert circuit1 == circuit2, "\ncircuit1: {},\n circuit2: {}".format(
        circuit1, circuit2
    )
