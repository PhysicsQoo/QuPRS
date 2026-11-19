#!/usr/bin/env python3
"""Homepage publication contract, including adversarial staging cases."""
from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "website"
REVISION = "a" * 40
spec = importlib.util.spec_from_file_location("homepage_stager", Path(__file__).with_name("stage-homepage.py"))
assert spec is not None and spec.loader is not None
stager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stager)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "a" and props.get("href"):
            self.urls.append(props["href"])


class HomepageTests(unittest.TestCase):
    def test_public_entry_contract(self) -> None:
        html = (SITE / "index.html").read_text(encoding="utf-8")
        parsed = Links()
        parsed.feed(html)
        self.assertIn("docs/", parsed.urls)
        self.assertIn("https://github.com/PhysicsQoo/QuPRS", parsed.urls)
        self.assertIn("https://pypi.org/project/QuPRS/", parsed.urls)
        self.assertIn("https://crates.io/crates/quprs", parsed.urls)
        self.assertIn("docs/stable/rust-api/quprs/", parsed.urls,
                      "Homepage must link to the existing stable Rustdoc")
        self.assertFalse(any("pr-preview/" in url for url in parsed.urls),
                         "Internal PR previews must not appear on the public homepage")
        self.assertNotIn("playground/", parsed.urls, "Unpublished Playground must not be a live link")
        self.assertIn("https://github.com/PhysicsQoo/QuPRS/blob/main/docs/browser-workbench.md",
                      parsed.urls, "A useful Playground guide must remain clickable before deployment")
        self.assertEqual(html.count(stager.REVISION_MARKER), 1)
        self.assertIn('<link rel="canonical" href="https://physicsqoo.github.io/QuPRS/">', html)
        self.assertNotIn("noindex", html.lower())
        self.assertNotIn("<script", html.lower())
        self.assertNotRegex(html, r"\b[A-Z]{2,8}-[0-9]{1,6}\b")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="quprs-homepage-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "source"
        self.source.mkdir()
        (self.source / "index.html").write_text(
            (SITE / "index.html").read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.pages = self.folder / "pages"
        self.pages.mkdir()
        subprocess.run(["git", "init", "-q", str(self.pages)], check=True)
        for name in (
            "index.html", "docs/stable/index.html", "docs/dev/index.html",
            "docs/stable/rust-api/quprs/index.html",
            "playground/index.html", "pr-preview/pr-17/index.html",
            ".nojekyll", "CNAME",
        ):
            file = self.pages / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("retain:" + name, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.pages), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.pages), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Initial"],
            check=True,
        )

    def test_stage_changes_only_root_index(self) -> None:
        before = {
            f.relative_to(self.pages): f.read_bytes()
            for f in self.pages.rglob("*")
            if f.is_file() and ".git" not in f.parts
        }
        self.assertEqual(stager.stage(self.source, self.pages, REVISION), ["index.html"])
        modified = subprocess.check_output(
            ["git", "-C", str(self.pages), "diff", "--cached", "--name-only"],
            text=True,
        ).splitlines()
        self.assertEqual(modified, ["index.html"])
        self.assertIn(REVISION, (self.pages / "index.html").read_text(encoding="utf-8"))
        for name, contents in before.items():
            if str(name) != "index.html":
                self.assertEqual((self.pages / name).read_bytes(), contents, str(name))

    def test_reject_preexisting_staged_changes(self) -> None:
        subprocess.run(["git", "-C", str(self.pages), "rm", "-q", ".nojekyll"], check=True)
        with self.assertRaisesRegex(ValueError, "Unrelated staged"):
            stager.stage(self.source, self.pages, REVISION)
        self.assertEqual((self.pages / "index.html").read_text(), "retain:index.html")

    def test_reject_symlink_destination(self) -> None:
        (self.pages / "index.html").unlink()
        (self.pages / "index.html").symlink_to(self.source / "index.html")
        with self.assertRaisesRegex(ValueError, "symlink"):
            stager.stage(self.source, self.pages, REVISION)

    def test_reject_invalid_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "source commit SHA"):
            stager.stage(self.source, self.pages, "unverified")

    def test_reject_missing_revision_marker(self) -> None:
        (self.source / "index.html").write_text(
            (self.source / "index.html").read_text().replace(stager.REVISION_MARKER, "lost")
        )
        with self.assertRaisesRegex(ValueError, "source revision marker"):
            stager.stage(self.source, self.pages, REVISION)


if __name__ == "__main__":
    unittest.main()
