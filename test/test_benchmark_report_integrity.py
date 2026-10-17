"""Fast report-integrity regressions; no solvers or benchmark execution required."""
import contextlib
import copy
import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "benchmark_report", ROOT / "scripts/generate_benchmark_report.py"
)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)
MAIN = "1a6be9d91745a41aa4d2ca69222454681d2deda7"
IDENTITY = {
    "source_sha": MAIN, "checkout_sha": MAIN,
    "solver_binaries": {name: {"sha256": "a" * 64} for name in ("ganak", "gpmc")},
    "gpmc_submodule_sha": "b" * 40, "cpu_model": "fixture CPU",
    "runner_os": "Linux", "runner_arch": "X64", "runner_image": "ubuntu24",
    "runner_image_version": "20261016.1", "python_version": "3.12.1", "rustc": "rustc fixture",
}


def benchmark(names):
    return {"benchmarks": [{"name": name, "stats": {"mean": 1.0, "stddev": 0.01}}
                            for name in names]}


class ReportIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.baseline = copy.deepcopy(IDENTITY)
        self.current = copy.deepcopy(IDENTITY)
        self.current.update(source_sha="c" * 40, checkout_sha="d" * 40)
        self.expected = MAIN
        self.outcome = "success"
        self.main_data = benchmark(["shared"])
        self.pr_data = benchmark(["shared"])

    def render(self):
        for name, data in (("base-prov", self.baseline), ("pr-prov", self.current),
                           ("main", self.main_data), ("pr", self.pr_data)):
            if data is not None:
                (self.root / name).write_text(data if isinstance(data, str) else json.dumps(data))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                REPORT.generate_report(
                    self.root / "main", self.root / "pr", self.root / "report", "true",
                    self.root / "base-prov", self.root / "pr-prov", self.expected, self.outcome,
                )
        except SystemExit as error:
            self.assertNotEqual(error.code, 0)
        return (self.root / "report").read_text()

    def assert_unverified(self):
        text = self.render()
        self.assertIn("UNVERIFIED", text)
        self.assertIn("NOT A PASS", text)
        self.assertNotIn("No significant performance changes detected", text)
        self.assertNotIn("No >10% change in recorded means", text)
        self.assertNotIn("Performance interpretation: report-only", text)
        return text

    def test_complete_matching_is_report_only(self):
        text = self.render()
        self.assertIn("Performance interpretation: report-only", text)
        self.assertIn("informational only, not a performance gate", text)
        self.assertNotIn("UNVERIFIED", text)

    def test_partial_failed_benchmark(self):
        self.outcome = "failure"
        self.main_data = benchmark(["shared", "failed-case"])
        text = self.assert_unverified()
        self.assertIn("'failure'", text)
        self.assertIn("baseline-only=1", text)

    def test_failed_benchmark_without_json(self):
        self.outcome = "failure"
        self.pr_data = None
        self.assert_unverified()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_benchmark_report.py"),
             "--main-file", str(self.root / "main"), "--pr-file", str(self.root / "pr"),
             "--report-file", str(self.root / "cli-report"), "--benchmark-outcome", "failure"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT A PASS", (self.root / "cli-report").read_text())

    def test_baseline_only_case(self):
        self.main_data = benchmark(["shared", "baseline-only"])
        self.assertIn("baseline-only=1", self.assert_unverified())

    def test_pr_only_case(self):
        self.pr_data = benchmark(["shared", "pr-only"])
        self.assertIn("PR-only=1", self.assert_unverified())

    def test_stale_baseline_sha(self):
        self.baseline["source_sha"] = "old"
        self.assertIn("Baseline source SHA", self.assert_unverified())

    def test_missing_baseline_sha(self):
        self.baseline.pop("source_sha")
        self.assert_unverified()

    def test_missing_expected_sha(self):
        self.expected = ""
        self.assert_unverified()

    def test_multiple_identity_mismatches_reported_independently(self):
        for record in [self.current]:
            for field in ["cpu_model", "runner_os", "runner_arch", "runner_image",
                          "runner_image_version", "python_version", "rustc", "gpmc_submodule_sha"]:
                record[field] = "changed"
            for solver in ("ganak", "gpmc"):
                record["solver_binaries"][solver]["sha256"] = "e" * 64
        text = self.assert_unverified()
        for label in ["CPU model", "Runner OS", "Runner architecture", "Runner image",
                      "Runner image version", "Python version", "Rust compiler", "GPMC submodule",
                      "ganak binary SHA256", "gpmc binary SHA256"]:
            self.assertIn(label, text)


def provenance_case(side, value):
    def test(self):
        setattr(self, side, value)
        self.assert_unverified()
    return test


for side in ("baseline", "current"):
    for label, value in [("missing", None), ("malformed", "{bad"), ("array", "[]"),
                         ("null", "null"), ("scalar", "42"), ("empty_object", {})]:
        setattr(ReportIntegrityTests, f"test_{side}_provenance_{label}", provenance_case(side, value))


def identity_case(field, label):
    def test(self):
        self.current[field] = "changed"
        self.assertIn(label, self.assert_unverified())
    return test


for field, label in [("cpu_model", "CPU model"), ("runner_image", "Runner image"),
                     ("runner_image_version", "Runner image version"),
                     ("python_version", "Python version"), ("gpmc_submodule_sha", "GPMC submodule")]:
    setattr(ReportIntegrityTests, f"test_equal_means_but_{field}_differs", identity_case(field, label))


def solver_case(solver, missing):
    def test(self):
        self.current["solver_binaries"][solver]["sha256"] = None if missing else "f" * 64
        self.assertIn(f"{solver} binary SHA256", self.assert_unverified())
    return test


for solver in ("ganak", "gpmc"):
    for missing in (True, False):
        setattr(ReportIntegrityTests, f"test_{solver}_{'missing' if missing else 'mismatch'}",
                solver_case(solver, missing))


if __name__ == "__main__":
    unittest.main()
