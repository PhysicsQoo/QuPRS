"""No-Solver source and identity gates for the new Qiskit261 CodSpeed cohort."""
from scripts.audit_codspeed_qasm_variants import audit
from benchmarks.codspeed.case_registry import (
    QASM261_PILOT_CASES, LEGACY_CASE_COUNT, LEGACY_SHARD_COUNT,
)


def test_all_registered_qasm_inputs_and_full_versioned_corpus_have_verified_hashes():
    report = audit()
    assert report == {
        "status": "QASM261_SOURCE_REVIEW_PASS",
        "cases": 37, "observations": 296, "matched": 244,
        "censored": 52, "contradictions": 0,
        "selected_mqt": 20, "feynman": 4, "versioned_pilots": 15,
    }


def test_versioned_pilots_do_not_repurpose_legacy_or_existing_experiment_uris():
    assert (LEGACY_CASE_COUNT, LEGACY_SHARD_COUNT) == (32, 5)
    assert len(QASM261_PILOT_CASES) == 15
    assert all(x.id.startswith("q261_") for x in QASM261_PILOT_CASES)
    assert len(set(x.id for x in QASM261_PILOT_CASES)) == 15
    assert all(x.qasm_corpus == "qiskit-2.6.1-opt0" for x in QASM261_PILOT_CASES)
    assert {x.pair_variant for x in QASM261_PILOT_CASES} == {
        "transpiled", "random_rotation",
    }
