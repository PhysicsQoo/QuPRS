"""Fail-closed source-angle and Boolean-activation proof controls."""
from fractions import Fraction as F
import unittest

from interval_wmc import ComplexInterval, WeightedCNF, normalized_magnitude
from python_diagonal_source_certificate import (
    audit_diagonal_source_to_emitted_cnf,
    boolean_truth_table, parse_diagonal_qasm, phase_kind,
    prove_boolean_encoding, source_phase_terms, source_unit_complex,
)

def fixture(*lines):
    return ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
            + ''.join(f"{line} q[0];\n" for line in lines))


class PythonSourceCertificateTests(unittest.TestCase):
    def test_exact_decimal_source_preserved(self):
        gates=parse_diagonal_qasm(fixture("rz(0.001)","u1(0.0004)","t"))
        self.assertEqual(gates[0],("rz",F(1,1000)))
        self.assertEqual(gates[1],("u1",F(1,2500)))
        self.assertEqual(source_phase_terms(gates)["constant"],(F(-1,2000),F(0)))
        self.assertEqual(source_phase_terms(gates)["bit"],(F(7,5000),F(1,4)))

    def test_rz_below_numerical_tolerance_has_independent_source_bound(self):
        # RZ(0.0002) is outside exact-equivalence despite falling within a
        # 1e-8 normalized-magnitude heuristic. Keep this independent of floats.
        source = fixture("rz(0.0002)")
        gates = parse_diagonal_qasm(source)
        self.assertEqual(gates, (("rz", F(1, 5000)),))
        terms = source_phase_terms(gates)
        self.assertEqual(terms["constant"], (F(-1, 10000), F(0)))
        self.assertEqual(terms["bit"], (F(1, 5000), F(0)))
        phase0 = source_unit_complex(terms["constant"])
        phase1 = phase0 * source_unit_complex(terms["bit"])
        bound = normalized_magnitude(phase0 + phase1, 2)
        self.assertGreater(bound.lower, F(99999999, 100000000))
        self.assertLess(bound.upper, F(1))
        # The analytic numerical acceptance does not contradict a strict bound.
        self.assertGreater(bound.lower, F(1) - F(1, 100000000))

    def test_negative_exact_decimal_radians(self):
        gates=parse_diagonal_qasm(fixture("rz(-0.001)","rz(0.001)"))
        terms=source_phase_terms(gates)
        self.assertEqual(terms["constant"],(F(0),F(0)))
        self.assertEqual(terms["bit"],(F(0),F(0)))

    def test_rational_pi_clifford_phase(self):
        z=source_unit_complex((F(0),F(1)))
        self.assertLessEqual(z.real.lower,-1)
        self.assertGreaterEqual(z.real.upper,-1)
        self.assertLessEqual(z.imag.lower,0)
        self.assertGreaterEqual(z.imag.upper,0)

    def test_source_relative_phase_defect(self):
        # One source RZ(0.001): the normalised one-qubit trace is cos(0.0005).
        c=source_unit_complex((F(-1,2000),F(0)))
        x=source_unit_complex((F(1,1000),F(0)))
        relative=c*x
        self.assertGreater(relative.real.lower,F(0))
        self.assertLess(relative.imag.upper,F(1,100))
        self.assertGreater(relative.imag.lower,F(0))

    def test_reject_untrusted_qasm(self):
        invalid=(
            "rz(0.001) q[0];",
            fixture("rz(pi/4)"),
            fixture("rz(1e-12)"),
            fixture("p(0.001)"),
            fixture("rz(0.001)")+"x q[0];\n",
            fixture("h"),
            fixture("rz(0.001)")+"// add this\n",
            fixture("rz(0.001)").replace("qreg q[1]","qreg q[2]"),
            fixture("rz(0.9)"),
            fixture("rz(0.001)","rz(0.001)","rz(0.001)","rz(0.001)","rz(0.001)"),
        )
        for src in invalid:
            with self.subTest(src=src),self.assertRaises(ValueError):
                parse_diagonal_qasm(src)

    def test_bit_truth_tables(self):
        import sympy as sp
        x=sp.Symbol("q_0")
        self.assertEqual(phase_kind(boolean_truth_table(sp.true,"q_0")),"constant")
        self.assertEqual(phase_kind(boolean_truth_table(x,"q_0")),"bit")
        with self.assertRaises(ValueError):
            phase_kind(boolean_truth_table(sp.Not(x),"q_0"))
        with self.assertRaises(ValueError):
            boolean_truth_table(sp.Symbol("unexpected"),"q_0")

    def test_actual_weighted_cnf_activation_unique(self):
        # 1=input, 2=bit, 3=constant (two Boolean equivalences).
        cnf=WeightedCNF(
            ((3,),(-2,1),(2,-1)),
            ((ComplexInterval.exact(1),ComplexInterval.exact(1)),
             (ComplexInterval.exact(F(3,4)),ComplexInterval.exact(1)),
             (ComplexInterval.exact(F(1,2)),ComplexInterval.exact(1))),
        )
        proven=prove_boolean_encoding(cnf,{2:"bit",3:"constant"})
        self.assertTrue(proven["weighted_literal_activation_verified"])
        self.assertEqual(proven["satisfying_assignments"],["4","7"])

        for changed in (
            WeightedCNF(cnf.clauses,cnf.weights+((
                ComplexInterval.exact(1),ComplexInterval.exact(1)),)),
            WeightedCNF(((3,),),cnf.weights),
            WeightedCNF(((3,),(-2,-1),(2,1)),cnf.weights),
            WeightedCNF(((3,),(-2,1),(2,-1)),(
                cnf.weights[0],(cnf.weights[1][0],ComplexInterval.exact(2)),
                cnf.weights[2])),
        ):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                prove_boolean_encoding(changed,{2:"bit",3:"constant"})

    def test_unattributed_weight_refused(self):
        cnf=WeightedCNF(((1,),),((ComplexInterval.exact(2),
                                 ComplexInterval.exact(1)),))
        with self.assertRaises(ValueError):
            prove_boolean_encoding(cnf,{})


if __name__=="__main__":
    unittest.main()
