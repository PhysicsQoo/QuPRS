#!/usr/bin/env python3
"""Install a SHA-256-pinned GPMC CLI release at build time, never at runtime."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PIN_FILE = ROOT / "src/QuPRS/utils/gpmc-release.txt"
# macOS/Windows retain their already-qualified v1.0.0 executable bytes.
VERSION = "v1.0.0"
SOURCE_COMMIT = "54d76042df6bfcf4366a8c8a6d689753618a3148"
# Linux runtime compatibility repair: new MPFR SONAME and glibc baseline.
LINUX_VERSION = "v1.0.1"
LINUX_SOURCE_COMMIT = "8b494feb59e26e74d2b4d5b1f8bb33100d248400"


def release_for(system: str) -> tuple[str, str]:
    """Resolve one immutable producer version and source SHA per OS."""
    if system == "linux":
        return LINUX_VERSION, LINUX_SOURCE_COMMIT
    if system in ("macos", "windows"):
        return VERSION, SOURCE_COMMIT
    raise ValueError(f"Unsupported GPMC release operating system: {system}")
RELEASE_URL = "https://github.com/PhysicsQoo/GPMC/releases/download"
MAX_ARCHIVE_BYTES = 20_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def target_for(system: str | None = None, machine: str | None = None) -> tuple[str, str]:
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    os_name = {"linux": "linux", "darwin": "macos", "macos": "macos", "windows": "windows"}.get(system)
    arch = {"x86_64": "x86_64", "amd64": "x86_64",
            "arm64": "aarch64", "aarch64": "aarch64"}.get(machine)
    if not os_name or not arch:
        raise ValueError(f"Unsupported GPMC release target: {system}/{machine}")
    return os_name, arch


def read_pins(path: Path = PIN_FILE) -> dict[tuple[str, str], tuple[str, str]]:
    entries = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split()
        if len(cols) != 4 or not re.fullmatch("[a-f0-9]{64}", cols[3]):
            raise ValueError("Invalid GPMC release pin record")
        key = (cols[0], cols[1])
        expected_version, _source = release_for(cols[0])
        valid_name = re.fullmatch(r"gpmc-cli-v[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9_-]+\.tar\.gz", cols[2])
        if (key in entries or valid_name is None or
                not cols[2].startswith(f"gpmc-cli-{expected_version}-")):
            raise ValueError("Duplicate or invalid GPMC release pin")
        entries[key] = (cols[2], cols[3])
    if len(entries) != 6:
        raise ValueError("Incomplete six-platform GPMC release pin")
    return entries


def architecture_matches(blob: bytes, system: str, arch: str) -> bool:
    if system == "linux":
        return (len(blob) >= 20 and blob[:6] == b"\x7fELF\x02\x01"
                and int.from_bytes(blob[18:20], "little")
                == {"x86_64": 62, "aarch64": 183}[arch])
    if system == "macos":
        return (len(blob) >= 8 and blob[:4] == b"\xcf\xfa\xed\xfe"
                and int.from_bytes(blob[4:8], "little")
                == {"x86_64": 0x01000007, "aarch64": 0x0100000c}[arch])
    if system == "windows" and len(blob) >= 64 and blob[:2] == b"MZ":
        offset = int.from_bytes(blob[60:64], "little")
        return (len(blob) >= offset + 6 and blob[offset:offset + 4] == b"PE\x00\x00"
                and int.from_bytes(blob[offset + 4:offset + 6], "little")
                == {"x86_64": 0x8664, "aarch64": 0xaa64}[arch])
    return False


def verify_archive(data: bytes, system: str, arch: str, expected_sha: str) -> tuple[bytes, str]:
    if len(data) > MAX_ARCHIVE_BYTES or sha256(data) != expected_sha:
        raise ValueError("GPMC release archive SHA256/size mismatch")
    exe_name = "gpmc.exe" if system == "windows" else "gpmc"
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        required = {exe_name, "provenance.json", "dependencies.txt", "README-CLI.txt",
                    "licenses/LICENSE.md", "licenses/flow-cutter-pace17/LICENSE",
                    "licenses/preprocessor/lib_sharpsat_td/LICENSE",
                    "licenses/mpfr/copying.txt"}
        if len(names) != len(set(names)) or set(names) != required:
            raise ValueError("Unexpected GPMC release archive members")
        if any(not m.isfile() or m.issym() or m.islnk() for m in members):
            raise ValueError("GPMC release archive contains non-regular files")
        def read(name: str) -> bytes:
            f = archive.extractfile(name)
            if f is None:
                raise ValueError(f"Missing GPMC archive member: {name}")
            return f.read()
        exe = read(exe_name)
        manifest = json.loads(read("provenance.json"))
        label = {"linux": "linux-ubuntu22", "macos": "macos15",
                 "windows": "windows-ucrt64" if arch == "x86_64" else "windows-clangarm64"}[system]
        version, source_commit = release_for(system)
        native_arch = "arm64" if system == "macos" and arch == "aarch64" else arch
        target = f"{label}-{native_arch}"
        if (manifest.get("project") != "PhysicsQoo/GPMC"
                or manifest.get("release_version") != version
                or manifest.get("source_commit") != source_commit
                or manifest.get("platform") != target
                or manifest.get("executable_sha256") != sha256(exe)
                or manifest.get("dependencies_sha256") != sha256(read("dependencies.txt"))
                or manifest.get("runtime_mode") != "external-system-shared-libraries"
                or manifest.get("bundled_runtime_libraries") != []):
            raise ValueError("GPMC release provenance mismatch")
        if not architecture_matches(exe, system, arch):
            raise ValueError("Wrong GPMC executable architecture")
        return exe, sha256(exe)


def download(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urlopen(url, timeout=45) as response:
                payload = response.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES:
                raise ValueError("GPMC release archive exceeds size limit")
            return payload
        except (HTTPError, URLError) as exc:
            retry = isinstance(exc, URLError) and not isinstance(exc, HTTPError)
            retry = retry or (isinstance(exc, HTTPError) and
                              (exc.code == 429 or 500 <= exc.code < 600))
            if not retry or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("Unreachable download retry state")


def install(*, dest: Path, archive_path: Path | None = None,
            cache_dir: Path | None = None, system: str | None = None,
            machine: str | None = None, verify_only: bool = False) -> dict:
    os_name, arch = target_for(system, machine)
    version, source_commit = release_for(os_name)
    name, expected_sha = read_pins()[(os_name, arch)]
    cache_dir = cache_dir or ROOT / "rust/target/gpmc-release-cache"
    cached = cache_dir / name
    if archive_path is not None:
        data = archive_path.read_bytes()
    elif cached.is_file() and sha256(cached.read_bytes()) == expected_sha:
        data = cached.read_bytes()
    else:
        data = download(f"{RELEASE_URL}/{version}/{name}")
    exe, executable_sha = verify_archive(data, os_name, arch, expected_sha)
    if archive_path is None and not cached.is_file() or (
        archive_path is None and sha256(cached.read_bytes()) != expected_sha
    ):
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    if not verify_only:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".gpmc-", dir=dest.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(exe)
            if os.name != "nt":
                os.chmod(temporary, 0o755)
            os.replace(temporary, dest)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"version": version, "source": source_commit,
            "platform": f"{os_name}/{arch}", "archive_sha256": expected_sha,
            "executable_sha256": executable_sha,
            "path": str(dest), "installed": not verify_only}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, help="Destination executable path")
    parser.add_argument("--archive", type=Path, help="Local archive for offline verification")
    parser.add_argument("--system", help="Rust build target operating system")
    parser.add_argument("--machine", help="Rust build target architecture")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    os_name, _ = target_for(args.system, args.machine)
    dest = args.dest or ROOT / "src/QuPRS/utils/wmc_tools" / (
        "gpmc.exe" if os_name == "windows" else "gpmc")
    result = install(dest=dest, archive_path=args.archive,
                     cache_dir=args.cache_dir, system=args.system,
                     machine=args.machine, verify_only=args.verify_only)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
