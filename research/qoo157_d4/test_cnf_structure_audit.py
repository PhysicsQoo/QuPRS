"""No-solver unit contracts for the SHA-verified source CNF structure audit."""
from __future__ import annotations
import unittest
from cnf_structure_audit import analyze


class SourceCnfAuditTests(unittest.TestCase):
    SIMPLE = (b"p cnf 4 3\n"
              b"c t wmc\n"
              b"c p weight 1 0.0 1.0 0\n"
              b"c p weight -1 1 0 0\n"
              b"c p weight 3 1 0 0\n"
              b"c p weight -3 1.0 0.0 0\n"
              b"1 2 0\n-2 3 0\n4 0\n")

    def test_components_and_weight_protection(self):
        got = analyze(self.SIMPLE)
        self.assertEqual(got["original_primal_graph_components"], [3, 1])
        self.assertEqual(got["weighted_variables"], 2)
        self.assertEqual(got["d4_string_protected_variables"], 2)
        self.assertEqual(got["numeric_asymmetric_weight_variables"], 1)
        self.assertEqual(got["binary_type_counts"], {"WU": 2})
        self.assertEqual(got["max_weighted_literals_per_clause"], 1)
        self.assertEqual(got["unmentioned_variables"], 0)

    def test_fail_closed_input_validation(self):
        invalid = [
            self.SIMPLE.replace(b"p cnf 4 3", b"p cnf 4 4"),
            self.SIMPLE.replace(b"c p weight -1 1 0 0\n", b""),
            self.SIMPLE.replace(b"1 2 0", b"1 5 0"),
            self.SIMPLE.replace(b"1 2 0", b"1 2 0 0"),
            self.SIMPLE.replace(b"c p weight 1 0.0 1.0 0",
                                b"c p weight 1 NaN 1.0 0"),
        ]
        for raw in invalid:
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                analyze(raw)

    def test_weighted_weighted_clause_is_not_hidden(self):
        got = analyze(self.SIMPLE.replace(b"-2 3 0", b"1 3 0"))
        self.assertEqual(got["binary_type_counts"], {"WU": 1, "WW": 1})
        self.assertEqual(got["max_weighted_literals_per_clause"], 2)


if __name__ == "__main__":
    unittest.main()
