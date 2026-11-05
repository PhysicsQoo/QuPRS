"""Source-pinned CLI-process overhead, measured ONLY by CodSpeed WallTime.

Comparisons are paired in one GitHub job with identical QASM and toolchain.
The same source code in rust/pathsum is used in base and HEAD. The internal
worker bypass is intentionally excluded from the release benchmark. These
CLI end-to-end observations, NOT Rust algorithmic CPU-cycle benchmarks.
"""
import os
import signal
import subprocess
from pathlib import Path

import pytest


def _fixture(case: str) -> list[str]:
    root = Path(os.environ["GITHUB_WORKSPACE"])
    if case == "single_h":
        return [str(root / "benchmarks" / "qoo156" / "single_h.qasm")]
    base = root / "benchmarks" / "MQTBench"
    name = {
        "dual_ghz32": "ghz_nativegates_ibm_qiskit_opt0_32.qasm",
        "dual_qpe8": "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    }[case]
    src = str(base / name)
    return [src, src]


def accepted_dual_verdict(stdout: str) -> bool:
    """Accept only complete machine-readable EQ verdicts, never NEQ/unknown."""
    return stdout.strip() in ("equivalent", "equivalent*")


def run_case(revision: str, case: str) -> str:
    binary = Path(os.environ["QOO156_BASE_CLI" if revision == "base" else "QOO156_HEAD_CLI"])
    command = [
        str(binary), *_fixture(case),
        "--timeout", "30", "--quiet",
    ]
    if case != "single_h":
        command.extend(["--method", "reduction-rules", "--strategy", "straightforward"])
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError(f"bounded CLI test exceeded 40s: {case}/{revision}")
    assert process.returncode == 0, f"CLI {case}/{revision} returned {process.returncode}: {err[-600:]}"
    if case == "single_h":
        assert "Reduced PathSum State" in out
    else:
        assert accepted_dual_verdict(out), (
            f"{case}/{revision}: expected exact EQ verdict, got {out[-350:]!r}"
        )
    return "ok"


@pytest.mark.parametrize(
    "revision,case",
    [
        pytest.param(revision, case, id=f"{case}-{order}-{revision}")
        for case in ("single_h", "dual_ghz32", "dual_qpe8")
        for order, revision in enumerate(("base", "head", "head", "base"))
    ],
)
def test_qoo156_cli_walltime(benchmark, revision: str, case: str):
    measured = benchmark(run_case, revision, case)
    assert measured == "ok"
    benchmark.extra_info.update({
        "variant": revision,
        "case": case,
        "base_sha": os.environ["QOO156_BASE_SHA"],
        "head_sha": os.environ["QOO156_HEAD_SHA"],
        "kind": "source_pinned_full_CLI_subprocess_walltime",
    })
