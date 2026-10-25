"""Adversarial controls on certificate promotion and exact provenance."""
import copy
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_contract import (
    Kind, SOURCE_HEAD, SOURCE_QASM_SHA256,
    inconclusive, numeric_observation, source_cnf_bundle, upper_bound)

def fixture():
    return [{
        "backend":b,"solver":s,"source_commit":head,
        "source_sha256":SOURCE_QASM_SHA256,"cnf_sha256":"a"*64,
        "native_binary_sha256_observation":"b"*64,
        "raw_recomputed_upper":"999999995/1000000000",
        "restricted_source_model_not_equivalent":True,
        "native_solver_arithmetic_certified":False,
        "general_compiler_soundness_certified":False,
        "replay":{
            "upper":"999999995/1000000000",
            "source_upper":"999999996/1000000000",
            **({"input_witnesses":["2","7"],
                "phase_roles":{"constant":2,"bit":3}}
               if b=="python"
               else {"boolean_witnesses":{
                   "input_variable":3,"unique_extensions":["1","7"],
                   "constant_phase_literal":1,
                   "input_bit_phase_literal":2,
                   "activation_verified":True}}),
            "independent_analytic_source_oracle":{
                "kind":"independent_source_analytic_negative",
                "backend":b,"solver":s,
                "source_sha256":SOURCE_QASM_SHA256,
                "cnf_sha256":"a"*64,
                "source_angle_radians":"1/5000",
                "analytic_cosine_lower":
                    str(1-Fraction(1,10000)**2/2),
                "analytic_cosine_upper":
                    str(1-Fraction(1,10000)**2/2+Fraction(1,10000)**4/24),
                "unique_witnesses":["2","7"] if b=="python" else ["1","7"],
                "constant_phase_literal":2 if b=="python" else 1,
                "bit_phase_literal":3 if b=="python" else 2,
                "source_semantics_conditional":True,
                "printed_weight_bound_claimed":False,
                "general_compiler_certified":False,
                "native_solver_certified":False,
            },
        },
    } for b,head in SOURCE_HEAD.items() for s in ("gpmc","ganak")]

class TrustContractTests(unittest.TestCase):
    def test_complete_scoped_certificate(self):
        bundle=source_cnf_bundle(fixture(),SOURCE_QASM_SHA256)
        self.assertEqual(len(bundle["records"]),4)
        self.assertFalse(bundle["metadata_self_authenticating"])
        self.assertTrue(bundle["raw_artifact_replay_required"])
        self.assertTrue(all(row["kind"]==Kind.SOURCE_MODEL_NEGATIVE.value
                            and not row["native_solver_arithmetic_certified"]
                            for row in bundle["records"]))

    def test_numerical_observation_cannot_become_proof(self):
        d=numeric_observation("rust","gpmc","0.999999995","1e-8")
        self.assertEqual(d["kind"],Kind.NUMERICAL_OBSERVATION.value)
        self.assertFalse(d["strict_equivalence_certified"])
        self.assertFalse(d["strict_non_equivalence_certified"])
        self.assertEqual(inconclusive("Interval upper includes one")["kind"],
                         Kind.INCONCLUSIVE.value)

    def test_strict_upper_must_be_exact_and_below_one(self):
        self.assertEqual(upper_bound("999999995/1000000000"),
                         Fraction(999999995,1000000000))
        for invalid in ("1","100/100","-1/2","1.0","0.999999995",
                        "2/1","1/0","0","nan","1"*300):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                upper_bound(invalid)

    def test_provenance_tampering_fails_closed(self):
        bad=[
            {"backend":"fake"},{"solver":"fake"},
            {"source_commit":"0"*40},{"source_sha256":"0"*64},
            {"cnf_sha256":"invalid"},{"native_binary_sha256_observation":""},
            {"raw_recomputed_upper":"1"},
            {"restricted_source_model_not_equivalent":False},
            {"native_solver_arithmetic_certified":True},
            {"general_compiler_soundness_certified":True},
            {"replay":{"upper":"1","source_upper":"1","boolean_witnesses":{}}},
            {"replay":{"upper":"999999995/1000000000",
                       "source_upper":"1","boolean_witnesses":{}}},
            {"replay":{"upper":"999999995/1000000000","source_upper":"1/2"}},
        ]
        for i,edit in enumerate(bad):
            with self.subTest(i=i),self.assertRaises(ValueError):
                v=fixture()
                v[0].update(edit)
                source_cnf_bundle(v,SOURCE_QASM_SHA256)

    def test_independent_oracle_is_required_and_bound_to_raw_replay(self):
        for key,value in (
            ("analytic_cosine_upper","1"),
            ("source_sha256","0"*64),
            ("source_angle_radians","1/1000"),
            ("unique_witnesses",["0","0"]),
            ("constant_phase_literal",3),
            ("printed_weight_bound_claimed",True),
            ("native_solver_certified",True),
            ("source_semantics_conditional",False),
        ):
            with self.subTest(key=key),self.assertRaises(ValueError):
                rows=fixture()
                rows[0]["replay"]["independent_analytic_source_oracle"][key]=value
                source_cnf_bundle(rows,SOURCE_QASM_SHA256)

    def test_independent_oracle_does_not_promote_native_solver(self):
        doc=source_cnf_bundle(fixture(),SOURCE_QASM_SHA256)
        for row in doc["records"]:
            self.assertTrue(row["independent_cnfs_boolean_shape_checked"])
            self.assertFalse(row["independent_source_oracle_printed_weight_bound"])
            self.assertFalse(row["native_solver_arithmetic_certified"])
            self.assertFalse(row["strict_positive_equivalence_certified"])
            self.assertLess(Fraction(row["independent_analytic_source_upper"]),1)

    def test_complete_unique_cross_backend_required(self):
        for rows in (fixture()[:3],fixture()+fixture()[:1]):
            with self.assertRaises(ValueError):
                source_cnf_bundle(rows,SOURCE_QASM_SHA256)
        rows=fixture()
        rows[3]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):
            source_cnf_bundle(rows,SOURCE_QASM_SHA256)
        with self.assertRaises(ValueError):
            source_cnf_bundle(fixture(),"0"*64)

if __name__=="__main__":
    unittest.main()
