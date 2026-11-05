#!/usr/bin/env python3
"""Original tiny exact-rational complex WMC/PWMC reference oracle.

Research-only. No solver-specific code, imports, or heuristics.
Count in C_Q = Q + iQ using Python stdlib Fraction.
No f64, MPFR, probability assumptions, or numerical acceptance bands.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from fractions import Fraction
from pathlib import Path

ZERO = (Fraction(0), Fraction(0))
ONE = (Fraction(1), Fraction(0))


def cadd(x, y):
    return (x[0] + y[0], x[1] + y[1])


def cmul(x, y):
    return (x[0]*y[0] - x[1]*y[1], x[0]*y[1] + x[1]*y[0])


def cpair(re, im):
    return Fraction(str(re)), Fraction(str(im))


def ctext(x):
    return {"re": str(x[0]), "im": str(x[1])}


def weight(c, variable, value):
    row = c.get("weights", {}).get(str(variable), ["1", "0", "1", "0"])
    return cpair(*(row[:2] if value else row[2:]))


def satisfies(c, assignment):
    return all(any(assignment[abs(lit)] == (lit > 0) for lit in clause)
               for clause in c["clauses"])


def valid(c):
    n = c["nvars"]
    assert isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 8
    assert c["mode"] in ("wmc", "pwmc")
    assert isinstance(c["id"], str) and c["id"]
    assert isinstance(c["clauses"], list)
    assert all(isinstance(cl, list) and
               all(type(lit) is int and lit != 0 and abs(lit) <= n for lit in cl)
               for cl in c["clauses"])
    projection = c.get("projection", [])
    if c["mode"] == "pwmc":
        assert len(set(projection)) == len(projection)
        assert all(type(v) is int and 1 <= v <= n for v in projection)
    else:
        assert not projection, "Full WMC must not carry projection"
    for var, row in c.get("weights", {}).items():
        assert var == str(int(var)) and 1 <= int(var) <= n
        assert len(row) == 4
        for part in row:
            Fraction(str(part))
        if c["mode"] == "pwmc":
            assert int(var) in projection, "Existential weights need a different semantics"
    assert set(c["expected"]) == {"value", "sat_models", "distinct_projected_models"}


def brute_force(c):
    """Enumerate full assignments; deduplicate satisfying projected assignments."""
    n = c["nvars"]
    projected = c["mode"] == "pwmc"
    pvars = tuple(sorted(c.get("projection", [])))
    seen = set()
    count = ZERO
    sat_models = 0
    for bits in itertools.product((False, True), repeat=n):
        assignment = {i+1: bits[i] for i in range(n)}
        if not satisfies(c, assignment):
            continue
        sat_models += 1
        key = tuple(assignment[v] for v in pvars)
        if projected:
            if key in seen:
                continue
            seen.add(key)
        term = ONE
        for v in (pvars if projected else range(1, n+1)):
            term = cmul(term, weight(c, v, assignment[v]))
        count = cadd(count, term)
    return count, sat_models, len(seen) if projected else None


def projected_existential_oracle(c):
    """Independent projection-first semantics: enumerate projected assignments,
    SAT-check each with a separate existential enumeration (no seen/hash dedup).
    """
    if c["mode"] != "pwmc":
        return None
    n = c["nvars"]
    p = tuple(sorted(c.get("projection", [])))
    e = tuple(v for v in range(1, n+1) if v not in set(p))
    value = ZERO
    projected_count = 0
    for pb in itertools.product((False, True), repeat=len(p)):
        fixed = dict(zip(p, pb))
        exists = False
        for eb in itertools.product((False, True), repeat=len(e)):
            assignment = {**fixed, **dict(zip(e, eb))}
            if satisfies(c, assignment):
                exists = True
                break
        if exists:
            projected_count += 1
            term = ONE
            for v in p:
                term = cmul(term, weight(c, v, fixed[v]))
            value = cadd(value, term)
    return value, projected_count


def mutate(c, kind):
    m = copy.deepcopy(c)
    n = c["nvars"]
    if kind == "clause_order":
        m["clauses"] = [list(reversed(cl)) for cl in reversed(m["clauses"])]
    elif kind == "idempotent_clause":
        if m["clauses"]:
            m["clauses"].append(copy.deepcopy(m["clauses"][0]))
    elif kind == "rename":
        if n:
            rename = lambda v: (n + 1 - v) if v > 0 else -(n + 1 + v)
            m["clauses"] = [[rename(l) for l in cl] for cl in m["clauses"]]
            m["weights"] = {str(rename(int(v))): w for v, w in c.get("weights", {}).items()}
            if c["mode"] == "pwmc":
                m["projection"] = [rename(v) for v in c["projection"]]
    elif kind == "tautology":
        if n:
            m["clauses"].append([1, -1])
    else:
        raise AssertionError(kind)
    return m


def run(path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    assert obj["schema_version"] == 1
    cases = obj["cases"]
    assert len(cases) == 24
    assert len({c["id"] for c in cases}) == len(cases)
    if obj.get("profile") == "quprs_complex_positive_weight_negative_literal_unity":
        for case in cases:
            for w in case.get("weights", {}).values():
                assert Fraction(w[2]) == 1 and Fraction(w[3]) == 0, (
                    case["id"], "QuPRS requires negative-polarity literal weight 1")
    results = []
    for c in cases:
        valid(c)
        got, sat, projected = brute_force(c)
        want = cpair(c["expected"]["value"]["re"], c["expected"]["value"]["im"])
        assert got == want, (c["id"], "count", ctext(got), ctext(want))
        assert sat == c["expected"]["sat_models"], (c["id"], "sat count")
        assert projected == c["expected"]["distinct_projected_models"], (c["id"], "projection count")
        if c["mode"] == "pwmc":
            v2, p2 = projected_existential_oracle(c)
            assert v2 == got and p2 == projected, (c["id"], "projection-first mismatch")
        for kind in ("clause_order", "idempotent_clause", "rename", "tautology"):
            m = mutate(c, kind)
            got2, sat2, projected2 = brute_force(m)
            assert (got2, sat2, projected2) == (got, sat, projected), (c["id"], kind)
            if m["mode"] == "pwmc":
                v2, p2 = projected_existential_oracle(m)
                assert (v2, p2) == (got, projected), (c["id"], kind, "projection-first")
        casebytes = json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        results.append({"id": c["id"], "value": ctext(got),
                        "satisfying_full_models": sat,
                        "satisfying_distinct_projections": projected,
                        "case_sha256": hashlib.sha256(casebytes).hexdigest()})

    by_id = {r["id"]: r for r in results}
    if obj.get("profile") == "quprs_complex_positive_weight_negative_literal_unity":
        assert by_id["qp_pure_literal_elimination_unsafe"]["value"] == {"re": "11", "im": "0"}
        assert by_id["qp_equivalence_elimination_weight_merge"]["value"] == {"re": "11", "im": "0"}
        assert by_id["qp_projected_cancel"]["value"] == {"re": "0", "im": "0"}
        assert by_id["qp_projected_cancel"]["satisfying_distinct_projections"] == 4
        assert by_id["qp_tiny_imag_residual"]["value"]["re"] == "0"
        assert by_id["qp_tiny_imag_residual"]["value"]["im"] == "1/10000000000000000000000000000000000000000"
        # Even when the negative literal is exactly 1+0i, weighted free variables
        # and non-conserving SAT preprocessing still affect the true count.
    else:
        assert by_id["sat_real_cancel_zero"]["satisfying_full_models"] > 0
        assert by_id["sat_real_cancel_zero"]["value"] == by_id["unsat_contradiction"]["value"]
        assert by_id["same_cnf_weights_v1"]["value"] != by_id["same_cnf_weights_v2"]["value"]
        assert by_id["projected_or_dedup"]["satisfying_full_models"] == 3
        assert by_id["projected_or_dedup"]["satisfying_distinct_projections"] == 2
        # An explicit f64 failure witness: exact count = 1, float rounds it to 0.
        big = next(c for c in cases if c["id"] == "forty_digit_cancellation")
        row = big["weights"]["1"]
        assert (Fraction(row[0]) + Fraction(row[2])) == 1
        assert (float(row[0]) + float(row[2])) == 0.0
    return {"status": "RAWMOCS_A0_EXACT_ORACLE_PASS_24_OF_24",
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "cases": len(results),
            "checks_per_case": ["direct enumeration", "reference expected",
                                "SAT and projected cardinalities", "projection-first independent oracle",
                                "clause order", "clause idempotence", "variable renaming",
                                "tautology preservation"],
            "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("complex_count_fixtures.json"))
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.fixtures)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, sort_keys=True))


if __name__ == "__main__":
    main()
