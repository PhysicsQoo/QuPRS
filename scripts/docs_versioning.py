#!/usr/bin/env python3
"""Prepare and audit source-accurate, isolated Zensical/mike documentation.

A release must be built from a tag that actually contains its documentation.
This script never publishes, pushes, or promotes a stable alias.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SITE_ORIGIN = "https://physicsqoo.github.io/QuPRS/docs/"
SEMVER = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
SHA = re.compile(r"[0-9a-f]{40}$")
NECESSARY_SOURCES = (
    "mkdocs.yml",
    "docs/requirements-site.txt",
    "docs/site/index.md",
    "docs/site/python-api.md",
    "docs/site/reference.md",
    "scripts/check_rust_api_docs.py",
    "rust/pathsum/Cargo.toml",
)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False,
        timeout=30,
    )


def check_release_tag(tag: str) -> str:
    if not SEMVER.fullmatch(tag):
        raise AssertionError(f"Not a semver-style release tag: {tag}")
    resolved = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    if resolved.returncode or not SHA.fullmatch(resolved.stdout.strip()):
        raise AssertionError(f"Release tag missing or invalid: {tag}")
    missing = []
    for filename in NECESSARY_SOURCES:
        found = git("cat-file", "-e", f"refs/tags/{tag}:{filename}")
        if found.returncode:
            missing.append(filename)
    if missing:
        raise AssertionError(
            f"{tag} predates versioned documentation; cannot publish "
            f"current development docs as this historical release: {missing}"
        )
    return resolved.stdout.strip()


def create_config(output: Path, ref: str) -> None:
    if ref != "dev" and not SEMVER.fullmatch(ref):
        raise AssertionError(f"Invalid source ref: {ref}")
    source = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    anchor = "  - mkdocstrings:"
    if source.count(anchor) != 1 or "\nextra:\n" in source:
        raise AssertionError("Unsupported mkdocs.yml layout; review versioning config")
    source = source.replace(
        anchor,
        "  - mike:\n"
        "      alias_type: redirect\n"
        "      deploy_prefix: docs\n"
        "      version_selector: true\n"
        + anchor,
    )
    source = source.replace(
        "edit_uri: edit/dev/docs/site/",
        f"edit_uri: blob/{ref}/docs/site/",
    )
    source += (
        "\nsite_url: " + SITE_ORIGIN + "\n"
        "extra:\n"
        "  version:\n"
        "    provider: mike\n"
        "    default: stable\n"
        "    alias: true\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    print(f"Versioned config created: {output} (source={ref}, prefix=docs)")


def check_local_layout(root: Path, expected: tuple[str, ...]) -> None:
    folder = root / "docs"
    if not folder.is_dir():
        raise AssertionError("Isolated docs/ prefix missing")
    for version in expected:
        if not re.fullmatch(r"dev|v[0-9]+\.[0-9]+\.[0-9]+(?:-test)?|stable", version):
            raise AssertionError(f"Unsafe version: {version}")
        for name in ("index.html", "python-api/index.html", "reference/index.html"):
            target = folder / version / name
            if not target.is_file():
                raise AssertionError(f"Missing versioned source page: {target}")
    candidates = [folder / "versions.json", root / "versions.json"]
    found = next((p for p in candidates if p.is_file()), None)
    if found is None:
        raise AssertionError("mike did not emit versions.json")
    versions = json.loads(found.read_text(encoding="utf-8"))
    if not isinstance(versions, list):
        raise AssertionError("Invalid versions.json")
    names = {entry.get("version") for entry in versions}
    for version in expected:
        if version != "stable" and version not in names:
            raise AssertionError(f"Missing mike version selector entry: {version}")
    if (root / "pr-preview").is_dir() and not (root / "index.html").is_file():
        raise AssertionError("Versioning removed the existing Pages root index")
    print(f"Versioned layout PASS: {', '.join(expected)}; {found}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("config")
    p.add_argument("--ref", required=True)
    p.add_argument("--output", default="mkdocs.versioned.yml")
    p = sub.add_parser("check-release")
    p.add_argument("tag")
    p = sub.add_parser("assert-historical-unavailable")
    p.add_argument("tag")
    p = sub.add_parser("check-layout")
    p.add_argument("--pages", required=True)
    p.add_argument("--versions", nargs="+", required=True)
    a = parser.parse_args()
    if a.command == "config":
        create_config(ROOT / a.output, a.ref)
    elif a.command == "check-release":
        print(f"Release document sources PASS: {a.tag} -> {check_release_tag(a.tag)}")
    elif a.command == "assert-historical-unavailable":
        try:
            check_release_tag(a.tag)
        except AssertionError as error:
            if "predates versioned documentation" not in str(error):
                raise
            print(f"Historical tag correctly excluded from stable docs: {a.tag}")
        else:
            raise AssertionError(f"Historical tag unexpectedly eligible: {a.tag}")
    elif a.command == "check-layout":
        check_local_layout(Path(a.pages), tuple(a.versions))


if __name__ == "__main__":
    main()
