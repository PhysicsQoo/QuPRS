#!/usr/bin/env python3
"""Validate the published documentation inputs and generated site."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "site"
EXPECTED_PAGES = (
    "index.html",
    "getting-started/index.html",
    "verification/index.html",
    "theory/index.html",
    "reference/index.html",
)
ALLOWED_SUFFIXES = {".md", ".js"}
PRIVATE_TRACKER_KEY = re.compile(r"\b[A-Z]{2,8}-[0-9]{1,6}\b")
PRIVATE_LINK = re.compile(r"https?://(?:www\.)?linear\.app/|github\.com/PhysicsQoo/obsidian(?:/|\b)", re.I)


def check_sources() -> None:
    paths = [p for p in DOCS_DIR.rglob("*") if p.is_file()]
    if not paths:
        raise AssertionError("Documentation source tree is empty")
    for path in paths:
        if path.is_symlink():
            raise AssertionError(f"Documentation symlink is not allowed: {path}")
        if path.suffix not in ALLOWED_SUFFIXES:
            raise AssertionError(f"Unexpected site source file: {path}")
        content = path.read_text(encoding="utf-8")
        if PRIVATE_TRACKER_KEY.search(content) or PRIVATE_LINK.search(content):
            raise AssertionError(f"Non-public reference in documentation source: {path}")


def verify_site(site_dir: Path) -> None:
    for relative in EXPECTED_PAGES:
        path = site_dir / relative
        if not path.is_file():
            raise AssertionError(f"Missing generated page: {path}")
        if "<html" not in path.read_text(encoding="utf-8").lower():
            raise AssertionError(f"Invalid generated HTML: {path}")
    theory = (site_dir / "theory" / "index.html").read_text(encoding="utf-8")
    if "arithmatex" not in theory:
        raise AssertionError("Mathematical expressions were not emitted")
    if not (site_dir / "javascripts" / "mathjax.js").is_file():
        raise AssertionError("MathJax configuration was not included")
    for path in site_dir.rglob("*.html"):
        content = path.read_text(encoding="utf-8")
        if PRIVATE_TRACKER_KEY.search(content) or PRIVATE_LINK.search(content):
            raise AssertionError(f"Non-public reference in generated HTML: {path}")


def negative_link_test() -> None:
    with tempfile.TemporaryDirectory(prefix="quprs-doc-links-") as directory:
        folder = Path(directory)
        (folder / "docs").mkdir()
        (folder / "docs" / "index.md").write_text(
            "# Link check\n\n[Missing page](does-not-exist.md)\n", encoding="utf-8"
        )
        (folder / "mkdocs.yml").write_text(
            "site_name: Link check\n"
            "docs_dir: docs\nsite_dir: site\n"
            "theme:\n  name: material\nnav:\n  - Home: index.md\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["zensical", "build", "--strict", "--clean", "-f", "mkdocs.yml"],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            raise AssertionError("Strict documentation build accepted a broken link")
        if "page does not exist" not in output or "index.md" not in output:
            raise AssertionError(
                "Negative link test failed for a reason unrelated to the missing page:\n"
                + output[-3000:]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--site", action="store_true")
    parser.add_argument("--negative-link-test", action="store_true")
    args = parser.parse_args()
    if not any((args.sources, args.site, args.negative_link_test)):
        parser.error("select at least one check")
    if args.sources:
        check_sources()
    if args.site:
        verify_site(ROOT / "site")
    if args.negative_link_test:
        negative_link_test()


if __name__ == "__main__":
    main()
