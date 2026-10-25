"""Bounded one-qubit *source-QASM* diagonal-family weighted-CNF audit.

This is a research-only certificate for a tightly specified grammar, NOT
a general Python/Rust source-to-WMC or solver-arithmetic certificate.

The source mathematical gate semantics are independent of Qiskit's float
parameters. Existing QuPRS Python generates the actual CNF and phase
activation order; an exhaustive Boolean check establishes that every input
bit has exactly one satisfying extension and that each weighted literal
matches the verified monomial activation. The original source weights and
printed decimal weights are both conservatively enclosed.
"""
from fractions import Fraction
from math import isqrt
import re

from interval_wmc import ComplexInterval, Interval, WeightedCNF, serialize_complex, serialize_interval, unit_phase_rational_radians
from phase_coeff_reference import ideal_rational_pi_phase, outward_decimal_interval, union_printed_and_ideal
from import_dimacs import normalized_for_pathsum

_BEGIN = ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n')
_DECIMAL = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
_GATE = re.compile(r'(rz|u1)\(('+_DECIMAL+r')\) q\[0\];|'
                   r'(z|s|sdg|t|tdg) q\[0\];')
_MAX_GATES = 4
_MAX_VARIABLES = 12
_MAX_RADIANS = Fraction(1, 2)


def parse_diagonal_qasm(raw):
    """Parse only canonical one-qubit decimal RZ/P + exact diagonal gates.

    We deliberately reject QASM expressions, exponent notation, registers,
    comments, injected extra statements, and malformed constructs.
    """
    if not isinstance(raw, str) or len(raw) > 1024 or not raw.startswith(_BEGIN):
        raise ValueError("Unsupported or oversized canonical QASM header")
    lines = raw[len(_BEGIN):].splitlines()
    if not 1 <= len(lines) <= _MAX_GATES:
        raise ValueError("Supported QASM must contain 1..4 diagonal gates")
    operations = []
    for line in lines:
        m = _GATE.fullmatch(line)
        if m is None:
            raise ValueError("Unsupported QASM gate or angle expression")
        kind = m.group(1) or m.group(3)
        angle = Fraction(m.group(2)) if m.group(2) is not None else None
        if angle is not None and abs(angle) > _MAX_RADIANS:
            raise ValueError("Source radian angle exceeds the validated range")
        operations.append((kind, angle))
    return tuple(operations)


def source_phase_terms(operations):
    """Independent source diagonal-gate action as (radian, pi multiple).

    Each term represents the exponent of a phase weight e^{i(r + p*pi)}.
    The bit term multiplies the computational-basis input bit x_0.
    """
    constant_rad = Fraction(0)
    bit_rad = Fraction(0)
    bit_pi = Fraction(0)
    for kind, angle in operations:
        if kind == "rz":
            constant_rad -= angle / 2
            bit_rad += angle
        elif kind == "u1":
            bit_rad += angle
        elif kind == "z":
            bit_pi += 1
        elif kind == "s":
            bit_pi += Fraction(1, 2)
        elif kind == "sdg":
            bit_pi -= Fraction(1, 2)
        elif kind == "t":
            bit_pi += Fraction(1, 4)
        elif kind == "tdg":
            bit_pi -= Fraction(1, 4)
        else:
            raise ValueError("Unsupported independent source gate")
    if abs(constant_rad) > 1 or abs(bit_rad) > 1:
        raise ValueError("Source phase exceeds rational Taylor domain")
    return {"constant": (constant_rad, Fraction(0)),
            "bit": (bit_rad, bit_pi)}


def is_trivial_phase(term):
    radians, pi_coeff = term
    # Radian input is symbolic exact decimal, not a rational multiple of pi
    # unless it vanishes; nonzero radians cannot be cancelled by pi rational.
    return radians == 0 and (pi_coeff % 2) == 0


def source_unit_complex(term):
    """Rigorous rational enclosure for e^{i*(r + pi*p)}."""
    radians, pi_coeff = term
    radians_ref = unit_phase_rational_radians(radians)
    phase = (pi_coeff / 2) % 1
    rational_pi_ref = ideal_rational_pi_phase(phase.numerator, phase.denominator)
    value = radians_ref * rational_pi_ref
    return ComplexInterval(outward_decimal_interval(value.real, digits=50),
                           outward_decimal_interval(value.imag, digits=50))


def boolean_truth_table(logical, bit_symbol):
    """Use exact SymPy Boolean substitution; refuse unknown other symbols."""
    import sympy as sp
    logical = sp.sympify(logical)
    free = logical.free_symbols
    x = sp.Symbol(bit_symbol)
    if free - {x}:
        raise ValueError("Unexpected non-input variable in gate phase monomial")
    result = []
    for bit in (0, 1):
        value = sp.simplify(logical.subs(x, sp.true if bit else sp.false))
        if value == sp.true:
            result.append(True)
        elif value == sp.false:
            result.append(False)
        else:
            raise ValueError("Phase monomial does not reduce to a Boolean")
    return tuple(result)


def phase_kind(truth):
    if truth == (True, True):
        return "constant"
    if truth == (False, True):
        return "bit"
    raise ValueError("Only constant and positive input-bit phases are supported")


