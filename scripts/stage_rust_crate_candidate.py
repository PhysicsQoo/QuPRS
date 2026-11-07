#!/usr/bin/env python3
"""Stage an independent RR-only Cargo package for dry-run validation.

The real Cargo manifests remain unpublished and their defaults unchanged.
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
    text = replace_once(text, 'default = ["high-precision-gpmc"]', 'default = ["standalone-rr"]')
    text = replace_once(text, "[package]\n", "[package]\nautobins = false\n")
    text += '\n[lib]\nname = "pathsum"\npath = "src/lib.rs"\n'
    parsed = tomllib.loads(text)
    if parsed["features"]["default"] != ["standalone-rr"] or parsed["package"]["publish"] is not True:
        raise AssertionError("standalone candidate metadata mismatch")

    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("target", ".git", "__pycache__", "*.pyc"))
    (destination / "Cargo.toml").write_text(text)
    (destination / "Cargo.lock").unlink(missing_ok=True)
    shutil.copyfile(ROOT / "LICENSE.md", destination / "LICENSE.md")
    if "CARGO_FEATURE_STANDALONE_RR" not in (destination / "build.rs").read_text():
        raise AssertionError("missing standalone solver-free build guard")
    print(f"STAGED_RR_CRATE={destination}")
    print(f"STAGED_RR_VERSION={package['version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    stage(parser.parse_args().output)
