#!/usr/bin/env python3
"""Convert the shared Cargo release version to the corresponding PyPI version.

Rust releases use SemVer (for example 0.15.0-rc.2), while Python uses
PEP 440 (0.15.0rc2). Only the supported release spellings are admitted.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
_CARGO = re.compile(
    r"^(?P<base>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)(?:-(?P<kind>alpha|beta|rc)\."
    r"(?P<number>0|[1-9][0-9]*))?$"
)


def python_from_cargo(cargo_version: str) -> str:
    match = _CARGO.fullmatch(cargo_version)
    if match is None:
        raise ValueError(f"Unsupported Cargo release version: {cargo_version!r}")
    base = ".".join(match.group(p) for p in ("base", "minor", "patch"))
    kind = match.group("kind")
    if kind is None:
        return base
    suffix = {"alpha": "a", "beta": "b", "rc": "rc"}[kind]
    return f"{base}{suffix}{match.group('number')}"


def cargo_version(root: Path = ROOT) -> str:
    manifest = root / "rust" / "Cargo.toml"
    return tomllib.loads(manifest.read_text())["workspace"]["package"]["version"]


def verify_source(root: Path = ROOT) -> tuple[str, str]:
    cargo = cargo_version(root)
    python = python_from_cargo(cargo)
    module = (root / "src" / "QuPRS" / "_version.py").read_text()
    actual = re.search(r'^__version__\s*=\s*"([^"]+)"', module, re.MULTILINE)
    if actual is None or actual.group(1) != python:
        raise ValueError(
            f"Cargo version {cargo} requires Python {python}, "
            f"found {actual.group(1) if actual else '<missing>'}"
        )
    return cargo, python


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["cargo", "python", "tag"], required=True)
    args = parser.parse_args()
    cargo, python = verify_source()
    print({"cargo": cargo, "python": python, "tag": f"v{cargo}"}[args.kind])


if __name__ == "__main__":
    main()
