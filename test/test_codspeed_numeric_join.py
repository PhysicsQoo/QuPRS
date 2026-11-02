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
    assert output["numerical_cross_validation_complete"]
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
