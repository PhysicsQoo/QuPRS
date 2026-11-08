#!/usr/bin/env python3
"""Stage an independent full-verification Cargo package for dry-run validation.

The reviewed core Cargo manifest is named quprs; staging only flattens
workspace inheritance and overrides the publication lock for dry-run validation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rust" / "pathsum"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected exactly one match for {old!r}")
    return text.replace(old, new, 1)


def stage(destination: Path) -> None:
    destination = destination.resolve()
    if destination == ROOT or ROOT in destination.parents or destination in ROOT.parents:
        raise ValueError("staged candidate must live outside the repository")
    if destination.exists():
        raise FileExistsError(destination)

    package = tomllib.loads((ROOT / "rust" / "Cargo.toml").read_text())["workspace"]["package"]
    text = (SOURCE / "Cargo.toml").read_text()
    text = replace_once(text, "version.workspace = true", f'version = "{package["version"]}"')
    text = replace_once(text, "edition.workspace = true", f'edition = "{package["edition"]}"')
    text = replace_once(text, "publish.workspace = true", "publish = true")
    parsed = tomllib.loads(text)
    if (parsed["package"]["name"] != "quprs"
            or parsed["lib"]["name"] != "quprs"
            or parsed["package"]["publish"] is not True
            or parsed["features"]["default"] != ["high-precision-gpmc"]
            or set(parsed["features"]) != {"default", "high-precision-gpmc"}):
        raise AssertionError("staged crate differs from the reviewed source manifest")

    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("target", ".git", "__pycache__", "*.pyc"))
    (destination / "Cargo.toml").write_text(text)
    (destination / "Cargo.lock").unlink(missing_ok=True)
    shutil.copyfile(ROOT / "LICENSE.md", destination / "LICENSE.md")
    manifest_source = ROOT / "src" / "QuPRS" / "utils" / "ganak-release.txt"
    if manifest_source.read_bytes() != (destination / "src" / "ganak-release.txt").read_bytes():
        raise AssertionError("Ganak pinned release manifest differs from original")
    if "QUPRS_SOLVER_PROVISION" not in (destination / "build.rs").read_text():
        raise AssertionError("missing explicit solver provisioning selection")
    print(f"STAGED_QUprs_CRATE={destination}")
    print(f"STAGED_QUprs_VERSION={package['version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    stage(parser.parse_args().output)
