"""Release science failure versus optional performance completeness (real auditor).

The test JUnit XML is policy-only; these records are not evidence of
quantum-circuit equivalence. All 32 identities and pinned source-distance
provenances are still independently checked by the actual auditor.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from scripts.check_benchmark_evidence import (
    _PINNED_SOURCE_BLOBS,
    audit,
    expected_cases,
    requires_distance_certificate,
)


def _junit(tmp_path, *, changed=None, omitted=()):
    catalog = Path(__file__).with_name("_benchmark_cases.py")
    cases = expected_cases(catalog)
    assert len(cases) == 32
    root = ET.Element("testsuite")
    for cls, name in cases:
        if (cls, name) in omitted:
            continue
        node = ET.SubElement(root, "testcase", classname=cls, name=name)
        if (cls, name) in (changed or {}):
            kind, reason = changed[cls, name]
            ET.SubElement(node, kind, message=reason)
        elif requires_distance_certificate(cls, name):
            properties = ET.SubElement(node, "properties")
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
    path = tmp_path / "release-policy-cases.xml"
    ET.ElementTree(root).write(path, encoding="utf-8")
    return path, catalog, cases


@pytest.mark.parametrize("tag,reason,expected", (
    ("skipped", "INCONCLUSIVE_RESOURCE: bounded timeout", "INCONCLUSIVE_RESOURCE"),
    ("skipped", "planned sampling skip", "PARTIAL_SKIP"),
    ("failure", "wrong science verdict", "BLOCKED"),
    ("error", "malformed solver output", "BLOCKED"),
))
def test_release_science_not_automatically_blocked_by_resource(
    tmp_path, tag, reason, expected
):
    _, _, cases = _junit(tmp_path)
    first = next(iter(cases))
    path, catalog, _ = _junit(tmp_path, changed={first: (tag, reason)})
    normal = audit(path, catalog, require_complete=False)
    strict_performance = audit(path, catalog, require_complete=True)
    assert normal["status"] == expected
    assert normal["counts"]["PASS"] == 31
    assert strict_performance["status"] == "BLOCKED"
    if tag in ("failure", "error"):
        assert normal["problems"]
        assert normal["counts"]["FAIL"] + normal["counts"]["ERROR"] == 1
    else:
        assert not normal["problems"]
        assert normal["counts"]["SKIP"] + normal["counts"]["INCONCLUSIVE_RESOURCE"] == 1
        assert normal["counts"]["PASS"] < normal["expected"]
        assert any("incomplete baseline" in p for p in strict_performance["problems"])


def test_entire_resource_limited_cohort_does_not_become_wrong_science(
    tmp_path
):
    _, _, cases = _junit(tmp_path)
    changed = {
        key: ("skipped", "INCONCLUSIVE_RESOURCE: bounded solver timeout")
        for key, group in cases.items() if group == "Feynman"
    }
    path, catalog, _ = _junit(tmp_path, changed=changed)
    result = audit(path, catalog)
    assert result["status"] == "INCONCLUSIVE_RESOURCE"
    assert result["by_cohort"]["Feynman"]["PASS"] == 0
    assert result["by_cohort"]["Feynman"]["INCONCLUSIVE_RESOURCE"] == len(changed)
    assert "Feynman" in " ".join(result["advisories"])
    assert not result["problems"]
    assert audit(path, catalog, require_complete=True)["status"] == "BLOCKED"


def test_missing_source_identity_and_invalid_proof_still_block(tmp_path):
    _, _, cases = _junit(tmp_path)
    first = next(iter(cases))
    path, catalog, _ = _junit(tmp_path, omitted={first})
    assert audit(path, catalog)["status"] == "BLOCKED"
    pinned = next(key for key in cases if requires_distance_certificate(*key))
    path, catalog, _ = _junit(tmp_path, changed={pinned: ("error", "invalid proof")})
    assert audit(path, catalog)["status"] == "BLOCKED"
