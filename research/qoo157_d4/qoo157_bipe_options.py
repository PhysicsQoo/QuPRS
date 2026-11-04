"""QOO-157: d4 pinned BiPe configuration ablation, science gate first.

Only 38-effective-decimal-digit scratch native d4; the original four source
CNFs are SHA-checked. Official CodSpeed alone supplies performance metrics.
Each diagnostic variant uses the SAME binary and source, and a change in
printed complex count fails science admission, not reported as speed.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from gpmc_vs_td_factorial import CASES, close_enough
from qoo157_preprocess_compare import D4_COUNTS, D4_RESULT
from gpmc_td_ablation import COMPLEX

# Every non-baseline variant is either a single switch or an explicitly
# labeled auto-config bundle change. Do not equate manual_sharp to a single
# isolated individual BiPe transformation.
OPTIONS = {
    "auto_default": (),
    "none": ("--preproc.auto-config=false", "--preproc.preproc-method=none"),
    "manual_sharp": (
        "--preproc.auto-config=false", "--preproc.preproc-method=sharp-equiv"),
    "auto_no_equiv_subst": ("--preproc.equiv-subst=false",),
    "auto_no_vivif": ("--preproc.eliminator.oracle-vivif=false",),
    "auto_no_probing": ("--preproc.eliminator.probing=false",),
}
STATUS = "COMPLETE_SCIENCE_ADMITTED_WITH_CENSORING_TRACKED"
TIMEOUT_SECONDS = 28


def run_one(binary: str, cnf: Path, variant: str, *, timeout: int = TIMEOUT_SECONDS) -> dict:
    if variant not in OPTIONS:
        raise ValueError("unknown d4 preproc option")
    cp = subprocess.run(
        [binary, "-i", str(cnf), *OPTIONS[variant]],
        check=False, capture_output=True, text=True, timeout=timeout,
    )
    if cp.returncode:
        raise RuntimeError(
            f"d4 {variant} rc={cp.returncode}; stderr={cp.stderr[:360]}")
    counts = D4_RESULT.findall(cp.stdout)
    if len(counts) != 1:
        raise ValueError(f"{variant}: expected exactly one complex WMC count")
    match = COMPLEX.fullmatch(counts[0].strip())
    if not match:
        raise ValueError(f"{variant}: malformed complex result {counts[0][:95]}")
    real, imag = map(Decimal, match.groups())
    if not all(q.is_finite() for q in (real, imag)):
        raise ValueError("nonfinite printed WMC")
    markers = D4_COUNTS.findall(cp.stdout)
    stages = {
        m[0]: {
            "vars": int(m[1]), "clauses": int(m[2]),
            "active_vars": int(m[3]), "protected_vars": int(m[4]),
            "weight_entries": int(m[5]), "projected": int(m[6]),
        } for m in markers
    }
    if len(markers) != 2 or set(stages) != {"before", "after"}:
        raise ValueError(f"missing or duplicate native BiPe markers for {variant}")
    if stages["before"]["protected_vars"] not in (319, 400):
        raise ValueError("source-weight-protection runtime count mismatch")
    if variant == "none" and any(
        stages["before"][k] != stages["after"][k]
        for k in ("vars", "clauses", "active_vars")
    ):
        raise ValueError("preproc.none mutated Boolean dimensions")
    return {
        "real": str(real), "imag": str(imag),
        "stdout_sha256": sha256(cp.stdout.encode()).hexdigest(),
        "native_preprocessor": stages,
        "flags": list(OPTIONS[variant]),
    }


def preflight(binary: Path, cnfdir: Path, original_file: Path, output: Path) -> dict:
    source = json.loads(original_file.read_text())
    if source.get("complete") is not True:
        raise ValueError("original source science evidence incomplete")
    info = {
        "status": "INCOMPLETE",
        "research_id": "QOO-157",
        "source_artifact_id": 13317939531,
        "d4_source_commit": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
        "d4_binary_sha256": sha256(binary.read_bytes()).hexdigest(),
        "gmp_requested_bits": 127, "gmp_actual_bits": 128,
        "effective_decimal_digits": 38,
        "source_cnf_sha_enforced": True,
        "science_screen_is_not_precision_certificate": True,
        "performance_instrument": "official_codspeed_only",
        "configurations": {k: list(v) for k, v in OPTIONS.items()},
        "cases": {},
    }
    for case in CASES:
        cnf = cnfdir / (case + ".cnf")
        original_case = source["cases"][case]
        digest = sha256(cnf.read_bytes()).hexdigest()
        if digest != original_case["same_cnf_sha256"]:
            raise ValueError("archived original CNF SHA differs: " + case)
        original_observation = original_case["precision_pairs"]["38"]["observations"]["d4-38"]
        if original_observation["status"] != "COMPLETED":
            raise ValueError("archived original d4-38 did not complete: " + case)
        with localcontext() as ctx:
            ctx.prec = 100
            expected_count = tuple(
                Decimal(Fraction(original_observation[k]).numerator)
                / Decimal(Fraction(original_observation[k]).denominator)
                for k in ("real", "imag")
            )
        row = {"source_cnf_sha256": digest, "results": {},
               "admitted": [], "censored": []}
        info["cases"][case] = row
        for variant in OPTIONS:
            try:
                record = run_one(str(binary), cnf, variant)
                count = (Decimal(record["real"]), Decimal(record["imag"]))
                ok, difference, tolerance = close_enough(count, expected_count)
                record.update({
                    "status": "COUNT_CONCORDANT_UNCERTIFIED" if ok
                    else "CENSORED_NUMERICAL_DISAGREEMENT",
                    "max_component_delta": difference,
                    "count_screen_bound": tolerance,
                })
            except subprocess.TimeoutExpired as ex:
                record = {"status": "CENSORED_TIMEOUT", "reason": str(ex)[:300]}
            except Exception as ex:
                record = {"status": "CENSORED_NATIVE_OR_OPTION_ERROR",
                          "kind": type(ex).__name__, "reason": str(ex)[:400]}
            row["results"][variant] = record
            if record["status"] == "COUNT_CONCORDANT_UNCERTIFIED":
                row["admitted"].append(variant)
            else:
                row["censored"].append(variant)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(info, indent=2) + "\n")
        # Original baseline and disabled BiPe are mandatory. A majority of
        # other variants must produce valid counts to justify this costly CI.
        for mandatory in ("auto_default", "none"):
            if mandatory not in row["admitted"]:
                raise ValueError(f"required science control censored: {case}/{mandatory}")
        if len(row["admitted"]) < 4:
            raise ValueError(f"insufficient science-admitted variants: {case}")
    info["status"] = STATUS
    output.write_text(json.dumps(info, indent=2) + "\n")
    return info


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = preflight(a.binary, a.cnf_dir, a.science_report, a.out)
    print(json.dumps({
        "status": result["status"],
        "admitted": {k: v["admitted"] for k, v in result["cases"].items()},
        "censored": {k: v["censored"] for k, v in result["cases"].items()},
    }))
