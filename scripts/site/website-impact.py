#!/usr/bin/env python3
"""Classify an exact Git diff for Website CI. No GitHub API or third-party action."""
from __future__ import annotations

import argparse
import json
import subprocess

ROUTES = ("homepage", "browser", "docs_fast", "docs_version", "docs_reference")
ALL_GATE = {
    ".github/workflows/website-ci.yml",
    ".github/workflows/site-homepage-publish.yml",
    ".github/workflows/browser-workbench-publish.yml",
    "scripts/site/website-impact.py",
    "scripts/site/test_website_impact.py",
}
HOMEPAGE_WORKFLOW = ".github/workflows/site-homepage.yml"
BROWSER_WORKFLOW = ".github/workflows/browser-workbench.yml"
DOC_VERSION_WORKFLOW = ".github/workflows/docs-versioning-poc.yml"
DOC_REFERENCE_WORKFLOW = ".github/workflows/rust-api-docs.yml"
DOC_FAST_WORKFLOW = ".github/workflows/docs-check.yml"
DOC_FAST_FILES = {
    "scripts/check_generated_stub.py",
    "test/test_generated_stub_parity.py",
    "scripts/check_docs_examples.py",
    "scripts/check_docs_scoped_contract.py",
    "src/QuPRS/utils/solver_adapter.py",
    "src/QuPRS/utils/wmc_problem.py",
    ".github/scripts/test-docs-workflow-coverage.cjs",
    DOC_FAST_WORKFLOW,
}

DOC_REFERENCE_FILES = {
    "src/QuPRS/__init__.py",
    "src/QuPRS/interface/load_qiskit.py",
    "src/QuPRS/pathsum/core.py",
    "src/QuPRS/pathsum/core.pyi",
    "src/QuPRS/pathsum/__init__.py",
    "src/QuPRS/pathsum/statistics.py",
    "src/QuPRS/py.typed",
    "rust/Cargo.lock", "mkdocs.yml",
    "scripts/check_rust_api_docs.py",
    "scripts/stage_rust_crate_candidate.py",
    "scripts/check_docs_gate_stubs.py",
    "scripts/generate_stubs.py",
    "scripts/check_docs_site.py",
    "scripts/check_docs_science.py",
    "scripts/check_docs_visual.py",
    "scripts/check_docs_links.py",
    "scripts/docs_versioning.py",
    "scripts/rustdoc_version_selector.js",
    "test/test_docs_rustdoc_versions.py",
    "docs/requirements-site.txt",
    "docs/requirements-versioned.txt",
    DOC_REFERENCE_WORKFLOW,
}
DOC_VERSION_FILES = {
    "scripts/docs_versioning.py",
    "scripts/check_docs_version_browser.py",
    "scripts/check_docs_links.py",
    "scripts/rustdoc_version_selector.js",
    "test/test_docs_rustdoc_versions.py",
    "docs/requirements-versioned.txt",
    "test/test_docs_auto_publication.py",
    "mkdocs.yml",
    ".github/workflows/docs-release-publish.yml",
    DOC_VERSION_WORKFLOW,
}

def classify(paths: list[str]) -> dict[str, bool]:
    result = {key: False for key in ROUTES}
    if not paths:
        raise ValueError("No changed files; cannot establish website CI scope")
    for path in paths:
        if (not path or path.startswith("/") or "\\" in path or
                any(segment in {".", ".."} for segment in path.split("/"))):
            raise ValueError(f"Unsafe changed path: {path!r}")
        if path in ALL_GATE:
            return {key: True for key in ROUTES}
        if path == HOMEPAGE_WORKFLOW or path.startswith(("website/", "scripts/site/")):
            result["homepage"] = True
        if path == BROWSER_WORKFLOW or path.startswith(("rust/", "web/", "scripts/web/")):
            result["browser"] = True
        if (path == DOC_REFERENCE_WORKFLOW or path in DOC_REFERENCE_FILES or
                path.startswith(("docs/site/", "rust/quprs/", "src/QuPRS/pathsum/gates/"))):
            result["docs_reference"] = True
        if path in DOC_FAST_FILES:
            result["docs_fast"] = True
        if path in DOC_VERSION_FILES or path.startswith("docs/site/"):
            result["docs_version"] = True
        # Shared publication boundary changes must exercise sibling isolation.
        if path in {
            "scripts/site/stage-homepage.py",
            "scripts/web/stage-pages.py",
            ".github/workflows/docs-release-publish.yml",
        }:
            result["homepage"] = True
            result["browser"] = True
            result["docs_version"] = True
        # The existing Rustdoc workflow also owns the PR preview publisher.
        if path == DOC_REFERENCE_WORKFLOW:
            result["docs_version"] = True
    return result


def git_changed(base: str, head: str) -> list[str]:
    for sha in (base, head):
        if len(sha) != 40 or any(c not in "0123456789abcdefABCDEF" for c in sha):
            raise ValueError("Expected full commit SHAs for the PR base and head")
    merge_base = subprocess.check_output(
        ["git", "merge-base", base, head], text=True
    ).strip()
    data = subprocess.check_output(["git", "diff", "--name-only", "-z", merge_base, head])
    return sorted(p.decode("utf-8") for p in data.split(b"\0") if p)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--github-output", required=True)
    a = p.parse_args()
    paths = git_changed(a.base, a.head)
    result = classify(paths)
    with open(a.github_output, "a", encoding="utf-8") as output:
        for key, value in result.items():
            output.write(f"{key}={'true' if value else 'false'}\n")
    print(json.dumps({"paths": paths, "routes": result}, indent=2))


if __name__ == "__main__":
    main()
