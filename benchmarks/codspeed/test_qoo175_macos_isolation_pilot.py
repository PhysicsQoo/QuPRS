"""One-shot macOS CodSpeed WallTime ABBA: direct PyO3 vs supervised Worker.

For an experiment branch only; not part of the permanent per-PR benchmark
registry. Compare timings only within a matched macOS host/run, and retain
CodSpeed's non-Macro Runner warnings as confidence limitations.
"""
import pytest
from QuPRS import check_equivalence

QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'

_VARIANTS = [
    ("rr", False, "A1"),
    ("rr", True, "B1"),
    ("rr", True, "B2"),
    ("rr", False, "A2"),
    ("wmc", False, "A1"),
    ("wmc", True, "B1"),
    ("wmc", True, "B2"),
    ("wmc", False, "A2"),
]


def _check(mode: str, isolation: bool):
    result = check_equivalence(
        QASM, QASM, backend="rust", safe_mode=isolation,
        method="reduction_rules" if mode == "rr" else "wmc_only",
        tool_name="gpmc", timeout=20,
    )
    assert result.equivalent == "equivalent", result.equivalent
    return "verified"


@pytest.mark.parametrize(
    "mode,isolation,pass_id", _VARIANTS,
    ids=[f"{mode}-{step}-{'isolated' if isolated else 'direct'}"
         for mode, isolated, step in _VARIANTS],
)
def test_macos_rust_isolation_walltime(benchmark, mode, isolation, pass_id):
    assert benchmark(_check, mode, isolation) == "verified"
    benchmark.extra_info.update({
        "method": mode, "isolation": isolation, "pass_id": pass_id,
        "metric": "macos_same-run_full_Python_API_WallTime",
    })
