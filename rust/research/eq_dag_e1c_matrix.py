#!/usr/bin/env python3
"""Source-locked E1c binary bundle and full-cohort aggregation.
No new solver, no cross-runner performance ranking.
"""
import itertools,json,os,re,subprocess,sys
from pathlib import Path
from eq_dag_d3_ab import sha,git,compare
from eq_dag_d3c_raw import parity,RAW
from eq_dag_e1c_ab import CASES,SHARDS,SOLVERS,MODES,D1,E1B

BINARIES=("gpmc","reader","rawmocs")
def dependencies(binary):
    p=subprocess.run(["ldd",str(binary.resolve())],capture_output=True,text=True)
    lines=p.stdout.splitlines()
    if p.returncode:
        assert "not a dynamic executable" in p.stdout+p.stderr,(binary,p.stderr)
        return {}
    result={}
    for line in lines:
        assert "not found" not in line,line
        m=re.search(r"(?:=>\s+|^\s*)(/[^\s]+)\s+\(",line)
        if m:
            path=Path(m[1])
            result[path.name]=sha(path)
    return result

def identity(bundle):
    return dict(head=git("rev-parse","HEAD"),tree=git("rev-parse","HEAD^{tree}"),
                raw_source=RAW,run_id=os.environ["GITHUB_RUN_ID"],
                run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                arch=os.uname().machine,
                binaries={x:sha(bundle/x) for x in BINARIES},
                libraries={x:dependencies(bundle/x) for x in BINARIES})

def seal(bundle,rawdir):
    assert subprocess.check_output(["git","-C",str(rawdir),"rev-parse","HEAD"],text=True).strip()==RAW
    d=identity(bundle)
    d["rustc"]=subprocess.check_output(["rustc","-vV"],text=True)
    d["cargo"]=subprocess.check_output(["cargo","--version"],text=True).strip()
    (bundle/"identity.json").write_text(json.dumps(d,indent=2)+"\n")

def verify(bundle):
    d=json.loads((bundle/"identity.json").read_text())
    assert all(d[k]==v for k,v in identity(bundle).items()),"binary/dependency/source/run mismatch"
    return d

def keys():
    return set(itertools.product((1,2),SOLVERS,MODES))

def validate_case(row):
    samples=row["samples"]
    key=lambda x:(x["period"],x["solver"],x["mode"])
    assert len(samples)==12 and {key(x) for x in samples}==keys()
    # Verify every original comparison independently, including incomplete outcomes.
    expected={}
    for a,b in itertools.combinations(samples,2):
        s=compare(a,b,row["normalization_twice_log2"])["status"] if a["solver"]==b["solver"]=="gpmc" else parity(a,b,row["normalization_twice_log2"])
        expected[(key(a),key(b))]=s
    actual={(tuple(x["a"]),tuple(x["b"])):x["status"] for x in row["comparisons"]}
    assert len(row["comparisons"])==len(expected)==66 and actual==expected
    assert row["disagreements"]==sum(s=="DISAGREEMENT" for s in expected.values())==0
    assert not row["expected_wrong"] and not row["unexpected"]
    permitted={"COMPLETE","TIMEOUT","OUTER_TIMEOUT","KILLED_137","RESOURCE_LIMIT","ROUTE_REJECTED"}
    assert all(x["status"] in permitted for x in samples)
    for solver,mode in itertools.product(SOLVERS,MODES):
        group=[x for x in samples if (x["solver"],x["mode"])==(solver,mode)]
        assert len({x["cnf_sha256"] for x in group})==1
        assert row["stats"][solver+"/"+mode]["complete"]==sum(x["status"]=="COMPLETE" for x in group)
    for mode in MODES:
        assert len({x["cnf_sha256"] for x in samples if x["mode"]==mode})==1
    return dict(arms=12,cases=1,complete=sum(x["status"]=="COMPLETE" for x in samples),
                disagreements=0,expected_wrong=0,unexpected=0,
                paired_pass=sum(s=="PASS" for s in expected.values()),
                paired_incomplete=sum(s=="INCOMPLETE" for s in expected.values()))

