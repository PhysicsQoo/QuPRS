"""No-solver regressions for representative benchmark JUnit evidence."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_benchmark_evidence", ROOT / "scripts/check_benchmark_evidence.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def catalog(tmp_path):
    path = tmp_path / "cases.py"
    path.write_text("MQT_CASES = ((\"m.qasm\", \"naive\", False),) * 6\n"
                    "FEYNMAN_CASES = ((\"f.qasm\", \"proportional\", True),) * 4\n")
    return path


def real_catalog():
    return ROOT / "test/_benchmark_cases.py"


def junit(tmp_path, statuses=None, drop=(), duplicate=()):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for key in checker.expected_cases(real_catalog()):
        if key in drop:
            continue
        cls, name = key
        case = ET.SubElement(suite, "testcase", classname="test." + cls, name=name)
        kind = (statuses or {}).get(key, "PASS")
        if kind == "INCONCLUSIVE_RESOURCE":
            ET.SubElement(case, "skipped", message="INCONCLUSIVE_RESOURCE: Timeout")
        elif kind == "SKIP":
            ET.SubElement(case, "skipped", message="Unsupported platform")
        elif kind == "FAIL":
            ET.SubElement(case, "failure", message="wrong verdict")
        elif kind == "ERROR":
            ET.SubElement(case, "error", message="runner failed")
        if key in duplicate:
            ET.SubElement(suite, "testcase", classname="test." + cls, name=name)
    path = tmp_path / "tests.xml"
    ET.ElementTree(root).write(path)
    return path


def test_full_thirty_two_cases_are_complete(tmp_path):
    report = checker.audit(junit(tmp_path), real_catalog(), require_complete=True)
    assert report["expected"] == report["observed"] == report["counts"]["PASS"] == 32
    assert report["status"] == "COMPLETE"


def test_single_timeout_is_inconclusive_not_blocking(tmp_path):
    key = next(iter(checker.expected_cases(real_catalog())))
    report = checker.audit(junit(tmp_path, {key: "INCONCLUSIVE_RESOURCE"}), real_catalog())
    assert report["status"] == "INCONCLUSIVE_RESOURCE"
    assert report["counts"]["INCONCLUSIVE_RESOURCE"] == 1
    assert report["counts"]["SKIP"] == 0
    assert report["counts"]["PASS"] == 31


def test_single_timeout_cannot_publish_a_main_baseline(tmp_path):
    key = next(iter(checker.expected_cases(real_catalog())))
    report = checker.audit(junit(tmp_path, {key: "INCONCLUSIVE_RESOURCE"}), real_catalog(), require_complete=True)
    assert report["status"] == "BLOCKED"
    assert "incomplete baseline" in " ".join(report["problems"])


def test_all_inconclusive_cannot_yield_green(tmp_path):
    cases = checker.expected_cases(real_catalog())
    report = checker.audit(junit(tmp_path, dict.fromkeys(cases, "INCONCLUSIVE_RESOURCE")), real_catalog())
    assert report["status"] == "BLOCKED"
    assert report["counts"]["PASS"] == 0


def test_planned_skip_is_distinct_from_inconclusive(tmp_path):
    key = next(iter(checker.expected_cases(real_catalog())))
    report = checker.audit(junit(tmp_path, {key: "SKIP"}), real_catalog())
    assert report["counts"]["SKIP"] == 1
    assert report["counts"]["INCONCLUSIVE_RESOURCE"] == 0
    assert report["status"] == "PARTIAL_SKIP"


def test_absent_or_duplicated_identity_blocks(tmp_path):
    key = next(iter(checker.expected_cases(real_catalog())))
    assert checker.audit(junit(tmp_path, drop={key}), real_catalog())["status"] == "BLOCKED"
    assert checker.audit(junit(tmp_path, duplicate={key}), real_catalog())["status"] == "BLOCKED"


def test_definitive_mismatch_still_blocks(tmp_path):
    key = next(iter(checker.expected_cases(real_catalog())))
    report = checker.audit(junit(tmp_path, {key: "FAIL"}), real_catalog())
    assert report["status"] == "BLOCKED"
    assert report["counts"]["FAIL"] == 1


def test_cohort_without_success_is_not_verified(tmp_path):
    cases = checker.expected_cases(real_catalog())
    statuses = {key: "INCONCLUSIVE_RESOURCE" for key, cohort in cases.items() if cohort == "Feynman"}
    report = checker.audit(junit(tmp_path, statuses), real_catalog())
    assert report["status"] == "BLOCKED"
    assert "Feynman" in " ".join(report["problems"])

def test_four_graphstate_backend_approximate_results_are_distinct_from_strict(tmp_path):
    """Approximate scientific controls count separately, never as 32 strict PASS."""
    keys = [
        key for key in checker.expected_cases(real_catalog())
        if checker.authorized_approximate_case(*key)
    ]
    assert len(keys) == 4
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for cls, name in checker.expected_cases(real_catalog()):
        node = ET.SubElement(suite, "testcase", classname="test." + cls, name=name)
        if (cls, name) not in keys:
            continue
        props = ET.SubElement(node, "properties")
        good = {
            "verification_status": checker.APPROXIMATE_REDUCED_BOUND,
            "strict_source_verdict": "not_equivalent",
            "observed_backend_verdict": (
                "not_equivalent" if name.endswith("-rust]") else "equivalent"
            ),
            "approximate_metric": "projective_hilbert_schmidt",
            "approximate_threshold": "1e-8",
            "distance_squared_upper": "1/100000000000000000000000000000",
            "proof_provenance": "source-pinned-reduced-diagonal",
            "source_blobs": checker._PINNED_SOURCE_BLOBS,
        }
        for k, v in good.items():
            ET.SubElement(props, "property", name=k, value=v)
    output = tmp_path / "approximately.xml"
    ET.ElementTree(root).write(output)
    summary = checker.audit(output, real_catalog())
    assert summary["status"] == "COMPLETE_WITH_APPROXIMATE"
    assert summary["counts"]["PASS"] == 28
    assert summary["counts"][checker.APPROXIMATE_REDUCED_BOUND] == 4
    strict = checker.audit(output, real_catalog(), require_complete=True)
    assert strict["status"] == "BLOCKED"
    assert strict["counts"]["PASS"] == 28

    # A missing provenance value, an unauthorized case, or a failed test
    # cannot be reclassified as a valid approximate result.
    special = suite.findall("testcase")
    first_approx = next(x for x in special if checker.authorized_approximate_case(
        x.get("classname").split(".")[-1], x.get("name")))
    metric = next(x for x in first_approx.findall("./properties/property")
                  if x.get("name") == "approximate_metric")
    metric.set("value", "wmc_magnitude_defect")
    ET.ElementTree(root).write(output)
    report = checker.audit(output, real_catalog())
    assert report["status"] == "BLOCKED"
    assert report["counts"]["ERROR"] == 1
    assert report["approximation_errors"]


def test_approximate_source_proof_rejected_for_unrelated_benchmark():
    key = next(k for k in checker.expected_cases(real_catalog())
               if not checker.authorized_approximate_case(*k))
    assert not checker.validate_approximate_properties(
        *key, {"verification_status": checker.APPROXIMATE_REDUCED_BOUND}
    )


def test_approximate_source_proof_rejects_invalid_upper_bound():
    key = next(k for k in checker.expected_cases(real_catalog())
               if checker.authorized_approximate_case(*k))
    good = {
        "verification_status": checker.APPROXIMATE_REDUCED_BOUND,
        "strict_source_verdict": "not_equivalent",
        "observed_backend_verdict": "not_equivalent",
        "approximate_metric": "projective_hilbert_schmidt",
        "approximate_threshold": "1e-8",
        "distance_squared_upper": "1/100000000000000000000000000000",
        "proof_provenance": "source-pinned-reduced-diagonal",
        "source_blobs": checker._PINNED_SOURCE_BLOBS,
    }
    assert checker.validate_approximate_properties(*key, good)
    for value in ("nan", "-1e-30", "1e-8", "1/0", "0"):
        broken = {**good, "distance_squared_upper": value}
        assert not checker.validate_approximate_properties(*key, broken)

def test_approximate_backend_verdict_is_provenance_not_strict_truth():
    cases = list(checker.expected_cases(real_catalog()))
    py = next(k for k in cases if checker.authorized_approximate_case(*k)
              and k[1].endswith("-python]"))
    rust = next(k for k in cases if checker.authorized_approximate_case(*k)
                and k[1].endswith("-rust]"))
    for case, raw in ((py, "equivalent"), (py, "not_equivalent"),
                      (rust, "not_equivalent")):
        values = {
            "verification_status": checker.APPROXIMATE_REDUCED_BOUND,
            "strict_source_verdict": "not_equivalent",
            "observed_backend_verdict": raw,
            "approximate_metric": "projective_hilbert_schmidt",
            "approximate_threshold": "1e-8",
            "distance_squared_upper": "1/100000000000000000000000000000",
            "proof_provenance": "source-pinned-reduced-diagonal",
            "source_blobs": checker._PINNED_SOURCE_BLOBS,
        }
        assert checker.validate_approximate_properties(*case, values)
    values["observed_backend_verdict"] = "equivalent"
    assert not checker.validate_approximate_properties(*rust, values)
    values["observed_backend_verdict"] = "unknown"
    assert not checker.validate_approximate_properties(*py, values)
