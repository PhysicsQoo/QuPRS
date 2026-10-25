#!/usr/bin/env python3
"""Audit representative benchmark outcomes from pytest JUnit XML.

Scientific INCONCLUSIVE_RESOURCE must never be reported as a proved equivalence.
An incomplete performance sample is distinct from a planned pytest skip.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import runpy
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]

APPROXIMATE_REDUCED_BOUND = "APPROXIMATE_REDUCED_BOUND"
_GRAPHSTATE_FILE = "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
_PINNED_SOURCE_BLOBS = (
    "ab34308febb31ea9a49e9761a988aad7017f3487:"
    "c2c6f9d04f6a8c2778415572aa247ee93e138c09"
)


def authorized_approximate_case(classname: str, name: str) -> bool:
    return (
        classname == "test_MQT"
        and name in {
            f"test_all_benchmarks[{_GRAPHSTATE_FILE}-naive-False-{tool}-{backend}]"
            for tool in ("gpmc", "ganak")
            for backend in ("python", "rust")
        }
    )


def validate_approximate_properties(classname: str, name: str, props: dict) -> bool:
    """Source-pinned, fail-closed evidence; not a strict-equivalence proof."""
    if not authorized_approximate_case(classname, name):
        return False
    mandatory = {
        "verification_status": APPROXIMATE_REDUCED_BOUND,
        "strict_source_verdict": "not_equivalent",
        "approximate_metric": "projective_hilbert_schmidt",
        "approximate_threshold": "1e-8",
        "proof_provenance": "source-pinned-reduced-diagonal",
        "source_blobs": _PINNED_SOURCE_BLOBS,
    }
    if any(props.get(k) != v for k, v in mandatory.items()):
        return False
    observed = props.get("observed_backend_verdict")
    if name.endswith("-rust]"):
        if observed != "not_equivalent":
            return False
    elif name.endswith("-python]"):
        if observed not in {"equivalent", "equivalent*", "not_equivalent"}:
            return False
    else:
        return False
    try:
        bound = Fraction(props["distance_squared_upper"])
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        return False
    return Fraction(0) < bound <= Fraction(1, 10**16)



def expected_cases(catalog: Path) -> dict[tuple[str, str], str]:
    cases = runpy.run_path(str(catalog))
    expected = {}
    for filename, strategy, reverse in cases["MQT_CASES"]:
        for solver in ("gpmc", "ganak"):
            for backend in ("python", "rust"):
                name = (f"test_all_benchmarks[{filename}-{strategy}-{reverse}-"
                        f"{solver}-{backend}]")
                expected[("test_MQT", name)] = "MQT"
    for filename, strategy, reverse in cases["FEYNMAN_CASES"]:
        for backend in ("python", "rust"):
            name = f"test_all_benchmarks[{filename}-{strategy}-{reverse}-{backend}]"
            expected[("test_Feynman", name)] = "Feynman"
    if len(expected) != 32:
        raise ValueError(f"Unexpected benchmark catalog: {len(expected)} cases")
    return expected


def audit(junit: Path, catalog: Path, *, require_complete: bool = False) -> dict:
    expected = expected_cases(catalog)
    root = ET.parse(junit).getroot()
    actual = {}
    unexpected = []
    approximation_errors = []
    for case in root.iter("testcase"):
        classname = case.get("classname", "").split(".")[-1]
        name = case.get("name", "")
        if classname not in {"test_MQT", "test_Feynman"} or not name.startswith("test_all_benchmarks["):
            continue
        key = (classname, name)
        if key not in expected or key in actual:
            unexpected.append({"class": classname, "name": name})
            continue
        if case.find("failure") is not None:
            state = "FAIL"
        elif case.find("error") is not None:
            state = "ERROR"
        elif (skipped := case.find("skipped")) is not None:
            reason = " ".join((skipped.get("message", ""), skipped.text or ""))
            state = "INCONCLUSIVE_RESOURCE" if "INCONCLUSIVE_RESOURCE" in reason else "SKIP"
        else:
            properties = {
                prop.get("name"): prop.get("value")
                for prop in case.findall("./properties/property")
            }
            required_approximate = authorized_approximate_case(classname, name)
            if properties.get("verification_status") == APPROXIMATE_REDUCED_BOUND:
                if validate_approximate_properties(classname, name, properties):
                    state = APPROXIMATE_REDUCED_BOUND
                else:
                    state = "ERROR"
                    approximation_errors.append({"class": classname, "name": name})
            elif required_approximate:
                # Missing metadata cannot silently upgrade source-approximate
                # evidence into a strict positive result.
                state = "ERROR"
                approximation_errors.append({"class": classname, "name": name})
            else:
                state = "PASS"
        actual[key] = {"group": expected[key], "status": state}
    missing = [{"class": cls, "name": name} for cls, name in expected if (cls, name) not in actual]
    counts = {name: sum(entry["status"] == name for entry in actual.values())
              for name in ("PASS", APPROXIMATE_REDUCED_BOUND, "FAIL", "ERROR", "INCONCLUSIVE_RESOURCE", "SKIP")}
    by_group = {group: {name: sum(entry == {"group": group, "status": name}
                                  for entry in actual.values()) for name in counts}
                for group in ("MQT", "Feynman")}
    problems = []
    if unexpected:
        problems.append("unexpected or duplicate benchmark identities")
    if approximation_errors:
        problems.append("unverified or unauthorized approximate evidence")
    if missing:
        problems.append("benchmark cases absent from JUnit evidence")
    if counts["FAIL"] or counts["ERROR"]:
        problems.append("benchmark contained definitive failures")
    for group, values in by_group.items():
        if values["PASS"] == 0:
            problems.append(f"no completed positive benchmark in {group} cohort")
    if require_complete and counts["PASS"] != len(expected):
        problems.append("incomplete baseline; do not publish partial performance history")
    return {
        "schema": "benchmark-outcome-evidence-v1",
        "provenance": {
            "github_sha": os.getenv("GITHUB_SHA"),
            "runner_os": os.getenv("RUNNER_OS"),
            "runner_arch": os.getenv("RUNNER_ARCH"),
            "runner_image": os.getenv("ImageOS"),
            "runner_image_version": os.getenv("ImageVersion"),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "expected": len(expected),
        "observed": len(actual),
        "counts": counts,
        "by_cohort": by_group,
        "missing": missing,
        "unexpected": unexpected,
        "approximation_errors": approximation_errors,
        "status": "BLOCKED" if problems else (
            "INCONCLUSIVE_RESOURCE" if counts["INCONCLUSIVE_RESOURCE"] else
            "PARTIAL_SKIP" if counts["SKIP"] else
            "COMPLETE_WITH_APPROXIMATE" if counts[APPROXIMATE_REDUCED_BOUND] else
            "COMPLETE"),
        "problems": problems,
        "interpretation": (
            "Only PASS is completed strict positive verification; "
            "APPROXIMATE_REDUCED_BOUND is a separate opt-in, source-pinned "
            "process-distance certificate conditional on a correct native reduction. "
            "Inconclusive, skipped, or approximate cases must not be counted "
            "as strict-equivalence or complete release-baseline samples."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=ROOT / "test/_benchmark_cases.py")
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit(args.junit, args.catalog, require_complete=args.require_complete)
    except (OSError, ET.ParseError, ValueError, SyntaxError, KeyError) as exc:
        report = {"schema": "benchmark-outcome-evidence-v1", "status": "BLOCKED",
                  "problems": [f"could not validate JUnit evidence: {exc}"],
                  "expected": 32, "counts": {}}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown:
        counts = report.get("counts", {})
        lines = ["### Benchmark outcome coverage", "",
                 f"**{report['status']}** — {counts.get('PASS', 0)}/{report['expected']} completed; "
                 f"{counts.get('INCONCLUSIVE_RESOURCE', 0)} resource-inconclusive; "
                 f"{counts.get('SKIP', 0)} planned/other skipped; "
                 f"{counts.get(APPROXIMATE_REDUCED_BOUND, 0)} source-pinned approximate.", "",
                 "Only completed PASS cases constitute positive equivalence evidence."]
        if report.get("problems"):
            lines.extend(["", "Coverage blockers:"] + [f"- {p}" for p in report["problems"]])
        args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: report.get(k) for k in ("status", "expected", "counts", "problems")}, sort_keys=True))
    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())