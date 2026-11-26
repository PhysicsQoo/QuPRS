"""Independent scalar residual contraction: no Rust CRR, CNF or WMC.

Exact Fraction coefficients, equality connected components (all variables
are summed in a scalar trace), Boolean indicator factors, deterministic
minimum bucket width elimination, mpmath at two precisions. Resource
rejections are inconclusive. This checks residual semantics, not QASM
parser/initial RR/source trust. Not a certified interval computation.
"""
from fractions import Fraction
from pathlib import Path
from collections import defaultdict
import hashlib
import itertools
import json
import os
import re
import subprocess
import tempfile
import time
import mpmath as mp

ROOT = Path(__file__).resolve().parents[2]
MAX_WIDTH = 14
MAX_WORK = 2_000_000
IDS = ("qft_16", "qft_20", "qft_22", "qft_24", "qpeexact_16",
       "qpeexact_20", "qpeinexact_20", "qwalk-noancilla_4", "wstate_4")
MUTATE = ("qft_16", "qpeexact_16", "qwalk-noancilla_4")
cases = {x["id"]: x for x in json.loads((ROOT / "docs/development/paper-corpus-manifest.json").read_text())["cohorts"]["table2_mqt"]["cases"]}
class Limit(Exception):
    pass

def parity(rows):
    result = set()
    for m in rows:
        m = tuple(sorted(set(m)))
        if m in result:
            result.remove(m)
        else:
            result.add(m)
    return result

def reduce_factors(ir):
    live = set(ir["live"])
    rows = [parity([*f, [i]]) for i, f in enumerate(ir["outputs"])]
    # Independent graph connected components, not a selected internal
    # alias forest; merging inputs is valid ONLY for scalar trace.
    edges = defaultdict(set)
    for q in rows:
        if len(q) == 2 and all(len(m) == 1 for m in q):
            a, b = [m[0] for m in q]
            edges[a].add(b)
            edges[b].add(a)
    mapping = {}
    for v in sorted(live):
        if v in mapping:
            continue
        todo = [v]
        mapping[v] = v
        while todo:
            u = todo.pop()
            for z in edges[u]:
                if z not in mapping:
                    mapping[z] = v
                    todo.append(z)
    def project(m):
        return tuple(sorted({mapping[v] for v in m}))
    phase = defaultdict(lambda: (Fraction(0), Fraction(0)))
    for m, a, b in ir["phase"]:
        k = project(m)
        x, y = phase[k]
        phase[k] = ((x + Fraction(a)) % 1, y + Fraction(b))
    return set(mapping.values()), {m: c for m,c in phase.items() if any(c)}, [
        parity(project(m) for m in q) for q in rows
    ], len(live) - len(set(mapping.values()))

