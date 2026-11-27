#!/usr/bin/env python3
"""L1 bounded research screen: current encoder, four sealed small residuals.
No repeated periods, no performance admission, no native EQ claim.
"""
import ast,itertools,json,math,sys,time
from pathlib import Path
from eq_dag_e1a_census import coeff,scan
from eq_dag_e1b_encode import build,weight_fn,positive_weights,test
from eq_dag_phase_screen import read_snapshot,flat_counts
from eq_dag_d3_ab import sha,git,run as gpmc_run,compare,DELTA
from eq_dag_d3c_raw import run as raw_run,parity
from eq_dag_e1c_ab import D1,SOLVERS,MODES
from eq_dag_e1c_matrix import verify

CASES=("wstate_8","qwalk-noancilla_negative_4","qnn_8","vqe_negative_8")
CAP=5
INCOMPLETE={"TIMEOUT","OUTER_TIMEOUT","KILLED_137","RESOURCE_LIMIT","ROUTE_REJECTED"}

def outcome(samples,comparisons,expected):
    if any(x["status"]!="COMPLETE" and x["status"] not in INCOMPLETE for x in samples):
        return "FAIL"
    if "DISAGREEMENT" in comparisons: return "FAIL"
    if expected not in ("EQ","NEQ"): return "FAIL"
    wanted={"equivalent","equivalent*"} if expected=="EQ" else {"not_equivalent"}
    opposite={"not_equivalent"} if expected=="EQ" else {"equivalent","equivalent*"}
    verdicts=[x["verdict"] for x in samples if x["solver"]=="gpmc" and x["status"]=="COMPLETE"]
    if any(v in opposite for v in verdicts): return "FAIL"
    if any(x["status"]!="COMPLETE" for x in samples) or any(v not in wanted for v in verdicts):
        return "INCONCLUSIVE"
    assert len(samples)==6 and len(verdicts)==3 and len(comparisons)==15
    return "SCREEN_PASS" if all(c=="PASS" for c in comparisons) else "FAIL"

def controls():
    v=[dict(solver=s,mode=m,status="COMPLETE",**({"verdict":"equivalent"} if s=="gpmc" else {})) for s,m in itertools.product(SOLVERS,MODES)]
    c=["PASS"]*15
    assert outcome(v,c,"EQ")=="SCREEN_PASS"
    assert outcome(v,c,"NEQ")=="FAIL"
    assert outcome(v,["DISAGREEMENT"]+c[1:],"EQ")=="FAIL"
    assert outcome([dict(v[0],status="OUTER_TIMEOUT")]+v[1:],c,"EQ")=="INCONCLUSIVE"
    assert outcome([dict(v[0],status="INVALID_PARTIAL_OUTPUT")]+v[1:],c,"EQ")=="FAIL"
    assert outcome([dict(v[0],verdict="unknown")]+v[1:],c,"EQ")=="INCONCLUSIVE"
    print("L1_CONTROLS_PASS")

