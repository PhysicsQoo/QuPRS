"""Benchmark outcome gates: one distance threshold, four pinned proofs."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "benchmark_audit", ROOT / "scripts/check_benchmark_evidence.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
CATALOG = ROOT / "test/_benchmark_cases.py"


def cases():
    return checker.expected_cases(CATALOG)


def pinned():
    return {k for k in cases() if checker.requires_distance_certificate(*k)}


def proof(verdict="equivalent", upper="1/100000000000000000000000000000"):
    return {
        "verification_status": "PASS",
        "observed_backend_verdict": verdict,
        "approximate_metric": "projective_hilbert_schmidt",
        "approximate_threshold": "1e-8",
        "distance_squared_upper": upper,
        "proof_provenance": "source-pinned-reduced-diagonal",
        "source_blobs": checker._PINNED_SOURCE_BLOBS,
    }


def fixture(tmp_path, statuses=None, overrides=None, omit=(), duplicate=()):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for key in cases():
        if key in omit:
            continue
        cls, name = key
        node = ET.SubElement(suite, "testcase", classname="test." + cls, name=name)
        status = (statuses or {}).get(key, "PASS")
        props = (overrides or {}).get(key, proof() if key in pinned() else {})
        if status == "PASS" and props:
            group = ET.SubElement(node, "properties")
            for k, v in props.items():
                ET.SubElement(group, "property", name=k, value=str(v))
        elif status == "FAIL":
            ET.SubElement(node, "failure", message="wrong verdict")
        elif status == "ERROR":
            ET.SubElement(node, "error", message="execution failed")
        elif status in ("INCONCLUSIVE_RESOURCE", "SKIP"):
            ET.SubElement(node, "skipped", message=status)
        if key in duplicate:
            ET.SubElement(suite, "testcase", classname="test." + cls, name=name)
    path = tmp_path / "evidence.xml"
    ET.ElementTree(root).write(path)
    return path


def report(tmp_path, **kw):
    return checker.audit(fixture(tmp_path, **kw), CATALOG)


def test_all_32_count_as_pass_and_release_complete(tmp_path):
    result = report(tmp_path)
    assert len(pinned()) == 4
    assert result["expected"] == result["observed"] == result["counts"]["PASS"] == 32
    assert result["distance_certificates_verified"] == 4
    assert result["status"] == "COMPLETE"
    strict = checker.audit(fixture(tmp_path), CATALOG, require_complete=True)
    assert strict["status"] == "COMPLETE"
    assert not strict["problems"]


def test_both_equivalent_and_equivalent_star_are_valid(tmp_path):
    values = {key: proof(verdict="equivalent*" if i % 2 else "equivalent")
              for i, key in enumerate(sorted(pinned()))}
    result = report(tmp_path, overrides=values)
    assert result["counts"]["PASS"] == 32
    assert result["distance_certificates_verified"] == 4


def test_zero_and_exact_tolerance_boundary_are_accepted():
    key = next(iter(pinned()))
    for upper_sq in ("0", "1/10000000000000000"):
        assert checker.validate_source_distance_certificate(*key, proof(upper=upper_sq))


def test_above_distance_limit_and_invalid_bounds_are_not_pass(tmp_path):
    key = next(iter(pinned()))
    for upper in ("1/9999999999999999", "1e-8", "-1e-29", "nan", "1/0"):
        sample = proof(upper=upper)
        assert not checker.validate_source_distance_certificate(*key, sample)
        r = report(tmp_path, overrides={key: sample})
        assert r["status"] == "BLOCKED" and r["counts"]["ERROR"] == 1


def test_solver_negative_and_unknown_are_not_silently_pass(tmp_path):
    key = next(iter(pinned()))
    for verdict in ("not_equivalent", "unknown", "Timeout", "invalid"):
        sample = proof(verdict=verdict)
        assert not checker.validate_source_distance_certificate(*key, sample)
        assert report(tmp_path, overrides={key: sample})["status"] == "BLOCKED"


def test_source_evidence_integrity_not_a_second_numeric_threshold(tmp_path):
    key = next(iter(pinned()))
    changes = [
        {"approximate_metric": "wmc_magnitude_defect"},
        {"approximate_threshold": "1e-7"},
        {"approximate_threshold": "1e-9"},
        {"source_blobs": "x" * 40},
        {"proof_provenance": "heuristic"},
        {"verification_status": "APPROXIMATE_REDUCED_BOUND"},
    ]
    for changed in changes:
        sample = {**proof(), **changed}
        assert not checker.validate_source_distance_certificate(*key, sample)
        assert report(tmp_path, overrides={key: sample})["status"] == "BLOCKED"


def test_missing_certificate_cannot_claim_pass(tmp_path):
    key = next(iter(pinned()))
    r = report(tmp_path, overrides={key: {}})
    assert r["status"] == "BLOCKED"
    assert r["counts"]["PASS"] == 31
    assert r["counts"]["ERROR"] == 1
    assert r["distance_certificates_verified"] == 3


def test_unrelated_benchmark_cannot_borrow_graphstate_proof(tmp_path):
    key = next(k for k in cases() if k not in pinned())
    assert not checker.validate_source_distance_certificate(*key, proof())
    assert report(tmp_path, overrides={key: proof()})["status"] == "BLOCKED"


def test_resource_timeout_and_missing_cases_never_count_pass(tmp_path):
    key = next(k for k in cases() if k not in pinned())
    r = report(tmp_path, statuses={key: "INCONCLUSIVE_RESOURCE"})
    assert r["status"] == "INCONCLUSIVE_RESOURCE"
    assert r["counts"]["PASS"] == 31
    assert checker.audit(fixture(tmp_path, statuses={key: "INCONCLUSIVE_RESOURCE"}),
                         CATALOG, require_complete=True)["status"] == "BLOCKED"
    assert report(tmp_path, omit={key})["status"] == "BLOCKED"
    assert report(tmp_path, duplicate={key})["status"] == "BLOCKED"


def test_failures_and_empty_feynman_cohort_still_block(tmp_path):
    key = next(iter(pinned()))
    assert report(tmp_path, statuses={key: "FAIL"})["status"] == "BLOCKED"
    missing = {k: "INCONCLUSIVE_RESOURCE" for k, group in cases().items()
               if group == "Feynman"}
    r = report(tmp_path, statuses=missing)
    assert r["status"] == "BLOCKED"
    assert "Feynman" in " ".join(r["problems"])


def test_skipped_benchmark_does_not_count_as_pass(tmp_path):
    key = next(iter(pinned()))
    r = report(tmp_path, statuses={key: "SKIP"})
    assert r["status"] == "PARTIAL_SKIP"
    assert r["counts"]["SKIP"] == 1


def test_report_interpretation_separates_provenance_from_verdict(tmp_path):
    r = report(tmp_path)
    assert "SAME distance tolerance" in r["interpretation"]
    assert "strict mathematical identity" in r["interpretation"]
    assert "APPROXIMATE_REDUCED_BOUND" not in r["counts"]
