import signal

from QuPRS.interface.load_qiskit import add_gate, get_gates


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


signal.signal(signal.SIGALRM, timeout_handler)


def proportional(
    pathsum_circuit,
    qiskit_circuit1,
    qiskit_circuit2,
    l1,
    l2,
    output_dict=dict(),
    timeout=600,
):
    gates1 = get_gates(qiskit_circuit1)
    gates2 = get_gates(qiskit_circuit2)

    min_length = min(l1, l2)
    d = l1 - l2
    r = int(l1 / l2) if d > 0 else int(l2 / l1)

    signal.alarm(timeout)
    count = 0
    try:
        if r == 1:
            for i in range(min_length):
                gate1 = gates1[i]
                gate2 = gates2[i]
                pathsum_circuit, count = add_gate(pathsum_circuit, gate1, count=count)
                pathsum_circuit, count = add_gate(
                    pathsum_circuit, gate2, count=count, is_bra=True
                )

            if d > 0:
                for i in range(d):
                    gate1 = gates1[min_length + i]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate1, count=count
                    )
            elif d < 0:
                for i in range(-d):
                    gate2 = gates2[min_length + i]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate2, count=count, is_bra=True
                    )
        elif d > 0:
            for i in range(l2):
                for j in range(r):
                    gate1 = gates1[i * r + j]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate1, count=count
                    )
                gate2 = gates2[i]
                pathsum_circuit, count = add_gate(
                    pathsum_circuit, gate2, count=count, is_bra=True
                )
            d2 = l1 - r * l2
            if d2 > 0:
                for i in range(d2):
                    gate1 = gates1[l2 * r + i]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate1, count=count
                    )
        elif d < 0:
            for i in range(l1):
                for j in range(r):
                    gate2 = gates2[i * r + j]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate2, count=count, is_bra=True
                    )
                gate1 = gates1[i]
                pathsum_circuit, count = add_gate(pathsum_circuit, gate1, count=count)
            d2 = l2 - r * l1
            if d2 > 0:
                for i in range(d2):
                    gate2 = gates2[l1 * r + i]
                    pathsum_circuit, count = add_gate(
                        pathsum_circuit, gate2, count=count, is_bra=True
                    )

        pathsum_circuit = pathsum_circuit.reduction()

    except TimeoutError:
        output_dict["Time"] = f">{timeout}"
        output_dict["equivalent"] = "Timeout"
        output_dict["progress"] = f"{count}/{l1 + l2}"
        return output_dict, pathsum_circuit
    finally:
        signal.alarm(0)

    output_dict["progress"] = f"{count}/{l1 + l2}"
    return output_dict, pathsum_circuit


def naive(
    pathsum_circuit,
    qiskit_circuit1,
    qiskit_circuit2,
    l1,
    l2,
    output_dict=dict(),
    timeout=600,
):
    gates1 = get_gates(qiskit_circuit1)
    gates2 = get_gates(qiskit_circuit2)

    signal.alarm(timeout)
    count = 0
    try:
        for i in range(min(len(gates1), len(gates2))):
            gate1 = gates1[i]
            gate2 = gates2[i]

            pathsum_circuit, count = add_gate(pathsum_circuit, gate1, count=count)
            pathsum_circuit, count = add_gate(
                pathsum_circuit, gate2, count=count, is_bra=True
            )
        if len(gates1) > len(gates2):
            for gate1 in gates1[len(gates2) :]:
                pathsum_circuit, count = add_gate(pathsum_circuit, gate1, count=count)
        elif len(gates1) < len(gates2):
            for gate2 in gates2[len(gates1) :]:
                pathsum_circuit, count = add_gate(
                    pathsum_circuit, gate2, count=count, is_bra=True
                )
        pathsum_circuit = pathsum_circuit.reduction()
    except TimeoutError:
        output_dict["Time"] = f">{timeout}"
        output_dict["equivalent"] = "Timeout"
        output_dict["progress"] = f"{count}/{l1 + l2}"
        return output_dict, pathsum_circuit
    finally:
        signal.alarm(0)

    output_dict["progress"] = f"{count}/{l1 + l2}"
    return output_dict, pathsum_circuit


def straightforward(
    pathsum_circuit,
    qiskit_circuit1,
    qiskit_circuit2,
    l1,
    l2,
    output_dict=dict(),
    timeout=600,
):
    qiskit_circuit = qiskit_circuit1.compose(qiskit_circuit2.inverse())
    gates = get_gates(qiskit_circuit)
    signal.alarm(timeout)
    count = 0
    try:
        for gate in gates:
            pathsum_circuit, count = add_gate(pathsum_circuit, gate, count=count)
        pathsum_circuit = pathsum_circuit.reduction()
    except TimeoutError:
        output_dict["Time"] = f">{timeout}"
        output_dict["equivalent"] = "Timeout"
        output_dict["progress"] = f"{count}/{l1 + l2}"
        return output_dict, pathsum_circuit
    finally:
        signal.alarm(0)
    output_dict["progress"] = f"{count}/{l1 + l2}"
    return output_dict, pathsum_circuit


def difference(
    pathsum_circuit,
    qiskit_circuit1,
    qiskit_circuit2,
    l1,
    l2,
    output_dict=dict(),
    timeout=600,
):
    gates1 = get_gates(qiskit_circuit1)
    gates2 = get_gates(qiskit_circuit2)

    import difflib

    def compare_lists_with_index(list1, list2):
        list1_str = [str(item) for item in list1]
        list2_str = [str(item) for item in list2]
        diff = list(difflib.ndiff(list1_str, list2_str))
        # Store index and its changes
        changes = []
        # Track current index
        index1 = index2 = 0
        for line in diff:
            if line.startswith("-"):
                # Element from `list1`, marked as deleted
                changes.append(("-", index1, list1[index1]))
                index1 += 1
            elif line.startswith("+"):
                # Element from `list2`, marked as added
                changes.append(("+", index2, list2[index2]))
                index2 += 1
            elif line.startswith(" "):
                # Element present in both lists
                changes.append((" ", index1, list1[index1]))
                index1 += 1
                index2 += 1
        return changes

    # Get the changed indices and their details
    try:
        changes = compare_lists_with_index(gates1, gates2)
        count = 0
        signal.alarm(timeout)
        for change_type, index, value in changes:
            if change_type == "-":
                pathsum_circuit, count = add_gate(pathsum_circuit, value, count=count)
            elif change_type == "+":
                pathsum_circuit, count = add_gate(
                    pathsum_circuit, value, count=count, is_bra=True
                )
            elif change_type == " ":
                pathsum_circuit, count = add_gate(pathsum_circuit, value, count=count)
                pathsum_circuit, count = add_gate(
                    pathsum_circuit, value, count=count, is_bra=True
                )
        pathsum_circuit = pathsum_circuit.reduction()
    except TimeoutError:
        output_dict["Time"] = f">{timeout}"
        output_dict["equivalent"] = "Timeout"
        output_dict["progress"] = f"{count}/{l1 + l2}"
        return output_dict, pathsum_circuit
    finally:
        signal.alarm(0)
    output_dict["progress"] = f"{count}/{l1 + l2}"
    return output_dict, pathsum_circuit
