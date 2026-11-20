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
        self.assertEqual(parsed.urls.count("playground/"), 2,
                         "Playground must be discoverable in top navigation and its card")
        self.assertIn('<a href="playground/">Playground</a>', html,
                      "Place the Playground entry in primary navigation")
        playground_card = re.search(
            r'<article class="card" data-index="02">(.*?)</article>', html, re.S
        )
        self.assertIsNotNone(playground_card, "Playground card must be present")
        card = playground_card.group(1)
        self.assertIn("<h3>Browser Playground</h3>", card,
                      "Use a plain heading consistent with other resource cards")
        self.assertIn('<a href="playground/">Open Browser Playground</a>', card)
        self.assertLess(
            card.index("local WebAssembly computation.</p>"),
            card.index('<a href="playground/">'),
            "The primary Playground link belongs below the description",
        )
        self.assertIn("Read the Playground guide", card)
        self.assertIn("https://github.com/PhysicsQoo/QuPRS/blob/main/docs/browser-workbench.md",
                      parsed.urls, "Keep the Playground guide available alongside the launch link")
        self.assertEqual(parsed.urls.count("https://doi.org/10.1007/978-3-032-22749-2_21"), 1,
                         "Homepage must link to the original peer-reviewed TACAS 2026 paper")
        self.assertIn("Equivalence Checking of Quantum Circuits via Path-Sum and Weighted Model Counting",
                      html)
        self.assertIn("TACAS", html)
        self.assertIn("hero-layout", html)
        self.assertIn("paper-feature", html)
        self.assertEqual(html.count(stager.REVISION_MARKER), 1)
        self.assertIn('<link rel="canonical" href="https://physicsqoo.github.io/QuPRS/">', html)
        self.assertNotIn("noindex", html.lower())
        self.assertEqual(html.count('<script id="quprsTheme">'), 1,
                         "Only the reviewed inline theme initializer is allowed")
        self.assertEqual(html.count("</script>"), 1)
        self.assertNotIn("<script src=", html.lower(),
                         "Homepage should not depend on a remote script")
        self.assertNotRegex(html, r"\b[A-Z]{2,8}-[0-9]{1,6}\b")

    def test_shared_light_dark_theme_contract(self) -> None:
        homepage = (SITE / "index.html").read_text(encoding="utf-8")
        playground = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        pattern = re.compile(r'<script id="quprsTheme">(.*?)</script>', re.S)
        homepage_theme = pattern.search(homepage)
        playground_theme = pattern.search(playground)
        self.assertIsNotNone(homepage_theme)
        self.assertIsNotNone(playground_theme)
        self.assertEqual(homepage_theme.group(1), playground_theme.group(1),
                         "Pages must use identical theme behavior and storage key")
        script = homepage_theme.group(1)
        self.assertIn("'quprs-theme'", script)
        self.assertIn("window.matchMedia('(prefers-color-scheme: dark)')", script)
        self.assertIn("window.localStorage.getItem(key)", script)
        self.assertIn("window.localStorage.setItem(key, next)", script)
        self.assertIn("document.addEventListener('DOMContentLoaded'", script)
        self.assertIn("system.addEventListener('change'", script)
        for page in (homepage, playground):
            self.assertEqual(page.count('id="themeToggle"'), 1)
            self.assertIn('aria-label="Switch to dark mode"', page)
            self.assertIn('data-theme="dark"', page if page is homepage else
                          (ROOT / "web" / "style.css").read_text(encoding="utf-8"))

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
