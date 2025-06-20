import QuPRS.pathsum as pathsum
from QuPRS.pathsum import PathSum

support_gate_set = pathsum.support_gate_set().copy()
support_gate_set.update(["barrier", "measure"])


def gate_map(
    circuit: PathSum,
    gate_name: str,
    qubit,
    gate_params=[],
    is_bra: bool = False,
    debug=False,
):
    """
    Applies a gate to the circuit object by its name.
    """
    if debug:
        print("add gate: %s, %s, %s, %s" % (gate_name, qubit, gate_params, is_bra))
        print("circuit in", circuit)

    assert gate_name in support_gate_set, "Not support %s gate yet." % gate_name

    if gate_name in ["barrier", "measure"]:
        return circuit

    func = getattr(circuit, gate_name)

    if gate_params == []:
        circuit = func(*qubit, is_bra)
    else:
        circuit = func(*gate_params, *qubit, is_bra)

    if debug:
        print("circuit out", circuit)

    return circuit
