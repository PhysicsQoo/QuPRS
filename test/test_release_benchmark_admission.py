"""Exercise release versus exploratory admission on the *actual* JUnit auditor.

Synthetic XML is restricted to this policy test. It never stands in for a
science result or introduces an expected quantum-circuit verdict.
"""
import xml.etree.ElementTree as ET

import pytest

from scripts.check_benchmark_evidence import (
    _PINNED_SOURCE_BLOBS,
    audit,
    expected_cases,
    requires_distance_certificate,
)


@pytest.mark.parametrize(
    "reason,tag",
    (
        ("INCONCLUSIVE_RESOURCE: solver timeout", "skipped"),
        ("planned opt-out", "skipped"),
        ("genuine scientific wrong answer", "failure"),
    ),
)
def test_release_32_case_auditor_never_promotes_unverified_science(
    tmp_path, reason, tag
):
    from pathlib import Path

    catalog = Path(__file__).with_name("_benchmark_cases.py")
    expected = expected_cases(catalog)
    assert len(expected) == 32
    suite = ET.Element("testsuite")
    first = next(iter(expected))
    for cls, name in expected:
        case = ET.SubElement(suite, "testcase", classname=cls, name=name)
        if (cls, name) == first:
            ET.SubElement(case, tag, message=reason)
        elif requires_distance_certificate(cls, name):
            properties = ET.SubElement(case, "properties")
            for key, value in (
                ("approximate_metric", "projective_hilbert_schmidt"),
                ("proof_provenance", "source-pinned-reduced-diagonal"),
                ("source_blobs", _PINNED_SOURCE_BLOBS),
                ("verification_status", "PASS"),
                ("observed_backend_verdict", "equivalent"),
                ("approximate_threshold", "1e-8"),
                ("distance_squared_upper", "0"),
            ):
                ET.SubElement(properties, "property", name=key, value=value)
    report_path = tmp_path / "scoped-science.xml"
    ET.ElementTree(suite).write(report_path, encoding="utf-8")

    regular = audit(report_path, catalog, require_complete=False)
    release = audit(report_path, catalog, require_complete=True)
    assert release["status"] == "BLOCKED"
    assert release["counts"]["PASS"] == 31
    if tag == "failure":
        assert regular["status"] == "BLOCKED"
        assert release["counts"]["FAIL"] == 1
    else:
        assert regular["status"] in ("INCONCLUSIVE_RESOURCE", "PARTIAL_SKIP")
        assert release["counts"]["SKIP"] + release["counts"]["INCONCLUSIVE_RESOURCE"] == 1
        assert any("incomplete baseline" in p for p in release["problems"])
