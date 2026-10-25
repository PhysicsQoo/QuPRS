"""Research-only typed contract. Metadata alone is NOT a mathematical proof.

Only the raw-CNF replay tool may emit bounded source-model negative evidence.
A user-adjustable WMC numerical verdict can never be promoted to strict proof.
"""
from enum import Enum
from fractions import Fraction
import re

class Kind(str, Enum):
    NUMERICAL_OBSERVATION = "observational_numeric"
    SOURCE_MODEL_NEGATIVE = "bounded_source_cnf_negative"
    INCONCLUSIVE = "inconclusive"

SOURCE_HEAD = {
    "python": "ed72156b860dbafe750bbc0fe2d2e537253609a1",
    "rust": "1adbb067793d2bdf6ae7ff24b7cac27a1655c609",
}
SOURCE_QASM_SHA256 = "fa2f30e8bb82e3558268696b355eb2a6af778217fc76685259de6267f3565281"
SOLVERS = ("gpmc", "ganak")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_RATIONAL = re.compile(r"[0-9]+(?:/[1-9][0-9]*)?\Z")

def check(condition, message):
    if not condition:
        raise ValueError(message)

def upper_bound(value):
    """Finite exact upper endpoint; no floats, decimals or equality to one."""
    check(isinstance(value, str) and len(value) <= 256
          and _RATIONAL.fullmatch(value) is not None,
          "Expected bounded exact nonnegative rational upper")
    bound = Fraction(value)
    check(0 < bound < 1, "No strict upper-bound separation from one")
    return bound

def numeric_observation(backend, solver, value, tolerance):
    check(backend in SOURCE_HEAD and solver in SOLVERS,
          "Unknown numerical solver provenance")
    check(isinstance(value,str) and isinstance(tolerance,str)
          and 0 < len(value) < 200 and 0 < len(tolerance) < 100,
          "Missing numerical result/tolerance observation")
    return {"kind": Kind.NUMERICAL_OBSERVATION.value,
            "status": "unverified_numeric", "backend":backend, "solver":solver,
            "observed_value":value, "user_tolerance":tolerance,
            "strict_equivalence_certified":False,
            "strict_non_equivalence_certified":False,
            "native_solver_arithmetic_certified":False}

def inconclusive(reason):
    check(isinstance(reason,str) and 0 < len(reason) <= 500,
          "Missing bounded reason for inconclusive")
    return {"kind":Kind.INCONCLUSIVE.value, "status":"inconclusive",
            "reason":reason, "strict_equivalence_certified":False,
            "strict_non_equivalence_certified":False}

