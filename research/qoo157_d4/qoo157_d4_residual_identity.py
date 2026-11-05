"""QOO-157 source-level native d4 BiPe residual formula fingerprint study.

This is an untimed structural audit, NOT a performance benchmark or an
independent quantum-WMC arithmetic certificate. Preserve full raw residual
formula dumps under the artifact and hash canonical literal clause multisets.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import subprocess

from qoo157_bipe_options import CASES, OPTIONS, TIMEOUT_SECONDS
from qoo157_preprocess_compare import D4_RESULT
from gpmc_td_ablation import COMPLEX
from gpmc_vs_td_factorial import close_enough


def parse_formula(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    nvars = clauses_expected = None
    clauses, weights, projection, protected = [], [], None, None
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "v" and len(parts) == 2 and nvars is None:
            nvars = int(parts[1])
        elif tag == "c" and len(parts) == 2 and clauses_expected is None:
            clauses_expected = int(parts[1])
        elif tag == "p" and projection is None:
            projection = sorted(int(x) for x in parts[1:])
        elif tag == "b" and protected is None:
            protected = sorted(int(x) for x in parts[1:])
        elif tag == "w" and len(parts) >= 3:
            weights.append((int(parts[1]), " ".join(parts[2:])))
        elif tag == "l":
            clause = tuple(sorted(int(x) for x in parts[1:]))
            if not clause or any(v == 0 or abs(v) > nvars for v in clause):
                raise ValueError("invalid residual native clause")
            clauses.append(clause)
        else:
            raise ValueError("unrecognized residual formula record: " + line[:100])
    if nvars is None or clauses_expected is None or projection is None or protected is None:
        raise ValueError("residual metadata incomplete")
    if any(v <= 0 or v > nvars for v in protected + projection):
        raise ValueError("projection or protected variable out of bounds")
    if len(set(protected)) != len(protected) or len(set(projection)) != len(projection):
        raise ValueError("duplicate variable in projection/protected list")
    if len(clauses) != clauses_expected:
        raise ValueError("native residual clause count mismatch")
    def digest(value):
        return sha256(json.dumps(value, separators=(",", ":"), ensure_ascii=True
                                ).encode()).hexdigest()
    canon_clauses = sorted(clauses)
    canon_weights = sorted(weights)
    if len(canon_weights) != len(set(k for k, _ in canon_weights)):
        raise ValueError("duplicate literal weight key")
    return {
        "vars": nvars,
        "clauses": clauses_expected,
        "projected_count": len(projection),
        "weight_entries": len(weights),
        "protected_count": len(protected),
        "canonical_clause_multiset_sha256": digest(canon_clauses),
        "canonical_weight_text_sha256": digest(canon_weights),
        "canonical_projection_sha256": digest(projection),
        "canonical_protected_sha256": digest(protected),
        "canonical_combined_sha256": digest({
            "vars": nvars, "clauses": canon_clauses,
            "weight_strings": canon_weights, "projection": projection,
            "protected": protected
        }),
    }


def run_once(binary: str, path: Path, variant: str, out_file: Path) -> dict:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["QOO157_RESIDUAL_DUMP"] = str(out_file.resolve())
    cp = subprocess.run(
        [binary, "-i", str(path), *OPTIONS[variant]],
        env=env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
        check=False
    )
    if cp.returncode:
        raise RuntimeError(f"d4 {variant} rc={cp.returncode}: {cp.stderr[:300]}")
    counts = D4_RESULT.findall(cp.stdout)
    if len(counts) != 1:
        raise ValueError("Expected exactly one d4 complex WMC printed result")
    match = COMPLEX.fullmatch(counts[0].strip())
    if not match:
        raise ValueError("Malformed d4 complex count")
    if not out_file.is_file():
        raise ValueError("native residual dump not written")
    return {
        "real": str(Decimal(match.group(1))),
        "imag": str(Decimal(match.group(2))),
        "residual_dump_sha256": sha256(out_file.read_bytes()).hexdigest(),
        "canonical": parse_formula(out_file.read_bytes()),
        "flags": list(OPTIONS[variant])
    }


def study(binary: Path, cnfdir: Path, source_report: Path,
          dumps: Path, output: Path) -> dict:
    archived = json.loads(source_report.read_text())
    if archived.get("complete") is not True:
        raise ValueError("Original archived science report not completed")
    report = {
        "status": "INCOMPLETE",
        "research_id": "QOO-157",
        "archive_id": 13317939531,
        "d4_source_commit": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
        "d4_scratch_binary_sha256": sha256(binary.read_bytes()).hexdigest(),
        "native_dump_is_only_science_not_performance": True,
        "internal_wmc_arithmetic_certified": False,
        "cases": {}
    }
    for case in CASES:
        cnf = cnfdir / (case + ".cnf")
        digest = sha256(cnf.read_bytes()).hexdigest()
        original = archived["cases"][case]
        if digest != original["same_cnf_sha256"]:
            raise ValueError("source weighted CNF SHA mismatch: " + case)
        obs = original["precision_pairs"]["38"]["observations"]["d4-38"]
        if obs["status"] != "COMPLETED":
            raise ValueError("source d4 count missing")
        with localcontext() as ctx:
            ctx.prec = 100
            reference = tuple(
                Decimal(Fraction(obs[k]).numerator) /
                Decimal(Fraction(obs[k]).denominator)
                for k in ("real", "imag")
            )
        row = {"original_cnf_sha256": digest, "variants": {}}
        report["cases"][case] = row
        for v in OPTIONS:
            rawfile = dumps / f"{case}_{v}.residual"
            data = run_once(str(binary), cnf, v, rawfile)
            value = (Decimal(data["real"]), Decimal(data["imag"]))
            ok, delta, allowed = close_enough(value, reference)
            if not ok:
                raise ValueError(f"{case}/{v}: WMC count inconcordant {delta}>{allowed}")
            data.update({"count_status": "COUNT_CONCORDANT_UNCERTIFIED",
                         "count_delta": delta, "count_screen": allowed})
            row["variants"][v] = data
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2) + "\n")
        # The no-BiPe control must preserve original residual clauses, but
        # original parser may already eliminate tautologies; do not compare
        # to raw CNF SHA directly without canonicalizing the raw grammar.
    # Compare content, not merely dimensions: different canonical clause
    # hashes do not, by themselves, prove different weighted-count semantics.
    # Separate protected/projection and textual weight identities from clauses.
    variants = list(OPTIONS)
    report["same_source_option_pairs"] = {}
    for case, row in report["cases"].items():
        comparisons = {}
        for i, left in enumerate(variants):
            for right in variants[i + 1:]:
                a = row["variants"][left]["canonical"]
                b = row["variants"][right]["canonical"]
                comparisons[left + "__vs__" + right] = {
                    "same_var_and_clause_count": (
                        a["vars"] == b["vars"] and a["clauses"] == b["clauses"]),
                    "same_clause_multiset": (
                        a["canonical_clause_multiset_sha256"] ==
                        b["canonical_clause_multiset_sha256"]),
                    "same_weight_text": (
                        a["canonical_weight_text_sha256"] ==
                        b["canonical_weight_text_sha256"]),
                    "same_projection": (
                        a["canonical_projection_sha256"] ==
                        b["canonical_projection_sha256"]),
                    "same_protected_variables": (
                        a["canonical_protected_sha256"] ==
                        b["canonical_protected_sha256"]),
                    "same_full_fingerprint": (
                        a["canonical_combined_sha256"] ==
                        b["canonical_combined_sha256"]),
                }
        report["same_source_option_pairs"][case] = comparisons
    report["status"] = "COMPLETE_RESIDUAL_CONTENT_AUDIT_SCIENCE_PASS"
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--dumps", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    r = study(a.binary, a.cnf_dir, a.science_report, a.dumps, a.out)
    print(json.dumps({
        "status": r["status"],
        "variants": {
            c: {v: entry["canonical"]["canonical_clause_multiset_sha256"]
                for v,entry in row["variants"].items()}
            for c,row in r["cases"].items()
        }
    }))
