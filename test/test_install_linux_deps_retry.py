"""Exercise fail-closed RPM metadata retries without network or system installs."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_linux_deps.sh"


@unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "requires a POSIX shell")
class RpmMetadataRetryTests(unittest.TestCase):
    def run_installer(self, always_fail: bool) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        # Restrict PATH to fake RPM commands and explicitly selected harmless
        # system utilities. No real package manager can be invoked.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = root / "trace"
            fake_yum = root / "yum"
            fake_yum.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = clean ]; then echo clean >> \"$YUM_TRACE\"; exit 0; fi\n"
                "echo install >> \"$YUM_TRACE\"\n"
                "if [ \"$YUM_ALWAYS_FAIL\" = 1 ]; then exit 23; fi\n"
                "attempts=$(grep -c '^install$' \"$YUM_TRACE\")\n"
                "[ \"$attempts\" -ge 3 ]\n"
            )
            fake_sleep = root / "sleep"
            fake_sleep.write_text("#!/bin/sh\nexit 0\n")
            for command in (fake_yum, fake_sleep):
                command.chmod(0o755)
            for utility in ("cat", "uname", "grep"):
                executable = shutil.which(utility)
                if executable is None:
                    self.skipTest(f"Missing required test utility: {utility}")
                (root / utility).symlink_to(executable)
            env = {
                **os.environ,
                "PATH": str(root),
                "YUM_TRACE": str(trace),
                "YUM_ALWAYS_FAIL": "1" if always_fail else "0",
            }
            result = subprocess.run(
                [shutil.which("sh") or "/bin/sh", str(SCRIPT)],
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
            return result, trace.read_text().splitlines() if trace.exists() else []

    def test_transient_metadata_failure_retries_and_recovers(self):
        result, operations = self.run_installer(always_fail=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(operations.count("install"), 3)
        self.assertEqual(operations.count("clean"), 2)

    def test_persistent_failure_stops_without_bypassing_dependencies(self):
        result, operations = self.run_installer(always_fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed after four attempts", result.stdout + result.stderr)
        self.assertEqual(operations.count("install"), 4)
        self.assertEqual(operations.count("clean"), 3)


if __name__ == "__main__":
    unittest.main()
