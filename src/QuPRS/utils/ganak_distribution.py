"""Pinned Ganak distribution identity shared with the Rust build."""
from functools import lru_cache
import hashlib
import logging
from pathlib import Path
import platform
import subprocess

VERSION = '2.8.0'
UPSTREAM_SHA = 'b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281'


def release_asset():
    system = {'Linux': 'linux', 'Darwin': 'macos', 'Windows': 'windows'}[platform.system()]
    machine = {'AMD64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine(), platform.machine())
    for line in Path(__file__).with_name('ganak-release.txt').read_text().splitlines():
        fields = line.split()
        if len(fields) == 5 and fields[:2] == [system, machine]:
            return fields
    raise RuntimeError(f'Unsupported Ganak platform: {system}/{machine}')


def architecture_matches(data, system, machine):
    if system == 'linux':
        return (len(data) >= 20 and data[:6] == b'\x7fELF\x02\x01'
                and int.from_bytes(data[18:20], 'little') == {'x86_64': 62, 'aarch64': 183}[machine])
    if system == 'macos':
        return (len(data) >= 8 and data[:4] == b'\xcf\xfa\xed\xfe'
                and int.from_bytes(data[4:8], 'little') == {'x86_64': 0x1000007, 'aarch64': 0x100000c}[machine])
    if system == 'windows' and len(data) >= 64 and data[:2] == b'MZ':
        offset = int.from_bytes(data[60:64], 'little')
        return data[offset:offset + 6] == b'PE\0\0\x64\x86'
    return False


def binary_diagnostics(path, overridden=False, timeout=10.0):
    path = Path(path).resolve()
    packaged = Path(__file__).with_name('wmc_tools') / ('ganak.exe' if platform.system() == 'Windows' else 'ganak')
    overridden = overridden and path != packaged.resolve()
    stat = path.stat()
    return _binary_diagnostics(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, overridden, float(timeout))


@lru_cache(maxsize=16)
def _binary_diagnostics(path, size, mtime, ctime, overridden, timeout):
    fields = release_asset()
    data = Path(path).read_bytes()
    fingerprint = hashlib.sha256(data).hexdigest()
    if not architecture_matches(data, *fields[:2]):
        raise RuntimeError(f'Wrong Ganak architecture: {fields[:2]}, sha256={fingerprint}')
    pinned = fingerprint == fields[4]
    if not overridden and not pinned:
        raise RuntimeError(f'Unverified packaged Ganak: sha256={fingerprint}; rebuild QuPRS')
    # The version check is a subprocess too; supervise its output, deadline,
    # and descendants rather than leaving a separate unsafe launch path.
    from QuPRS.utils.solver_process import run as run_solver
    output = run_solver([path, '--version'], timeout=timeout)
    if output.returncode != 0:
        raise RuntimeError(f'Ganak --version failed: status={output.returncode}')
    embedded = next((line for line in output.stdout.splitlines() if 'Ganak SHA1:' in line), 'unknown')
    if pinned and UPSTREAM_SHA not in embedded:
        raise RuntimeError(f'Ganak embedded version mismatch: {embedded}')
    info = dict(requested_version=VERSION, actual_version=VERSION if pinned else None, pinned=pinned, override=overridden,
                sha256=fingerprint, architecture='/'.join(fields[:2]), embedded_version=embedded)
    logging.getLogger(__name__).info('Ganak provenance: %s', info)
    if overridden and not pinned:
        logging.getLogger(__name__).warning('Ganak override does not match pinned v%s: %s', VERSION, info)
    return info


if __name__ == '__main__':
    import json
    from . import WMC
    with WMC('ganak') as binary:
        info = binary_diagnostics(binary)
    if not info['pinned']:
        raise SystemExit('CI requires the pinned Ganak release')
    print(json.dumps(info, indent=2))
