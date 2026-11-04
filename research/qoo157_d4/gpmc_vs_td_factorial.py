"""QOO-157 GPMC 2x2 VS x TD science-gated factorial, source-CNF only.

This experiment does not time anything without official CodSpeed. -vs=0
can still consume TD exscore: the design measures their interaction, not
independent TD usage or phase-level causal fractions.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess

from gpmc_td_ablation import CASES, COUNT, COMPLEX

DIGITS = 38
GPMC_GITLINK = "a1bda3489e959d3695b6798d327c5a1fc1bed305"
ORIGINAL_ARTIFACT = 13317939531
VARIANTS = {
    "vs0_td": ("-mode=1", "-prec=38", "-vs=0", "-td"),
    "vs0_no_td": ("-mode=1", "-prec=38", "-vs=0", "-no-td"),
    "vs1_td": ("-mode=1", "-prec=38", "-vs=1", "-td"),
    "vs1_no_td": ("-mode=1", "-prec=38", "-vs=1", "-no-td"),
}
STATUS = "COMPLETED_COUNT_CONCORDANCE_UNCERTIFIED"


def run_one(binary: str, cnf: Path, variant: str, *, timeout: float = 25) -> dict:
    if variant not in VARIANTS:
        raise ValueError("unsupported GPMC 2x2 variant")
    cp = subprocess.run(
        [binary, *VARIANTS[variant], str(cnf)], check=False,
        capture_output=True, text=True, timeout=timeout,
    )
    if cp.returncode:
        raise RuntimeError(f"GPMC {variant} rc={cp.returncode}: {cp.stderr[:300]}")
    matches = COUNT.findall(cp.stdout)
    if len(matches) != 1:
        raise ValueError(f"Expected one complex GPMC count; found {len(matches)}")
    found = COMPLEX.fullmatch(matches[0].strip())
    if not found:
        raise ValueError("GPMC complex count output malformed")
    real, imag = map(Decimal, found.groups())
    if not (real.is_finite() and imag.is_finite()):
        raise ValueError("non-finite WMC result")
    log = cp.stdout
    td_running = "FlowCutter is running..." in log
    td_skipped = "skip td" in log
    td_ignored = "ignore td" in log
    if variant.endswith("no_td") and td_running:
        raise ValueError("TD disabled but FlowCutter unexpectedly executed")
    if variant.endswith("_td") and (not td_running or td_skipped or td_ignored):
        raise ValueError(f"TD enabled but no accepted decomposition: {variant}")
    metrics = {}
    for metric in ("conflicts", "decisions", "propagations", "SAT calls", "backjumps"):
        match = re.search(r"(?m)^c o " + re.escape(metric) + r"\s+=\s+(\d+)", log)
        if match:
            metrics[metric.replace(" ", "_")] = int(match.group(1))
    graph = re.search(r"Primal graph: nodes\s+(\d+), edges\s+(\d+)", log)
    return {
        "real": str(real), "imag": str(imag),
        "printed": matches[0].strip(),
        "stdout_sha256": sha256(cp.stdout.encode()).hexdigest(),
        "flowcutter_executed": td_running,
        "td_skipped": td_skipped, "td_ignored": td_ignored,
        "post_preprocessing_primal": (
            {"nodes": int(graph.group(1)), "edges": int(graph.group(2))}
            if graph else None
        ),
        "native_search_counters": metrics,
    }


def close_enough(a: tuple[Decimal, Decimal], b: tuple[Decimal, Decimal]) -> tuple[bool, str, str]:
    threshold = Decimal("1e-12") * max(Decimal(1), abs(b[0]), abs(b[1]))
    deviation = max(abs(x-y) for x, y in zip(a, b))
    return deviation <= threshold, str(deviation), str(threshold)


def preflight(binary: str, cnf_dir: Path, source_report: Path, output: Path) -> dict:
    original = json.loads(source_report.read_text())
    if original.get("complete") is not True:
        raise ValueError("source science admission report incomplete")
    summary = {
        "status": "INCOMPLETE", "original_artifact_id": ORIGINAL_ARTIFACT,
        "gpmc_gitlink": GPMC_GITLINK, "precision_digits": DIGITS,
        "source_sha": "efab7ccd132214758d4209d0b5c4f6488f30695e",
        "binary_sha256": sha256(Path(binary).read_bytes()).hexdigest(),
        "variants": {k:list(v) for k,v in VARIANTS.items()},
        "cases": {},
        "internal_arithmetic_certified": False,
        "timing_source": "official_CodSpeed_only",
        "scope": "original weighted CNF native external solver inclusive; no QASM/RR",
    }
    for case in CASES:
        source = cnf_dir / (case + ".cnf")
        digest = sha256(source.read_bytes()).hexdigest()
        expected = original["cases"][case]
        if digest != expected["same_cnf_sha256"]:
            raise ValueError("source CNF SHA mismatch for " + case)
        record = {"cnf_sha256": digest, "variants": {}}
        summary["cases"][case] = record
        anchor = expected["precision_pairs"]["38"]["observations"]["gpmc-38"]
        if anchor["status"] != "COMPLETED":
            raise ValueError("original GPMC38 count not admissible")
        # Original QuPRS SolverAdapter records exact printed-value rationals.
        # Never pass a "numerator/denominator" string directly to Decimal.
        with localcontext() as ctx:
            ctx.prec = 100
            reference = tuple(
                Decimal(Fraction(anchor[component]).numerator)
                / Decimal(Fraction(anchor[component]).denominator)
                for component in ("real", "imag")
            )
        for variant in VARIANTS:
            obs = run_one(binary, source, variant)
            reference_check = close_enough(
                (Decimal(obs["real"]), Decimal(obs["imag"])), reference
            )
            obs["archived_gpmc38_concordance"] = {
                "pass": reference_check[0],
                "max_delta": reference_check[1],
                "bound": reference_check[2],
            }
            record["variants"][variant] = obs
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, indent=2) + "\n")
            if not reference_check[0]:
                raise ValueError("CENSORED_COUNT_DISAGREEMENT_ARCHIVED: " + case + "/" + variant)
        baseline = record["variants"]["vs1_td"]
        target = (Decimal(baseline["real"]), Decimal(baseline["imag"]))
        for variant, obs in record["variants"].items():
            accepted, delta, bound = close_enough(
                (Decimal(obs["real"]), Decimal(obs["imag"])), target
            )
            obs["baseline_vs1_td_concordance"] = {
                "pass": accepted, "max_delta": delta, "bound": bound
            }
            if not accepted:
                raise ValueError("CENSORED_COUNT_DISAGREEMENT_BASELINE: " + case + "/" + variant)
        record["status"] = "COUNT_CONCORDANT_UNCERTIFIED"
    summary["status"] = STATUS
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps({"status": preflight(
        args.binary, args.cnf_dir, args.science_report, args.out
    )["status"]}))
