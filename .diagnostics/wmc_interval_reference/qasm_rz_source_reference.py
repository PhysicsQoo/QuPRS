"""Bounded source-QASM decimal RZ proof against represented Rust phase terms.

Scope: exactly one positive rational-decimal RZ(δ) applied as Bra to the
one-qubit identity miter. The source literal is an exact rational number of
radians; this is not a general OpenQASM expression parser or native solver
rounding certificate. An unsupported or missing phase mapping fails closed.
"""
import re
from fractions import Fraction

from interval_wmc import (
    ComplexInterval, WeightedCNF, unit_phase_rational_radians,
    serialize_complex, serialize_interval,
)
from import_dimacs import normalized_for_pathsum
from phase_coeff_reference import pi_interval, union_printed_and_ideal

_RZ_SOURCE = re.compile(
    r'\AOPENQASM 2\.0;\s+include "qelib1\.inc";\s+qreg q\[1\];\s+'
    r'rz\(([0-9]+(?:\.[0-9]+)?)\) q\[0\];\s*\Z'
)


def parse_single_positive_rz_radians(qasm):
    if not isinstance(qasm, str) or len(qasm) > 4096:
        raise ValueError("Unsupported source size")
    match = _RZ_SOURCE.fullmatch(qasm)
    if not match or len(match.group(1)) > 60:
        raise ValueError("Only single 1-qubit positive decimal RZ source supported")
    radians = Fraction(match.group(1))
    if not 0 < radians <= 1:
        raise ValueError("Only nonzero exact rational radians in (0,1] supported")
    return radians


def _source_coefficient_interval(delta, monomial):
    """Bra-side exact QASM RZ coefficients, reduced modulo one.

    Rust implementation applies RZ as Bra when gates1=[], gates2=[RZ].
      constant phase:  +δ/(4π)
      x[0] phase:      -δ/(2π) modulo 1 = 1-δ/(2π)
    """
    pi = pi_interval()
    if monomial == "":
        return Fraction(delta, 4 * pi.upper), Fraction(delta, 4 * pi.lower)
    if monomial == "0":
        return (Fraction(1) - Fraction(delta, 2 * pi.lower),
                Fraction(1) - Fraction(delta, 2 * pi.upper))
    raise ValueError("Unrecognized RZ Bra phase polynomial monomial")



def prove_single_rz_boolean_activation(cnf, by_monomial):
    """Exhaustively bind the two source phase monomials to a 1-bit Rust CNF.

    Exactly two weighted variables (constant, x0) and one unweighted input
    variable are allowed. Each input bit must have ONE satisfying extension
    with the expected phase-weight activation. No solver output is trusted.
    """
    if not isinstance(cnf, WeightedCNF) or set(by_monomial) != {"", "0"}:
        raise ValueError("Unsupported single-RZ source/CNF phase binding")
    phase_literals = {monomial: entry[0] for monomial, entry in by_monomial.items()}
    if len(cnf.weights) != 3 or len(set(phase_literals.values())) != 2:
        raise ValueError("Single-RZ proof requires exactly 2 phase vars and 1 input bit")
    remaining = set(range(1, len(cnf.weights) + 1)) - set(phase_literals.values())
    if len(remaining) != 1:
        raise ValueError("Unique input bit CNF variable is missing")
    input_var = remaining.pop()
    witnesses = []
    for bit in (0, 1):
        solutions = []
        for assignment in range(1 << len(cnf.weights)):
            if bool(assignment & (1 << (input_var - 1))) != bool(bit):
                continue
            if all(
                any(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0)
                    for lit in clause)
                for clause in cnf.clauses
            ):
                solutions.append(assignment)
        if len(solutions) != 1:
            raise ValueError("Non-unique or missing input-bit CNF extension")
        assignment = solutions[0]
        if not (assignment & (1 << (phase_literals[""] - 1))):
            raise ValueError("Constant phase literal not active")
        if bool(assignment & (1 << (phase_literals["0"] - 1))) != bool(bit):
            raise ValueError("Input-dependent phase activation mismatch")
        witnesses.append(str(assignment))
    return {
        "input_variable": input_var,
        "unique_extensions": witnesses,
        "weighted_literal_activation_verified": True,
        "input_bit_zero_unique_extension": True,
        "input_bit_one_unique_extension": True,
    }