def main():
    controls()
    d1,bundle,lib,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    identity=verify(bundle)
    assert (d1/"head.txt").read_text().strip()==D1
    assert (d1/"tree.txt").read_text().strip()=="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"
    assert json.loads((d1/"provenance.json").read_text())["gpmc_sha256"]==sha(bundle/"gpmc")
    source={r["case"]:r for r in map(json.loads,(d1/"rows.jsonl").read_text().splitlines())}
    weight=weight_fn(lib);test(weight)
    prov=dict(head=git("rev-parse","HEAD"),tree=git("rev-parse","HEAD^{tree}"),source=D1,bundle=identity,mpfr_bridge_sha256=sha(lib),cases=list(CASES),digits=30,raw_bits=100,cap_s=CAP,raw_outer_s=CAP+2,address_space_mib=4096,normalized_delta=str(DELTA),scope="current research encoder; 1 period, screen only")
    (out/"provenance.json").write_text(json.dumps(prov,indent=2)+"\n")
    reports=[]
    for case in CASES:
        r=source[case];arm=d1/(case+"-hybrid");snap=arm/"residual.tsv";archived=arm/"actual.cnf"
        assert sha(snap)==r["residual_sha256"] and sha(archived)==r["cnf"]["sha256"]
        t=time.monotonic()
        n,h,phase,outputs=read_snapshot(snap);k=2*n+h
        p={m:coeff(v) for m,v in phase.items()};assert all(c is not None for c in p.values())
        domain=ast.literal_eval(next(s.split("\t")[1] for s in snap.read_text().splitlines() if s.startswith("vars\t")))
        assert len(domain)==n+h and domain==sorted(set(domain))
        bits=max(96,32*math.ceil((-2*math.log2(1e-8)+math.ceil(math.log2(max(1,len(p))))+32)/32))
        plan=scan(p,"mixed")
        assert plan["status"]=="OK" and plan["exact_replay"]
        a=build(domain,n,p,outputs,[],weight,bits)
        b=build(domain,n,p,outputs,plan["choices"],weight,bits)
        flat=a.render();factored=b.render()
        assert (a.n,len(a.c))==flat_counts(n,h,phase,outputs)==(r["cnf"]["variables"],r["cnf"]["clauses"])
        assert positive_weights(flat)==positive_weights(archived.read_text())
        assert len(a.w)-len(b.w)==plan["weighted_factor_saving"] and b.n<=a.n and len(b.c)<=len(a.c)
        files={"archived":archived,"canonical":out/(case+"-canonical.cnf"),"factored":out/(case+"-factored.cnf")}
        files["canonical"].write_text(flat);files["factored"].write_text(factored)
        encode_s=time.monotonic()-t
        samples=[]
        for solver,mode in itertools.product(SOLVERS,MODES):
            dest=out/f"{case}-{solver}-{mode}"
            if solver=="gpmc":
                x=gpmc_run(bundle/"gpmc",bundle/"reader",files[mode],dest,k,cap=CAP)
                if x["returncode"]==137: x["status"]="KILLED_137";x["rss_individual_kib"]=None
                elif x["returncode"]==124: x["status"]="OUTER_TIMEOUT"
                if x["status"]=="COMPLETE" and set(x["reported_precision"])!={"30"}: x["status"]="PRECISION_MISMATCH"
            else:
                x=raw_run(bundle/"rawmocs",files[mode],dest,False,cap=CAP)
            x.update(solver=solver,mode=mode)
            samples.append(x)
            print("L1_ARM",json.dumps(dict(case=case,**x)),flush=True)
        comparisons=[]
        for a1,b1 in itertools.combinations(samples,2):
            s=compare(a1,b1,k)["status"] if a1["solver"]==b1["solver"]=="gpmc" else parity(a1,b1,k)
            comparisons.append(dict(a=[a1["solver"],a1["mode"]],b=[b1["solver"],b1["mode"]],status=s))
        status=outcome(samples,[c["status"] for c in comparisons],r["expected"])
        record=dict(case=case,expected=r["expected"],status=status,residual_sha256=sha(snap),normalization_twice_log2=k,weight_bits=bits,encoding_wall_s=encode_s,flat_vars=a.n,factored_vars=b.n,flat_clauses=len(a.c),factored_clauses=len(b.c),samples=samples,comparisons=comparisons)
        reports.append(record)
        with (out/"cases.jsonl").open("a") as f: f.write(json.dumps(record)+"\n")
        print("L1_CASE",json.dumps({x:y for x,y in record.items() if x not in ("samples","comparisons")}),flush=True)
    assert len(reports)==4 and sum(len(r["samples"]) for r in reports)==24
    states=[r["status"] for r in reports]
    status="FAIL" if "FAIL" in states else "INCONCLUSIVE" if "INCONCLUSIVE" in states else "SCREEN_PASS"
    summary=dict(status=status,cases=4,arms=24,complete=sum(x["status"]=="COMPLETE" for r in reports for x in r["samples"]),encoding_wall_s=sum(r["encoding_wall_s"] for r in reports),solver_wall_s=sum(x["wall_s"] for r in reports for x in r["samples"]),scope="L1 only; not L2 or admission")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("L1_SUMMARY",json.dumps(summary),flush=True)
    sys.exit({"SCREEN_PASS":0,"FAIL":1,"INCONCLUSIVE":3}[status])

if __name__=="__main__":
    if sys.argv[1:]==["controls"]: controls()
    else: main()
