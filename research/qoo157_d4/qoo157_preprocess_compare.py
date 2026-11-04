"""Native GPMC vs d4 preprocessing: structural and count-preservation audit.

Four config families per original weighted CNF:
GPMC -pp_ee/-no-pp_ee (all other defaults fixed);
d4-38 default BiPe / preproc.none, with early instrumentation in scratch source.
Only official CodSpeed may compare measured WallTime. Non-fatal censored
variants are excluded, never treated as speed wins.
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

from gpmc_td_ablation import COMPLEX, COUNT
from gpmc_vs_td_factorial import CASES, close_enough

FLAGS = {
    "gpmc_ee_on": ("-mode=1", "-prec=38", "-vs=1", "-td", "-pp_ee"),
    "gpmc_ee_off": ("-mode=1", "-prec=38", "-vs=1", "-td", "-no-pp_ee"),
    "d4_bipe_default": ("-i",),
    "d4_bipe_none": (
        "-i", "--preproc.auto-config=false", "--preproc.preproc-method=none"
    ),
}
GPMC_COUNTS = re.compile(r"(?m)^c o \[(Init|Simp)\s*\]\s+(\d+) vars \((\d+) pvars\), (\d+) cls")
D4_COUNTS = re.compile(
    r"(?m)^c QOO157_BIPE (before|after) vars=(\d+) clauses=(\d+) "
    r"active=(\d+) protected=(\d+) weight_entries=(\d+) projected=(\d+)"
)
D4_RESULT = re.compile(r"(?m)^c s exact arb float (.+)$")
TARGET_STATUS = "SCIENTIFIC_PREFLIGHT_COMPLETED_WITH_CENSORING_POSSIBLE"


def run_one(gpmc_binary: str, d4_binary: str, source: Path, variant: str,
            *, timeout: float = 25) -> dict:
    if variant not in FLAGS:
        raise ValueError("unknown preprocessing variant")
    is_gpmc = variant.startswith("gpmc_")
    if is_gpmc:
        cmd = [gpmc_binary, *FLAGS[variant], str(source)]
    else:
        cmd = [d4_binary, "-i", str(source), *FLAGS[variant][1:]]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if cp.returncode:
        raise RuntimeError(f"{variant}: rc={cp.returncode}, stderr={cp.stderr[:500]}")
    stdout = cp.stdout
    lines = COUNT.findall(stdout) if is_gpmc else D4_RESULT.findall(stdout)
    if len(lines) != 1:
        raise ValueError(f"{variant}: one complex count required, found {len(lines)}")
    m = COMPLEX.fullmatch(lines[0].strip())
    if not m:
        raise ValueError(f"{variant}: malformed complex count {lines[0][:100]}")
    real, imag = [Decimal(z) for z in m.groups()]
    if not (real.is_finite() and imag.is_finite()):
        raise ValueError("nonfinite WMC")
    if is_gpmc:
        stats = GPMC_COUNTS.findall(stdout)
        names = {z[0]: {"vars": int(z[1]), "pvars": int(z[2]),
                        "clauses": int(z[3])} for z in stats}
        if "Init" not in names or "Simp" not in names:
            raise ValueError(f"missing GPMC native preprocessor dimensions: {stats}")
        native = {"native_preprocess": names,
                  "flowcutter_executed": "FlowCutter is running..." in stdout}
    else:
        stages = D4_COUNTS.findall(stdout)
        names = {z[0]: {"vars": int(z[1]), "clauses": int(z[2]),
                        "active": int(z[3]), "protected": int(z[4]),
                        "weight_entries": int(z[5]), "projected": int(z[6])}
                 for z in stages}
        if "before" not in names or "after" not in names:
            raise ValueError(f"missing d4 BiPe runtime markers: {stages}")
        if names["before"]["protected"] not in (319, 400):
            raise ValueError("d4 actual protected-variable count mismatch")
        if variant == "d4_bipe_none":
            for key in ("vars", "clauses", "active"):
                if names["before"][key] != names["after"][key]:
                    raise ValueError("d4 disabled BiPe still changed " + key)
        native = {"native_preprocess": names, "instrumentation": "scratch_only"}
    return {
        "real": str(real), "imag": str(imag),
        "count_stdout_sha256": sha256(stdout.encode()).hexdigest(),
        "count_format": "gpmc_mpfr" if is_gpmc else "d4_gmp",
        **native,
    }


def preflight(gpmc_binary: str, d4_binary: str, cnf_dir: Path,
              science_report: Path, out: Path) -> dict:
    original = json.loads(science_report.read_text())
    if original.get("complete") is not True:
        raise ValueError("Missing archived scientific report")
    report = {
        "status": "INCOMPLETE",
        "gpmc_sha256": sha256(Path(gpmc_binary).read_bytes()).hexdigest(),
        "d4_scratch_binary_sha256": sha256(Path(d4_binary).read_bytes()).hexdigest(),
        "gpmc_source_gitlink": "a1bda3489e959d3695b6798d327c5a1fc1bed305",
        "d4_upstream_commit": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
        "effective_decimal_digits": 38,
        "gpmc_mpfr_bits": 127,
        "d4_gmp_bits": 128,
        "same_decimal_digits_not_same_exact_bits": True,
        "d4_instrumented_binary_not_for_cross_solver_speed_rank": True,
        "original_science_artifact": 13317939531,
        "scientific_count_screen": "1e-12 * max(1,|reference real|,|reference imag|)",
        "arithmetic_certified": False,
        "cases": {},
    }
    for case in CASES:
        file = cnf_dir / (case + ".cnf")
        expected = original["cases"][case]
        digest = sha256(file.read_bytes()).hexdigest()
        if digest != expected["same_cnf_sha256"]:
            raise ValueError("source CNF SHA mismatch " + case)
        e = expected["precision_pairs"]["38"]["observations"]["gpmc-38"]
        if e["status"] != "COMPLETED":
            raise ValueError("Reference count not admitted")
        with localcontext() as ctx:
            ctx.prec = 100
            ref = tuple(
                Decimal(Fraction(e[k]).numerator) / Decimal(Fraction(e[k]).denominator)
                for k in ("real", "imag")
            )
        row = {"cnf_sha256": digest, "variants": {}, "admitted_solvers": []}
        report["cases"][case] = row
        for variant in FLAGS:
            try:
                value = run_one(gpmc_binary, d4_binary, file, variant)
                okay, delta, allowed = close_enough(
                    (Decimal(value["real"]), Decimal(value["imag"])), ref
                )
                value["delta_from_archived_gpmc38"] = delta
                value["max_allowed_delta"] = allowed
                value["status"] = ("COUNT_CONCORDANT_UNCERTIFIED" if okay
                                   else "CENSORED_NUMERICAL_DISAGREEMENT")
            except subprocess.TimeoutExpired as exc:
                value = {"status": "CENSORED_TIMEOUT", "error": str(exc)[:220]}
            except Exception as exc:
                value = {"status": "CENSORED_SOLVER_OR_INSTRUMENTATION_ERROR",
                         "error_type": type(exc).__name__, "error": str(exc)[:400]}
            row["variants"][variant] = value
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2) + "\n")
        for solver, pair in (
            ("gpmc", ("gpmc_ee_on", "gpmc_ee_off")),
            ("d4", ("d4_bipe_default", "d4_bipe_none")),
        ):
            if all(row["variants"][v]["status"] == "COUNT_CONCORDANT_UNCERTIFIED"
                   for v in pair):
                row["admitted_solvers"].append(solver)
        if "gpmc" not in row["admitted_solvers"]:
            raise ValueError("GPMC preprocessing science pair not admitted: " + case)
    report["status"] = TARGET_STATUS
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--gpmc", required=True)
    a.add_argument("--d4", required=True)
    a.add_argument("--cnf-dir", type=Path, required=True)
    a.add_argument("--science-report", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    o = a.parse_args()
    print(json.dumps({"status": preflight(
        o.gpmc, o.d4, o.cnf_dir, o.science_report, o.out
    )["status"]}))