def audit_single_rz_bra_source(qasm, cnf, phase_map, *, num_qubits, num_pathvar):
    """Enclose source-angle, Rust represented-phase, and printed CNF weights.

    Source-only small-CNF reference is conditional on the checked 1-qubit
    RZ Bra phase mapping and exact CNF structural clauses. No claim of full
    QASM-to-Rust representation fidelity or native solver internal bounds.
    """
    delta = parse_single_positive_rz_radians(qasm)
    if num_qubits != 1 or num_pathvar != 0:
        raise ValueError("Unsupported RZ pathsum size")
    if not isinstance(cnf, WeightedCNF) or len(phase_map) != 2:
        raise ValueError("Single-RZ Bra reference requires exactly two phases")
    by_monomial = {}
    for lit, values in phase_map.items():
        numer, denom, monomial = values
        if monomial in by_monomial or monomial not in ("", "0"):
            raise ValueError("Unsupported or repeated RZ monomial")
        if not (1 <= lit <= len(cnf.weights) and 0 <= numer < denom):
            raise ValueError("Invalid phase-to-weight binding")
        by_monomial[monomial] = (lit, Fraction(numer, denom))
    if set(by_monomial) != {"", "0"}:
        raise ValueError("Missing expected constant or x[0] phase")

    exact_source = []
    inclusive = []
    source_records = []
    phase_to_source = {
        "": delta / 2,
        "0": -delta,
    }
    for index, (printed_positive, printed_negative) in enumerate(cnf.weights, 1):
        matched = [(monomial, represented) for monomial, (lit, represented)
                   in by_monomial.items() if lit == index]
        if matched:
            monomial, represented = matched[0]
            if printed_negative != ComplexInterval.exact(1):
                raise ValueError("Nonunit negative phase weight in RZ source CNF")
            source_weight = unit_phase_rational_radians(phase_to_source[monomial])
            from phase_coeff_reference import ideal_rational_pi_phase
            represented_weight = ideal_rational_pi_phase(
                represented.numerator, represented.denominator
            )
            source_coeff_low, source_coeff_high = _source_coefficient_interval(delta, monomial)
            source_coeff_error_upper = max(
                abs(represented - source_coeff_low),
                abs(represented - source_coeff_high)
            )
            extended = union_printed_and_ideal(
                union_printed_and_ideal(printed_positive, represented_weight),
                source_weight
            )
            exact_source.append((source_weight, printed_negative))
            inclusive.append((extended, printed_negative))
            source_records.append({
                "positive_literal": index,
                "monomial": monomial,
                "represented_rust_coefficient": str(represented),
                "source_decimal_radians": str(delta),
                "source_phase_coefficient_pi_units": {
                    "lower": str(source_coeff_low),
                    "upper": str(source_coeff_high),
                },
                "represented_minus_source_coeff_abs_upper_pi_units": str(
                    source_coeff_error_upper
                ),
                "exact_source_complex_weight_enclosure": serialize_complex(source_weight),
                "source_representation_printed_weight_hull": serialize_complex(extended),
            })
        else:
            if (printed_positive != ComplexInterval.exact(1)
                    or printed_negative != ComplexInterval.exact(1)):
                raise ValueError("Unattributed source-RZ weight")
            exact_source.append((printed_positive, printed_negative))
            inclusive.append((printed_positive, printed_negative))

    # Check the *actual* emitted clause structure, not just two phase tags.
    boolean_proof = prove_single_rz_boolean_activation(cnf, by_monomial)
    source_count = WeightedCNF(cnf.clauses, tuple(exact_source)).count()
    hull_count = WeightedCNF(cnf.clauses, tuple(inclusive)).count()
    source_norm = normalized_for_pathsum(
        source_count, num_qubits=num_qubits, num_pathvar=num_pathvar
    )
    hull_norm = normalized_for_pathsum(
        hull_count, num_qubits=num_qubits, num_pathvar=num_pathvar
    )
    return {
        "source_semantics": "positive literal decimal interpreted as exact rational radians",
        "scope": "one-qubit single RZ Bra WMC CNF, checked monomial mapping",
        "source_radians": str(delta),
        "source_boolean_encoding_proof": boolean_proof,
        "source_reference_count": serialize_complex(source_count),
        "source_reference_normalized_magnitude": serialize_interval(source_norm),
        "source_reference_strictly_below_one": source_norm.upper < 1,
        "source_represented_printed_hull_count": serialize_complex(hull_count),
        "source_represented_printed_hull_normalized_magnitude": serialize_interval(hull_norm),
        "source_represented_printed_hull_strictly_below_one": hull_norm.upper < 1,
        "phase_provenance": source_records,
        "native_solver_interval_certified": False,
        "full_qasm_parser_semantics_certified": False,
    }
