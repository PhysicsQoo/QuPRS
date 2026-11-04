"""QOO-157 pinned GPMC TD on/off, fixed-CNF numeric admission and trace.

Only official CodSpeed may rank speed. Untimed preflight is a science gate.
No solver source, QuPRS default, or original CNF is modified.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

CASES = ("qaoa7_neq", "qft16_eq")
SCALAR = r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
COMPLEX = re.compile(rf"^([+-]?{SCALAR})([+-]{SCALAR})i$")
COUNT = re.compile(r"^c s exact double prec-sci (.+)$", re.MULTILINE)
FLAGS = {
    "td_default": ("-mode=1", "-prec=38", "-vs=1", "-td"),
    "td_disabled": ("-mode=1", "-prec=38", "-vs=1", "-no-td"),
}


def run_one(binary: str, cnf: Path, variant: str, *, timeout: float = 20) -> dict:
    if variant not in FLAGS:
        raise ValueError("unsupported variant")
    cp = subprocess.run(
        [binary, *FLAGS[variant], str(cnf)], check=False,
        capture_output=True, text=True, timeout=timeout,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"GPMC {variant}: rc={cp.returncode}, stderr={cp.stderr[:350]}"
        )
    results = COUNT.findall(cp.stdout)
    if len(results) != 1:
        raise ValueError(f"Expected one complex WMC result, got {results}")
    match = COMPLEX.fullmatch(results[0].strip())
    if not match:
        raise ValueError(f"Malformed complex GPMC result: {results[0]}")
    real, imag = (Decimal(s) for s in match.groups())
    if not (real.is_finite() and imag.is_finite()):
        raise ValueError("Nonfinite GPMC count")
    return {
        "real": str(real), "imag": str(imag),
        "printed": results[0].strip(),
        "raw_sha256": sha256(cp.stdout.encode()).hexdigest(),
        "flowcutter_executed": "FlowCutter is running" in cp.stdout,
        "td_skip_recorded": "skip td" in cp.stdout,
        "td_ignored_recorded": "ignore td" in cp.stdout,
        "gpmc_log_markers": [
            line.strip() for line in cp.stdout.splitlines()
            if ("FlowCutter" in line or "skip td" in line
                or "ignore td" in line or "Primal graph" in line)
        ],
    }


def preflight(binary: str, input_dir: Path, science_report: Path, output: Path) -> dict:
    original = json.loads(science_report.read_text())
    if original.get("complete") is not True:
        raise ValueError("Original QOO-157 science report is incomplete")
    report = {
        "status": "SCIENTIFIC_PREFLIGHT_ONLY",
        "old_source_sha": "efab7ccd132214758d4209d0b5c4f6488f30695e",
        "original_artifact_id": 13317939531,
        "gpmc_gitlink": "a1bda3489e959d3695b6798d327c5a1fc1bed305",
        "binary_sha256": sha256(Path(binary).read_bytes()).hexdigest(),
        "cases": {},
        "codspeed_only_for_timing": True,
        "uncertified_internal_arithmetic": True,
    }
    for case in CASES:
        source = input_dir / f"{case}.cnf"
        input_sha = sha256(source.read_bytes()).hexdigest()
        if original["cases"][case]["same_cnf_sha256"] != input_sha:
            raise ValueError(f"Original source CNF SHA mismatch: {case}")
        entry = {"input_sha256": input_sha, "variants": {}}
        report["cases"][case] = entry
        for variant in FLAGS:
            entry["variants"][variant] = run_one(binary, source, variant)
        base, other = (entry["variants"][v] for v in FLAGS)
        a = Decimal(base["real"]), Decimal(base["imag"])
        b = Decimal(other["real"]), Decimal(other["imag"])
        bound = Decimal("1e-12") * max(Decimal(1), abs(a[0]), abs(a[1]))
        entry["max_component_delta"] = str(max(abs(x-y) for x, y in zip(a, b)))
        entry["max_allowed_delta"] = str(bound)
        entry["status"] = (
            "COUNT_CONCORDANT_UNCERTIFIED"
            if all(abs(x-y) <= bound for x, y in zip(a, b))
            else "COUNT_DISAGREEMENT"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        if entry["status"] != "COUNT_CONCORDANT_UNCERTIFIED":
            raise ValueError(f"FAIL_CLOSED_CNF_COUNT_DISAGREEMENT: {case}")
    report["status"] = "COMPLETED_COUNT_CONCORDANCE_UNCERTIFIED"
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--science-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps({
        "status": preflight(
            args.binary, args.cnf_dir, args.science_report, args.out
        )["status"]
    }))
