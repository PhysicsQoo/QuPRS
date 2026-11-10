"""Offline guards for automatic, source-verified stable documentation publishing."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/docs-release-publish.yml"


class StableDocumentationAutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_automatic_release_and_single_backfill_trigger(self):
        src = self.source
        self.assertRegex(src, r"(?m)^  workflow_run:\n    workflows:\n      - Build and Publish Python Package\n    types: \[completed\]")
        self.assertRegex(src, r"(?m)^  push:\n    branches: \[main\]\n    paths:\n      - '\.github/workflows/docs-release-publish\.yml'")
        self.assertIn("github.event.workflow_run.conclusion == 'success'", src)
        self.assertIn("github.event.workflow_run.event == 'push'", src)
        self.assertIn("github.event.workflow_run.repository.full_name == github.repository", src)
        self.assertIn("github.event.workflow_run.path == '.github/workflows/python-publish.yml'", src)
        self.assertIn("!contains(github.event.workflow_run.head_branch, '-')", src)

    def test_signed_release_identity_and_original_tag_source(self):
        src = self.source
        self.assertIn('python3 scripts/docs_versioning.py check-release "$tag"', src)
        self.assertIn('test "$tag_type" = tag', src)
        self.assertIn(".verification.verified", src)
        self.assertIn("test \"$SOURCE_RUN_REPO\" = \"$GITHUB_REPOSITORY\"", src)
        self.assertIn('"$tag_sha" != "$SOURCE_RUN_SHA"', src)
        self.assertIn('gh release view "$tag" --json isDraft,isPrerelease', src)
        self.assertIn("release_state\" != '[false,false]'", src)
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/actions/runs?head_sha=$tag_sha&per_page=100"', src)
        self.assertIn('and .conclusion == "success"', src)
        self.assertIn('RELEASE_TAG: ${{ needs.admission.outputs.release_tag }}', src)

    def test_publishing_is_automatic_only_on_main(self):
        src = self.source
        publish = src.split("\n  publish:\n", 1)[1]
        head = publish.split("\n    steps:", 1)[0]
        self.assertIn("needs: [admission, build]", head)
        self.assertIn("needs.admission.outputs.should_publish == 'true'", head)
        self.assertIn("github.ref == 'refs/heads/main'", head)
        self.assertIn("(github.event_name != 'workflow_dispatch' || inputs.publish == true)", head)
        self.assertNotIn("refs/heads/dev", head)
        self.assertIn("if: ${{ needs.admission.outputs.should_publish == 'true' }}", src)
        self.assertIn("ref: main", src)

    def test_existing_docs_skip_republishing(self):
        src = self.source
        self.assertIn("docs/$tag/source-sha.txt", src)
        self.assertIn('test "$existing_sha" = "$tag_sha"', src)
        self.assertIn('index("stable") != null', src)
        self.assertIn('echo "should_publish=false" >> "$GITHUB_OUTPUT"', src)
        self.assertIn('echo "should_publish=true" >> "$GITHUB_OUTPUT"', src)
        self.assertIn('group: quprs-docs-stable-release', src)
        self.assertIn("cancel-in-progress: false", src)

    def test_negative_mutations_are_rejected(self):
        source = self.source
        def safe(s):
            return (
                "github.event.workflow_run.conclusion == 'success'" in s
                and 'test "$tag_type" = tag' in s
                and ".verification.verified" in s
                and 'test "$existing_sha" = "$tag_sha"' in s
                and "needs: [admission, build]" in s
                and "(github.event_name != 'workflow_dispatch' || inputs.publish == true)" in s
            )
        self.assertTrue(safe(source))
        for old, replacement in (
            ("github.event.workflow_run.conclusion == 'success'", "true"),
            ('test "$tag_type" = tag', 'echo unverified-tag'),
            ('.verification.verified', '.message'),
            ('test "$existing_sha" = "$tag_sha"', 'echo ignore-existing-source'),
            ("needs: [admission, build]", "needs: build"),
            ("(github.event_name != 'workflow_dispatch' || inputs.publish == true)", "true"),
        ):
            with self.subTest(mutation=old):
                self.assertFalse(safe(source.replace(old, replacement, 1)))


if __name__ == "__main__":
    unittest.main()
