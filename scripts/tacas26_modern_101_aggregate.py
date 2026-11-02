#!/usr/bin/env python3
"""Fail-closed aggregation of two *completed* TACAS modern GPMC runs.

Research branch only. Matching 101 cases and MPFR convergence do not certify
the GPMC arithmetic error; this reporter NEVER claims such a certificate.
"""
from __future__ import annotations
import argparse
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from scripts.tacas26_modern_full_101 import comparable_source_records, ROOT

EXPECTED_SOURCE = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
EXPECTED_DISTANCE = "2e-5"
SCHEMA = "tacas26-modern-complete-101-science-audit-v1"


def collect(path, expected_sha, expected_digits, expected_backends, reference):
    rows = {}
    files = sorted(Path(path).rglob("*.jsonl"))
    if len(files) != 24 * len(expected_backends):
        raise ValueError(f"Expected {24 * len(expected_backends)} artifacts, got {len(files)}")
    for path in files:
        lines = path.read_text(encoding="utf8").splitlines()
        if not lines:
            raise ValueError("Empty science observations: " + str(path))
        for line in lines:
            rec = json.loads(line)
            key = (rec["id"], rec["backend"])
            if key in rows:
                raise ValueError(f"Duplicate modern science case/backend: {key}")
            if rec["id"] not in reference or rec["backend"] not in expected_backends:
                raise ValueError(f"Unexpected modern science case/backend: {key}")
            case, source, counterpart, historical = reference[rec["id"]]
            if (rec.get("schema") != "tacas26-modern-101-source-pinned-v1"
                or rec.get("head_sha") != expected_sha
                or rec.get("historical_sha") != EXPECTED_SOURCE
                or rec.get("source_historical_verdict") != historical["verdict"]
                or rec.get("historical_output_sha256") != historical["source_result_sha256"]
                or rec.get("method") != case["method"]
                or rec.get("gpmc_precision_digits") != expected_digits
                or rec.get("distance_tolerance") != EXPECTED_DISTANCE
                or rec.get("rr_tolerance") != "1e-10"
                or rec.get("phase_tolerance") != "1e-8"
                or rec.get("source_original") != source
                or rec.get("source_counterpart") != counterpart):
                raise ValueError("Source/strategy/parameter provenance mismatch: " + str(key))
            # Independently rederive binary verdict from original and modern
            # outputs. A producer-written BINARY_MATCH string cannot serve as
            # its own proof, especially after a Timeout/parse failure.
            from scripts.tacas26_modern_calibration import binary
            if rec["observation"].get("run_status") != "COMPLETED":
                recalculated = "NOT_MEASURED_OR_CENSORED"
            else:
                new_binary = binary(rec["observation"].get("verdict"))
                old_binary = binary(historical["verdict"])
                recalculated = ("NOT_MEASURED_OR_CENSORED" if new_binary is None
                                else ("BINARY_MATCH" if new_binary == old_binary
                                      else "BINARY_MISMATCH"))
            if rec["binary_comparison"] != recalculated:
                raise ValueError("Untrusted producer-scored binary classification: " + str(key))
            rows[key] = rec
    expected = {(case_id, backend) for case_id in reference for backend in expected_backends}
    if rows.keys() != expected:
        missing = sorted(expected - rows.keys())
        extra = sorted(rows.keys() - expected)
        raise ValueError(f"Incomplete modern 101-case dataset: missing={missing}, extra={extra}")
    return rows


def _decimal_fraction(text):
    q = Fraction(text)
    with localcontext() as ctx:
        ctx.prec = 130
        return Decimal(q.numerator) / Decimal(q.denominator)


