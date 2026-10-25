"""Reject altered CNF witnesses, weights, phase data and archived evidence."""
from fractions import Fraction as F
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from replay_small_rz_evidence import sha, replay_python, parse_rust_phases, verify_manifest
from interval_wmc import ComplexInterval, WeightedCNF


class ReplayControls(unittest.TestCase):
    def make_cnf(self):
        u = ComplexInterval.exact(1)
        d = F(1,5000)
        c = ComplexInterval.exact(F(str(math.cos(float(d/2)))),
                                  F(str(-math.sin(float(d/2)))))
        b = ComplexInterval.exact(F(str(math.cos(float(d)))),
                                  F(str(math.sin(float(d)))))
        return WeightedCNF(((2,),(-3,1),(-1,3)),((u,u),(c,u),(b,u)))

    def test_rational_replay_is_negative(self):
        proof = replay_python(self.make_cnf())
        self.assertLess(F(proof["upper"]),1)
        self.assertEqual(proof["phase_roles"],{"constant":2,"bit":3})

    def test_mutilated_input_is_rejected(self):
        c = self.make_cnf()
        u = ComplexInterval.exact(1)
        mutants = [
            WeightedCNF(((2,),),c.weights),
            WeightedCNF(((2,),(-3,1)),c.weights),
            WeightedCNF(c.clauses,((ComplexInterval.exact(2),u),c.weights[1],c.weights[2])),
            WeightedCNF(c.clauses,(c.weights[0],
                                   (c.weights[1][0],ComplexInterval.exact(2)),
                                   c.weights[2])),
            WeightedCNF(c.clauses,c.weights+((u,u),))
        ]
        for mutant in mutants:
            with self.subTest(clauses=mutant.clauses),self.assertRaises(ValueError):
                replay_python(mutant)

    def test_rust_metadata_injection(self):
        header=b"weight_lit\tphase_numerator\tphase_denominator\tmonomial\n"
        good=header+b"1\t1\t10\t\n2\t9\t10\t0\n"
        self.assertEqual({v[2] for v in parse_rust_phases(good).values()},{"","0"})
        for bad in [
            header,header+b"1\t1\t10\t\n",
            header+b"1\t1\t10\t\n1\t9\t10\t0\n",
            header+b"1\t1\t0\t\n2\t9\t10\t0\n",
            header+b"1\t1\t10\t0\n2\t9\t10\t0\n",
        ]:
            with self.assertRaises(ValueError):
                parse_rust_phases(bad)

    def test_artifact_manifest_mutations(self):
        with TemporaryDirectory() as root:
            d=Path(root)
            p=d/"source-sha.txt"
            p.write_text("known\n")
            m=d/"SHA256SUMS"
            m.write_text(sha(p.read_bytes())+"  ./source-sha.txt\n")
            verify_manifest(d)
            p.write_text("changed")
            with self.assertRaises(ValueError):
                verify_manifest(d)
            p.write_text("known\n")
            (d/"not-in-manifest").write_text("injected")
            with self.assertRaises(ValueError):
                verify_manifest(d)
            (d/"not-in-manifest").unlink()
            m.write_text(sha(p.read_bytes())+"  ./../source-sha.txt\n")
            with self.assertRaises(ValueError):
                verify_manifest(d)


if __name__=="__main__":
    unittest.main()
