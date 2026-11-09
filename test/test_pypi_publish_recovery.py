"""Offline acceptance tests for safe retries of immutable PyPI release artifacts."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_pypi_artifacts.py"
SPEC = importlib.util.spec_from_file_location("pypi_reconcile", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class PyPIRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "quprs-0.15.0-py3-none-any.whl").write_bytes(b"wheel-a")
        (root / "QuPRS-0.15.0.tar.gz").write_bytes(b"sdist-a")
        self.local = module.local_inventory(root, "0.15.0")
        self.remote = {name: sha for name, (_, sha) in self.local.items()}

    def test_empty_release_requires_all_archives(self):
        self.assertEqual(module.compare_inventory(self.local, {}), sorted(self.local))

    def test_partial_identical_release_uploads_only_missing_archive(self):
        name = sorted(self.local)[0]
        self.assertEqual(module.compare_inventory(self.local, {name: self.remote[name]}),
                         sorted(set(self.local) - {name}))

    def test_complete_identical_release_skips_upload(self):
        self.assertEqual(module.compare_inventory(self.local, self.remote), [])

    def test_modified_existing_archive_is_rejected(self):
        changed = dict(self.remote)
        changed[next(iter(changed))] = "a" * 64
        with self.assertRaisesRegex(ValueError, "SHA256_mismatch"):
            module.compare_inventory(self.local, changed)

    def test_unexpected_registry_artifact_is_rejected(self):
        changed = dict(self.remote)
        changed["quprs-0.15.0-extra.whl"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "unexpected"):
            module.compare_inventory(self.local, changed)

    def test_registry_rejects_yanked_invalid_or_duplicate_records(self):
        name, sha = next(iter(self.remote.items()))
        record = {"filename": name, "digests": {"sha256": sha}, "yanked": False}
        self.assertEqual(module.parse_registry_json({"urls": [record]}), {name: sha})
        for bad in (
            {"urls": []},
            {"urls": [{**record, "yanked": True}]},
            {"urls": [{**record, "digests": {"sha256": "invalid"}}]},
            {"urls": [record, record]},
            {"urls": [{**record, "filename": "../corrupt.whl"}]},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                module.parse_registry_json(bad)

    def test_beta_archive_names_normalize_and_reject_stable_files(self):
        self.assertEqual(module.python_from_cargo("0.15.0-beta.1"), "0.15.0b1")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "quprs-0.15.0b1-py3-none-any.whl").write_bytes(b"wheel-beta")
            (root / "QuPRS-0.15.0b1.tar.gz").write_bytes(b"sdist-beta")
            inventory = module.local_inventory(root, "0.15.0b1")
            self.assertEqual(len(inventory), 2)
            with self.assertRaisesRegex(ValueError, "Unexpected Python"):
                module.local_inventory(root, "0.15.0")

    def test_invalid_prerelease_name_is_rejected(self):
        with self.assertRaises(ValueError):
            module.python_from_cargo("0.15.0-beta.01")

    def test_no_foreign_version_in_upload_inventory(self):
        root = Path(self.temp.name)
        (root / "quprs-0.14.1-py3-none-any.whl").write_bytes(b"old")
        with self.assertRaisesRegex(ValueError, "Unexpected Python"):
            module.local_inventory(root, "0.15.0")


if __name__ == "__main__":
    unittest.main()