def normalized_complex_gap(row30, row90):
    """Empirical 30/90 difference; no solver error bound may be inferred."""
    a, b = row30["observation"], row90["observation"]
    if (a.get("run_status") != "COMPLETED" or b.get("run_status") != "COMPLETED"):
        return {"status": "UNCLASSIFIABLE_NONCOMPLETED"}
    if not a.get("solver_invoked") and not b.get("solver_invoked"):
        return {"status": "NO_WMC_SOLVER_IN_EITHER"}
    ac, bc = a.get("observed_solver_calls", []), b.get("observed_solver_calls", [])
    if len(ac) != 1 or len(bc) != 1:
        return {"status": "MISSING_OR_DUPLICATE_RAW_SOLVER_WITNESS",
                "count30": len(ac), "count90": len(bc)}
    if ac[0].get("cnf_sha256") != bc[0].get("cnf_sha256"):
        return {"status": "CNF_MISMATCH",
                "cnf30": ac[0].get("cnf_sha256"),
                "cnf90": bc[0].get("cnf_sha256")}
    x = ac[0]["printed_count"]; y = bc[0]["printed_count"]
    if "solver_printed_complex_re" not in x or "solver_printed_complex_re" not in y:
        return {"status": "PRINTED_COMPLEX_UNAVAILABLE"}
    with localcontext() as ctx:
        ctx.prec = 110
        xr = _decimal_fraction(x["solver_printed_complex_re"])
        xi = _decimal_fraction(x["solver_printed_complex_im"])
        yr = _decimal_fraction(y["solver_printed_complex_re"])
        yi = _decimal_fraction(y["solver_printed_complex_im"])
        mag = (yr*yr+yi*yi).sqrt()
        rel = ((xr-yr)**2+(xi-yi)**2).sqrt() / mag if mag else None
    return {"status": "SAME_CNF_PRECISION_COMPARABLE",
            "cnf_sha256": ac[0]["cnf_sha256"],
            "gpmc_output_relative_difference": str(rel) if rel is not None else None,
            "printed_decision_30": x.get("printed_status"),
            "printed_decision_90": y.get("printed_status"),
            "conditional_normalized_error_allowance_30": x.get("conditional_allowable_normalized_error"),
            "conditional_normalized_error_allowance_90": y.get("conditional_allowable_normalized_error"),
            "certified_gpmc_arithmetic": False,
            "arithmetic_bound": None,
            "certification_status": "NOT_CERTIFIED_NO_VALIDATED_SOLVER_ERROR_BUDGET"}


