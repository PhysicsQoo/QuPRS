#!/usr/bin/env python3
"""RaWMoCS A0e: adversarial weighted-component cache context oracle.

Research-only exact-rational arithmetic, no cache implementation and no solver.
Uses the original independent exhaustive Python reference, not upstream code.
"""
from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

from exact_complex_oracle import (
    brute_force,
    ctext,
    projected_existential_oracle,
    valid,
)


def normalize(raw):
    if raw["mode"] not in ("wmc", "epwmc"):
        raise ValueError("Unexpected counting mode")
    expected = raw["expected"]
    result = dict(raw)
    result["mode"] = "pwmc" if raw["mode"] == "epwmc" else "wmc"
    result["id"] = "A0e temporary reference state"
    result["expected"] = {
        "value": {"re": expected["re"], "im": expected["im"]},
        "sat_models": expected["sat_models"],
        "distinct_projected_models": expected["projected_models"],
    }
    valid(result)
    return result


def check_state(raw):
    state = normalize(raw)
    count, sat, projected = brute_force(state)
    want = state["expected"]
    exact_want = (Fraction(want["value"]["re"]), Fraction(want["value"]["im"]))
    assert count == exact_want, (state, "complex", ctext(count), want["value"])
    assert sat == want["sat_models"], (state, "sat", sat, want["sat_models"])
    assert projected == want["distinct_projected_models"], (
        state, "projection", projected, want["distinct_projected_models"]
    )
    if state["mode"] == "pwmc":
        alt_count, alt_projected = projected_existential_oracle(state)
        assert (alt_count, alt_projected) == (count, projected), (
            state, "projection first oracle"
        )
    return count, sat, projected


def run(path):
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == 1
    pairs = raw["pairs"]
    assert len(pairs) == 20
    assert len({pair["id"] for pair in pairs}) == 20
    relations = {"equal": 0, "different": 0, "sat-different": 0}
    for pair in pairs:
        a = check_state(pair["left"])
        b = check_state(pair["right"])
        relation = pair["assert"]
        assert relation in relations
        if relation == "equal":
            assert a[0] == b[0], (pair["id"], "expected identical complex count")
            assert (a[1] > 0) == (b[1] > 0), (pair["id"], "logical status drift")
        elif relation == "different":
            assert a[0] != b[0], (pair["id"], "expected distinguishable count")
        else:
            assert a[0] == b[0] and a[0] == (Fraction(0), Fraction(0))
            assert (a[1] > 0) != (b[1] > 0), (pair["id"], "SAT status must differ")
        relations[relation] += 1

    # Counterexample to multiplying components that SHARE a variable x.
    # A=(x|y), B=(!x|z). Each locally has 3 models, but together 4, not 9.
    left = {"mode": "wmc", "nvars": 2, "clauses": [[1, 2]], "weights": {}}
    right = {"mode": "wmc", "nvars": 2, "clauses": [[-1, 2]], "weights": {}}
    joined = {"mode": "wmc", "nvars": 3,
              "clauses": [[1, 2], [-1, 3]], "weights": {}}
    for s in (left, right, joined):
        s["expected"] = {"re": "3" if s is not joined else "4", "im": "0",
                         "sat_models": 3 if s is not joined else 4,
                         "projected_models": None}
    aa, _, _ = check_state(left)
    bb, _, _ = check_state(right)
    whole, _, _ = check_state(joined)
    assert aa[0] * bb[0] == Fraction(9)
    assert whole[0] == Fraction(4)
    assert whole != (aa[0]*bb[0], Fraction(0)), "sharing variable forbids product"

    # F=x, w(x)=i -> after assigning x=true the residual is ⊤ over zero vars.
    # Cached residual count is 1; the caller owns its i factor. Do not cache i
    # under the same canonical empty-residual key.
    forced = {"mode": "wmc", "nvars": 1, "clauses": [[1]],
              "weights": {"1": ["0", "1", "1", "0"]},
              "expected": {"re": "0", "im": "1",
                           "sat_models": 1, "projected_models": None}}
    residual = {"mode": "wmc", "nvars": 0, "clauses": [], "weights": {},
                "expected": {"re": "1", "im": "0",
                             "sat_models": 1, "projected_models": None}}
    weighted_count, _, _ = check_state(forced)
    residual_count, _, _ = check_state(residual)
    assert weighted_count == (-residual_count[1], residual_count[0])
    assert weighted_count != residual_count

    # The zero count for SAT may arise from a zero literal or cancellation:
    # cannot use complex-zero as logical UNSAT nor divide out zero weights.
    assert relations == {"equal": 6, "different": 13, "sat-different": 1}
    return {"status": "RAWMOCS_A0E_CACHE_CONTEXT_SCIENCE_PASS",
            "exact_context_pairs": len(pairs),
            "states_checked": len(pairs) * 2 + 5,
            "relations": relations,
            "cross_component_shared_variable_counterexample": "4 != 3*3",
            "prefix_factor_owned_outside_residual_cache": "i * 1 = i",
            "scope": "research-only oracle, not solver cache implementation"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path,
                        default=Path(__file__).with_name("cache_context_fixtures.json"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = run(args.fixtures)
    report = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
