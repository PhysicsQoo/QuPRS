"""Pure Python TACAS artifact classifier fidelity (no Solver/time measurement)."""
import json
import math
from pathlib import Path

import pytest

from scripts.replay_tacas26_artifact import (
    ARTIFACT_SHA, QPE20_SOURCE_SHA256, QU_PRS_SHA,
    replay_classifier, replay_qpe20_observation,
)

def test_real_artifact_provenance_is_pinned():
    assert ARTIFACT_SHA == "d8d3e7da555e9e20bdec6f3abe4a13ad899af62b"
    assert QU_PRS_SHA == "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
    assert set(QPE20_SOURCE_SHA256) == {"original","transpiled"}

def test_legacy_rounding_can_accept_source_distinct_from_modern_threshold():
    # The old v0.9.1 classifier rounds log2 count BEFORE comparison.
    result=replay_classifier(20.999999999987054,21,theta_rad=0.02)
    assert result["rounded_log2_magnitude"]==21
    assert result["legacy_verdict"]=="equivalent*"
    assert result["magnitude_accepted"] is True
    unknown=replay_classifier(20.999999999987054,21)
    assert unknown["legacy_verdict"]=="PHASE_UNOBSERVED"

def test_legacy_quantization_is_not_1e_8_projective_certification():
    # A separate example demonstrates how coarse the old quantization was.
    near=replay_classifier(21-0.00049,21)
    assert near["magnitude_accepted"]
    assert near["legacy_verdict"]=="PHASE_UNOBSERVED"
    assert math.sqrt(1-2**(-2*0.00049)) > 0.02

def test_legacy_magnitude_boundary_and_finite_input():
    assert not replay_classifier(20.9994,21)["magnitude_accepted"]
    with pytest.raises(ValueError,match="Nonfinite"):
        replay_classifier(float("nan"),21)

def test_qpe20_replay_does_not_forge_archived_solver_verdict():
    rows = [
        {"id":"python_default","status":None,"exit_code":0,
         "solver_invoked":True,"verdict":"not_equivalent",
         "effective_distance_tolerance":1e-8,
         "wmc_expected_log2":21.0,"wmc_log_wmc":20.999999999987054,
         "wmc_precision_reason":"printed_count_uncertified"},
        {"id":"python_d1e-5","status":None,"exit_code":0,
         "solver_invoked":True,"verdict":"equivalent*",
         "effective_distance_tolerance":1e-5,
         "wmc_expected_log2":21.0,"wmc_log_wmc":20.999999999987054,
         "wmc_precision_reason":"printed_count_uncertified"}
    ]
    data={"sha":"d8db00a", "source_qasm_sha256":dict(QPE20_SOURCE_SHA256),
          "observations":rows}
    report=replay_qpe20_observation(data)
    assert report["replayed_legacy_magnitude"]["magnitude_accepted"] is True
    assert report["replayed_legacy_magnitude"]["legacy_verdict"]=="PHASE_UNOBSERVED"
    assert report["modern_default"]["verdict"]=="not_equivalent"
    assert report["modern_explicit_paper_comparison"]["verdict"]=="equivalent*"
    assert report["archived_solver_reexecuted"] is False
    assert report["modern_source_operator_equivalence_certified"] is False
    assert report["paper_phase_verdict_reproduced_from_archived_solver"] is False
    data["source_qasm_sha256"]["original"]="wrong"
    with pytest.raises(ValueError,match="Unpinned source"):
        replay_qpe20_observation(data)