def assemble(root, path30, path90, sha30, sha90):
    from scripts.tacas26_modern_calibration import binary
    reference = {row["id"]: (row, original, counterpart, saved)
                 for row, saved, original, counterpart in comparable_source_records(root)}
    rows30 = collect(path30, sha30, 30, {"python", "rust"}, reference)
    rows90 = collect(path90, sha90, 90, {"python"}, reference)
    cases = []
    stats = {"python_30": 0, "rust_30": 0, "python_90": 0,
             "python_rust_disagreement": [], "precision_30_90_disagreement": [],
             "binary_mismatch": [], "censored_or_invalid": [],
             "same_cnf_count": 0, "numeric_probe_without_raw_wmc": [],
             "solver_arithmetic_certified": 0,
             "observed_gpmc_invocations": {"python_30": 0, "rust_30": 0, "python_90": 0},
             "no_solver_stage_cases": []}
    for case_id in sorted(reference):
        p30 = rows30[(case_id,"python")]
        r30 = rows30[(case_id,"rust")]
        p90 = rows90[(case_id,"python")]
        statuses = {name: q["binary_comparison"] for name,q in [
            ("python_30",p30), ("rust_30",r30), ("python_90",p90)]}
        actual = {name: q["observation"].get("verdict") for name,q in [
            ("python_30",p30), ("rust_30",r30), ("python_90",p90)]}
        for label, row in [("python_30",p30),("rust_30",r30),("python_90",p90)]:
            if statuses[label] == "BINARY_MATCH":
                stats[label] += 1
            elif statuses[label] == "BINARY_MISMATCH":
                stats["binary_mismatch"].append({"id":case_id,"backend_digit":label,"verdict":actual[label]})
            else:
                stats["censored_or_invalid"].append({"id":case_id,"backend_digit":label,
                     "status":row["observation"].get("run_status"),"verdict":actual[label]})
        for label, r in [("python_30",p30),("rust_30",r30),("python_90",p90)]:
            invoked = r["observation"].get("solver_invoked")
            if invoked is True:
                stats["observed_gpmc_invocations"][label] += 1
            else:
                stats["no_solver_stage_cases"].append({
                    "id":case_id, "backend_digits":label, "solver_invoked":invoked})
        if (binary(actual["python_30"]) is not None and
            binary(actual["rust_30"]) is not None and
            binary(actual["python_30"]) != binary(actual["rust_30"])):
            stats["python_rust_disagreement"].append(case_id)
        if (binary(actual["python_30"]) is not None and
            binary(actual["python_90"]) is not None and
            binary(actual["python_30"]) != binary(actual["python_90"])):
            stats["precision_30_90_disagreement"].append(case_id)
        g=normalized_complex_gap(p30,p90)
        if g["status"] == "SAME_CNF_PRECISION_COMPARABLE":
            stats["same_cnf_count"] += 1
        else:
            stats["numeric_probe_without_raw_wmc"].append({"id":case_id,"reason":g["status"]})
        cases.append({
            "id": case_id, "historical_verdict": reference[case_id][3]["verdict"],
            "historical_binary": binary(reference[case_id][3]["verdict"]),
            "new_verdicts": actual, "new_binary_comparisons": statuses,
            "modern_solver_invoked_by_backend": {
                "python_30":p30["observation"].get("solver_invoked"),
                "rust_30":r30["observation"].get("solver_invoked"),
                "python_90":p90["observation"].get("solver_invoked")},
            "modern_wmc_precision_reasons": {
                "python_30":p30["observation"].get("wmc_precision_reason"),
                "rust_30":r30["observation"].get("wmc_precision_reason"),
                "python_90":p90["observation"].get("wmc_precision_reason")},
            "empirical_30_vs_90": g,
            "modern_gpmc_sha256": p30["observation"].get("solver_binary_sha256"),
            "source_original_qasm_sha256": p30["source_original"]["sha256"],
            "source_counterpart_qasm_sha256": p30["source_counterpart"]["sha256"],
            "method": reference[case_id][0]["method"],
            "solver_arithmetic_certificate": "ABSENT",
        })
    complete_binary = all(stats[n]==101 for n in ("python_30","rust_30","python_90"))
    report = {
        "schema":SCHEMA, "historical_sha":EXPECTED_SOURCE,
        "source_sha_30":sha30,"source_sha_90":sha90,
        "source_same_source_files_required":True,
        "counts":{"historical_wmc_count_records":101,"historical_eq":45,
                  "historical_neq":56,"modern_backend_case_probes":303},
        "statistics":stats,
        "gates":{
            "full_101_python_rust_binary_reproduction":complete_binary,
            "full_101_precision90_binary_reproduction":stats["python_90"]==101,
            "all_cnf_printed_30_90_comparable":stats["same_cnf_count"]==101,
            "solver_arithmetic_precision_certified":False,
        },
        "certification_blockers":[
          "GPMC solver arithmetic truncation/roundoff not bounded",
          "Source trig phase/weight numerical error not bounded",
          "Full PathSum->CNF->trace normalization not independently proven for every instance",
          "30-versus-90 equality is an empirical observation, not an a priori error bound",
        ],
        "cases":cases,
    }
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--dir30",type=Path,required=True)
    p.add_argument("--dir90",type=Path,required=True)
    p.add_argument("--sha30",required=True)
    p.add_argument("--sha90",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=assemble(args.root,args.dir30,args.dir90,args.sha30,args.sha90)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("TACAS26_FINAL_NUMERIC_AUDIT "+json.dumps({
        "gates":report["gates"],"statistics":report["statistics"],
        "head_sha_30":report["source_sha_30"],
        "head_sha_90":report["source_sha_90"]},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
