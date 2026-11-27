#!/usr/bin/env python3
"""D3c offline mechanism attribution, not a trained router or a solver run.
Pinned GPMC v1.0.2 source: Main.cc, Preprocessor.h, Counter.cc, Component.h.
Read sealed original stdout; report missing stage markers as censored.
"""
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import re
import statistics
import sys
from eq_dag_d2a_rewrite import parse, blocks, replay
from eq_dag_d3_ab import sha

SOURCE="93cae8dbf2da967e34fea8b7f40bc8f98362e2e0"
PRE=re.compile(r"^c o \[([A-Za-z_]+)\s*\] (\d+) vars \((\d+) pvars\), (\d+) cls(?:, (\d+) lrnts, (\d+) fvars, elap\. ([\d.]+) s)?$")
PRIMAL=re.compile(r"^c o Primal graph: nodes (\d+), edges (\d+)$")
TD=re.compile(r"^c o td: #bags (\d+), tw (\d+)")
ELAP=re.compile(r"^c o Elapsed time ([\d.]+) s$")
CPU=re.compile(r"^c o CPU time\s*=\s*([\d.]+) s$")
STAT=re.compile(r"^c o (conflicts|decisions|propagations|Components|Split|Cache lookup|Cache hit|Cache reduce)\s*=\s*(\d+)")
MARKERS={"Reading finished.":"read_done","Simplification starts...":"simplify_start","Simplification finished.":"simplify_done","Preparing extra variable scores ...":"score_start","FlowCutter is running...":"td_start","Counting starts ...":"count_start","Solved by simplification.":"solved_by_simplification","[Result]":"result","GPMC Counting finished.":"finished"}

def attribution(raw):
    marks=[]
    pp=[]
    times={}
    primal=[]
    td=[]
    stats={}
    pending=None
    for line in raw.splitlines():
        line=line.strip()
        if line.startswith("c o ") and line[4:] in MARKERS:
            tag=MARKERS[line[4:]]
            marks.append(tag)
            if tag in ("read_done","simplify_done","score_start"):
                pending=tag
        m=ELAP.fullmatch(line)
        if m and pending is not None:
            times[pending]=float(m[1])
            pending=None
        m=CPU.fullmatch(line)
        if m:
            times["finished"]=float(m[1])
        m=PRE.fullmatch(line)
        if m:
            pp.append(dict(stage=m[1],variables=int(m[2]),projected=int(m[3]),clauses=int(m[4]),learnts=int(m[5]) if m[5] else None,freevars=int(m[6]) if m[6] else None,cpu_s=float(m[7]) if m[7] else None))
        m=PRIMAL.fullmatch(line)
        if m:
            primal.append(dict(nodes=int(m[1]),edges=int(m[2])))
        m=TD.match(line)
        if m:
            td.append(dict(bags=int(m[1]),reported_tw=int(m[2])))
        m=STAT.match(line)
        if m:
            stats[m[1]]=int(m[2])
    # Last confirmed phase, not proof of the actual interrupted location:
    # stdout may be buffered, and partial lines are not parsed.
    if "finished" in marks:
        stage="finished"
    elif "result" in marks:
        stage="result_seen"
    elif "count_start" in marks:
        stage="counting_started"
    elif "td_start" in marks:
        stage="tree_decomposition_started"
    elif "score_start" in marks:
        stage="score_preparation_started"
    elif "simplify_done" in marks:
        stage="simplification_finished"
    elif "simplify_start" in marks or pp:
        stage="simplification_observed"
    elif "read_done" in marks:
        stage="read_finished"
    else:
        stage="no_confirmed_stage"
    dur={}
    for label,a,b in (("simplification","read_done","simplify_done"),("score_preparation","simplify_done","score_start"),("counting_and_finalization","score_start","finished")):
        if a in times and b in times and times[b]>=times[a]:
            dur[label]=round(times[b]-times[a],6)
    return dict(last_confirmed_stage=stage,markers=marks,cumulative_cpu_s=times,approx_cpu_intervals_s=dur,preprocessing=pp,post_simplification=next((x for x in reversed(pp) if x["stage"]=="Simp"),None),primal_graph=primal[-1] if primal else None,td=td[-1] if td else None,skip_td="c o skip td" in raw.splitlines(),ignore_td="c o ignore td" in raw.splitlines(),stats=stats)

