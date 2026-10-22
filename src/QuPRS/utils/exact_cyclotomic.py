"""Bounded exact Clifford+T operator certificate over Q(zeta_8).

zeta = exp(i*pi/4), zeta**4 = -1; 1/sqrt(2) = (zeta-zeta**3)/2.
A 4-tuple of Fractions represents a+b*zeta+c*zeta**2+d*zeta**3.
No floating arithmetic, weighted model counting, solver, or tolerance is
used in a certificate. All inputs are re-evaluated by the verifier.

Deliberately limited to <=4 qubits and 128 gates across both circuits.
QASM strings, symbolic parameters, measurements, nonzero explicit global
phases, and unsupported operations are NOT admissible.
"""

from fractions import Fraction

from qiskit import QuantumCircuit

_ZERO = (Fraction(0),) * 4
_ONE = (Fraction(1), Fraction(0), Fraction(0), Fraction(0))
_ZETA = (Fraction(0), Fraction(1), Fraction(0), Fraction(0))
_I = (Fraction(0), Fraction(0), Fraction(1), Fraction(0))
_MINUS_I = tuple(-x for x in _I)
_MINUS_ZETA3 = (Fraction(0), Fraction(0), Fraction(0), Fraction(-1))
_H_FACTOR = (
    Fraction(0), Fraction(1, 2), Fraction(0), Fraction(-1, 2),
)
_SUPPORTED = frozenset({
    "h", "x", "y", "z", "s", "sdg", "t", "tdg",
    "cx", "cz", "swap", "ccx",
})
_ARITY = {
    "h": 1, "x": 1, "y": 1, "z": 1, "s": 1,
    "sdg": 1, "t": 1, "tdg": 1,
    "cx": 2, "cz": 2, "swap": 2, "ccx": 3,
}


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _neg(a):
    return tuple(-x for x in a)


def _mul(a, b):
    """Multiplication in Q[x]/(x**4+1), computed with exact Fractions."""
    out = [Fraction(0)] * 4
    for i in range(4):
        if not a[i]:
            continue
        for j in range(4):
            if not b[j]:
                continue
            k = i + j
            out[k % 4] += (-1 if k >= 4 else 1) * a[i] * b[j]
    return tuple(out)


def _prepare(c1, c2):
    if not isinstance(c1, QuantumCircuit) or not isinstance(c2, QuantumCircuit):
        return None
    n = c1.num_qubits
    if (n < 1 or n > 4 or n != c2.num_qubits or c1.num_clbits
            or c2.num_clbits or len(c1.data) + len(c2.data) > 128):
        return None
    gates = []
    for circuit in (c1, c2):
        if type(circuit.global_phase) not in (int, float) or circuit.global_phase != 0:
            return None
        sequence = []
        for instruction in circuit.data:
            operation = instruction.operation
            name = operation.name
            if (name not in _SUPPORTED or len(operation.params) != 0
                    or len(instruction.qubits) != _ARITY[name]
                    or getattr(operation, "condition", None) is not None):
                return None
            bits = tuple(circuit.find_bit(q).index for q in instruction.qubits)
            if len(set(bits)) != len(bits):
                return None
            sequence.append((name, bits))
        gates.append(sequence)
    return n, gates[0], gates[1]


def _evolve(n, gates, basis):
    dimension = 1 << n
    state = [_ZERO] * dimension
    state[basis] = _ONE
    for name, bits in gates:
        m = 1 << bits[0]
        if name in {"cx", "cz", "ccx"}:
            controls = (m,) if name in {"cx", "cz"} else (m, 1 << bits[1])
            target = 1 << bits[-1]
            if name == "cz":
                for k in range(dimension):
                    if k & m and k & target:
                        state[k] = _neg(state[k])
            else:
                for k in range(dimension):
                    if all(k & c for c in controls) and not (k & target):
                        state[k], state[k | target] = state[k | target], state[k]
            continue
        if name == "swap":
            target = 1 << bits[1]
            for k in range(dimension):
                if not (k & m) and (k & target):
                    j = (k | m) & ~target
                    state[k], state[j] = state[j], state[k]
            continue
        if name in {"x", "y", "h"}:
            for k in range(dimension):
                if k & m:
                    continue
                j = k | m
                u, v = state[k], state[j]
                if name == "x":
                    state[k], state[j] = v, u
                elif name == "y":
                    state[k], state[j] = _mul(_MINUS_I, v), _mul(_I, u)
                else:
                    state[k] = _mul(_H_FACTOR, _add(u, v))
                    state[j] = _mul(_H_FACTOR, _add(u, _neg(v)))
            continue
        factor = {
            "z": _neg(_ONE),
            "s": _I,
            "sdg": _MINUS_I,
            "t": _ZETA,
            "tdg": _MINUS_ZETA3,
        }[name]
        for k in range(dimension):
            if k & m:
                state[k] = _mul(factor, state[k])
    return state


def _decision(prepared):
    """Projective-minor exact proof, with strict-equality refinement."""
    n, a, b = prepared
    d = 1 << n
    # Anchor must be established BEFORE traversing any matrix entries:
    # otherwise an earlier coordinate with V=0, U!=0 could be skipped.
    v0 = _evolve(n, b, 0)
    ay = next((row for row, value in enumerate(v0) if value != _ZERO), None)
    if ay is None:
        raise AssertionError("A unitary operator has a nonzero first column")
    anchor = (ay, 0, _evolve(n, a, 0)[ay], v0[ay])
    all_equal = True
    for x in range(d):
        left, right = _evolve(n, a, x), _evolve(n, b, x)
        for y in range(d):
            u, v = left[y], right[y]
            if u != v:
                all_equal = False
            if anchor is None and v != _ZERO:
                anchor = (y, x, u, v)
            if anchor is not None:
                ay, ax, au, av = anchor
                if _mul(u, av) != _mul(au, v):
                    return {
                        "schema": "quprs-source-certificate-v1",
                        "kind": "cyclotomic-operator-minor",
                        "status": "not_equivalent",
                        "anchor": [ay, ax],
                        "witness": [y, x],
                        "provenance": "exact-q-zeta8-four-coefficient-replay",
                    }
    if anchor is None:
        raise AssertionError("A unitary circuit cannot have a zero operator")
    return {
        "schema": "quprs-source-certificate-v1",
        "kind": "cyclotomic-operator-full",
        "status": "equivalent" if all_equal else "equivalent*",
        "qubits": n,
        "entries_checked": d * d,
        "provenance": "exact-q-zeta8-four-coefficient-replay",
    }


def make_cyclotomic_certificate(circuit1, circuit2):
    """A complete, exact projective operator check for the admitted domain."""
    prepared = _prepare(circuit1, circuit2)
    return None if prepared is None else _decision(prepared)


def verify_cyclotomic_certificate(circuit1, circuit2, certificate):
    """Recompute every exact source gate and compare entire certificate."""
    if not isinstance(certificate, dict):
        return False
    # Never accept claimed matrix entries, status or witness without replay.
    result = make_cyclotomic_certificate(circuit1, circuit2)
    return result is not None and certificate == result