def aggregate(root,out):
    out.mkdir(parents=True,exist_ok=False)
    total={};seen=set();reference=None
    for shard,cases in SHARDS.items():
        p=root/("eq-dag-e1c-shard-"+shard)
        subprocess.run(["sha256sum","-c","SHA256SUMS"],cwd=p,check=True,stdout=subprocess.DEVNULL)
        prov=json.loads((p/"provenance.json").read_text())
        bundle=json.loads((p/"bundle-identity.json").read_text())
        assert prov["head"]==bundle["head"]==git("rev-parse","HEAD")
        assert bundle["tree"]==git("rev-parse","HEAD^{tree}")
        assert bundle["run_id"]==os.environ["GITHUB_RUN_ID"] and bundle["run_attempt"]==os.environ["GITHUB_RUN_ATTEMPT"]
        assert (p/"head.txt").read_text().strip()==bundle["head"] and (p/"tree.txt").read_text().strip()==bundle["tree"]
        assert prov["d1"]==D1 and prov["e1b"]==E1B and prov["raw_source"]==bundle["raw_source"]==RAW
        assert prov["shard"]==shard and prov["selected_cases"]==list(cases)
        assert all(prov[k]==bundle["binaries"][b] for k,b in (("gpmc_sha256","gpmc"),("reader_sha256","reader"),("raw_sha256","rawmocs")))
        assert prov["digits"]==30 and prov["raw_bits"]==100 and prov["timeout_s"]==60 and prov["raw_outer_s"]==62 and prov["address_space_mib"]==4096
        if reference is None: reference=bundle
        assert bundle==reference,"mixed binary bundles or attempts"
        rows=[json.loads(line) for line in (p/"cases.jsonl").read_text().splitlines()]
        assert [r["case"] for r in rows]==list(cases)
        subtotal={}
        for row in rows:
            assert row["case"] not in seen
            seen.add(row["case"])
            for k,v in validate_case(row).items(): subtotal[k]=subtotal.get(k,0)+v
            with (out/"cases.jsonl").open("a") as f: f.write(json.dumps(dict(row,shard=shard))+"\n")
        assert subtotal==json.loads((p/"summary.json").read_text()),"shard summary mismatch"
        for k,v in subtotal.items(): total[k]=total.get(k,0)+v
    assert seen==set(CASES) and total["arms"]==84 and total["cases"]==7
    assert total["paired_pass"]+total["paired_incomplete"]==7*66 and total["paired_pass"]>0
    (out/"summary.json").write_text(json.dumps(total,indent=2)+"\n")
    print("E1C_MATRIX_SUMMARY",json.dumps(total),flush=True)

def controls():
    # Shape-only tests, not scientific evidence.
    assert len(keys())==12 and sorted(itertools.chain.from_iterable(SHARDS.values()))==sorted(CASES)
    samples=[dict(period=p,solver=s,mode=m,status="OUTER_TIMEOUT",cnf_sha256=m) for p,s,m in sorted(keys())]
    key=lambda x:[x["period"],x["solver"],x["mode"]]
    row=dict(samples=samples,normalization_twice_log2=0,comparisons=[dict(a=key(a),b=key(b),status="INCOMPLETE") for a,b in itertools.combinations(samples,2)],disagreements=0,expected_wrong=[],unexpected=[],stats={s+"/"+m:dict(complete=0) for s,m in itertools.product(SOLVERS,MODES)})
    assert validate_case(row)["paired_incomplete"]==66
    for bad in (samples[:-1],samples[:-1]+samples[:1]):
        try: validate_case(dict(row,samples=bad))
        except AssertionError: pass
        else: raise AssertionError("missing/duplicate arm accepted")
    print("E1C_MATRIX_CONTROLS_PASS")

if __name__=="__main__":
    mode=sys.argv[1]
    if mode=="seal": seal(Path(sys.argv[2]),Path(sys.argv[3]))
    elif mode=="verify": verify(Path(sys.argv[2]))
    elif mode=="aggregate": aggregate(Path(sys.argv[2]),Path(sys.argv[3]))
    elif mode=="controls": controls()
    else: raise ValueError(mode)
