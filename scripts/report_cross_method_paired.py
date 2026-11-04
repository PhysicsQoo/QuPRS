"""Audit cross-method source and result provenance without inventing timings.

CodSpeed supplies times. Request-execution cost may be compared even when
scientific verdicts differ; successful equivalence-throughput cannot.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def inspect(records, base_sha, head_sha, instrument):
    # Load the source-pinned experimental matrix by file path: pytest and
    # Docker run with different sys.path roots; no package install is needed.
    from runpy import run_path
    case_file = Path(__file__).resolve().parents[1] / (
        "benchmarks/codspeed/test_cross_method_paired.py"
    )
    matrix = run_path(str(case_file))
    CASES, CPU_CASES = matrix["CASES"], matrix["CPU_CASES"]
    expected = CPU_CASES if instrument == "simulation" else CASES
    mapping = {c[0]: c for c in expected}
    paired = defaultdict(dict)
    errors = []
    for row in records:
        case, rev = row.get("case"), row.get("revision")
        if case not in mapping or rev not in ("base", "head"):
            errors.append(f"unexpected case/revision {case}/{rev}")
            continue
        if rev in paired[case]:
            errors.append(f"duplicate {case}/{rev}")
        paired[case][rev] = row
        sha = base_sha if rev == "base" else head_sha
        if row.get("sha") != sha or row.get("fixture_sha") != head_sha:
            errors.append(f"{case}/{rev}: wrong source/fixture SHA")
        params = mapping[case]
        for key, expect in (("instrument", instrument), ("method", "hybrid"),
                            ("strategy", params[2]), ("reverse", params[3]),
                            ("solver", params[4]), ("backend", params[5]),
                            ("solver_timeout_secs", 300 if instrument == "simulation" else 90)):
            if row.get(key) != expect:
                errors.append(f"{case}/{rev}: mismatched {key}")
        hashes = row.get("qasm_sha256")
        if not (isinstance(hashes, list) and len(hashes) == 2
                and all(isinstance(h, str) and len(h) == 64 for h in hashes)):
            errors.append(f"{case}/{rev}: invalid fixture hashes")

    output = []
    for name in mapping:
        if set(paired[name]) != {"base", "head"}:
            errors.append(f"{name}: missing base/head")
            continue
        b, h = paired[name]["base"], paired[name]["head"]
        for field in ("qasm_sha256", "method", "strategy", "reverse",
                      "backend", "solver", "solver_timeout_secs"):
            if b.get(field) != h.get(field):
                errors.append(f"{name}: input mismatch {field}")
        same_stage = b.get("solver_invoked") == h.get("solver_invoked")
        same_verdict = b.get("verdict") == h.get("verdict")
        output.append({
            "case": name, "backend": h["backend"], "solver": h["solver"],
            "verdict_base": b.get("verdict"), "verdict_head": h.get("verdict"),
            "solver_invoked_base": b.get("solver_invoked"),
            "solver_invoked_head": h.get("solver_invoked"),
            "same_solver_stage": same_stage,
            "same_observed_verdict": same_verdict,
            # Both executions respond to the same source and request. A delta
            # describes response latency, NOT proof of verified equivalence.
            "request_execution_cost_comparable": True,
            "solver_work_cost_comparable": bool(
                same_stage and b.get("solver_invoked") is True),
            "scientific_verdict_parity": "MATCHED" if same_verdict else "MISMATCHED",
            "performance_scope": ("matched_verdict_request_cost" if same_verdict
                                  else "execution_only_not_verified_speedup"),
        })
    return {
        "status": "PASS" if not errors else "FAIL",
        "base_sha": base_sha, "head_sha": head_sha,
        "instrument": instrument, "expected_pairs": len(mapping),
        "observed_pairs": len(output), "pairs": output, "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", choices=("walltime", "simulation"), required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.provenance.read_text().splitlines()
               if line.strip()]
    result = inspect(records, args.base_sha, args.head_sha, args.instrument)
    args.json.write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        f"### Cross-method {args.instrument} source pairing: {result['status']}",
        f"Exact base: {args.base_sha}; HEAD: {args.head_sha}",
        "Timings are provided exclusively by CodSpeed, not this audit.",
        "| Circuit/method | Base verdict | HEAD verdict | Same Solver stage | Scope |",
        "|---|---|---|---|---|",
    ]
    for item in result["pairs"]:
        lines.append(
            "| {case} | {verdict_base} | {verdict_head} | "
            "{same_solver_stage} | {performance_scope} |".format(**item))
    if result["errors"]:
        lines.extend(["", "Errors:"] + [f"- {error}" for error in result["errors"]])
    if args.summary:
        with args.summary.open("a") as summary:
            summary.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
