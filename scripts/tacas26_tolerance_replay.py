#!/usr/bin/env python3
"""Exact-rational offline v0.14 tolerance replay of historical v0.9.1 counts.

Science-only, no Solver and no CodSpeed. The input counts stay pinned to
v0.9.1; this cannot predict the outcome of a modern solver rerun.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal
from fractions import Fraction
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/development/tacas26-results/wmc-evidence.json"
OUT=ROOT/"docs/development/tacas26-results/tolerance-offline-v0140"
DISTANCES=("1e-8","1e-7","1e-6","1e-5","1.4e-5","2e-5","1e-4","1e-3")
PHASES=("1e-15","1e-12","1e-10","1e-8")
VALID=("equivalent","equivalent*","not_equivalent")
HISTORICAL_DISTANCE_CANDIDATE="2e-5"

def binary_label(label):
    if label in ("equivalent","equivalent*"):
        return "EQUIVALENT"
    if label=="not_equivalent":
        return "NOT_EQUIVALENT"
    raise ValueError("Not a determinate equivalence label: "+str(label))



def metrics(row):
    re=Fraction(Decimal(row["solver_real_printed"]))
    im=Fraction(Decimal(row["solver_imag_printed"]))
    twice=Fraction(Decimal(str(row["expected_log2"])))*2
    if twice.denominator!=1 or abs(twice.numerator)>2000:
        raise ValueError("Non-integral/unsupported exponent: "+row["id"])
    norm=Fraction(2)**int(twice)
    defect=1-(re*re+im*im)/norm
    scale=abs(re)+abs(im)
    if scale==0:raise ValueError("Zero complex count: "+row["id"])
    phase=abs(math.atan2(float(im/scale),float(re/scale)))
    return defect,phase


def predict(defect,phase,distance_tolerance,phase_tolerance):
    epsilon=Fraction(Decimal(str(distance_tolerance)))
    if defect>epsilon*epsilon:
        return "not_equivalent"
    return "equivalent" if phase<float(phase_tolerance) else "equivalent*"


def evaluate(data):
    case_rows=[]
    valid=[]
    for item in data["records"]:
        r=item["numeric_summary"]
        if r["wmc_evidence_status"]!="WMC_PRINTED_VALUE_AVAILABLE":
            case_rows.append({"id":r["id"],"historical":r["verdict"],
                              "status":"NOT_REPLAYABLE","defect":None,
                              "estimated_distance":None,"signed_abs_phase_rad":None})
            continue
        if r["verdict"] not in VALID:
            raise ValueError("Nondeterminate original WMC: "+r["id"])
        defect,phase=metrics(r)
        candidate=predict(defect,phase,HISTORICAL_DISTANCE_CANDIDATE,"1e-8")
        x={"id":r["id"],"historical":r["verdict"],
           "historical_binary":binary_label(r["verdict"]),
           "candidate_binary":binary_label(candidate),
           "candidate_binary_matches":binary_label(candidate)==binary_label(r["verdict"]),
           "status":"ORIGINAL_PRINTED_WMC_REPLAY",
           "defect":str(float(defect)),
           "estimated_distance":str(math.sqrt(max(0.0,float(defect)))),
           "signed_abs_phase_rad":format(phase,".17g"),
           "original_unwrapped_phase_rad":str(r["original_phase_rad"]),
           "source_run":r["source_run_id"]}
        case_rows.append(x)
        valid.append((x,defect,phase))
    if len(case_rows)!=184 or len(valid)!=101 or len({x["id"] for x in case_rows})!=184:
        raise ValueError("Archive source counts have changed")
    accepted=[x for x in valid if x[0]["historical"]!="not_equivalent"]
    rejected=[x for x in valid if x[0]["historical"]=="not_equivalent"]
    if (len(accepted),len(rejected))!=(45,56):
        raise ValueError("Unexpected original label count")
    highest=max(accepted,key=lambda x:x[1])
    smallest=min(rejected,key=lambda x:x[1])
    largest_eq=max((x for x in accepted if x[0]["historical"]=="equivalent"),
                   key=lambda x:x[2])
    smallest_star=min((x for x in accepted if x[0]["historical"]=="equivalent*"),
                      key=lambda x:x[2])
    if not all(x["candidate_binary_matches"] for x,_,_ in valid):
        raise ValueError("Candidate binary WMC agreement no longer holds")
    sweep=[]
    for epsilon in DISTANCES:
        for phi in PHASES:
            exact=0
            binary=0
            mismatches=[]
            for x,defect,phase in valid:
                old=x["historical"]
                new=predict(defect,phase,epsilon,phi)
                exact+=(old==new)
                binary+=((old=="not_equivalent")==(new=="not_equivalent"))
                if old!=new:
                    mismatches.append({"id":x["id"],"old":old,"new":new,
                                       "type":("distance" if (old=="not_equivalent")!=(new=="not_equivalent") else "phase")})
            sweep.append({"distance_tolerance":epsilon,"phase_tolerance":phi,
                          "numeric_records":len(valid),"binary_match":binary,
                          "exact_match":exact,"mismatches":mismatches})
    return {
        "schema":"tacas26-historical-wmc-v0140-offline-calibration-v2",
        "primary_acceptance_metric":"BINARY_EQUIVALENT_VS_NOT_EQUIVALENT",
        "binary_candidate":{
            "approximate_distance_tolerance":HISTORICAL_DISTANCE_CANDIDATE,
            "matched":sum(x["candidate_binary_matches"] for x,_,_ in valid),
            "total":len(valid),
            "mismatched_case_ids":[x["id"] for x,_,_ in valid if not x["candidate_binary_matches"]],
            "phase_tolerance_independent":True,
            "scope":"SAME_historical_GPMC_printed_counts_NOT_new_v014_solver_execution"
        },
        "binary_compatibility_window":{
            "lower_bound_inclusive":True,
            "lower_bound_case_id":highest[0]["id"],
            "lower_bound_distance_estimate":highest[0]["estimated_distance"],
            "upper_bound_exclusive":True,
            "upper_bound_case_id":smallest[0]["id"],
            "upper_bound_distance_estimate":smallest[0]["estimated_distance"],
            "meaning":"eps >= max historical accepted distance and eps < min historical rejected distance for these same 101 original printed WMC counts only",
        },
        "source_sha":data["historical_source_sha"],
        "target_classifier_sha":"2e3c5f1b160324445240db8ee204988c5d1aed70",
        "population":{"all":184,"wmc":101,"positive":45,"negative":56},
        "max_accepted_distance":{"id":highest[0]["id"],
                                 "value":highest[0]["estimated_distance"]},
        "min_rejected_distance":{"id":smallest[0]["id"],
                                 "value":smallest[0]["estimated_distance"]},
        "phase_infeasibility":{
            "old_equivalent_requires_phase_tol_gt":largest_eq[2],
            "case_needing_large_phase_tol":largest_eq[0]["id"],
            "old_equivalent_star_requires_phase_tol_le":smallest_star[2],
            "case_needing_small_phase_tol":smallest_star[0]["id"],
            "single_phase_tolerance_possible":largest_eq[2]<smallest_star[2],
        },
        "methodology":"Exact Fraction(Decimal(GPMC stdout)) squared-defect comparison with v0.14 printed-count classifier and scaled atan2 phase; original v0.9.1 source only",
        "limitations":["Not a current v0.14 QASM/solver execution",
                       "Source RR reductions and CNF conversion may differ",
                       "GPMC printed digits have no certified solver error bound",
                       "Missing/censored/WMC-less cases excluded",
                       "No universal default implied; no CodSpeed measurement"],
        "cases":case_rows,"sweep":sweep}


def generate(source=SOURCE,out=OUT):
    data=json.loads(Path(source).read_text())
    report=evaluate(data)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    with (out/"cases.csv").open("w",newline="") as f:
        columns=["id","historical","historical_binary","candidate_binary","candidate_binary_matches","status","defect","estimated_distance",
                 "signed_abs_phase_rad","original_unwrapped_phase_rad","source_run"]
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(report["cases"])
    with (out/"sweep.csv").open("w",newline="") as f:
        columns=["distance_tolerance","phase_tolerance","numeric_records",
                 "binary_match","exact_match"]
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["sweep"])
    lines=["# TACAS v0.9.1 to v0.14.0 binary equivalence tolerance replay","",
           "**PRIMARY GOAL: equivalent/equivalent* versus not_equivalent; the phase subtype is secondary.**",
           "OFFLINE ORIGINAL PRINTED COUNTS ONLY; not a new v0.14 solver run.",
           "",
           "101 cases with GPMC counts, including 45 historical positive",
           "and 56 historical negative results.","",
           "Maximum positive distance estimate: "+str(report["max_accepted_distance"]),
           "Minimum negative distance estimate: "+str(report["min_rejected_distance"]),
           "Candidate for reproduced binary historical WMC labels: 2e-5 distance (101/101).",
           "This must not replace the modern public default 1e-8.",
           "",
           "The old phase [0, 2pi) label convention is inconsistent with",
           "modern signed atan2 wrapping for five near-zero negative phases.",
           "One phase tolerance cannot reproduce all historical three-way labels; this is a SECONDARY label discrepancy.",
           "",
           "## Primary binary result (phase tolerance = 1e-8 rad only for secondary label)","",
           "| Distance epsilon | binary equivalence reproduced | secondary exact label |",
           "|---:|---:|---:|"]
    for row in report["sweep"]:
        if row["phase_tolerance"]=="1e-8":
            lines.append("| "+row["distance_tolerance"]+" | "+str(row["binary_match"])+
                         "/101 | "+str(row["exact_match"])+"/101 |")
    lines.extend(["",
                  "## Evidence limits",
                  "Phase tolerance does not enter the WMC equivalent/not_equivalent test.",
                  "The binary historical-fit interval is [max original accepted distance, min original rejected distance).",
                  "It only applies to fixed historical printed GPMC values: RR reduction, CNF normalization,",
                  "solver precision and generated WMC values may change in a real v0.14.0 rerun.",
                  "Cases lacking printed WMC output (RR-only, timeout, watchdog) are NOT scored.",
                  "Do not change v0.14 default 1e-8 from these historical data alone.",
                  "",
                  "Data: cases.csv, sweep.csv, report.json","",
                  "Old classifier rounded log2(magnitude) to three decimals before",
                  "1e-10 comparison. The theoretical coarse rounded-log acceptance",
                  "boundary can reach about 0.0263 projective distance;",
                  "the observed printed original counts need only ~1.38e-5.",
                  "Separate tolerance scopes: RR chemistry cannot be reconstructed",
                  "from these printed GPMC values; original phase labels are",
                  "not an independent source-equivalence oracle.",""])
    (out/"README.md").write_text("\n".join(lines))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--output",type=Path,default=OUT)
    a=parser.parse_args()
    r=generate(a.source,a.output)
    print(json.dumps({"population":r["population"],"window":
                      [r["max_accepted_distance"],r["min_rejected_distance"]],
                      "phase_infeasibility":r["phase_infeasibility"]},sort_keys=True))
