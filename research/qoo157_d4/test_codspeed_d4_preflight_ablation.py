"""QOO-157 ablate repeated external d4 binary hashing inside official CodSpeed.

Same prepared QuPRS weighted CNF, same native binary, same supervisor, same
count parser, same 426-bit GMP. Only per-invocation binary SHA verification
is changed: once per experimental process vs every request.

Not a production security recommendation. No runtime hash caching is added to
QuPRS defaults. The experiment records SHA before timing and verifies pinned
input and output per case. A mutable external binary could invalidate the
cached preflight and MUST NOT be used for production without a trusted install.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

import pytest

from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils.solver_adapter import (
    SolverExecutionError, registered_solver_adapter,
)
from d4_solver_adapter_poc import D4ResearchAdapter, external_research_adapter
from codspeed_choice_preflight import PAPER_CANDIDATES


@dataclass(frozen=True)
class D4PrecheckedAdapter(D4ResearchAdapter):
    prechecked_path: str = ""

    def verify_binary(self, executable, timeout):
        if timeout <= 0:
            raise SolverExecutionError("d4 prechecked admission timeout exhausted")
        if str(Path(executable).resolve()) != self.prechecked_path:
            raise SolverExecutionError("d4 binary path differs from once-checked source")
        # No hash read in timed call. Prechecked *outside* benchmark and only
        # valid for immutable scratch binary under one controlled CI job.


@pytest.fixture(scope="module", autouse=True)
def register_verified_and_cached_d4():
    binary = Path(os.environ["QOO157_D4_BINARY"]).resolve(strict=True)
    provenance = Path(os.environ["QOO157_D4_PROVENANCE"])
    verified = external_research_adapter(binary, provenance)
    verified.verify_binary(binary, 30)
    prechecked = D4PrecheckedAdapter(
        "d4-prechecked", verified.arguments, verified.capabilities,
        verified.resource_factory,
        verified.expected_binary_sha256, verified.upstream_commit,
        verified.preparse_gmp_bits, str(binary),
    )
    with registered_solver_adapter(verified), registered_solver_adapter(prechecked):
        yield


def run_case(case: str, solver: str):
    cnf = Path(os.environ["QOO157_CNF_DIR"]) / (case + ".cnf")
    if solver == "gpmc30":
        return run_wmc(str(cnf), "gpmc", 15, preserve_count=True)
    if solver == "d4_426_sha_each":
        return run_wmc(str(cnf), "d4-poc", 15, preserve_count=True)
    if solver == "d4_426_prechecked":
        return run_wmc(str(cnf), "d4-prechecked", 15, preserve_count=True)
    raise AssertionError(f"Unexpected solver: {solver}")


MODES = ("gpmc30", "d4_426_sha_each", "d4_426_prechecked")
PARAMS = [
    pytest.param(case, mode, id=f"{case}-{mode}")
    for case in PAPER_CANDIDATES
    for mode in MODES
]


@pytest.mark.parametrize("case,mode", PARAMS)
def test_qoo157_d4_preflight_hash_ablation(benchmark, case, mode):
    report = json.loads(Path(os.environ["QOO157_PREFLIGHT"]).read_text())
    if case not in report["eligible_cases"]:
        pytest.skip("NOT_QUALIFIED_FOR_WMC_PERFORMANCE: "
                    + report["cases"][case]["status"])
    result = benchmark(run_case, case, mode)
    source_solver = "d4_426" if mode.startswith("d4_") else "gpmc30"
    expected = report["cases"][case]["solver_observations"][source_solver]["count"]
    assert [str(result.real), str(result.imag)] == expected
    benchmark.extra_info.update({
        "case": case,
        "mode": mode,
        "input_sha256": report["cases"][case]["source_cnf_sha256"],
        "verification": ("sha256_each_call" if mode == "d4_426_sha_each" else
                         "sha256_once_untimed" if mode == "d4_426_prechecked" else
                         "gpmc_default"),
        "science_screen": "CONCORDANT_UNCERTIFIED",
        "timing_scope": "prepared_CNF_solver_inclusive_no_QASM_RR",
        "instrument": "CodSpeed_WallTime",
        "statistical_gate": "OBSERVATION_ONLY_NOT_MACRO_RUNNER",
    })
