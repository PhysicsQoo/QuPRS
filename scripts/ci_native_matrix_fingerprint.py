#!/usr/bin/env python3
"""Report-only exact-tree/native test-environment fingerprint.

This witness is not a permission to skip scientific tests. For future reuse
a trusted CI controller must independently verify successful GitHub jobs,
artifact source/identity and the same 16-slot contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def command(*args: str) -> str:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=12, check=True
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def witness() -> dict:
    freeze = command(sys.executable, "-m", "pip", "freeze", "--all")
    packages = "\n".join(sorted(line.strip() for line in freeze.splitlines() if line.strip()))
    submodules = command("git", "submodule", "status", "--recursive")
    contract = Path(".github/workflows/pytest.yml")
    contract_digest = hashlib.sha256(contract.read_bytes()).hexdigest() if contract.is_file() else ""
    image = os.getenv("ImageVersion", "")
    os_image = os.getenv("ImageOS", "")
    rust = command("rustc", "--version", "--verbose")
    native_libs = {
        "gmp": command("pkg-config", "--modversion", "gmp"),
        "mpfr": command("pkg-config", "--modversion", "mpfr"),
    }
    source = {
        "tree": command("git", "rev-parse", "HEAD^{tree}"),
        "submodule_sha256": digest(submodules),  # Empty submodule set is a valid fingerprint.
        "contract_sha256": contract_digest,
        "command_contract": "native-16-python-4-rust-source-v3",
    }
    environment = {
        "image_os": os_image,
        "image_version": image,
        "runner_os": os.getenv("RUNNER_OS", ""),
        "runner_arch": os.getenv("RUNNER_ARCH", ""),
        "python": sys.version.split()[0],
        "rustc_sha256": digest(rust) if rust else "",
        "pip_sha256": digest(packages) if packages else "",
        "native_libs": native_libs,
    }
    critical = [
        source["tree"], source["submodule_sha256"], source["contract_sha256"],
        image, os_image, environment["runner_os"], environment["runner_arch"],
        environment["python"], environment["rustc_sha256"],
        environment["pip_sha256"], native_libs["gmp"], native_libs["mpfr"],
    ]
    return {
        "schema": 1,
        "slot": f"{os.getenv('MATRIX_PYTHON', '')}|{os.getenv('MATRIX_OS', '')}",
        "job_step_status": os.getenv("TEST_STEP_STATUS", ""),
        "source": source,
        "environment": environment,
        "complete": bool(all(critical)),
        "reuse_decision": "NOT_CERTIFIED",
        "note": "Report-only: never skip a post-merge test from this artifact alone.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    info = witness()
    Path(args.output).write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    print("NATIVE_MATRIX_EVIDENCE", info["slot"], info["reuse_decision"], "complete=", info["complete"])


if __name__ == "__main__":
    main()
