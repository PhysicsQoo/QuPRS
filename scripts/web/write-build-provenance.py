#!/usr/bin/env python3
"""Emit fail-closed, source-matched browser build metadata from tested assets.

This is build-reported provenance, not a cryptographic proof of a quantum
verdict. All paths resolve inside the already validated static site.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def build(site: Path) -> dict:
    site = site.resolve()
    source = (site / "source-sha.txt").read_text(encoding="ascii").strip()
    if not SHA.fullmatch(source):
        raise ValueError("Missing or malformed exact-source SHA")

    core = site / "pkg" / "quprs_web_bg.wasm"
    gpmc = site / "engines" / "gpmc.wasm"
    metadata = site / "engines" / "PROVENANCE.json"
    if any(path.is_symlink() for path in (core, gpmc, metadata)):
        raise ValueError("Source-matched binary metadata cannot use symlinks")
    upstream = json.loads(metadata.read_text(encoding="utf-8"))
    revision = upstream.get("revision")
    version = upstream.get("version")
    declared = upstream.get("sha256", {}).get("gpmc.wasm")
    if not isinstance(revision, str) or not SHA.fullmatch(revision):
        raise ValueError("Missing source-pinned GPMC revision")
    if not isinstance(version, str) or not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise ValueError("Missing GPMC version")
    if not isinstance(declared, str) or not DIGEST.fullmatch(declared):
        raise ValueError("Missing validated GPMC WASM checksum")
    core_digest = hashlib.sha256(core.read_bytes()).hexdigest()
    gpmc_digest = hashlib.sha256(gpmc.read_bytes()).hexdigest()
    if gpmc_digest != declared:
        raise ValueError("Published GPMC WASM differs from original upstream checksum")

    return {
        "format": "quprs-browser-build",
        "schema": 1,
        "source_sha": source,
        "core_wasm_sha256": core_digest,
        "gpmc_wasm_sha256": gpmc_digest,
        "gpmc_version": version,
        "gpmc_revision": revision,
        "identity_kind": "build-reported",
    }


def write(site: Path) -> None:
    manifest = build(site)
    (site / "build-provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: write-build-provenance.py <validated-site>")
    write(Path(sys.argv[1]))
