"""P1 independent per-round provenance and five-round CodSpeed verification."""
import argparse
import json
import math
import re
import sys
from pathlib import Path

# Direct execution "python scripts/..." sets sys.path[0] to scripts/, not
# the repo root. Restore the original reporter import contract.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.codspeed.test_paper_gap_repeatability import EXPECT
URI = re.compile(r"test_paper_gap_repeatability\[([^\]]+)\]$")

def produce(measured: dict, science: list, sha: str) -> dict:
    if measured.get("instrument", {}).get("type") != "walltime":
        raise ValueError("Expected CodSpeed WallTime export")
    bench = {}
    for item in measured.get("benchmarks", []):
        hit = URI.search(item.get("uri", ""))
        if not hit or hit.group(1) in bench:
            raise ValueError("Unexpected or duplicated P1 benchmark URI")
        stats = item.get("stats", {})
        if stats.get("rounds", 0) < 5 or stats.get("iter_per_round", 0) < 1:
            raise ValueError("P1 requires >=5 CodSpeed measured rounds")
        for metric in ("min_ns", "median_ns", "stdev_ns", "mean_ns"):
            value = stats.get(metric)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Missing or invalid P1 CodSpeed {metric}")
        bench[hit.group(1)] = stats
    records = {}
    for record in science:
        key = record.get("case")
        if key not in EXPECT or key in records or record.get("sha") != sha:
            raise ValueError("P1 repeated science record or wrong SHA")
        if record.get("stage_and_verdict_stable") is not True:
            raise ValueError(f"P1 unstable stage or verdict: {key}")
        desired_verdict, stage = EXPECT[key]
        if (record.get("expected_verdict") != desired_verdict
                or record.get("expected_solver_invoked") is not stage):
            raise ValueError(f"P1 expected verdict/stage mismatch: {key}")
        calls = record.get("observations", [])
        if not calls or len(calls) != record.get("observed_invocations"):
            raise ValueError(f"P1 missing invocation evidence: {key}")
        records[key] = record
    if set(bench) != set(EXPECT) or set(records) != set(EXPECT):
        raise ValueError("P1 incomplete five-case source/measurement coverage")
    report = {"schema": "quprs-codspeed-paper-gap-five-round-v1",
              "sha": sha, "instrument": "CodSpeed WallTime",
              "science_status": "DIAGNOSTIC_NO_FULL_OPERATOR_CERTIFICATE",
              "performance_certified": False, "cases": []}
    for case in sorted(EXPECT):
        stats=bench[case]
        report["cases"].append({
            "case": case, "median_ms": stats["median_ns"]/1e6,
            "min_ms": stats["min_ns"]/1e6,
            "stdev_ms": stats["stdev_ns"]/1e6,
            "coefficient_of_variation": (
                stats["stdev_ns"]/stats["mean_ns"] if stats["mean_ns"] else None),
            "rounds": stats["rounds"],
            "observed_calls": records[case]["observed_invocations"],
            "solver_invoked": EXPECT[case][1],
            "verdict": EXPECT[case][0],
            "qasm_sha256": records[case]["source_sha256"],
            "precision_reasons": sorted({
                x["wmc_precision_reason"]
                for x in records[case]["observations"]
                if x["wmc_precision_reason"] is not None
            }),
            "science_certified": False,
        })
    report["warning"] = ("Hosted non-Macro WallTime, single experiment and "
                         "independent source oracle not a certified release gate.")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--measurements",type=Path,required=True)
    p.add_argument("--science",type=Path,required=True)
    p.add_argument("--sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=produce(json.loads(a.measurements.read_text()),
                   [json.loads(x) for x in a.science.read_text().splitlines() if x.strip()],
                   a.sha)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({x["case"]:{"median_ms":x["median_ms"],"cv":x["coefficient_of_variation"]}
                      for x in result["cases"]},sort_keys=True))
    print("P1: REPEATABILITY_DIAGNOSTIC_COMPLETE, PERFORMANCE_NOT_CERTIFIED")
if __name__=="__main__":
    main()
