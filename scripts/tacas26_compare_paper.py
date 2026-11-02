#!/usr/bin/env python3
"""Read-only published-verdict comparison, never a performance measurement."""
import argparse
import json
from pathlib import Path
import zipfile
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/"docs/development/tacas26-paper-verdict-oracle.json"

def expected(rows,case):
    suite=case["suite"]
    if suite=="table2":
        return rows["table2"][case["case"]][case["method"]]
    if suite=="table3_positive":
        return rows["table3_positive"][case["case"]][case["method"]]
    if suite=="table3_negative":
        o=rows["table3_negative"]
        if case["method"]=="hybrid":
            if case["case"] in o["hybrid_memoryout"]:return "MemoryOut"
            if case["case"] in o["hybrid_timeout"]:return "Timeout"
        elif case["case"] in o["wmc_only_timeout"]:
            return "Timeout"
        return o["default_verdict"]
    return rows["figure3"][case["case"]][case["method"]]

def read_results(artifacts):
    results={}
    for path in artifacts:
        files=[]
        if path.suffix==".zip":
            with zipfile.ZipFile(path) as zipfile_reader:
                files=[(n,zipfile_reader.read(n)) for n in zipfile_reader.namelist()
                       if n.endswith(".json") and "_results/" in n
                       and not n.endswith("summary.json")
                       and not n.endswith("case-plan.json")]
        elif path.is_dir():
            files=[(str(p),p.read_bytes()) for p in path.rglob("*.json")
                   if p.name not in {"summary.json","case-plan.json"}]
        else:
            files=[(str(path),path.read_bytes())]
        for name,raw in files:
            try: obs=json.loads(raw)
            except ValueError:continue
            key=obs.get("id")
            if not isinstance(key,str) or key.count(":")!=3:continue
            if key in results:
                prev=results[key]
                if (prev.get("status"),prev.get("verdict"))!=(obs.get("status"),obs.get("verdict")):
                    raise ValueError("Conflicting repeated paper evidence: "+key)
            else:
                results[key]=obs
    return results

def compare(root, artifacts):
    from scripts.tacas26_paper_matrix import matrix
    paper=json.loads(ORACLE.read_text())
    observed=read_results(artifacts)
    rows=matrix(root)
    if len(rows)!=187:raise ValueError("Unexpected total paper cases")
    if set(observed)-{r["id"] for r in rows}:
        raise ValueError("Observed non-paper identities")
    report={"schema":"quprs-tacas26-published-comparison-v1",
            "source_tag":"v0.9.1","planned":187,"observed":len(observed),
            "paper_reference":paper["reference"],
            "reference_transcription":paper["transcription_status"],
            "performance_measured":False,"rows":[]}
    for item in rows:
        want=expected(paper,item)
        obs=observed.get(item["id"])
        if obs is None:
            label="NOT_EXECUTED"
        elif obs.get("source_sha") not in (None,"e928abc47dd15926364ec77905eb0d5dc92ce8cc"):
            label="PROVENANCE_MISMATCH"
        elif obs.get("status") not in ("RETURNED","EXTERNAL_TIMEOUT"):
            label="INVALID_OBSERVATION"
        elif want=="UNTRANSCRIBED_FROM_FIGURE":
            label="REFERENCE_NOT_TRANSCRIBED"
        elif obs.get("status")=="EXTERNAL_TIMEOUT" and want=="Timeout":
            label="CENSORED_WATCHDOG_COMPATIBLE"
        elif want=="FAILED_TO_VERIFY":
            label=("PAPER_UNQUALIFIED_LABEL" if obs.get("verdict") in
                   ("unknown","Timeout","MemoryOut") else "REVIEW_PUBLISHED_FAILURE")
        elif obs.get("verdict")==want:
            label="MATCH"
        elif (want in ("Timeout","MemoryOut")
              and obs.get("verdict") in (
                  "equivalent","equivalent*","not_equivalent","Timeout","MemoryOut")):
            label="RESOURCE_LIMIT_DIFFERENCE"
        else:
            label="VERDICT_MISMATCH"
        report["rows"].append({"id":item["id"],"paper":want,
                               "observed":obs.get("verdict") if obs else None,
                               "status":obs.get("status") if obs else "NOT_RUN",
                               "classification":label})
    report["categories"]=dict(Counter(x["classification"] for x in report["rows"]))
    report["fully_executed"]=len(observed)==187
    report["strict_paper_match_certified"]=(
        report["fully_executed"] and not any(x["classification"] in
           ("NOT_EXECUTED","PROVENANCE_MISMATCH","INVALID_OBSERVATION",
            "REFERENCE_NOT_TRANSCRIBED","REVIEW_PUBLISHED_FAILURE",
            "RESOURCE_LIMIT_DIFFERENCE","VERDICT_MISMATCH")
           for x in report["rows"]))
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--artifacts",type=Path,nargs="+",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=compare(a.root,a.artifacts)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"observed":r["observed"],"planned":r["planned"],
         "categories":r["categories"],
         "strict_paper_match_certified":r["strict_paper_match_certified"]},sort_keys=True))

if __name__=="__main__":main()
