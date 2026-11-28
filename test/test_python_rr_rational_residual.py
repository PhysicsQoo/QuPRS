"""Source-locked QWalk3 and exact rational residual RR policy controls."""
from pathlib import Path
import hashlib

import pytest
import sympy as sp
from QuPRS import check_equivalence

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "MQTBench"
LEFT = ROOT / "qwalk-noancilla_nativegates_ibm_qiskit_opt0_3.qasm"
RIGHT = ROOT / "h,ry,rz,cx" / LEFT.name

def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}".encode() + bytes([0]) + data).hexdigest()

def test_qwalk3_rr_default_regression():
    assert blob(LEFT) == "0960c698e44cb5320301f7bd4acdd892d9069db0"
    assert blob(RIGHT) == "ea56fe6eb2ff58503931784f0ceb9bc2bb59fab2"
    r = check_equivalence(str(LEFT), str(RIGHT), backend="python",
                          method="reduction_rules", strategy="Proportional",
                          rr_tolerance=1e-10, timeout=8)
    assert r.equivalent == "equivalent"
    assert r.rr_approximate is True
    assert r.wmc_solver_invoked is False
    assert r.final_pathsum.P.free_symbols
    assert r.final_pathsum.num_pathvar == 0

def test_qwalk3_hybrid_rr_no_solver():
    common = dict(backend="python", strategy="Proportional", rr_tolerance=1e-10, timeout=8)
    rr = check_equivalence(str(LEFT), str(RIGHT), method="reduction_rules", **common)
    hybrid = check_equivalence(str(LEFT), str(RIGHT), method="hybrid", **common)
    assert rr.equivalent == hybrid.equivalent == "equivalent"
    assert rr.rr_approximate is hybrid.rr_approximate is True
    assert rr.wmc_solver_invoked is hybrid.wmc_solver_invoked is False
    assert rr.final_pathsum == hybrid.final_pathsum

def test_qwalk3_zero_tolerance_still_unknown():
    r = check_equivalence(str(LEFT), str(RIGHT), backend="python",
                          method="reduction_rules", strategy="Proportional",
                          rr_tolerance=0, timeout=8)
    assert r.equivalent == "unknown"
    assert not r.rr_approximate
    assert r.wmc_solver_invoked is False

def test_rational_aggregate_bound_exact_and_fail_closed():
    from QuPRS.interface.load_qiskit import _rr_rational_diagonal_phase as bound
    x, y, z = sp.symbols("x y z")
    eps = 2**-20
    a = sp.Rational(1, 2**21)
    scalar = sp.Rational(1, 4)
    assert bound(scalar+a*x, (x,y), eps) == scalar
    assert bound(scalar+(1-a)*x, (x,y), eps) == scalar
    assert bound(a*x+a*y, (x,y), eps) is None  # strict boundary
    assert bound(a*x+2*a*y, (x,y), eps) is None
    assert bound(a*x, (x,y), 0) is None
    assert bound(scalar, (x,y), eps) is None
    assert bound(a*x*z, (x,y), eps) is None
    assert bound(a*x**2, (x,y), eps) is None
    assert bound(sp.Float(1e-15)*x, (x,y), eps) is None
    assert bound(sp.sqrt(2)*a*x, (x,y), eps) is None
    assert bound(sp.Symbol("theta")*x, (x,y), eps) is None
