"""Independently checkable *structural* certificates for exact discrete gates.

No floating solver output enters these proofs. Parameterized gates are
excluded because a certified exact source-angle domain is not yet wired
through both public backends. A circuit that needs path summation or
nontrivial phase equality beyond these sufficient conditions returns None.

This deliberately does not claim a certified WMC enclosure exists.
"""

_DISCRETE_GATES = frozenset({
    "h", "x", "y", "z", "s", "sdg", "t", "tdg",
    "cx", "cz", "swap", "ccx",
})


def certify_discrete_pathsum(circuit1, circuit2, pathsum, identity):
    """Return an exact structural verdict when sufficient evidence exists.

    A no-path Boolean ANF is a deterministic basis map; distinct output ANFs
    prove a different unitary (not even up to global phase). If the output
    map is the identity, an identical zero phase proves strict equality,
    while an input-independent constant phase proves global-phase equality.
    """
    if any(
        instruction.operation.name not in _DISCRETE_GATES
        for circuit in (circuit1, circuit2)
        for instruction in circuit.data
    ):
        return None
    if pathsum.pathvar:
        return None
    if pathsum.f != identity.f:
        return "not_equivalent"
    if pathsum.P == identity.P:
        return "equivalent"
    if not pathsum.P.free_symbols:
        return "equivalent*"
    # A nonconstant multilinear phase over exact Clifford/T source angles
    # witnesses a relative phase on the same deterministic basis map.
    # Each nonzero monomial is observable on some Boolean assignment.
    return "not_equivalent"

# Source-level certificates are independent of the solver's weighted count
# and independent of the candidate Rust/Python phase-polynomial reductions.
# Keep a narrow allowlist: unsupported operations must not be erased.
from fractions import Fraction

from qiskit import QuantumCircuit


_CLIFFORD_GATES = frozenset({
    "h", "x", "y", "z", "s", "sdg", "sx", "sxdg",
    "cx", "cz",
})


def _source_quantum_circuits(circuit1, circuit2):
    # A QASM string/file is not a parsed, source-pinned exact-angle AST:
    # neither QASM-to-Qiskit nor QASM-to-Rust is certified as such yet.
    if not isinstance(circuit1, QuantumCircuit) or not isinstance(circuit2, QuantumCircuit):
        return False
    return (
        circuit1.num_qubits == circuit2.num_qubits
        and 0 < circuit1.num_qubits <= 128
        and len(circuit1.data) + len(circuit2.data) <= 20000
        and circuit1.num_clbits == circuit2.num_clbits == 0
    )


def certify_rz_basis_witness(circuit1, circuit2):
    """Return an exact strict verdict for bounded diagonal RZ source circuits.

    The source contains *only* RZ operations with finite, concrete Python
    float/int arguments. The IEEE-754 value is an exact rational number
    (float.as_integer_ratio), NOT a rounded proxy for symbolic pi.

    On a computational basis vector x, RZ rotations contribute relative
    phase exp(i sum_j delta_j*x_j). Two unitaries are equal up to global
    phase iff every delta_j is an integer multiple of 2*pi. We prove
    delta_j != 0 and |delta_j| < 6 < 2*pi using exact Fraction arithmetic,
    so comparing |0..0> with |2**j> is a strict negative witness.

    If *all* deltas are zero, each RZ gate and inverse cancels exactly,
    including global phase. Larger angle differences or resource limits
    remain inconclusive; no floating sin/cos or WMC count is consulted.
    """
    if not _source_quantum_circuits(circuit1, circuit2):
        return None
    # This witness proves *strict* equality when all RZ deltas cancel.
    # A Qiskit circuit can carry an explicit global phase with no gates;
    # omitting that state would manufacture a false positive.
    for circuit in (circuit1, circuit2):
        phase = circuit.global_phase
        if type(phase) not in (int, float) or phase != 0:
            return None
    totals = [Fraction(0) for _ in range(circuit1.num_qubits)]
    for sign, circuit in ((1, circuit1), (-1, circuit2)):
        for instruction in circuit.data:
            if instruction.operation.name != "rz":
                return None
            if len(instruction.qubits) != 1 or len(instruction.operation.params) != 1:
                return None
            value = instruction.operation.params[0]
            if isinstance(value, bool) or type(value) not in (int, float):
                return None
            try:
                angle = Fraction(value)
            except (ValueError, OverflowError, TypeError):
                return None
            if angle.numerator.bit_length() > 512 or angle.denominator.bit_length() > 512:
                return None
            index = circuit.find_bit(instruction.qubits[0]).index
            totals[index] += sign * angle
            if (
                totals[index].numerator.bit_length() > 1024
                or totals[index].denominator.bit_length() > 1024
            ):
                return None
    if all(delta == 0 for delta in totals):
        return "equivalent"
    # Rigorous exact inequality 2*pi > 6, with no pi evaluation.
    if any(0 < abs(delta) < 6 for delta in totals):
        return "not_equivalent"
    return None


def certify_clifford_tableau_difference(circuit1, circuit2):
    """Prove projective *inequality* via exact Clifford conjugation tableaux.

    The Pauli action of a Clifford unitary is faithful modulo global phase.
    Distinct exact tableaux therefore witness different quantum channels
    (and inequivalent unitaries). Equal tableaux are NOT strict unitary
    equality certificates; global phase is intentionally left unresolved.
    """
    if not _source_quantum_circuits(circuit1, circuit2):
        return None
    if any(
        instruction.operation.name not in _CLIFFORD_GATES
        for circuit in (circuit1, circuit2)
        for instruction in circuit.data
    ):
        return None
    from qiskit.quantum_info import Clifford

    # Fail closed if a Qiskit version cannot construct this exact tableau.
    try:
        a = Clifford(circuit1)
        b = Clifford(circuit2)
    except (ValueError, TypeError, NotImplementedError):
        return None
    return "not_equivalent" if a != b else None



