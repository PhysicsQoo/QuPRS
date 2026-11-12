#!/usr/bin/env python3
"""Observe a real pinned GPMC CLI count and the QuPRS Python SolverAdapter."""
import argparse
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument("--binary", type=Path, required=True)
p.add_argument("--adapter", action="store_true")
args = p.parse_args()
binary = args.binary.resolve(strict=True)
assert binary.is_file()
print("GPMC_RELEASE_EXECUTABLE_SHA256=" + hashlib.sha256(binary.read_bytes()).hexdigest())
with tempfile.TemporaryDirectory(prefix="gpmc-release-") as d:
    cnf = Path(d) / "complex.cnf"
    cnf.write_text(
        "p cnf 1 1\n"
        "c t wmc\n"
        "c p weight 1 0.5 0.25 0\n"
        "c p weight -1 1.0 0.0 0\n"
        "1 0\n", encoding="ascii")
    proc = subprocess.run([str(binary), "-mode=1", str(cnf)], text=True,
                          capture_output=True, timeout=30, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"GPMC runtime unavailable: status={proc.returncode}; stderr={proc.stderr[-2000:]!r}")
    if not re.search(r"(?m)^c s exact (?:arb|double|quadruple|octuple|single|half)\b", proc.stdout):
        raise RuntimeError(f"No GPMC weighted count: {proc.stdout[-2000:]!r}")
    print("GPMC_RELEASE_NATIVE_CLI_EXECUTION=PASS")
    if args.adapter:
        from QuPRS.interface.ps2wmc import run_wmc
        from QuPRS.utils import get_gpmc_path
        original = os.environ.get("QUPRS_GPMC_PATH")
        try:
            os.environ["QUPRS_GPMC_PATH"] = str(binary)
            with get_gpmc_path() as selected:
                assert selected.resolve() == binary
            real, imag = run_wmc(str(cnf), "gpmc", timeout=30)
        finally:
            if original is None:
                os.environ.pop("QUPRS_GPMC_PATH", None)
            else:
                os.environ["QUPRS_GPMC_PATH"] = original
        if not math.isclose(real, 0.5, abs_tol=1e-8) or not math.isclose(imag, 0.25, abs_tol=1e-8):
            raise AssertionError(f"Complex WMC mismatch: {real}+{imag}i")
        print("GPMC_RELEASE_SOLVER_ADAPTER=PASS")
