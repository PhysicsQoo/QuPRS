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

# In-process C/MPFR CPU kernel (not a subprocess or full Rust weight pipeline).
import ctypes
from functools import lru_cache

@lru_cache(maxsize=1)
def _inprocess_lib():
    lib=ctypes.CDLL(os.environ["QUPRS_CODSPEED_NATIVE_LIB"])
    prototype=[ctypes.c_char_p]*4+[ctypes.c_ulong,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t]
    for name in ("quprs_exp_f64_phase_weight","quprs_exp_mpfr_phase_weight"):
        f=getattr(lib,name)
        f.argtypes=prototype
        f.restype=ctypes.c_int
    return lib

@lru_cache(maxsize=1)
def _phase_inputs():
    return [(b"0",b"1",str(317*k).encode(),b"10000000000000000") for k in range(1,25)]

def _cpu_kernel(variant):
    function=getattr(_inprocess_lib(),"quprs_exp_"+variant+"_phase_weight")
    real=ctypes.create_string_buffer(160)
    imag=ctypes.create_string_buffer(160)
    for a,b,c,d in _phase_inputs():
        assert function(a,b,c,d,192,real,imag,160)==0
    return 24

@pytest.mark.parametrize("variant",("f64","mpfr"))
def test_inprocess_phase_weight_cpu(benchmark,variant):
    _inprocess_lib()
    _phase_inputs()
    assert benchmark(_cpu_kernel,variant)==24

@pytest.mark.parametrize("case", ("grover4", "qaoa7", "graphstate16", "qft16"))
@pytest.mark.parametrize("variant", ("f64", "mpfr"))
def test_gpmc_end_to_end_walltime(benchmark, case, variant):
    # Eight stable names; exactly one GPMC solve per benchmark iteration.
    assert benchmark(_run,
        "experimental_mpfr_bridge::end_to_end::experimental_codspeed_compiled_case",
        variant, case) == 0
