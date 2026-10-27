"""Fail-closed parsing and interval normalization tests, no native dependencies."""
from fractions import Fraction as F
import unittest

from import_dimacs import (
    decimal_token, normalized_for_pathsum, parse_emitted_dimacs,
    parse_weight, serialized_count_verdict,
)
from interval_wmc import ComplexInterval, Interval


def weighted_text(solver, clauses="", header="p cnf 2 0"):
    # Literal 1 receives (1/2 + 1/4 i) when set and unit when not.
    if solver == "gpmc":
        literal = "c p weight 1 0.5 0.25 0"
        opposite = "c p weight -1 1 0 0"
    else:
        literal = "c p weight 1 0.5 + 0.25i 0"
        opposite = "c p weight -1 1 + 0i 0"
    return "\n".join((header, "c t wmc", literal, opposite, clauses))


class PrintedDimacsReferenceTests(unittest.TestCase):
    def test_exact_decimal_tokens_without_float(self):
        self.assertEqual(decimal_token("1.25e-2"), F(1, 80))
        self.assertEqual(decimal_token("-0.5"), -F(1, 2))
        for token in ("nan", "inf", "1/2", "1e1000", "0.1j", "1" * 121):
            with self.subTest(token=token), self.assertRaises(ValueError):
                decimal_token(token)

    def test_gpmc_and_ganak_printed_weight_parity(self):
        for solver in ("gpmc", "ganak"):
            with self.subTest(solver=solver):
                reference = parse_emitted_dimacs(weighted_text(solver), solver=solver)
                self.assertEqual(reference.count(), ComplexInterval.exact(3, F(1, 2)))
                self.assertEqual(len(reference.weights), 2)
                self.assertEqual(reference.weights[1][0], ComplexInterval.exact(1))
                self.assertEqual(reference.weights[1][1], ComplexInterval.exact(1))

    def test_ganak_negative_imaginary_and_scientific_notation(self):
        z = parse_weight(("1e-3", "-", "2.5e-2i", "0"), "ganak")
        self.assertEqual(z, ComplexInterval.exact(F(1, 1000), -F(1, 40)))

    def test_or_clauses_and_negative_literals(self):
        text = "p cnf 2 2\nc t wmc\n1 2 0\n-1 -2 0"
        reference = parse_emitted_dimacs(text, solver="gpmc")
        self.assertEqual(reference.count(), ComplexInterval.exact(2))

    def test_zero_clause_is_unsatisfiable(self):
        text = "p cnf 1 1\nc t wmc\n0"
        reference = parse_emitted_dimacs(text, solver="ganak")
        self.assertEqual(reference.count(), ComplexInterval.exact(0))

    def test_exact_pathsum_normalization_with_even_and_odd_pathvars(self):
        z = ComplexInterval.exact(4)
        self.assertEqual(
            normalized_for_pathsum(z, num_qubits=1, num_pathvar=2),
            Interval.exact(1),
        )
        odd = normalized_for_pathsum(
            ComplexInterval.exact(F(3, 2)), num_qubits=1, num_pathvar=1
        )
        self.assertLess(odd.lower, F(3, 5))
        self.assertGreater(odd.upper, F(1, 2))
        self.assertLess(odd.upper - odd.lower, F(1, 10**30))

    def test_refusal_of_unsupported_or_ambiguous_dimacs(self):
        cases = (
            "p cnf 2 0\nc p weight 1 1 0 0",  # no weighted marker
            "p cnf 2 1\nc t wmc",  # missing clause
            "p cnf 2 0\nc t wmc\nc p weight 1 1 0 0\nc p weight 1 1 0 0",
            "p cnf 2 1\nc t wmc\n3 0",  # beyond declared range
            "p cnf 2 1\nc t wmc\n1 0 2 0",  # embedded zero
            "p cnf 13 0\nc t wmc",  # cost cap
            "p cnf 1 0\nc t wmc\nc p weight 1 inf 0 0",
            "p cnf 1 0\nc t wmc\nc p weight 1 1 0 0\nc p weight -1 1 0 0\ngarbage",
            "p cnf 1 0\nc t wmc\nc t wmc",
            "p cnf 1 0\nc t wmc\nc p weight 1 1 + -0.1i 0",
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                parse_emitted_dimacs(case, solver="gpmc" if "+ -0.1i" not in case else "ganak")

    def test_no_overstated_verdict(self):
        self.assertEqual(
            serialized_count_verdict(Interval.exact(F(9, 10))),
            "REFERENCE_MAGNITUDE_BELOW_ONE",
        )
        self.assertEqual(
            serialized_count_verdict(Interval.exact(1)),
            "PRINTED_WEIGHT_REFERENCE_EXACTLY_ONE",
        )
        self.assertEqual(
            serialized_count_verdict(Interval(F(9, 10), F(11, 10))),
            "REFERENCE_UNRESOLVED",
        )


if __name__ == "__main__":
    unittest.main()
