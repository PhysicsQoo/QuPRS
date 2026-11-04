"""Read-only structural audit of archived, source-pinned QuPRS weighted CNFs.

Metrics concern input CNF only, NOT runtime preprocessing, cache behavior or
solver performance. A matching original science-report SHA is mandatory.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path


def analyze(raw: bytes) -> dict:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("CNF is not UTF-8") from exc
    variables = expected_clauses = None
    weights: dict[int, tuple[str, str]] = {}
    clauses: list[list[int]] = []
    for lineno, text in enumerate(lines, 1):
        tokens = text.strip().split()
        if not tokens:
            continue
        if tokens[:2] == ["p", "cnf"]:
            if variables is not None or len(tokens) != 4:
                raise ValueError(f"bad/multiple CNF header at line {lineno}")
            variables, expected_clauses = map(int, tokens[2:])
            if variables < 1 or expected_clauses < 0:
                raise ValueError("invalid CNF dimensions")
        elif tokens[:3] == ["c", "p", "weight"]:
            if len(tokens) != 7 or tokens[-1] != "0":
                raise ValueError(f"malformed complex weight at line {lineno}")
            literal = int(tokens[3])
            real, imag = tokens[4:6]
            if literal == 0 or literal in weights:
                raise ValueError(f"invalid/duplicate literal weight at line {lineno}")
            try:
                if not (Decimal(real).is_finite() and Decimal(imag).is_finite()):
                    raise ValueError("nonfinite weight")
            except InvalidOperation as exc:
                raise ValueError("nonnumeric weight") from exc
            weights[literal] = (real, imag)
        elif tokens[0] == "c":
            continue
        else:
            if variables is None:
                raise ValueError("clause before header")
            literals = list(map(int, tokens))
            if not literals or literals[-1] != 0 or 0 in literals[:-1]:
                raise ValueError(f"invalid clause at line {lineno}")
            if any(abs(x) > variables for x in literals[:-1]):
                raise ValueError(f"clause literal out of range at line {lineno}")
            clauses.append(literals[:-1])
    if variables is None or expected_clauses != len(clauses):
        raise ValueError("CNF header clause count mismatch")
    if any(abs(k) > variables for k in weights):
        raise ValueError("weighted literal out of range")
    weight_variables = {abs(k) for k in weights}
    if any(v not in weights or -v not in weights for v in weight_variables):
        raise ValueError("missing positive/negative literal weight pair")
    # d4 Main.cpp::runPreproc compares the stored positive/negative strings.
    protected_by_d4 = {v for v in weight_variables if weights[v] != weights[-v]}
    asym_numeric = {v for v in weight_variables if
                    tuple(Decimal(t) for t in weights[v]) !=
                    tuple(Decimal(t) for t in weights[-v])}
    parent = list(range(variables + 1))

    def find(v: int) -> int:
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    def union(u: int, v: int) -> None:
        a, b = find(u), find(v)
        if a != b:
            parent[b] = a

    counts = Counter()
    seen = set()
    weighted_clause_count = weighted_occurrences = 0
    binary_type = Counter()
    for clause in clauses:
        counts[len(clause)] += 1
        if not clause:
            continue
        wa = sum(abs(v) in weight_variables for v in clause)
        weighted_clause_count += wa > 0
        weighted_occurrences += wa
        if len(clause) == 2:
            binary_type["WW" if wa == 2 else "WU" if wa == 1 else "UU"] += 1
        v0 = abs(clause[0])
        for lit in clause:
            seen.add(abs(lit))
            union(v0, abs(lit))
    components = Counter(find(v) for v in range(1, variables + 1))
    weighted_components = Counter(find(v) for v in weight_variables)
    return {
        "source_sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
        "variables": variables,
        "clauses": len(clauses),
        "weighted_variables": len(weight_variables),
        "d4_string_protected_variables": len(protected_by_d4),
        "numeric_asymmetric_weight_variables": len(asym_numeric),
        "unweighted_variables": variables - len(weight_variables),
        "literal_weight_records": len(weights),
        "clause_lengths": {str(k): counts[k] for k in sorted(counts)},
        "binary_share": round(counts[2] / len(clauses), 6) if clauses else 0,
        "binary_type_counts": dict(binary_type),
        "clauses_with_weighted_variables": weighted_clause_count,
        "weighted_literal_occurrences": weighted_occurrences,
        "max_weighted_literals_per_clause": max(
            (sum(abs(v) in weight_variables for v in clause) for clause in clauses),
            default=0,
        ),
        "unmentioned_variables": variables - len(seen),
        "original_primal_graph_components": sorted(components.values(), reverse=True),
        "original_components_weighted_counts": sorted(
            (weighted_components[rep] for rep in components), reverse=True
        ),
        "meaning": "unpreprocessed source CNF; NOT solver runtime components or causal latency attribution",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = json.loads(args.science_report.read_text())
    if report.get("complete") is not True:
        raise ValueError("Incomplete original source-CNF science admission")
    observed = {}
    for case, record in report["cases"].items():
        source = args.cnf_dir / (case + ".cnf")
        value = analyze(source.read_bytes())
        if value["source_sha256"] != record["same_cnf_sha256"]:
            raise ValueError(f"CNF provenance SHA mismatch: {case}")
        observed[case] = value
    if len(observed) != 4:
        raise ValueError("Expected four original source CNFs")
    result = {
        "study": "QOO-157 actual source-CNF structural audit",
        "measurement_head_sha": "efab7ccd132214758d4209d0b5c4f6488f30695e",
        "original_artifact_id": 13317939531,
        "structural_analysis_only": True,
        "not_preprocessing_or_runtime_evidence": True,
        "solver_precision_fairness_inherited_from_original_science_report": True,
        "cases": observed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "case_count": len(observed),
        "all_weighted_are_d4_protected": all(
            v["weighted_variables"] == v["d4_string_protected_variables"]
            for v in observed.values()
        ),
        "original_primal_component_sizes": {
            k: v["original_primal_graph_components"] for k, v in observed.items()
        },
        "output": str(args.out),
    }))


if __name__ == "__main__":
    main()
