#!/usr/bin/env python3
"""Check published macOS wheel tags against QuPRS' documented minimum OS.

This is an *artifact compatibility* check, not a macOS 14 source-build test.
"""

import argparse
import re
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MACOS_TAG = re.compile(r"macosx_(\d+)_(\d+)_(arm64|x86_64|universal2)")
DEPLOYMENT = re.compile(r"MACOSX_DEPLOYMENT_TARGET=(\d+)\.(\d+)")


def documented_minimums(readme: str) -> dict[str, tuple[int, int]]:
    found = {}
    for line in readme.splitlines():
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] != "**macOS**":
            continue
        arch = "arm64" if "Apple Silicon" in cells[1] else (
            "x86_64" if "Intel" in cells[1] else None
        )
        if arch is None or arch in found:
            raise ValueError(f"Unexpected or duplicate macOS platform: {line}")
        match = re.fullmatch(r"macOS (\d+)\+", cells[3])
        if not match:
            raise ValueError(f"Invalid macOS support minimum: {cells[3]!r}")
        found[arch] = (int(match.group(1)), 0)
    if set(found) != {"arm64", "x86_64"}:
        raise ValueError(f"Expected exactly Intel and Apple Silicon rows, got {found}")
    return found


def release_deployment(workflow: str) -> tuple[int, int]:
    matches = {tuple(map(int, match)) for match in DEPLOYMENT.findall(workflow)}
    if len(matches) != 1:
        raise ValueError(f"Expected one macOS deployment target, got {matches}")
    return next(iter(matches))


def validate_policy(readme: str, workflow: str) -> dict[str, tuple[int, int]]:
    documented = documented_minimums(readme)
    deployment = release_deployment(workflow)
    for arch, minimum in documented.items():
        if minimum != deployment:
            raise ValueError(
                f"{arch} README minimum {minimum} != release deployment {deployment}"
            )
    return documented


def _platforms_from_filename(filename: str) -> set[str]:
    if not filename.endswith(".whl"):
        raise ValueError(f"Not a wheel: {filename}")
    parts = filename[:-4].rsplit("-", 3)
    if len(parts) != 4:
        raise ValueError(f"Malformed wheel name: {filename}")
    return set(parts[-1].split("."))


def _platforms_from_metadata(wheel: Path) -> set[str]:
    with ZipFile(wheel) as archive:
        wheel_files = [name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")]
        if len(wheel_files) != 1:
            raise ValueError(f"{wheel.name}: missing or duplicate WHEEL metadata")
        header = archive.read(wheel_files[0]).decode("utf-8")
    tags = {line[5:].strip().rsplit("-", 1)[-1] for line in header.splitlines()
            if line.startswith("Tag: ")}
    if not tags:
        raise ValueError(f"{wheel.name}: no Tag fields in WHEEL metadata")
    return tags


def validate_wheels(paths: list[Path], minimums: dict[str, tuple[int, int]], arch: str) -> None:
    if arch not in minimums:
        raise ValueError(f"Unexpected build arch: {arch}")
    if not paths:
        raise ValueError("No wheels produced by the macOS build")
    for wheel in paths:
        filename_tags = _platforms_from_filename(wheel.name)
        metadata_tags = _platforms_from_metadata(wheel)
        if filename_tags != metadata_tags:
            raise ValueError(
                f"{wheel.name}: WHEEL metadata tags differ: "
                f"filename={filename_tags}, metadata={metadata_tags}"
            )
        matching = False
        for tag in filename_tags:
            match = MACOS_TAG.fullmatch(tag)
            if not match:
                raise ValueError(f"{wheel.name}: unexpected macOS tag: {tag}")
            major, minor, tag_arch = match.groups()
            if tag_arch not in {arch, "universal2"}:
                raise ValueError(f"{wheel.name}: unexpected arch: {tag_arch}")
            expected = minimums[arch]
            if (int(major), int(minor)) != expected:
                raise ValueError(f"{wheel.name}: tag {tag} != documented minimum {expected}")
            matching = True
        if not matching:
            raise ValueError(f"{wheel.name}: no suitable macOS tags")
        print(f"Verified macOS {arch} wheel: {wheel.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--arch", choices=("arm64", "x86_64"))
    args = parser.parse_args()
    documented = validate_policy(
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / ".github/workflows/python-publish.yml").read_text(encoding="utf-8"),
    )
    print(f"README and release deployment target agree: {documented}")
    if args.wheel_dir is not None:
        if args.arch is None:
            parser.error("--arch is required with --wheel-dir")
        validate_wheels(sorted(args.wheel_dir.glob("*.whl")), documented, args.arch)
    elif args.arch is not None:
        parser.error("--arch requires --wheel-dir")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit(f"macOS wheel support validation failed: {exc}")
