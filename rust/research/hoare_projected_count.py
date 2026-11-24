"""Research-only verdict projection on an admitted COMPLETE squared norm.

Not a general phase-sum zero test, source certificate, or numeric leakage
value. A zero coefficient on arbitrary non-norm data is not evidence.
All callers must use the existing shared-input/full-output paired domain.
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import time


def projected_query(base, bits, primary, prefix=()):
    """Pack N_0 and N_(M/2), with signed little-endian selectors."""
    header, *clauses = base.splitlines()
    p, kind, vs, cs = header.split()
    v, c = int(vs), int(cs)
    if (p, kind) != ("p", "cnf") or v < 1 or c != len(clauses):
        raise ValueError("invalid CNF header")
    bits, prefix = tuple(bits), tuple(prefix)
    if not 3 <= len(bits) <= 6 or not 0 <= primary <= v:
        raise ValueError("unsupported phase domain or count bound")
    if any(type(l) is not int or not 0 < abs(l) <= v for l in bits + prefix):
        raise ValueError("invalid phase/prefix literal")
    # Existing Z8 selectors can be signed or aliased; constraining literals
    # (not their absolute IDs) preserves that semantics.
    bound = 1 << primary
    radix = bound * 2
    assumptions = prefix + tuple(-l for l in bits[:-1])
    high = bits[-1]
    weights = f"c p weight {high} {radix} 0\nc p weight {-high} 1 0\n"
    data = (f"c t wmc\np cnf {v} {c+len(assumptions)}\n" + weights +
            "".join(l+"\n" for l in clauses) +
            "".join(f"{l} 0\n" for l in assumptions))
    return data, radix, bound


def decode_projected(value, radix, bound):
    if type(value) is not int or value < 0 or bound < 1 or radix != 2*bound:
        raise ValueError("invalid packed natural count")
    hi, lo = divmod(value, radix)
    if lo > bound or hi > bound or lo+hi > bound:
        raise ValueError("projected count exceeds domain")
    if lo < hi:
        raise ValueError("negative squared-norm coefficient")
    return lo, hi, lo-hi


def projected_contract():
    assert decode_projected(0, 16, 8) == (0,0,0)
    assert decode_projected(3+16*3,16,8) == (3,3,0)
    assert decode_projected(5+16*2,16,8) == (5,2,3)
    big=1<<61
    assert decode_projected(big+1,2*(big+1),big+1)==(big+1,0,big+1)
    for value,radix,bound in [(-1,16,8),(9,16,8),(9*16,16,8),
                               (5+16*4,16,8),(1+16*2,16,8),
                               (0,8,8),(0.0,16,8)]:
        try: decode_projected(value,radix,bound)
        except ValueError: continue
        raise AssertionError("accepted invalid projected count")
    data,r,b=projected_query("p cnf 5 1\n1 0\n",[2,-3,-4],5,[5])
    assert (r,b)==(64,32)
    assert data.splitlines()==["c t wmc","p cnf 5 4","c p weight -4 64 0",
                               "c p weight 4 1 0","1 0","5 0","-2 0","3 0"]
    # Raw phase sum X is nonzero but has constant 0: never admit arbitrary
    # histograms as squared leakage. This is an admission limitation.
    for bits,p in [([1,2],5),([1,2,6],5),([1,2,3],6)]:
        try: projected_query("p cnf 5 0\n",bits,p)
        except ValueError: continue
        raise AssertionError("accepted invalid query domain")
    print("HOARE_PROJECTED_CONTRACT=PASS",flush=True)


def projected_count(gpmc,tmp,base,bits,primary,end,prefix=()):
    from hoare_ganak_exact import parse_gpmc_integer,profile_gpmc,SolverSignalKilled
    data,radix,bound=projected_query(base,bits,primary,prefix)
    tmp=pathlib.Path(tmp)
    path=tmp/"projected-norm.cnf"
    path.write_text(data)
    remaining=end-time.monotonic()
    metrics=[]
    row=dict(status="UNKNOWN",mass=None,verdict="UNKNOWN",n0=None,nd=None,
             queries=metrics,root_queries=0,modulus=1<<len(bits),
             primary_bound_bits=primary,weight_bits=radix.bit_length(),
             base_sha256=hashlib.sha256(base.encode()).hexdigest(),
             query_sha256=hashlib.sha256(data.encode()).hexdigest())
    start=time.monotonic()
    try:
        if remaining<=0: raise TimeoutError("projected stage budget")
        row["root_queries"]=1
        stdout=profile_gpmc([str(gpmc),"-mode=1","-natw",str(path)],remaining,
                            tmp/"projected-resource.tsv",metrics)
        value=parse_gpmc_integer(stdout,"wmc",bound*radix)
        lo,hi,mass=decode_projected(value,radix,bound)
        row.update(status="EXACT_PROJECTED",mass=mass,n0=lo,nd=hi,
                   verdict="PROVED" if mass==0 else "REFUTED")
    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
    row["root_s"]=time.monotonic()-start
    return row


def z8_differential(directory,gpmc,tmp,baseline):
    """Frozen 26 root fixtures; compare also complete input restrictions."""
    projected_contract()
    cases=[]
    with (directory/"hybrid.tsv").open() as f:
        for name,n,nq,delta,expected,witnesses,build_us,direct_us,plan_us in csv.reader(f,delimiter="\t"):
            cases.append((name,int(n),delta,"READY",directory/f"hybrid-{name}-wmc.cnf"))
    with (directory/"pure-rare.tsv").open() as f:
        for name,n,h,delta,expected,witnesses,build_us,encoding_us,status in csv.reader(f,delimiter="\t"):
            cases.append((name,int(n),delta,status,directory/f"pure-{name}.cnf"))
    refs={r["case"]:r for r in baseline}
    assert len(cases)==len(refs)==26
    roots=prefix_checks=0
    for name,n,delta,status,file in cases:
        ref=refs[name]
        if status!="READY":
            print("HOARE_PROJECTED_Z8 "+json.dumps(dict(case=name,status=status,verdict="UNKNOWN")),flush=True)
            continue
        base=file.read_text();bits=list(map(int,delta.split(",")))
        v=int(base.splitlines()[0].split()[2])
        def query(prefix=()):
            return projected_count(gpmc,tmp,base,bits,v,time.monotonic()+5,prefix)
        row=query()
        target=tuple(ref["expected_raw"])
        if row["mass"] is not None:
            assert row["mass"]==target[0] and row["verdict"]==("REFUTED" if any(target) else "PROVED"),(name,row,target)
            if ref["coeff"] is not None: assert row["mass"]==ref["coeff"][0]
            if ref["verdict"]!="UNKNOWN":roots+=1
        row.update(case=name,expected_mass=target[0],baseline_verdict=ref["verdict"],
                   baseline_coeff=ref["coeff"],baseline_root_batches=ref["root_queries"])
        print("HOARE_PROJECTED_Z8 "+json.dumps(row),flush=True)
        if row["mass"] is not None and row["verdict"]=="REFUTED":
            # Original input literals are the same as in pure_wmc_decision.
            left,right=query([-2]),query([2])
            ok=left["mass"] is not None and right["mass"] is not None
            if ok:
                assert left["mass"]+right["mass"]==row["mass"]
                prefix_checks+=1
            print("HOARE_PROJECTED_PREFIX "+json.dumps(dict(case=name,kind="partition",matched=ok,left=left,right=right)),flush=True)
            if ref["witness_status"]=="VERIFIED":
                x=ref["witness"]
                fixed=query([i+2 if x>>i&1 else -(i+2) for i in range(n)])
                ok=fixed["mass"] is not None
                if ok:
                    assert fixed["mass"]==ref["witness_coeff"][0] and fixed["mass"]>0
                    prefix_checks+=1
                print("HOARE_PROJECTED_PREFIX "+json.dumps(dict(case=name,kind="baseline-witness",matched=ok,input=x,projected=fixed)),flush=True)
    print("HOARE_PROJECTED_Z8_SUMMARY "+json.dumps(dict(cases=len(cases),matched_roots=roots,
          prefix_checks=prefix_checks)),flush=True)
    assert roots==26 and prefix_checks==24,(roots,prefix_checks)


def long_differential(directory,gpmc,tmp,solve,deadline,metrics):
    """Matched root-only A/B then B/A on a frozen long-case subset.

    Identical source, CNF, phase selectors, radix, GPMC binary and
    per-arm wall deadline. Existing full Z8 solve first query equals
    the projected query; the full arm must also complete its second
    query. Exports are offline, so timings are NOT end-to-end.
    """
    def manifest(name,fields):
        with (directory/name).open() as f:
            return {r["case"]:r for r in csv.DictReader(f,fieldnames=fields.split(),delimiter="\t")}
    rr=manifest("dispatch-rr.tsv","case h hr scale hits retained representation status reason witness vars clauses delta rr_us encoding_us pure_status pure_vars pure_clauses pure_delta build_us pure_us")
    prop=manifest("property-factor.tsv","case n h hr scale post_count branch_count factor_status cnf_status vars clauses delta common_us base_us factor_us expected oracle")
    cone=manifest("cone.tsv","case h hr gates gr scale vars clauses delta status cone_us build_us encoding_us expected")
    # Predeclared from historical long-cohort evidence, before this run:
    # two direct cases near the 30s decision boundary; one faster cone
    # control; one harder cone. All selected properties are negative.
    cases=[
        ("mixing-10-3layer","direct",30),
        ("affine-mixing-10","direct",30),
        ("mixing-10-3layer","cone",15),
        ("mixing-13-3layer","cone",60),
    ]
    rows=[]
    solver_sha=hashlib.sha256(pathlib.Path(gpmc).read_bytes()).hexdigest()
    for rep in range(2):
        for i,(name,route,cap) in enumerate(cases):
            target=tuple(map(int,prop[name]["expected"].split(",")))
            if route=="direct":
                r=rr[name];status=r["pure_status"];delta=r["pure_delta"];scale=0
                path=directory/f"dispatch-pure-{name}.cnf"
                prep=(int(r["build_us"])+int(r["pure_us"]))/1e6
            else:
                r=cone[name];status=r["status"];delta=r["delta"];scale=int(r["scale"])
                path=directory/f"cone-{name}.cnf"
                prep=sum(int(r[k]) for k in ("cone_us","build_us","encoding_us"))/1e6
                assert r["expected"]==prop[name]["expected"]
            assert status=="READY",(name,route,status)
            base=path.read_text();bits=list(map(int,delta.split(",")))
            v=int(base.splitlines()[0].split()[2])
            first_query,radix,bound=projected_query(base,bits,v)
            first_sha=hashlib.sha256(first_query.encode()).hexdigest()
            src_sha=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest()
            order=("full","projected") if (i+rep)%2==0 else ("projected","full")
            for position,arm in enumerate(order):
                metrics.clear()
                start=time.monotonic()
                # A global cap cannot silently shorten one arm.
                if deadline-start<cap+2:
                    raise RuntimeError("long differential global budget insufficient")
                end=start+cap
                row=dict(case=name,route=route,repeat=rep,position=position,arm=arm,
                         cap_s=cap,cnf_sha256=hashlib.sha256(base.encode()).hexdigest(),
                         source_sha256=src_sha,solver_sha256=solver_sha,
                         first_query_sha256=first_sha,radix_bits=radix.bit_length(),
                         scale=scale,expected_mass=target[0],prep_proxy_s=prep,
                         status="UNKNOWN",verdict="UNKNOWN",mass=None,coeff=None)
                if arm=="full":
                    from hoare_ganak_exact import SolverSignalKilled
                    try:
                        raw=tuple(solve(base,bits,[],end))
                        coeff=tuple(x*(1<<scale) for x in raw)
                        assert coeff==target,(name,route,coeff,target)
                        row.update(status="EXACT_FULL",coeff=coeff,mass=coeff[0],
                                   verdict="REFUTED" if any(coeff) else "PROVED")
                    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                    row["queries"]=[dict(m) for m in metrics]
                else:
                    p=projected_count(gpmc,tmp,base,bits,v,end)
                    assert p["query_sha256"]==first_sha
                    row.update(status=p["status"],verdict=p["verdict"],queries=p["queries"])
                    if p["mass"] is not None:
                        row["mass"]=p["mass"]*(1<<scale)
                        assert row["mass"]==target[0] and row["verdict"]==("REFUTED" if any(target) else "PROVED")
                elapsed=time.monotonic()-start
                qs=row["queries"]
                row.update(root_s=elapsed,decision_proxy_s=prep+elapsed,
                           attempted_queries=len(qs),
                           completed_queries=sum(q["status"]=="COMPLETED" for q in qs),
                           cpu_s=sum(q["user_s"]+q["system_s"] for q in qs) if qs and all(q["user_s"] is not None and q["system_s"] is not None for q in qs) else None,
                           max_rss_kib=max(q["max_rss_kib"] for q in qs) if qs and all(q["max_rss_kib"] is not None for q in qs) else None)
                rows.append(row)
                print("HOARE_PROJECTED_LONG "+json.dumps(row),flush=True)
    assert len(rows)==16
    pairs=[]
    for rep in range(2):
        for name,route,cap in cases:
            f,p=(next(r for r in rows if (r["case"],r["route"],r["repeat"],r["arm"])==(name,route,rep,a)) for a in ("full","projected"))
            if f["mass"] is not None and p["mass"] is not None:
                assert f["mass"]==p["mass"] and f["verdict"]==p["verdict"]
            pairs.append(dict(case=name,route=route,repeat=rep,cap_s=cap,
                              full=f["verdict"],projected=p["verdict"],
                              full_status=f["status"],projected_status=p["status"],
                              full_s=f["root_s"],projected_s=p["root_s"],
                              speedup=f["root_s"]/p["root_s"] if f["mass"] is not None and p["mass"] is not None else None))
    print("HOARE_PROJECTED_LONG_SUMMARY "+json.dumps(dict(pairs=pairs,
          full_decided=sum(p["full"]!="UNKNOWN" for p in pairs),
          projected_decided=sum(p["projected"]!="UNKNOWN" for p in pairs),
          both_decided=sum(p["full"]!="UNKNOWN" and p["projected"]!="UNKNOWN" for p in pairs),
          root_only=True,offline_prep_proxy=True)),flush=True)
