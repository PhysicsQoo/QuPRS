"""Exercise registry identity checks and the actual release shell step."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_crates_io_registry_state.py"
WORKFLOW = ROOT / ".github" / "workflows" / "python-publish.yml"
VERSION = "0.15.0-beta.1"


def registry_step_script() -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    step = "      - name: Admit a previously published identical crate on safe retries\n"
    if source.count(step) != 1:
        raise AssertionError("Expected exactly one registry admission step")
    portion = source.split(step, 1)[1].split("\n      - name: ", 1)[0]
    if portion.count("        run: |\n") != 1:
        raise AssertionError("Expected shell script in registry admission step")
    return "\n".join(
        line[10:] if line.startswith(" " * 10) else line
        for line in portion.split("        run: |\n", 1)[1].splitlines()
    ) + "\n"


class RegistryStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.crate = self.root / "quprs-crate" / "target" / "package" / f"quprs-{VERSION}.crate"
        self.crate.parent.mkdir(parents=True)
        self.crate.write_bytes(b"reviewed immutable crate bytes")
        self.metadata = self.root / "registry-version.json"
        self.output = self.root / "github-output.txt"
        self.digest = hashlib.sha256(self.crate.read_bytes()).hexdigest()

    def record(self, **changes: object) -> None:
        version = dict(num=VERSION, yanked=False, checksum=self.digest)
        version.update(changes)
        self.metadata.write_text(json.dumps({"version": version}), encoding="utf-8")

    def verify(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VERIFIER), VERSION, str(self.crate), str(self.metadata)],
            capture_output=True, text=True, timeout=10, cwd=ROOT,
        )

    def test_existing_identical_crate_is_accepted(self) -> None:
        self.record()
        self.assertEqual(self.verify().returncode, 0)

    def test_registry_mismatch_and_yanked_versions_fail_closed(self) -> None:
        for bad in ({"checksum": "0" * 64}, {"num": "0.15.0-beta.2"}, {"yanked": True}):
            with self.subTest(bad=bad):
                self.record(**bad)
                self.assertNotEqual(self.verify().returncode, 0)

    def test_missing_and_malformed_registry_response_fail_closed(self) -> None:
        self.metadata.write_text("{}", encoding="utf-8")
        self.assertNotEqual(self.verify().returncode, 0)
        self.metadata.write_text("not-json", encoding="utf-8")
        self.assertNotEqual(self.verify().returncode, 0)

    def test_workflow_bash_compiles_and_handles_http_statuses(self) -> None:
        script = registry_step_script()
        self.assertEqual(subprocess.run(["bash", "-n"], input=script, text=True,
                                        capture_output=True, timeout=10).returncode, 0)
        self.record()
        for status, valid, expected in (
            ("404", True, "already_published=false"),
            ("200", True, "already_published=true"),
            ("200", False, None),
            ("503", True, None),
        ):
            with self.subTest(status=status, valid=valid):
                self.record(**({} if valid else {"checksum": "0" * 64}))
                self.output.write_text("", encoding="utf-8")
                environment = dict(os.environ,
                    GITHUB_REF_NAME="v" + VERSION, RUNNER_TEMP=str(self.root),
                    GITHUB_OUTPUT=str(self.output), MOCK_HTTP_CODE=status)
                # A local curl stub exercises the actual workflow shell, without network access.
                command = 'curl() { printf "%s" "$MOCK_HTTP_CODE"; }\n' + script
                result = subprocess.run(["bash", "-eo", "pipefail"], input=command,
                    text=True, capture_output=True, cwd=ROOT, env=environment, timeout=10)
                if expected is None:
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self.output.read_text(encoding="utf-8"), "")
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected, self.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
