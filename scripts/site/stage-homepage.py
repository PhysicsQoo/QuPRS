#!/usr/bin/env python3
"""Stage exactly the homepage index in an existing gh-pages worktree."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REVISION_MARKER = "__SOURCE_REVISION__"


def run_git(checkout: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(checkout), *args], text=True
    ).strip()


def stage(source: Path, checkout: Path, revision: str) -> list[str]:
    source = source.resolve(strict=True)
    checkout = checkout.resolve(strict=True)
    entry = source / "index.html"
    destination = checkout / "index.html"
    if not re.fullmatch(r"[a-fA-F0-9]{40}", revision):
        raise ValueError("Expected a full source commit SHA")
    if not entry.is_file() or entry.is_symlink():
        raise ValueError("Missing or symlinked source homepage")
    if not (checkout / ".git").exists() or destination.is_symlink():
        raise ValueError("Expected an existing non-symlink gh-pages worktree")
    if not destination.is_file():
        raise ValueError("Expected an existing root index.html")
    if run_git(checkout, "ls-files", "--", "index.html") != "index.html":
        raise ValueError("Root index.html must already be tracked")
    if run_git(checkout, "diff", "--cached", "--name-only"):
        raise ValueError("Unrelated staged changes are not allowed")
    html = entry.read_text(encoding="utf-8")
    if html.count(REVISION_MARKER) != 1:
        raise ValueError("Expected exactly one source revision marker")
    if 'rel="canonical" href="https://physicsqoo.github.io/QuPRS/"' not in html:
        raise ValueError("Unexpected canonical homepage URL")
    if "noindex" in html.lower():
        raise ValueError("Public homepage must not contain noindex")
    destination.write_text(html.replace(REVISION_MARKER, revision), encoding="utf-8")
    subprocess.run(["git", "-C", str(checkout), "add", "--", "index.html"], check=True)
    changed = run_git(checkout, "diff", "--cached", "--name-only").splitlines()
    if changed not in ([], ["index.html"]):
        raise ValueError("Refusing staged changes outside root index.html")
    subprocess.run(["git", "-C", str(checkout), "diff", "--cached", "--check"], check=True)
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: stage-homepage.py SOURCE_DIR PAGES_CHECKOUT SOURCE_SHA")
    print(stage(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
