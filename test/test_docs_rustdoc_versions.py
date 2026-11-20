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
        self.head = ROOT / "scripts" / "rustdoc_quprs_head.html"
        self.selector = ROOT / "scripts" / "rustdoc_version_selector.js"
        self.css = ROOT / "scripts" / "rustdoc_navigation.css"
        self.build = ROOT / "scripts" / "build-rustdoc.sh"
        head = self.head.read_text(encoding="utf-8")
        for page in (self.root_page, self.nested_page):
            page.write_text(
                '<!doctype html><html><head><title>quprs</title>' + head +
                '</head><body><rustdoc-topbar></rustdoc-topbar><main></main></body></html>',
                encoding="utf-8",
            )

    def test_native_pages_remain_byte_identical_after_asset_staging(self):
        original = (self.root_page.read_bytes(), self.nested_page.read_bytes())
        self.assertEqual(module.inject_rustdoc_version_navigation(self.staged, self.selector), 2)
        self.assertEqual((self.root_page.read_bytes(), self.nested_page.read_bytes()), original)
        self.assertEqual(
            (self.staged / "quprs-versions.js").read_bytes(), self.selector.read_bytes()
        )
        self.assertEqual(module.inject_rustdoc_version_navigation(self.staged, self.selector), 2)
        self.assertEqual((self.root_page.read_bytes(), self.nested_page.read_bytes()), original)

    def test_official_rustdoc_extension_flags_are_source_controlled(self):
        build = self.build.read_text(encoding="utf-8")
        self.assertIn("cargo rustdoc --locked", build)
        self.assertIn('--html-in-header "$root/scripts/rustdoc_quprs_head.html"', build)
        self.assertIn('--extend-css "$root/scripts/rustdoc_navigation.css"', build)
        self.assertIn('data-quprs-version-selector="true"', self.head.read_text())
        self.assertIn(".quprs-version-switcher", self.css.read_text())
        for workflow in ("rust-api-docs.yml", "docs-versioning-poc.yml",
                         "docs-release-publish.yml"):
            source = (ROOT / ".github" / "workflows" / workflow).read_text()
            self.assertIn("bash scripts/build-rustdoc.sh", source)

    def test_reject_missing_or_unreviewed_html_header(self):
        self.nested_page.write_text("<html><head><title>missing</title></head></html>")
        with self.assertRaisesRegex(AssertionError, "Missing or unreviewed"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)
        self.nested_page.write_text("<html><body>missing head</body></html>")
        with self.assertRaisesRegex(AssertionError, "Invalid Rustdoc head"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)

    def test_reject_duplicate_or_untrusted_script_marker(self):
        marker = '<script data-quprs-version-selector="true"></script>'
        self.root_page.write_text(
            "<html><head>" + marker + marker + "</head></html>"
        )
        with self.assertRaisesRegex(AssertionError, "Missing or unreviewed"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)
        self.root_page.write_text(
            '<html><head><script src="https://untrusted.invalid/script.js" '
            'data-quprs-version-selector="true"></script></head></html>'
        )
        with self.assertRaisesRegex(AssertionError, "Missing or unreviewed"):
            module.inject_rustdoc_version_navigation(self.staged, self.selector)

    def test_native_rustdoc_redirect_needs_no_header_extension(self):
        redirect = (
            '<!DOCTYPE html><html lang="en"><head>'
            '<meta http-equiv="refresh" content="0;URL=../../quprs/struct.ExclusiveLedger.html">'
            '<title>Redirection</title></head><body>'
            '<script>location.replace("../../quprs/struct.ExclusiveLedger.html")</script>'
            '</body></html>'
        )
        self.nested_page.write_text(redirect, encoding="utf-8")
        self.assertEqual(module.inject_rustdoc_version_navigation(self.staged, self.selector), 2)
        self.assertEqual(self.nested_page.read_text(encoding="utf-8"), redirect)

    def test_reject_rustdoc_redirect_outside_source_tree(self):
        self.nested_page.write_text(
            '<html><head><meta http-equiv="refresh" content="0;URL=https://evil.invalid/">'
            '<title>Redirection</title></head><body>'
            '<script>location.replace("https://evil.invalid/")</script></body></html>',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(AssertionError, "Unsafe native Rustdoc redirect"):
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
