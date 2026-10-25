"""Exact one-qubit RZ sequence oracle: source semantics only, stdlib only.

The theorem is conditional on interpreting decimal QASM parameters as exact
rational radians. Source equivalence up to global phase is characterized by
the difference of the two rational rotation-angle sums. This module does NOT
verify emitted CNFs, Rust PhasePolynomial, or native solver arithmetic.
"""
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re

HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
_GATE = re.compile(r'rz\(([+-]?[0-9]+(?:\.[0-9]+)?)\) q\[0\];')
_MAX_GATES = 4
_MAX_ANGLE = Fraction(1, 2)
_MAX_SUM = Fraction(1)
_DELTA = Fraction(1, 5000)

# The six independent examples include two equivalences (exact cancellation,
# identical paths) and four negative cases, one only 1e-9 rad from cancellation.
CASES = (
    ("positive_rotation", (), ("0.0002",), "NON_EQUIVALENT"),
    ("negative_rotation", (), ("-0.0002",), "NON_EQUIVALENT"),
    ("accumulated_rotation", (), ("0.0002", "0.0002"), "NON_EQUIVALENT"),
    ("exact_cancellation", (), ("0.0002", "-0.0002"), "EQUIVALENT"),
    ("identical_paths", ("0.0002",), ("0.0002",), "EQUIVALENT"),
    ("nearly_cancelled", (), ("0.0002", "-0.000199999"), "NON_EQUIVALENT"),
)


def require(predicate, message):
    if not predicate:
        raise ValueError(message)


def make_qasm(angles):
    """No Qiskit conversion: preserve literal textual angles exactly."""
    require(len(angles) <= _MAX_GATES, "Unsupported RZ gate count")
    return HEADER + "".join(f"rz({angle}) q[0];\n" for angle in angles)


def parse_qasm(raw):
    """Fail closed on extra gates, comments, expressions and noncanonical QASM."""
    require(isinstance(raw, str) and len(raw) <= 1024
            and raw.startswith(HEADER), "Unsupported canonical QASM")
    tail = raw[len(HEADER):]
    lines = tail.splitlines()
    require(len(lines) <= _MAX_GATES, "Too many RZ gates")
    parsed = []
    for line in lines:
        match = _GATE.fullmatch(line)
        require(match is not None, "Unsupported RZ source expression")
        angle = Fraction(match.group(1))
        require(abs(angle) <= _MAX_ANGLE, "RZ angle outside supported domain")
        parsed.append(angle)
    require(abs(sum(parsed, Fraction(0))) <= _MAX_SUM,
            "Cumulative source phase outside current bounded domain")
    return tuple(parsed)


def cosine_strict_upper(x):
    """Valid for 0 < x <= 1/2 by alternating cosine series.

    0 < 1 - x^2/2 <= cos(x) <= 1 - x^2/2 + x^4/24 < 1.
    All arithmetic here is exact rational, with no pi or float computation.
    """
    require(isinstance(x, Fraction) and 0 < x <= Fraction(1, 2),
            "Unsupported strict cosine-bounding argument")
    lower = 1 - x**2 / 2
    upper = lower + x**4 / 24
    require(0 < lower < upper < 1, "Cosine bound does not separate from one")
    return lower, upper


def compare_sources(left_raw, right_raw):
    left = parse_qasm(left_raw)
    right = parse_qasm(right_raw)
    left_angle = sum(left, Fraction(0))
    right_angle = sum(right, Fraction(0))
    delta = right_angle - left_angle

    # Rz(a)Rz(b)=Rz(a+b). U^dagger V=Rz(delta) exactly in the
    # stipulated ideal source semantics. Rz(delta) differs from identity
    # by global phase iff delta = 2*pi*k. A rational delta cannot equal
    # nonzero 2*pi*k (irrationality of pi), so delta==0 is iff.
    equivalent = delta == 0
    proof = {
        "schema": "pure-rz-exact-source-equivalence-v1",
        "scope": "canonical 1q 0-4 RZ gates, exact decimal rational radians",
        "left_qasm_sha256": sha256(left_raw.encode("ascii")).hexdigest(),
        "right_qasm_sha256": sha256(right_raw.encode("ascii")).hexdigest(),
        "left_radians_exact": [str(x) for x in left],
        "right_radians_exact": [str(x) for x in right],
        "left_angle_sum_exact": str(left_angle),
        "right_angle_sum_exact": str(right_angle),
        "relative_radians_exact": str(delta),
        "source_global_phase_verdict": "EQUIVALENT" if equivalent else "NON_EQUIVALENT",
        "global_phase_convention": "RZ(delta) relative phase eigenvalues",
        "exact_source_gate_semantics_assumed": True,
        "pi_irrationality_mathematical_lemma_assumed": True,
        "emitted_cnf_semantics_verified": False,
        "rust_phase_polynomial_verified": False,
        "native_solver_arithmetic_certified": False,
        "strict_equivalence_of_compiled_circuits_certified": False,
    }
    if equivalent:
        proof["source_identity_certificate"] = {
            "relative_angle_is_exactly_zero": True,
            "source_matrix_product_is_identity": True,
        }
    else:
        half = abs(delta) / 2
        # Cumulative phase differences are constrained to |delta| <= 2.
        # That yields half <=1. Positive bound is used only for |delta|<=1.
        require(half <= Fraction(1, 2),
                "Relative source angle outside strict bound domain")
        lower, upper = cosine_strict_upper(half)
        proof["source_negative_certificate"] = {
            "relative_angle_nonzero_rational": True,
            "trace_magnitude_lower_exact": str(lower),
            "trace_magnitude_upper_exact": str(upper),
            "upper_strictly_below_one": True,
        }
    return proof


def six_case_report():
    results = []
    for label, left, right, expected in CASES:
        report = compare_sources(make_qasm(left), make_qasm(right))
        require(report["source_global_phase_verdict"] == expected,
                "Unexpected exact source result for " + label)
        results.append({"name":label, "expected_source":expected,
                        "source_proof":report})
    return {
        "schema":"pure-rz-six-case-source-matrix-v1",
        "scientific_scope":"source_only_not_compiled_cnf",
        "case_count":len(results),
        "passed":len(results),
        "source_model_only":True,
        "printed_weight_cnf_proof_included":False,
        "results":results,
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report = six_case_report()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                           encoding="utf-8")
    for row in report["results"]:
        print("RZ_SOURCE_EXACT",row["name"],
              row["source_proof"]["source_global_phase_verdict"],
              "delta",row["source_proof"]["relative_radians_exact"])
    print("RZ_SOURCE_CASES",report["passed"],"/",report["case_count"])


if __name__ == "__main__":
    main()
