"""Real GPMC regressions at the projective-distance precision boundary."""
from pathlib import Path
import pytest
from QuPRS import check_equivalence

_BASE = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'

@pytest.mark.parametrize(("angle","expected"),[
    ("0.0000000099","equivalent"),
    ("0.0000000199","equivalent"),
    ("0.0000000201","not_equivalent"),
    ("0.0000000204","not_equivalent"),
    ("0.00000004","not_equivalent"),
])
def test_rust_gpmc_distance_boundary(angle,expected):
    result=check_equivalence(
        _BASE,_BASE+f"rz({angle}) q[0];\n",
        method="wmc_only",strategy="Naive",
        backend="rust",tool_name="gpmc",
        approximate_distance_tolerance=1e-8,timeout=30)
    assert result.wmc_solver_invoked
    assert result.equivalent==expected

@pytest.mark.parametrize(("filename","expected"),[
    ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm","equivalent*"),
    ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm","equivalent"),
])
def test_rust_compiled_physical_equivalence(filename,expected):
    root=Path(__file__).resolve().parents[1]/"benchmarks"/"MQTBench"
    a=(root/filename).read_text()
    b=(root/"h,ry,rz,cx"/filename).read_text()
    result=check_equivalence(a,b,method="wmc_only",strategy="Difference",
        backend="rust",tool_name="gpmc",
        approximate_distance_tolerance=1e-8,timeout=45)
    assert result.wmc_solver_invoked
    assert result.equivalent==expected
