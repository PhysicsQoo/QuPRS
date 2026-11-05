"""Early isolated-worker resource admission before importing the QuPRS package.

This file is executed as a script in a NEW Python process, not with -m:
importing the QuPRS package first would allocate memory before the address
space cap was applied. The cap applies to this worker, never its parent.
"""
from __future__ import annotations

import os
import sys

_MAX_MIB = 1 << 30


def _parse_address_space_cap(raw: str | None) -> int | None:
    if raw is None:
        return None
    if not raw or not raw.isascii() or not raw.isdecimal():
        raise ValueError("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB must be a positive integer")
    mib = int(raw)
    if mib <= 0 or mib > _MAX_MIB:
        raise ValueError("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB is out of range")
    return mib


def _apply_address_space_cap() -> None:
    mib = _parse_address_space_cap(os.environ.get("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB"))
    if mib is None:
        return
    # RLIMIT_AS is virtual address space, never a guarantee of physical RSS.
    import resource

    if not hasattr(resource, "RLIMIT_AS"):
        raise RuntimeError("RLIMIT_AS is unsupported on this host")
    size = mib * 1024 * 1024
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    # A pre-existing lower hard limit is preserved, never relaxed.
    capped = min(size, hard) if hard != resource.RLIM_INFINITY else size
    resource.setrlimit(resource.RLIMIT_AS, (capped, capped))
    actual, _ = resource.getrlimit(resource.RLIMIT_AS)
    if actual != capped:
        raise RuntimeError("RLIMIT_AS could not be verified")


def main() -> int:
    try:
        _apply_address_space_cap()
    except (ValueError, OSError, RuntimeError, OverflowError) as exc:
        print(f"IsolatedWorkerResourceAdmissionFailed: {exc}", file=sys.stderr)
        return 125
    from QuPRS.interface.rust_isolation import _worker_main
    return _worker_main()


if __name__ == "__main__":
    sys.exit(main())
