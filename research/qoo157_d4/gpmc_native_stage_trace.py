"""QOO-157: verify which *native GPMC* preprocessor stage removes variables.

A source-identical scientific trace, NOT a performance benchmark. GPMC's
already-existing -ppverb=1 prints EquivEl / VE / DefVE / SAT_FLE transition
counts, without patches to upstream GPMC or extra CodSpeed costs.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import subprocess

from gpmc_td_ablation import CASES, COUNT, COMPLEX
from gpmc_vs_td_factorial import close_enough

FLAGS = {
    "ee_on": ("-mode=1", "-prec=38", "-vs=1", "-td", "-pp_ee", "-ppverb=1"),
    "ee_off": ("-mode=1", "-prec=38", "-vs=1", "-td", "-no-pp_ee", "-ppverb=1"),
}
STAGES = re.compile(
    r"(?m)^c o \[\s*([A-Za-z0-9_]+)\s*\]\s+(\d+) vars "
    r"\((\d+) pvars\), (\d+) cls"
)


def run_once(binary: str, cnf: Path, variant: str) -> dict:
    if variant not in FLAGS:
        raise ValueError("unknown GPMC trace setting")
    cp = subprocess.run(
        [binary, *FLAGS[variant], str(cnf)], capture_output=True,
        text=True, check=False, timeout=25
    )
    if cp.returncode:
        raise RuntimeError(f"GPMC {variant} rc={cp.returncode} stderr={cp.stderr[:200]}")
    matches = COUNT.findall(cp.stdout)
    if len(matches) != 1:
        raise ValueError("one complex GPMC WMC count required")
    m = COMPLEX.fullmatch(matches[0].strip())
    if not m:
        raise ValueError("invalid complex result")
    real, imag = (Decimal(t) for t in m.groups())
    phases = [
        {"stage": name, "vars": int(v), "pvars": int(p), "clauses": int(c)}
        for name, v, p, c in STAGES.findall(cp.stdout)
    ]
    if not phases or phases[0]["stage"] != "Init" or phases[-1]["stage"] != "Simp":
        raise ValueError("incomplete native GPMC preprocessing stage trace")
    equiv = [x for x in phases if x["stage"] == "EquivEl"]
    if (variant == "ee_on") != bool(equiv):
        raise ValueError("GPMC EE stage activation inconsistent with flag")
    if not ("FlowCutter is running..." in cp.stdout):
        raise ValueError("TD expected, but no FlowCutter native marker")
    return {
        "real": str(real), "imag": str(imag),
        "stages": phases,
        "equiv_stage_invocations": len(equiv),
        "source_run_output_sha256": sha256(cp.stdout.encode()).hexdigest(),
        "flowcutter_executed": True,
        "equiv_stage_attributable_vars": sum(
            max(0, phases[i-1]["vars"] - item["vars"])
            for i, item in enumerate(phases) if i > 0 and item["stage"] == "EquivEl"
        ),
        "equiv_stage_attributable_clauses": sum(
            phases[i-1]["clauses"] - item["clauses"]
            for i, item in enumerate(phases) if i > 0 and item["stage"] == "EquivEl"
        ),
    }


def audit(binary: Path, cnf_dir: Path, report_path: Path, dest: Path) -> dict:
    archived = json.loads(report_path.read_text())
    if archived.get("complete") is not True:
        raise ValueError("archived original source science report incomplete")
    data = {
        "status": "INCOMPLETE",
        "original_source_artifact": 13317939531,
        "gpmc_gitlink": "a1bda3489e959d3695b6798d327c5a1fc1bed305",
        "gpmc_binary_sha256": sha256(binary.read_bytes()).hexdigest(),
        "effective_decimal_digits": 38,
        "native_trace_only_not_performance": True,
        "internal_arithmetic_certified": False,
        "cases": {},
    }
    for case in CASES:
        path = cnf_dir / (case + ".cnf")
        digest = sha256(path.read_bytes()).hexdigest()
        entry = archived["cases"][case]
        if digest != entry["same_cnf_sha256"]:
            raise ValueError(f"{case}: source CNF SHA mismatch")
        original = entry["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec = 100
            reference = tuple(
                Decimal(Fraction(original[key]).numerator)
                / Decimal(Fraction(original[key]).denominator)
                for key in ("real", "imag")
            )
        observed = {}
        for variant in FLAGS:
            trace = run_once(str(binary), path, variant)
            accepted, delta, threshold = close_enough(
                (Decimal(trace["real"]), Decimal(trace["imag"])), reference)
            if not accepted:
                raise ValueError(f"{case}/{variant}: numeric screen failed {delta}>{threshold}")
            trace.update({
                "count_status": "COUNT_CONCORDANT_UNCERTIFIED",
                "max_printed_count_delta": delta, "count_screen_bound": threshold
            })
            observed[variant] = trace
            data["cases"][case] = {
                "source_cnf_sha256": digest, "variants": observed}
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(data, indent=2) + "\n")
        if (observed["ee_on"]["stages"][-1]["vars"] >=
                observed["ee_off"]["stages"][-1]["vars"]):
            raise ValueError(f"{case}: did not reproduce EE structural reduction")
    data["status"] = "COMPLETE_GPMC_STAGE_TRACE_SCIENCE_PASS"
    dest.write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    x = p.parse_args()
    result = audit(x.binary, x.cnf_dir, x.science_report, x.out)
    print(json.dumps({
        "status": result["status"],
        "cases": {
            k: {
                v: {"equiv_invocations": d["equiv_stage_invocations"],
                    "equiv_attributable_vars": d["equiv_stage_attributable_vars"],
                    "native_post_vars": d["stages"][-1]["vars"]}
                for v, d in row["variants"].items()
            } for k, row in result["cases"].items()
        }
    }))
