"""Regression checks for macOS wheel compatibility metadata."""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.verify_macos_wheel_support import (
    documented_minimums,
    release_deployment,
    validate_policy,
    validate_wheels,
)


class MacOSWheelSupportTests(unittest.TestCase):
    README = (
        "| **macOS** | Intel (x86_64) | Supported | macOS 15+ |\n"
        "| **macOS** | Apple Silicon (M1/M2/M3) | Supported | macOS 15+ |\n"
    )
    WORKFLOW = 'echo "MACOSX_DEPLOYMENT_TARGET=15.0" >> $GITHUB_ENV'

    def test_current_source_policy(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(
            validate_policy(
                (root / "README.md").read_text(encoding="utf-8"),
                (root / ".github/workflows/python-publish.yml").read_text(encoding="utf-8"),
            ),
            {"arm64": (15, 0), "x86_64": (15, 0)},
        )

    def test_macos_14_claim_rejected(self):
        readme = self.README.replace("Apple Silicon (M1/M2/M3) | Supported | macOS 15+",
                                     "Apple Silicon (M1/M2/M3) | Supported | macOS 14+")
        with self.assertRaisesRegex(ValueError, "README minimum"):
            validate_policy(readme, self.WORKFLOW)

    def test_missing_or_ambiguous_support_declaration_rejected(self):
        with self.assertRaises(ValueError):
            documented_minimums(self.README.replace("Intel (x86_64)", "Unknown"))
        with self.assertRaises(ValueError):
            release_deployment(self.WORKFLOW + " MACOSX_DEPLOYMENT_TARGET=14.0")

    def _wheel(self, directory, tag, metadata_tag=None):
        filename = f"quprs-0.13.2-cp38-abi3-{tag}.whl"
        path = Path(directory) / filename
        with ZipFile(path, "w") as archive:
            archive.writestr("quprs-0.13.2.dist-info/WHEEL",
                             "Wheel-Version: 1.0\nRoot-Is-Purelib: false\n"
                             f"Tag: cp38-abi3-{metadata_tag or tag}\n")
        return path

    def test_valid_wheel_tag_and_embedded_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = self._wheel(directory, "macosx_15_0_arm64")
            validate_wheels([wheel], {"arm64": (15, 0)}, "arm64")

    def test_intel_wheel_tag_and_embedded_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = self._wheel(directory, "macosx_15_0_x86_64")
            validate_wheels([wheel], {"x86_64": (15, 0)}, "x86_64")
            with self.assertRaisesRegex(ValueError, "unexpected arch"):
                validate_wheels([wheel], {"arm64": (15, 0)}, "arm64")

    def test_old_and_mismatched_wheel_tags_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            wrong_min = self._wheel(directory, "macosx_14_0_arm64")
            with self.assertRaisesRegex(ValueError, "documented minimum"):
                validate_wheels([wrong_min], {"arm64": (15, 0)}, "arm64")
            wrong_meta = self._wheel(directory, "macosx_15_0_arm64",
                                     "macosx_14_0_arm64")
            with self.assertRaisesRegex(ValueError, "metadata tags differ"):
                validate_wheels([wrong_meta], {"arm64": (15, 0)}, "arm64")

    def test_no_mac_wheel_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "No wheels"):
            validate_wheels([], {"arm64": (15, 0)}, "arm64")


if __name__ == "__main__":
    unittest.main()
