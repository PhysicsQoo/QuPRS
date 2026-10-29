"""Independent exact CNF arithmetic oracle is intentionally solver-free."""
from fractions import Fraction
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exact_gpmc_cnf_oracle import (
    count_printed_cnf_exact, exact_count_distance_classification,
)


def _cnf(n, clauses, weights=""):
    return f"p cnf {n} {len(clauses)}\nc t wmc\n{weights}\n" + "\n".join(clauses) + "\n"


def test_exact_complex_weighted_count():
    cnf = _cnf(1, ["1 0"], "c p weight 1 0.6 0.8 0\nc p weight -1 1.0 0.0 0")
    r = count_printed_cnf_exact(cnf)
    assert r["status"] == "observed"
    assert (r["real"], r["imag"]) == (Fraction(3, 5), Fraction(4, 5))
    assert r["satisfying_assignments"] == 1


def test_exact_count_includes_unweighted_tseitin_variables():
    # 3 satisfying assignments: 10,01,11 -> 0.5 + 0.5 + 0.25 = 1.25.
    cnf = _cnf(
        2, ["1 2 0"],
        "c p weight 1 0.5 0.0 0\nc p weight -1 1 0 0\n"
        "c p weight 2 0.5 0 0\nc p weight -2 1 0 0",
    )
    result = count_printed_cnf_exact(cnf)
    assert result["real"] == Fraction(5, 4)
    assert result["imag"] == 0
    assert result["satisfying_assignments"] == 3


def test_unsatisfiable_and_empty_clauses():
    r=count_printed_cnf_exact(_cnf(1, ["1 0", "-1 0"]))
    assert r["real"] == r["imag"] == 0
    r=count_printed_cnf_exact(_cnf(1, []))
    assert r["real"] == 2 and r["imag"] == 0


def test_independent_exact_weighted_sum_distance_threshold():
    below=Fraction("0.999999999999950651977994553604")
    assert exact_count_distance_classification(below, 0, 0, 1e-8) == "not_equivalent"
    assert exact_count_distance_classification(Fraction(1), 0, 0, 1e-8) == "inside_threshold"
    assert exact_count_distance_classification(Fraction(11, 10), 0, 0, 1e-8) == "unknown_overshoot"


@pytest.mark.parametrize("cnf", [
    _cnf(1, ["1 0"], "c p weight 1 nan 0 0"),
    _cnf(1, ["1 0"], "c p weight 1 1/2 0 0"),
    _cnf(1, ["1 0"], "c p weight 1 1 0 0\nc p weight 1 1 0 0"),
    _cnf(1, ["2 0"]),
    "p cnf 1 0\nc t wmc\nc p gweight 2 0\n",
    "p cnf 2 1\nc t wmc\n",
])
def test_rejects_unsupported_or_malformed_source(cnf):
    with pytest.raises(ValueError):
        count_printed_cnf_exact(cnf)


def test_limit_is_explicit_not_proof():
    value=count_printed_cnf_exact("p cnf 13 0\nc t wmc\n", max_variables=12)
    assert value["status"] == "skipped"
    assert value["reason"] == "variable_limit"
