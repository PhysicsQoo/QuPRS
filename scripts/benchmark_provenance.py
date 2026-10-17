#!/usr/bin/env python3
"""Record reproducible benchmark provenance; warn when the saved main baseline is stale."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def version(*args):
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return (completed.stdout or completed.stderr).strip()[:600]
    except (OSError, subprocess.TimeoutExpired):
        return None


def sha256(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cpu_model():
    if sys.platform.startswith("linux"):
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            for line in cpuinfo.read_text(errors="replace").splitlines():
                if line.lower().startswith(("model name", "hardware")) and ":" in line:
                    return line.split(":", 1)[1].strip()
    return platform.processor() or platform.uname().processor or None


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--expected-main-sha")
    args = parser.parse_args()
    binary_dir = ROOT / "src/QuPRS/utils/wmc_tools"
    tools = {
        name: {"sha256": sha256(binary_dir / name),
               "version_output": version(str(binary_dir / name), "--version")
               if (binary_dir / name).is_file() else None}
        for name in ("ganak", "gpmc")
    }
    record = {
        "schema": 1,
        "source_sha": os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD"),
        "checkout_sha": git("rev-parse", "HEAD"),
        "ref": os.environ.get("GITHUB_REF"),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "cpu_count": os.cpu_count(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_image": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "gpmc_submodule_sha": git("rev-parse", "HEAD:GPMC"),
        "rustc": version("rustc", "--version"),
        "solver_binaries": tools,
        "ganak_release_manifest_sha256": sha256(
            ROOT / "src/QuPRS/utils/ganak-release.txt"),
        "ganak_build_script_sha256": sha256(ROOT / "rust/pathsum/build.rs"),
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print("Current benchmark provenance:\n" + json.dumps(record, indent=2))

    if args.baseline is not None:
        try:
            previous = json.loads(args.baseline.read_text())
        except (ValueError, OSError):
            previous = {}
        if not isinstance(previous, dict):
            previous = {}

        expected = args.expected_main_sha
        base = previous.get("source_sha")
        if not base or not expected or base != expected:
            print("::warning::Benchmark main_baseline provenance missing/stale: "
                  f"recorded={base!r}; current_main={expected!r}. "
                  "Do not regard regression results as same-commit comparisons.")
        else:
            print("Baseline source SHA matches current main; runtime and "
                  "hardware identities must still be checked.")

        # Report identity differences independently. An if/elif chain would
        # suppress CPU/GPMC changes whenever Ganak differs as well.
        baseline_tools = previous.get("solver_binaries")
        if not isinstance(baseline_tools, dict):
            baseline_tools = {}
        for name in ("ganak", "gpmc"):
            prior = baseline_tools.get(name)
            prior_sha = prior.get("sha256") if isinstance(prior, dict) else None
            current_sha = tools[name]["sha256"]
            if not prior_sha or not current_sha:
                print(f"::warning::{name} binary SHA256 missing from baseline "
                      "or current benchmark; solver identity is unverified.")
            elif prior_sha != current_sha:
                print(f"::warning::{name} solver binary differs from baseline; "
                      "compare using matched binary and input CNF before "
                      "attributing a runtime difference.")

        for field, label in (
            ("gpmc_submodule_sha", "GPMC submodule"),
            ("cpu_model", "CPU model"),
            ("runner_image", "Runner image"),
            ("runner_image_version", "Runner image version"),
            ("python_version", "Python version"),
        ):
            prior = previous.get(field)
            current = record.get(field)
            if not prior or not current:
                print(f"::warning::{label} provenance missing in baseline "
                      "or current run; matched-environment comparison unverified.")
            elif prior != current:
                print(f"::warning::{label} differs: "
                      f"baseline={prior!r}, current={current!r}.")


if __name__ == "__main__":
    run()
