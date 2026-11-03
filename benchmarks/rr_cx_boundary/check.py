"""Experimental exact-angle EQ/NEQ + RR-to-Hybrid science witnesses.

Runs only public QuPRS APIs. No clocks/benchmark durations are measured here.
Both revisions execute this SAME file in independent installed environments.
This is not a performance benchmark, and does not mutate the verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from QuPRS import check_equivalence

DECIMAL = "0.12345678901234567890123456789"
DISTANCE = 1e-8
OPTIONS = {
    "strategy": "Proportional", "tool_name": "gpmc", "timeout": 90,
    "rr_tolerance": 0.0,  # No RR source-angle rounding at distance boundary.
    "approximate_distance_tolerance": DISTANCE,
    "wmc_phase_tolerance": 1e-8,
    "gpmc_precision_digits": 30,
}

HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
# Nontrivial, source-exact Bra-CX source terms with both constant rotations
# and, for mixed, exact multiples of pi. All pair differences below are the
# deliberately appended single-qubit Z rotation (up to identity CX pairs).
def qasm(kind: str) -> str:
    assert kind in {"decimal", "mixed"}
    gates = (
        "h q[0];\n"
        "cx q[0],q[1];\n"
        f"rz({DECIMAL}) q[1];\n"
        "cx q[0],q[1];\n"
        "h q[0];\n"
    )
    if kind == "mixed":
        gates = (
            "h q[0];\n"
            "cx q[0],q[1];\n"
            "rz(pi/4) q[0];\n"
            f"rz({DECIMAL}) q[1];\n"
            "cx q[0],q[1];\n"
            "t q[1];\n"
            "h q[0];\n"
        )
    return HEADER + gates


def manifest(fixtures: Path) -> list[dict]:
    cases = []
    for kind in ("decimal", "mixed"):
        base = qasm(kind)
        # The additional CX^2 pair is an *exact* identity. Placing it after
        # the source circuit exercises Bra-CX without modifying truth.
        identity = "cx q[0],q[1];\ncx q[0],q[1];\n"
        for variant, angle, truth, methods in (
            ("exact_eq", None, "eq", ("hybrid", "reduction_rules")),
            # Projective distance of RZ(theta) relative to I is
            # |sin(theta/2)|, independent of all preceding common gates.
            ("near_eq", "0.000000001", "eq", ("hybrid", "wmc_only")),
            ("near_neq", "0.000001", "neq", ("hybrid", "wmc_only")),
            ("far_neq", "0.125", "neq", ("hybrid",)),
        ):
            suffix = (f"rz({angle}) q[1];\n" if angle is not None else "") + identity
            cases.append({
                "case": f"{kind}_{variant}", "kind": kind,
                "truth": truth, "methods": list(methods),
                "source": base, "candidate": base + suffix,
                "theta_radians_literal": angle,
                "distance_tolerance": DISTANCE,
                "independent_distance_interval": (
                    "0" if angle is None else
                    "<1e-9" if variant == "near_eq" else
                    ">1e-7" if variant == "near_neq" else
                    ">1e-2"
                ),
            })
    # Existing independent Solver-inclusive VQE4 fixture is guaranteed to
    # exercise the RR residual/Hybrid hand-off. Don't infer its timing here.
    root = fixtures / "benchmarks" / "MQTBench"
    left = (root / "vqe_nativegates_ibm_qiskit_opt0_4.qasm").read_text()
    right = (root / "h,ry,rz,cx" /
             "vqe_nativegates_ibm_qiskit_opt0_4.qasm").read_text()
    cases.append({
        "case": "vqe4_real_eq", "kind": "real_circuit", "truth": "eq",
        "methods": ["hybrid", "reduction_rules"],
        "source": left, "candidate": right,
        "theta_radians_literal": None,
    })
    # A non-global RZ rotates the verified candidate relative to the true
    # equivalent VQE. Qubit 0 exists in the source's real QASM registers.
    cases.append({
        "case": "vqe4_real_neq", "kind": "real_circuit", "truth": "neq",
        "methods": ["hybrid"],
        "source": left, "candidate": right + "\nrz(0.125) q[0];\n",
        "theta_radians_literal": "0.125",
    })
    return cases


def classification(verdict: str) -> str:
    if verdict in {"equivalent", "equivalent*"}:
        return "eq"
    if verdict == "not_equivalent":
        return "neq"
    return verdict


def run(revision: str, fixtures: Path) -> dict:
    rows = []
    residual_states = {}
    cases = manifest(fixtures)
    hashes = {}
    for case in cases:
        ident = case["case"]
        hashes[ident] = {
            "reference": hashlib.sha256(case["source"].encode()).hexdigest(),
            "candidate": hashlib.sha256(case["candidate"].encode()).hexdigest(),
            "theta_radians_literal": case["theta_radians_literal"],
            "truth": case["truth"],
            "kind": case["kind"],
        }
        for method in case["methods"]:
            for backend in ("python", "rust"):
                result = check_equivalence(
                    case["source"], case["candidate"],
                    method=method, backend=backend, **OPTIONS
                )
                verdict = str(result.equivalent)
                # The public result returns the RR residual: Python exposes
                # the PathSum object, and Rust exposes its printed snapshot.
                # Preserve it until all requests are finished so we can
                # test the exact RR-only -> Hybrid handoff (not just statuses).
                residual_states[(ident, backend, method)] = result.final_pathsum
                stage = getattr(result, "wmc_solver_invoked", None)
                if stage is None:
                    stage = getattr(result, "tool_time", None) is not None
                obs = {
                    "case": ident, "truth": case["truth"], "method": method,
                    "backend": backend, "revision": revision,
                    "verdict": verdict, "class": classification(verdict),
                    "wmc_solver_invoked": bool(stage),
                    "rr_approximate": bool(getattr(result, "rr_approximate", False)),
                    "wmc_numerical_verdict": getattr(
                        result, "wmc_numerical_verdict", None),
                    "wmc_printed_verdict": getattr(
                        result, "wmc_printed_verdict", None),
                    "wmc_precision_reason": getattr(
                        result, "wmc_precision_reason", None),
                    "wmc_print_resolution_distance": getattr(
                        result, "wmc_print_resolution_distance", None),
                    "wmc_log_wmc": getattr(result, "log_wmc", None),
                    "wmc_expected_log2": getattr(result, "expect", None),
                }
                # RR alone cannot certify a projective distance. It may
                # legitimately return unknown; do not force Solver or claim
                # RR-only unknown is a false classification.
                if method in {"hybrid", "wmc_only"}:
                    assert obs["class"] == case["truth"], obs
                else:
                    # RR-only is a structural/source-exact status, not a
                    # distance-tolerant verifier. A transpiled VQE pair may
                    # be strict-negative while Hybrid finds distance-EQ.
                    # Do not falsely treat this difference as RR failure.
                    if case["kind"] != "real_circuit":
                        assert obs["class"] in {case["truth"], "unknown"}, obs
                    assert not obs["wmc_solver_invoked"], obs
                if method == "wmc_only":
                    assert obs["wmc_solver_invoked"], obs
                if obs["rr_approximate"]:
                    # rr_tolerance=0: sources are exact, no RR rounding.
                    raise AssertionError(f"Unrequested RR approximation: {obs}")
                rows.append(obs)
                print("RR_CX_BOUNDARY_WITNESS=" + json.dumps(
                    obs, sort_keys=True, default=str), flush=True)
    residual_checks = []
    for ident in ("decimal_exact_eq", "mixed_exact_eq", "vqe4_real_eq"):
        for backend in ("python", "rust"):
            rr = residual_states[ident, backend, "reduction_rules"]
            hybrid = residual_states[ident, backend, "hybrid"]
            assert rr == hybrid, (
                "Hybrid must preserve the *same* RR residual sent to WMC",
                revision, backend, ident, repr(rr), repr(hybrid)
            )
            residual_checks.append({
                "case": ident, "backend": backend, "equal": True,
                # Source-print fingerprint is for evidence only; cross-backend
                # polynomial formatting is not a canonical source representation.
                "rr_residual_repr_sha256": hashlib.sha256(
                    repr(rr).encode()).hexdigest(),
                "hybrid_residual_repr_sha256": hashlib.sha256(
                    repr(hybrid).encode()).hexdigest(),
            })
    assert len(residual_checks) == 6
    print("RR_CX_RESIDUAL_IDENTITY_PASS=" + json.dumps({
        "revision": revision, "cases": residual_checks
    }, sort_keys=True), flush=True)
    return {
        "schema": "quprs-rr-cx-exact-boundary-v1",
        "revision": revision, "tolerances": OPTIONS,
        "sources": hashes, "observations": rows,
        "rr_hybrid_residual_checks": residual_checks,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--revision", choices=("base", "head"), required=True)
    p.add_argument("--fixture-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = run(args.revision, args.fixture_root)
    args.output.write_text(json.dumps(
        report, indent=2, sort_keys=True, default=str) + "\n")
    print("RR_CX_BOUNDARY_REVISION_PASS=" +
          json.dumps({"revision": args.revision,
                      "observations": len(report["observations"]),
                      "cases": len(report["sources"])}, sort_keys=True))


if __name__ == "__main__":
    main()
