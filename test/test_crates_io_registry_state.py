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


def workflow_step_script(name: str) -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    step = "      - name: " + name + "\n"
    if source.count(step) != 1:
        raise AssertionError("Expected exactly one step named " + name)
    portion = source.split(step, 1)[1].split("\n      - name: ", 1)[0]
    if portion.count("        run: |\n") != 1:
        raise AssertionError("Expected shell script in " + name)
    return "\n".join(
        line[10:] if line.startswith(" " * 10) else line
        for line in portion.split("        run: |\n", 1)[1].splitlines()
    ) + "\n"


def registry_step_script() -> str:
    return workflow_step_script("Admit a previously published identical crate on safe retries")


def job_shell_scripts(name: str) -> list[str]:
    source = WORKFLOW.read_text(encoding="utf-8")
    section = "\n  " + name + ":\n"
    if source.count(section) != 1:
        raise AssertionError("Expected exactly one job named " + name)
    job = source.split(section, 1)[1]
    import re
    job = re.split(r"\n  [a-z_]+:\n", job, maxsplit=1)[0]
    scripts = []
    for tail in job.split("        run: |\n")[1:]:
        lines = []
        for line in tail.splitlines():
            if line.strip() and not line.startswith(" " * 10):
                break
            lines.append(line[10:] if line.startswith(" " * 10) else "")
        scripts.append("\n".join(lines) + "\n")
    return scripts

class RegistryStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.crate = self.root / "quprs-crate" / "target" / "package" / f"quprs-{VERSION}.crate"
        self.crate.parent.mkdir(parents=True)
        self.crate.write_bytes(b"reviewed immutable crate bytes")
        self.native = self.root / "quprs-native-assets" / f"quprs-{VERSION}.crate"
        self.native.parent.mkdir(parents=True)
        self.native.write_bytes(self.crate.read_bytes())
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
        self.assertIn("--user-agent 'QuPRS-release/1.0", script)
        self.assertIn("Accept: application/json", script)
        self.assertEqual(subprocess.run(["bash", "-n"], input=script, text=True,
                                        capture_output=True, timeout=10).returncode, 0)
        self.record()
        for status, valid, expected in (
            ("404", True, "already_published=false"),
            ("200", True, "already_published=true"),
            ("200", False, None),
            ("503", True, None),
            ("403", True, None),
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

    def test_registry_preflight_checks_http_and_exact_existing_crate(self) -> None:
        script = workflow_step_script("Verify crates.io registry access before PyPI publication")
        self.assertIn("--user-agent 'QuPRS-release/1.0", script)
        self.assertIn("Accept: application/json", script)
        self.assertNotIn("cargo publish", script)
        self.assertEqual(subprocess.run(["bash", "-n"], input=script, text=True,
                                        capture_output=True, timeout=10).returncode, 0)
        for status, correct, should_pass in (
            ("404", True, True),
            ("200", True, True),
            ("200", False, False),
            ("403", True, False),
            ("503", True, False),
        ):
            with self.subTest(status=status, correct=correct):
                self.record(**({} if correct else {"checksum": "0" * 64}))
                (self.root / "crates-io-preflight.json").write_text(
                    self.metadata.read_text(encoding="utf-8"), encoding="utf-8"
                )
                env = dict(os.environ, GITHUB_REF_NAME="v" + VERSION,
                           RUNNER_TEMP=str(self.root), MOCK_HTTP_CODE=status)
                command = 'curl() { printf "%s" "$MOCK_HTTP_CODE"; }\n' + script
                result = subprocess.run(["bash", "-eo", "pipefail"], input=command,
                                        text=True, capture_output=True, cwd=ROOT, env=env, timeout=10)
                self.assertEqual(result.returncode == 0, should_pass, result.stderr)

    def test_manual_recovery_and_registry_probe_shell_syntax(self) -> None:
        for job, minimum in (
            ("registry_probe", 1),
            ("recover_crates_io", 5),
            ("recover_github_release", 1),
        ):
            scripts = job_shell_scripts(job)
            self.assertGreaterEqual(len(scripts), minimum, job)
            for index, script in enumerate(scripts):
                with self.subTest(job=job, script=index):
                    result = subprocess.run(["bash", "-n"], input=script, text=True,
                                            capture_output=True, timeout=10, cwd=ROOT)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