def prove_boolean_encoding(cnf, phase_lits):
    """Exhaustively verify bit-to-weighted-literal CNF consistency.

    Conditions:
      * variable 1 is the input bit;
      * for x=0,1 exactly one satisfying auxiliary-variable extension exists;
      * in that unique extension each weighted literal z equals its monomial
        source bit activation;
      * all other literals have positive/negative weight 1.
    This checks actual printed CNF structure for the narrow diagonal model;
    it does not prove the arbitrary source-to-PathSum compiler.
    """
    if not isinstance(cnf, WeightedCNF) or len(cnf.weights) > _MAX_VARIABLES:
        raise ValueError("Unsupported CNF size for exhaustive proof")
    n = len(cnf.weights)
    if not n:
        raise ValueError("No input variable in CNF")
    for index, (positive, negative) in enumerate(cnf.weights, 1):
        if index in phase_lits:
            if negative != ComplexInterval.exact(1):
                raise ValueError("Nonunit negative phase literal")
        elif positive != ComplexInterval.exact(1) or negative != ComplexInterval.exact(1):
            raise ValueError("Unattributed or nonunit weighted literal")
    satisfiers = [[], []]
    for bits in range(1 << n):
        if all(any(bool(bits & (1 << (abs(lit)-1))) == (lit > 0)
                   for lit in clause) for clause in cnf.clauses):
            satisfiers[bool(bits & 1)].append(bits)
    if any(len(row) != 1 for row in satisfiers):
        raise ValueError("CNF does not encode one unique satisfying extension per bit")
    for bit, row in enumerate(satisfiers):
        assignment = row[0]
        for index, kind in phase_lits.items():
            expected = kind == "constant" or bool(bit)
            observed = bool(assignment & (1 << (index-1)))
            if expected != observed:
                raise ValueError("Weighted literal is not activated by its source monomial")
    return {"input_bit_zero_unique_extension": True,
            "input_bit_one_unique_extension": True,
            "weighted_literal_activation_verified": True,
            "satisfying_assignments": [str(x[0]) for x in satisfiers]}


def audit_diagonal_source_to_emitted_cnf(source_qasm, ps, emitted_cnf, *,
                                        p_to_wlogi):
    """Fail-closed source-to-actual-CNF audit and interval non-equivalence.

    Preconditions for a certified source model: accepted exact source grammar,
    fixed 1-qubit identity-input trace setup, unchanged output map, no path
    variables, exact activation mapping for each phase and unique Boolean
    auxiliary witness for both possible input bits. Neither native solver
    floating arithmetic nor arbitrary gate compiler correctness is covered.
    """
    gates = parse_diagonal_qasm(source_qasm)
    model = source_phase_terms(gates)
    if ps.num_qubits != 1 or ps.num_pathvar != 0 or len(ps.bits) != 1:
        raise ValueError("Expected one-qubit diagonal pathsum without path vars")
    import sympy as sp
    bit = ps.bits[0]
    if sp.sympify(ps.f[0]) != sp.Symbol(bit):
        raise ValueError("Output map is not the single preserved input bit")
    symbolic = list(p_to_wlogi(ps.P))
    phase_lits = {}
    for i, (_, logi) in enumerate(symbolic):
        kind = phase_kind(boolean_truth_table(logi, bit))
        if kind in phase_lits.values():
            raise ValueError("Repeated source phase monomial")
        phase_lits[i + 2] = kind
    if any(not is_trivial_phase(term) and kind not in phase_lits.values()
           for kind, term in model.items()):
        raise ValueError("Represented phase term is missing from generated PathSum")
    boolean_proof = prove_boolean_encoding(emitted_cnf, phase_lits)
    exact_weights = []
    widened_weights = []
    audit_rows = []
    for index, (printed_positive, negative) in enumerate(emitted_cnf.weights, 1):
        if index in phase_lits:
            kind = phase_lits[index]
            ideal = source_unit_complex(model[kind])
            source_radians, source_pi_multiple = model[kind]
            original_vs_printed = union_printed_and_ideal(ideal, printed_positive)
            exact_weights.append((ideal, negative))
            widened_weights.append((original_vs_printed, negative))
            audit_rows.append({
                "positive_literal": index, "monomial": kind,
                "source_radians": str(source_radians),
                "source_pi_multiplier": str(source_pi_multiple),
                "exact_source_weight_interval": serialize_complex(ideal),
                "actual_emitted_decimal_weight": serialize_complex(printed_positive),
                "source_printed_hull": serialize_complex(original_vs_printed),
            })
        else:
            exact_weights.append((printed_positive, negative))
            widened_weights.append((printed_positive, negative))
    source_count = WeightedCNF(emitted_cnf.clauses, tuple(exact_weights)).count()
    inclusive_count = WeightedCNF(emitted_cnf.clauses, tuple(widened_weights)).count()
    src_magnitude = normalized_for_pathsum(source_count, num_qubits=1, num_pathvar=0)
    hull_magnitude = normalized_for_pathsum(inclusive_count, num_qubits=1, num_pathvar=0)
    return {
        "scope": "1-qubit canonical 1-4 gate diagonal family, WMC-only, exact source decimal radians",
        "source_operations": [
            {"name": kind, "exact_radians": str(angle) if angle is not None else None}
            for kind, angle in gates
        ],
        "normalization": "2^(n+p/2), n=1, p=0",
        "proof_assumptions": (
            "Independently audited diagonal gate phase formulas and fixed "
            "Python PathSum/encoder implementations; CNF Boolean activation "
            "exhaustively verified; solver count is not interval certified."
        ),
        "source_boolean_encoding_proof": boolean_proof,
        "weight_source_provenance": audit_rows,
        "exact_source_count": serialize_complex(source_count),
        "exact_source_normalized_magnitude": serialize_interval(src_magnitude),
        "inclusive_source_printed_count": serialize_complex(inclusive_count),
        "inclusive_source_printed_normalized_magnitude": serialize_interval(hull_magnitude),
        "source_non_equivalent_up_to_global_phase_proved": src_magnitude.upper < 1,
        "source_printed_hull_strictly_below_one": hull_magnitude.upper < 1,
        "native_solver_internal_rounding_certified": False,
        "general_qasm_compiler_certified": False,
        "formal_source_wmc_non_equivalence_supported": hull_magnitude.upper < 1,
    }
