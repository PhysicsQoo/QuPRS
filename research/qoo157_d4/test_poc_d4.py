"""No-native-binary regression tests for the independent d4 PoC oracle."""
from argparse import Namespace
from fractions import Fraction
from pathlib import Path
import json
import tempfile
import unittest

from poc_d4 import FIXTURES, oracle_count, parse_cnf, parse_d4_count, run


class D4ExactOracleTests(unittest.TestCase):
    def test_hand_computable_weighted_counts(self):
        expected = {
            "unsat": (0, 0),
            "zero_weight": (0, 0),
            "free_variable": (1, 1),
            "negative_complex": (-3, Fraction(1, 2)),
            "cancellation": (0, 0),
            "global_phase": (-1, 0),
            "nondyadic_decimal": (Fraction(1, 10), Fraction(1, 5)),
            "both_polarities": (1, 0),
            "unweighted_free": (8, 0),
        }
        self.assertEqual(set(expected), set(FIXTURES))
        for name, result in expected.items():
            with self.subTest(name=name):
                self.assertEqual(oracle_count(FIXTURES[name]), result)

    def test_reject_duplicate_weights_and_unknown_projection(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_cnf(
                "p cnf 1 0\nc p weight 1 1 0 0\nc p weight 1 2 0 0\n"
            )
        with self.assertRaisesRegex(ValueError, "projected"):
            parse_cnf("p cnf 1 0\nc p show 1 0\n")

    def test_reject_inconsistent_header(self):
        for text in (
            "p cnf 1 2\n1 0\n",
            "p cnf 1 1\n2 0\n",
            "p cnf 1 1\n0 1\n",
            "p cnf 17 0\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_cnf(text)

    def test_d4_complex_stdout_parsing(self):
        self.assertEqual(
            parse_d4_count("s SATISFIABLE\nc s exact arb float 1.5e0-2.5e-2i\n"),
            (Fraction(3, 2), Fraction(-1, 40)),
        )
        self.assertEqual(
            parse_d4_count("c s exact arb float 0.0000 + 0.0000i\n"),
            (0, 0),
        )
        self.assertEqual(
            parse_d4_count("s UNSATISFIABLE\nc s exact arb int 0\n"), (0, 0)
        )
        self.assertEqual(
            parse_d4_count("c s exact arb int 8\n"), (8, 0)
        )
        self.assertEqual(
            parse_d4_count("c s exact arb float 1.25e-01\n"),
            (Fraction(1, 8), 0),
        )
        with self.assertRaisesRegex(ValueError, "conflicting"):
            parse_d4_count("c s exact arb int 1\nc s exact arb float 2+0i\n")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            parse_d4_count(
                "c s exact arb float 1+0i\nc s exact arb float 2+0i\n"
            )
        with self.assertRaisesRegex(ValueError, "lacks"):
            parse_d4_count("c s exact arb cpx 1 + 0i\n")

    def test_oracle_only_mode_preserves_fixtures_and_evidence(self):
        with tempfile.TemporaryDirectory(prefix="qoo157-d4-") as temp:
            workdir = Path(temp)
            run(Namespace(workdir=workdir, binary=None, cnf=[], timeout=5))
            report = json.loads((workdir / "report.json").read_text())
            self.assertEqual(len(report["cases"]), len(FIXTURES))
            self.assertTrue(all(c["native_status"] == "NOT_RUN" for c in report["cases"]))
            self.assertTrue(all(len(c["cnf_sha256"]) == 64 for c in report["cases"]))
            self.assertIsNone(report["upstream_binary_sha256"])


if __name__ == "__main__":
    unittest.main()
