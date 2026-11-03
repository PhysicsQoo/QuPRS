"""Cross-revision and Python/Rust audit for exact-source Bra-CX boundary.

No timing, and no artificial forced WMC. Requires all public API observations
from both independent checked-out revisions. Never silently change EQ vs NEQ.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def audit(base: dict, head: dict) -> dict:
    assert base["schema"] == head["schema"] == "quprs-rr-cx-exact-boundary-v1"
    assert base["revision"] == "base" and head["revision"] == "head"
    assert base["tolerances"] == head["tolerances"]
    assert base["sources"] == head["sources"]
    rows = [*base["observations"], *head["observations"]]
    grouped = defaultdict(dict)
    for row in rows:
        key = (row["case"], row["method"], row["backend"])
        assert row["revision"] not in grouped[key], (row["revision"], key)
        grouped[key][row["revision"]] = row
    assert len(grouped) == 2 * 4 * 2 + 2 * 2 * 2 + 2 * 2, len(grouped)
    observed_equivalence = []
    numeric_observations = []
    rr_to_hybrid_witnesses = []
    for key, revisions in sorted(grouped.items()):
        assert set(revisions) == {"base", "head"}, key
        a, b = revisions["base"], revisions["head"]
        for r in (a, b):
            assert r["truth"] in {"eq", "neq"} and r["verdict"] not in {
                "Timeout", "MemoryOut", "error"
            }, (key, r)
        if a["class"] != b["class"]:
            raise AssertionError(f"Base/HEAD EQ/NEQ boundary divergence {key}: {a} vs {b}")
        if a["wmc_solver_invoked"] != b["wmc_solver_invoked"]:
            raise AssertionError(f"Base/HEAD RR→WMC stage divergence {key}: {a} vs {b}")
        observed_equivalence.append({
            "case": key[0], "method": key[1], "backend": key[2],
            "class": a["class"], "verdict_base": a["verdict"],
            "verdict_head": b["verdict"],
            "solver_invoked": a["wmc_solver_invoked"],
        })
        numeric_observations.extend([a, b])
    # Compare Python and Rust *at the same method and revision*, treating
    # equivalent and equivalent* as one physical EQ class by design.
    for revision in ("base", "head"):
        for case in base["sources"]:
            for method in {"hybrid", "wmc_only", "reduction_rules"}:
                python = grouped.get((case, method, "python"), {}).get(revision)
                rust = grouped.get((case, method, "rust"), {}).get(revision)
                if python is None and rust is None:
                    continue
                assert python and rust, (case, method, revision)
                assert python["class"] == rust["class"], (revision, case, method,
                                                        python, rust)
                # Only compare RR→WMC stage where the method demands it.
                if method == "wmc_only":
                    assert python["wmc_solver_invoked"] is True
                    assert rust["wmc_solver_invoked"] is True
    for revision in ("base", "head"):
        for backend in ("python", "rust"):
            # Existing VQE4 positive pair is known to leave a residual and
            # invoke GPMC, unlike a trivially RR-terminated identity.
            vqe = grouped[("vqe4_real_eq", "hybrid", backend)][revision]
            assert vqe["wmc_solver_invoked"] is True, (
                "Expected real RR→Hybrid→WMC witness missing", revision, backend, vqe
            )
            rr = grouped[("vqe4_real_eq", "reduction_rules", backend)][revision]
            assert rr["wmc_solver_invoked"] is False
            rr_to_hybrid_witnesses.append({
                "revision": revision, "backend": backend,
                "rr_only_verdict": rr["verdict"],
                "hybrid_verdict": vqe["verdict"],
                "hybrid_solver_invoked": True,
                "rr_approximate": vqe["rr_approximate"],
            })
    return {
        "schema": "quprs-rr-cx-boundary-comparison-v1",
        "science": "PASS", "stage": "PASS",
        "base_revision": base["revision"],
        "head_revision": head["revision"],
        "compared_public_api_cases": len(grouped),
        "full_observations": len(rows),
        "physical_eq_neq_boundary_parity": True,
        "rr_to_hybrid_witnesses": rr_to_hybrid_witnesses,
        "cases": observed_equivalence,
        "raw_solver_arithmetic_and_precision": numeric_observations,
        "source_sha256": base["sources"],
        "tolerances": base["tolerances"],
        "policy": ("RR-only unknown permitted; equivalent vs equivalent* "
                   "treated as EQ; no extra magnitude guard; solver print "
                   "precision recorded but not used to override projective-distance verdict"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--head", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    comparison = audit(json.loads(a.base.read_text()), json.loads(a.head.read_text()))
    a.output.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n")
    print("RR_CX_BOUNDARY_SCIENCE_AND_STAGE_PASS=" + json.dumps({
        "compared_keys": comparison["compared_public_api_cases"],
        "observations": comparison["full_observations"],
        "rr_to_hybrid": comparison["rr_to_hybrid_witnesses"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
