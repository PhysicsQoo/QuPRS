"""Strict QASM source-radian versus Rust represented-coefficient reference."""
from fractions import Fraction as F
import unittest

from import_dimacs import parse_emitted_dimacs
from interval_wmc import WeightedCNF
from qasm_rz_source_reference import (
    audit_single_rz_bra_source, parse_single_positive_rz_radians,
    prove_single_rz_boolean_activation,
)

SOURCE = ('OPENQASM 2.0;\ninclude "qelib1.inc";\n'
          'qreg q[1];\nrz(0.001) q[0];\n')
# Source-pinned Rust-generated fixture reproduced from the opt-in exporter:
EMITTED = """p cnf 3 5
c t wmc
c p weight 2 9.9999950000002225e-1 -9.9999985274949114e-4 0
c p weight -2 1.0 0.0 0
c p weight 1 9.9999987499999776e-1 4.9999998887467181e-4 0
c p weight -1 1.0 0.0 0
1 0
-2 3 0
-3 2 0
-3 3 0
3 -3 0
"""
PHASES = {1: (27, 339292, ""), 2: (169619, 169646, "0")}


class QasmRzSourceTests(unittest.TestCase):
    def test_exact_qasm_literal(self):
        self.assertEqual(parse_single_positive_rz_radians(SOURCE), F(1, 1000))

    def test_original_decimal_radian_remains_inequivalent(self):
        cnf = parse_emitted_dimacs(EMITTED, solver="gpmc")
        result = audit_single_rz_bra_source(
            SOURCE, cnf, PHASES, num_qubits=1, num_pathvar=0
        )
        self.assertTrue(result["source_reference_strictly_below_one"])
        self.assertTrue(result["source_boolean_encoding_proof"]["weighted_literal_activation_verified"])
        self.assertTrue(result["source_represented_printed_hull_strictly_below_one"])
        self.assertEqual({r["monomial"] for r in result["phase_provenance"]}, {"", "0"})
        self.assertTrue(all(
            F(r["represented_minus_source_coeff_abs_upper_pi_units"]) > 0
            for r in result["phase_provenance"]
        ))
        self.assertFalse(result["native_solver_interval_certified"])
        self.assertFalse(result["full_qasm_parser_semantics_certified"])

    def test_tiny_source_radians_remain_nonzero_exact_fraction(self):
        tiny = SOURCE.replace("0.001", "0.0002")
        self.assertEqual(parse_single_positive_rz_radians(tiny), F(1, 5000))

    def test_rust_boolean_activation_proved_and_mutations_fail_closed(self):
        original = parse_emitted_dimacs(EMITTED, solver="gpmc")
        mapping = {"": (1, F(27, 339292)), "0": (2, F(169619, 169646))}
        verified = prove_single_rz_boolean_activation(original, mapping)
        self.assertEqual(verified["input_variable"], 3)
        self.assertTrue(verified["weighted_literal_activation_verified"])
        self.assertEqual(len(verified["unique_extensions"]), 2)
        cases = (
            WeightedCNF((), original.weights),  # lost source constraints
            WeightedCNF(tuple(c for c in original.clauses if c != (-2, 3)),
                        original.weights),  # broken bit -> phase binding
            WeightedCNF(original.clauses, original.weights + (original.weights[2],)),
        )
        for changed in cases:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                prove_single_rz_boolean_activation(changed, mapping)

    def test_unsupported_qasm_rejected(self):
        for value in (
            "rz(0.001) q[0];",
            SOURCE.replace("0.001", "0.001+0"),
            SOURCE.replace("0.001", "pi/4"),
            SOURCE.replace("0.001", "0"),
            SOURCE.replace("0.001", "-0.001"),
            SOURCE + "x q[0];\n",
            SOURCE.replace("qreg q[1]", "qreg q[2]"),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_single_positive_rz_radians(value)

    def test_missing_or_mismatched_rust_phase_metadata_fails_closed(self):
        cnf = parse_emitted_dimacs(EMITTED, solver="gpmc")
        for phase_map in (
            {},
            {1: PHASES[1]},
            {1: PHASES[1], 2: (169619, 169646, "")},
            {1: PHASES[1], 3: PHASES[2]},
        ):
            with self.subTest(phase_map=phase_map), self.assertRaises(ValueError):
                audit_single_rz_bra_source(
                    SOURCE, cnf, phase_map, num_qubits=1, num_pathvar=0
                )

    def test_unsupported_normalization_fails_closed(self):
        cnf = parse_emitted_dimacs(EMITTED, solver="gpmc")
        with self.assertRaises(ValueError):
            audit_single_rz_bra_source(
                SOURCE, cnf, PHASES, num_qubits=1, num_pathvar=1
            )


if __name__ == "__main__":
    unittest.main()
