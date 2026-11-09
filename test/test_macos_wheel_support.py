"""Regression checks for macOS wheel compatibility metadata."""

import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zipfile import ZipFile

# pytest-xdist may import test modules without the repo root on sys.path.
# Load this offline release validator by location rather than as a package.
_SPEC = spec_from_file_location(
    "quprs_macos_wheel_validator",
    Path(__file__).resolve().parents[1] / "scripts/verify_macos_wheel_support.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_VALIDATOR = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_VALIDATOR)

release_architectures = _VALIDATOR.release_architectures
release_deployment = _VALIDATOR.release_deployment
validate_policy = _VALIDATOR.validate_policy
validate_wheels = _VALIDATOR.validate_wheels


class MacOSWheelSupportTests(unittest.TestCase):
    WORKFLOW = (
        "name: example\n"
        "  build_wheels:\n"
        "    strategy:\n"
        "      matrix:\n"
        "        include:\n"
        "          - os: macos-15-intel\n"
        '            arch: "x86_64"\n'
        "          - os: macos-15\n"
        '            arch: "arm64"\n'
        "    steps:\n"
        '      - run: echo "MACOSX_DEPLOYMENT_TARGET=15.0"\n'
        "        env:\n"
        "          CIBW_ARCHS: ${{ matrix.arch }}\n"
        "  build_sdist:\n"
    )

    def test_current_source_policy(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(
            validate_policy(
                (root / ".github/workflows/python-publish.yml").read_text(encoding="utf-8")
            ), {"arm64": (15, 0), "x86_64": (15, 0)}
        )

    def test_release_workflow_is_source_of_truth(self):
        self.assertEqual(validate_policy(self.WORKFLOW),
                         {"arm64": (15, 0), "x86_64": (15, 0)})
        shifted = self.WORKFLOW.replace("MACOSX_DEPLOYMENT_TARGET=15.0",
                                        "MACOSX_DEPLOYMENT_TARGET=14.0")
        self.assertEqual(validate_policy(shifted),
                         {"arm64": (14, 0), "x86_64": (14, 0)})

    def test_missing_or_ambiguous_support_declaration_rejected(self):
        with self.assertRaisesRegex(ValueError, "Intel and Apple Silicon"):
            release_architectures(self.WORKFLOW.replace("macos-15-intel", "ubuntu-latest"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            release_architectures(self.WORKFLOW.replace('arch: "x86_64"', 'arch: "arm64"'))
        with self.assertRaisesRegex(ValueError, "mismatches wheel arch"):
            release_architectures(self.WORKFLOW.replace("macos-15-intel", "macos-15"))
        with self.assertRaisesRegex(ValueError, "matrix.arch"):
            release_architectures(self.WORKFLOW.replace("CIBW_ARCHS: ${{ matrix.arch }}",
                                                        "CIBW_ARCHS: arm64"))
        with self.assertRaisesRegex(ValueError, "one release deployment"):
            release_deployment(self.WORKFLOW + " MACOSX_DEPLOYMENT_TARGET=14.0")
        with self.assertRaisesRegex(ValueError, "one release deployment"):
            release_deployment(self.WORKFLOW.replace("MACOSX_DEPLOYMENT_TARGET=15.0", ""))
        with self.assertRaisesRegex(ValueError, "uniquely locate"):
            release_architectures(self.WORKFLOW.replace("  build_sdist:", "  bad_job:"))

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
            with self.assertRaisesRegex(ValueError, "release deployment minimum"):
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
