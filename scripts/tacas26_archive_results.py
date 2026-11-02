#!/usr/bin/env python3
"""Archive original QuPRS TACAS'26 Actions observations into immutable Git data.

No Solver calls, competitor tools or performance timing. Preserve raw case JSON.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from scripts.tacas26_quprs_only import matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/development/tacas26-results"
ORACLE=ROOT/"docs/development/tacas26-paper-verdict-oracle.json"
PAPER_DIFFICULTY=ROOT/"benchmarks/codspeed/paper_difficulty.json"
SOURCE_SHA="e928abc47dd15926364ec77905eb0d5dc92ce8cc"
RUNS={"tacas26-v091-matrix-smoke-":(41452992918,0),
      "tacas26-v091-hybrid-full-":(41453497227,1),
      "tacas26-quprs-v091-shard-":(41461438155,2)}
FIELDS=["id","suite","case","kind","method","paper_expected","observed_verdict",
        "status","classification","run_id","artifact","original_sha256",
        "counterpart_sha256","gpmc_sha256","raw_json_sha256","derived_rr",
        "paper_hybrid_time_s","verification_time_s","pathsum_time_s",
        "to_DIMACS_time_s","gpmc_time_s","wmc_time_s",
        "time_evidence_status","time_instrument","codspeed_certified",
        "source_qasm","counterpart_qasm"]

def expected(oracle,case):
    suite,name,method=case["suite"],case["case"],case["method"]
    if suite=="table2":return oracle["table2"][name][method]
    if suite=="table3_positive":
        return oracle["table3_positive"].get(name,{}).get(method,"NOT_REPORTED_IN_TABLE")
    if suite=="figure3":
        return oracle["figure3"].get(name,{}).get(method,"UNTRANSCRIBED_FROM_FIGURE")
    o=oracle["table3_negative"]
    if method=="hybrid":
        if name in o["hybrid_memoryout"]:return "MemoryOut"
        if name in o["hybrid_timeout"]:return "Timeout"
    elif name in o["wmc_only_timeout"]:return "Timeout"
    return o["default_verdict"]

def classify(want,status,got):
    if status in ("MISSING_RESULT","NOT_ARCHIVED"):return status
    if status=="EXTERNAL_TIMEOUT":
        return "CENSORED_WATCHDOG_COMPATIBLE" if want=="Timeout" else "CENSORED_WATCHDOG_UNRESOLVED"
    if status!="RETURNED":return "INVALID_OBSERVATION"
    if want in ("NOT_REPORTED_IN_TABLE","UNTRANSCRIBED_FROM_FIGURE"):return "NO_PUBLISHED_VERDICT"
    if want==got:return "MATCH"
    if want=="FAILED_TO_VERIFY" and got in ("Timeout","MemoryOut","unknown"):
        return "PAPER_UNQUALIFIED_COMPATIBLE"
    if got in ("Timeout","MemoryOut"):return "RESOURCE_LIMIT_INCOMPLETE"
    if want in ("Timeout","MemoryOut","FAILED_TO_VERIFY"):return "RESOURCE_LIMIT_DIFFERENCE"
    if got=="unknown":return "UNKNOWN_NO_VERDICT"
    return "VERDICT_DIFFERENCE_REVIEW"

def load(dirpath):
    selected={}
    all_records=[]
    source_counts=Counter()
    for path in sorted(dirpath.rglob("summary.json")):
        rel=path.relative_to(dirpath)
        artifact=rel.parts[0]
        match=next(((run,rank) for prefix,(run,rank) in RUNS.items()
                    if artifact.startswith(prefix)),None)
        if match is None:continue
        run,rank=match
        summary=json.loads(path.read_text())
        for result in summary.get("results",[]):
            name=result.get("source_result_file")
            f=path.parent/name if name else None
            if f and f.is_file():
                b=f.read_bytes()
                raw=json.loads(b)
                if raw["id"]!=result["id"]:raise ValueError("Mismatched result ID")
                if raw.get("source_sha") not in (None,SOURCE_SHA):
                    raise ValueError("Wrong historical SHA: "+result["id"])
                sha=hashlib.sha256(b).hexdigest()
            else:
                raw=None
                sha=None
            stem=Path(name).stem if name else result["id"].replace(":","_")
            stdout=path.parent/(stem+".stdout")
            stderr=path.parent/(stem+".stderr")
            entry=dict(id=result["id"],status=raw.get("status") if raw else result["status"],
                       verdict=raw.get("verdict") if raw else result.get("verdict"),
                       run_id=run,artifact=artifact,raw_json_sha256=sha,
                       raw=raw,
                       child_stdout=stdout.read_text(errors="replace") if stdout.exists() else None,
                       child_stderr=stderr.read_text(errors="replace") if stderr.exists() else None,
                       source_result_file=name)
            all_records.append(entry)
            source_counts[run]+=1
            prev=selected.get(entry["id"])
            if prev is None or rank>prev[0]:
                selected[entry["id"]]=(rank,entry)
    return {k:v[1] for k,v in selected.items()},all_records,source_counts

def write_table(path,items,fields):
    with path.open("w",encoding="utf-8",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)

def generate(download_dir,output=OUT):
    oracle=json.loads(ORACLE.read_text())
    selected,all_records,source_counts=load(download_dir)
    paper_meta=json.loads(PAPER_DIFFICULTY.read_text())
    reference_times={x["id"]:x for x in paper_meta["cases"]+paper_meta["table3_only_cases"]}
    canonical=matrix(ROOT)
    ids={x["id"] for x in canonical}
    # Original smoke includes one independent RR-only additional method control.
    unexpected=set(selected)-ids-{"table2:ghz32:positive:reduction_rules"}
    if unexpected:raise ValueError("Unknown QuPRS cases: "+repr(sorted(unexpected)))
    rows=[]
    rr_rows=[]
    for case in canonical:
        evidence=selected.get(case["id"])
        raw=evidence.get("raw") if evidence else None
        status=evidence["status"] if evidence else "NOT_ARCHIVED"
        got=evidence["verdict"] if evidence else None
        want=expected(oracle,case)
        def digest(field):
            value=raw.get(field) if raw else None
            return value.get("sha256") if isinstance(value,dict) else None
        derived=raw.get("derived_rr") if raw else None
        meta=reference_times.get(case["case"],{})
        if case["method"]=="hybrid" and case["kind"]=="positive":
            paper_hybrid_time_s=meta.get("positive_hybrid_seconds")
        elif case["method"]=="hybrid" and case["kind"]=="negative":
            paper_hybrid_time_s=meta.get("random_rotation_hybrid_seconds")
        else:
            paper_hybrid_time_s=None
        timing=raw.get("timing") if raw else None
        if timing and timing.get("instrument")!="ORIGINAL_QU_PRS_V091_INTERNAL_CLOCK":
            raise ValueError("Unexpected timing instrument for "+case["id"])
        native=timing.get("values",{}) if timing else {}
        observed_time=any(value is not None for value in native.values())
        time_evidence_status=("ORIGINAL_V091_TIME_CAPTURED" if observed_time
                              else "NOT_CAPTURED_IN_ARCHIVED_RUN" if raw
                              else "NO_RESULT_FILE_OR_WATCHDOG")
        row=dict(id=case["id"],suite=case["suite"],case=case["case"],
                 kind=case["kind"],method=case["method"],paper_expected=want,
                 observed_verdict=got,status=status,classification=classify(want,status,got),
                 run_id=evidence["run_id"] if evidence else None,
                 artifact=evidence["artifact"] if evidence else None,
                 original_sha256=digest("original"),counterpart_sha256=digest("counterpart"),
                 gpmc_sha256=raw.get("original_gpmc_sha256") if raw else None,
                 raw_json_sha256=evidence["raw_json_sha256"] if evidence else None,
                 derived_rr=derived.get("verdict") if isinstance(derived,dict) else None,
                 paper_hybrid_time_s=paper_hybrid_time_s,
                 verification_time_s=native.get("verification_time"),
                 pathsum_time_s=native.get("pathsum_time"),
                 to_DIMACS_time_s=native.get("to_DIMACS_time"),
                 gpmc_time_s=native.get("gpmc_time"),
                 wmc_time_s=native.get("wmc_time"),
                 time_evidence_status=time_evidence_status,
                 time_instrument=timing.get("instrument") if timing else None,
                 codspeed_certified=False,
                 source_qasm=case["a"],counterpart_qasm=case["b"])
        rows.append(row)
        if case["kind"]=="positive" and case["method"]=="hybrid":
            paper_rr=oracle["table2"][case["case"]]["reduction_rules"] if case["suite"]=="table2" else "NOT_REPORTED_IN_TABLE"
            rr_rows.append(dict(case=case["case"],hybrid_id=case["id"],paper_rr=paper_rr,
                                derived_rr=row["derived_rr"] or "UNOBSERVED",
                                pathsum_time_s=row["pathsum_time_s"],
                                time_evidence_status=row["time_evidence_status"],
                                run_id=row["run_id"],status=status))
    if len(rows)!=184 or len(set(x["id"] for x in rows))!=184 or len(rr_rows)!=37:
        raise ValueError("Incomplete source registry")
    counts=Counter(x["classification"] for x in rows)
    output.mkdir(parents=True,exist_ok=True)
    write_table(output/"results.csv",rows,FIELDS)
    write_table(output/"derived_rr.csv",rr_rows,
                ["case","hybrid_id","paper_rr","derived_rr","pathsum_time_s",
                 "time_evidence_status","run_id","status"])
    archive=dict(schema="quprs-tacas26-permanent-results-v1",
                 scope="QU_PRS_ONLY_SCIENCE_WITH_PAPER_REFERENCE_SECONDS",
                 source_sha=SOURCE_SHA,
                 paper_source_sha="d8d3e7da555e9e20bdec6f3abe4a13ad899af62b",
                 paper_reference=oracle["reference"],
                 paper_transcription=oracle["transcription_status"],
                 timing_policy="Historical paper seconds are reference values, NOT new observations; QuPRS native timings were omitted by the original capture runner, no CodSpeed comparison",
                 classifications=dict(counts),run_sources=RUNS,rows=rows,
                 derived_rr=rr_rows,selected_raw_evidence=selected,
                 all_raw_observations_including_repeats=all_records)
    (output/"results.json").write_text(json.dumps(archive,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    lines=["# TACAS 2026 — QuPRS-only experimental results","",
           "Permanent Git archive; source QuPRS v0.9.1 ("+SOURCE_SHA+").",
           "This is science verdict reproduction, NOT CodSpeed timing or Docker image certification.",
           "",
           "## Summary","",
           "- Canonical QuPRS calls: **184**; derived positive Hybrid RR cells: **37**.",
           "- Cases with archived observations: **"+str(184-counts.get("NOT_ARCHIVED",0))+" / 184**.",
           "- Classification counts: "+", ".join(k+" = "+str(v) for k,v in sorted(counts.items()))+".",
           "- Input run records: "+", ".join(str(k)+" = "+str(v) for k,v in sorted(source_counts.items()))+".",
           "- Matching published Timeout is MATCH. External watchdog means censored; missing JSON means MISSING_RESULT.",
           "- Paper Figure 3 per-case verdicts are incompletely transcribed; no silent claims of equality.",
           "- Original per-case JSON, recorded GPMC stdout, child stdout/stderr and source hashes are in results.json.",
           "- Git tracked data is authoritative for preservation, not the expiring Actions artifacts.",
           ""]
    for key,label in (("table2","Table 2 positive MQT"),("table3_positive","WState32 positive extra"),
                       ("table3_negative","Table 3 negative MQT"),("figure3","Figure 3 Feynman")):
        lines.extend(["## "+label,"","| Case | Method | Paper | Observed | Status | Classification | Run |",
                      "|---|---|---|---|---|---|---|"])
        for row in rows:
            if row["suite"]!=key:continue
            run=row["run_id"]
            link=("[Actions "+str(run)+"](https://github.com/PhysicsQoo/QuPRS/actions/runs/"+str(run)+")"
                  if run else "not archived")
            lines.append("| "+ " | ".join(str(row[f]) if row[f] is not None else "—"
                         for f in ("case","method","paper_expected","observed_verdict","status","classification"))+
                         " | "+link+" |")
        lines.append("")
    lines.extend(["## Derived RR from the same Hybrid invocation","",
                  "| Case | Paper RR | Derived RR | Run |","|---|---|---|---|"])
    for item in rr_rows:
        lines.append("| "+item["case"]+" | "+item["paper_rr"]+" | "+item["derived_rr"]+
                     " | "+str(item["run_id"] or "—")+" |")
    lines.extend(["","## Data files","",
                  "- results.csv: full 184-row case table.",
                  "- derived_rr.csv: 37 same-Hybrid RR result cells, not 37 separate method calls.",
                  "- results.json: full raw evidence (with repeated observations and provenance).",""])
    (output/"README.md").write_text("\n".join(lines))
    return dict(counts)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--download-dir",required=True,type=Path)
    p.add_argument("--output",type=Path,default=OUT)
    a=p.parse_args()
    print(json.dumps(generate(a.download_dir,a.output),sort_keys=True))

if __name__=="__main__":
    main()
