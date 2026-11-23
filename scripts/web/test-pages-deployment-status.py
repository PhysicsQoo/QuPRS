"""Offline regression tests for exact-SHA GitHub Pages deployment admission."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
PARSER = Path(__file__).with_name("pages-deployment-status.py")
spec = importlib.util.spec_from_file_location("pages_deployment_status", PARSER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SHA = "a" * 40
OTHER = "b" * 40


def run(status="completed", conclusion="success", *, sha=SHA,
        branch="gh-pages", name="pages build and deployment"):
    return {
        "name": name,
        "head_branch": branch,
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
    }


class PagesDeploymentTests(unittest.TestCase):
    def assess(self, *runs):
        return module.deployment_status({"workflow_runs": list(runs)}, SHA)

    def test_no_matching_sha_never_passes(self):
        self.assertEqual(self.assess(run(sha=OTHER)), "absent")
        self.assertEqual(self.assess(run(branch="main")), "absent")
        self.assertEqual(self.assess(run(name="Documentation Stable Release")), "absent")
        self.assertEqual(self.assess(), "absent")

    def test_duplicate_cancelled_and_successful_runs(self):
        cancelled = run(conclusion="cancelled")
        success = run()
        self.assertEqual(self.assess(cancelled, success), "success")
        self.assertEqual(self.assess(success, cancelled), "success")
        self.assertEqual(self.assess(run(conclusion="failure"), success), "success")

    def test_cancelled_only_requires_fallback_not_promotion(self):
        self.assertEqual(self.assess(run(conclusion="cancelled")), "cancelled")
        self.assertEqual(self.assess(run(conclusion="cancelled"),
                                     run(conclusion="skipped")), "cancelled")

    def test_in_progress_and_failed_do_not_falsely_pass(self):
        self.assertEqual(self.assess(run(status="queued", conclusion=None)), "active")
        self.assertEqual(self.assess(run(status="in_progress", conclusion=None),
                                     run(conclusion="cancelled")), "active")
        self.assertEqual(self.assess(run(status="in_progress", conclusion=None),
                                     run(conclusion="failure")), "active")
        self.assertEqual(self.assess(run(conclusion="failure")), "failed")
        self.assertEqual(self.assess(run(conclusion="timed_out")), "failed")

    def test_rejects_malformed_or_ambiguous_evidence(self):
        for payload in ({}, {"workflow_runs": None},
                        {"workflow_runs": [None]},
                        {"workflow_runs": [run(conclusion="surprise")]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                module.deployment_status(payload, SHA)
        with self.assertRaises(ValueError):
            module.deployment_status({"workflow_runs": []}, "not-a-commit")

    def test_cli_prints_exact_status_and_rejects_invalid_json(self):
        command = [sys.executable, str(PARSER), "--sha", SHA]
        passed = subprocess.run(
            command, input=json.dumps({"workflow_runs": [
                run(conclusion="cancelled"), run()
            ]}), text=True, capture_output=True, check=True)
        self.assertEqual(passed.stdout.strip(), "success")
        failed = subprocess.run(command, input="{bad-json", text=True,
                                capture_output=True, check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("Invalid Pages Actions response", failed.stderr)

    def test_dev_publisher_has_one_explicit_build_and_sha_readback(self):
        source = (ROOT / ".github/workflows/website-publish.yml").read_text()
        self.assertEqual(
            source.count('gh api --method POST "repos/$GITHUB_REPOSITORY/pages/builds"'),
            1, "Each dev target must request just one explicit Pages build",
        )
        for required in (
            "Reject obsolete source after concurrent dev merges",
            "group: quprs-gh-pages-publish",
            "Confirm the existing GitHub Pages branch source",
            "Request and verify real GitHub Pages publication",
            'test "$(tr -d',
            'cmp "$RUNNER_TEMP/public-homepage.html" pages/index.html',
            'sha256sum "$RUNNER_TEMP/public-asset"',
            'Pages dynamic run snapshot for this SHA (informational)',
            'Public exact-source/hash verification | PASS',
        ):
            self.assertIn(required, source)
        # Never treat a cancelled auto-generated sibling as authorization to
        # skip the exact-source and public asset checks.
        self.assertNotIn("|| echo 'verified'", source)

    def test_browser_dependency_cache_never_skips_real_science(self):
        browser = (ROOT / ".github/workflows/browser-workbench.yml").read_text()
        self.assertIn("uses: Swatinem/rust-cache@v2", browser)
        self.assertIn("workspaces: rust -> target", browser)
        self.assertIn("save-if: ${{ github.ref == 'refs/heads/dev' && inputs.source_sha == '' }}", browser)
        self.assertIn("Native adapter and transport tests", browser)
        self.assertIn("Build actual QuPRS core as WebAssembly", browser)
        self.assertIn("Build pinned original MPFR GPMC", browser)
        self.assertIn("Assemble exact tested binaries and sources", browser)
        self.assertNotIn("if: steps.rust-cache.outputs.cache-hit", browser)
        deploy = (ROOT / ".github/workflows/website-deploy.yml").read_text()
        self.assertIn("Summarize exactly selected dev publication lanes", deploy)
        self.assertIn("Select changed site subsystems from the exact protected push", deploy)

    def test_publication_script_keeps_fail_closed_guards(self):
        source = (ROOT / "scripts/web/publish-stable-pages.sh").read_text()
        self.assertIn('wait_for_pages "$(git -C "$pages" rev-parse HEAD)"', source)
        self.assertIn('python3 source/scripts/web/pages-deployment-status.py', source)
        self.assertIn('fallback_after=$((SECONDS + 75))', source)
        self.assertIn('fallback_requested=true', source)
        self.assertNotIn("build_url=", source)
        self.assertIn("rollback()", source)
        self.assertIn('test "$(gh api "repos/$GITHUB_REPOSITORY/git/tags/$tag_object" --jq .verification.verified)" = true', source)
        self.assertIn('check_live "$PAGES_BASE/playground/$tag" "$source_sha"', source)


if __name__ == "__main__":
    unittest.main()
