#!/usr/bin/env python3
"""Fail closed if release validation and tag publishing build/smoke jobs drift.

Only the release publisher's publishing job may differ from the reusable
read-only candidate validation workflow. No YAML package dependency required.
"""
from __future__ import annotations

import difflib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/release-artifact-ci.yml"
PUBLISH = ROOT / ".github/workflows/python-publish.yml"
PUBLISH_SECTION = "\n  # --- Job 3: Publish to PyPI"


def normalized_parts(reusable: str, release: str) -> tuple[str, str]:
    if reusable.count("\njobs:\n") != 1 or release.count("\njobs:\n") != 1:
        raise ValueError("Missing or duplicate jobs blocks")
    if release.count(PUBLISH_SECTION) != 1:
        raise ValueError("Missing or duplicate publishing boundary")
    a = "jobs:\n" + reusable.split("\njobs:\n", 1)[1]
    b = "jobs:\n" + release.split("\njobs:\n", 1)[1].split(PUBLISH_SECTION, 1)[0]
    return a.rstrip(), b.rstrip()


def equal_jobs(reusable: str, release: str) -> bool:
    return normalized_parts(reusable, release)[0] == normalized_parts(reusable, release)[1]


def main() -> None:
    reusable, release = CI.read_text(), PUBLISH.read_text()
    first, second = normalized_parts(reusable, release)
    if "--self-test" in sys.argv:
        assert first == second, "Current sources already drifted"
        assert not equal_jobs(reusable.replace("Build source distribution", "BAD BUILD NAME"), release), (
            "Negative mutation was not detected"
        )
        print("Parity negative mutation check PASS")
        return
    if first != second:
        diff = difflib.unified_diff(
            second.splitlines(), first.splitlines(), fromfile="tag-publisher",
            tofile="release-candidate", lineterm=""
        )
        raise SystemExit("Release Artifact workflow drift detected:\n" + "\n".join(diff))
    print("PASS: wheel/sdist build+installed smoke jobs exactly match tagged publisher")


if __name__ == "__main__":
    main()
