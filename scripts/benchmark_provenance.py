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
        except (ValueError, FileNotFoundError):
            previous = {}
        expected = args.expected_main_sha
        base = previous.get("source_sha")
        if not base or not expected or base != expected:
            print("::warning::Benchmark main_baseline provenance missing/stale: "
                  f"recorded={base!r}; current_main={expected!r}. "
                  "Do not regard regression results as same-commit comparisons.")
        elif (previous.get("solver_binaries", {}).get("ganak", {}).get("sha256")
              != tools["ganak"]["sha256"]):
            print("::notice::Benchmark binary differs between main and PR as expected for "
                  "a solver upgrade. Compare walltimes using an identical input CNF.")
        else:
            print("Baseline main SHA matches currently fetched main. "
                  "Runner characteristics are still potentially different.")


if __name__ == "__main__":
    run()