def source_cnf_bundle(raw_replayed_records, expected_source_hash):
    """Metadata checks AFTER actual QASM/CNF/phase replay. Not self-attesting.

    The caller must have independently recomputed raw Boolean witnesses,
    literal weights and conservative interval bounds from sealed artifacts.
    Manually written JSON with identical fields has no evidentiary standing.
    """
    check(isinstance(raw_replayed_records,list) and len(raw_replayed_records)==4,
          "Four independent backend/solver raw replays required")
    check(expected_source_hash == SOURCE_QASM_SHA256,
          "Unsupported or altered exact source QASM")
    seen = set()
    output = []
    for record in raw_replayed_records:
        check(isinstance(record,dict),"Malformed raw replay evidence")
        backend, solver = record.get("backend"),record.get("solver")
        check(backend in SOURCE_HEAD and solver in SOLVERS,
              "Unsupported backend or solver")
        check((backend,solver) not in seen,"Repeated backend/solver evidence")
        seen.add((backend,solver))
        check(record.get("source_commit")==SOURCE_HEAD[backend],
              "Source HEAD mismatch")
        check(record.get("source_sha256")==expected_source_hash,
              "Source QASM hash mismatch")
        for key in ("cnf_sha256","native_binary_sha256_observation"):
            v=record.get(key)
            check(isinstance(v,str) and _SHA256.fullmatch(v) is not None,
                  "Missing sha256 evidence: "+key)
        check(record.get("restricted_source_model_not_equivalent") is True,
              "Raw replay did not establish source-model inequivalence")
        check(record.get("native_solver_arithmetic_certified") is False
              and record.get("general_compiler_soundness_certified") is False,
              "Unsupported broader scientific proof claim")
        bound=record.get("raw_recomputed_upper")
        upper_bound(bound)
        replay=record.get("replay")
        check(isinstance(replay,dict) and replay.get("upper")==bound,
              "Replay upper and certificate upper mismatch")
        upper_bound(replay.get("source_upper"))
        if backend == "python":
            witness = replay.get("input_witnesses")
            roles = replay.get("phase_roles")
            check(isinstance(witness,list) and len(witness)==2
                  and len(set(witness))==2
                  and all(isinstance(x,str) and x.isdecimal() for x in witness)
                  and isinstance(roles,dict) and set(roles)=={"constant","bit"}
                  and all(type(v) is int and v > 1 for v in roles.values())
                  and roles["constant"] != roles["bit"],
                  "Python replay missing independently derived Boolean witnesses")
        else:
            witness = replay.get("boolean_witnesses")
            check(isinstance(witness,dict)
                  and witness.get("activation_verified") is True
                  and type(witness.get("input_variable")) is int
                  and witness["input_variable"] > 0
                  and isinstance(witness.get("unique_extensions"),list)
                  and len(witness["unique_extensions"])==2
                  and len(set(witness["unique_extensions"]))==2
                  and all(isinstance(x,str) and x.isdecimal()
                          for x in witness["unique_extensions"]),
                  "Rust replay missing independent Boolean activation witnesses")
        # Separately recomputed stdlib source/CNF-Boolean oracle.
        # This independently checks ideal source inequivalence, NOT that
        # printed weights or Rust-represented fractions enclose source phases.
        oracle = replay.get("independent_analytic_source_oracle")
        check(isinstance(oracle,dict)
              and oracle.get("kind")=="independent_source_analytic_negative"
              and oracle.get("backend")==backend
              and oracle.get("solver")==solver
              and oracle.get("source_sha256")==expected_source_hash
              and oracle.get("cnf_sha256")==record["cnf_sha256"]
              and oracle.get("source_angle_radians")=="1/5000"
              and oracle.get("source_semantics_conditional") is True
              and oracle.get("printed_weight_bound_claimed") is False
              and oracle.get("general_compiler_certified") is False
              and oracle.get("native_solver_certified") is False,
              "Missing/invalid independent analytic source oracle")
        x = Fraction(1,10000)
        analytic_lower = 1-x*x/2
        analytic_upper = analytic_lower+x**4/24
        check(oracle.get("analytic_cosine_lower")==str(analytic_lower)
              and oracle.get("analytic_cosine_upper")==str(analytic_upper)
              and analytic_upper < 1,
              "Analytic source Taylor bound not the exact rational lemma")
        ow = oracle.get("unique_witnesses")
        check(isinstance(ow,list) and len(ow)==2
              and len(set(ow))==2
              and all(isinstance(z,str) and z.isdecimal() for z in ow),
              "Independent CNF witness data absent/invalid")
        if backend == "python":
            check(ow == witness
                  and oracle.get("constant_phase_literal")==roles["constant"]
                  and oracle.get("bit_phase_literal")==roles["bit"],
                  "Python independent CNF witness/phase mismatch")
        else:
            check(ow == witness["unique_extensions"]
                  and oracle.get("constant_phase_literal") ==
                      replay["boolean_witnesses"].get("constant_phase_literal")
                  and oracle.get("bit_phase_literal") ==
                      replay["boolean_witnesses"].get("input_bit_phase_literal"),
                  "Rust independent CNF witness/phase mismatch")
        output.append({
            "independent_analytic_source_upper":str(analytic_upper),
            "independent_cnfs_boolean_shape_checked":True,
            "independent_source_oracle_printed_weight_bound":False,
            "kind":Kind.SOURCE_MODEL_NEGATIVE.value,
            "status":"non_equivalent_within_audited_source_cnf_model",
            "backend":backend,"solver":solver,
            "source_commit":record["source_commit"],
            "source_qasm_sha256":expected_source_hash,
            "emitted_cnf_sha256":record["cnf_sha256"],
            "outward_rational_normalized_upper":bound,
            "original_source_normalized_upper":replay["source_upper"],
            "native_solver_binary_sha256_observed_only":
                record["native_binary_sha256_observation"],
            "strict_positive_equivalence_certified":False,
            "source_cnf_negative_conditional":True,
            "native_solver_arithmetic_certified":False,
            "general_qasm_compiler_certified":False,
        })
    check(seen == {(b,s) for b in SOURCE_HEAD for s in SOLVERS},
          "Incomplete backend/solver source coverage")
    output.sort(key=lambda row:(row["backend"],row["solver"]))
    return {
        "schema":"small-rz-conditional-source-cnf-evidence-v1",
        "status":"non_equivalent_within_audited_source_cnf_model",
        "scope":"one-qubit source QASM identity vs RZ(0.0002)",
        "metadata_self_authenticating":False,
        "raw_artifact_replay_required":True,
        "strict_positive_equivalence_certified":False,
        "native_solver_arithmetic_certified":False,
        "general_qasm_compiler_certified":False,
        "records":output,
    }
