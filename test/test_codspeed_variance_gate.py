"""P5 is a CodSpeed sampling audit, not an automatically tuned GO threshold."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


paired = _load("paired", "scripts/report_codspeed_paired_walltime.py")
variance = _load("variance", "scripts/report_codspeed_variance_gate.py")


def fixture():
    measurements = {"instrument": {"type": "walltime"}, "benchmarks": []}
    records = []
    for case in sorted(paired.EXPECTED):
        for rev in ("base", "head"):
            measurements["benchmarks"].append({
                "uri": f"test_pr_solver_inclusive_walltime[{case}-{rev}]",
                "stats": {"rounds": 3, "iter_per_round": 1,
                          "min_ns": 790_000_000, "median_ns": 800_000_000,
                          "mean_ns": 810_000_000, "stdev_ns": 12_000_000},
            })
            records.append({
                "case": case, "revision": rev,
                "sha": "b" * 40 if rev == "base" else "a" * 40,
                "fixture_sha": "a" * 40,
                "solver_invoked": True, "method": "hybrid",
                "verdict": "equivalent", "verification_status": "PASS",
                "backend": "rust", "solver": "gpmc",
                "strategy": "proportional", "reverse": False,
                "rr_approximate": False,
            })
    return paired.produce(measurements, records, "b"*40, "a"*40)[0]


def test_all_seven_sample_summaries_reported_without_go():
    r = variance.produce(fixture())
    assert r["collection_status"] == "PAIRED_ROUND_SUMMARIES_AVAILABLE"
    assert r["case_count"] == 7
    assert r["performance_status"] == "NOT_CERTIFIED"
    assert r["default_regression_threshold"] is None
    assert all(x["base_rounds"] == 3 and x["head_rounds"] == 3 for x in r["cases"])
    assert all(x["exploratory_median_change_percent"] == 0 for x in r["cases"])


def test_changed_verdict_does_not_create_performance_delta():
    report = fixture()
    report["cases"][0]["performance_comparable"] = False
    report["cases"][0]["verdict_head"] = "not_equivalent"
    audited = variance.produce(report)
    row = audited["cases"][0]
    assert "INCOMPARABLE_VERDICT" in row["blocking_reasons"]
    assert row["exploratory_median_change_percent"] is None
    assert row["performance_decision"] == "NOT_CERTIFIED"


def test_no_sample_stats_remains_explicit_missing():
    report = fixture()
    report["cases"][0].pop("head_cv")
    output = variance.produce(report)
    assert output["collection_status"] == "INCOMPLETE_SAMPLE_SUMMARIES"
    assert "MISSING_ROUND_DISTRIBUTION" in output["cases"][0]["blocking_reasons"]


def test_invalid_rounds_fails_closed():
    report = fixture()
    report["cases"][0]["head_rounds"] = 0
    with pytest.raises(ValueError, match="invalid CodSpeed sample"):
        variance.produce(report)


def test_p5_opt_in_subset_remains_noncertifying():
    r = fixture()
    r['cases'] = r['cases'][:4]
    report = variance.produce(r, expected_count=4)
    assert report['case_count'] == 4
    assert report['performance_status'] == 'NOT_CERTIFIED'
    assert report['default_regression_threshold'] is None
    with pytest.raises(ValueError, match='expected 7'):
        variance.produce(r)
