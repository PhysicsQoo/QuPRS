#!/usr/bin/env python3
"""Check macOS wheels against actual release-build deployment policy.

The root README is version-neutral; release workflow and wheel metadata are authoritative.
"""

import argparse
import re
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MACOS_TAG = re.compile(r"macosx_(\d+)_(\d+)_(arm64|x86_64|universal2)")
DEPLOYMENT = re.compile(r"MACOSX_DEPLOYMENT_TARGET=(\d+)\.(\d+)")


def release_architectures(workflow: str) -> set[str]:
    """Check the actual cibuildwheel macOS runner/arch matrix (not README)."""
    start, end = "\n  build_wheels:\n", "\n  build_sdist:\n"
    if workflow.count(start) != 1 or workflow.count(end) != 1:
        raise ValueError("Cannot uniquely locate release wheel matrix")
    build = workflow.split(start, 1)[1].split(end, 1)[0]
    if "CIBW_ARCHS: ${{ matrix.arch }}" not in build:
        raise ValueError("Release builder must set CIBW_ARCHS from matrix.arch")
    rows = build.splitlines()
    found: set[str] = set()
    count = 0
    for i, line in enumerate(rows):
        if not line.startswith("          - os: macos-"):
            continue
        count += 1
        runner_match = re.fullmatch(r" {10}- os: (macos-[0-9]+(?:-intel)?)(?:\s+#.*)?", line)
        arch_match = (
            re.match(r' {12}arch: ["\']?([a-z0-9_]+)', rows[i + 1])
            if i + 1 < len(rows) else None
        )
        if not runner_match or not arch_match:
            raise ValueError(f"Invalid macOS wheel matrix entry: {line}")
        runner, arch = runner_match.group(1), arch_match.group(1)
        if arch not in {"x86_64", "arm64"} or arch in found:
            raise ValueError(f"Invalid or duplicate macOS wheel architecture: {arch}")
        if runner.endswith("-intel") != (arch == "x86_64"):
            raise ValueError(f"macOS runner {runner} mismatches wheel arch {arch}")
        found.add(arch)
    if count != 2 or found != {"x86_64", "arm64"}:
        raise ValueError(f"Expected Intel and Apple Silicon wheel builds, got {found}")
    return found


def release_deployment(workflow: str) -> tuple[int, int]:
    matches = DEPLOYMENT.findall(workflow)
    if len(matches) != 1:
        raise ValueError(f"Expected one release deployment target, got {matches}")
    return tuple(map(int, matches[0]))


def validate_policy(workflow: str) -> dict[str, tuple[int, int]]:
    minimum = release_deployment(workflow)
    return {arch: minimum for arch in sorted(release_architectures(workflow))}


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
                raise ValueError(f"{wheel.name}: tag {tag} != release deployment minimum {expected}")
            matching = True
        if not matching:
            raise ValueError(f"{wheel.name}: no suitable macOS tags")
        print(f"Verified macOS {arch} wheel: {wheel.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--arch", choices=("arm64", "x86_64"))
    args = parser.parse_args()
    minimums = validate_policy(
        (ROOT / ".github/workflows/python-publish.yml").read_text(encoding="utf-8")
    )
    print(f"macOS release wheel policy: {minimums}")
    if args.wheel_dir is not None:
        if args.arch is None:
            parser.error("--arch is required with --wheel-dir")
        validate_wheels(sorted(args.wheel_dir.glob("*.whl")), minimums, args.arch)
    elif args.arch is not None:
        parser.error("--arch requires --wheel-dir")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit(f"macOS wheel support validation failed: {exc}")
