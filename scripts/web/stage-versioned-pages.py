"""Isolated GitHub Pages staging for dev and immutable stable browser versions.

This module only touches gh-pages/playground. Its caller must independently
verify signed release provenance and serialize with other gh-pages writers.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

STABLE_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")
MANDATORY = (
    "index.html", "app.js", "worker.js", "pkg/quprs_web_bg.wasm",
    "engines/gpmc.wasm", "source-sha.txt",
)
METADATA = {"versions.json", "stable-release.json"}


def version_key(tag: str) -> tuple[int, int, int]:
    match = STABLE_TAG.fullmatch(tag)
    if not match:
        raise ValueError("Only canonical stable vX.Y.Z tags are supported")
    return tuple(map(int, match.groups()))


def files(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Invalid or symlinked browser directory")
    result = {}
    for entry in directory.rglob("*"):
        if entry.is_symlink():
            raise ValueError("Symlink in browser assets is forbidden")
        if ".git" in entry.relative_to(directory).parts:
            raise ValueError("Git metadata in browser assets is forbidden")
        if entry.is_file():
            result[entry.relative_to(directory).as_posix()] = entry.read_bytes()
    return result


def sha(directory: Path) -> str:
    data = (directory / "source-sha.txt").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", data):
        raise ValueError("Missing or malformed source SHA")
    return data


def require_checkout(checkout: Path) -> None:
    if not (checkout / ".git").exists():
        raise ValueError("Expected a gh-pages Git checkout")
    dirty = subprocess.check_output(
        ["git", "-C", str(checkout), "diff", "--cached", "--name-only"],
        text=True,
    ).splitlines()
    if any(not name.startswith("playground/") for name in dirty):
        raise ValueError("Other Pages files are already staged")


def load_existing(root: Path) -> tuple[dict, dict | None]:
    manifest = root / "versions.json"
    stable_file = root / "stable-release.json"
    if not manifest.exists():
        if stable_file.exists():
            raise ValueError("Stable metadata without a version manifest")
        if any(p.is_dir() and STABLE_TAG.fullmatch(p.name) for p in root.iterdir()):
            raise ValueError("Existing version directories lack a manifest")
        return {"schema": 1, "stable": None, "versions": []}, None
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("versions"), list):
        raise ValueError("Invalid versions manifest")
    versions = data["versions"]
    tags = [item["version"] for item in versions]
    for item in versions:
        version_key(item["version"])
        if not re.fullmatch(r"[0-9a-f]{40}", item["source_sha"]):
            raise ValueError("Invalid manifest source SHA")
        dest = root / item["version"]
        if not dest.is_dir() or dest.is_symlink() or sha(dest) != item["source_sha"]:
            raise ValueError("Immutable version inventory is inconsistent")
    if len(tags) != len(set(tags)):
        raise ValueError("Duplicate version in manifest")
    if tags != sorted(tags, key=version_key, reverse=True):
        raise ValueError("Versions must be sorted newest first")
    stable = json.loads(stable_file.read_text(encoding="utf-8")) if stable_file.exists() else None
    if stable is None and data.get("stable") is not None:
        raise ValueError("Missing stable-release.json")
    if stable is not None:
        tag, source = stable.get("version"), stable.get("source_sha")
        if data.get("stable") != tag or not any(
            v["version"] == tag and v["source_sha"] == source for v in versions
        ):
            raise ValueError("Stable pointer does not match version inventory")
        if sha(root) != source:
            raise ValueError("Stable alias does not match selected release")
    return data, stable


def store_manifest(root: Path, data: dict) -> None:
    data["versions"].sort(key=lambda item: version_key(item["version"]), reverse=True)
    (root / "versions.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def stage(site: Path, checkout: Path, mode: str, tag: str = "", expected_sha: str = ""):
    site, checkout = site.resolve(), checkout.resolve()
    root = checkout / "playground"
    require_checkout(checkout)
    if root.is_symlink():
        raise ValueError("Symlinked Playground root")
    original = files(site)
    if any(name not in original for name in MANDATORY):
        raise ValueError("Incomplete validated browser site")
    if expected_sha and sha(site) != expected_sha:
        raise ValueError("Validated site was not built from the admitted SHA")
    root.mkdir(exist_ok=True)
    if mode == "dev":
        dest = root / "dev"
        if dest.is_symlink():
            raise ValueError("Symlinked dev preview")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(site, dest)
    elif mode in ("snapshot", "promote"):
        version_key(tag)
        if not expected_sha:
            raise ValueError("Stable operations require an admitted SHA")
        inventory, stable = load_existing(root)
        dest = root / tag
        if dest.exists():
            if files(dest) != original:
                raise ValueError("Immutable version exists with different bytes")
        elif mode == "snapshot":
            shutil.copytree(site, dest)
        else:
            raise ValueError("Cannot promote an unvalidated or missing snapshot")
        if mode == "snapshot" and not any(
            item["version"] == tag for item in inventory["versions"]
        ):
            inventory["versions"].append({"version": tag, "source_sha": expected_sha})
        if mode == "promote" and (
            stable is None or version_key(tag) > version_key(stable["version"])
        ):
            # Root contains only current browser assets, existing version dirs,
            # the explicit dev preview and the stable metadata.
            for child in root.iterdir():
                if child.name in METADATA or child.name == "dev" or STABLE_TAG.fullmatch(child.name):
                    continue
                if child.is_symlink():
                    raise ValueError("Symlinked root asset")
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            for child in site.iterdir():
                dest_asset = root / child.name
                if child.is_dir():
                    shutil.copytree(child, dest_asset)
                else:
                    shutil.copy2(child, dest_asset)
            stable = {"version": tag, "source_sha": expected_sha}
            (root / "stable-release.json").write_text(
                json.dumps(stable, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            inventory["stable"] = tag
        store_manifest(root, inventory)
    else:
        raise ValueError("Unexpected browser staging mode")
    subprocess.run(["git", "-C", str(checkout), "add", "--", "playground"], check=True)
    changes = subprocess.check_output(
        ["git", "-C", str(checkout), "diff", "--cached", "--name-only"], text=True
    ).splitlines()
    if any(not change.startswith("playground/") for change in changes):
        raise ValueError("Staged paths escaped Playground")
    return changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["dev", "snapshot", "promote"])
    parser.add_argument("site", type=Path)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--tag", default="")
    parser.add_argument("--sha", default="")
    opts = parser.parse_args()
    changes = stage(opts.site, opts.checkout, opts.mode, opts.tag, opts.sha)
    print(json.dumps({"mode": opts.mode, "staged_paths": changes}, indent=2))


if __name__ == "__main__":
    main()
