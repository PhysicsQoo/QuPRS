"""No fabricated or cross-SHA CodSpeed numeric comparisons."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "numeric_report", ROOT / "scripts" / "join_codspeed_numeric.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SHA = "a" * 40
CASE = "test/test_MQT.py::test_all_benchmarks[vqe4]"

def _input():
    return {"schema":"quprs-codspeed-cross-instrument-v2", "head_sha":SHA,
            "scientific_status":"PASS",
            "cross_instrument_rows":[{
                "case":"vqe4_gpmc", "simulation_uri":CASE,
                "comparable_verdict": True,
                "walltime_base_median_ms":800.0,
                "walltime_head_median_ms":810.0,
            }]}

def test_missing_remote_numeric_is_explicit():
    output=module.join(_input(),{"results":[]})
    assert output["missing_numeric"] == 1
    assert not output["numerical_cross_validation_complete"]
    assert output["cases"][0]["numeric_cpu"] is None

def test_same_sha_has_separate_typed_numbers():
    r={"sha":SHA, "runner_mode":"Simulation", "uri":CASE,
       "measured_in_run":True, "run_id":"codspeed-current-run",
       "cpu_model":"EPYC", "unit":"ms", "value":18.5}
    output=module.join(_input(),{"results":[r]})
    # Same-SHA common-case CPU is present, but 22 Rust-native metrics are
    # still missing from the service import: do not assert complete coverage.
    assert not output["numerical_cross_validation_complete"]
    assert output["cases"][0]["numeric_cpu"]["value"] == 18.5
    assert output["cases"][0]["walltime"]["head_median_ms"] == 810
    assert not output["performance_certified"]

@pytest.mark.parametrize("mutation",[
    {"sha":"b"*40},
    {"measured_in_run":False},
    {"value":float("nan")},
    {"cpu_model":""},
])
def test_wrong_or_unverified_numeric_is_rejected(mutation):
    r={"sha":SHA, "runner_mode":"Simulation", "uri":CASE,
       "measured_in_run":True, "run_id":"codspeed-current-run",
       "cpu_model":"EPYC", "unit":"ms", "value":18.5}
    r.update(mutation)
    with pytest.raises(ValueError):
        module.join(_input(),{"results":[r]})

def test_native_rust_core_explicitly_missing_without_service_measurements():
    from benchmarks.codspeed.case_registry import NATIVE_IDS
    output = module.join(_input(), {"results": []})
    assert output["native_core_expected_count"] == len(NATIVE_IDS)
    assert output["native_core_missing_numeric"] == len(NATIVE_IDS)
    assert output["external_source_status"] == "PARTIALLY_MISSING"
    assert not output["numerical_cross_validation_complete"]


def test_exact_sha_service_native_cpu_measurement_is_matched():
    from benchmarks.codspeed.case_registry import NATIVE_IDS
    r = {"sha": SHA, "runner_mode": "Simulation",
         "uri": "benches/core.rs::" + NATIVE_IDS[-1],
         "measured_in_run": True, "run_id": "same-head-current-codspeed-run",
         "cpu_model": "runner-identical", "unit": "us", "value": 13.5}
    output = module.join(_input(), {"results": [r]})
    assert output["native_core_missing_numeric"] == len(NATIVE_IDS) - 1
    assert output["native_core"][-1]["measurement"]["value"] == 13.5
    assert not output["numerical_cross_validation_complete"]

def test_all_legacy_uris_are_listed_and_missing_without_numeric_export():
    ev = _input()
    ev["simulation_uris"] = [
        f"test/test_Feynman.py::candidate[{i}]" for i in range(32)
    ]
    output = module.join(ev, {"results": []})
    assert output["legacy_expected_count"] == 32
    assert output["legacy_missing_numeric"] == 32
    assert len(output["legacy_core"]) == 32
    assert not output["numerical_cross_validation_complete"]


def test_python_core_optional_missing_is_not_silent():
    from benchmarks.codspeed.case_registry import PYTHON_CORE_CASE_IDS
    ev = _input()
    ev["optional_python_core_count"] = len(PYTHON_CORE_CASE_IDS)
    output = module.join(ev, {"results": []})
    assert output["python_core_expected_count"] == 5
    assert output["python_core_missing_numeric"] == 5
    assert all(r["status"] == "MISSING_NUMERIC" for r in output["python_core"])


def test_global_ganak_science_caveat_does_not_mark_valid_gpmc_case_wrong():
    ev = _input()
    ev["scientific_status"] = "PRECISION_LIMITED"
    r = {"sha":SHA, "runner_mode":"Simulation", "uri":CASE,
         "measured_in_run":True, "run_id":"codspeed-current-run",
         "cpu_model":"source-pinned exact", "unit":"ms", "value":18.5}
    out = module.join(ev, {"results":[r]})
    assert out["cases"][0]["status"] == "NUMERIC_AVAILABLE"
    assert not out["performance_certified"]