def contract(ir, dps, *, project=True):
    with mp.workdps(dps):
        if project:
            live, phase, rows, aliases = reduce_factors(ir)
        else:
            live = set(ir["live"])
            phase = {tuple(m): (Fraction(a), Fraction(b)) for m,a,b in ir["phase"]}
            rows = [parity([*f, [i]]) for i, f in enumerate(ir["outputs"])]
            aliases = 0
        factors = []
        work = peak = 0
        def reserve(width, cost):
            nonlocal work, peak
            peak = max(peak, width)
            work += cost
            if width > MAX_WIDTH or work > MAX_WORK:
                raise Limit(f"width={width} work={work}")
        def real(q):
            return mp.mpf(q.numerator) / q.denominator
        scalar = mp.mpc(1)
        for m,(a,b) in sorted(phase.items()):
            z = mp.expj(2*(mp.pi*real(a)+real(b)))
            if not m:
                scalar *= z
                continue
            reserve(len(m), 1 << len(m))
            factors.append((m, [mp.mpc(1)]*((1<<len(m))-1)+[z]))
        for row in rows:
            if not row:
                continue
            if row == {()}:
                return mp.mpc(0), dict(aliases=aliases, width=peak, work=work)
            scope = tuple(sorted({v for m in row for v in m}))
            reserve(len(scope), (1<<len(scope))*len(row))
            pos = {v:i for i,v in enumerate(scope)}
            masks = [sum(1<<pos[v] for v in m) for m in row]
            factors.append((scope, [int(sum((k&mask)==mask for mask in masks)%2==0)
                                    for k in range(1<<len(scope))]))
        # Sum over every live representative, including isolated variables.
        while live:
            scopes = {v:set() for v in live}
            for scope,_ in factors:
                for v in scope:
                    scopes[v].update(scope)
            pivot = min(live, key=lambda v:(len(scopes[v]),v))
            live.remove(pivot)
            bucket = [(s,t) for s,t in factors if pivot in s]
            if not bucket:
                scalar *= 2
                continue
            factors = [(s,t) for s,t in factors if pivot not in s]
            scope = tuple(sorted(scopes[pivot]))
            rest = tuple(v for v in scope if v != pivot)
            reserve(len(scope), (1<<len(scope))*max(1,len(bucket)))
            pos = {v:i for i,v in enumerate(scope)}
            maps = [[pos[v] for v in s] for s,_ in bucket]
            out = [mp.mpc(0)]*(1<<len(rest))
            p = pos[pivot]
            for k in range(1<<len(scope)):
                z = mp.mpc(1)
                for (_,table),idx in zip(bucket,maps):
                    j = sum(((k>>v)&1)<<i for i,v in enumerate(idx))
                    z *= table[j]
                    if not z:
                        break
                j = (k&((1<<p)-1))|((k>>(p+1))<<p)
                out[j] += z
            if rest:
                factors.append((rest,out))
            else:
                scalar *= out[0]
        assert not factors
        return scalar, dict(aliases=aliases,width=peak,work=work)

def brute(ir):
    with mp.workdps(100):
        live = ir["live"]
        total = mp.mpc(0)
        for bits in itertools.product((0,1),repeat=len(live)):
            x = dict(zip(live,bits))
            def mono(m):
                return all(x[v] for v in m)
            if any(sum(mono(m) for m in f)%2 != x[i] for i,f in enumerate(ir["outputs"])):
                continue
            a = sum((Fraction(c) for m,c,_ in ir["phase"] if mono(m)),Fraction(0))
            b = sum((Fraction(c) for m,_,c in ir["phase"] if mono(m)),Fraction(0))
            total += mp.expj(2*(mp.pi*mp.mpf(a.numerator)/a.denominator+mp.mpf(b.numerator)/b.denominator))
        return total

def controls():
    import random
    rng = random.Random(268)
    with mp.workdps(100):
        for k in range(64):
            phase = [[list(m),str(Fraction(rng.randrange(8),8)),str(Fraction(rng.randrange(-2,3),7))]
                     for d in range(3) for m in itertools.combinations(range(5),d) if rng.randrange(3)==0]
            outputs = [[[2]],[[3]]] if k%2==0 else [[[1]],[[2],[3],[2,4]]]
            ir = dict(n=2,live=list(range(5)),phase=phase,outputs=outputs,twice=7)
            truth = brute(ir)
            for project in (True,False):
                result,_ = contract(ir,100,project=project)
                assert abs(result-truth)<mp.mpf("1e-90"), (k,project)
    print("CRR_REF_CONTROL models=64 comparisons=128",flush=True)

def locked(case,side):
    entry = cases[case][side]
    p = ROOT / entry["path"]
    b = p.read_bytes()
    assert hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()==entry["git_blob_sha1"]
    return p,b

