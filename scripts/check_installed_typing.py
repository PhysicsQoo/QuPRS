#!/usr/bin/env python3
"""Verify public type information from an installed QuPRS wheel, not source.

Run only in the existing Linux x86_64/Python 3.12 wheel admission job.
The file passed to mypy is typechecked but never executed: no QASM input,
solver process or gate execution is involved.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CONSUMER = """from typing import assert_type

from QuPRS import check_equivalence
from QuPRS.interface.load_qiskit import EquivalenceCheckResult
from QuPRS.pathsum import PathSum, Register, F

register = Register(2, "q")
assert_type(register.size, int)
ps = PathSum.QuantumCircuit(2)
assert_type(ps, PathSum)
assert_type(ps.h(0), PathSum)
assert_type(ps.cx(0, 1), PathSum)
assert_type(ps.rz(0.5, 0), PathSum)
assert_type(ps.mcx(0, 1), PathSum)
assert_type(ps.reduction(), PathSum)
assert_type(ps.f, F)
result = check_equivalence("first.qasm", "second.qasm")
assert_type(result, EquivalenceCheckResult)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mypy", action="store_true", required=True)
    args = parser.parse_args()
    assert args.mypy

    from importlib.metadata import distribution
    import QuPRS

    installed = Path(QuPRS.__file__).resolve()
    package_dir = installed.parent
    dist = distribution("QuPRS")
    install_root = Path(dist.locate_file("")).resolve()
    if not installed.is_relative_to(install_root):
        raise AssertionError("QuPRS resolved outside installed site-packages")
    if not (package_dir / "py.typed").is_file():
        raise AssertionError("Installed wheel has no py.typed marker")
    if not (package_dir / "pathsum" / "core.pyi").is_file():
        raise AssertionError("Installed wheel has no core.pyi")

    with TemporaryDirectory(prefix="quprs-wheel-typing-") as tmp:
        root = Path(tmp)
        source = root / "consumer.py"
        source.write_text(CONSUMER, encoding="utf-8")
        env = os.environ.copy()
        # Do not allow this repository to satisfy imports instead of the wheel.
        env.pop("MYPYPATH", None)
        env.pop("PYTHONPATH", None)
        cmd = [
            sys.executable, "-m", "mypy",
            "--no-incremental",
            "--ignore-missing-imports",
            "--follow-imports=silent",
            "--show-error-codes",
            "--python-version=3.12",
            str(source),
        ]
        completed = subprocess.run(
            cmd, cwd=root, env=env, capture_output=True,
            text=True, check=False, timeout=120,
        )
        print(completed.stdout, end="")
        if completed.returncode:
            raise AssertionError(
                f"Installed QuPRS static consumer typing FAILED (mypy {completed.returncode}): "
                + completed.stderr[-3000:]
            )
    print("Installed wheel external-consumer typing: PASS")


if __name__ == "__main__":
    main()
