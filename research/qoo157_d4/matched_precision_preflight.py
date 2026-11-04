"""QOO-157 GPMC versus d4 *matched decimal targets* correctness preflight.

GPMC uses MPFR ceil(d*log2(10)) actual precision bits; d4 uses GMP mpf
requested the same bits, with real implementation-rounded bits recorded.
Each d4 variant also prints d decimal significant digits. Compare exact
parsed printed rational values; this is a numerical screen, not a solver
arithmetic certificate or quantum equivalence oracle.

Only admitted same-CNF, same-target precision pairs enter CodSpeed.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils.solver_adapter import registered_solver_adapter
from matched_precision_adapter import matched_adapter, read_pinned_manifest

from codspeed_choice_preflight import PAPER_CANDIDATES

DIGITS = (30, 90)
SCREEN = Fraction(1, 10**12)


def sha256(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def run_mode(mode: str, source: Path, *, timeout: int = 25):
    if mode.startswith("gpmc-"):
        return run_wmc(str(source), tool_name="gpmc", timeout=timeout,
                       precision_digits=int(mode.split("-")[1]), preserve_count=True)
    if mode.startswith("d4-"):
        return run_wmc(str(source), tool_name=mode, timeout=timeout,
                       preserve_count=True)
    raise ValueError("unsupported pilot solver")


def decimal_record(count):
    return {
        "real": str(count.real),
        "imag": str(count.imag),
        "print_half_units": [
            str(count.real_print_half_unit),
            str(count.imag_print_half_unit),
        ],
        "format_name": count.format_name,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnf-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--binary-dir", type=Path, required=True)
    parser.add_argument("--provenance-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    if args.timeout < 1 or args.timeout > 60:
        parser.error("solver timeout must be [1,60] seconds")

    reports = {}
    valid_modes = {}
    for digits in DIGITS:
        binary = args.binary_dir / str(digits) / "counter"
        manifest = args.provenance_dir / f"d4-matched-{digits}.json"
        valid_modes[digits] = {
            "binary": binary, "manifest": manifest,
            "details": read_pinned_manifest(binary, manifest, digits)
        }

    with ExitStack() as stack:
        for digits in DIGITS:
            mode = valid_modes[digits]
            adapter = matched_adapter(mode["binary"], mode["manifest"], digits)
            stack.enter_context(registered_solver_adapter(adapter))

        for case, (qasm, pair_dir) in PAPER_CANDIDATES.items():
            source = args.cnf_dir / (case + ".cnf")
            sources = [args.source_dir / qasm, args.source_dir / pair_dir / qasm]
            report = {
                "case": case,
                "source_sha256": [sha256(p) if p.is_file() else None for p in sources],
                "same_cnf_sha256": sha256(source) if source.is_file() else None,
                "source_cnf_bytes": source.stat().st_size if source.is_file() else None,
                "methods": {"gpmc": "complex_weighted_model_count", "d4": "complex_weighted_model_count"},
                "precision_pairs": {},
            }
            reports[case] = report
            for digits in DIGITS:
                key = str(digits)
                pair = {
                    "target_decimal_digits": digits,
                    "source_cnf_sha256": report["same_cnf_sha256"],
                    "requested_mpfr_bits": valid_modes[digits]["details"]["mpfr_reference_bits"],
                    "requested_d4_gmp_bits": valid_modes[digits]["details"]["gmp_requested_bits"],
                    "actual_d4_gmp_bits": valid_modes[digits]["details"]["gmp_actual_bits"],
                    "gpmc_print_decimal_digits": digits,
                    "d4_print_decimal_digits": digits,
                    "observations": {},
                }
                report["precision_pairs"][key] = pair
                if not source.is_file():
                    pair["status"] = "CENSORED_SOURCE_MISSING"
                    continue
                for solver in (f"gpmc-{digits}", f"d4-{digits}"):
                    try:
                        observed = run_mode(solver, source, timeout=args.timeout)
                        pair["observations"][solver] = {"status": "COMPLETED", **decimal_record(observed)}
                    except Exception as exc:
                        pair["observations"][solver] = {
                            "status": "TIMEOUT" if "Timeout" in type(exc).__name__ else "SOLVER_ERROR",
                            "type": type(exc).__name__, "reason": str(exc)[:400],
                        }
                a, b = (pair["observations"].get(f"{solver}-{digits}", {})
                        for solver in ("gpmc", "d4"))
                if a.get("status") != "COMPLETED" or b.get("status") != "COMPLETED":
                    pair["status"] = "CENSORED_SOLVER_FAILURE"
                    continue
                ref = (Fraction(a["real"]), Fraction(a["imag"]))
                other = (Fraction(b["real"]), Fraction(b["imag"]))
                bound = SCREEN * max(Fraction(1), *(abs(x) for x in ref))
                pair["max_component_absolute_delta"] = str(max(abs(a - b) for a, b in zip(ref, other)))
                pair["max_allowed_absolute_delta"] = str(bound)
                pair["status"] = (
                    "COUNT_CONCORDANT_UNCERTIFIED"
                    if all(abs(x-y) <= bound for x,y in zip(ref, other))
                    else "COUNT_DISAGREEMENT"
                )
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps({
                    "complete": False, "cases": reports,
                    "data_not_internal_arithmetic_certificate": True
                }, indent=2) + "\n")

    eligible = [
        [case, d] for case, r in reports.items()
        for d in DIGITS if r["precision_pairs"][str(d)]["status"] == "COUNT_CONCORDANT_UNCERTIFIED"
    ]
    all_pairs = len(PAPER_CANDIDATES) * len(DIGITS)
    data = {
        "complete": True,
        "title": "QOO-157 nominal-precision-match (not exact bit parity)",
        "gpmc_source_revision": "submodule-pinned",
        "same_CNF_source_required": True,
        "working_precision_difference_is_reported_not_hidden": True,
        "printed_decimal_digits_equalized": True,
        "count_concordance_threshold": str(SCREEN),
        "eligible": eligible,
        "expected_pairs": all_pairs,
        "cases": reports,
        "d4_variants": {str(d): valid_modes[d]["details"] for d in DIGITS},
        "internal_solver_error_certified": False,
        "timing_source": "ONLY_official_CodSpeed",
        "recommendation_performance_certified": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({
        "eligible": eligible, "attempted": all_pairs,
        "excluded": [[c, d] for c in PAPER_CANDIDATES for d in DIGITS if [c,d] not in eligible],
    }))
    if not eligible:
        raise SystemExit("No matched-precision solver cases scientifically comparable")


if __name__ == "__main__":
    main()
