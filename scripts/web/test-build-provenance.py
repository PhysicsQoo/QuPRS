"""Offline integrity and negative tests for source-bound browser build manifests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("write-build-provenance.py")
spec = importlib.util.spec_from_file_location("write_build_provenance", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)
        (self.site / "pkg").mkdir()
        (self.site / "engines").mkdir()
        (self.site / "source-sha.txt").write_text("a" * 40 + "\n")
        (self.site / "pkg/quprs_web_bg.wasm").write_bytes(b"quprs-core")
        (self.site / "engines/gpmc.wasm").write_bytes(b"original-gpmc")
        import hashlib
        digest = hashlib.sha256(b"original-gpmc").hexdigest()
        self.data = {
            "revision": "b" * 40,
            "version": "v1.0.2",
            "sha256": {"gpmc.wasm": digest},
        }
        self.store()

    def store(self):
        (self.site / "engines/PROVENANCE.json").write_text(
            json.dumps(self.data), encoding="utf-8"
        )

    def test_build_binds_exact_source_both_binary_digests_and_solver(self):
        module.write(self.site)
        manifest = json.loads((self.site / "build-provenance.json").read_text())
        self.assertEqual(manifest["source_sha"], "a" * 40)
        self.assertEqual(manifest["gpmc_revision"], "b" * 40)
        self.assertEqual(manifest["gpmc_version"], "v1.0.2")
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(len(manifest["core_wasm_sha256"]), 64)
        self.assertEqual(manifest["gpmc_wasm_sha256"], self.data["sha256"]["gpmc.wasm"])
        self.assertEqual(manifest["identity_kind"], "build-reported")

    def test_modified_gpmc_binary_rejected(self):
        (self.site / "engines/gpmc.wasm").write_bytes(b"forged")
        with self.assertRaisesRegex(ValueError, "differs"):
            module.write(self.site)

    def test_invalid_or_missing_source_rejected(self):
        for value in ("dev", "", "0" * 39):
            (self.site / "source-sha.txt").write_text(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.write(self.site)

    def test_unpinned_solver_revision_rejected(self):
        self.data["revision"] = "not-an-immutable-source"
        self.store()
        with self.assertRaises(ValueError):
            module.write(self.site)

    def test_symlinked_wasm_rejected(self):
        wasm = self.site / "engines/gpmc.wasm"
        wasm.unlink()
        wasm.symlink_to(self.site / "pkg/quprs_web_bg.wasm")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            module.write(self.site)


if __name__ == "__main__":
    unittest.main()
