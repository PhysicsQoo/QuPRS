#!/usr/bin/env python3
"""Validate an existing crates.io version against the exact reviewed .crate.

Called only after an HTTP 200 registry-version response. HTTP 404 and any
unexpected HTTP status are handled by the release workflow, failing closed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def verify_registry_version(expected_version: str, crate_file: Path, response_file: Path) -> None:
    response = json.loads(response_file.read_text(encoding="utf-8"))
    record = response.get('version') if isinstance(response, dict) else None
    if not isinstance(record, dict):
        raise ValueError("Missing crates.io version metadata")
    actual_checksum = hashlib.sha256(Path(crate_file).read_bytes()).hexdigest()
    if (record.get('num') != expected_version
            or record.get('yanked') is not False
            or record.get('checksum') != actual_checksum):
        raise ValueError("Existing registry version metadata or SHA-256 differs")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: verify_crates_io_registry_state.py VERSION CRATE_FILE RESPONSE_JSON")
    version, crate_file, response_file = sys.argv[1:]
    try:
        verify_registry_version(version, Path(crate_file), Path(response_file))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Registry version cannot be safely reused: {exc}") from exc


if __name__ == "__main__":
    main()
