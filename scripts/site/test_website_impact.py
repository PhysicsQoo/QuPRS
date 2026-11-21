#!/usr/bin/env python3
"""Fail-closed routing fixtures for website-only and mixed changes."""
from __future__ import annotations

import importlib.util
from fnmatch import fnmatchcase
from pathlib import Path
import re
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
        self.assertEqual(selected("scripts/build-rustdoc.sh"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("scripts/rustdoc_quprs_head.html"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("scripts/rustdoc_navigation.css"), {"docs_reference", "docs_version"})
        self.assertEqual(selected("docs/requirements-site.txt"), {"docs_reference", "docs_version"})

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

    def test_independent_edits_route_to_exact_ci_and_dev_publish_jobs(self) -> None:
        """Exercise real event filters and job gates, not just classifier results."""
        root = Path(__file__).resolve().parents[2] / ".github" / "workflows"
        ci = (root / "website-ci.yml").read_text(encoding="utf-8")
        dev = (root / "website-deploy.yml").read_text(encoding="utf-8")

        def event_paths(workflow: str, event: str) -> list[str]:
            lines = workflow.splitlines()
            self.assertIn(f"  {event}:", lines)
            patterns = []
            in_paths = False
            for line in lines[lines.index(f"  {event}:") + 1:]:
                if line and not line.startswith(" "):
                    break
                if line.startswith("  ") and not line.startswith("    "):
                    break
                if line == "    paths:":
                    in_paths = True
                elif in_paths and line.startswith("      - '") and line.endswith("'"):
                    patterns.append(line[len("      - '"):-1])
                elif in_paths and line.startswith("    ") and not line.startswith("      "):
                    break
            self.assertTrue(patterns, f"Missing {event} path filters")
            return patterns

        def job_block(workflow: str, job: str) -> str:
            match = re.search(
                rf"(?ms)^  {re.escape(job)}:\\n(.*?)(?=^  [a-z][a-z-]*:\\n|\\Z)",
                workflow,
            )
            self.assertIsNotNone(match, f"Missing job: {job}")
            assert match is not None
            return match.group(1)

        # The PR gate runs validation; dev push is the only auto-publisher.
        ci_lanes = {
            "homepage": ("homepage", "site-homepage.yml"),
            "browser": ("browser", "browser-workbench.yml"),
            "docs_fast": ("docs-fast", "docs-check.yml"),
            "docs_version": ("docs-version", "docs-versioning-poc.yml"),
            "docs_reference": ("docs-reference", "rust-api-docs.yml"),
        }
        dev_lanes = {
            "homepage": ("homepage", "website-publish.yml", "target: homepage"),
            "browser": ("playground", "website-publish.yml", "target: playground"),
            "docs_reference": ("docs-dev", "rust-api-docs.yml", ""),
        }
        for workflow, lanes in ((ci, ci_lanes), (dev, dev_lanes)):
            for route, (job, called, *markers) in lanes.items():
                with self.subTest(workflow="ci" if workflow == ci else "dev", lane=job):
                    block = job_block(workflow, job)
                    self.assertIn(
                        f"if: needs.impact.outputs.{route} == 'true'", block
                    )
                    self.assertIn(f"uses: ./.github/workflows/{called}", block)
                    for marker in markers:
                        if marker:
                            self.assertIn(marker, block)

        ci_paths = event_paths(ci, "pull_request")
        dev_paths = event_paths(dev, "push")
        cases = (
            ("homepage HTML", "website/index.html", {"homepage"}, {"homepage"}),
            ("homepage validation", "scripts/site/test_homepage.py", {"homepage"}, {"homepage"}),
            ("Playground frontend", "web/worker.js", {"browser"}, {"playground"}),
            ("Playground Rust adapter", "rust/web/src/lib.rs", {"browser"}, {"playground"}),
            ("Docs content", "docs/site/index.md",
             {"docs_reference", "docs_version"}, {"docs-dev"}),
            ("Docs API", "scripts/check_rust_api_docs.py",
             {"docs_reference"}, {"docs-dev"}),
        )
        for label, path, expected_routes, expected_publishers in cases:
            with self.subTest(change=label, path=path):
                self.assertTrue(any(fnmatchcase(path, p) for p in ci_paths),
                                f"PR trigger misses {path}")
                self.assertTrue(any(fnmatchcase(path, p) for p in dev_paths),
                                f"dev-push trigger misses {path}")
                routes = selected(path)
                self.assertEqual(routes, expected_routes)
                self.assertEqual(
                    {job for route, (job, _) in ci_lanes.items() if route in routes},
                    {job for route, (job, _) in ci_lanes.items()
                     if route in expected_routes},
                )
                self.assertEqual(
                    {job for route, (job, _, _) in dev_lanes.items() if route in routes},
                    expected_publishers,
                    f"Unexpected dev publisher for independent {label} edit",
                )

    def test_ci_own_changes_force_full_gate(self) -> None:
        self.assertEqual(selected(".github/workflows/website-ci.yml"), set(routing.ROUTES))
        self.assertEqual(selected(".github/workflows/website-deploy.yml"), set(routing.ROUTES))
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
        self.assertIn("Automatic publication is allowed only from dev", workflow)
        self.assertIn("Untrusted website publication event", workflow)
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/$branch"', workflow)
        self.assertIn('if [[ "$latest" != "$GITHUB_SHA" ]]', workflow)
        adapter = (root / ".github/workflows/website-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("  push:\n    branches: [dev]", adapter)
        self.assertIn("uses: ./.github/workflows/website-publish.yml", adapter)
        self.assertIn("uses: ./.github/workflows/rust-api-docs.yml", adapter)
        self.assertIn("target: playground", adapter)
        self.assertIn("target: homepage", adapter)
        self.assertIn("group: quprs-gh-pages-publish", workflow)
        self.assertIn("git -C pages push origin HEAD:gh-pages", workflow)
        self.assertIn('gh api --method POST "repos/$GITHUB_REPOSITORY/pages/builds"', workflow)
        self.assertIn("source-sha.txt", workflow)
        self.assertIn("sha256sum", workflow)

    def test_rust_source_dev_rebuild_and_immutable_stable_contract(self) -> None:
        """A Rust code edit must rebuild the real WASM for dev, never overwrite stable."""
        root = Path(__file__).resolve().parents[2]
        workflows = root / ".github/workflows"
        publisher = (workflows / "website-deploy.yml").read_text(encoding="utf-8")
        builder = (workflows / "browser-workbench.yml").read_text(encoding="utf-8")
        shared = (workflows / "website-publish.yml").read_text(encoding="utf-8")
        release = (workflows / "docs-release-publish.yml").read_text(encoding="utf-8")
        # These trigger paths cover the actual Rust core and WebAssembly adapter,
        # while unrelated Python-only/native CLI edits need not rebuild the counter.
        for pattern in ("rust/quprs/**", "rust/web/**", "rust/Cargo.toml",
                        "rust/Cargo.lock", "web/**", "scripts/web/**"):
            self.assertIn("'" + pattern + "'", publisher)
        self.assertNotIn("\n  push:\n", builder,
                         "The publisher is the only dev-push Browser build owner")
        self.assertIn("  workflow_call:\n", builder)
        self.assertIn("branches: [dev]", publisher)
        self.assertIn("uses: ./.github/workflows/website-publish.yml", publisher)
        self.assertIn("target: playground", publisher)
        self.assertIn("cargo build --locked", builder)
        self.assertIn("--target wasm32-unknown-unknown -p quprs-web", builder)
        self.assertIn("wasm-bindgen rust/target/wasm32-unknown-unknown", builder)
        self.assertIn("bash scripts/web/build-counter.sh", builder)
        self.assertIn("Actual browser and native differential checks", builder)
        self.assertIn("source-sha.txt", builder)
        self.assertIn("test \"$(tr -d", shared)
        self.assertIn("scripts/web/stage-versioned-pages.py dev", shared.replace("source/", ""))
        self.assertIn("playground/dev", shared)
        self.assertIn("sha256sum", shared)
        self.assertIn("Publish immutable release and stable alias", shared)
        self.assertIn("signed", release.lower())
        self.assertIn("playground-stable", release)
        self.assertNotIn("environment: github-pages", publisher)
        self.assertNotIn("environment: github-pages", shared)

    def test_single_dev_push_owner_per_site_subsystem(self) -> None:
        """Read-only PR validators must not repeat protected dev publishing jobs."""
        root = Path(__file__).resolve().parents[2] / ".github" / "workflows"
        names = (
            "browser-workbench.yml", "site-homepage.yml",
            "docs-check.yml", "docs-examples.yml",
            "website-deploy.yml", "rust-api-docs.yml",
            "website-ci.yml",
        )
        sources = {name: (root / name).read_text(encoding="utf-8") for name in names}
        browser = sources["browser-workbench.yml"]
        homepage = sources["site-homepage.yml"]
        docs_fast = sources["docs-check.yml"]
        examples = sources["docs-examples.yml"]
        website = sources["website-ci.yml"]
        for name in ("browser-workbench.yml", "docs-check.yml", "docs-examples.yml"):
            self.assertNotIn("\n  push:\n", sources[name],
                             f"Duplicate post-merge dev validation: {name}")
        self.assertIn("  workflow_call:\n", browser)
        self.assertIn("  workflow_call:\n", docs_fast)
        self.assertIn("  pull_request:\n", examples)
        self.assertIn("  workflow_dispatch:\n", examples)
        self.assertIn("  workflow_call:\n", homepage)
        self.assertIn("    branches: [main]", homepage)
        self.assertNotIn("    branches: [dev, main]", homepage)
        adapter = sources["website-deploy.yml"]
        self.assertIn("  push:\n    branches: [dev]", adapter)
        self.assertIn("uses: ./.github/workflows/website-publish.yml", adapter)
        self.assertIn("uses: ./.github/workflows/rust-api-docs.yml", adapter)
        self.assertNotIn("\n  push:\n", sources["rust-api-docs.yml"])
        for workflow in ("site-homepage.yml", "browser-workbench.yml",
                         "docs-check.yml"):
            self.assertIn(f"uses: ./.github/workflows/{workflow}", website)

    def test_no_changes_or_unsafe_paths_do_not_bypass(self) -> None:
        for paths in ([], ["../docs/site/index.md"], ["/absolute"], ["docs\\site\\index.md"]):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                routing.classify(paths)

    def test_unrelated_code_is_not_treated_as_website(self) -> None:
        self.assertEqual(selected("CHANGELOG.md"), set())
        self.assertEqual(selected("test/test_quantum.py"), set())

if __name__ == "__main__":
    unittest.main()
