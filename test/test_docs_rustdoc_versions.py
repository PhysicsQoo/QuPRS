"""Native Rustdoc cross-version navigation: injection and negative contracts."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "docs_versioning", ROOT / "scripts" / "docs_versioning.py"
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RustdocVersionNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="quprs-rustdoc-navigation-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.staged = self.root / "rust-api"
        self.crate = self.staged / "quprs"
        (self.crate / "nested").mkdir(parents=True)
        self.root_page = self.crate / "index.html"
        self.nested_page = self.crate / "nested" / "struct.Sample.html"
        self.root_page.write_text(
            '<!doctype html><html><head><title>quprs</title></head>'
            '<body><rustdoc-topbar></rustdoc-topbar></body></html>', encoding="utf-8"
        )
        self.nested_page.write_text(
            '<!doctype html><html><head><title>Sample</title></head>'
            '<body><rustdoc-topbar></rustdoc-topbar></body></html>', encoding="utf-8"
        )
        self.selector = ROOT / "scripts" / "rustdoc_version_selector.js"

    def test_native_pages_share_one_relative_selector(self):
        self.assertEqual(module.inject_rustdoc_version_navigation(self.staged, self.selector), 2)
        self.assertIn(
            '<script defer src="../quprs-versions.js" data-quprs-version-selector="true"></script>',
            self.root_page.read_text(encoding="utf-8")
        )
        self.assertIn(
            '<script defer src="../../quprs-versions.js" data-quprs-version-selector="true"></script>',
            self.nested_page.read_text(encoding="utf-8")
        )
        self.assertEqual(
            (self.staged / "quprs-versions.js").read_bytes(), self.selector.read_bytes()
        )
        self.assertEqual(module.inject_rustdoc_version_navigation(self.staged, self.selector), 2)
        self.assertEqual(
            self.root_page.read_text().count('data-quprs-version-selector="true"'), 1
        )
        self.assertEqual(
            self.nested_page.read_text().count('data-quprs-version-selector="true"'), 1
        )

    def test_reject_bad_html_before_accepting_native_docs(self):
        self.nested_page.write_text("<html><body>no head</body></html>")
        with self.assertRaisesRegex(AssertionError, "Invalid Rustdoc head"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)

    def test_reject_multiple_or_mismatched_existing_scripts(self):
        self.root_page.write_text(
            '<html><head><script defer src="https://untrusted.invalid/widget.js" '
            'data-quprs-version-selector="true"></script></head><body></body></html>'
        )
        with self.assertRaisesRegex(AssertionError, "Unreviewed Rustdoc selector"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)

    def test_reject_symlink_source(self):
        alias = self.root / "untrusted.js"
        alias.symlink_to(self.selector)
        with self.assertRaisesRegex(AssertionError, "symlinked"):
            module.inject_rustdoc_version_navigation(self.staged, alias)

    def test_initializer_checks_navigation_not_script_marker(self):
        script = self.selector.read_text(encoding="utf-8")
        self.assertIn('querySelector("nav[data-quprs-version-selector]")', script)
        self.assertNotIn('querySelector("[data-quprs-version-selector]")', script)
        self.assertIn('bar.setAttribute("data-quprs-version-selector", "")', script)

    def test_selector_does_not_create_a_desktop_flex_column(self):
        script = self.selector.read_text(encoding="utf-8")
        self.assertIn('const main = document.querySelector("main");', script)
        self.assertIn("main.insertBefore(bar, main.firstChild);", script)
        self.assertNotIn('topbar.insertAdjacentElement("afterend", bar)', script)
        self.assertNotIn('document.body.insertBefore(bar', script)
        for link in ('"/QuPRS/"', '"/QuPRS/playground/"', '"Documentation"'):
            self.assertIn(link, script)

    def test_isolated_preview_does_not_request_live_manifest(self):
        script = self.selector.read_text(encoding="utf-8")
        self.assertIn('if (preview) {', script)
        self.assertIn('option("preview", "PR preview", true);', script)
        self.assertLess(
            script.index('option("preview", "PR preview", true);'),
            script.index('fetch(docsPrefix + "versions.json"'),
        )
        self.assertIn('nav[data-quprs-version-selector]', script)

    def test_missing_reference_fails_closed(self):
        self.root_page.unlink()
        with self.assertRaisesRegex(AssertionError, "Missing staged"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)


if __name__ == "__main__":
    unittest.main()
