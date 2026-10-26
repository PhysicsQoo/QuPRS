#!/usr/bin/env python3
"""Compare real Rust VQE4 emitted weighted CNF and solver time on one VM.

Research diagnostic only. Old-vs-new angle models are scientifically
different, so comparisons do not certify equality of emitted weighted CNFs.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path("vqe4-cnf-evidence")
VARIANTS = ("base", "head")
GATES = ("ganak", "gpmc")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def profile_cnf(path):
    lines = Path(path).read_text().splitlines()
    hdr = [line for line in lines if line.startswith("p cnf ")]
    if len(hdr) != 1:
        raise ValueError("Unexpected CNF header")
    _, _, nvars, nclauses = hdr[0].split()
    weight_lines = [line for line in lines if line.startswith("c p weight ")]
    clauses = [line for line in lines if line and not line.startswith(("c ", "p "))]
    if len(clauses) != int(nclauses):
        raise ValueError("Unexpected clause count")
    weights = Counter(" ".join(line.split()[4:]) for line in weight_lines)
    clause_width = Counter(len(line.split()) - 1 for line in clauses)
    return {
        "sha256": sha(path), "vars": int(nvars), "clauses": int(nclauses),
        "weighted_literal_entries": len(weight_lines),
        "weight_token_multiset": dict(sorted(weights.items())),
        "clause_width_histogram": dict(sorted(clause_width.items())),
    }

def run():
    ROOT.mkdir(exist_ok=True)
    binaries = {}
    for v in VARIANTS:
        folder = ROOT / v
        if not (folder / "vqe4-ganak.cnf").is_file():
            raise ValueError("Missing exact native CNF export " + v)
        for solver in GATES:
            profile = profile_cnf(folder / f"vqe4-{solver}.cnf")
            (folder / f"{solver}-profile.json").write_text(json.dumps(profile, indent=2) + "\n")
        binaries[v] = sha(folder / "ganak")
    if len(set(binaries.values())) != 1:
        raise ValueError("Base/head Ganak binaries differ")
    records = []
    for i, v in enumerate(("base", "head", "head", "base")):
        for warm in (True, True, False, False, False, False, False, False):
            command = [str((ROOT / v / "ganak").resolve()), "--mode=6",
                       str((ROOT / v / "vqe4-ganak.cnf").resolve())]
            start = time.perf_counter_ns()
            proc = subprocess.run(command, capture_output=True, text=True, timeout=45)
            elapsed = (time.perf_counter_ns() - start) / 1e9
            if proc.returncode != 0:
                raise RuntimeError(f"Ganak failed: variant={v} exit={proc.returncode} stderr={proc.stderr[-900:]}")
            row = {
                "round": i, "revision": v, "warmup": warm,
                "duration_seconds": elapsed, "solver_binary_sha256": binaries[v],
                "weighted_cnf_sha256": sha(ROOT / v / "vqe4-ganak.cnf"),
                "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
                "stdout_tail": proc.stdout[-1100:],
                "stderr_tail": proc.stderr[-300:],
            }
            records.append(row)
            print(f"VQE4_RAW round={i} revision={v} warmup={warm} wall={elapsed:.6f}", flush=True)
    (ROOT / "trials.json").write_text(json.dumps(records, indent=2) + "\n")
    grouped = {v: [x["duration_seconds"] for x in records
                   if x["revision"] == v and not x["warmup"]] for v in VARIANTS}
    if any(len(vals) != 12 for vals in grouped.values()):
        raise ValueError("Unbalanced measured samples")
    summary = {
        "schema": "vqe4-ganak-source-cnf-diagnostic-v1",
        "notes": [
            "Both CNFs originate from actual Rust proportional Hybrid miters with reduction",
            "Same VM and bit-identical Ganak binary; source models differ across historical revisions",
            "CNF weight histograms ignore variable identity and are descriptive, not semantic equivalence proofs",
            "Same raw CNF different SHA can arise from hash-map ordering",
            "One hosted VM is not fixed physical hardware or a solver arithmetic certificate",
        ],
        "medians": {v: statistics.median(vals) for v, vals in grouped.items()},
        "samples": {v: len(vals) for v, vals in grouped.items()},
        "ratio_head_over_base": statistics.median(grouped["head"]) / statistics.median(grouped["base"]),
        "cnf": {v: {solver: json.loads((ROOT/v/f"{solver}-profile.json").read_text())
                    for solver in GATES} for v in VARIANTS},
        "phase_source_sha256": {v: sha(ROOT/v/"phase-signatures.tsv") for v in VARIANTS},
        "solver_sha256": binaries,
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("VQE4_ANALYSIS " + json.dumps({
        "medians": summary["medians"], "ratio": summary["ratio_head_over_base"],
        "vars": {v: summary["cnf"][v]["ganak"]["vars"] for v in VARIANTS},
        "clauses": {v: summary["cnf"][v]["ganak"]["clauses"] for v in VARIANTS},
        "phase_sources_equal": len(set(summary["phase_source_sha256"].values())) == 1,
    }), flush=True)

if __name__ == "__main__":
    run()
