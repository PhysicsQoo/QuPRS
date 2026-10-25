"""Pure-RZ exact-decimal source theorem; never treat as CNF proof."""
import copy
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from rz_sequence_oracle import (
    CASES, HEADER, compare_sources, cosine_strict_upper, make_qasm,
    parse_qasm, six_case_report,
)


class RZSequenceSourceTheoremTests(unittest.TestCase):
    def test_six_scientific_cases(self):
        report=six_case_report()
        self.assertEqual(report["passed"],6)
        self.assertEqual(sum(row["expected_source"]=="EQUIVALENT"
                             for row in report["results"]),2)
        self.assertTrue(all(
            not row["source_proof"]["emitted_cnf_semantics_verified"]
            and not row["source_proof"]["strict_equivalence_of_compiled_circuits_certified"]
            for row in report["results"]))

    def test_opposite_sign_and_near_cancellation(self):
        table={row["name"]:row["source_proof"]
               for row in six_case_report()["results"]}
        self.assertEqual(table["negative_rotation"]["relative_radians_exact"],"-1/5000")
        self.assertEqual(table["accumulated_rotation"]["relative_radians_exact"],"1/2500")
        self.assertEqual(table["exact_cancellation"]["relative_radians_exact"],"0")
        self.assertEqual(table["nearly_cancelled"]["relative_radians_exact"],"1/1000000000")
        self.assertIn("source_identity_certificate",table["exact_cancellation"])
        self.assertNotIn("source_negative_certificate",table["exact_cancellation"])
        self.assertLess(F(table["nearly_cancelled"]["source_negative_certificate"]
                          ["trace_magnitude_upper_exact"]),1)

    def test_metaproperties_swap_and_identity(self):
        for _, left, right, expected in CASES:
            direct=compare_sources(make_qasm(left),make_qasm(right))
            inverse=compare_sources(make_qasm(right),make_qasm(left))
            self.assertEqual(inverse["source_global_phase_verdict"],expected)
            self.assertEqual(F(inverse["relative_radians_exact"]),
                             -F(direct["relative_radians_exact"]))
        empty=compare_sources(make_qasm(()),make_qasm(()))
        self.assertEqual(empty["source_global_phase_verdict"],"EQUIVALENT")

    def test_rz_sequence_angle_permutation_and_additivity(self):
        a=compare_sources(make_qasm(()),make_qasm(("0.0002","-0.000199999")))
        b=compare_sources(make_qasm(()),make_qasm(("-0.000199999","0.0002")))
        self.assertEqual(a["relative_radians_exact"], b["relative_radians_exact"])
        self.assertEqual(a["source_global_phase_verdict"],"NON_EQUIVALENT")
        cancel=compare_sources(make_qasm(("0.0002","-0.0002")),
                               make_qasm(("0.0",)))
        self.assertEqual(cancel["source_global_phase_verdict"],"EQUIVALENT")

    def test_cosine_small_bound_exact_rational(self):
        x=F(1,10**9*2)
        lo,hi=cosine_strict_upper(x)
        self.assertEqual(hi,1-x*x/2+x**4/24)
        self.assertTrue(0<lo<hi<1)
        with self.assertRaises(ValueError):
            cosine_strict_upper(F(0))
        with self.assertRaises(ValueError):
            cosine_strict_upper(F(1))

    def test_reject_qasm_injection_and_unsupported_expression(self):
        canonical=make_qasm(("0.0002",))
        for raw in (
            canonical+"x q[0];\n",
            canonical.replace("0.0002","pi/2"),
            canonical.replace("0.0002","2e-4"),
            canonical.replace("rz(","rx("),
            canonical.replace("qreg q[1]", "qreg q[2]"),
            canonical.replace("0.0002","1.3"),
            HEADER+"rz(0.0002) q[0];\n"*5,
            canonical+"//injected\n",
            canonical.replace("0.0002","nan"),
        ):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                parse_qasm(raw)

    def test_reject_phase_range_but_preserve_source_equivalence(self):
        with self.assertRaises(ValueError):
            compare_sources(make_qasm(()),make_qasm(("0.5","0.5","0.5")))
        with self.assertRaises(ValueError):
            parse_qasm(make_qasm(("0.8",)))
        valid=compare_sources(make_qasm(("0.0002","-0.0002")),make_qasm(()))
        self.assertEqual(valid["source_global_phase_verdict"],"EQUIVALENT")


if __name__=="__main__":
    unittest.main()