def _source_rz_delta_vector(circuit1, circuit2):
    """Reconstruct exact binary-rational angle differences for certificate verification."""
    if not _source_quantum_circuits(circuit1, circuit2):
        return None
    # This witness proves *strict* equality when all RZ deltas cancel.
    # A Qiskit circuit can carry an explicit global phase with no gates;
    # omitting that state would manufacture a false positive.
    for circuit in (circuit1, circuit2):
        phase = circuit.global_phase
        if type(phase) not in (int, float) or phase != 0:
            return None
    totals = [Fraction(0) for _ in range(circuit1.num_qubits)]
    for sign, circuit in ((1, circuit1), (-1, circuit2)):
        for instruction in circuit.data:
            if instruction.operation.name != "rz":
                return None
            if len(instruction.qubits) != 1 or len(instruction.operation.params) != 1:
                return None
            angle = instruction.operation.params[0]
            if isinstance(angle, bool) or type(angle) not in (int, float):
                return None
            try:
                exact = Fraction(angle)
            except (ValueError, OverflowError, TypeError):
                return None
            if exact.numerator.bit_length() > 512 or exact.denominator.bit_length() > 512:
                return None
            bit = circuit.find_bit(instruction.qubits[0]).index
            totals[bit] += sign * exact
            if (totals[bit].numerator.bit_length() > 1024
                    or totals[bit].denominator.bit_length() > 1024):
                return None
    return totals


def make_source_witness_certificate(circuit1, circuit2):
    """Produce a portable small witness without exposing solver numerics as proof.

    Certificates are meaningful only with the original Qiskit inputs and
    should be checked with verify_source_witness_certificate before use.
    """
    deltas = _source_rz_delta_vector(circuit1, circuit2)
    if deltas is not None:
        if all(delta == 0 for delta in deltas):
            return {
                "schema": "quprs-source-certificate-v1",
                "kind": "rz-exact-cancellation",
                "status": "equivalent",
                "provenance": "qiskit-typed-binary-rational-parameters",
            }
        for bit, delta in enumerate(deltas):
            if 0 < abs(delta) < 6:
                return {
                    "schema": "quprs-source-certificate-v1",
                    "kind": "rz-basis-inequality",
                    "status": "not_equivalent",
                    "qubit": bit,
                    "numerator": str(delta.numerator),
                    "denominator": str(delta.denominator),
                    "provenance": "qiskit-typed-binary-rational-parameters",
                }
        return None
    if certify_clifford_tableau_difference(circuit1, circuit2) != "not_equivalent":
        return None
    from qiskit.quantum_info import Clifford
    a = Clifford(circuit1).tableau
    b = Clifford(circuit2).tableau
    for row in range(a.shape[0]):
        for col in range(a.shape[1]):
            if a[row, col] != b[row, col]:
                return {
                    "schema": "quprs-source-certificate-v1",
                    "kind": "clifford-tableau-inequality",
                    "status": "not_equivalent",
                    "row": row,
                    "column": col,
                    "left": int(a[row, col]),
                    "right": int(b[row, col]),
                    "provenance": "exact-qiskit-clifford-tableau",
                }
    return None


def verify_source_witness_certificate(circuit1, circuit2, certificate):
    """Verifier independent of Ganak, GPMC, threshold decisions, and Rust IR."""
    if not isinstance(certificate, dict):
        return False
    if certificate.get("schema") != "quprs-source-certificate-v1":
        return False
    kind, status = certificate.get("kind"), certificate.get("status")
    if kind in ("rz-exact-cancellation", "rz-basis-inequality"):
        deltas = _source_rz_delta_vector(circuit1, circuit2)
        if deltas is None:
            return False
        if kind == "rz-exact-cancellation":
            return status == "equivalent" and all(d == 0 for d in deltas)
        bit = certificate.get("qubit")
        if type(bit) is not int or bit < 0 or bit >= len(deltas):
            return False
        try:
            num, den = int(certificate["numerator"]), int(certificate["denominator"])
            claimed = Fraction(num, den)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return False
        return (status == "not_equivalent"
                and claimed == deltas[bit] and 0 < abs(claimed) < 6)
    if kind != "clifford-tableau-inequality" or status != "not_equivalent":
        return False
    if not _source_quantum_circuits(circuit1, circuit2):
        return False
    if any(i.operation.name not in _CLIFFORD_GATES
           for circuit in (circuit1, circuit2) for i in circuit.data):
        return False
    row, col = certificate.get("row"), certificate.get("column")
    if type(row) is not int or type(col) is not int:
        return False
    from qiskit.quantum_info import Clifford
    try:
        a, b = Clifford(circuit1).tableau, Clifford(circuit2).tableau
        if (row < 0 or row >= a.shape[0] or col < 0 or col >= a.shape[1]):
            return False
        return (int(a[row, col]) == certificate.get("left")
                and int(b[row, col]) == certificate.get("right")
                and a[row, col] != b[row, col])
    except (ValueError, TypeError, NotImplementedError):
        return False


def certify_source_witness(circuit1, circuit2):
    """Narrow solver-independent source witness; no positive WMC claims."""
    proof = certify_rz_basis_witness(circuit1, circuit2)
    if proof is not None:
        return proof
    return certify_clifford_tableau_difference(circuit1, circuit2)
