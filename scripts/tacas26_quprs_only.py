#!/usr/bin/env python3
"""Canonical QuPRS-only TACAS'26 execution protocol; no competing verifiers.

The prior 187-case source index is intentionally retained as an independent
exploratory ledger, not silently relabeled as the submitted paper protocol.
"""
import argparse
import json
from pathlib import Path

from scripts.tacas26_paper_matrix import matrix as exploratory_matrix, run_parent

HISTORICAL_DIRECT_CALLS = 184
DERIVED_HYBRID_RR_CELLS = 37
PENDING_DIRECT_CALLS = 107
POSITIVE_HYBRID_RECAPTURE = 37

def matrix(root: Path):
    """Original paper scripts: 37 positive * 2 + 37 negative * 2 + 36 RR."""
    root = Path(root)
    old = exploratory_matrix(root)
    rows = [dict(x) for x in old if not (
        x["suite"] == "table2" and x["method"] == "reduction_rules")]
    # Submitted table_MQT.py runs WState32 for *both* Hybrid and WMC.
    extra = next(x for x in rows if x["suite"] == "table3_positive"
                 and x["case"] == "wstate32" and x["method"] == "hybrid")
    wmc = dict(extra, method="wmc_only",
               id="table3_positive:wstate32:positive:wmc_only",
               paper_expected="NOT_YET_TRANSCRIBED")
    rows.append(wmc)

    sample = {x["case"] for x in rows if x["suite"] == "figure3"}
    originals = sorted((root / "benchmarks/Feynman").glob("*.qasm"))
    if len(originals) != 36 or len({p.stem for p in originals}) != 36:
        raise ValueError("Expected exactly 36 original Feynman circuits")
    transformed = root / "benchmarks/Feynman/h,y,z,t,tdg,cx"
    if not all((transformed / p.name).is_file() for p in originals):
        raise ValueError("Missing historical Feynman transformed circuit")
    for source in originals:
        if source.stem in sample:
            continue
        rel = "benchmarks/Feynman/" + source.name
        rows.append({
            "id": f"figure3:{source.stem}:positive:reduction_rules",
            "suite": "figure3", "case": source.stem,
            "kind": "positive", "method": "reduction_rules",
            "a": rel, "b": "benchmarks/Feynman/h,y,z,t,tdg,cx/" + source.name,
            "sha_a": None, "sha_b": None,
            "historical_hybrid_timeout": None,
            "paper_expected": "NOT_YET_TRANSCRIBED",
            "provenance": "ORIGINAL_FH_FIG3_QU_PRS_ONLY",
        })

    counts = {
        "positive_hybrid": sum(x["kind"] == "positive" and
                               x["method"] == "hybrid" for x in rows),
        "positive_wmc": sum(x["kind"] == "positive" and
                            x["method"] == "wmc_only" for x in rows),
        "negative_hybrid": sum(x["kind"] == "negative" and
                               x["method"] == "hybrid" for x in rows),
        "negative_wmc": sum(x["kind"] == "negative" and
                            x["method"] == "wmc_only" for x in rows),
        "feynman_rr": sum(x["suite"] == "figure3" and
                          x["method"] == "reduction_rules" for x in rows),
    }
    if counts != dict(positive_hybrid=37, positive_wmc=37,
                      negative_hybrid=37, negative_wmc=37, feynman_rr=36):
        raise ValueError(f"Unexpected canonical QuPRS methods: {counts}")
    if len(rows) != HISTORICAL_DIRECT_CALLS or len({x["id"] for x in rows}) != 184:
        raise ValueError("Canonical 184-call register incomplete/duplicated")
    return rows

def pending_with_rr_recapture(root: Path):
    """Only original calls not covered by earlier results, plus RR stage recapture."""
    rows = []
    for case in matrix(root):
        method = case["method"]
        if method == "hybrid" and case["kind"] == "positive":
            rows.append(case)  # same Hybrid run now records derived RR evidence
        elif method == "wmc_only" and case["case"] != "ghz32":
            rows.append(case)  # all WMC positives and negatives except GHZ32
        elif case["suite"] == "figure3" and case["case"] != "tof_3":
            rows.append(case)
    if len(rows) != PENDING_DIRECT_CALLS + POSITIVE_HYBRID_RECAPTURE:
        raise ValueError("Unexpected 144-case bounded continuation")
    if len({x["id"] for x in rows}) != len(rows):
        raise ValueError("Repeated canonical execution identity")
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", type=Path,
                   default=Path(__file__).resolve().parents[1])
    p.add_argument("--paper", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--cohort", choices=("pending", "all"), default="pending")
    p.add_argument("--list", action="store_true")
    p.add_argument("--shards", type=int, default=24)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--max-cases", type=int, default=6)
    p.add_argument("--watchdog", type=int, default=215)
    a = p.parse_args()
    current = a.current.resolve()
    rows = (pending_with_rr_recapture(current) if a.cohort == "pending"
            else matrix(current))
    if a.list:
        print(json.dumps({"schema": "quprs-tacas26-canonical-v1",
                          "official_direct_calls": 184,
                          "derived_rr_cells": 37,
                          "selected": len(rows), "cases": rows},
                         sort_keys=True, indent=2))
        return
    if a.paper is None or a.output is None:
        p.error("--paper and --output required for actual original-source calls")
    run_parent(current, a.paper.resolve(), a.output, rows, a.shard, a.shards,
               a.max_cases, a.watchdog, matrix_size=HISTORICAL_DIRECT_CALLS)

if __name__ == "__main__":
    main()