def percentile(a,q):
    a=sorted(a)
    return a[(len(a)-1)*q//100] if a else None

def graph(text):
    n,comments,ids,c=parse(text)
    defs,tail=blocks(ids,c)
    weighted=set(ids)
    occ=Counter()
    for clause in c:
        occ.update(set(map(abs,clause)))
    # Pair enumeration is capped; do not claim full primal edge count on cap.
    work=sum(len(set(map(abs,cl)))*(len(set(map(abs,cl)))-1)//2 for cl in c)
    edges=None
    if work<=5000000:
        pairs=set()
        for cl in c:
            for a,b in combinations(sorted(set(map(abs,cl))),2):
                pairs.add(a*(n+1)+b)
        edges=len(pairs)
    fans=Counter(x for ops in defs.values() for x in ops if x in weighted)
    wp=[occ[v] for v in ids]
    up=[occ[v] for v in range(1,n+1) if v not in weighted]
    return dict(variables=n,clauses=len(c),literals=sum(map(len,c)),clause_width_hist=dict(sorted(Counter(map(len,c)).items())),input_primal_pair_work=work,input_primal_edges=edges,weighted_occurrence_p50=percentile(wp,50),weighted_occurrence_p99=percentile(wp,99),weighted_occurrence_max=max(wp,default=0),other_occurrence_p99=percentile(up,99),other_occurrence_max=max(up,default=0),root_fanout_p99=percentile(list(fans.values()),99),root_fanout_max=max(fans.values(),default=0),reused_weighted_roots=len(fans),weighted_root_edges=sum(fans.values()))

def controls():
    s=attribution("c o Reading finished.\nc o Elapsed time 0.02 s\nc o Simplification starts...\nc o [Init   ] 7 vars (7 pvars), 9 cls\nc o [Simp   ] 5 vars (5 pvars), 6 cls, 1 lrnts, 0 fvars, elap. 0.10 s\nc o Simplification finished.\nc o Elapsed time 0.10 s\nc o Preparing extra variable scores ...\nc o Primal graph: nodes 5, edges 8\nc o FlowCutter is running...\nc o td: #bags 4, tw 2\nc o Elapsed time 0.30 s\nc o Counting starts ...\nc o decisions             = 17 (count 17, sat 0)\nc o Cache hit             = 3\nc o GPMC Counting finished.\nc o CPU time    = 1.30 s\n")
    assert s["last_confirmed_stage"]=="finished" and s["stats"]["decisions"]==17
    assert s["post_simplification"]["variables"]==5 and s["td"]["reported_tw"]==2
    assert s["approx_cpu_intervals_s"]==dict(simplification=0.08,score_preparation=0.2,counting_and_finalization=1.0)
    assert attribution("c o Simplification starts...\n")["last_confirmed_stage"]=="simplification_observed"
    assert attribution("")["last_confirmed_stage"]=="no_confirmed_stage"

def main():
    controls()
    d1,d2,d3,d3b,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    for p,h,t in [(d1,"8811544a462338569bc5a375e3df41fdd18ea3b8","b7ebfdcf3cfdac115bf971fddc92306bc66adde8"),(d2,"9c62004793c91f99213f782f3518f84267efb385","4ab682e34d8b748fbdbae3e20380fa28cb4d3f0d"),(d3,"5fb621c803000c6d4ffc7e819c48fad0f4097536","86430ccc4c78185df9768f58e200bce1c4e59f75"),(d3b,"9e9b91e82bb7f7f29542e439e802dda955a6e8fb","d188223e30f0bba5202714bc90582736eaef2d0f")]:
        assert (p/"head.txt").read_text().strip()==h
        assert (p/"tree.txt").read_text().strip()==t
    prov=[json.loads((p/"provenance.json").read_text()) for p in (d1,d3,d3b)]
    assert len({x["gpmc_sha256"] for x in prov})==1
    recs={r["case"]:r for r in json.loads((d2/"rewrite_receipts.json").read_text())["rows"]}
    cases=[json.loads(x) for x in (d3b/"cases.jsonl").read_text().splitlines()]
    assert len(cases)==4
    structures=[]
    logs=[]
    for c in cases:
        case=c["case"]
        r=recs[case]
        files={"flat":d1/(case+"-hybrid")/"actual.cnf","deep":d2/(case+".cnf"),"balanced":d3b/(case+"-balanced.cnf")}
        hashes={"flat":r["flat_sha256"],"deep":r["dag_sha256"],"balanced":c["structure"]["balanced_sha256"]}
        assert all(sha(p)==hashes[m] for m,p in files.items())
        original=files["flat"].read_text()
        for m,p in files.items():
            t=p.read_text()
            if m!="flat":
                replay(original,t)
            q=dict(case=case,mode=m,cnf_sha256=hashes[m],**graph(t))
            structures.append(q)
            print("D3C_GRAPH",json.dumps(q),flush=True)
        for m,seq in c["samples"].items():
            assert len(seq)==3 and m in files
            for i,x in enumerate(seq,1):
                assert x["cnf_sha256"]==hashes[m]
                a=attribution((d3b/f"{case}-{i}-{m}"/"stdout.txt").read_text(errors="replace"))
                logs.append(dict(cohort="D3b",case=case,period=i,mode=m,status=x["status"],wall_s=x["wall_s"],rss_kib=x["rss_valid_kib"],**a))
    for c in map(json.loads,(d3/"cases.jsonl").read_text().splitlines()):
        case=c["case"];r=recs[case]
        for p in c["pairs"]:
            for m in ("flat","dag"):
                x=p[m]
                assert x["cnf_sha256"]==r["flat_sha256" if m=="flat" else "dag_sha256"]
                a=attribution((d3/f"{case}-{p['period']}-{m}"/"stdout.txt").read_text(errors="replace"))
                logs.append(dict(cohort="D3",case=case,period=p["period"],mode=m,status=x["status"],wall_s=x["wall_s"],**a))
    assert len(logs)==84 and len(structures)==12
    groups=[]
    for cohort,case,mode in sorted({(x["cohort"],x["case"],x["mode"]) for x in logs}):
        seq=[x for x in logs if (x["cohort"],x["case"],x["mode"])==(cohort,case,mode)]
        def med(key,field):
            vals=[x[key][field] for x in seq if x.get(key) and x[key].get(field) is not None]
            return statistics.median(vals) if vals else None
        z=dict(cohort=cohort,case=case,mode=mode,arms=len(seq),stages=dict(Counter(x["last_confirmed_stage"] for x in seq)),post_simp_vars=med("post_simplification","variables"),post_simp_clauses=med("post_simplification","clauses"),post_primal_edges=med("primal_graph","edges"),td_reported_tw=med("td","reported_tw"),simplify_cpu_s=med("approx_cpu_intervals_s","simplification"),score_cpu_s=med("approx_cpu_intervals_s","score_preparation"),count_cpu_s=med("approx_cpu_intervals_s","counting_and_finalization"),decisions=med("stats","decisions"),propagations=med("stats","propagations"),components=med("stats","Components"),cache_lookup=med("stats","Cache lookup"),cache_hit=med("stats","Cache hit"))
        groups.append(z)
        print("D3C_GROUP",json.dumps(z),flush=True)
    summary=dict(solver_source=SOURCE,logs=len(logs),structures=len(structures),completed_logs=sum(x["status"]=="COMPLETE" for x in logs),completed_with_finished_marker=sum(x["status"]=="COMPLETE" and x["last_confirmed_stage"]=="finished" for x in logs),post_simplification_observed=sum(x["post_simplification"] is not None for x in logs),td_observed=sum(x["td"] is not None for x in logs),solver_calls=0,scope="retrospective attribution; no fit, causal conclusion or admission")
    (out/"mechanism_audit.json").write_text(json.dumps(dict(summary=summary,structures=structures,logs=logs,groups=groups),indent=2)+"\n")
    print("D3C_SUMMARY",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
