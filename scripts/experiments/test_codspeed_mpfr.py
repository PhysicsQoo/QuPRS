"""Dedicated CodSpeed profiles for experimental native Rust precision.
Simulation measures only phase-weight CPU, WallTime measures the whole GPMC path.
Both are prebuilt release native test executables; no build under measurement.
"""
import os
import subprocess
from pathlib import Path

import pytest

_BIN = "QUPRS_CODSPEED_BINARY"

def _run(test_name: str, variant: str, case: str | None = None):
    binary = Path(os.environ[_BIN])
    assert binary.is_file(), binary
    env = dict(os.environ, QUPRS_CODSPEED_VARIANT=variant)
    if case is not None:
        env["QUPRS_CODSPEED_CASE"] = case
    run = subprocess.run(
        [str(binary), "--exact", test_name, "--quiet"],
        env=env, capture_output=True, text=True, timeout=35,
        check=False,
    )
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert "1 passed" in run.stdout, (run.stdout, run.stderr)
    return run.returncode

@pytest.mark.parametrize("variant", ("f64", "mpfr"))
def test_native_weight_cpu(benchmark, variant):
    # Simulation with subprocess tracking; no GPMC executable is used.
    assert benchmark(_run,
        "experimental_mpfr_bridge::experimental_codspeed_weight_case",
        variant) == 0

@pytest.mark.parametrize("case", ("grover4", "qaoa7", "graphstate16", "qft16"))
@pytest.mark.parametrize("variant", ("f64", "mpfr"))
def test_gpmc_end_to_end_walltime(benchmark, case, variant):
    # Eight stable names; exactly one GPMC solve per benchmark iteration.
    assert benchmark(_run,
        "experimental_mpfr_bridge::end_to_end::experimental_codspeed_compiled_case",
        variant, case) == 0
