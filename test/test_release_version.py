"""Offline validation for SemVer to PEP 440 release mapping."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_version", ROOT / "scripts" / "release_version.py")
assert SPEC and SPEC.loader
release_version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_version)


class ReleaseVersionTests(unittest.TestCase):
    def test_stable_and_prerelease_versions(self):
        cases = {
            "0.15.0": "0.15.0",
            "0.15.0-alpha.1": "0.15.0a1",
            "0.15.0-beta.1": "0.15.0b1",
            "0.15.0-beta.2": "0.15.0b2",
            "0.15.0-rc.1": "0.15.0rc1",
            "0.15.0-rc.2": "0.15.0rc2",
        }
        for cargo, expected in cases.items():
            with self.subTest(cargo=cargo):
                self.assertEqual(release_version.python_from_cargo(cargo), expected)

    def test_reject_ambiguous_or_unsupported_versions(self):
        for value in ("0.15.0b1", "0.15.0-beta", "0.15.0-beta.01",
                      "0.15.0-beta.1+metadata", "0.15.0-dev.1", "0.15", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    release_version.python_from_cargo(value)

    def test_version_source_agrees_with_cargo(self):
        cargo, python = release_version.verify_source(ROOT)
        self.assertEqual(python, release_version.python_from_cargo(cargo))

    def test_mismatched_python_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rust").mkdir()
            (root / "src" / "QuPRS").mkdir(parents=True)
            (root / "rust" / "Cargo.toml").write_text(
                '[workspace.package]\nversion = "0.15.0-beta.1"\n'
            )
            (root / "src" / "QuPRS" / "_version.py").write_text(
                '__version__ = "0.15.0"\n'
            )
            with self.assertRaises(ValueError):
                release_version.verify_source(root)
            (root / "src" / "QuPRS" / "_version.py").write_text(
                '__version__ = "0.15.0b1"\n'
            )
            self.assertEqual(
                release_version.verify_source(root),
                ("0.15.0-beta.1", "0.15.0b1"),
            )


if __name__ == "__main__":
    unittest.main()
