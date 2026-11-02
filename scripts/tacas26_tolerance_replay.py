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
        x={"id":r["id"],"historical":r["verdict"],
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
        "schema":"tacas26-historical-wmc-v0140-offline-calibration-v1",
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
        columns=["id","historical","status","defect","estimated_distance",
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
    lines=["# TACAS v0.9.1 to v0.14.0 WMC tolerance replay","",
           "OFFLINE ORIGINAL PRINTED COUNTS ONLY; not a new v0.14 solver run.",
           "",
           "101 cases with GPMC counts, including 45 historical positive",
           "and 56 historical negative results.","",
           "Maximum positive distance estimate: "+str(report["max_accepted_distance"]),
           "Minimum negative distance estimate: "+str(report["min_rejected_distance"]),
           "Candidate for historical WMC numerical labeling: 2e-5 distance.",
           "This must not replace the modern public default 1e-8.",
           "",
           "The old phase [0, 2pi) label convention is inconsistent with",
           "modern signed atan2 wrapping for five near-zero negative phases.",
           "One phase tolerance cannot reproduce all historical three-way labels.",
           "",
           "## Phase tolerance fixed to 1e-8 radians","",
           "| Distance epsilon | eq/not-eq match | exact label match |",
           "|---:|---:|---:|"]
    for row in report["sweep"]:
        if row["phase_tolerance"]=="1e-8":
            lines.append("| "+row["distance_tolerance"]+" | "+str(row["binary_match"])+
                         "/101 | "+str(row["exact_match"])+"/101 |")
    lines.extend(["","Data: cases.csv, sweep.csv, report.json","",
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
