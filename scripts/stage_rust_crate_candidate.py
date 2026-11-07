#!/usr/bin/env python3
"""Stage an independent full-verification Cargo package for dry-run validation.

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
    text = replace_once(text, 'name = "pathsum"', 'name = "quprs"')
    text = replace_once(text, "version.workspace = true", f'version = "{package["version"]}"')
    text = replace_once(text, "edition.workspace = true", f'edition = "{package["edition"]}"')
    text = replace_once(text, "publish.workspace = true", "publish = true")
    text = replace_once(text, 'default = ["high-precision-gpmc"]', 'default = ["external-wmc", "high-precision-gpmc"]')
    text = replace_once(text, "[package]\n", "[package]\nautobins = false\n")
    text += '\n[lib]\nname = "quprs"\npath = "src/lib.rs"\n'
    parsed = tomllib.loads(text)
    if parsed["features"]["default"] != ["external-wmc", "high-precision-gpmc"] or parsed["package"]["publish"] is not True:
        raise AssertionError("standalone candidate metadata mismatch")

    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("target", ".git", "__pycache__", "*.pyc"))
    (destination / "Cargo.toml").write_text(text)
    (destination / "Cargo.lock").unlink(missing_ok=True)
    shutil.copyfile(ROOT / "LICENSE.md", destination / "LICENSE.md")
    # Rewrite only Rustdoc examples in the staged public-name candidate.
    # Never rewrite executable code, which uses internal crate:: imports.
    for source_file in (destination / "src").rglob("*.rs"):
        original = source_file.read_text()
        patched = "".join(
            line.replace("pathsum::", "quprs::")
            if line.lstrip().startswith(("///", "//!")) else line
            for line in original.splitlines(keepends=True)
        )
        if patched != original:
            source_file.write_text(patched)
    for test_file in (destination / "tests").rglob("*.rs"):
        test_file.write_text(test_file.read_text().replace("pathsum::", "quprs::"))
    manifest_source = ROOT / "src" / "QuPRS" / "utils" / "ganak-release.txt"
    if manifest_source.read_bytes() != (destination / "src" / "ganak-release.txt").read_bytes():
        raise AssertionError("Ganak pinned release manifest differs from original")
    if "CARGO_FEATURE_EXTERNAL_WMC" not in (destination / "build.rs").read_text():
        raise AssertionError("missing external WMC build isolation")
    print(f"STAGED_QUprs_CRATE={destination}")
    print(f"STAGED_QUprs_VERSION={package['version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    stage(parser.parse_args().output)
