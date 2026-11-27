#!/usr/bin/env python3
"""E1c matched encoding/solver pilot. No production or RR changes."""
import itertools,json,statistics,subprocess,sys
from pathlib import Path
from eq_dag_d3_ab import sha,git,run as gpmc_run,compare,controls,DELTA
from eq_dag_d3c_raw import run as raw_run,parity,RAW
from eq_dag_phase_screen import read_snapshot

D1="8811544a462338569bc5a375e3df41fdd18ea3b8"
E1B="2addb665bd8015791c5ee7527a8ce0de5bf8e3a1"
CASES=("wstate_16","grover-noancilla_negative_5","qwalk-noancilla_negative_5","vqe_16","qnn_8","qnn_12","vqe_negative_8")
MODES=("archived","canonical","factored")
SOLVERS=("gpmc","rawmocs")

def main():
    controls()
    d1,e1b,gpmc,reader,rawdir,raw,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (d1/"head.txt").read_text().strip()==D1
    assert (d1/"tree.txt").read_text().strip()=="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"
    assert (e1b/"head.txt").read_text().strip()==E1B
    assert (e1b/"tree.txt").read_text().strip()=="f3c63a58c6a7ab651e0117e2a847ffa52b1c0f47"
    assert subprocess.check_output(["git","-C",str(rawdir),"rev-parse","HEAD"],text=True).strip()==RAW
    assert json.loads((d1/"provenance.json").read_text())["gpmc_sha256"]==sha(gpmc)
    source={r["case"]:r for r in map(json.loads,(d1/"rows.jsonl").read_text().splitlines())}
    receipt=json.loads((e1b/"receipts.json").read_text())
    assert receipt["summary"]["arms"]==receipt["summary"]["exact_phase_replay"]==receipt["summary"]["flat_weight_multiset_parity"]==12
    rec={r["case"]:r for r in receipt["rows"]}
    assert len(rec)==12
    for case,r in rec.items():
        arm=d1/(case+"-hybrid")
        assert sha(arm/"residual.tsv")==r["source_residual_sha256"]==source[case]["residual_sha256"]
        assert sha(arm/"actual.cnf")==r["original_cnf_sha256"]==source[case]["cnf"]["sha256"]
        for name in ("flat","factored"):
            assert sha(e1b/(case+"-"+name+".cnf"))==r[name+"_sha256"]
        assert r["exact_phase_replay"] and r["flat_weight_multiset_parity"]
    prov=dict(head=git("rev-parse","HEAD"),d1=D1,e1b=E1B,raw_source=RAW,gpmc_sha256=sha(gpmc),reader_sha256=sha(reader),raw_sha256=sha(raw),digits=30,raw_bits=100,timeout_s=60,raw_outer_s=62,address_space_mib=4096,normalized_delta=str(DELTA),scope="solver-only screening; 7 fixed cases; 2 reversed periods; no certified finite-weight bound or E2E claim")
    (out/"provenance.json").write_text(json.dumps(prov,indent=2)+"\n")
    reports=[]
    for case in CASES:
        arm=d1/(case+"-hybrid")
        n,h,_,_=read_snapshot(arm/"residual.tsv");k=2*n+h
        files=dict(archived=arm/"actual.cnf",canonical=e1b/(case+"-flat.cnf"),factored=e1b/(case+"-factored.cnf"))
        samples=[];comparisons=[];expected_wrong=[];unexpected=[]
        order=list(itertools.product(SOLVERS,MODES))
        for period,seq in enumerate((order,list(reversed(order))),1):
            for solver,mode in seq:
                folder=out/f"{case}-{period}-{solver}-{mode}"
                if solver=="gpmc":
                    x=gpmc_run(gpmc,reader,files[mode],folder,k)
                    if x["returncode"]==137: x["status"]="KILLED_137";x["rss_individual_kib"]=None
                    elif x["returncode"]==124: x["status"]="OUTER_TIMEOUT"
                    if x["status"]=="COMPLETE" and set(x["reported_precision"])!={"30"}:
                        x["status"]="PRECISION_MISMATCH"
                    if x["status"]=="COMPLETE" and ((source[case]["expected"]=="EQ" and x["verdict"]=="not_equivalent") or (source[case]["expected"]=="NEQ" and x["verdict"] in ("equivalent","equivalent*"))):
                        expected_wrong.append([period,mode,x["verdict"]])
                else:
                    # Wstate16 all variants exceed normal admission cap.
                    x=raw_run(raw,files[mode],folder,case=="wstate_16")
                if x["status"] not in ("COMPLETE","TIMEOUT","OUTER_TIMEOUT","KILLED_137","RESOURCE_LIMIT","ROUTE_REJECTED"):
                    unexpected.append([period,solver,mode,x["status"]])
                row=dict(period=period,solver=solver,mode=mode,**x)
                samples.append(row)
                print("E1C_ARM",json.dumps(dict(case=case,**row)),flush=True)
        # Every pair of observations, including within-variant repeatability
        # and cross-solver counts. Raw SAT status is not an EQ verdict.
        for a,b in itertools.combinations(samples,2):
            same_gpmc=a["solver"]==b["solver"]=="gpmc"
            result=compare(a,b,k)["status"] if same_gpmc else parity(a,b,k)
            comparisons.append(dict(a=[a["period"],a["solver"],a["mode"]],b=[b["period"],b["solver"],b["mode"]],status=result))
        stats={}
        for solver,mode in order:
            v=[x for x in samples if (x["solver"],x["mode"])==(solver,mode)]
            done=[x for x in v if x["status"]=="COMPLETE"]
            def rss(x):
                s=str(x.get("rss_individual_kib")).strip()
                return int(s) if s.isdigit() else None
            rv=[rss(x) for x in done]
            stats[solver+"/"+mode]=dict(complete=len(done),statuses=[x["status"] for x in v],routes=[x.get("route") for x in v],median_wall_s=statistics.median(x["wall_s"] for x in done) if len(done)==2 else None,median_rss_kib=statistics.median(rv) if len(rv)==2 and all(x is not None for x in rv) else None)
        bad=sum(c["status"]=="DISAGREEMENT" for c in comparisons)
        ratios={}
        for solver in SOLVERS:
            for base,candidate in (("archived","canonical"),("canonical","factored"),("archived","factored")):
                a,b=stats[solver+"/"+base],stats[solver+"/"+candidate]
                if a["complete"]==b["complete"]==2 and not (bad or expected_wrong or unexpected):
                    ratios[solver+"/"+base+"->"+candidate]=a["median_wall_s"]/b["median_wall_s"]
        record=dict(case=case,expected=source[case]["expected"],normalization_twice_log2=k,stats=stats,ratios=ratios,comparisons=comparisons,disagreements=bad,expected_wrong=expected_wrong,unexpected=unexpected,samples=samples)
        reports.append(record)
        with (out/"cases.jsonl").open("a") as f: f.write(json.dumps(record)+"\n")
        print("E1C_CASE",json.dumps({x:y for x,y in record.items() if x not in ("samples","comparisons")}),flush=True)
    summary=dict(arms=sum(len(r["samples"]) for r in reports),cases=len(reports),complete=sum(x["status"]=="COMPLETE" for r in reports for x in r["samples"]),disagreements=sum(r["disagreements"] for r in reports),expected_wrong=sum(len(r["expected_wrong"]) for r in reports),unexpected=sum(len(r["unexpected"]) for r in reports),paired_pass=sum(c["status"]=="PASS" for r in reports for c in r["comparisons"]),paired_incomplete=sum(c["status"]=="INCOMPLETE" for r in reports for c in r["comparisons"]))
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("E1C_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==84 and summary["disagreements"]==summary["expected_wrong"]==summary["unexpected"]==0 and summary["paired_pass"]>0

if __name__=="__main__": main()