def run_case(name,source,target,expected):
    sha = {k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [("source",source),("target",target)]}
    env = dict(os.environ,CRR_SOURCE=str(source),CRR_TARGET=str(target))
    cmd = ["timeout","--kill-after=3s","45s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_trace::native_reference_export","--","--exact","--nocapture"]
    r = subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    row = dict(case=name,sha256=sha,expected=expected,returncode=r.returncode)
    if r.returncode:
        row.update(status="PROCESS_TIMEOUT" if r.returncode in (124,137) else "ERROR",stderr=r.stderr[-3000:])
        return row
    if "CRR_REF_SKIP " in r.stdout:
        row.update(status="NOT_ADMITTED")
        return row
    def record(prefix):
        return json.loads(next(l[len(prefix):] for l in r.stdout.splitlines() if l.startswith(prefix)))
    ir = record("CRR_REF_IR ")
    solver = record("CRR_REF_SOLVER ")
    row.update(ir=ir,solver=solver)
    start = time.monotonic()
    try:
        low,stats = contract(ir,90)
        high,stats2 = contract(ir,120)
        assert stats==stats2
    except Limit as e:
        row.update(status="REFERENCE_LIMIT",reason=str(e))
        return row
    with mp.workdps(120):
        norm = mp.power(2,mp.mpf(ir["twice"])/2)
        z = high/norm
        stability = abs((high-low)/norm)
        # Conservative empirical stability guard (not interval certification).
        margin = abs(z)**2 - (1-mp.mpf("1e-8")**2)
        verdict = "UNKNOWN" if abs(margin)<=mp.mpf("1e-50") else ("Equivalent" if margin>0 else "NotEquivalent")
        row.update(reference_real=mp.nstr(z.real,100),reference_imag=mp.nstr(z.imag,100),
                   reference_abs=mp.nstr(abs(z),100),reference_verdict=verdict,
                   stability=mp.nstr(stability,8),reference_stats=stats,reference_s=time.monotonic()-start)
        assert stability<mp.mpf("1e-75"), ("precision instability",name)
        if expected is not None:
            target_abs = mp.mpf(1 if expected=="Equivalent" else 0)
            assert abs(abs(z)-target_abs)<mp.mpf("1e-50"), ("analytic mutation mismatch",name)
            assert verdict==expected
        if solver["status"]!="complete":
            row.update(status="SOLVER_INCOMPLETE")
            return row
        def rat(v):
            x=Fraction(v)
            return mp.mpf(x.numerator)/x.denominator
        delta = abs(z.real-rat(solver["real"])/norm)+abs(z.imag-rat(solver["imag"])/norm)
        row.update(normalized_l1=mp.nstr(delta,12))
        assert delta<mp.mpf("1e-60"), ("independent count mismatch",name,mp.nstr(delta,12))
        if verdict!="UNKNOWN":
            assert solver["verdict"]==verdict, ("independent verdict mismatch",name)
        row.update(status="MATCHED" if verdict!="UNKNOWN" else "COUNT_MATCHED_BOUNDARY")
        return row

def main():
    controls()
    results=[]
    with tempfile.TemporaryDirectory(prefix="crr-ref-") as td:
        for name in IDS:
            p,_=locked(name,"source")
            q,_=locked(name,"transpiled")
            results.append(run_case(name,p,q,None))
            print(json.dumps(results[-1]),flush=True)
        for name in MUTATE:
            p,data=locked(name,"source")
            original=data.decode()
            assert not re.search(r"(?m)^\s*(measure|reset)\b",original)
            reg=re.search(r"(?m)^\s*qreg\s+(\w+)\[\d+\]\s*;",original).group(1)
            for tag,angle,expected in [("global_phase","2*pi","Equivalent"),("pauli_z","pi","NotEquivalent")]:
                q=Path(td)/f"{name}-{tag}.qasm"
                q.write_bytes(data+f"\nrz({angle}) {reg}[0];\n".encode())
                results.append(run_case(f"{name}:{tag}",p,q,expected))
                print(json.dumps(results[-1]),flush=True)
    print(json.dumps(dict(summary="independent_reference",n=len(results),statuses={s:sum(r["status"]==s for r in results) for s in sorted({r["status"] for r in results})})),flush=True)
    # Analytic mutation controls are mandatory. Resource limits on
    # original benchmarks are explicit incomplete evidence, not failures.
    assert all(r["status"]!="ERROR" for r in results)
    assert all(r["status"]=="MATCHED" for r in results if r["expected"] is not None)
if __name__=="__main__":
    main()
