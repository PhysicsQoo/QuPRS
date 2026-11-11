"""Offline checks for the pinned GPMC CLI consumer; no network or source build."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install_gpmc_release.py"
spec = importlib.util.spec_from_file_location("install_gpmc_release", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def fake_archive(*, source=None, binary=None, extra=None):
    source = source or release.SOURCE_COMMIT
    binary = binary or (b"\x7fELF\x02\x01" + b"\0" * 12 + struct.pack("<H", 62))
    deps = b"libmpfr.so.4\n"
    manifest = dict(project="PhysicsQoo/GPMC", release_version="v1.0.0",
                    source_commit=source, platform="linux-almalinux8-x86_64",
                    executable_sha256=release.sha256(binary),
                    dependencies_sha256=release.sha256(deps),
                    runtime_mode="external-system-shared-libraries",
                    bundled_runtime_libraries=[])
    entries = {name: b"notice" for name in (
        "licenses/LICENSE.md", "licenses/flow-cutter-pace17/LICENSE",
        "licenses/preprocessor/lib_sharpsat_td/LICENSE", "licenses/mpfr/copying.txt")}
    entries.update({"gpmc": binary, "dependencies.txt": deps,
                    "README-CLI.txt": b"external libraries required",
                    "provenance.json": json.dumps(manifest).encode()})
    if extra:
        entries.update(extra)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, contents in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            tar.addfile(info, io.BytesIO(contents))
    return output.getvalue()


def test_all_six_pins_match_release_platforms():
    pins = release.read_pins()
    assert len(pins) == 6
    assert set(pins) == {(os_name, arch)
                         for os_name in ("linux", "macos", "windows")
                         for arch in ("x86_64", "aarch64")}
    assert release.target_for("Darwin", "arm64") == ("macos", "aarch64")
    assert release.target_for("Windows", "AMD64") == ("windows", "x86_64")
    with pytest.raises(ValueError, match="Unsupported"):
        release.target_for("Linux", "i686")


def test_archive_verifies_executable_and_source():
    data = fake_archive()
    exe, fingerprint = release.verify_archive(
        data, "linux", "x86_64", release.sha256(data))
    assert exe.startswith(b"\x7fELF")
    assert fingerprint == release.sha256(exe)


def test_archive_tamper_and_source_mismatch_fail_closed():
    data = fake_archive()
    with pytest.raises(ValueError, match="SHA256"):
        release.verify_archive(data, "linux", "x86_64", "0" * 64)
    bad = fake_archive(source="0" * 40)
    with pytest.raises(ValueError, match="provenance"):
        release.verify_archive(bad, "linux", "x86_64", release.sha256(bad))


def test_invalid_architecture_and_members_fail_closed():
    wrong_arch = fake_archive(binary=b"not an ELF")
    with pytest.raises(ValueError, match="architecture"):
        release.verify_archive(wrong_arch, "linux", "x86_64",
                               release.sha256(wrong_arch))
    unexpected = fake_archive(extra={"../../escape": b"surprise"})
    with pytest.raises(ValueError, match="members"):
        release.verify_archive(unexpected, "linux", "x86_64",
                               release.sha256(unexpected))


def test_override_path_remains_authoritative(monkeypatch, tmp_path):
    from QuPRS.utils import WMC, get_gpmc_path
    p = tmp_path / "not-installed-yet"
    monkeypatch.setenv("QUPRS_GPMC_PATH", str(p))
    with WMC("gpmc") as found:
        assert found == p
    with get_gpmc_path() as found:
        assert found == p
