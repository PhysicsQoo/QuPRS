"""Source checks for safe, separately versioned pre-release publication."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / ".github" / "workflows" / "python-publish.yml"
ARTIFACT = ROOT / ".github" / "workflows" / "release-artifact-ci.yml"
RECONCILE = ROOT / "scripts" / "reconcile_pypi_artifacts.py"


class PrereleasePolicyTests(unittest.TestCase):
    def test_both_artifact_workflows_normalize_python_package_versions(self):
        for path in (PUBLISH, ARTIFACT):
            with self.subTest(path=path.name):
                source = path.read_text()
                self.assertIn("from release_version import python_from_cargo", source)
                self.assertIn("python_from_cargo(workspace_version)", source)
                self.assertIn("scripts/release_version.py --kind python", source)

    def test_github_prerelease_is_not_latest(self):
        source = PUBLISH.read_text()
        self.assertIn("prerelease: ${{ contains(github.ref_name, '-') }}", source)
        self.assertIn("make_latest: ${{ contains(github.ref_name, '-') && 'false' || 'true' }}", source)
        self.assertIn("needs: [verify_release_ref, rust_preflight, publish, publish_crates_io]", source)

    def test_python_registry_reconciliation_uses_normalized_cargo_version(self):
        source = RECONCILE.read_text()
        self.assertIn("python_version = python_from_cargo(args.version)", source)
        self.assertIn("local_inventory(args.dist_dir, python_version)", source)
        self.assertIn("registry_inventory(python_version)", source)


if __name__ == "__main__":
    unittest.main()
