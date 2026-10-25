"""Pure-stdlib independent source and CNF proof mutation controls."""
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from independent_source_oracle import SOURCE, independent_source_check

GPMC=b"""p cnf 3 3
c t wmc
c p weight 2 0.999999995 -0.0001 0
c p weight -2 1 0 0
c p weight 3 0.99999998 0.0002 0
c p weight -3 1 0 0
2 0
-3 1 0
-1 3 0
"""
GANAK=b"""p cnf 3 3
c t wmc
c p weight 2 0.999999995 - 0.0001i 0
c p weight -2 1 + 0i 0
c p weight 3 0.99999998 + 0.0002i 0
c p weight -3 1 + 0i 0
2 0
-3 1 0
-1 3 0
"""
RUST=b"""p cnf 3 3
c t wmc
c p weight 1 0.999999995 0.0001 0
c p weight 2 0.99999998 -0.0002 0
1 0
-2 3 0
-3 2 0
"""
PHASE=b"""weight_lit\tphase_numerator\tphase_denominator\tmonomial
1\t1\t10\t
2\t9\t10\t0
"""

class IndependentSourceOracleTests(unittest.TestCase):
    def test_rational_source_taylor_upper_is_strict(self):
        z=independent_source_check(SOURCE,GPMC,"python","gpmc")
        x=F(1,10000)
        self.assertEqual(F(z["analytic_cosine_upper"]),1-x*x/2+x**4/24)
        self.assertLess(F(z["analytic_cosine_upper"]),1)
        self.assertFalse(z["printed_weight_bound_claimed"])

    def test_two_real_weight_dialects(self):
        for name,data in (("gpmc",GPMC),("ganak",GANAK)):
            with self.subTest(solver=name):
                p=independent_source_check(SOURCE,data,"python",name)
                self.assertEqual(p["constant_phase_literal"],2)
                self.assertEqual(p["bit_phase_literal"],3)

    def test_rust_raw_tsv_phase_roles(self):
        p=independent_source_check(SOURCE,RUST,"rust","gpmc",PHASE)
        self.assertEqual((p["constant_phase_literal"],p["bit_phase_literal"]),(1,2))
        self.assertEqual(len(p["unique_witnesses"]),2)

    def test_fail_closed_source_and_cnf_mutations(self):
        problems=[
            (SOURCE.replace(b"0.0002",b"0.0000"),GPMC),
            (SOURCE,GPMC.replace(b"2 0\n",b"")),
            (SOURCE,GPMC.replace(b"-1 3 0\n",b"1 3 0\n")),
            (SOURCE,GPMC.replace(b"-3 1 0\n",b"")),
            (SOURCE,GPMC.replace(b"0.99999998",b"1")),
            (SOURCE,GPMC.replace(b"-2 1 0 0",b"-2 2 0 0")),
            (SOURCE,GPMC.replace(b"0.999999995",b"nan")),
            (SOURCE,GPMC.replace(b"p cnf 3 3",b"p cnf 13 3")),
        ]
        for src,cnf in problems:
            with self.subTest(cnf=cnf),self.assertRaises(ValueError):
                independent_source_check(src,cnf,"python","gpmc")

    def test_fail_closed_wrong_rust_fraction_and_role(self):
        for bad in (b"", PHASE.replace(b"\t0\n",b"\t2\n"),
                    PHASE.replace(b"2\t9\t10\t0",b"3\t9\t10\t0"),
                    PHASE.replace(b"1\t1\t10\t",b"1\t1\t0\t")):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                independent_source_check(SOURCE,RUST,"rust","gpmc",bad)

if __name__=="__main__":
    unittest.main()
