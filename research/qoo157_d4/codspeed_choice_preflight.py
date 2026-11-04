"""QOO-157 CodSpeed scientific preflight for a *candidate* solver.

Runs selected GPMC30/GPMC90/d4 on identical QuPRS-emitted paper-family CNFs.
This script NEVER emits speedup numbers: it only qualifies science, timeout,
source SHA and executable identity for separately instrumented CodSpeed runs.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import traceback

from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils.solver_adapter import registered_solver_adapter
from d4_solver_adapter_poc import external_research_adapter

# Small mixed pilot; expensive or canceled cases are retained, not imputed.
PAPER_CANDIDATES = {
    "grover4_eq": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "h,ry,rz,cx"),
    "qaoa7_neq": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "qiskit-2.6.1-opt0/Random_Rotation"),
    "qpeexact8_eq": ("qpeexact_nativegates_ibm_qiskit_opt0_8.qasm", "h,ry,rz,cx"),
    "qft16_eq": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "h,ry,rz,cx"),
}
SOLVERS = ("gpmc30", "gpmc90", "d4_426")
SCIENTIFIC_SCREEN = Fraction(1, 10**12)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_one(solver: str, path: Path, timeout: int):
    if solver == "gpmc30":
        return run_wmc(str(path), tool_name="gpmc", timeout=timeout, preserve_count=True)
    if solver == "gpmc90":
        return run_wmc(str(path), tool_name="gpmc", timeout=timeout,
                       preserve_count=True, precision_digits=90)
    if solver == "d4_426":
        return run_wmc(str(path), tool_name="d4-poc", timeout=timeout, preserve_count=True)
    raise ValueError("unsupported solver")

def scalar(x: Fraction) -> str:
    return str(x)

def preflight(cnf_dir: Path, binary: Path, manifest: Path, out: Path,
              timeout: int, source_dir: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    adapter = external_research_adapter(binary, manifest)
    cases = {}
    with registered_solver_adapter(adapter):
        for case, (qasm, second_dir) in PAPER_CANDIDATES.items():
            candidate = cnf_dir / (case + ".cnf")
            source_a = source_dir / qasm
            source_b = source_dir / second_dir / qasm
            result = {
                "candidate": case, "qasm": qasm, "pair_variant": second_dir,
                "source_sha256": [
                    sha256(source_a) if source_a.exists() else None,
                    sha256(source_b) if source_b.exists() else None,
                ],
                "source_cnf_sha256": sha256(candidate) if candidate.is_file() else None,
                "source_cnf_bytes": candidate.stat().st_size if candidate.is_file() else None,
                "method": "wmc_only_no_rr", "scope": "prepared_CNF_solver_inclusive",
                "status": "SOURCE_MISSING" if not candidate.is_file() else "PROBING",
                "solver_observations": {},
            }
            cases[case] = result
            if not candidate.is_file():
                continue
            for solver in SOLVERS:
                try:
                    observation = run_one(solver, candidate, timeout)
                    result["solver_observations"][solver] = {
                        "status": "COMPLETED",
                        "count": [scalar(observation.real), scalar(observation.imag)],
                        "printed_half_units": [scalar(observation.real_print_half_unit),
                                               scalar(observation.imag_print_half_unit)],
                        "format_name": observation.format_name,
                    }
                except Exception as e:
                    # Fail by status, not a fake zero count or invented timeout duration.
                    cls = type(e).__name__
                    result["solver_observations"][solver] = {
                        "status": "TIMEOUT" if "Timeout" in cls else "SOLVER_ERROR",
                        "exception_type": cls, "message": str(e)[:900],
                    }
            counts = result["solver_observations"]
            if all(counts.get(s, {}).get("status") == "COMPLETED" for s in SOLVERS):
                ref = tuple(Fraction(v) for v in counts["gpmc90"]["count"])
                if all(
                    all(abs(Fraction(val) - r) <= SCIENTIFIC_SCREEN *
                        max(Fraction(1), abs(ref[0]), abs(ref[1]))
                        for val,r in zip(counts[solver]["count"], ref))
                    for solver in SOLVERS
                ):
                    result["status"] = "NUMERICALLY_CONCORDANT_UNCERTIFIED"
                else:
                    result["status"] = "SCIENTIFIC_DIVERGENCE"
            else:
                result["status"] = "INELIGIBLE_SOLVER_TIMEOUT_OR_ERROR"
            out.write_text(json.dumps({
                "complete": False, "source":"quprs-research-d4-v1",
                "d4_binary_sha256": sha256(binary),
                "gmp_precise_arithmetic_certified": False,
                "cases": cases,
            }, indent=2) + "\n")
    qualified = [k for k,v in cases.items()
                 if v["status"] == "NUMERICALLY_CONCORDANT_UNCERTIFIED"]
    report = {
        "complete": True, "source": "quprs-research-d4-v1",
        "d4_binary_sha256": sha256(binary),
        "gmp_precise_arithmetic_certified": False,
        "reference_note": "GPMC 90 is a numerical reference, not an independent proof",
        "scientific_screen": "1e-12 scale-relative (not equivalent-distance tolerance)",
        "eligible_cases": qualified, "cases": cases,
        "codspeed_policy": "no timing outside CodSpeed; timeout cases censored",
        "recommendation_certified": False,
    }
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"eligible": qualified, "excluded": [
        [k,v["status"]] for k,v in cases.items() if k not in qualified
    ], "report": str(out)}))
    if not qualified:
        raise SystemExit("NO_COMPARABLE_QOO157_CANDIDATE: no CodSpeed measurement authorized")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=15)
    a=p.parse_args()
    preflight(a.cnf_dir, a.binary, a.manifest, a.out, a.timeout, a.source_dir)

if __name__=="__main__":
    main()
