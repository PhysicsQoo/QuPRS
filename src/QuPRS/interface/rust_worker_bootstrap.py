"""Private admission gate for QuPRS's isolated Python/Rust worker.

No QuPRS/Qiskit modules load until the dedicated supervisor has admitted the
worker into its requested cgroup (if any). Applies opt-in Unix RLIMIT_AS
before importing the scientific package. This file is not a public CLI.
"""
from __future__ import annotations

import os
import sys

ADMISSION = b"QuPRS-Rust-Worker-Admit-v1\n"


def _positive_mib(name: str) -> int | None:
    text = os.environ.get(name)
    if text is None:
        return None
    if not text.isascii() or not text.isdecimal():
        raise ValueError(f"{name} must be a positive integer MiB value")
    value = int(text)
    if not (0 < value <= (2**63 - 1) // (1024 * 1024)):
        raise ValueError(f"{name} is outside the supported MiB range")
    return value


def _apply_address_space_limit() -> None:
    mib = _positive_mib("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB")
    if mib is None:
        return
    if os.name != "posix":
        raise RuntimeError("RLIMIT_AS requires Unix")
    import resource

    size = mib * 1024 * 1024
    _, old_hard = resource.getrlimit(resource.RLIMIT_AS)
    hard = min(size, old_hard) if old_hard != resource.RLIM_INFINITY else size
    resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
    soft, actual_hard = resource.getrlimit(resource.RLIMIT_AS)
    if soft > size or actual_hard > size:
        raise RuntimeError("RLIMIT_AS was not enforced")


def _read_admission() -> None:
    remaining = len(ADMISSION)
    chunks = []
    while remaining:
        fragment = os.read(0, remaining)
        if not fragment:
            raise RuntimeError("missing supervisor admission")
        chunks.append(fragment)
        remaining -= len(fragment)
    if b"".join(chunks) != ADMISSION:
        raise RuntimeError("invalid supervisor admission")
    expected_parent = os.environ.get("QUPRS_RUST_WORKER_PARENT_PID")
    if not expected_parent or int(expected_parent) != os.getppid():
        raise RuntimeError("isolated worker supervisor is not the parent")


def main() -> int:
    _read_admission()
    _apply_address_space_limit()
    from QuPRS.interface import rust_isolation

    return rust_isolation._worker_main()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"IsolatedWorkerAdmissionError: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(125)
