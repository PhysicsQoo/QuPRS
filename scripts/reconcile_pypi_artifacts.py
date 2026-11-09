#!/usr/bin/env python3
"""Reconcile immutable PyPI release files before retrying an interrupted upload."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def local_inventory(dist: Path, version: str) -> dict[str, tuple[Path, str]]:
    paths = sorted((*dist.glob("*.whl"), *dist.glob("*.tar.gz")))
    if not any(p.name.endswith(".whl") for p in paths):
        raise ValueError("Missing Python wheel artifacts")
    if not any(p.name.endswith(".tar.gz") for p in paths):
        raise ValueError("Missing source distribution")
    expected_prefix = re.compile(r"^quprs-" + re.escape(version) + r"(?:-|\.)", re.I)
    result = {}
    for path in paths:
        if not path.is_file() or path.is_symlink() or not expected_prefix.match(path.name):
            raise ValueError(f"Unexpected Python release artifact: {path.name}")
        if path.name in result:
            raise ValueError(f"Duplicate distribution: {path.name}")
        result[path.name] = (path, hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def parse_registry_json(data: object) -> dict[str, str]:
    if not isinstance(data, dict) or not isinstance(data.get("urls"), list) or not data["urls"]:
        raise ValueError("Invalid or empty PyPI release metadata")
    result = {}
    for record in data["urls"]:
        if not isinstance(record, dict):
            raise ValueError("Malformed PyPI file record")
        name = record.get("filename")
        sha = (record.get("digests") or {}).get("sha256")
        if (not isinstance(name, str) or not name or "/" in name or "\\" in name
                or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
                or record.get("yanked") is not False or name in result):
            raise ValueError("Invalid, duplicated, or yanked PyPI file record")
        result[name] = sha
    return result


def registry_inventory(version: str) -> dict[str, str]:
    url = f"https://pypi.org/pypi/QuPRS/{quote(version, safe='')}/json"
    req = Request(url, headers={"Accept": "application/json", "Cache-Control": "no-cache"})
    try:
        with urlopen(req, timeout=20) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return {}
        raise
    if not isinstance(data, dict) or (data.get("info") or {}).get("version") != version:
        raise ValueError("PyPI release version differs from requested source version")
    return parse_registry_json(data)


def compare_inventory(local: dict[str, tuple[Path, str]], remote: dict[str, str]) -> list[str]:
    unexpected = sorted(remote.keys() - local.keys())
    mismatched = sorted(name for name in remote.keys() & local.keys()
                        if remote[name] != local[name][1])
    if unexpected or mismatched:
        raise ValueError(f"PyPI immutable release conflict: unexpected={unexpected}, SHA256_mismatch={mismatched}")
    return sorted(local.keys() - remote.keys())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "verify"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--upload-dir", type=Path, default=Path("pypi-to-upload"))
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        raise ValueError("Only stable numeric release versions may be published")
    local = local_inventory(args.dist_dir, args.version)
    if args.mode == "plan":
        missing = compare_inventory(local, registry_inventory(args.version))
        if args.upload_dir.exists():
            raise FileExistsError(args.upload_dir)
        args.upload_dir.mkdir(parents=True)
        for name in missing:
            shutil.copy2(local[name][0], args.upload_dir / name)
        required = "true" if missing else "false"
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                stream.write(f"publish_required={required}\n")
        print(f"PyPI immutable release reconciliation: existing={len(local) - len(missing)} "
              f"missing={len(missing)}, publish_required={required}")
        return

    for attempt in range(12):
        missing = compare_inventory(local, registry_inventory(args.version))
        if not missing:
            print(f"Verified {len(local)} published PyPI files by exact name and SHA-256")
            return
        if attempt < 11:
            time.sleep(5)
    raise RuntimeError(f"PyPI publication incomplete: {len(missing)} release files missing")


if __name__ == "__main__":
    main()
