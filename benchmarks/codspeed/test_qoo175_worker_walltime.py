"""QOO-175 controlled single-SHA CodSpeed WallTime isolation pilot.

This benchmark uses the same installed Python/PyO3 Rust engine, QASM inputs,
toolchain and runner for direct and opt-in worker execution. Never interpret
the direct/isolated ratio as a release-to-release source regression.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from QuPRS import check_equivalence

IDENTITY = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
VALID = {"equivalent", "equivalent*"}


@pytest.mark.parametrize("case", ("identity_1q", "ghz32_rr"))
@pytest.mark.parametrize("safe_mode", (False, True), ids=("direct_pyo3", "isolated_worker"))
def test_qoo175_rust_rr_full_call_walltime(benchmark, case, safe_mode):
    root = Path(os.environ["GITHUB_WORKSPACE"])
    if case == "identity_1q":
        first = second = IDENTITY
        digest = hashlib.sha256(IDENTITY.encode()).hexdigest()
    else:
        fixture = root / "benchmarks" / "MQTBench" / "ghz_nativegates_ibm_qiskit_opt0_32.qasm"
        assert fixture.is_file()
        first = second = str(fixture)
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    seen = []

    def verify():
        res = check_equivalence(
            first, second,
            backend="rust", method="reduction_rules",
            strategy="Straightforward",
            tool_name="gpmc", timeout=45, safe_mode=safe_mode,
        )
        row = (res.equivalent, res.wmc_solver_invoked, res.rr_approximate)
        seen.append(row)
        if res.equivalent not in VALID or res.wmc_solver_invoked is True:
            raise AssertionError(f"Unexpected RR scientific result for {case}: {row}")
        return "PASS"

    assert benchmark(verify) == "PASS"
    assert seen and all(x[0] in VALID and x[1] is not True for x in seen)
    benchmark.extra_info.update({
        "kind": "full_python_api_rust_rr_walltime",
        "source_sha": os.environ["HEAD_SHA"],
        "case": case,
        "qasm_sha256": digest,
        "safe_mode": str(safe_mode),
        "executed_invocations": str(len(seen)),
        "verdicts": ",".join(sorted({x[0] for x in seen})),
        "solver_invoked": "false",
        "measured_scope": "same_SHA_installed_Python_API_call",
    })
