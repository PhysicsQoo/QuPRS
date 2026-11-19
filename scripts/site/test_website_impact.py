#!/usr/bin/env python3
"""Fail-closed routing fixtures for website-only and mixed changes."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).with_name("website-impact.py")
spec = importlib.util.spec_from_file_location("website_impact", source)
assert spec is not None and spec.loader is not None
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)

def selected(*paths: str) -> set[str]:
    return {key for key, value in routing.classify(list(paths)).items() if value}

class WebsiteImpactTests(unittest.TestCase):
    def test_homepage_does_not_recompile_gpmc_or_rustdoc(self) -> None:
        self.assertEqual(selected("website/index.html"), {"homepage"})
        self.assertEqual(selected("scripts/site/test_homepage.py"), {"homepage"})

    def test_browser_runs_full_differential_only_for_browser_changes(self) -> None:
        self.assertEqual(selected("web/worker.js"), {"browser"})
        self.assertEqual(selected("rust/web/src/lib.rs"), {"browser"})
        self.assertEqual(selected("rust/quprs/src/lib.rs"), {"browser", "docs_reference"})

    def test_documentation_routes_are_separate(self) -> None:
        self.assertEqual(selected("docs/site/index.md"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("mkdocs.yml"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("scripts/check_rust_api_docs.py"), {"docs_reference"})
        self.assertEqual(selected("scripts/check_docs_examples.py"), {"docs_fast"})
        self.assertEqual(selected(".github/scripts/test-docs-workflow-coverage.cjs"), {"docs_fast"})
        self.assertEqual(selected("src/QuPRS/utils/solver_adapter.py"), {"docs_fast"})
        self.assertEqual(selected(".github/workflows/docs-check.yml"), {"docs_fast"})
        self.assertEqual(selected("scripts/docs_versioning.py"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("scripts/rustdoc_version_selector.js"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("test/test_docs_rustdoc_versions.py"), {"docs_reference", "docs_version"})

    def test_shared_publication_stages_all_relevant_siblings(self) -> None:
        self.assertEqual(
            selected("scripts/site/stage-homepage.py"),
            {"homepage", "browser", "docs_version"},
        )
        self.assertEqual(
            selected("scripts/web/stage-pages.py"),
            {"homepage", "browser", "docs_version"},
        )

    def test_mixed_pr_unions_routing_without_duplicate_jobs(self) -> None:
        self.assertEqual(
            selected("website/index.html", "docs/site/index.md", "web/app.js"),
            {"homepage", "browser", "docs_reference", "docs_version"},
        )

    def test_ci_own_changes_force_full_gate(self) -> None:
        self.assertEqual(selected(".github/workflows/website-ci.yml"), set(routing.ROUTES))
        self.assertEqual(selected(".github/workflows/site-homepage-publish.yml"), set(routing.ROUTES))
        self.assertEqual(selected(".github/workflows/browser-workbench-publish.yml"), set(routing.ROUTES))
        self.assertEqual(selected(".github/workflows/website-publish.yml"), set(routing.ROUTES))
        self.assertEqual(selected("scripts/site/website-impact.py"), set(routing.ROUTES))

    def test_existing_pages_branch_publish_policy(self) -> None:
        # Keep publishing on the existing Pages branch without broadening
        # the configured github-pages Environment source restrictions.
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/website-publish.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("environment: site-publisher", workflow)
        self.assertNotIn("environment: github-pages", workflow)
        self.assertNotIn("QUPRS_SITE_PUBLISHER_READY", workflow)
        self.assertIn("GITHUB_EVENT_NAME", workflow)
        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("refs/heads/dev", workflow)
        self.assertIn("refs/heads/main", workflow)
        self.assertIn("group: quprs-gh-pages-publish", workflow)
        self.assertIn("git -C pages push origin HEAD:gh-pages", workflow)
        self.assertIn('gh api --method POST "repos/$GITHUB_REPOSITORY/pages/builds"', workflow)
        self.assertIn("source-sha.txt", workflow)
        self.assertIn("sha256sum", workflow)

    def test_no_changes_or_unsafe_paths_do_not_bypass(self) -> None:
        for paths in ([], ["../docs/site/index.md"], ["/absolute"], ["docs\\site\\index.md"]):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                routing.classify(paths)

    def test_unrelated_code_is_not_treated_as_website(self) -> None:
        self.assertEqual(selected("CHANGELOG.md"), set())
        self.assertEqual(selected("test/test_quantum.py"), set())

if __name__ == "__main__":
    unittest.main()
