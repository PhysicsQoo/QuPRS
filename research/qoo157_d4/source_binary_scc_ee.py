"""Binary-implication SCC audit of original QuPRS source weighted CNFs.

Independent source-structural calculation, not a solver, benchmark, SAT proof
of the whole weighted CNF, nor a certified numerical WMC error bound.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from hashlib import sha256
import argparse
import json
from pathlib import Path

CASES = ("grover4_eq", "qaoa7_neq", "qpeexact8_eq", "qft16_eq")
NATIVE_CASES = ("qaoa7_neq", "qft16_eq")


def parse(raw: bytes) -> tuple[int, list[list[int]], set[int]]:
    nvars = nclauses = None
    clauses = []
    weighted = set()
    for line in raw.decode("utf-8").splitlines():
        s = line.split()
        if not s:
            continue
        if s[:2] == ["p", "cnf"]:
            if nvars is not None or len(s) != 4:
                raise ValueError("bad/duplicate DIMACS header")
            nvars, nclauses = int(s[2]), int(s[3])
        elif s[:3] == ["c", "p", "weight"]:
            weighted.add(abs(int(s[3])))
        elif s[0] == "c":
            continue
        else:
            if nvars is None or s[-1] != "0":
                raise ValueError("malformed source clause")
            clause = [int(v) for v in s[:-1]]
            if any(v == 0 or abs(v) > nvars for v in clause):
                raise ValueError("out of range variable")
            clauses.append(clause)
    if nvars is None or nclauses is None or len(clauses) != nclauses:
        raise ValueError("original source CNF clause count mismatch")
    if any(v < 1 or v > nvars for v in weighted):
        raise ValueError("weighted literal out of range")
    return nvars, clauses, weighted


def binary_scc(nvars: int, clauses: list[list[int]], weighted: set[int]) -> dict:
    n = nvars * 2
    graph = [[] for _ in range(n)]
    back = [[] for _ in range(n)]
    def node(lit: int) -> int:
        return 2 * (abs(lit) - 1) + int(lit < 0)

    binary_count = 0
    for clause in clauses:
        if len(clause) != 2:
            continue
        x, y = clause
        binary_count += 1
        for a, b in ((-x, y), (-y, x)):
            u, v = node(a), node(b)
            graph[u].append(v)
            back[v].append(u)

    # Kosaraju without recursion, so the source audit is bounded and robust.
    seen = set()
    finish = []
    for root in range(n):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, 0)]
        while stack:
            u, idx = stack[-1]
            if idx >= len(graph[u]):
                finish.append(u)
                stack.pop()
                continue
            stack[-1] = (u, idx + 1)
            v = graph[u][idx]
            if v not in seen:
                seen.add(v)
                stack.append((v, 0))

    component = [-1] * n
    next_comp = 0
    for root in reversed(finish):
        if component[root] != -1:
            continue
        component[root] = next_comp
        stack = [root]
        while stack:
            u = stack.pop()
            for v in back[u]:
                if component[v] == -1:
                    component[v] = next_comp
                    stack.append(v)
        next_comp += 1

    groups = defaultdict(list)
    for var in range(1, nvars + 1):
        plus, minus = component[node(var)], component[node(-var)]
        if plus == minus:
            raise ValueError("binary clauses alone imply opposite literal equivalence")
        # For any consistent implication 2-CNF, SCC negation is an involution.
        key = tuple(sorted((plus, minus)))
        groups[key].append(var)
    all_merged = [g for g in groups.values() if len(g) > 1]
    group_sizes = Counter(len(g) for g in all_merged)
    weighted_groups = Counter(
        (len(g), sum(v in weighted for v in g)) for g in all_merged
    )
    return {
        "binary_clauses": binary_count,
        "literal_scc_count": next_comp,
        "equivalence_group_sizes": {str(k): v for k, v in sorted(group_sizes.items())},
        "equivalence_group_sizes_x_weighted_counts": {
            f"size{k[0]}_weighted{k[1]}": v for k, v in sorted(weighted_groups.items())
        },
        "binary_only_equivalent_variables_eliminable": sum(len(g) - 1 for g in all_merged),
        "weighted_variables_in_equivalence_groups": sum(
            sum(v in weighted for v in g) for g in all_merged
        ),
        "source_weighted_variable_count": len(weighted),
        "projected_variable_semantics_not_inferred": True,
    }


def audit(cnf_dir: Path, original: Path, native: Path, out: Path) -> dict:
    archive = json.loads(original.read_text())
    trace = json.loads(native.read_text())
    if archive.get("complete") is not True or trace.get("status") != (
        "COMPLETE_GPMC_STAGE_TRACE_SCIENCE_PASS"
    ):
        raise ValueError("original SCIENCE or native GPMC EE stage evidence invalid")
    report = {
        "status": "INCOMPLETE",
        "source_artifact": 13317939531,
        "native_stage_artifact": 13327644747,
        "not_timing_not_solver_proof": True,
        "cases": {}
    }
    for case in CASES:
        file = cnf_dir / (case + ".cnf")
        raw = file.read_bytes()
        digest = sha256(raw).hexdigest()
        if digest != archive["cases"][case]["same_cnf_sha256"]:
            raise ValueError("original CNF SHA mismatch " + case)
        nvars, clauses, weights = parse(raw)
        row = {
            "sha256": digest, "vars": nvars, "source_clauses": len(clauses),
            **binary_scc(nvars, clauses, weights)
        }
        if case in NATIVE_CASES:
            native_case = trace["cases"][case]
            if digest != native_case["source_cnf_sha256"]:
                raise ValueError("native GPMC source SHA mismatch")
            gpmc = native_case["variants"]["ee_on"]
            eliminated = gpmc["equiv_stage_attributable_vars"]
            deleted = gpmc["equiv_stage_attributable_clauses"]
            row["gpmc_EE_eliminated_variables"] = eliminated
            row["gpmc_EE_eliminated_clauses"] = deleted
            row["binary_SCC_versus_GPMC_EE_var_count_equal"] = (
                row["binary_only_equivalent_variables_eliminable"] == eliminated
            )
            if not row["binary_SCC_versus_GPMC_EE_var_count_equal"]:
                raise ValueError("independent graph SCC count != GPMC native EE")
            if deleted != 2 * eliminated:
                raise ValueError("unexpected native GPMC EE clause pattern")
        report["cases"][case] = row
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")
    report["status"] = "SOURCE_SCC_NATIVE_EE_CROSSCHECK_PASS"
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--original-science", type=Path, required=True)
    p.add_argument("--gpmc-native", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = audit(
        args.cnf_dir, args.original_science, args.gpmc_native, args.out)
    print(json.dumps({
        "status": result["status"],
        "source_binary_equivalence": {
            case: {
                "binary_scc_eliminable": row["binary_only_equivalent_variables_eliminable"],
                "weighted_in_groups": row["weighted_variables_in_equivalence_groups"],
                "gpmc_ee_eliminated": row.get("gpmc_EE_eliminated_variables")
            } for case, row in result["cases"].items()
        }
    }))
