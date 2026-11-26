"""Research-only exact external #SAT experiment; not a production adapter."""
import csv
import decimal
import hashlib
from fractions import Fraction
import json
import os
import signal
import pathlib
import re
import subprocess
import sys
import tempfile
import time

EXPECTED_SHA = "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"

def parse_count(stdout, bound, weighted=False):
    lines = stdout.splitlines()
    def single(prefix):
        rows = [l[len(prefix):].strip() for l in lines if l.startswith(prefix)]
        if len(rows) != 1:
            raise ValueError("missing or conflicting " + prefix)
        return rows[0]
    if any(l.startswith("c s approx") for l in lines):
        raise ValueError("approximate result")
    if single("c s type ") != ("wmc" if weighted else "mc"):
        raise ValueError("wrong counting mode")
    count = single("c s exact arb frac " if weighted else "c s exact arb int ")
    if weighted:
        if not re.fullmatch(r"-?[0-9]+(?:/[1-9][0-9]*)?", count):
            raise ValueError("not an exact rational")
        value = Fraction(count)
        if value.denominator != 1:
            raise ValueError("noninteger signed coefficient")
        n = value.numerator
    else:
        if not re.fullmatch(r"[0-9]+", count):
            raise ValueError("not an exact unsigned integer")
        n = int(count)
    if abs(n) > bound:
        raise ValueError("count exceeds Boolean domain")
    pac = single("c s pac guarantees ")
    m = re.fullmatch(r"epsilon:\s*(\S+)\s+delta:\s*(\S+)", pac)
    if not m or any(decimal.Decimal(v) != 0 for v in m.groups()):
        raise ValueError("nonzero or missing PAC guarantee")
    if single("s ") != ("SATISFIABLE" if n else "UNSATISFIABLE"):
        raise ValueError("count/status mismatch")
    return n

def parser_tests():
    good = "s SATISFIABLE\nc s type mc\nc s exact arb int 9007199254740993\nc s pac guarantees epsilon: 0 delta: 0\n"
    assert parse_count(good, 2**60) == 9007199254740993
    signed = good.replace("type mc", "type wmc").replace("arb int 9007199254740993", "arb frac -3/1")
    assert parse_count(signed, 2**60, weighted=True) == -3
    cancelled = signed.replace("SATISFIABLE", "UNSATISFIABLE").replace("-3/1", "0")
    assert parse_count(cancelled, 2**60, weighted=True) == 0
    for bad in [signed.replace("-3/1", "-3/2"), signed.replace("-3/1", "-3.0"),
                signed.replace("delta: 0", "delta: 1e-12")]:
        try:
            parse_count(bad, 2**60, weighted=True)
        except (ValueError, decimal.InvalidOperation):
            continue
        raise AssertionError("accepted malformed signed response")
    for bad in [good.replace("delta: 0", "delta: 1e-12"),
                good.replace("arb int", "arb frac"),
                good.replace("9007199254740993", "9e15"),
                good.replace("s SATISFIABLE", "s UNSATISFIABLE"),
                good + "c s exact arb int 1\n",
                good + "c s approx arb int 1\n"]:
        try:
            parse_count(bad, 2**60)
        except (ValueError, decimal.InvalidOperation):
            continue
        raise AssertionError("accepted malformed response")

def main():
    parser_tests()
    exe, directory = map(lambda x: pathlib.Path(x).resolve(), sys.argv[1:3])
    if hashlib.sha256(exe.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("unqualified Ganak binary")
    deadline = time.monotonic() + 90
    calls = 0
    solver_seconds = 0.0
    with tempfile.TemporaryDirectory(prefix="hoare-exact-") as tmp:
        query = pathlib.Path(tmp) / "query.cnf"
        def count(base, assumptions, negative_lit=None, stage_deadline=None):
            nonlocal calls, solver_seconds
            lines = base.splitlines()
            _, _, vs, cs = lines[0].split()
            v, c = int(vs), int(cs)
            assert len(lines) == c + 1
            assert all(0 < abs(l) <= v for l in assumptions)
            weighted = negative_lit is not None
            if weighted:
                assert 0 < abs(negative_lit) <= v
            weights = (f"c p weight {negative_lit} -1 0\n"
                       f"c p weight {-negative_lit} 1 0\n") if weighted else ""
            query.write_text(f"c t {'wmc' if weighted else 'mc'}\np cnf {v} {c+len(assumptions)}\n" +
                             weights + "\n".join(lines[1:]) + "\n" +
                             "".join(f"{l} 0\n" for l in assumptions))
            remaining = min(deadline, stage_deadline if stage_deadline is not None else deadline) - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("experiment budget")
            t = time.monotonic()
            r = subprocess.run([str(exe), "--mode", "1" if weighted else "0", "--prob", "0", str(query)],
                               capture_output=True, text=True, timeout=min(5, remaining),
                               check=True)
            solver_seconds += time.monotonic() - t
            calls += 1
            return parse_count(r.stdout, 2**v, weighted=weighted)
        def buckets(base, delta, prefix=()):
            return [count(base, list(prefix) + [l if j >> i & 1 else -l
                     for i, l in enumerate(delta)]) for j in range(8)]
        def signed(ns):
            return tuple(ns[j]-ns[j+4] for j in range(4))
        def symmetric(ns):
            assert all(ns[j] == ns[(-j)%8] for j in range(8))
            return (ns[0]-ns[4], ns[1]-ns[3])
        def four_counts(base, delta, prefix=()):
            values = [count(base, list(prefix) + [l if j >> i & 1 else -l
                      for i, l in enumerate(delta)]) for j in (0,4,1,3)]
            return (values[0]-values[1], values[2]-values[3])
        def two_weighted(base, delta, prefix=(), stage_deadline=None):
            # A=N0-N4: d0=d1=0, sign (-1)^d2.
            # B=N1-N3: d0=1,d2=0, sign (-1)^d1.
            # delta entries are signed literals; assign weights to literals
            # rather than variable IDs to support negated selectors.
            d0,d1,d2 = delta
            return (count(base, list(prefix)+[-d0,-d1], negative_lit=d2, stage_deadline=stage_deadline),
                    count(base, list(prefix)+[d0,-d2], negative_lit=d1, stage_deadline=stage_deadline))

        # Primary GPMC pilot uses a separate budget before Ganak regressions.
        gpmc_rows=run_gpmc_pure(directory,pathlib.Path(sys.argv[4]).resolve(),tmp,time.monotonic()+45)
        deadline=time.monotonic()+90
        # Qualify unweighted free variables, UNSAT and large integers.
        assert count("p cnf 3 1\n1 0\n", []) == 4
        assert count("p cnf 1 2\n1 0\n-1 0\n", []) == 0
        assert count("p cnf 61 1\n1 0\n", []) == 2**60
        # Weighted UNSATISFIABLE status means zero count, not Boolean UNSAT.
        assert count("p cnf 1 0\n", [], negative_lit=1) == 0
        assert count("p cnf 1 1\n1 0\n", [], negative_lit=1) == -1
        assert count("p cnf 1 1\n1 0\n", [], negative_lit=-1) == 1
        direct = {}
        records = []
        with (directory / "manifest.tsv").open() as fh:
            for name, route, n, scale, delta, expected, witnesses in csv.reader(fh, delimiter="\t"):
                n, scale = int(n), int(scale)
                delta = list(map(int, delta.split(",")))
                expected = list(map(int, expected.split(",")))
                witnesses = set() if witnesses == "-" else set(map(int, witnesses.split(",")))
                base = (directory / f"{name}-{route}.cnf").read_text()
                start = solver_seconds
                ns = buckets(base, delta)
                eight_s = solver_seconds-start
                assert ns == expected, (name, route, ns, expected)
                target = symmetric(ns)
                start = solver_seconds
                assert four_counts(base, delta) == target
                four_s = solver_seconds-start
                start = solver_seconds
                assert two_weighted(base, delta) == target
                two_s = solver_seconds-start
                coefficients = signed(ns)
                start = solver_seconds
                normalized = tuple(x * 2**scale for x in coefficients)
                if route == "direct":
                    direct[name] = normalized
                else:
                    assert direct[name] == normalized
                witness = None
                if any(coefficients):
                    prefix = []
                    witness = 0
                    for i in range(n):
                        l = i + 2
                        prefix.append(-l)
                        if not any(two_weighted(base, delta, prefix)):
                            prefix[-1] = l
                            witness |= 1 << i
                    fixed = two_weighted(base, delta, prefix)
                    assert any(fixed)
                    assert fixed == symmetric(buckets(base, delta, prefix))
                    assert witness in witnesses
                else:
                    assert not witnesses
                row = dict(case=name, route=route, counts=ns,
                           verdict="PROVED" if witness is None else "REFUTED",
                           witness=witness, coefficients=target,
                           eight_root_s=round(eight_s,6), four_root_s=round(four_s,6),
                           two_root_s=round(two_s,6),
                           witness_s=round(solver_seconds-start,6))
                records.append(row)
                print("HOARE_GANAK_EXACT " + json.dumps(row), flush=True)
        assert len(records) == 14 and len(direct) == 7
        print(f"HOARE_GANAK_PASS variants={len(records)} calls={calls} solver_wall_s={solver_seconds:.6f} modes=0,1 prob=0 symmetry=true signed=true")
        # Scale pilot uses analytic raw coefficients, independently checked
        # at small sizes in Rust. Same external solver; no DPLL expansion.
        # Root-only two/four query comparison; negative known input is
        # reconfirmed, not claimed to be a newly extracted witness.
        scaled = []
        with (directory / "scaled.tsv").open() as fh:
            for name, route, n, h, scale, delta, expected, witness, vars_, clauses, encoding_us, status, query_witness, prep_us, phase_terms in csv.reader(fh, delimiter="\t"):
                n,h,scale,vars_,clauses,encoding_us = map(int,(n,h,scale,vars_,clauses,encoding_us))
                delta = list(map(int,delta.split(",")))
                expected = tuple(map(int,expected.split(",")))
                row = dict(case=name,route=route,n=n,h=h,vars=vars_,clauses=clauses,
                           encoding_us=encoding_us,prep_us=int(prep_us),phase_terms=int(phase_terms),expected_raw=expected,known_witness=witness,query_witness=query_witness,
                           status=status,two_status="NOT_RUN",four_status="NOT_RUN",witness_status="NOT_REQUIRED" if witness=="-" else "NOT_RUN")
                if status=="READY":
                    base=(directory/f"scale-{name}-{route}.cnf").read_text()
                    for method,fn in [("two",two_weighted),("four",four_counts)]:
                        start=time.monotonic()
                        try:
                            coeff=fn(base,delta)
                            assert tuple(v*Fraction(2)**scale for v in coeff)==expected,(name,route,method,coeff,expected)
                            row[method+"_status"]="PASS"
                            row[method+"_coeff"]=coeff
                        except (subprocess.TimeoutExpired,TimeoutError):
                            row[method+"_status"]="UNKNOWN_TIMEOUT"
                        row[method+"_root_s"]=round(time.monotonic()-start,6)
                    if witness!="-" and row["two_status"]=="PASS":
                        x=int(query_witness)
                        prefix=[i+2 if x>>i&1 else -(i+2) for i in range(n)]
                        try:
                            assert any(two_weighted(base,delta,prefix))
                            row["witness_status"]="PASS"
                        except (subprocess.TimeoutExpired,TimeoutError):
                            row["witness_status"]="UNKNOWN_TIMEOUT"
                    row["status"]="PASS" if row["two_status"]==row["four_status"]=="PASS" and row["witness_status"] in ("PASS","NOT_REQUIRED") else "UNKNOWN_RESOURCE"
                scaled.append(row)
                print("HOARE_GANAK_SCALE "+json.dumps(row),flush=True)
        assert len(scaled)==96
        ok=sum(r["status"]=="PASS" for r in scaled)
        print(f"HOARE_GANAK_SCALE_SUMMARY variants={len(scaled)} pass={ok} unknown={len(scaled)-ok} calls={calls} solver_wall_s={solver_seconds:.6f}")
        run_hybrid(directory,tmp,deadline,two_weighted,pathlib.Path(sys.argv[3]).resolve())
        # Separate bounded qualification budget; preserve all legacy regressions.
        deadline = time.monotonic() + 45
        ganak_rows=run_pure_wmc(directory,two_weighted,deadline)
        paired=[]
        for g,a in zip(gpmc_rows,ganak_rows,strict=True):
            assert g['case']==a['case']
            if g['verdict']!='UNKNOWN' and a['verdict']!='UNKNOWN':
                assert g['coeff']==a['coeff'] and g['verdict']==a['verdict']
                paired.append(dict(case=g['case'],gpmc_root_s=g['root_s'],ganak_root_s=a['root_s']))
        print('HOARE_WMC_MATCHED_BACKENDS '+json.dumps(dict(paired=len(paired),rows=paired)),flush=True)



def positive_surd(coeff):
    """Sign of a+b sqrt(2) using integers only."""
    a,b = coeff
    if a == b == 0:
        return False
    if a >= 0 and b >= 0:
        return True
    if a <= 0 and b <= 0:
        return False
    return a*a > 2*b*b if a > 0 else 2*b*b > a*a


def pure_wmc_decision(base, delta, n, solve, deadline, witness_seconds=2.0):
    """Root decision independent of optional counterexample extraction.

    A positive exact root is REFUTED even if witness reconstruction runs
    out of budget. Invalid solver output or a negative squared norm is
    an integrity failure, not UNKNOWN_RESOURCE.
    """
    row = dict(verdict="UNKNOWN", reason="ROOT_RESOURCE", coeff=None,
               witness=None, witness_status="NOT_RUN", root_queries=0,
               witness_queries=0, root_s=0.0, witness_s=0.0)
    start=time.monotonic()
    def query(prefix, end, field):
        if time.monotonic() >= end:
            raise TimeoutError("pure WMC stage budget")
        row[field] += 1  # two-signed-count batches attempted
        v=tuple(solve(base,delta,prefix,end))
        if len(v)!=2 or any(type(c) is not int for c in v):
            raise ValueError("invalid exact coefficient pair")
        if any(v) and not positive_surd(v):
            raise ValueError("negative squared leakage")
        return v
    try:
        coeff=query([], deadline, "root_queries")
    except (TimeoutError,subprocess.TimeoutExpired):
        row["root_s"]=time.monotonic()-start
        return row
    row["root_s"]=time.monotonic()-start
    row["coeff"]=coeff
    row["verdict"]="REFUTED" if any(coeff) else "PROVED"
    row["reason"]="EXACT_ROOT"
    row["witness_status"]="NOT_REQUIRED" if not any(coeff) else "UNKNOWN_RESOURCE"
    if not any(coeff):
        return row
    start=time.monotonic()
    end=min(deadline,start+witness_seconds)
    try:
        prefix=[];x=0
        for i in range(n):
            l=i+2;prefix.append(-l)
            if not any(query(prefix,end,"witness_queries")):
                prefix[-1]=l;x|=1<<i
        fixed=query(prefix,end,"witness_queries")
        if not any(fixed):
            raise ValueError("conditioned witness has zero leakage")
        row["witness"]=x
        row["witness_status"]="VERIFIED"
        row["witness_coeff"]=fixed
    except (TimeoutError,subprocess.TimeoutExpired):
        pass
    row["witness_s"]=time.monotonic()-start
    return row


def pure_wmc_contract_tests():
    assert positive_surd((2,-1)) and positive_surd((-1,1))
    assert not positive_surd((1,-1)) and not positive_surd((0,0))
    # Root proof, root resource, witness resource and verified witness.
    def fail(*args):
        raise TimeoutError("synthetic budget")
    end=time.monotonic()+10
    z=pure_wmc_decision("",[],1,lambda *a:(0,0),end)
    assert z["verdict"]=="PROVED" and z["witness_queries"]==0
    z=pure_wmc_decision("",[],1,fail,end)
    assert z["verdict"]=="UNKNOWN" and z["coeff"] is None
    z=pure_wmc_decision("",[],1,lambda *a:(2,-1),end,0)
    assert z["verdict"]=="REFUTED" and z["witness"] is None and z["witness_status"]=="UNKNOWN_RESOURCE"
    def cond(base,delta,prefix,end):
        return (0,0) if -2 in prefix else (2,-1)
    z=pure_wmc_decision("",[],1,cond,end)
    assert z["verdict"]=="REFUTED" and z["witness"]==1 and z["witness_status"]=="VERIFIED"
    try:
        pure_wmc_decision("",[],1,lambda *a:(1,-1),end)
    except ValueError:
        pass
    else:
        raise AssertionError("negative leakage accepted")


def run_pure_wmc(directory, two_weighted, deadline, backend="ganak-signed-rational"):
    """Standalone direct path; never consumes RR or SAT plans."""
    pure_wmc_contract_tests()
    cases=[]
    with (directory/"hybrid.tsv").open() as f:
        for name,n,nq,delta,expected,witnesses,build_us,direct_us,plan_us in csv.reader(f,delimiter="\t"):
            cases.append((name,int(n),None,delta,expected,witnesses,int(build_us),
                          int(direct_us),"READY",directory/f"hybrid-{name}-wmc.cnf"))
    with (directory/"pure-rare.tsv").open() as f:
        for name,n,h,delta,expected,witnesses,build_us,encoding_us,status in csv.reader(f,delimiter="\t"):
            cases.append((name,int(n),int(h),delta,expected,witnesses,int(build_us),
                          int(encoding_us),status,directory/f"pure-{name}.cnf"))
    rows=[]
    for name,n,h,delta,expected,witnesses,build_us,encoding_us,status,file in cases:
        # Same per-case cap for all matched and rare cases; no hidden
        # fallback, and no known witness supplied to the solver.
        end=min(deadline,time.monotonic()+5.0)
        if status!="READY":
            row=dict(verdict="UNKNOWN",reason=status,coeff=None,witness=None,
                     witness_status="NOT_RUN",root_queries=0,witness_queries=0,root_s=0.0,witness_s=0.0)
        else:
            row=pure_wmc_decision(file.read_text(),list(map(int,delta.split(","))),
                                  n,two_weighted,end)
        # Oracle access only after the route is complete.
        target=tuple(map(int,expected.split(",")))
        legal_witnesses=set() if witnesses=="-" else set(map(int,witnesses.split(",")))
        truth="REFUTED" if any(target) else "PROVED"
        if row["verdict"]!="UNKNOWN":
            assert row["verdict"]==truth and row["coeff"]==target,(name,row,target)
        if row["witness_status"]=="VERIFIED":
            assert row["witness"] in legal_witnesses
        if name.startswith("rare-") and row["witness_status"]=="VERIFIED":
            assert row["witness_coeff"]==target
        row.update(backend=backend,case=name,n=n,h=h,build_us=build_us,encoding_us=encoding_us,
                   expected_raw=target,rr_calls=0,sat_queries=0,
                   decision_total_s=build_us/1e6+encoding_us/1e6+row["root_s"])
        rows.append(row)
        print("HOARE_PURE_WMC "+json.dumps(row),flush=True)
    assert len(rows)==26
    def summary(rs):
        return dict(cases=len(rs),decided=sum(r["verdict"]!="UNKNOWN" for r in rs),
                    proved=sum(r["verdict"]=="PROVED" for r in rs),
                    refuted=sum(r["verdict"]=="REFUTED" for r in rs),
                    witnesses=sum(r["witness_status"]=="VERIFIED" for r in rs),
                    witness_unknown=sum(r["witness_status"]=="UNKNOWN_RESOURCE" for r in rs),
                    unknown=sum(r["verdict"]=="UNKNOWN" for r in rs),
                    root_batches=sum(r["root_queries"] for r in rs),
                    witness_batches=sum(r["witness_queries"] for r in rs))
    print("HOARE_PURE_WMC_SUMMARY "+json.dumps(dict(backend=backend,matched=summary(rows[:16]),rare=summary(rows[16:]),
          rr_calls=0,sat_queries=0)),flush=True)
    return rows



def parse_gpmc_integer(stdout, mode, bound):
    """GPMC mpz output (not MPFR). All packed weights are positive."""
    lines=stdout.splitlines()
    def one(prefix):
        values=[l[len(prefix):].strip() for l in lines if l.startswith(prefix)]
        if len(values)!=1:
            raise ValueError("GPMC missing or conflicting "+prefix)
        return values[0]
    if any(l.startswith("c s approx") for l in lines):
        raise ValueError("GPMC approximate count")
    if one("c s type ")!=mode:
        raise ValueError("GPMC wrong count mode")
    raw=one("c s exact arb int ")
    if not re.fullmatch(r"[0-9]+",raw):
        raise ValueError("GPMC nonnegative integer expected")
    value=int(raw)
    if value>bound or one("s ")!=("SATISFIABLE" if value else "UNSATISFIABLE"):
        raise ValueError("GPMC count/domain/status mismatch")
    return value


def unpack_pair(value, radix):
    lo,hi=value%radix,value//radix
    if hi>=radix:
        raise ValueError("GPMC packed digit overflow")
    return lo-hi



def run_amplitude_factor_pilot(directory, exe, tmp, repeat_round=None, multi=False):
    """Bounded, exact natural-integer class weights; no float fallback."""
    assert not (multi and repeat_round is not None)
    manifest = list(csv.reader((directory/("native-multi-factor.tsv" if multi else "native-factor.tsv")).open(), delimiter="\t"))
    if multi:
        assert len(manifest)==16 and len({r[0] for r in manifest})==16
    if repeat_round is not None:
        # Four-period balanced crossover; same eight source-only queries in
        # each period. Preserve the 10 s cap and all exact bucket checks.
        order = ((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1))
        assert 0 <= repeat_round < len(order)
        routes = (("flat","1"),("flat","2"),("factor","1"),("factor","2"))
        source = {(int(r[1]),r[3],r[4]):r for r in manifest if r[2]=="source"}
        assert len(source)==8, "incomplete source-only repeat cohort"
        assert sum(r[2]=="source" for r in manifest)==8
        sizes = (3,4) if repeat_round%2==0 else (4,3)
        manifest = [source[(k,*routes[j])] for k in sizes for j in order[repeat_round]]
        print("HOARE_FACTOR_REPEAT_PLAN "+json.dumps(dict(
            round=repeat_round, order=[r[0] for r in manifest],
            solver_sha256=hashlib.sha256(pathlib.Path(exe).read_bytes()).hexdigest(),
            cap_s=10)),flush=True)
    rows = {}
    for r in manifest:
        (name,k,variant,mode,copies,primary,vs,cs,encode_ns,prep_ns,
         classes,ep,em,norm,residual,witness)=r
        k,copies,primary,vs,cs,encode_ns,prep_ns,ep,em,norm,residual=map(
            int,(k,copies,primary,vs,cs,encode_ns,prep_ns,ep,em,norm,residual))
        weights = [(int(l),int(w)) for l,w in (pair.split(":") for pair in classes.split(","))]
        assert len(weights) == (4 if copies==1 else 2)
        assert len({l for l,w in weights})==len(weights)
        assert all(0<abs(l)<=vs and w for l,w in weights)
        bound=(1<<primary)*max(abs(w) for l,w in weights)
        radix=bound+1
        # Complementary self classes share a variable; set explicit weights
        # first, and only then fill unspecified polarities with one.
        natural={l:abs(w)*(radix if w<0 else 1) for l,w in weights}
        for l,w in weights:
            natural.setdefault(-l,1)
        base=(directory/f"factor-{name}.cnf").read_text()
        header,*clauses=base.splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        assert 0<=primary<=32 and vs<=10000 and cs<=40000
        query=pathlib.Path(tmp)/"factor-pilot.cnf"
        body="".join(f"c p weight {l} {w} 0\n" for l,w in sorted(natural.items()))
        query.write_text("c t wmc\n"+header+"\n"+body+"\n".join(clauses)+"\n")
        metrics=[]
        row=dict(case=name,k=k,variant=variant,mode=mode,copies=copies,
                 primary=primary,vars=vs,clauses=cs,encode_ns=encode_ns,
                 prep_ns=prep_ns,query_sha256=hashlib.sha256(query.read_bytes()).hexdigest(),
                 status="UNKNOWN",metrics=metrics)
        try:
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(query)],10,
                             pathlib.Path(tmp)/"factor-time.tsv",metrics)
            value=parse_gpmc_integer(out,"wmc",bound*(radix+1))
            plus,minus=value%radix,value//radix
            assert plus+minus<=bound
            assert (plus,minus)==(ep,em),(name,plus,minus,ep,em)
            score=plus-minus
            if copies==2:
                assert score==norm
            else:
                actual=2*(norm-score)
                assert actual>=0 and actual==residual
                row.update(verdict="PROVED" if actual==0 else "REFUTED", residual=actual,
                           oracle_output_witness=None if witness=="-" else (int(witness)&255 if multi else int(witness)))
                if multi:
                    row["oracle_input_witness"]=None if witness=="-" else int(witness)>>8
            row.update(status="EXACT",plus=plus,minus=minus,score=score)
        except (TimeoutError,subprocess.TimeoutExpired):
            row["status"]="TIMEOUT"
        except SolverSignalKilled:
            row["status"]="UNATTRIBUTED_SIGNAL_KILL"
        row["target_norm"]=norm
        rows[(k,variant,mode,copies)]=row
        if repeat_round is None:
            print(("HOARE_MULTI_GPMC " if multi else "HOARE_FACTOR_GPMC ")+json.dumps(row),flush=True)
        else:
            row["round"]=repeat_round
            print("HOARE_FACTOR_REPEAT "+json.dumps(row),flush=True)
    matched=0
    for k in ((3,) if multi else (3,4)):
        for variant in (("source","Z-last","X-scratch","Z-mark0") if multi else ("source","Z-last","X-scratch")):
            for mode in ("flat","factor"):
                a=rows.get((k,variant,mode,1));b=rows.get((k,variant,mode,2))
                if a and b and a["status"]==b["status"]=="EXACT":
                    assert a["target_norm"]==b["target_norm"]
                    assert a["residual"]==b["score"]-2*a["score"]+a["target_norm"]
                    matched+=1
    if repeat_round is None:
        print(("HOARE_MULTI_GPMC_SUMMARY " if multi else "HOARE_FACTOR_GPMC_SUMMARY ")+json.dumps(dict(expected=16 if multi else 24,exported=len(rows),
              exact=sum(r["status"]=="EXACT" for r in rows.values()),matched=matched)),flush=True)
    else:
        print("HOARE_FACTOR_REPEAT_SUMMARY "+json.dumps(dict(round=repeat_round,
              expected=8,exported=len(rows),exact=sum(r["status"]=="EXACT" for r in rows.values()),
              matched=matched)),flush=True)



def witness_target(x,z):
    if z&7!=x or z>>6!=2:
        return 0
    return 11 if (z>>3)&7==x else -1


def witness_prefix_search(query):
    """Query returns exact signed buckets or raises a resource exception.
    Input-prefix norm uses certified full columns; output prefix never does.
    No oracle or expected witness is consulted here.
    """
    calls=0
    def signed(kind,xm,xv,zm,zv):
        nonlocal calls
        calls+=1
        p,m=query(kind,xm,xv,zm,zv)
        assert p>=0 and m>=0
        return p-m
    def norm(xm,xv,zm,zv):
        # Only the declared target support, not circuit amplitudes.
        return sum(witness_target(x,z)**2 for x in range(8) if x&xm==xv
                   for z in range(256) if z&zm==zv)
    def residual(xm,xv,zm,zv):
        t=norm(xm,xv,zm,zv)
        s=(8>>xm.bit_count())*128 if zm==0 else signed("self",xm,xv,zm,zv)
        c=signed("cross",xm,xv,zm,zv)
        w=s-2*c+t
        assert s>=0 and w>=0
        return w
    root=None
    trace=[]
    try:
        root=residual(0,0,0,0)
        if root==0:
            return dict(verdict="PROVED",root=0,witness_status="NOT_REQUIRED",calls=calls,trace=trace)
        xm=xv=zm=zv=0
        w=root
        for i in range(3):
            bit=1<<i
            left=residual(xm|bit,xv,0,0)
            assert 0<=left<=w
            parent=w
            if left:
                w=left
            else:
                xv|=bit
            xm|=bit
            trace.append(dict(axis="x",bit=i,left=left,parent=parent,kept=w,value=xv))
        for i in reversed(range(8)):
            bit=1<<i
            left=residual(xm,xv,zm|bit,zv)
            assert 0<=left<=w
            parent=w
            if left:
                w=left
            else:
                zv|=bit
            zm|=bit
            trace.append(dict(axis="z",bit=i,left=left,parent=parent,kept=w,value=zv))
        a=signed("amp",7,xv,255,zv)
        t=witness_target(xv,zv)
        assert w>0 and (a-t)**2==w
        return dict(verdict="REFUTED",root=root,witness_status="VERIFIED",calls=calls,
                    x=xv,z=zv,amplitude=a,target=t,residual=w,trace=trace)
    except (TimeoutError,subprocess.TimeoutExpired,SolverSignalKilled):
        return dict(verdict="REFUTED" if root is not None and root>0 else "UNKNOWN",
                    root=root,witness_status="UNKNOWN",calls=calls,trace=trace)


def run_multi_witness_pilot(directory,exe,tmp):
    for variant in ("source","Z-last","X-scratch","Z-mark0"):
        records={}
        with (directory/f"witness-{variant}.tsv").open() as f:
            for kind,name,primary,vs,cs,classes,roots in csv.reader(f,delimiter="\t"):
                primary,vs,cs=map(int,(primary,vs,cs))
                assert kind not in records and kind in ("cross","self","amp")
                assert primary==(17 if kind=="self" else 10)
                assert 0<vs<=10000 and 0<cs<=40000
                weights=[(int(l),int(w)) for l,w in (s.split(":") for s in classes.split(","))]
                assert sorted(w for l,w in weights)==([-11,-1,1,11] if kind=="cross" else [-1,1])
                assert len({l for l,w in weights})==len(weights) and all(0<abs(l)<=vs for l,w in weights)
                roots=list(map(int,roots.split(",")))
                assert len(roots)==8 and all(0<abs(l)<=vs for l in roots)
                header,*clauses=(directory/f"{name}.cnf").read_text().splitlines()
                assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
                records[kind]=(primary,vs,clauses,weights,roots)
        assert set(records)=={"cross","self","amp"}
        history=[]
        start=time.monotonic()
        def query(kind,xm,xv,zm,zv):
            primary,vs,clauses,weights,roots=records[kind]
            assert 0<=xm<=7 and xv&~xm==0 and 0<=zm<=255 and zv&~zm==0
            units=[(2+i) if xv>>i&1 else -(2+i) for i in range(3) if xm>>i&1]
            units.extend(l if zv>>i&1 else -l for i,l in enumerate(roots) if zm>>i&1)
            bound=(1<<primary)*max(abs(w) for l,w in weights)
            radix=bound+1
            natural={l:abs(w)*(radix if w<0 else 1) for l,w in weights}
            for l,w in weights:natural.setdefault(-l,1)
            text=f"c t wmc\np cnf {vs} {len(clauses)+len(units)}\n"
            text+="".join(f"c p weight {l} {w} 0\n" for l,w in sorted(natural.items()))
            text+="\n".join(clauses)+"\n"+"".join(f"{l} 0\n" for l in units)
            path=pathlib.Path(tmp)/"witness-pilot.cnf"
            path.write_text(text)
            row=dict(kind=kind,xm=xm,xv=xv,zm=zm,zv=zv,
                     sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=[])
            history.append(row)
            remaining=60-(time.monotonic()-start)
            if remaining<=0:
                raise TimeoutError("witness total scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],min(5,remaining),
                             pathlib.Path(tmp)/"witness-time.tsv",row["metrics"])
            value=parse_gpmc_integer(out,"wmc",bound*(radix+1))
            p,m=value%radix,value//radix
            assert p+m<=bound
            row.update(plus=p,minus=m)
            return p,m
        result=witness_prefix_search(query)
        # Only after search: compare all completed queries against actual
        # path histograms, and exact returned amplitude against source fixture.
        hist=[tuple(map(int,l.split("\t"))) for l in (directory/f"witness-{variant}-oracle.tsv").read_text().splitlines()]
        assert len(hist)==2048
        checked=0
        for q in history:
            if "plus" not in q:continue
            p=m=0
            for x in range(8):
                if x&q["xm"]!=q["xv"]:continue
                for z in range(256):
                    if z&q["zm"]!=q["zv"]:continue
                    a,b=hist[256*x+z]
                    t=witness_target(x,z)
                    if q["kind"]=="self":p+=a*a+b*b;m+=2*a*b
                    elif q["kind"]=="amp":p+=a;m+=b
                    elif t>=0:p+=a*t;m+=b*t
                    else:p-=b*t;m-=a*t
            assert (p,m)==(q["plus"],q["minus"])
            checked+=1
        expected={"source":0,"Z-last":4096,"X-scratch":2048,"Z-mark0":2048}[variant]
        if result["root"] is not None:assert result["root"]==expected
        if result["witness_status"]=="VERIFIED":
            x,z=result["x"],result["z"]
            a,b=hist[256*x+z]
            assert a-b==result["amplitude"] and (a-b-witness_target(x,z))**2==result["residual"]>0
        result.update(variant=variant,checked=checked,query_records=history)
        print("HOARE_SOLVER_WITNESS "+json.dumps(result),flush=True)

        # Replay exact completed query receipts, injecting a timeout at every
        # call boundary. This tests verdict/witness separation, not OS killing.
        if checked==result["calls"] and result["witness_status"] in ("VERIFIED","NOT_REQUIRED"):
            for stop in range(len(history)):
                at=0
                def replay(kind,xm,xv,zm,zv):
                    nonlocal at
                    q=history[at]
                    assert (kind,xm,xv,zm,zv)==tuple(q[k] for k in ("kind","xm","xv","zm","zv"))
                    at+=1
                    if at==stop+1:
                        raise TimeoutError("injected query timeout")
                    return q["plus"],q["minus"]
                failure=witness_prefix_search(replay)
                assert failure["calls"]==stop+1 and at==stop+1
                assert failure["witness_status"]=="UNKNOWN"
                assert failure["verdict"]==("UNKNOWN" if stop==0 else "REFUTED")
                assert failure["root"]==(None if stop==0 else result["root"])
                assert "x" not in failure and "z" not in failure
            print("HOARE_WITNESS_TIMEOUT_CONTROL "+json.dumps(dict(variant=variant,checks=len(history))),flush=True)


def run_qft_complex_pilot(directory,exe,tmp):
    """Generated QFT specification: exact trace coefficient norm and packed witness."""
    for n in (3,5):
        N=1<<n
        D=1<<max(3,n)
        M=D//2
        h=n+2
        for variant in ("source","Z","T","X"):
            records={}
            with (directory/f"qftcomplex-{n}-{variant}.tsv").open() as f:
                for mode,kind,name,primary,vs,cs,classes,roots in csv.reader(f,delimiter="\t"):
                    primary,vs,cs=map(int,(primary,vs,cs))
                    assert (mode,kind) not in records and mode in ("heap","factor") and kind in ("cross","self","amp","amp-bits")
                    assert primary==n+h*(2 if kind=="self" else 1) and 0<vs<=10000 and 0<cs<=40000
                    classes=list(map(int,classes.split(",")))
                    roots=list(map(int,roots.split(",")))
                    assert len(classes)==(D if kind=="amp" else D.bit_length()-1 if kind=="amp-bits" else 2) and len(set(classes))==len(classes)
                    assert all(0<l<=vs for l in classes) and len(roots)==n and all(0<abs(l)<=vs for l in roots)
                    header,*clauses=(directory/f"{name}.cnf").read_text().splitlines()
                    assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
                    records[mode,kind]=(primary,vs,clauses,classes,roots)
            assert set(records)=={("heap","cross"),("heap","self"),("factor","cross"),("factor","self"),("factor","amp"),("factor","amp-bits")}
            history=[]
            start=time.monotonic()
            def query(mode,kind,xm=0,xv=0,zm=0,zv=0):
                primary,vs,clauses,classes,roots=records[mode,kind]
                assert 0<=xm<N and xv&~xm==0 and 0<=zm<N and zv&~zm==0
                units=[(2+i) if xv>>i&1 else -(2+i) for i in range(n) if xm>>i&1]
                units.extend(l if zv>>i&1 else -l for i,l in enumerate(roots) if zm>>i&1)
                bound=1<<primary
                B=bound+1
                natural={l:B**(1<<j if kind=="amp-bits" else j) for j,l in enumerate(classes)}
                for l in classes:natural[-l]=1
                body=f"c t wmc\np cnf {vs} {len(clauses)+len(units)}\n"
                body+="".join(f"c p weight {l} {w} 0\n" for l,w in sorted(natural.items()))
                body+="\n".join(clauses)+"\n"+"".join(f"{l} 0\n" for l in units)
                path=pathlib.Path(tmp)/"qft-complex.cnf"
                path.write_text(body)
                row=dict(mode=mode,kind=kind,xm=xm,xv=xv,zm=zm,zv=zv,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=[])
                history.append(row)
                remaining=90-(time.monotonic()-start)
                if remaining<=0:raise TimeoutError("Fourier scheduling deadline")
                out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],min(5,remaining),
                                 pathlib.Path(tmp)/"qft-complex-time.tsv",row["metrics"])
                digit_count=D if kind=="amp-bits" else len(classes)
                value=parse_gpmc_integer(out,"wmc",B**digit_count-1)
                digits=[]
                packed=value
                for _ in range(digit_count):digits.append(packed%B);packed//=B
                assert not packed and sum(digits)<=bound
                row.update(digits=digits,packed_bits=value.bit_length())
                return digits
            norm=4*N*N
            root=None
            result=dict(verdict="UNKNOWN",witness_status="UNKNOWN")
            pack_pairs=0
            try:
                for mode in ("heap","factor"):
                    a,b=query(mode,"cross")
                    c=2*(a-b)
                    a,b=query(mode,"self")
                    assert a-b==norm
                    w=2*(norm-c)
                    assert w>=0
                    if root is None:root=w
                    else:assert root==w
                result.update(root=root,verdict="PROVED" if root==0 else "REFUTED")
                if root==0:
                    result["witness_status"]="NOT_REQUIRED"
                    for x,z in ((0,0),(N-1,N-1)):
                        one=query("factor","amp",N-1,x,N-1,z)
                        bits=query("factor","amp-bits",N-1,x,N-1,z)
                        assert one==bits
                        pack_pairs+=1
                else:
                    w=root
                    xm=xv=zm=zv=0
                    def restricted(xm,xv,zm,zv):
                        T=4*(N>>xm.bit_count())*(N>>zm.bit_count())
                        if zm:
                            a,b=query("factor","self",xm,xv,zm,zv)
                            S=a-b
                        else:S=4*(N>>xm.bit_count())*N
                        a,b=query("factor","cross",xm,xv,zm,zv)
                        W=S-4*(a-b)+T
                        assert S>=0 and W>=0
                        return W
                    for i in range(n):
                        bit=1<<i
                        left=restricted(xm|bit,xv,0,0)
                        assert left<=w
                        if left:w=left
                        else:xv|=bit
                        xm|=bit
                    for i in reversed(range(n)):
                        bit=1<<i
                        left=restricted(xm,xv,zm|bit,zv)
                        assert left<=w
                        if left:w=left
                        else:zv|=bit
                        zm|=bit
                    digits=query("factor","amp",N-1,xv,N-1,zv)
                    a=[digits[j]-digits[j+M] for j in range(M)]
                    t=[0]*M
                    e=(D//N)*xv*zv%D
                    t[e%M]=2 if e<M else -2
                    assert sum((u-v)**2 for u,v in zip(a,t))==w>0
                    result.update(witness_status="VERIFIED",x=xv,z=zv,amplitude=a,target=t,residual=w)
                    compact_digits=query("factor","amp-bits",N-1,xv,N-1,zv)
                    assert digits==compact_digits
                    pack_pairs+=1
            except (TimeoutError,subprocess.TimeoutExpired,SolverSignalKilled):
                if root is not None:
                    result.update(root=root,verdict="REFUTED" if root else "PROVED")
                    if root==0:result["witness_status"]="NOT_REQUIRED"
            # No independent circuit histogram loaded until all solver decisions finish.
            hist=[list(map(int,l.split("\t"))) for l in (directory/f"qftcomplex-{n}-{variant}-oracle.tsv").read_text().splitlines()]
            assert len(hist)==N*N and all(len(a)==D for a in hist)
            checked=0
            for q in history:
                if "digits" not in q:continue
                counts=[0]*(D if q["kind"] in ("amp","amp-bits") else 2)
                for x in range(N):
                    if x&q["xm"]!=q["xv"]:continue
                    for z in range(N):
                        if z&q["zm"]!=q["zv"]:continue
                        a=hist[x*N+z]
                        e=(D//N)*x*z%D
                        if q["kind"]=="cross":
                            counts[0]+=a[e];counts[1]+=a[(e+M)%D]
                        elif q["kind"]=="self":
                            counts[0]+=sum(v*v for v in a)
                            counts[1]+=sum(v*a[(j+M)%D] for j,v in enumerate(a))
                        else:
                            for j,v in enumerate(a):counts[j]+=v
                assert counts==q["digits"]
                checked+=1
            expected=0 if variant=="source" else norm if variant=="T" else 2*norm
            if root is not None:assert root==expected
            result.update(n=n,d=D,variant=variant,checked=checked,calls=len(history),pack_pairs=pack_pairs,query_records=history)
            print("HOARE_QFT_COMPLEX_GPMC "+json.dumps(result),flush=True)



def rus_mul(a,b):
    r=[0]*4
    for i,u in enumerate(a):
        for j,v in enumerate(b):
            r[(i+j)%4]+=u*v*(-1 if i+j>=4 else 1)
    return r


def rus_conj(a):
    return [a[0],-a[3],-a[2],-a[1]]



def rus_gram_real_sign(a):
    assert a==rus_conj(a)
    x,y=a[:2]
    if x==0:return (y>0)-(y<0)
    if y==0 or (x>0)==(y>0):return (x>0)-(x<0)
    d=x*x-2*y*y
    if d==0:return 0
    return ((x>0)-(x<0)) if d>0 else ((y>0)-(y<0))




def cubic_edges(n):
    """Stable generated scalar benchmarks, independent of platform RNG."""
    state=0x43637a21+n
    edges=[];seen=set()
    for _ in range(10000):
        a=[]
        for j in range(3):
            state=(1664525*state+1013904223)&0xffffffff
            a.append((state>>8)%n)
        e=tuple(sorted(set(a)))
        if len(e)==3 and e not in seen:
            seen.add(e);edges.append(e)
        if len(edges)==3*n:return edges
    raise AssertionError("cubic generator cap")


def cubic_cnf(n,edges,alternate=False):
    """Same scalar polynomial, two distinct full-equivalence encodings.

    Primary z_i, true constant1, fresh weighted phase aliases. No source
    PathSum or unverified quantum norm is assumed by this scalar pilot.
    """
    nv=n+1;clauses=[[1]];cache={}
    def fresh():
        nonlocal nv
        nv+=1
        return nv
    def gate(op,a,b):
        if op=="and":
            if a==-1 or b==-1 or a==-b:return -1
            if a==1:return b
            if b==1 or a==b:return a
        else:
            if a==-1:return b
            if b==-1:return a
            if a==1:return -b
            if b==1:return -a
            if a==b:return -1
            if a==-b:return 1
            if (a<0)!=(b<0):return -gate(op,abs(a),abs(b))
            a,b=abs(a),abs(b)
        a,b=sorted((a,b));key=(op,a,b)
        if key in cache:return cache[key]
        z=fresh();cache[key]=z
        if op=="and":clauses.extend(([-a,-b,z],[a,-z],[b,-z]))
        else:clauses.extend(([-a,-b,-z],[a,b,-z],[a,-b,z],[-a,b,z]))
        return z
    def relation(inputs,width,fn):
        # Truth-table transition with one implication per output bit for
        # every possible input row. Inconsistent constant rows are tautologies.
        out=[fresh() for _ in range(width)]
        for a in range(1<<len(inputs)):
            prefix=[-v if a>>i&1 else v for i,v in enumerate(inputs)]
            value=fn(a)
            for i,z in enumerate(out):
                clauses.append(prefix+[z if value>>i&1 else -z])
        return out
    p=[-1]*3
    for i in range(n):
        r=1+3*i%7;z=i+2
        if alternate:
            p=relation(p+[z],3,lambda a:((a&7)+r*(a>>3&1))%8)
        else:
            q=[];carry=-1
            for j in range(3):
                b=z if r>>j&1 else -1
                t=gate("xor",p[j],b);q.append(gate("xor",t,carry))
                if j<2:carry=gate("xor",gate("and",p[j],b),gate("and",t,carry))
            p=q
    for i,j,k in edges:
        if alternate:
            p[2]=relation([p[2],i+2,j+2,k+2],1,
                          lambda a:(a&1)^int(a>>1==7))[0]
        else:p[2]=gate("xor",p[2],gate("and",gate("and",i+2,j+2),k+2))
    aliases=[]
    for l in p:
        z=fresh();clauses.extend(([-z,l],[z,-l]));aliases.append(z)
    assert nv<=4096 and len(clauses)<=32768
    return nv,clauses,aliases


def cubic_up(n,nv,clauses,aliases,edges,x):
    a=[0]*(nv+1)
    for i in range(n):a[i+2]=1 if x>>i&1 else -1
    while True:
        changed=False
        for cl in clauses:
            free=0;last=0;ok=False
            for l in cl:
                v=a[abs(l)]*(1 if l>0 else -1)
                if v==1:ok=True;break
                if v==0:free+=1;last=l
            if ok:continue
            assert free,"unexpected conflict in cubic transition"
            if free==1:
                a[abs(last)]=1 if last>0 else -1;changed=True
        if not changed:break
    assert all(a[1:]),"nonunique or incomplete primary extension"
    e=sum((1+3*i%7) for i in range(n) if x>>i&1)
    e+=4*sum(all(x>>i&1 for i in edge) for edge in edges)
    d=sum((1<<j) for j,l in enumerate(aliases) if a[l]==1)
    assert d==e%8
    return d


def cubic_bitset(n,edges):
    """Independent bit-parallel exhaustive truth table, bounded at 24 bits.

    No CNF, solver or weighted formula. Partition assignments by number
    of selected weight-2 variables set, then popcount each phase class.
    """
    assert 3<=n<=24
    N=1<<n;mask=(1<<N)-1;zs=[]
    for i in range(n):
        if i<3:v=int.from_bytes(bytes(([0xaa,0xcc,0xf0][i],))*(N//8),"little")
        else:
            p=1<<(i-3)
            v=int.from_bytes((b"\x00"*p+b"\xff"*p)*(N//(16*p)),"little")
        zs.append(v)
    d=[0,0,0]
    for i,z in enumerate(zs):
        r=1+3*i%7;c=0
        for j in range(3):
            b=z if r>>j&1 else 0;x=d[j]^b
            carry=(d[j]&b)|(x&c);d[j]=x^c;c=carry
    for i,j,k in edges:d[2]^=zs[i]&zs[j]&zs[k]
    classes=[mask]
    for z in zs[::3]:
        new=[0]*(len(classes)+1)
        for i,a in enumerate(classes):
            new[i]|=a&(mask^z);new[i+1]|=a&z
        classes=new
    assert sum(v.bit_count() for v in classes)==N
    bins=[];weighted=[]
    for j in range(8):
        a=mask
        for k,v in enumerate(d):a&=v if j>>k&1 else mask^v
        bins.append(a.bit_count())
        weighted.append(sum((a&c).bit_count()*(1<<i) for i,c in enumerate(classes)))
    assert sum(bins)==N and sum(weighted)==3**len(zs[::3])*2**(n-len(zs[::3]))
    return bins,weighted


def run_weighted_cubic(exe,ganak,tmp,sizes=(14,18,24,32)):
    """Research-only condensed scalar fallback comparison.

    Separate exact solver status from independent admission. No quantum
    verdict, no claim of end-to-end speed, no unbounded count retry.
    """
    known={
        14:([2016,2024,2048,2072,2080,2072,2048,2024],
            [15484,15148,15556,15620,15620,15956,15548,15484]),
        18:([32768,32848,32800,32656,32768,32688,32736,32880],
            [372920,373960,373032,371920,373576,372536,373464,374576]),
        24:([2095936,2096704,2098496,2098368,2098368,2097600,2095808,2095936],
            [53705536,53770608,53799536,53789408,53789888,53724816,53695888,53706016]),
    }
    # Distinct exact positive-weight qualification of Ganak, including
    # an integer larger than 2^53. It was hash-qualified by main.
    qual=pathlib.Path(tmp)/"cubic-ganak-qualification.cnf"
    qual.write_text("c t wmc\np cnf 2 1\nc p weight 2 1152921504606846976 0\nc p weight -2 1 0\n1 0\n")
    qmetrics=[];ganak_ok=False
    try:
        out=profile_gpmc([str(ganak),"--mode","1","--prob","0",str(qual)],5,
                         pathlib.Path(tmp)/"cubic-time.tsv",qmetrics)
        assert parse_count(out,(1<<60)+1,weighted=True)==(1<<60)+1
        ganak_ok=True
    except (TimeoutError,subprocess.TimeoutExpired,SolverSignalKilled,subprocess.CalledProcessError,ValueError) as err:
        print("HOARE_CUBIC_GANAK_QUALIFICATION "+json.dumps(dict(status="UNAVAILABLE",reason=type(err).__name__,metrics=qmetrics)),flush=True)
    if ganak_ok:print("HOARE_CUBIC_GANAK_QUALIFICATION "+json.dumps(dict(status="PASS",metrics=qmetrics)),flush=True)
    deadline=time.monotonic()+100
    admitted=0;gexact=0;aexact=0;matches=0
    for n in sizes:
        edges=cubic_edges(n);oracle=None
        if n<=24:
            t=time.monotonic_ns();oracle=cubic_bitset(n,edges)
            assert oracle==known[n]
            print("HOARE_CUBIC_ORACLE "+json.dumps(dict(n=n,assignments=1<<n,bins=oracle,ns=time.monotonic_ns()-t)),flush=True)
        compiled=[]
        for alt in (False,True):
            t=time.monotonic_ns();nv,cs,dl=cubic_cnf(n,edges,alt)
            enc=time.monotonic_ns()-t
            state=0x43435a31;xs=[0,(1<<n)-1]
            for _ in range(254):
                state=(1664525*state+1013904223)&0xffffffff;xs.append(state&((1<<n)-1))
            covered={cubic_up(n,nv,cs,dl,edges,x) for x in xs}
            assert len(covered)==8
            if not alt:assert (nv,len(cs))=={14:(196,625),18:(259,829),24:(344,1103),32:(471,1513)}[n]
            compiled.append((nv,cs,dl,enc))
            print("HOARE_CUBIC_EXPORT "+json.dumps(dict(n=n,encoding="table" if alt else "gates",vars=nv,clauses=len(cs),checks=len(xs),phase_bins=len(covered),encode_ns=enc)),flush=True)
        for mode in (0,1):
            m=[2 if mode and i%3==0 else 1 for i in range(n)]
            total=1
            maxprod=1
            for w in m:total*=1+w;maxprod*=w
            B=(1<<n)*maxprod+1
            counts={}
            for alt,(nv,cs,dl,enc) in enumerate(compiled):
                backend="ganak" if alt else "gpmc"
                r=dict(n=n,mode="magnitude" if mode else "phase",backend=backend,
                       encoding="table" if alt else "gates",vars=nv,clauses=len(cs),encode_ns=enc,metrics=[],status="UNKNOWN")
                if alt and not ganak_ok:
                    r["status"]="BACKEND_UNAVAILABLE"
                    print("HOARE_CUBIC_COUNT "+json.dumps(r),flush=True);continue
                weights={i+2:w for i,w in enumerate(m) if w!=1}
                weights.update({l:B**(1<<i) for i,l in enumerate(dl)})
                weights.update({-l:1 for l in list(weights)})
                body="c t wmc\n"+f"p cnf {nv} {len(cs)}\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"".join(" ".join(map(str,c))+" 0\n" for c in cs)
                path=pathlib.Path(tmp)/"weighted-cubic.cnf";path.write_text(body)
                r["query_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
                try:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise TimeoutError("cubic scheduling deadline")
                    args=[str(ganak),"--mode","1","--prob","0"] if alt else [str(exe),"-mode=1","-natw"]
                    out=profile_gpmc(args+[str(path)],min(5,remaining),pathlib.Path(tmp)/"cubic-time.tsv",r["metrics"])
                    value=parse_count(out,B**8-1,weighted=True) if alt else parse_gpmc_integer(out,"wmc",B**8-1)
                    assert value>=0
                    bits=value.bit_length();bins=[]
                    for _ in range(8):bins.append(value%B);value//=B
                    assert value==0 and sum(bins)==total
                    if oracle is not None:assert bins==oracle[mode]
                    counts[backend]=bins
                    gexact+=int(not alt);aexact+=int(bool(alt))
                    r.update(status="EXACT",digits=bins,coeff=[bins[i]-bins[i+4] for i in range(4)],packed_bits=bits,oracle_checked=oracle is not None)
                except (TimeoutError,subprocess.TimeoutExpired):r["status"]="TIMEOUT"
                except SolverSignalKilled:r["status"]="UNATTRIBUTED_SIGNAL_KILL"
                except subprocess.CalledProcessError:r["status"]="SOLVER_ERROR"
                except ValueError as err:r.update(status="INVALID_SOLVER_OUTPUT",reason=str(err))
                print("HOARE_CUBIC_COUNT "+json.dumps(r),flush=True)
            paired=len(counts)==2
            if paired:
                assert counts["gpmc"]==counts["ganak"];matches+=1
            accepted="gpmc" in counts and (oracle is not None or paired)
            admitted+=int(accepted)
            print("HOARE_CUBIC_ADMISSION "+json.dumps(dict(n=n,mode="magnitude" if mode else "phase",
                  status="VERIFIED" if accepted else "UNKNOWN",independent_oracle=oracle is not None,paired=paired)),flush=True)
    print("HOARE_CUBIC_SUMMARY "+json.dumps(dict(expected=2*len(sizes),gpmc_exact=gexact,ganak_exact=aexact,paired=matches,admitted=admitted)),flush=True)


def run_rus_composite(directory,exe,tmp):
    """One source copy; source norm derived from local gate certificates,
    not from any global self query. Fixed all-success product scope only."""
    names=("Figure7","Figure8","Figure9","Figure10a","Figure10b","Figure10c")
    def inner(a,b):
        t=[rus_mul(rus_conj(x),y) for x,y in zip(a,b)]
        return [sum(v[j] for v in t) for j in range(4)]
    def prod(v):
        r=[1,0,0,0]
        for a in v:r=rus_mul(r,a)
        return r
    def align(a,s):
        for _ in range(s):a=rus_mul(a,[0,1,0,-1])
        return a
    cert_start=time.monotonic_ns()
    cert={}
    with (directory/"native-rus-composite-cert.tsv").open() as f:
        for name,h0,h,scale,branch,a,t in csv.reader(f,delimiter="\t"):
            h0,h,scale,branch=map(int,(h0,h,scale,branch))
            assert name in names and name not in cert and branch==1 and 0<=h<=h0<=17
            a=list(map(int,a.split(",")));t=list(map(int,t.split(",")))
            assert len(a)==len(t)==16
            a=[a[i:i+4] for i in range(0,16,4)];t=[t[i:i+4] for i in range(0,16,4)]
            p=inner(a[:2],a[:2]);assert p==inner(a[2:],a[2:]) and not any(inner(a[:2],a[2:]))
            assert rus_gram_real_sign(p)>0 and rus_gram_real_sign([(1<<h0)-p[0],-p[1],-p[2],-p[3]])>0
            q=inner(t,t);assert rus_gram_real_sign(q)>0
            cert[name]=dict(h0=h0,h=h,scale=scale,branch=branch,p=p,t=t,a=a,T=q)
    assert tuple(cert)==names
    print("HOARE_RUS_COMPOSITE_CERT_READ_VERIFY "+json.dumps(dict(ns=time.monotonic_ns()-cert_start)),flush=True)
    # Scope is constructed by the fixed source generator, not accepted from
    # an external certificate. Fail closed on altered branch/domain/order.
    def admit(scope,k,branch,domain,post):
        return k in (2,4,6) and tuple(scope)==names[:k] and branch==1 and domain=="full-disjoint-basis" and post in ("source","cz-chain")
    assert admit(names[:2],2,1,"full-disjoint-basis","cz-chain")
    assert not admit(names[:2],2,0,"full-disjoint-basis","source")
    assert not admit(names[:2],2,1,"partial","source")
    assert not admit((names[0],names[0]),2,1,"full-disjoint-basis","source")
    assert not admit(names[:2],2,1,"full-disjoint-basis","projector")
    print("HOARE_RUS_COMPOSITE_SCOPE "+json.dumps(dict(rejected_controls=4)),flush=True)
    with (directory/"native-rus-composite.tsv").open() as f:rows=list(csv.reader(f,delimiter="\t"))
    assert len(rows)==6 and len({r[0] for r in rows})==6
    start=time.monotonic();exact=0
    for name,k,mut,h,primary,vs,cs,B,ds,ms,ex,scope,enc,checks in rows:
        k,mut,h,primary,vs,cs,B,enc,checks=map(int,(k,mut,h,primary,vs,cs,B,enc,checks))
        assert mut in (0,1)
        scope=scope.split(",");assert admit(scope,k,1,"full-disjoint-basis","cz-chain" if mut else "source")
        b=[cert[n] for n in scope]
        assert h==sum(q["h"] for q in b) and primary==3*k+h<=63
        assert 0<vs<=4096 and 0<cs<=32768
        dl=list(map(int,ds.split(",")));mag=[tuple(map(int,s.split(":"))) for s in ms.split(",")]
        assert len(dl)==3 and all(0<=i<k and 1<=w<=5 for i,l,w in mag)
        import math
        assert B==(1<<primary)*math.prod(max(w for j,l,w in mag if i==j) for i in range(k))+1
        lits=dl+[l for i,l,w in mag];assert len(lits)==len(set(lits)) and all(0<l<=vs for l in lits)
        expected=list(map(int,ex.split(",")));assert len(expected)==8 and all(0<=v<B for v in expected)
        S=prod([[2*v for v in q["p"]] for q in b]);T=prod([q["T"] for q in b])
        # Independent exact reference contraction, using original local
        # gate amplitudes and literal target, not the encoded phase bins.
        contraction_start=time.monotonic_ns()
        w=[[inner([q["t"][z],q["t"][z+2]],[q["a"][z],q["a"][z+2]]) for z in range(2)] for q in b]
        v=w[0]
        for u in w[1:]:
            v=[rus_mul([a+c for a,c in zip(v[0],v[1])],u[0]),
               rus_mul([a-c if mut else a+c for a,c in zip(v[0],v[1])],u[1])]
        oracle=[a+c for a,c in zip(*v)]
        contraction_ns=time.monotonic_ns()-contraction_start
        weights={l:B**(1<<i) for i,l in enumerate(dl)}
        weights.update({l:w for i,l,w in mag});weights.update({-l:1 for l in lits})
        header,*clauses=(directory/f"{name}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        path=pathlib.Path(tmp)/"rus-composite.cnf"
        path.write_text("c t wmc\n"+header+"\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"\n".join(clauses)+"\n")
        r=dict(case=name,k=k,mutant=bool(mut),h=h,primary=primary,vars=vs,clauses=cs,encode_ns=enc,checks=checks,
               query_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=[],status="UNKNOWN",verdict="UNKNOWN",contraction_ns=contraction_ns)
        try:
            remaining=90-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError("composite scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],min(10,remaining),pathlib.Path(tmp)/"rus-composite-time.tsv",r["metrics"])
            value=parse_gpmc_integer(out,"wmc",B**8-1)
            bits=value.bit_length();digits=[]
            for _ in range(8):digits.append(value%B);value//=B
            assert value==0 and digits==expected
            C=align([digits[i]-digits[i+4] for i in range(4)],sum(q["scale"] for q in b))
            D=[u-v for u,v in zip(rus_mul(S,T),rus_mul(C,rus_conj(C)))]
            assert rus_gram_real_sign(D)>=0 and rus_gram_real_sign(S)>0 and rus_gram_real_sign(T)>0
            ray=not any(D)
            assert C==oracle and ray==(not bool(mut))
            r.update(status="EXACT",verdict="PROVED" if ray else "REFUTED",S=S,T=T,C=C,delta=D,packed_bits=bits,digits=digits)
            exact+=1
        except (TimeoutError,subprocess.TimeoutExpired):
            r["status"]="TIMEOUT"
        except SolverSignalKilled:
            r["status"]="UNATTRIBUTED_SIGNAL_KILL"
        print("HOARE_RUS_COMPOSITE_GPMC "+json.dumps(r),flush=True)
    print("HOARE_RUS_COMPOSITE_SUMMARY "+json.dumps(dict(expected=6,exact=exact)),flush=True)


def run_rus_unit(directory,exe,tmp,direct):
    """Exact natural counting of phase/fibre/real-unit exponents, no selectors."""
    with (directory/"native-rus-unit.tsv").open() as f:rows=list(csv.reader(f,delimiter="\t"))
    assert len(rows)<=6 and len({r[0] for r in rows})==len(rows)
    exact=0;cross=0;start=time.monotonic()
    for case,h0,h,primary,odd,vs,cs,B,ds,ex,base,ref,enc,checks,admitted in rows:
        h0,h,primary,odd,vs,cs,B,enc,checks,admitted=map(int,(h0,h,primary,odd,vs,cs,B,enc,checks,admitted))
        assert 0<=h<=h0<=17 and primary==1+h and B==(1<<primary)+1
        assert 0<=odd<=h0-h and checks==1<<primary and 0<=admitted<=checks
        assert 0<vs<=4096 and 0<cs<=32768
        dl=list(map(int,ds.split(",")));expected=list(map(int,ex.split(",")))
        K=list(map(int,base.split(",")));ref=list(map(int,ref.split(",")))
        assert len(K)==4 and len(ref)==32 and len(dl)==6+odd.bit_length()
        assert len(dl)==len(set(dl)) and all(0<l<=vs for l in dl)
        assert len(expected)==1<<len(dl) and sum(expected)==admitted
        assert all(0<=v<B for v in expected) and not any(expected[64*(odd+1):])
        header,*clauses=(directory/f"{case}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        weights={l:B**(1<<i) for i,l in enumerate(dl)}
        weights.update({-l:1 for l in dl})
        path=pathlib.Path(tmp)/"rus-unit.cnf"
        path.write_text("c t wmc\n"+header+"\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"\n".join(clauses)+"\n")
        r=dict(case=case,h0=h0,h=h,primary=primary,odd=odd,vars=vs,clauses=cs,
               encode_ns=enc,checks=checks,admitted=admitted,query_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=[],status="UNKNOWN")
        try:
            remaining=40-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError("unit scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],min(5,remaining),pathlib.Path(tmp)/"rus-unit-time.tsv",r["metrics"])
            v=parse_gpmc_integer(out,"wmc",B**len(expected)-1)
            bits=v.bit_length();digits=[]
            for _ in expected:digits.append(v%B);v//=B
            assert v==0 and digits==expected
            coeff=[[0]*4 for _ in range(8)]
            a=K
            t=time.monotonic_ns()
            for k in range(odd+1):
                for j in range(8):
                    for e in range(8):
                        q=[0]*4;q[e%4]=1 if e<4 else -1
                        term=rus_mul(a,q)
                        for i,c in enumerate(term):coeff[j][i]+=c*digits[64*k+8*j+e]
                a=rus_mul(a,[1,1,0,-1])
            decode_ns=time.monotonic_ns()-t
            assert [c for a in coeff for c in a]==ref
            name=case.removeprefix("rus-unit-")
            if name in direct:
                assert direct[name]==coeff
                cross+=1
                r["raw_crosscheck"]=True
            exact+=1
            r.update(status="EXACT",packed_bits=bits,nonzero_bins=sum(v!=0 for v in digits),
                     decode_ns=decode_ns,coeff=coeff)
        except (TimeoutError,subprocess.TimeoutExpired):r["status"]="TIMEOUT"
        except SolverSignalKilled:r["status"]="UNATTRIBUTED_SIGNAL_KILL"
        print("HOARE_RUS_UNIT_GPMC "+json.dumps(r),flush=True)
    print("HOARE_RUS_UNIT_SUMMARY "+json.dumps(dict(expected=6,exported=len(rows),exact=exact,raw_crosschecked=cross)),flush=True)


def rus_unit_moment_classes(vs,dl,odd):
    """Full-equivalence one-hot flags determined by the existing exponent."""
    assert odd>0 and len(dl)==6+odd.bit_length()
    counter=dl[6:]
    flags=list(range(vs+1,vs+odd+2))
    extra=[]
    for k,l in enumerate(flags):
        bits=[v if k>>j&1 else -v for j,v in enumerate(counter)]
        extra.extend([[-l,b] for b in bits])
        extra.append([l]+[-b for b in bits])
    extra.append(flags)
    # Exhaustively verify the small decoder, including invalid counter codes
    # and all possible flag vectors. No source assignments are required here:
    # the original native UP receipt already verifies the counter semantics.
    tested=0
    for k in range(1<<len(counter)):
        extensions=0
        for mask in range(1<<len(flags)):
            truth={v:bool(k>>j&1) for j,v in enumerate(counter)}
            truth.update({v:bool(mask>>j&1) for j,v in enumerate(flags)})
            valid=all(any(truth[abs(l)]==(l>0) for l in c) for c in extra)
            if valid:
                assert k<=odd and mask==1<<k
                extensions+=1
            tested+=1
        assert extensions==int(k<=odd)
    return flags,extra,tested


def run_rus_unit_moments(directory,exe,tmp,direct):
    """Compress unit exponent to two nonnegative Pell coefficients.

    The two coefficient sums occupy subdigits of one natural count.
    Existing deterministic counter + equality flags, no new primary bits.
    """
    with (directory/"native-rus-unit.tsv").open() as f:rows=list(csv.reader(f,delimiter="\t"))
    exact=0;cross=0;skipped=0;tested=0;start=time.monotonic()
    for case,h0,h,primary,odd,vs,cs,B,ds,ex,base,ref,enc,checks,admitted in rows:
        h0,h,primary,odd,vs,cs,B,enc,checks,admitted=map(int,(h0,h,primary,odd,vs,cs,B,enc,checks,admitted))
        if odd==0:
            skipped+=1
            print("HOARE_RUS_MOMENT_SKIP "+json.dumps(dict(case=case,reason="no-odd-factors")),flush=True)
            continue
        assert 0<h<=h0<=17 and primary==h+1 and B==(1<<primary)+1
        # Pilot bounded to the observed fixture range. No unbounded decoder
        # enumeration or implicit cap increase for future larger circuits.
        assert 1<=odd<=6 and odd<=h0-h
        dl=list(map(int,ds.split(",")));expected=list(map(int,ex.split(",")))
        K=list(map(int,base.split(",")));ref=list(map(int,ref.split(",")))
        assert len(dl)==6+odd.bit_length() and len(dl)==len(set(dl)) and all(0<l<=vs for l in dl)
        assert len(K)==4 and len(ref)==32 and len(expected)==1<<len(dl)
        assert sum(expected)==admitted and all(0<=v<B for v in expected) and not any(expected[64*(odd+1):])
        N=1<<primary
        A=[1];C=[0]
        for k in range(odd):
            A.append(A[-1]+2*C[-1]);C.append(A[-2]+C[-1])
        R=N*max(A[-1],C[-1])+1;radix=R*R
        want_a=[sum(expected[64*k+j]*A[k] for k in range(odd+1)) for j in range(64)]
        want_b=[sum(expected[64*k+j]*C[k] for k in range(odd+1)) for j in range(64)]
        assert all(0<=v<R for v in want_a+want_b)
        t=time.monotonic_ns()
        flags,extra,local_checks=rus_unit_moment_classes(vs,dl,odd)
        tested+=local_checks
        header,*body=(directory/f"{case}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(body)==cs
        nv=vs+len(flags);nc=cs+len(extra)
        assert nv<=4096 and nc<=32768
        weights={l:radix**(1<<i) for i,l in enumerate(dl[:6])}
        weights.update({l:A[k]+R*C[k] for k,l in enumerate(flags)})
        weights.update({-l:1 for l in list(weights)})
        p=pathlib.Path(tmp)/"rus-unit-moment.cnf"
        p.write_text("c t wmc\n"+f"p cnf {nv} {nc}\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"\n".join(body)+"\n"+"".join(" ".join(map(str,c))+" 0\n" for c in extra))
        augment_ns=time.monotonic_ns()-t
        r=dict(case=case,h0=h0,h=h,primary=primary,odd=odd,vars=nv,clauses=nc,
               base_vars=vs,base_clauses=cs,base_encode_ns=enc,augment_ns=augment_ns,
               class_checks=local_checks,radix=radix,subradix=R,checks=checks,
               query_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),metrics=[],status="UNKNOWN")
        try:
            remaining=40-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError("moment scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(p)],min(5,remaining),pathlib.Path(tmp)/"rus-unit-moment-time.tsv",r["metrics"])
            val=parse_gpmc_integer(out,"wmc",radix**64-1)
            bits=val.bit_length()
            t=time.monotonic_ns()
            got_a=[];got_b=[];coeff=[[0]*4 for _ in range(8)]
            for j in range(64):
                digit=val%radix;val//=radix
                a=digit%R;b=digit//R
                got_a.append(a);got_b.append(b)
                e=j%8;q=[0]*4;q[e%4]=1 if e<4 else -1
                term=rus_mul(rus_mul(K,[a,b,0,-b]),q)
                for i,c in enumerate(term):coeff[j//8][i]+=c
            decode_ns=time.monotonic_ns()-t
            assert val==0 and got_a==want_a and got_b==want_b
            assert [c for v in coeff for c in v]==ref
            name=case.removeprefix("rus-unit-")
            if name in direct:
                assert direct[name]==coeff
                cross+=1;r["raw_crosscheck"]=True
            exact+=1
            r.update(status="EXACT",packed_bits=bits,decode_ns=decode_ns,coeff=coeff,
                     moments_a=got_a,moments_b=got_b)
        except (TimeoutError,subprocess.TimeoutExpired):r["status"]="TIMEOUT"
        except SolverSignalKilled:r["status"]="UNATTRIBUTED_SIGNAL_KILL"
        print("HOARE_RUS_MOMENT_GPMC "+json.dumps(r),flush=True)
    print("HOARE_RUS_MOMENT_SUMMARY "+json.dumps(dict(expected=5,exact=exact,raw_crosschecked=cross,
          skipped_no_odd=skipped,class_checks=tested)),flush=True)

def run_rus_gram(directory,exe,tmp,reference,linear):
    """Independent reduced-source Gram queries; no oracle in verdict computation."""
    with (directory/"native-rus-gram.tsv").open() as f:
        rows=list(csv.reader(f,delimiter="\t"))
    assert len(rows)==28 and len({r[0] for r in rows})==28
    norms={}
    cross=[]
    start=time.monotonic()
    def align(a,scale):
        for _ in range(scale):a=rus_mul(a,[0,1,0,-1])
        return a
    def inner(a,b):
        terms=[rus_mul(rus_conj(x),y) for x,y in zip(a,b)]
        return [sum(t[j] for t in terms) for j in range(4)]
    for case,name,label,kind,branch,correct,h,scale,primary,vs,cs,B,ds,ms,expected,target,enc,checks in rows:
        branch,correct,h,scale,primary,vs,cs,B,enc,checks=map(int,(branch,correct,h,scale,primary,vs,cs,B,enc,checks))
        assert kind in ("norm","cross") and branch in (0,1) and correct in (0,1)
        norm=kind=="norm"
        assert 0<=h<=17 and 0<=scale<=34 and 0<vs<=4096 and 0<cs<=32768
        assert primary==1+(2*h if norm else h+2)
        dl=list(map(int,ds.split(",")))
        mag=[] if ms=="-" else [tuple(map(int,v.split(":"))) for v in ms.split(",")]
        ex=list(map(int,expected.split(",")))
        t=list(map(int,target.split(",")));assert len(t)==16;t=[t[i:i+4] for i in range(0,16,4)]
        assert len(dl)==3 and len(ex)==8 and all(0<=v<B for v in ex)
        assert (not mag)==norm
        assert B==((2<<(2*h)) if norm else (2<<h)*max(w for l,w in mag))+1
        assert all(1<=w<=5 for l,w in mag)
        lits=dl+[l for l,w in mag];assert len(lits)==len(set(lits)) and all(0<l<=vs for l in lits)
        weights={l:B**(1<<i) for i,l in enumerate(dl)}
        weights.update(mag);weights.update({-l:1 for l in lits})
        header,*clauses=(directory/f"{case}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        query=pathlib.Path(tmp)/"rus-gram.cnf"
        query.write_text("c t wmc\n"+header+"\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"\n".join(clauses)+"\n")
        r=dict(case=case,name=name,label=label,kind=kind,branch=branch,correct=correct,h=h,scale2=scale,primary=primary,vars=vs,clauses=cs,
               encode_ns=enc,checks=checks,query_sha256=hashlib.sha256(query.read_bytes()).hexdigest(),metrics=[],status="UNKNOWN")
        try:
            remaining=120-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError("Gram scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(query)],min(5,remaining),pathlib.Path(tmp)/"rus-gram-time.tsv",r["metrics"])
            v=parse_gpmc_integer(out,"wmc",B**8-1)
            bits=v.bit_length();counts=[]
            for _ in range(8):counts.append(v%B);v//=B
            assert v==0 and counts==ex
            val=[counts[i]-counts[i+4] for i in range(4)] if norm else [counts[2*i]-counts[2*i+1] for i in range(4)]
            a=align(val,2*scale if norm else scale)
            r.update(status="EXACT",digits=counts,packed_bits=bits,aligned=a)
            # Oracle only for cross-check, never for constructing a verdict.
            if name in reference:
                A=[reference[name][4*x+2*z+branch] for x in range(2) for z in range(2)]
                if correct:A=[[-v for v in a] if i&1 else a for i,a in enumerate(A)]
                assert a==(inner(A,A) if norm else inner(t,A))
                r["raw_crosscheck"]=True
            if norm:
                assert not correct and rus_gram_real_sign(a)>=0
                assert (name,branch) not in norms
                norms[name,branch]=a
            else:cross.append((r,t))
        except (TimeoutError,subprocess.TimeoutExpired):
            r["status"]="TIMEOUT"
        except SolverSignalKilled:
            r["status"]="UNATTRIBUTED_SIGNAL_KILL"
        print("HOARE_RUS_GRAM_GPMC "+json.dumps(r),flush=True)
    exact=0;matched=0
    for r,t in cross:
        key=(r["name"],r["branch"])
        if key not in norms:
            print("HOARE_RUS_GRAM_VERDICT "+json.dumps(dict(case=r["case"],verdict="UNKNOWN",reason="missing-norm")),flush=True)
            continue
        S=norms[key];T=inner(t,t);C=r["aligned"]
        D=[u-v for u,v in zip(rus_mul(S,T),rus_mul(C,rus_conj(C)))]
        assert rus_gram_real_sign(D)>=0
        ray=rus_gram_real_sign(S)>0 and rus_gram_real_sign(T)>0 and not any(D)
        real=ray and C==rus_conj(C)
        verdict="PROVED" if ray else "REFUTED";rv="PROVED" if real else "REFUTED"
        k=(r["name"],r["label"])
        if k in linear:
            assert verdict==linear[k]["ray_verdict"] and rv==linear[k]["real_verdict"]
            matched+=1
        exact+=1
        print("HOARE_RUS_GRAM_VERDICT "+json.dumps(dict(case=r["case"],S=S,T=T,C=C,delta=D,verdict=verdict,real_verdict=rv)),flush=True)
    print("HOARE_RUS_GRAM_SUMMARY "+json.dumps(dict(norm_exact=len(norms),cross_exact=len(cross),verdict_exact=exact,linear_matched=matched)),flush=True)

def run_rus_pilot(directory,exe,tmp,route="direct"):
    """Positive-integer packed raw and anchor-linear counts; no postselection
    norm shortcut. HSL basis-column targets are hash-pinned transcriptions."""
    assert route in ("direct","fixed","rr")
    with (directory/("native-rus.tsv" if route=="direct" else f"native-rus-{route}.tsv")).open() as f:
        rows=list(csv.reader(f,delimiter="\t"))
    assert len(rows)==22 and len({r[0] for r in rows})==22
    raw={}
    result={}
    aligned_raw={}
    def align(a,scale2):
        for _ in range(scale2):a=rus_mul(a,[0,1,0,-1])
        return a
    start=time.monotonic()
    for case,name,label,h,branch,correct,primary,vs,cs,B,ds,ms,expected,target,prep,enc,checks,h0,scale2 in rows:
        h,branch,correct,primary,vs,cs,B,prep,enc,checks=map(int,(h,branch,correct,primary,vs,cs,B,prep,enc,checks))
        h0,scale2=map(int,(h0,scale2))
        assert 0<=h<=h0<=17 and 0<=scale2<=2*(h0-h)
        assert route=="rr" or (h==h0 and scale2==0)
        assert 0<vs<=10000 and 0<cs<=40000
        is_raw=label=="raw"
        assert primary==1+h+(0 if is_raw else 4)
        digit_lits=list(map(int,ds.split(",")))
        magnitude=[] if ms=="-" else [tuple(map(int,v.split(":"))) for v in ms.split(",")]
        expected=list(map(int,expected.split(",")))
        t=list(map(int,target.split(",")))
        assert len(t)==16
        t=[t[i:i+4] for i in range(0,16,4)]
        assert len(digit_lits)==(6 if is_raw else 5)
        digits=1<<len(digit_lits)
        assert len(expected)==digits and all(0<=v<B for v in expected)
        assert (not magnitude)==is_raw
        lits=digit_lits+[l for l,w in magnitude]
        assert len(lits)==len(set(lits)) and all(0<l<=vs for l in lits)
        assert all(1<=w<=5 for l,w in magnitude)
        assert B==(2<<h)*(max(w for l,w in magnitude) if magnitude else 1)+1
        weights={l:B**(1<<i) for i,l in enumerate(digit_lits)}
        weights.update(magnitude)
        weights.update({-l:1 for l in lits})
        header,*clauses=(directory/f"{case}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        body="c t wmc\n"+header+"\n"+"".join(f"c p weight {l} {w} 0\n" for l,w in sorted(weights.items()))+"\n".join(clauses)+"\n"
        path=pathlib.Path(tmp)/"rus-pilot.cnf"
        path.write_text(body)
        row=dict(case=case,name=name,label=label,route=route,h=h,h0=h0,scale2=scale2,primary=primary,vars=vs,clauses=cs,prep_ns=prep,encode_ns=enc,checks=checks,
                 query_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=[],status="UNKNOWN")
        try:
            remaining=120-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError("RUS scheduling deadline")
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],min(5,remaining),pathlib.Path(tmp)/"rus-time.tsv",row["metrics"])
            value=parse_gpmc_integer(out,"wmc",B**digits-1)
            packed_bits=value.bit_length()
            counts=[]
            for _ in range(digits):
                counts.append(value%B);value//=B
            assert value==0 and counts==expected
            row.update(status="EXACT",packed_bits=packed_bits,digits=counts)
            if is_raw:
                assert sum(counts)==2<<h
                raw[name]=counts
                aligned_raw[name]=[align([counts[8*i+j]-counts[8*i+j+4] for j in range(4)],scale2) for i in range(8)]
            else:
                signed=[counts[i]-counts[i+1] for i in range(0,32,2)]
                minors=[signed[i:i+4] for i in range(0,12,4)]
                anchor=signed[12:16]
                w=sum(v*v for v in signed[:12])
                real=rus_mul(anchor,rus_conj(t[0]))
                nonzero=any(anchor)
                complex_ok=nonzero and w==0
                real_ok=complex_ok and real==rus_conj(real)
                aligned_minors=[align(v,scale2) for v in minors]
                aligned_anchor=align(anchor,scale2)
                row.update(aligned_minors=aligned_minors,aligned_anchor=aligned_anchor,
                           aligned_residual=sum(v*v for a in aligned_minors for v in a),
                           minors=minors,anchor=anchor,residual=w,anchor_nonzero=nonzero,
                           ray_verdict="PROVED" if complex_ok else "REFUTED",
                           real_verdict="PROVED" if real_ok else "REFUTED")
                # Recompute from independently solver-counted raw fibres,
                # not from the expected histogram.
                if name in raw:
                    a=[]
                    for fibre in range(4):
                        x,z=divmod(fibre,2)
                        base=32*x+8*(2*z+branch)
                        q=[raw[name][base+j]-raw[name][base+j+4] for j in range(4)]
                        if correct and z:q=[-v for v in q]
                        a.append(q)
                    assert a[0]==anchor
                    for i in range(1,4):
                        assert minors[i-1]==[u-v for u,v in zip(rus_mul(t[0],a[i]),rus_mul(t[i],a[0]))]
                    row["raw_crosscheck"]=True
                result[(name,label)]=row
        except (TimeoutError,subprocess.TimeoutExpired):
            row["status"]="TIMEOUT"
        except SolverSignalKilled:
            row["status"]="UNATTRIBUTED_SIGNAL_KILL"
        print("HOARE_RUS_GPMC "+json.dumps(row),flush=True)
    # Probability and retry certificates use actual raw branch counts.
    p_expected={"Figure7":(7,0,8),"Figure8":(3,0,4),"Figure9":(5,0,8),
                "Figure10a":(13,0,16),"Figure10b":(102,17,128),"Figure10c":(58,29,128)}
    for name,counts in raw.items():
        h=next(int(r[-2]) for r in rows if r[1]==name)
        scale2=next(int(r[-1]) for r in rows if r[1]==name)
        S=[];F=[]
        for x in range(2):
            for z in range(2):
                for branch,dst in ((1,S),(0,F)):
                    base=32*x+8*(2*z+branch)
                    dst.append(align([counts[base+j]-counts[base+j+4] for j in range(4)],scale2))
        if name in ("Figure7","Figure10b"):
            F[1]=[-v for v in F[1]];F[3]=[-v for v in F[3]]
        def inner(a,b):
            terms=[rus_mul(rus_conj(x),y) for x,y in zip(a,b)]
            return [sum(t[j] for t in terms) for j in range(4)]
        den=1<<h
        a,b,d=p_expected[name]
        assert 0<a and b>=0 and a*a>=0 and (d-a)>0 and (d-a)**2>2*b*b
        assert den%d==0
        p=[a*(den//d),b*(den//d),0,-b*(den//d)]
        assert inner(S[:2],S[:2])==inner(S[2:],S[2:])==p
        assert inner(S[:2],S[2:])==[0]*4
        assert F[0]==F[3] and not any(F[1]) and not any(F[2])
        assert rus_mul(F[0],rus_conj(F[0]))==[den-p[0],-p[1],0,-p[3]]
        print("HOARE_RUS_RETRY "+json.dumps(dict(name=name,route=route,success_numerator=p,denominator=den,
             corrected_failure_scalar=F[0],physical_termination="PROVED")),flush=True)
    wanted={("Figure10a","original-post"):18432,("Figure10c","original-post"):1638400,
            ("Figure7","omit-Z-correction"):64,("Figure10b","omit-Z-correction"):106496}
    for key,row in result.items():
        assert row["aligned_residual"]==wanted.get(key,0) and row["anchor_nonzero"]
        assert row["real_verdict"]=="REFUTED"
    print("HOARE_RUS_GPMC_SUMMARY "+json.dumps(dict(route=route,expected=22,raw_exact=len(raw),linear_exact=len(result),
         crosschecked=sum(bool(r.get("raw_crosscheck")) for r in result.values()))),flush=True)
    return aligned_raw,result,raw

def run_sparse_target_pilot(directory,exe,tmp):
    """Bounded canonical target coefficient lookup versus term selector."""
    with (directory/"native-sparse-target.tsv").open() as f:
        manifest=list(csv.reader(f,delimiter="\t"))
    assert len(manifest)==32 and len({r[0] for r in manifest})==32
    rows={}
    for name,n,variant,route,primary,vs,cs,classes,ep,em,norm,w,enc,checks in manifest:
        n,primary,vs,cs,ep,em,norm,w,enc,checks=map(int,(n,primary,vs,cs,ep,em,norm,w,enc,checks))
        assert n in (2,4) and variant in ("source","Z","T","X") and route in ("lookup","selector","grouped","self")
        h=2*n+2
        assert primary==n+h+(n if route in ("selector","grouped") else h if route=="self" else 0)
        assert 0<vs<=10000 and 0<cs<=40000 and norm==1<<(n+h)
        weights=[(int(l),int(v)) for l,v in (x.split(":") for x in classes.split(","))]
        assert len({l for l,v in weights})==len(weights) and all(0<l<=vs for l,v in weights)
        assert sorted(v for l,v in weights)==([-4,-2,2,4] if route in ("lookup","grouped") else [-2,2] if route=="selector" else [-1,1])
        bound=(1<<primary)*max(abs(v) for l,v in weights)
        B=bound+1
        natural={l:abs(v)*(B if v<0 else 1) for l,v in weights}
        for l,v in weights:natural[-l]=1
        header,*clauses=(directory/f"{name}.cnf").read_text().splitlines()
        assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
        body="c t wmc\n"+header+"\n"+"".join(f"c p weight {l} {v} 0\n" for l,v in sorted(natural.items()))+"\n".join(clauses)+"\n"
        path=pathlib.Path(tmp)/"sparse-target.cnf"
        path.write_text(body)
        row=dict(case=name,n=n,variant=variant,route=route,primary=primary,vars=vs,clauses=cs,encode_ns=enc,checks=checks,norm=norm,expected_residual=w,status="UNKNOWN",metrics=[],sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        try:
            out=profile_gpmc([str(exe),"-mode=1","-natw",str(path)],5,pathlib.Path(tmp)/"sparse-target-time.tsv",row["metrics"])
            v=parse_gpmc_integer(out,"wmc",bound*(B+1))
            p,q=v%B,v//B
            assert p+q<=bound and (p,q)==(ep,em)
            row.update(status="EXACT",plus=p,minus=q,score=p-q)
            if route=="self":assert p-q==norm
            else:assert 2*(norm-p+q)==w
        except (TimeoutError,subprocess.TimeoutExpired):
            row["status"]="TIMEOUT"
        except SolverSignalKilled:
            row["status"]="UNATTRIBUTED_SIGNAL_KILL"
        rows[n,variant,route]=row
        print("HOARE_SPARSE_GPMC "+json.dumps(row),flush=True)
    matched=0
    for n in (2,4):
        for v in ("source","Z","T","X"):
            a,b,g,c=(rows[n,v,r] for r in ("lookup","selector","grouped","self"))
            if all(r["status"]=="EXACT" for r in (a,b,g,c)):
                assert a["score"]==b["score"]==g["score"] and c["score"]==a["norm"]
                assert (a["plus"],a["minus"])==(g["plus"],g["minus"])
                assert a["expected_residual"]==b["expected_residual"]==g["expected_residual"]==c["expected_residual"]
                matched+=1
    print("HOARE_SPARSE_GPMC_SUMMARY "+json.dumps(dict(exported=len(rows),exact=sum(r["status"]=="EXACT" for r in rows.values()),matched=matched)),flush=True)

def run_partition_pilot(directory, exe, tmp):
    """Separate source-only partition pilot. Unknown leaves never certify a cover."""
    with (directory/"native-partition.tsv").open() as f:
        manifest=list(csv.reader(f,delimiter="\t"))
    assert len({r[1] for r in manifest})==len(manifest)
    strategies=("fixed","restart","resume","resume-fixed")
    assert {r[0] for r in manifest}==set(strategies)
    exact_rows={}
    for strategy in strategies:
        cohort=[r for r in manifest if r[0]==strategy]
        assert 1<=len(cohort)<=16
        coverage=set()
        decided=set()
        residual=0
        start=time.monotonic()
        solver_seconds=0.0
        max_rss=0
        for route,name,mask,val,inputs,state,primary,vs,cs,encode_ns,classes,ep,em,norm in cohort:
            mask,val,inputs,primary,vs,cs,encode_ns,ep,em,norm=map(int,(mask,val,inputs,primary,vs,cs,encode_ns,ep,em,norm))
            assert 0<=mask<=15 and 0<=val<=15 and val&~mask==0
            xs={x for x in range(16) if x&mask==val}
            assert xs and len(xs)==inputs and norm==65536*inputs
            assert not coverage.intersection(xs)
            coverage.update(xs)
            row=dict(strategy=route,case=name,mask=mask,value=val,inputs=inputs,
                     norm=norm,primary=primary,vars=vs,clauses=cs,encode_ns=encode_ns,status=state,metrics=[])
            if state=="READY":
                assert primary==16+4-mask.bit_count() and 0<vs<=10000 and 0<cs<=40000
                weights=[(int(l),int(w)) for l,w in (s.split(":") for s in classes.split(","))]
                assert len(weights)==4 and len({l for l,w in weights})==4 and sorted(w for l,w in weights)==[-251,-13,13,251]
                assert all(0<l<=vs for l,w in weights)
                bound=(1<<primary)*251
                radix=bound+1
                natural={l:abs(w)*(radix if w<0 else 1) for l,w in weights}
                for l,w in weights:natural.setdefault(-l,1)
                base=(directory/f"{name}.cnf").read_text()
                header,*clauses=base.splitlines()
                assert header==f"p cnf {vs} {cs}" and len(clauses)==cs
                query=pathlib.Path(tmp)/"partition-pilot.cnf"
                weights_text="".join(f"c p weight {l} {w} 0\n" for l,w in sorted(natural.items()))
                query.write_text("c t wmc\n"+header+"\n"+weights_text+"\n".join(clauses)+"\n")
                row["query_sha256"]=hashlib.sha256(query.read_bytes()).hexdigest()
                remaining=120-(time.monotonic()-start)
                if remaining<=0:
                    row["status"]="TOTAL_DEADLINE"
                else:
                    try:
                        out=profile_gpmc([str(exe),"-mode=1","-natw",str(query)],min(10,remaining),
                                         pathlib.Path(tmp)/"partition-time.tsv",row["metrics"])
                        value=parse_gpmc_integer(out,"wmc",bound*(radix+1))
                        plus,minus=value%radix,value//radix
                        assert plus+minus<=bound and (plus,minus)==(ep,em)
                        w=2*(norm-(plus-minus))
                        assert w==0
                        row.update(status="EXACT",plus=plus,minus=minus,residual=w)
                        decided.update(xs);residual+=w
                        exact_rows[(strategy,mask,val)]=(plus,minus)
                    except (TimeoutError,subprocess.TimeoutExpired):
                        row["status"]="TIMEOUT"
                    except SolverSignalKilled:
                        row["status"]="UNATTRIBUTED_SIGNAL_KILL"
                for m in row["metrics"]:
                    solver_seconds+=m["wall_s"]
                    max_rss=max(max_rss,m["max_rss_kib"] or 0)
            else:
                assert state in ("RR_LIMIT","ENCODER_LIMIT")
            print("HOARE_PARTITION_GPMC "+json.dumps(row),flush=True)
        assert coverage==set(range(16))
        print("HOARE_PARTITION_GPMC_SUMMARY "+json.dumps(dict(
            strategy=strategy,leaves=len(cohort),coverage=len(coverage),decided_inputs=len(decided),
            residual=residual if decided==coverage else None,
            verdict="PROVED" if decided==coverage else "UNKNOWN",
            solver_s=solver_seconds,solver_peak_rss_kib=max_rss,
            route_wall_s=time.monotonic()-start)),flush=True)
    # No RR is applied after final specialization: both signed buckets
    # must add exactly within every fully solved parent, not just their difference.
    checked=0
    for (strategy,mask,val),bucket in exact_rows.items():
        if strategy!="resume":continue
        xs=[x for x in range(16) if x&mask==val]
        children=[exact_rows.get(("resume-fixed",15,x)) for x in xs]
        if all(c is not None for c in children):
            assert bucket==tuple(sum(c[i] for c in children) for i in range(2))
            checked+=1
    print("HOARE_PARTITION_REBUCKET "+json.dumps(dict(checked=checked)),flush=True)

def run_dual_mask_wmc(directory, count, deadline):
    """Bounded native dual-mask pilot, exact MPZ weights, original input witness."""
    rows = []
    with (directory / "native-dual-mask.tsv").open() as f:
        manifest = list(csv.reader(f, delimiter="\t"))
    assert len(manifest) == 18
    assert len({(r[0], r[1]) for r in manifest}) == 18
    assert {r[1] for r in manifest} == {"full", "identity", "flip"}
    for name, route, sign, primary, vars_, clauses, encode_ns, p0, m0, p1, m1 in manifest:
        sign, primary, vars_, clauses, encode_ns, p0, m0, p1, m1 = map(
            int, (sign, primary, vars_, clauses, encode_ns, p0, m0, p1, m1))
        assert primary == 7 and 0 < abs(sign) <= vars_
        expected = ((p0, m0), (p1, m1))
        base = (directory / f"dual-mask-{name}-{route}.cnf").read_text()
        assert base.splitlines()[0] == f"p cnf {vars_} {clauses}"
        row = dict(case=name, route=route, vars=vars_, clauses=clauses,
                   encode_ns=encode_ns, backend="gpmc-mpz-packed",
                   verdict="UNKNOWN", root=None, root_queries=0, witness_queries=0,
                   witness=None, witness_status="NOT_RUN", root_s=0.0, witness_s=0.0)
        def query(prefix, end, field):
            row[field] += 1
            value, radix = count(base, prefix, sign, end, primary=primary)
            plus, minus = value % radix, value // radix
            if not 0 <= plus + minus <= (1 << (primary - len(prefix))):
                raise ValueError("dual-mask count exceeds primary assignment bound")
            if plus < minus:
                raise ValueError("dual-mask negative projected norm")
            return plus, minus

        start = time.monotonic()
        try:
            root = query([], min(deadline, start + 5), "root_queries")
        except (TimeoutError, subprocess.TimeoutExpired):
            row["root_s"] = time.monotonic() - start
        else:
            row["root_s"] = time.monotonic() - start
            row["root"] = root
            row["verdict"] = "PROVED" if root[0] == root[1] else "REFUTED"
            row["witness_status"] = "NOT_REQUIRED" if row["verdict"] == "PROVED" else "UNKNOWN_RESOURCE"
            # Read the independent oracle only after the root decision.
            assert root == (p0 + p1, m0 + m1), (name, route, root, expected)
            if row["verdict"] == "REFUTED":
                start = time.monotonic()
                end = min(deadline, start + 5)
                try:
                    a = query([-2], end, "witness_queries")
                    assert a == expected[0]
                    if a[0] > a[1]:
                        x, witness = 0, a
                    else:
                        x, witness = 1, query([2], end, "witness_queries")
                        assert witness == expected[1]
                    if witness[0] <= witness[1]:
                        raise ValueError("dual-mask witness is not positive")
                    row["witness"] = x
                    row["witness_status"] = "VERIFIED"
                    row["witness_count"] = witness
                except (TimeoutError, subprocess.TimeoutExpired):
                    pass
                row["witness_s"] = time.monotonic() - start
        row["decision_s"] = encode_ns / 1e9 + row["root_s"]
        rows.append(row)
        print("HOARE_GPMC_DUAL_MASK " + json.dumps(row), flush=True)
    for name in {r["case"] for r in rows}:
        decided = [r for r in rows if r["case"] == name and r["verdict"] != "UNKNOWN"]
        norms = {r["root"][0] - r["root"][1] for r in decided}
        assert len(norms) <= 1, (name, norms)
    print("HOARE_GPMC_DUAL_MASK_SUMMARY " + json.dumps(dict(
        variants=len(rows), decided=sum(r["verdict"] != "UNKNOWN" for r in rows),
        proved=sum(r["verdict"] == "PROVED" for r in rows),
        refuted=sum(r["verdict"] == "REFUTED" for r in rows),
        witnesses=sum(r["witness_status"] == "VERIFIED" for r in rows),
        unknown=sum(r["verdict"] == "UNKNOWN" for r in rows))), flush=True)
    return rows


def run_gpmc_pure(directory, exe, tmp, deadline):
    """Two exact natural-weight queries, with arbitrary-precision packed counts.

    Packing avoids negative weights and does not require complex MPFR
    or a floating-point near-zero threshold. Every model contributes
    either 1 or radix. radix=2^(CNF variables+1) exceeds either bucket.
    """
    query_file=pathlib.Path(tmp)/"gpmc-pure.cnf"
    query_cap=5
    long_metrics=None
    def count(base, assumptions, weighted_lit, end, primary=None):
        header,*clauses=base.splitlines()
        p,kind,v,c=header.split();v,c=int(v),int(c)
        assert (p,kind)==("p","cnf") and len(clauses)==c
        assert all(0<abs(l)<=v for l in assumptions)
        bound_bits=v if primary is None else primary
        assert 0<=bound_bits<=v
        radix=1<<(bound_bits+1)
        weights=""
        mode="mc"
        if weighted_lit is not None:
            assert 0<abs(weighted_lit)<=v
            mode="wmc"
            weights=f"c p weight {weighted_lit} {radix} 0\nc p weight {-weighted_lit} 1 0\n"
        query_file.write_text(f"c t {mode}\np cnf {v} {c+len(assumptions)}\n"+weights+
            "".join(l+"\n" for l in clauses)+"".join(f"{l} 0\n" for l in assumptions))
        remaining=min(deadline,end)-time.monotonic()
        if remaining<=0:
            raise TimeoutError("GPMC stage budget")
        args=[str(exe),"-mode=1","-natw"] if mode=="wmc" else [str(exe),"-mode=0"]
        if long_metrics is None:
            proc=subprocess.run(args+[str(query_file)],capture_output=True,text=True,
                                timeout=min(query_cap,remaining),check=True)
            stdout=proc.stdout
        else:
            stdout=profile_gpmc(args+[str(query_file)],min(query_cap,remaining),
                                pathlib.Path(tmp)/"gpmc-resource.tsv",long_metrics)
        result=parse_gpmc_integer(stdout,mode,(1<<bound_bits)*(radix if mode=="wmc" else 1))
        return result,radix
    def solve(base,delta,prefix,end):
        d0,d1,d2=delta
        a,radix=count(base,list(prefix)+[-d0,-d1],d2,end)
        b,rb=count(base,list(prefix)+[d0,-d2],d1,end)
        assert radix==rb
        return unpack_pair(a,radix),unpack_pair(b,radix)

    # Runtime qualification includes free variables, both polarities,
    # UNSAT and integer weights beyond IEEE-754 precision.
    end=min(deadline,time.monotonic()+10)
    assert count("p cnf 3 1\n1 0\n",[],None,end)[0]==4
    assert count("p cnf 1 2\n1 0\n-1 0\n",[],None,end)[0]==0
    for lit in (1,-1):
        value,radix=count("p cnf 61 1\n1 0\n",[],lit,end)
        assert value==(1<<60)*(radix if lit==1 else 1)
    value,radix=count("p cnf 1 0\n",[],1,end)
    assert unpack_pair(value,radix)==0
    assert parse_gpmc_integer("s SATISFIABLE\nc s type wmc\nc s exact arb int 9007199254740993\n",
                              "wmc",1<<60)==9007199254740993
    for bad in ("s SATISFIABLE\nc s type wmc\nc s exact arb frac 1/1\n",
                "s UNSATISFIABLE\nc s type wmc\nc s exact arb int 1\n"):
        try:
            parse_gpmc_integer(bad,"wmc",100)
        except ValueError:
            continue
        raise AssertionError("accepted malformed GPMC output")
    print("HOARE_GPMC_QUALIFICATION=PASS backend=mpz_natural_packed",flush=True)
    rows=run_pure_wmc(directory,solve,deadline,backend="gpmc-mpz-packed")
    from hoare_projected_count import z8_differential
    z8_differential(directory,exe,tmp,rows)
    from hoare_projected_count import audit_fourier_heldout
    audit_fourier_heldout(directory/"fourier-heldout")
    if os.environ.get("HOARE_SECTOR_TRANSPORT")=="1":
        from hoare_sector_transport import run_fourier
        run_fourier(directory/"fourier-heldout")
    deadline=time.monotonic()+45
    run_residual_hybrid(directory,solve,deadline,rows)
    if (directory/"native-dual-mask.tsv").is_file():
        deadline=time.monotonic()+60
        run_dual_mask_wmc(directory,count,deadline)
    if (directory/"native-factor.tsv").is_file():
        run_amplitude_factor_pilot(directory,exe,tmp)
        # The paired timing cohort is opt-in; keep ordinary exact regressions.
        repeat_flag=os.environ.get("HOARE_FACTOR_REPEATS","0")
        if repeat_flag not in ("0","1"):
            raise ValueError("HOARE_FACTOR_REPEATS must be 0 or 1")
        if repeat_flag=="1":
            for repeat_round in range(4):
                run_amplitude_factor_pilot(directory,exe,tmp,repeat_round=repeat_round)
        else:
            print("HOARE_FACTOR_REPEAT_SKIPPED opt_in=HOARE_FACTOR_REPEATS=1",flush=True)
    if (directory/"native-multi-factor.tsv").is_file():
        run_amplitude_factor_pilot(directory,exe,tmp,multi=True)
    if (directory/"witness-source.tsv").is_file():
        run_multi_witness_pilot(directory,exe,tmp)
    if (directory/"native-partition.tsv").is_file():
        run_partition_pilot(directory,exe,tmp)
    if (directory/"qftcomplex-3-source.tsv").is_file():
        run_qft_complex_pilot(directory,exe,tmp)
    if (directory/"native-sparse-target.tsv").is_file():
        run_sparse_target_pilot(directory,exe,tmp)
    if (directory/"native-rus.tsv").is_file():
        direct,dr,digits=run_rus_pilot(directory,exe,tmp)
        for route in ("fixed","rr"):
            if not (directory/f"native-rus-{route}.tsv").is_file():continue
            reduced,rr,other_digits=run_rus_pilot(directory,exe,tmp,route=route)
            raw_pairs=direct.keys() & reduced.keys()
            linear_pairs=dr.keys() & rr.keys()
            for k in raw_pairs:
                assert direct[k]==reduced[k]
                if route=="fixed":assert digits[k]==other_digits[k]
            for k in linear_pairs:
                for field in ("aligned_anchor","aligned_minors","aligned_residual","ray_verdict","real_verdict"):
                    assert dr[k][field]==rr[k][field]
                if route=="fixed":assert dr[k]["digits"]==rr[k]["digits"]
            print("HOARE_RUS_ABLATION_PARITY "+json.dumps(dict(route=route,raw_pairs=len(raw_pairs),linear_pairs=len(linear_pairs))),flush=True)
        if (directory/"native-rus-gram.tsv").is_file():
            run_rus_gram(directory,exe,tmp,direct,dr)
        if (directory/"native-rus-unit.tsv").is_file():
            run_rus_unit(directory,exe,tmp,direct)
            run_rus_unit_moments(directory,exe,tmp,direct)
        if (directory/"native-rus-composite.tsv").is_file():
            run_rus_composite(directory,exe,tmp)
            replay=os.environ.get("HOARE_CUBIC_REPLAY","0")
            assert replay in ("0","1")
            run_weighted_cubic(exe,pathlib.Path(sys.argv[1]).resolve(),tmp,sizes=(14,18,24,32) if replay=="1" else (14,))
            from hoare_cubic_rr import run_cubic_rr
            run_cubic_rr(cubic_edges)
    if (directory/"native-affine-wmc.tsv").is_file():
        query_cap=30
        deadline=time.monotonic()+720
        long_metrics=[]
        run_native_affine_wmc(directory,solve,deadline,long_metrics)
        long_metrics=None
        query_cap=5
    if (directory/"native-gse-wmc.tsv").is_file():
        query_cap=35
        deadline=time.monotonic()+360
        long_metrics=[]
        run_native_gse_wmc(directory,solve,deadline,long_metrics)
        long_metrics=None
        query_cap=5
    if (directory/"paper-conditioned-fibre.tsv").is_file():
        run_paper_single_fibre(directory,exe,tmp,conditioned=True)
    elif (directory/"paper-single-fibre.tsv").is_file():
        run_paper_single_fibre(directory,exe,tmp)
    # Freeze previously accepted timeout baselines instead of repeatedly
    # spending six additional 30s queries during conditioned-RR research.
    if (directory/"paper-projected.tsv").is_file() and not (directory/"paper-conditioned-fibre.tsv").is_file():
        query_cap=30
        deadline=time.monotonic()+240
        long_metrics=[]
        with (directory/"paper-projected.tsv").open() as f:
            optimized=any("\thybrid-pre-heap\t" in line for line in f)
        if optimized:
            run_paper_projected_optimized(directory,count,deadline,long_metrics)
        else:
            run_paper_projected(directory,count,deadline,long_metrics)
        long_metrics=None
        query_cap=5
    # Preserve the original discovery protocol on explicit request. Default
    # to the frozen long cohort rather than rerunning all 19 known timeouts.
    if os.environ.get("HOARE_SECTOR_TRANSPORT")=="1":
        # Prior long/held-out comparisons are frozen; no repeated timing.
        pass
    elif os.environ.get("HOARE_FOURIER_COMPARE")=="1":
        heldout_long=os.environ.get("HOARE_FOURIER_LONG")=="1"
        query_cap=120 if heldout_long else 30
        deadline=time.monotonic()+1200
        long_metrics=[]
        profile_contract_tests(pathlib.Path(tmp),long_metrics)
        run_structure_dispatch(directory/"fourier-heldout",solve,deadline,long_metrics,
                               heldout=True,gpmc_exe=exe,tmp=tmp,heldout_long=heldout_long)
        long_metrics=None
    elif os.environ.get("HOARE_SCALE_DISCOVERY")=="1":
        query_cap=30
        deadline=time.monotonic()+1500
        run_scale_discovery(directory/"scale-discovery",solve,deadline)
    else:
        query_cap=200
        deadline=time.monotonic()+1800
        long_metrics=[]
        profile_contract_tests(pathlib.Path(tmp),long_metrics)
        if os.environ.get("HOARE_SCALE_LONG")=="1":
            run_scale_long(directory/"scale-discovery",solve,deadline,long_metrics)
            query_cap=60
            deadline=time.monotonic()+330
            run_cone_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
        else:
            query_cap=120
            deadline=time.monotonic()+1050
            if os.environ.get("HOARE_LITERAL_QUOTIENT")=="1":
                run_quotient_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            elif os.environ.get("HOARE_AFFINE_QUOTIENT")=="1":
                run_affine_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            elif os.environ.get("HOARE_PHASE_FACTOR")=="1":
                run_factor_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            elif os.environ.get("HOARE_STREAMED_FACTOR")=="1":
                run_streamed_factor_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            elif os.environ.get("HOARE_CONDITIONED_FACTOR")=="1":
                run_conditioned_factor_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            elif os.environ.get("HOARE_PROPERTY_FACTOR")=="1" or os.environ.get("HOARE_R27A_FULL")=="1":
                run_property_factor_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
            else:
                run_structure_dispatch(directory/"scale-discovery",solve,deadline,long_metrics)
                # Frozen paired root benchmark; keep the preceding dispatch
                # experiment unchanged, give each arm the same root budget.
                from hoare_projected_count import long_differential
                query_cap=60
                deadline=time.monotonic()+660
                long_differential(directory/"scale-discovery",exe,tmp,solve,deadline,long_metrics)
        long_metrics=None
    return rows




def affine_prefix_witness(base,delta,width,positions,offset,basis,mode,solve,end):
    """Search only free input coordinates; no oracle or candidate enumeration.
    For a bijective affine model the free assignment determines one legal x.
    Reconfirm the decoded full input in the SAME residual CNF.
    """
    assert len(positions)==len(basis) and len(set(positions))==len(positions)
    assert all(0<=j<width for j in positions)
    prefix=[];t=0;calls=0
    for i,j in enumerate(positions):
        prefix.append(-(j+2));calls+=1
        if not any(solve(base,delta,prefix,end)):
            prefix[-1]=j+2;t|=1<<i
    original=offset
    for i,v in enumerate(basis):
        if t>>i&1:original^=v
    if mode=="mono":
        encoded=original
    elif mode=="padded":
        encoded=sum(((t>>i)&1)<<j for i,j in enumerate(positions))
    else:
        assert mode=="free"
        encoded=t
    assert 0<=encoded<1<<width
    full=[j+2 if encoded>>j&1 else -(j+2) for j in range(width)]
    calls+=1
    value=tuple(solve(base,delta,full,end))
    if not any(value) or not positive_surd(value):raise ValueError("invalid affine-prefix witness")
    return encoded,original,value,calls


def affine_prefix_contract():
    # Two free coordinates, nonzero offset and nontrivial parity; the
    # positive witness is NOT the all-zero free assignment.
    # x = 1 xor t0*3 xor t1*4, only x=5 has positive leakage.
    for mode,width,positions,wanted in (("mono",3,[1,2],5),
                                        ("padded",3,[1,2],4),
                                        ("free",2,[0,1],2)):
        def fake(base,delta,prefix,end):
            return (3,0) if all(bool(wanted>>(abs(l)-2)&1)==(l>0) for l in prefix) else (0,0)
        u,x,value,calls=affine_prefix_witness("",[],width,positions,1,[3,4],mode,fake,time.monotonic()+1)
        assert (u,x,value,calls)==(wanted,5,(3,0),3)
    print("HOARE_AFFINE_PREFIX_CONTRACT=PASS nonzero_offset=true nonzero_free_assignment=true",flush=True)


def run_native_affine_wmc(directory,solve,deadline,metrics):
    """Same exact GPMC root; isolate coordinate encoding from witness search."""
    affine_prefix_contract()
    fields="case mode n h0 h scale width vars clauses delta status prep_ns encoding_ns expected mapping oracle free_positions offset basis".split()
    with (directory/"native-affine-wmc.tsv").open() as f:
        plans={(r["case"],r["mode"]):r for r in csv.DictReader(f,fieldnames=fields,delimiter="\t")}
    assert len(plans)==9
    rows=[]
    caps={6:(8,5),7:(20,8),8:(30,12)}
    for i,name in enumerate(sorted({name for name,_ in plans},key=lambda s:int(s.rsplit("-",1)[1]))):
        n=int(name.rsplit("-",1)[1]);root_cap,witness_cap=caps[n]
        for rep in range(2):
            modes=["mono","padded","free"]
            modes=modes[i%3:]+modes[:i%3]
            if rep:modes.reverse()
            for mode in modes:
                p=plans[name,mode]
                row=dict(case=name,mode=mode,rep=rep,status=p["status"],root_cap_s=root_cap,witness_cap_s=witness_cap,
                         **{k:int(p[k]) for k in ("n","h0","h","scale","width","vars","clauses","prep_ns","encoding_ns")})
                target=tuple(map(int,p["expected"].split(",")))
                assert p["expected"]==plans[name,"mono"]["expected"]
                row.update(expected=target,coeff=None,verdict="UNKNOWN",root_s=0.0,root_queries=0,witness_routes={})
                if p["status"]=="READY" and time.monotonic()<deadline:
                    base=(directory/f"native-affine-{name}-{mode}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(base).hexdigest()
                    delta=list(map(int,p["delta"].split(",")))
                    positions=list(map(int,p["free_positions"].split(",")))
                    offset=int(p["offset"]);basis=list(map(int,p["basis"].split(",")))
                    mapping=dict(tuple(map(int,s.split(":"))) for s in p["mapping"].split(","))
                    oracle={int(x):(int(a),int(b)) for x,a,b in (s.split(":") for s in p["oracle"].split(","))}
                    start=time.monotonic();end=min(deadline,start+root_cap)
                    metrics.clear()
                    try:
                        row["root_queries"]=1
                        c=tuple(solve(base.decode(),delta,[],end))
                        if any(c) and not positive_surd(c):raise ValueError("negative root")
                        c=tuple(v*(1<<row["scale"]) for v in c)
                        assert c==target,(name,mode,c,target)
                        row.update(coeff=c,verdict="REFUTED" if any(c) else "PROVED",status="EXACT_ROOT")
                    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                    row["root_s"]=time.monotonic()-start
                    row["root_metrics"]=[dict(m) for m in metrics]
                    if row["verdict"]=="REFUTED":
                        strategies=["guided"] if mode=="free" else ["full","guided"]
                        if rep:strategies.reverse()
                        for strategy in strategies:
                            rec=dict(status="UNKNOWN_RESOURCE",queries=0,seconds=0.0)
                            st=time.monotonic();end=min(deadline,st+witness_cap)
                            metrics.clear()
                            def counted(base,delta,prefix,end):
                                rec["queries"]+=1
                                value=tuple(solve(base,delta,prefix,end))
                                if any(value) and not positive_surd(value):raise ValueError("negative conditioned leakage")
                                return value
                            try:
                                if strategy=="guided":
                                    u,x,v,calls=affine_prefix_witness(base.decode(),delta,row["width"],positions,offset,basis,mode,counted,end)
                                    assert calls==rec["queries"]
                                else:
                                    prefix=[];u=0
                                    for j in range(row["width"]):
                                        prefix.append(-(j+2))
                                        if not any(counted(base.decode(),delta,prefix,end)):
                                            prefix[-1]=j+2;u|=1<<j
                                    v=counted(base.decode(),delta,prefix,end)
                                    x=mapping[u]
                                v=tuple(a*(1<<row["scale"]) for a in v)
                                assert mapping[u]==x and any(v) and v==oracle[x],(name,mode,strategy,u,x,v)
                                rec.update(status="VERIFIED",witness=x,coeff=v)
                            except (TimeoutError,subprocess.TimeoutExpired,SolverSignalKilled):pass
                            rec["seconds"]=time.monotonic()-st
                            rec["metrics"]=[dict(m) for m in metrics]
                            row["witness_routes"][strategy]=rec
                elif p["status"]=="READY":
                    row["status"]="GLOBAL_BUDGET_NOT_RUN"
                rows.append(row)
                print("HOARE_NATIVE_AFFINE_GUIDED "+json.dumps(row),flush=True)
    assert len(rows)==18
    print("HOARE_NATIVE_AFFINE_GUIDED_SUMMARY "+json.dumps({m:dict(attempts=sum(r["mode"]==m for r in rows),
        exact=sum(r["mode"]==m and r["coeff"] is not None for r in rows),
        full_verified=sum(r["mode"]==m and r["witness_routes"].get("full",{}).get("status")=="VERIFIED" for r in rows),
        guided_verified=sum(r["mode"]==m and r["witness_routes"].get("guided",{}).get("status")=="VERIFIED" for r in rows)) for m in ("mono","padded","free")}),flush=True)


def run_native_gse_wmc(directory,solve,deadline,metrics):
    """Root-only pilot; matched common preparation and GPMC exact backend."""
    fields="case mode n h0 common_h h scale hits vars clauses delta status baseline_status common_ns prep_ns encoding_ns expected cancellation_hits sat_visits limits".split()
    with (directory/"native-gse-wmc.tsv").open() as f:
        plans={(p["case"],p["mode"]):p for p in csv.DictReader(f,fieldnames=fields,delimiter="\t")}
    assert len(plans)==8
    rows=[]
    for i,name in enumerate(sorted({name for name,_ in plans})):
        n=int(plans[name,"baseline"]["n"]);cap={6:12,7:20,8:35}[n]
        for rep in range(2):
            modes=["baseline","gse"]
            if (i+rep)%2:modes.reverse()
            for mode in modes:
                p=plans[name,mode]
                row=dict(case=name,mode=mode,rep=rep,status=p["status"],baseline_status=p["baseline_status"],cap_s=cap,
                    **{k:int(p[k]) for k in ("n","h0","common_h","h","scale","hits","vars","clauses","common_ns","prep_ns","encoding_ns","cancellation_hits","sat_visits","limits")})
                target=tuple(map(int,p["expected"].split(",")))
                assert p["expected"]==plans[name,"baseline"]["expected"]
                row.update(expected=target,coeff=None,root_s=0.0,verdict="UNKNOWN")
                if p["status"]=="READY" and time.monotonic()<deadline:
                    base=(directory/f"native-gse-{name}-{mode}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(base).hexdigest()
                    delta=list(map(int,p["delta"].split(",")))
                    st=time.monotonic();end=min(deadline,st+cap)
                    metrics.clear()
                    try:
                        v=tuple(solve(base.decode(),delta,[],end))
                        if any(v) and not positive_surd(v):raise ValueError("negative leakage")
                        c=tuple(x*(1<<row["scale"]) for x in v)
                        assert c==target,(name,mode,c,target)
                        row.update(coeff=c,status="EXACT_ROOT",verdict="REFUTED" if any(c) else "PROVED")
                    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                    row["root_s"]=time.monotonic()-st
                    row["metrics"]=[dict(m) for m in metrics]
                elif p["status"]=="READY":
                    row["status"]="GLOBAL_BUDGET_NOT_RUN"
                rows.append(row)
                print("HOARE_NATIVE_GSE_GPMC "+json.dumps(row),flush=True)
    assert len(rows)==16
    print("HOARE_NATIVE_GSE_GPMC_SUMMARY "+json.dumps({m:dict(records=sum(r["mode"]==m for r in rows),
        exact=sum(r["mode"]==m and r["coeff"] is not None for r in rows),
        no_match=sum(r["mode"]==m and r["status"]=="NO_GSE_MATCH" for r in rows),
        baseline_terminal=sum(r["mode"]==m and r["status"]=="BASELINE_TERMINAL" for r in rows)) for m in ("baseline","gse")}),flush=True)




def single_fibre_pack(base, phase, primary):
    """One MPZ query: independent deterministic aliases even for signed/constant bits."""
    header,*clauses=base.splitlines()
    p,kind,vs,cs=header.split()
    v,c=int(vs),int(cs)
    if (p,kind)!=("p","cnf") or len(clauses)!=c or not 0<=primary<=v:
        raise ValueError("invalid fibre CNF")
    if not 1<=len(phase)<=6 or any(not 0<abs(l)<=v for l in phase):
        raise ValueError("invalid phase bits")
    bound=1<<primary
    radix=bound+1
    weights=[]
    for i,l in enumerate(phase):
        a=v+i+1
        clauses.extend((f"{-a} {l} 0",f"{a} {-l} 0"))
        weights.extend((f"c p weight {a} {radix**(1<<i)} 0",f"c p weight {-a} 1 0"))
    return "\n".join(["c t wmc",f"p cnf {v+len(phase)} {len(clauses)}",*weights,*clauses])+"\n",radix,bound

def single_fibre_decode(value,radix,bound,d):
    if value<0 or radix!=bound+1 or d not in (2,4,8,16,32,64):
        raise ValueError("invalid packed fibre count")
    digits=[]
    for _ in range(d):
        value,digit=divmod(value,radix)
        digits.append(digit)
    if value or sum(digits)>bound:
        raise ValueError("packed fibre exceeds primary bound")
    return digits

def run_paper_single_fibre(directory,exe,tmp,conditioned=False):
    fields="key case x z kind route status primary vars clauses phase denominator scale build_ns rr_ns encoding_ns expected".split()
    with (directory/("paper-conditioned-fibre.tsv" if conditioned else "paper-single-fibre.tsv")).open() as f:
        plans=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    assert len(plans)==(6 if conditioned else 8)
    rows=[]
    # Each route gets its own equal 120 s solver-stage envelope, 30 s/query.
    # Alternate route order on successive probes, no oracle-driven stopping.
    spent=({"condition-first":0.0,"rr-first":0.0} if conditioned else {"fixed":0.0,"affine":0.0})
    for i in range(0,len(plans),2):
        pair=plans[i:i+2]
        if (i//2)%2:pair.reverse()
        for p in pair:
            r=dict(p);route=p["route"]
            for k in ("x","z","primary","vars","clauses","denominator","scale","build_ns","rr_ns","encoding_ns"):
                r[k]=int(p[k])
            assert r["x"]&16==0 and r["z"]&16==16
            r.update(digits=None,coefficients=None,verdict="UNKNOWN",metrics=[],query_s=0.0)
            if p["status"]=="READY":
                base=(directory/(p["key"]+".cnf")).read_text()
                assert base.splitlines()[0]==f'p cnf {r["vars"]} {r["clauses"]}'
                t=time.monotonic()
                data,radix,bound=single_fibre_pack(base,list(map(int,p["phase"].split(","))),r["primary"])
                r["pack_s"]=time.monotonic()-t
                r["base_sha256"]=hashlib.sha256(base.encode()).hexdigest()
                r["query_sha256"]=hashlib.sha256(data.encode()).hexdigest()
                query=pathlib.Path(tmp)/"single-fibre.cnf"
                query.write_text(data)
                t=time.monotonic()
                remaining=min(30,(90 if conditioned else 120)-spent[route])
                try:
                    if remaining<=0:raise TimeoutError("route budget")
                    out=profile_gpmc([str(exe),"-mode=1","-natw",str(query)],remaining,
                                     pathlib.Path(tmp)/"single-fibre-time.tsv",r["metrics"])
                    d=r["denominator"]
                    value=parse_gpmc_integer(out,"wmc",bound*radix**(d-1))
                    bins=single_fibre_decode(value,radix,bound,d)
                    coeff=[bins[j]-bins[j+d//2] for j in range(d//2)]
                    nonzero=any(coeff)
                    assert nonzero==(p["expected"]=="true"),(p["key"],coeff)
                    r.update(status="EXACT",digits=bins,coefficients=coeff,
                             verdict="REFUTED" if nonzero else "UNKNOWN",
                             fibre_status="NONZERO" if nonzero else "ZERO")
                except (TimeoutError,subprocess.TimeoutExpired):r["status"]="TIMEOUT"
                except SolverSignalKilled:r["status"]="SIGNAL_KILL"
                r["query_s"]=time.monotonic()-t
                spent[route]+=r["query_s"]
            rows.append(r)
            print(("HOARE_PAPER_CONDITIONED_GPMC " if conditioned else "HOARE_PAPER_SINGLE_GPMC ")+json.dumps(r),flush=True)
    for i in range(0,len(rows),2):
        a,b=rows[i:i+2]
        if a["digits"] is not None and b["digits"] is not None:
            if conditioned:
                assert any(a["coefficients"])==any(b["coefficients"]),(a["key"],b["key"])
                # RR may alter raw phase coefficients and normalization.
                na=sum(v*v for v in a["coefficients"])<<a["scale"]
                nb=sum(v*v for v in b["coefficients"])<<b["scale"]
                assert na==nb,(a["key"],b["key"],na,nb)
            else:
                assert a["digits"]==b["digits"],(a["key"],b["key"])
    print(("HOARE_PAPER_CONDITIONED_GPMC_SUMMARY " if conditioned else "HOARE_PAPER_SINGLE_GPMC_SUMMARY ")+json.dumps(dict(
        records=len(rows),exact=sum(r["digits"] is not None for r in rows),
        blind_nonzero=sum(r["verdict"]=="REFUTED" and r["kind"]=="blind" for r in rows),
        oracle_control_nonzero=sum(r["verdict"]=="REFUTED" and r["kind"]=="oracle-control" for r in rows),
        spent_s=spent)),flush=True)

def run_paper_projected_optimized(directory,count,deadline,metrics):
    fields="case mode n h0 h scale vars clauses sign denominator status build_ns rr_ns encoding_ns expected_bad".split()
    with (directory/"paper-projected.tsv").open() as f:
        plans={(p["case"],p["mode"]):p for p in csv.DictReader(f,fieldnames=fields,delimiter="\t")}
    assert len(plans)==8
    rows=[]
    # Preserve old six-route evidence; rerun only matched specialized
    # residuals. Fixed x=0 is a deterministic first legal assignment,
    # not a witness selected from the reference result.
    for name,scope in [("vchain","root"),("noancilla","first-input"),("noancilla","root")]:
        modes=["hybrid-pre","hybrid-pre-heap"]
        if scope=="first-input":modes.reverse()
        for mode in modes:
            p=plans[name,mode]
            r=dict(case=name,mode=mode,scope=scope,status=p["status"],
                **{k:int(p[k]) for k in ("n","h0","h","scale","vars","clauses","sign","denominator","build_ns","rr_ns","encoding_ns")})
            r.update(projected_count=None,query_s=0.0,verdict="UNKNOWN",witness=None,metrics=[])
            if r["status"]=="READY" and time.monotonic()<deadline:
                base=(directory/f"paper-{name}-{mode}.cnf").read_bytes()
                r["cnf_sha256"]=hashlib.sha256(base).hexdigest()
                primary=r["n"]+2*r["h"]
                prefix=[-(j+2) for j in range(r["n"])] if scope=="first-input" else []
                metrics.clear();start=time.monotonic()
                try:
                    v,radix=count(base.decode(),prefix,r["sign"],min(deadline,start+30),primary=primary)
                    a,b=v%radix,v//radix
                    assert a+b<=1<<primary and a>=b
                    value=a-b;r["projected_count"]=str(value);r["status"]="EXACT"
                    if scope=="first-input":
                        if value:r.update(verdict="REFUTED",witness=0)
                        else:r["status"]="CONDITIONED_ZERO_ONLY"
                    elif value:
                        r["status"]="POSITIVE_ROOT"
                    else:r["verdict"]="PROVED"
                    # Only consult source reference after the query.
                    assert bool(value)==(p["expected_bad"]=="true"),(name,mode,scope,value)
                except (TimeoutError,subprocess.TimeoutExpired):r["status"]="TIMEOUT"
                except SolverSignalKilled:r["status"]="SIGNAL_KILL"
                r["query_s"]=time.monotonic()-start;r["metrics"]=[dict(m) for m in metrics]
            elif r["status"]=="READY":r["status"]="GLOBAL_BUDGET_NOT_RUN"
            rows.append(r)
            print("HOARE_PAPER_HEAP_GPMC "+json.dumps(r),flush=True)
    for name,scope in {(r["case"],r["scope"]) for r in rows}:
        paired=[r for r in rows if r["case"]==name and r["scope"]==scope and r["projected_count"] is not None]
        if len(paired)==2:assert paired[0]["projected_count"]==paired[1]["projected_count"]
    print("HOARE_PAPER_HEAP_GPMC_SUMMARY "+json.dumps(dict(records=len(rows),
        exact=sum(r["projected_count"] is not None for r in rows),
        proved=sum(r["verdict"]=="PROVED" for r in rows),refuted=sum(r["verdict"]=="REFUTED" for r in rows))),flush=True)

def run_paper_projected(directory,count,deadline,metrics):
    fields="case mode n h0 h scale vars clauses sign denominator status build_ns rr_ns encoding_ns expected_bad".split()
    with (directory/"paper-projected.tsv").open() as f:
        plans=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    assert len(plans)==6
    # First the bounded reference-positive v-chain; reverse ordering
    # across families, no repeated timing or result-driven case removal.
    order={"vchain":0,"noancilla":1}
    plans.sort(key=lambda p:(order[p["case"]],({"pure":0,"hybrid":1,"hybrid-pre":2} if p["case"]=="vchain" else {"hybrid":0,"hybrid-pre":1,"pure":2})[p["mode"]]))
    rows=[]
    for p in plans:
        r=dict(case=p["case"],mode=p["mode"],status=p["status"],expected_bad=p["expected_bad"]=="true",
            **{k:int(p[k]) for k in ("n","h0","h","scale","vars","clauses","sign","denominator","build_ns","rr_ns","encoding_ns")})
        r.update(root=None,root_s=0.0,witness_s=0.0,witness=None,root_queries=0,witness_queries=0,verdict="UNKNOWN",metrics=[])
        if r["status"]=="READY" and time.monotonic()<deadline:
            base=(directory/f"paper-{r['case']}-{r['mode']}.cnf").read_bytes()
            r["cnf_sha256"]=hashlib.sha256(base).hexdigest()
            primary=r["n"]+2*r["h"]
            def signed(prefix,end):
                v,radix=count(base.decode(),prefix,r["sign"],end,primary=primary)
                a,b=v%radix,v//radix
                if a+b>1<<primary or a<b:raise ValueError("invalid projected count")
                return a-b
            metrics.clear()
            start=time.monotonic()
            try:
                r["root_queries"]+=1
                root=signed([],min(deadline,start+30))
                r["root"]=str(root)
                assert bool(root)==r["expected_bad"],(r["case"],r["mode"],root)
                r["status"]="EXACT_ROOT"
                if not root:r["verdict"]="PROVED"
            except (TimeoutError,subprocess.TimeoutExpired):r["status"]="ROOT_TIMEOUT"
            except SolverSignalKilled:r["status"]="ROOT_SIGNAL_KILL"
            r["root_s"]=time.monotonic()-start
            if r["status"]=="EXACT_ROOT" and root:
                start=time.monotonic();end=min(deadline,start+30)
                # q4 fixed zero by original property; choose data bits
                # using nonnegative conditioned counts, not oracle answers.
                prefix=[-6];x=0
                try:
                    for j in range(4):
                        lit=j+2;r["witness_queries"]+=1
                        if signed(prefix+[-lit],end):prefix.append(-lit)
                        else:prefix.append(lit);x|=1<<j
                    r["witness_queries"]+=1
                    assert signed(prefix,end)>0
                    assert 0<=x<16
                    r.update(witness=x,verdict="REFUTED",status="EXACT_ROOT_WITNESS")
                except (TimeoutError,subprocess.TimeoutExpired):r["status"]="POSITIVE_ROOT_WITNESS_TIMEOUT"
                except SolverSignalKilled:r["status"]="POSITIVE_ROOT_WITNESS_SIGNAL_KILL"
                r["witness_s"]=time.monotonic()-start
            r["metrics"]=[dict(m) for m in metrics]
        elif r["status"]=="READY":r["status"]="GLOBAL_BUDGET_NOT_RUN"
        rows.append(r)
        print("HOARE_PAPER_PROJECTED_GPMC "+json.dumps(r),flush=True)
    print("HOARE_PAPER_PROJECTED_GPMC_SUMMARY "+json.dumps(dict(records=len(rows),
        roots=sum(r["root"] is not None for r in rows),verdicts=sum(r["verdict"]!="UNKNOWN" for r in rows))),flush=True)

def run_residual_hybrid(directory,solve,deadline,direct_rows):
    direct={r["case"]:r for r in direct_rows}
    rows=[]
    with (directory/"residual.tsv").open() as f:
        for name,mode,n,h0,h,scale,hits,trials,guard_terms,variables,clauses,delta,status,witness,prep_us,encoding_us,reason,expected,witnesses,retained,representation,sat_queries,sat_visits,sat_us,sat_added,sat_reason in csv.reader(f,delimiter="\t"):
            n,h0,h,scale,hits,trials,guard_terms,variables,clauses,prep_us,encoding_us=map(int,(n,h0,h,scale,hits,trials,guard_terms,variables,clauses,prep_us,encoding_us))
            if status=="READY":
                end=min(deadline,time.monotonic()+5)
                row=pure_wmc_decision((directory/f"residual-{name}-{mode}.cnf").read_text(),
                    list(map(int,delta.split(","))),n,solve,end)
                for key in ("coeff","witness_coeff"):
                    if row.get(key) is not None:
                        row[key]=tuple(v*(1<<scale) for v in row[key])
                route="GUARDED_RESIDUAL" if int(retained)>0 else "NATIVE_RR_RESIDUAL"
            else:
                row=dict(verdict=status if status in ("PROVED","REFUTED") else "UNKNOWN",
                    reason=reason,coeff=None,witness=None if witness=="-" else int(witness),
                    witness_status="VERIFIED" if witness!="-" else "NOT_REQUIRED" if status=="PROVED" else "NOT_RUN",
                    root_queries=0,witness_queries=0,root_s=0.0,witness_s=0.0)
                route="RR_TERMINAL" if status in ("PROVED","REFUTED") else status
            target=tuple(map(int,expected.split(",")))
            legal=set() if witnesses=="-" else set(map(int,witnesses.split(",")))
            if row["verdict"]!="UNKNOWN":
                assert row["verdict"]==("REFUTED" if any(target) else "PROVED"),(name,mode,row)
            if row["coeff"] is not None:
                assert row["coeff"]==target,(name,mode,row,target)
            if row["witness_status"]=="VERIFIED":
                assert row["witness"] in legal,(name,mode,row)
            row.update(case=name,mode=mode,route=route,initial_h=h0,residual_h=h,scale2=scale,
                hits=hits,trials=trials,retained_hits=int(retained),representation=representation,guard_terms=guard_terms,vars=variables,clauses=clauses,
                prep_us=prep_us,encoding_us=encoding_us,sat_queries=int(sat_queries),sat_visits=int(sat_visits),sat_us=int(sat_us),sat_added=int(sat_added),sat_reason=sat_reason,
                decision_total_s=direct[name]["build_us"]/1e6+(prep_us+encoding_us+int(sat_us))/1e6+row["root_s"],
                direct_decision_s=direct[name]["decision_total_s"])
            rows.append(row)
            print("HOARE_RESIDUAL_HYBRID "+json.dumps(row),flush=True)
    assert len(rows)==64
    summary={}
    for mode in ("standard","property","adaptive","sat-assisted"):
        rs=[r for r in rows if r["mode"]==mode]
        summary[mode]=dict(cases=len(rs),decided=sum(r["verdict"]!="UNKNOWN" for r in rs),
            rr_terminal=sum(r["route"]=="RR_TERMINAL" for r in rs),
            count_routes=sum(r["root_queries"]>0 for r in rs),
            reduced_count_routes=sum(r["root_queries"]>0 and (r["residual_h"]<r["initial_h"] or r["retained_hits"]>0) for r in rs),
            partial_guard_count_routes=sum(r["root_queries"]>0 and r["retained_hits"]>0 for r in rs),
            rejected_growth=sum(r["representation"]=="native-reject-growth" for r in rs),
            retained_hits=sum(r["retained_hits"] for r in rs),
            sat_proofs=sum(r["representation"]=="sat-proof" for r in rs),
            sat_queries=sum(r["sat_queries"] for r in rs),
            sat_visits=sum(r["sat_visits"] for r in rs),
            sat_us=sum(r["sat_us"] for r in rs),
            sat_added=sum(r["sat_added"] for r in rs),
            witnesses=sum(r["witness_status"]=="VERIFIED" for r in rs),
            root_batches=sum(r["root_queries"] for r in rs),
            decision_total_s=sum(r["decision_total_s"] for r in rs))
    print("HOARE_RESIDUAL_HYBRID_SUMMARY "+json.dumps(summary),flush=True)




def run_scale_discovery(directory,solve,deadline):
    """Root-only difficulty discovery. Fixed ladder, rotated route order."""
    direct_fields="case n h gates vars clauses delta status build_us encoding_us oracle_us expected witnesses".split()
    residual_fields="case mode n h0 h scale hits trials guard_terms vars clauses delta status witness prep_us encoding_us reason expected witnesses retained representation sat_queries sat_visits sat_us sat_added sat_reason".split()
    with (directory/"direct.tsv").open() as f:
        direct=list(csv.DictReader(f,fieldnames=direct_fields,delimiter="\t"))
    with (directory/"residual.tsv").open() as f:
        residual=list(csv.DictReader(f,fieldnames=residual_fields,delimiter="\t"))
    assert len(direct)==9 and len(residual)==36
    rows=[]
    for i,base in enumerate(direct):
        name=base["case"]
        candidates=[dict(base,mode="direct",scale="0",prep_us="0",sat_us="0",
                         retained="0",representation="original",witness="-")]
        candidates.extend(r for r in residual if r["case"]==name)
        assert len(candidates)==5
        k=i%5
        for order,r in enumerate(candidates[k:]+candidates[:k]):
            target=tuple(map(int,base["expected"].split(",")))
            assert r["expected"]==base["expected"]
            result=dict(case=name,mode=r["mode"],order=order,n=int(base["n"]),
                initial_h=int(base["h"]),residual_h=int(r["h"]),gates=int(base["gates"]),
                vars=int(r["vars"]),clauses=int(r["clauses"]),representation=r["representation"],
                retained=int(r["retained"]),root_s=0.0,root_batches=0,coeff=None,
                build_us=int(base["build_us"]),prep_us=int(r["prep_us"]),
                encoding_us=int(r["encoding_us"]),sat_us=int(r["sat_us"]),
                oracle_us=int(base["oracle_us"]),status=r["status"],verdict="UNKNOWN")
            if r["status"] in ("PROVED","REFUTED"):
                result["verdict"]=r["status"]
                if r["status"]=="REFUTED":
                    assert r["witness"]=="0"
            elif r["status"]=="READY":
                start=time.monotonic()
                end=min(deadline,start+30)
                if end>start:
                    result["root_batches"]=1
                    file=directory/(f"direct-{name}.cnf" if r["mode"]=="direct" else f"residual-{name}-{r['mode']}.cnf")
                    try:
                        coeff=tuple(solve(file.read_text(),list(map(int,r["delta"].split(","))),[],end))
                        if any(coeff) and not positive_surd(coeff):
                            raise ValueError("negative scale leakage")
                        coeff=tuple(v*(1<<int(r["scale"])) for v in coeff)
                        assert coeff==target,(name,r["mode"],coeff,target)
                        result.update(coeff=coeff,verdict="REFUTED" if any(coeff) else "PROVED",status="EXACT_ROOT")
                    except (TimeoutError,subprocess.TimeoutExpired):
                        result["status"]="ROOT_TIMEOUT"
                else:
                    result["status"]="GLOBAL_BUDGET_NOT_RUN"
                result["root_s"]=time.monotonic()-start
            if result["verdict"]!="UNKNOWN":
                assert result["verdict"]==("REFUTED" if any(target) else "PROVED")
            result["decision_total_s"]=result["root_s"]+sum(result[x] for x in ("build_us","prep_us","encoding_us","sat_us"))/1e6
            rows.append(result)
            print("HOARE_SCALE_DISCOVERY "+json.dumps(result),flush=True)
    assert len(rows)==45
    modes={}
    for mode in ("direct","standard","property","adaptive","sat-assisted"):
        rs=[r for r in rows if r["mode"]==mode]
        modes[mode]=dict(cases=len(rs),decided=sum(r["verdict"]!="UNKNOWN" for r in rs),
            timeouts=sum(r["status"]=="ROOT_TIMEOUT" for r in rs),
            encoding_or_reduction_unknown=sum(r["status"] in ("UNKNOWN_ENCODING_LIMIT","UNKNOWN_REDUCTION_LIMIT") for r in rs),
            global_not_run=sum(r["status"]=="GLOBAL_BUDGET_NOT_RUN" for r in rs),
            root_batches=sum(r["root_batches"] for r in rs),
            completed_over_1s=sum(r["status"]=="EXACT_ROOT" and r["root_s"]>=1 for r in rs),
            observed_over_10s=sum(r["root_s"]>=10 for r in rs))
    hard=sorted({r["case"] for r in rows if r["root_s"]>=1 or r["status"]=="ROOT_TIMEOUT"})
    print("HOARE_SCALE_DISCOVERY_SUMMARY "+json.dumps(dict(modes=modes,hard_candidates=hard,cap_s=30,repeat=1)),flush=True)




class SolverSignalKilled(RuntimeError):
    pass


def profile_gpmc(args, seconds, metrics_path, records):
    """GNU time around a single bounded solver subprocess, including timeout.
    RSS is the reported maximum for this invocation, not Python/CNF memory.
    A verbose GNU timeout signal receipt distinguishes timer escalation
    from an unattributed SIGKILL. Neither produces a quantum verdict.
    """
    metrics_path.unlink(missing_ok=True)
    cmd=["/usr/bin/time","-q","-f","%U\t%S\t%M","-o",str(metrics_path),
         "timeout","--verbose","--foreground","--signal=TERM","--kill-after=1s",f"{seconds:.6f}s",
         *args]
    start=time.monotonic()
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       text=True,start_new_session=True,env=dict(os.environ,LC_ALL="C"))
    outer=False
    try:
        stdout,stderr=p.communicate(timeout=seconds+3)
    except subprocess.TimeoutExpired:
        outer=True
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        stdout,stderr=p.communicate()
    row=dict(wall_s=time.monotonic()-start,exit=p.returncode,
             user_s=None,system_s=None,max_rss_kib=None,status="EXIT")
    if metrics_path.is_file():
        parts=metrics_path.read_text().strip().split("\t")
        if len(parts)==3:
            row.update(user_s=float(parts[0]),system_s=float(parts[1]),max_rss_kib=int(parts[2]))
    notices=[l for l in stderr.splitlines() if re.match(r"^timeout: sending signal (TERM|KILL) to command ",l)]
    row.update(timer_notices=notices,outer_deadline=outer,stderr_tail=stderr[-1000:])
    expired=bool(notices) and row["wall_s"]>=max(0,seconds-.1)
    if outer or (expired and p.returncode in (124,137,-9)):
        row["status"]="TIMEOUT"
        records.append(row)
        raise TimeoutError("profiled GPMC root deadline")
    if p.returncode in (137,-9):
        row["status"]="UNATTRIBUTED_SIGNAL_KILL"
        records.append(row)
        raise SolverSignalKilled("SIGKILL without timer receipt; OOM not established")
    if p.returncode:
        row["status"]="SOLVER_ERROR"
        records.append(row)
        raise subprocess.CalledProcessError(p.returncode,cmd,stdout,stderr)
    row["status"]="COMPLETED"
    records.append(row)
    return stdout


def run_scale_long(directory,solve,deadline,metrics):
    """Frozen R25A representative cohort; repeated solver-only observations.
    Source/preparation is regenerated once and reported separately, not
    falsely treated as independently repeated pipeline timing.
    """
    df="case n h gates vars clauses delta status build_us encoding_us oracle_us expected witnesses".split()
    rf="case mode n h0 h scale hits trials guard_terms vars clauses delta status witness prep_us encoding_us reason expected witnesses retained representation sat_queries sat_visits sat_us sat_added sat_reason".split()
    with (directory/"direct.tsv").open() as f:
        direct={r["case"]:r for r in csv.DictReader(f,fieldnames=df,delimiter="\t")}
    with (directory/"residual.tsv").open() as f:
        residual={(r["case"],r["mode"]):r for r in csv.DictReader(f,fieldnames=rf,delimiter="\t")}
    assert len(direct)==9 and len(residual)==36
    short=("uncompute-8-safe","uncompute-10-mutant","mixing-10-3layer")
    modes=("direct","standard","sat-assisted")
    schedule=[]
    for rep in range(2):
        cases=short if rep==0 else tuple(reversed(short))
        for name in cases:
            i=short.index(name)
            order=modes[i:]+modes[:i]
            if rep:order=tuple(reversed(order))
            schedule.extend((name,mode,rep,60,j) for j,mode in enumerate(order))
    schedule.extend(("uncompute-12-safe",mode,0,200,j) for j,mode in enumerate(("standard","direct","sat-assisted")))
    assert len(schedule)==21 and sum(cap for _,_,_,cap,_ in schedule)==1680
    rows=[]
    for name,mode,rep,cap,order in schedule:
        base=direct[name]
        r=dict(base,mode="direct",scale="0",prep_us="0",sat_us="0",retained="0",
               representation="original",witness="-") if mode=="direct" else residual[(name,mode)]
        target=tuple(map(int,base["expected"].split(",")))
        assert r["expected"]==base["expected"]
        source=(directory/f"quokka-{name}.tsv").read_bytes()
        row=dict(case=name,mode=mode,rep=rep,cap_s=cap,order=order,n=int(base["n"]),
                 initial_h=int(base["h"]),residual_h=int(r["h"]),gates=int(base["gates"]),
                 vars=int(r["vars"]),clauses=int(r["clauses"]),scale=int(r["scale"]),
                 expected_raw=target,source_sha256=hashlib.sha256(source).hexdigest(),
                 representation=r["representation"],retained=int(r["retained"]),
                 status=r["status"],verdict="UNKNOWN",coeff=None,root_s=0.0,
                 root_batches=0,cnf_sha256=None,delta=r["delta"],
                 build_us=int(base["build_us"]),prep_us=int(r["prep_us"]),
                 encoding_us=int(r["encoding_us"]),sat_us=int(r["sat_us"]),
                 oracle_us=int(base["oracle_us"]))
        metrics.clear()
        if r["status"] in ("PROVED","REFUTED"):
            row["verdict"]=r["status"]
            if r["status"]=="REFUTED":assert r["witness"]=="0"
        elif r["status"]=="READY":
            file=directory/(f"direct-{name}.cnf" if mode=="direct" else f"residual-{name}-{mode}.cnf")
            data=file.read_bytes()
            row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
            start=time.monotonic()
            end=min(deadline,start+cap)
            if end<=start:
                row["status"]="GLOBAL_BUDGET_NOT_RUN"
            else:
                row["root_batches"]=1
                try:
                    coeff=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                    if any(coeff) and not positive_surd(coeff):raise ValueError("negative scale leakage")
                    coeff=tuple(v*(1<<row["scale"]) for v in coeff)
                    assert coeff==target,(name,mode,coeff,target)
                    row.update(coeff=coeff,verdict="REFUTED" if any(coeff) else "PROVED",status="EXACT_ROOT")
                except (TimeoutError,subprocess.TimeoutExpired):
                    row["status"]="ROOT_TIMEOUT"
                except SolverSignalKilled:
                    row["status"]="ROOT_SIGNAL_KILL"
                row["root_s"]=time.monotonic()-start
        if row["verdict"]!="UNKNOWN":
            assert row["verdict"]==("REFUTED" if any(target) else "PROVED")
        row["queries"]=[dict(m) for m in metrics]
        row["cpu_s"]=sum(m["user_s"]+m["system_s"] for m in metrics) if metrics and all(m["user_s"] is not None for m in metrics) else None
        row["max_rss_kib"]=max(m["max_rss_kib"] for m in metrics) if metrics and all(m["max_rss_kib"] is not None for m in metrics) else None
        row["prep_proxy_s"]=sum(row[x] for x in ("build_us","prep_us","encoding_us","sat_us"))/1e6
        row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
        rows.append(row)
        print("HOARE_SCALE_LONG "+json.dumps(row),flush=True)
    summary={}
    for cap in (60,200):
        summary[str(cap)]={}
        for mode in modes:
            rs=[r for r in rows if r["cap_s"]==cap and r["mode"]==mode]
            summary[str(cap)][mode]=dict(attempts=len(rs),decided=sum(r["verdict"]!="UNKNOWN" for r in rs),
                timeouts=sum(r["status"]=="ROOT_TIMEOUT" for r in rs),
                not_run=sum(r["status"]=="GLOBAL_BUDGET_NOT_RUN" for r in rs),
                signal_kills=sum(r["status"]=="ROOT_SIGNAL_KILL" for r in rs),
                completed_root_s=[r["root_s"] for r in rs if r["status"]=="EXACT_ROOT"],
                terminal=sum(r["root_batches"]==0 and r["verdict"]!="UNKNOWN" for r in rs))
    print("HOARE_SCALE_LONG_SUMMARY "+json.dumps(dict(summary=summary,attempts=len(rows),
          frozen_discovery_head="1bc06be95734f54c0ba229b4c9560ec19cb6de32",
          repeated_scope="solver-only",backend="gpmc-mpz-packed")),flush=True)




def profile_contract_tests(tmp,metrics):
    path=tmp/"profile-contract.tsv"
    for program,expected in (
        ("import time; time.sleep(10)","TIMEOUT"),
        ("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)","TIMEOUT"),
        ("import os,signal; os.kill(os.getpid(),signal.SIGKILL)","UNATTRIBUTED_SIGNAL_KILL"),
    ):
        metrics.clear()
        try:
            profile_gpmc([sys.executable,"-c",program],.4,path,metrics)
        except (TimeoutError,SolverSignalKilled):
            assert len(metrics)==1 and metrics[0]["status"]==expected,metrics
        else:
            raise AssertionError("resource contract expected termination")
        print("HOARE_RESOURCE_CONTRACT "+json.dumps(metrics[0]),flush=True)
    metrics.clear()


def run_cone_pilot(directory,solve,deadline,metrics):
    """Three property-cone cases, direct controls for the two larger sizes.
    Mixing10 direct is already repeated in the preceding long cohort."""
    fields="case h hr gates gr scale vars clauses delta status cone_us build_us encoding_us expected".split()
    df="case n h gates vars clauses delta status build_us encoding_us oracle_us expected witnesses".split()
    with (directory/"cone.tsv").open() as f:
        cones=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    with (directory/"direct.tsv").open() as f:
        direct={r["case"]:r for r in csv.DictReader(f,fieldnames=df,delimiter="\t")}
    assert len(cones)==3
    rows=[]
    for i,c in enumerate(cones):
        name=c["case"]
        base=direct[name]
        assert c["expected"]==base["expected"]
        b=dict(base,hr=base["h"],gr=base["gates"],scale="0",cone_us="0")
        cases=[("cone",c)] if i==0 else ([("direct",b),("cone",c)] if i%2 else [("cone",c),("direct",b)])
        for mode,r in cases:
            metrics.clear()
            target=tuple(map(int,base["expected"].split(",")))
            row=dict(case=name,mode=mode,n=int(base["n"]),h=int(r["h"]),hr=int(r["hr"]),
                gates=int(r["gates"]),gr=int(r["gr"]),scale=int(r["scale"]),
                vars=int(r["vars"]),clauses=int(r["clauses"]),cone_us=int(r["cone_us"]),
                build_us=int(r["build_us"]),encoding_us=int(r["encoding_us"]),
                expected_raw=target,coeff=None,status=r["status"],verdict="UNKNOWN",root_s=0.0,
                cnf_sha256=None,source_sha256=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest())
            if r["status"]=="READY":
                data=(directory/f"{mode}-{name}.cnf").read_bytes()
                row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                start=time.monotonic();end=min(deadline,start+60)
                if end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                else:
                    try:
                        raw=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                        if any(raw) and not positive_surd(raw):raise ValueError("negative cone leakage")
                        coeff=tuple(v*(1<<row["scale"]) for v in raw)
                        assert coeff==target,(name,mode,coeff,target)
                        row.update(status="EXACT_ROOT",verdict="REFUTED" if any(coeff) else "PROVED",coeff=coeff)
                    except (TimeoutError,subprocess.TimeoutExpired):
                        row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:
                        row["status"]="ROOT_SIGNAL_KILL"
                row["root_s"]=time.monotonic()-start
            row["queries"]=[dict(m) for m in metrics]
            row["cpu_s"]=sum(m["user_s"]+m["system_s"] for m in metrics) if metrics and all(m["user_s"] is not None for m in metrics) else None
            row["max_rss_kib"]=max(m["max_rss_kib"] for m in metrics) if metrics and all(m["max_rss_kib"] is not None for m in metrics) else None
            row["decision_proxy_s"]=row["root_s"]+sum(row[k] for k in ("cone_us","build_us","encoding_us"))/1e6
            rows.append(row)
            print("HOARE_CONE_PILOT "+json.dumps(row),flush=True)
    assert len(rows)==5
    print("HOARE_CONE_PILOT_SUMMARY "+json.dumps(dict(cases=3,routes=5,cap_s=60,
          cone_decided=sum(r["mode"]=="cone" and r["verdict"]!="UNKNOWN" for r in rows),
          direct_decided=sum(r["mode"]=="direct" and r["verdict"]!="UNKNOWN" for r in rows))),flush=True)




def run_quotient_pilot(directory,solve,deadline,metrics):
    """Matched same-run cone vs quotient; two reversed repeats at 60s
    for 10q and 13q, single 120s attempt each at 15q."""
    fields="case h hr gates gr scale vars clauses delta status cone_us build_us encoding_us expected".split()
    def read(name,extra):
        with (directory/name).open() as f:
            return {r["case"]:r for r in csv.DictReader(f,fieldnames=fields+extra,delimiter="\t")}
    cone=read("cone.tsv",[]); quotient=read("quotient.tsv",["primary","phase_terms"])
    assert set(cone)==set(quotient) and len(cone)==3
    rows=[]
    for name in sorted(cone):
        cap=120 if name.startswith("mixing-15") else 60
        for rep in range(1 if cap==120 else 2):
            order=("cone","quotient") if rep==0 else ("quotient","cone")
            for mode in order:
                r=(cone if mode=="cone" else quotient)[name]
                target=tuple(map(int,cone[name]["expected"].split(",")))
                assert r["expected"]==cone[name]["expected"]
                row=dict(case=name,mode=mode,rep=rep,cap_s=cap,h=int(r["h"]),hr=int(r["hr"]),
                    vars=int(r["vars"]),clauses=int(r["clauses"]),scale=int(r["scale"]),
                    primary=int(r["primary"]) if "primary" in r else None,
                    phase_terms=int(r["phase_terms"]) if "phase_terms" in r else None,
                    expected_raw=target,coeff=None,status=r["status"],verdict="UNKNOWN",root_s=0.0,
                    cnf_sha256=None,source_sha256=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest())
                metrics.clear()
                if r["status"]=="READY":
                    data=(directory/f"{mode}-{name}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                    start=time.monotonic();end=min(deadline,start+cap)
                    if end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                    else:
                        try:
                            coeff=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                            if any(coeff) and not positive_surd(coeff):raise ValueError("negative quotient leakage")
                            coeff=tuple(v*(1<<row["scale"]) for v in coeff)
                            assert coeff==target,(name,mode,coeff,target)
                            row.update(status="EXACT_ROOT",verdict="REFUTED" if any(coeff) else "PROVED",coeff=coeff)
                        except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                        except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                    row["root_s"]=time.monotonic()-start
                row["queries"]=[dict(m) for m in metrics]
                row["cpu_s"]=sum(m["user_s"]+m["system_s"] for m in metrics) if metrics and all(m["user_s"] is not None for m in metrics) else None
                row["max_rss_kib"]=max(m["max_rss_kib"] for m in metrics) if metrics and all(m["max_rss_kib"] is not None for m in metrics) else None
                row["prep_proxy_s"]=sum(int(r[k]) for k in ("cone_us","build_us","encoding_us"))/1e6
                row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
                rows.append(row)
                print("HOARE_QUOTIENT_PILOT "+json.dumps(row),flush=True)
    assert len(rows)==10
    print("HOARE_QUOTIENT_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        mode:dict(decided=sum(r["mode"]==mode and r["verdict"]!="UNKNOWN" for r in rows),
        timeouts=sum(r["mode"]==mode and r["status"]=="ROOT_TIMEOUT" for r in rows))
        for mode in ("cone","quotient")})),flush=True)




def run_affine_pilot(directory,solve,deadline,metrics):
    fields="case mode h hr scale vars clauses primary phase_terms delta status cone_us build_us encoding_us expected".split()
    with (directory/"affine.tsv").open() as f:
        plans={(r["case"],r["mode"]):r for r in csv.DictReader(f,fieldnames=fields,delimiter="\t")}
    assert len(plans)==6
    rows=[]
    for name in sorted({name for name,_ in plans}):
        cap=120 if name.endswith("-15") else 60
        for rep in range(1 if cap==120 else 2):
            for mode in (("cone","affine") if rep==0 else ("affine","cone")):
                r=plans[(name,mode)]
                target=tuple(map(int,r["expected"].split(",")))
                assert r["expected"]==plans[(name,"cone")]["expected"]
                row=dict(case=name,mode=mode,rep=rep,cap_s=cap,
                    **{k:int(r[k]) for k in ("h","hr","scale","vars","clauses","primary","phase_terms")},
                    expected_raw=target,coeff=None,status=r["status"],verdict="UNKNOWN",root_s=0.0,
                    cnf_sha256=None,source_sha256=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest())
                metrics.clear()
                if r["status"]=="READY":
                    data=(directory/f"{mode}-{name}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                    start=time.monotonic();end=min(deadline,start+cap)
                    if end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                    else:
                        try:
                            coeff=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                            if any(coeff) and not positive_surd(coeff):raise ValueError("negative affine leakage")
                            coeff=tuple(v*(1<<row["scale"]) for v in coeff)
                            assert coeff==target,(name,mode,coeff,target)
                            row.update(status="EXACT_ROOT",verdict="REFUTED" if any(coeff) else "PROVED",coeff=coeff)
                        except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                        except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                    row["root_s"]=time.monotonic()-start
                row["queries"]=[dict(m) for m in metrics]
                row["cpu_s"]=sum(m["user_s"]+m["system_s"] for m in metrics) if metrics and all(m["user_s"] is not None for m in metrics) else None
                row["max_rss_kib"]=max(m["max_rss_kib"] for m in metrics) if metrics and all(m["max_rss_kib"] is not None for m in metrics) else None
                row["prep_proxy_s"]=sum(int(r[k]) for k in ("cone_us","build_us","encoding_us"))/1e6
                row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
                rows.append(row)
                print("HOARE_AFFINE_PILOT "+json.dumps(row),flush=True)
    assert len(rows)==10
    print("HOARE_AFFINE_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        mode:dict(decided=sum(r["mode"]==mode and r["verdict"]!="UNKNOWN" for r in rows),
        timeouts=sum(r["mode"]==mode and r["status"]=="ROOT_TIMEOUT" for r in rows))
        for mode in ("cone","affine")})),flush=True)




# Exact Z[w] (w^4=-1), with no float arithmetic in the sum.
RZERO=(0,0,0,0)
RONE=(1,0,0,0)
ROOTS=tuple(tuple((1 if j<4 else -1) if i==j%4 else 0 for i in range(4)) for j in range(8))


def radd(a,b):
    return tuple(x+y for x,y in zip(a,b))


def rmul(a,b):
    if a==RZERO or b==RZERO:return RZERO
    if a==RONE:return b
    if b==RONE:return a
    if not any(a[1:]):return tuple(a[0]*x for x in b)
    if not any(b[1:]):return tuple(b[0]*x for x in a)
    x,y,z,t=a;u,v,w,s=b
    return (x*u-y*s-z*w-t*v,x*v+y*u-z*s-t*w,
            x*w+y*v+z*u-t*s,x*s+y*w+z*v+t*u)


def mask_positions(m):
    return tuple(i for i in range(m.bit_length()) if m>>i&1)


def projection(outer,inner):
    """Index of an outer assignment in the ordered inner scope."""
    index=[0]
    pos={v:i for i,v in enumerate(inner)}
    for v in outer:
        b=1<<pos[v] if v in pos else 0
        index.extend([x|b for x in index])
    return index


class FactorLimit(Exception):
    pass


def factor_sum(primary,terms,deadline,max_width=16,max_work=4_000_000,max_live=524288,streamed=False,order=None):
    """Bounded exact variable elimination; return a ring element or UNKNOWN.
    The graph is built from affine-product scopes before any CNF construction.
    Work counts table-entry operations conservatively, not CPU instructions.
    """
    stats=dict(work=0,width=0,peak_entries=0,eliminated=0,isolated=0,components=0,streamed=streamed,peak_index_entries=0)
    factors=[]
    active=set(range(primary))
    if order is not None:assert sorted(order)==list(range(primary))
    constant=RONE
    def charge(w):
        stats["work"]+=w
        if stats["work"]>max_work or time.monotonic()>=deadline:
            raise FactorLimit("work-or-time")
    def admit(scope,live):
        stats["width"]=max(stats["width"],len(scope))
        if len(scope)>max_width:raise FactorLimit("width")
        size=1<<len(scope)
        stats["peak_entries"]=max(stats["peak_entries"],live+size)
        if live+size>max_live:raise FactorLimit("live-entries")
        return size
    try:
        grouped={}
        for k,forms in terms:
            scope=0
            assert 0<=k<8
            for m,b in forms:
                assert m>>primary==0 and b in (0,1)
                scope|=m
            grouped.setdefault(scope,[]).append((k,forms))
        # Connected components are descriptive; disjoint components
        # contract independently under the same bucket elimination loop.
        unseen=set(active)
        scopes=[set(mask_positions(m)) for m in grouped]
        while unseen:
            comp={min(unseen)}
            while True:
                nxt=comp.union(*(s for s in scopes if s&comp))
                if nxt==comp:break
                comp=nxt
            unseen-=comp
            stats["components"]+=1
        live=0
        for mask,group in sorted(grouped.items()):
            scope=mask_positions(mask)
            size=admit(scope,live)
            charge(size*max(1,sum(len(fs)+1 for _,fs in group)))
            local={v:i for i,v in enumerate(scope)}
            packed=[(k,[(sum(1<<local[v] for v in mask_positions(m)),b) for m,b in fs]) for k,fs in group]
            tab=[]
            for a in range(size):
                if a%1024==0:charge(0)
                exponent=sum(k for k,fs in packed if all(((a&m).bit_count()&1)^b for m,b in fs))%8
                tab.append(ROOTS[exponent])
            if not scope:constant=rmul(constant,tab[0])
            else:factors.append((scope,tab));live+=size
        while active:
            if constant==RZERO:return RZERO,stats,"EXACT_ZERO"
            # Minimum union width, then number of factors, then stable ID.
            def candidate(v):
                fs=[f for f in factors if v in f[0]]
                union=set().union(*(set(s) for s,_ in fs))
                return (len(union),len(fs),v)
            v=min(active,key=candidate) if order is None else order[stats["eliminated"]]
            active.remove(v)
            hit=[f for f in factors if v in f[0]]
            if not hit:
                constant=tuple(2*x for x in constant);stats["isolated"]+=1
                stats["eliminated"]+=1;continue
            union=tuple(sorted(set().union(*(set(s) for s,_ in hit))))
            remain=tuple(i for i in union if i!=v)
            # Bound temporary index tables as well as ring entries.
            live=sum(len(t) for _,t in factors)
            if streamed:
                stats["width"]=max(stats["width"],len(union))
                if len(union)>max_width:raise FactorLimit("width")
                size=1<<len(union)
                split=min(10,len(union))
                block=1<<split
                # For each factor, projection(a) = projection(lo) OR
                # projection(hi); the two bit masks are disjoint.
                # Count both maps and conservative construction scratch.
                index_entries=(block+(size//block))*len(hit)
                temporary=2*index_entries+(1<<len(remain))
            else:
                size=admit(union,live)
                index_entries=size*len(hit)
                temporary=index_entries+(1<<len(remain))
            stats["peak_index_entries"]=max(stats["peak_index_entries"],index_entries)
            stats["peak_entries"]=max(stats["peak_entries"],live+temporary)
            if live+temporary>max_live:raise FactorLimit("live-entries")
            charge(size*(len(hit)+2))
            if streamed:
                maps=[(projection(union[:split],s),projection(union[split:],s)) for s,_ in hit]
            else:
                maps=[projection(union,s) for s,_ in hit]
            out=[RZERO]*(1<<len(remain))
            pos=union.index(v);low=(1<<pos)-1
            if streamed:
                # Keep only two small projection tables per factor.
                # No full union-sized projection vector is materialized.
                for hi in range(size//block):
                    charge(0)
                    group=[(tab,lo,high[hi]) for (_,tab),(lo,high) in zip(hit,maps)]
                    for lo in range(block):
                        a=(hi<<split)|lo
                        z=RONE
                        for tab,idx,offset in group:
                            z=rmul(z,tab[idx[lo]|offset])
                            if z==RZERO:break
                        key=(a&low)|((a>>(pos+1))<<pos)
                        out[key]=radd(out[key],z)
                    del group
            else:
                for a in range(size):
                    if a%1024==0:charge(0)
                    z=RONE
                    for (_,tab),idx in zip(hit,maps):
                        z=rmul(z,tab[idx[a]])
                        if z==RZERO:break
                    key=(a&low)|((a>>(pos+1))<<pos)
                    out[key]=radd(out[key],z)
            factors=[f for f in factors if v not in f[0]]
            if remain:factors.append((remain,out))
            else:constant=rmul(constant,out[0])
            # Do not retain previous bucket tables or projection maps.
            # Loop locals can otherwise hold a large old table alive.
            del hit,maps,out
            if streamed:
                if "tab" in locals():del tab
                if "idx" in locals():del idx
            else:
                if "tab" in locals():del tab
                if "idx" in locals():del idx
            stats["eliminated"]+=1
        assert not factors
        return constant,stats,"EXACT_SUM"
    except FactorLimit as e:
        return None,stats,str(e)


def factor_contract():
    import random
    rng=random.Random(2626)
    # Independent direct phase evaluation, including constant and affine
    # factors, free/unused variables, products and complex intermediate sums.
    for k in range(160):
        n=k%7
        terms=[(rng.randrange(8),[(rng.randrange(1<<n),rng.randrange(2))
               for _ in range(rng.randrange(4))]) for _ in range(rng.randrange(12))]
        expected=[0]*4
        for a in range(1<<n):
            e=sum(c for c,fs in terms if all(((a&m).bit_count()%2)^b for m,b in fs))%8
            expected[e%4]+=1 if e<4 else -1
        z,_,_=factor_sum(n,terms,time.monotonic()+2)
        assert z==tuple(expected),(n,terms,z,expected)
        zs,_,_=factor_sum(n,terms,time.monotonic()+2,streamed=True)
        assert zs==tuple(expected),(n,terms,zs,expected)
    for streamed in (False,True):
        z,_,why=factor_sum(3,[(1,[(7,0)])],time.monotonic()+1,max_width=1,streamed=streamed)
        assert z is None and why=="width"
    # Exercise the split on scopes above 10 bits independently of the
    # sum implementation, including arbitrary gaps in global variable IDs.
    for k in range(40):
        outer=tuple(sorted(rng.sample(range(48),rng.randrange(11,17))))
        inner=tuple(v for v in outer if rng.randrange(2))
        split=10
        a=projection(outer,inner)
        lo=projection(outer[:split],inner)
        hi=projection(outer[split:],inner)
        assert all(v==lo[i%1024]|hi[i//1024] for i,v in enumerate(a))
    # Same admitted polynomial, exact known sum, deliberately tiny
    # index-table budget: streaming must succeed where full maps cannot.
    terms=[(1,[(1<<i,0) for i in range(12)]) for _ in range(3)]
    expected=radd((4095,0,0,0),ROOTS[3])
    z,_,why=factor_sum(12,terms,time.monotonic()+2,max_live=9000)
    assert z is None and why=="live-entries"
    z,_,why=factor_sum(12,terms,time.monotonic()+2,max_live=9000,streamed=True)
    assert z==expected,(z,why,expected)
    print("HOARE_FACTOR_CONTRACT checks=364",flush=True)


def run_factor_pilot(directory,solve,deadline,metrics):
    factor_contract()
    ff="case hr scale primary terms status prep_us expected".split()
    cf="case h hr gates gr scale vars clauses delta status cone_us build_us encoding_us expected".split()
    af="case mode h hr scale vars clauses primary phase_terms delta status cone_us build_us encoding_us expected".split()
    with (directory/"factors.tsv").open() as f:
        plans=list(csv.DictReader(f,fieldnames=ff,delimiter="\t"))
    with (directory/"cone.tsv").open() as f:
        baseline={r["case"]:r for r in csv.DictReader(f,fieldnames=cf,delimiter="\t")}
    with (directory/"affine.tsv").open() as f:
        baseline.update({r["case"]:r for r in csv.DictReader(f,fieldnames=af,delimiter="\t") if r["mode"]=="cone"})
    assert len(plans)==11 and len(baseline)==6
    rows=[]
    for i,r in enumerate(plans):
        name=r["case"];target=tuple(map(int,r["expected"].split(",")))
        scale=int(r["scale"]);primary=int(r["primary"])
        modes=("factor","gpmc") if i%2==0 else ("gpmc","factor")
        if name not in baseline:modes=("factor",)
        for mode in modes:
            row=dict(case=name,mode=mode,primary=primary,terms=int(r["terms"]),scale=scale,
                     expected_raw=target,coeff=None,verdict="UNKNOWN",status=r["status"],
                     root_s=0.0,prep_proxy_s=int(r["prep_us"])/1e6,queries=[])
            start=time.monotonic()
            if mode=="factor":
                if r["status"]=="UNSAT_AFFINE":
                    row.update(coeff=(0,0),status="EXACT_AFFINE_UNSAT")
                elif r["status"]=="READY":
                    data=(directory/f"factors-{name}.tsv").read_bytes()
                    row["factor_sha256"]=hashlib.sha256(data).hexdigest()
                    terms=[]
                    for line in data.decode().splitlines():
                        k,*fs=line.split("\t")
                        terms.append((int(k),[tuple(map(int,f.split(":"))) for f in fs]))
                    assert len(terms)==int(r["terms"])
                    z,stats,why=factor_sum(primary,terms,min(deadline,start+15))
                    row.update(stats=stats,status=why)
                    if z is not None:
                        assert z[2]==0 and z[3]==-z[1],(name,z)
                        row["coeff"]=(z[0]*(1<<scale),z[1]*(1<<scale))
            else:
                b=baseline[name];assert b["expected"]==r["expected"]
                row.update(vars=int(b["vars"]),clauses=int(b["clauses"]),
                    prep_proxy_s=sum(int(b[k]) for k in ("cone_us","build_us","encoding_us"))/1e6)
                metrics.clear()
                cap=120 if "15" in name else 60
                row["cap_s"]=cap
                if b["status"]=="READY":
                    data=(directory/f"cone-{name}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                    end=min(deadline,start+cap)
                    if end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                    else:
                        try:
                            coeff=tuple(solve(data.decode(),list(map(int,b["delta"].split(","))),[],end))
                            row.update(coeff=tuple(v*(1<<int(b["scale"])) for v in coeff),status="EXACT_ROOT")
                        except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                        except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                row["queries"]=[dict(m) for m in metrics]
                row["max_rss_kib"]=max(m["max_rss_kib"] for m in metrics) if metrics and all(m["max_rss_kib"] is not None for m in metrics) else None
            row["root_s"]=time.monotonic()-start
            if row["coeff"] is not None:
                assert row["coeff"]==target,(name,mode,row["coeff"],target)
                assert not any(target) or positive_surd(target)
                row["verdict"]="REFUTED" if any(target) else "PROVED"
            if name.startswith("factor-"):assert row["verdict"]!="UNKNOWN",(name,row)
            row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
            rows.append(row)
            print("HOARE_FACTOR_PILOT "+json.dumps(row),flush=True)
    assert len(rows)==17
    print("HOARE_FACTOR_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        mode:dict(decided=sum(r["mode"]==mode and r["verdict"]!="UNKNOWN" for r in rows),
                  scale_decided=sum(r["mode"]==mode and r["case"] in baseline and r["verdict"]!="UNKNOWN" for r in rows))
        for mode in ("factor","gpmc")})),flush=True)




def run_streamed_factor_pilot(directory,solve,deadline,metrics):
    """Matched factor representation ablation under identical budgets.
    All six original scale cases, two repetitions in reversed mode order.
    Run GPMC only as explicit fallback if neither representation decides.
    """
    factor_contract()
    ff="case hr scale primary terms status prep_us expected".split()
    cf="case h hr gates gr scale vars clauses delta status cone_us build_us encoding_us expected".split()
    af="case mode h hr scale vars clauses primary phase_terms delta status cone_us build_us encoding_us expected".split()
    with (directory/"factors.tsv").open() as f:
        plans=list(csv.DictReader(f,fieldnames=ff,delimiter="\t"))
    with (directory/"cone.tsv").open() as f:
        baseline={r["case"]:r for r in csv.DictReader(f,fieldnames=cf,delimiter="\t")}
    with (directory/"affine.tsv").open() as f:
        baseline.update({r["case"]:r for r in csv.DictReader(f,fieldnames=af,delimiter="\t") if r["mode"]=="cone"})
    assert len(plans)==11 and len(baseline)==6
    rows=[]
    for i,r in enumerate(plans):
        name=r["case"];target=tuple(map(int,r["expected"].split(",")))
        scale=int(r["scale"]);primary=int(r["primary"])
        terms=[]
        data=None
        if r["status"]=="READY":
            data=(directory/f"factors-{name}.tsv").read_bytes()
            for line in data.decode().splitlines():
                k,*fs=line.split("\t")
                terms.append((int(k),[tuple(map(int,f.split(":"))) for f in fs]))
            assert len(terms)==int(r["terms"])
        cohort=[]
        for rep in range(2 if name in baseline else 1):
            order=("table","streamed") if (i+rep)%2==0 else ("streamed","table")
            for mode in order:
                row=dict(case=name,mode=mode,rep=rep,primary=primary,terms=int(r["terms"]),scale=scale,
                         expected_raw=target,coeff=None,verdict="UNKNOWN",status=r["status"],
                         prep_proxy_s=int(r["prep_us"])/1e6,
                         factor_sha256=hashlib.sha256(data).hexdigest() if data is not None else None)
                start=time.monotonic()
                if r["status"]=="UNSAT_AFFINE":
                    row.update(coeff=(0,0),status="EXACT_AFFINE_UNSAT")
                elif data is not None:
                    z,stats,why=factor_sum(primary,terms,min(deadline,start+15),streamed=mode=="streamed")
                    row.update(stats=stats,status=why)
                    if z is not None:
                        assert z[2]==0 and z[3]==-z[1],(name,z)
                        row["coeff"]=(z[0]*(1<<scale),z[1]*(1<<scale))
                row["root_s"]=time.monotonic()-start
                if row["coeff"] is not None:
                    assert row["coeff"]==target,(name,mode,row["coeff"],target)
                    assert not any(target) or positive_surd(target)
                    row["verdict"]="REFUTED" if any(target) else "PROVED"
                if name.startswith("factor-"):assert row["verdict"]!="UNKNOWN",(name,row)
                row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
                rows.append(row);cohort.append(row)
                print("HOARE_STREAMED_FACTOR "+json.dumps(row),flush=True)
        if name in baseline and all(row["verdict"]=="UNKNOWN" for row in cohort if row["mode"]=="streamed"):
            b=baseline[name];assert b["expected"]==r["expected"]
            cap=120 if "15" in name else 60
            row=dict(case=name,mode="gpmc-fallback",cap_s=cap,expected_raw=target,
                     coeff=None,verdict="UNKNOWN",status=b["status"])
            start=time.monotonic()
            metrics.clear()
            if b["status"]=="READY":
                data=(directory/f"cone-{name}.cnf").read_bytes()
                row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                end=min(deadline,start+cap)
                if end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                else:
                    try:
                        coeff=tuple(solve(data.decode(),list(map(int,b["delta"].split(","))),[],end))
                        coeff=tuple(v*(1<<int(b["scale"])) for v in coeff)
                        assert coeff==target,(name,coeff,target)
                        row.update(coeff=coeff,status="EXACT_ROOT",verdict="REFUTED" if any(coeff) else "PROVED")
                    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
            row["root_s"]=time.monotonic()-start
            row["queries"]=[dict(m) for m in metrics]
            rows.append(row)
            print("HOARE_STREAMED_FACTOR "+json.dumps(row),flush=True)
    assert sum(r["mode"] in ("table","streamed") for r in rows)==34
    print("HOARE_STREAMED_FACTOR_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        mode:dict(decided=sum(r["mode"]==mode and r["verdict"]!="UNKNOWN" for r in rows),
                  scale_decided=sum(r["mode"]==mode and r["case"] in baseline and r["verdict"]!="UNKNOWN" for r in rows))
        for mode in ("table","streamed","gpmc-fallback")})),flush=True)




def scope_plan(primary,terms,heuristic,deadline):
    """Simulate factor scopes only. No oracle or sampled solver timing."""
    groups={}
    for k,forms in terms:
        mask=0
        for m,b in forms:mask|=m
        groups[mask]=groups.get(mask,0)+len(forms)+1
    scopes=[m for m in groups if m]
    work=sum((1<<m.bit_count())*cost for m,cost in groups.items())
    width=max((m.bit_count() for m in groups),default=0)
    active=set(range(primary));order=[]
    while active:
        if time.monotonic()>=deadline:raise FactorLimit("planning-time")
        adjacency=[0]*primary
        for m in scopes:
            for v in mask_positions(m):adjacency[v]|=m&~(1<<v)
        def rank(v):
            mask=adjacency[v];w=mask.bit_count()+1 if mask else 0
            incident=sum(bool(m>>v&1) for m in scopes)
            missing=sum((mask&~adjacency[u]&~(1<<u)).bit_count() for u in mask_positions(mask))//2
            if heuristic=="fill":return (missing,w,incident,v)
            if heuristic=="work":return ((1<<w)*(incident+2),w,missing,v)
            return (w,incident,v)
        v=min(active,key=rank);active.remove(v);order.append(v)
        hit=[m for m in scopes if m>>v&1]
        if hit:
            union=0
            for m in hit:union|=m
            w=union.bit_count();width=max(width,w)
            work+=(1<<w)*(len(hit)+2)
            scopes=[m for m in scopes if not m>>v&1]
            remain=union&~(1<<v)
            if remain:scopes.append(remain)
    return dict(width=width,work=work,order=order,heuristic=heuristic)


def condition_terms(primary,terms,cut,assignment):
    """Exact restriction and compact reindexing. Each cut assignment
    partitions the original Boolean domain; no additional factor of 2."""
    fixed=sum(1<<v for v in cut)
    value=sum(1<<v for i,v in enumerate(cut) if assignment>>i&1)
    free=[v for v in range(primary) if not fixed>>v&1]
    pos={v:i for i,v in enumerate(free)}
    result={}
    for k,forms in terms:
        key=[];zero=False
        for m,b in forms:
            constant=b^((m&value).bit_count()&1)
            mask=sum(1<<pos[v] for v in mask_positions(m&~fixed))
            if mask==0:
                if not constant:zero=True;break
                continue
            if (mask,1^constant) in key:zero=True;break
            key.append((mask,constant))
        if zero:continue
        key=tuple(sorted(set(key)))
        result[key]=(result.get(key,0)+k)%8
    return len(free),[(k,list(key)) for key,k in sorted(result.items()) if k]


def planned_factor(primary,terms,deadline,max_width=16,max_work=4_000_000,
                   max_live=524288,allow_cut=True):
    """Bounded structural planning then exact contraction of ALL branches.
    No incomplete branch sum can yield a verdict. Planner wall time counts
    toward the same deadline; operation budget counts contraction work."""
    planning_start=time.monotonic()
    planning_end=min(deadline,planning_start+3)
    stats=dict(work=0,width=0,peak_entries=0,branches_done=0,branches=0,
               cut=[],plans=0,planning_s=0.0,estimated_work=None,
               estimated_width=None,heuristics=[])
    best=None
    def evaluate(cut):
        nonlocal best
        branches=[]
        for a in range(1<<len(cut)):
            n,ts=condition_terms(primary,terms,cut,a) if cut else (primary,terms)
            options=[scope_plan(n,ts,h,planning_end) for h in ("width","fill","work")]
            stats["plans"]+=len(options)
            plan=min(options,key=lambda p:(p["width"]>max_width,
                       p["work"] if p["width"]<=max_width else p["width"],p["width"],p["work"]))
            branches.append((n,ts,plan))
        width=max(p["width"] for _,_,p in branches)
        work=sum(p["work"] for _,_,p in branches)
        rank=(width>max_width,work>max_work if width<=max_width else False,
              work if width<=max_width else width,width,work,len(cut),cut)
        if best is None or rank<best[0]:best=(rank,cut,branches,width,work)
    try:
        evaluate(())
        if allow_cut and (best[3]>max_width or best[4]>max_work):
            # Predeclare a small candidate set from the original factor graph.
            # High interaction degree first; tie-break by incident factor count.
            scopes=[]
            for _,fs in terms:
                mask=0
                for m,_ in fs:mask|=m
                scopes.append(set(mask_positions(mask)))
            def rank(v):
                hit=[s for s in scopes if v in s]
                return (-len(set().union(*hit)) if hit else 0,-len(hit),v)
            candidates=sorted(range(primary),key=rank)[:8]
            for v in candidates:evaluate((v,))
            # Only attempt two-bit cuts if one-bit plans cannot fit.
            if best[3]>max_width or best[4]>max_work:
                for i,v in enumerate(candidates[:4]):
                    for w in candidates[i+1:4]:evaluate(tuple(sorted((v,w))))
    except FactorLimit:
        pass
    stats["planning_s"]=time.monotonic()-planning_start
    if best is None:return None,stats,"planning-time"
    _,cut,branches,width,work=best
    stats.update(cut=list(cut),branches=len(branches),estimated_width=width,
                 estimated_work=work,heuristics=[p["heuristic"] for _,_,p in branches])
    if width>max_width:return None,stats,"planned-width"
    # Work estimate ignores early zero and is deliberately conservative.
    # Try a feasible-width plan even if estimated work exceeds the cap.
    total=RZERO
    for n,ts,plan in branches:
        remaining=max_work-stats["work"]
        if remaining<=0 or time.monotonic()>=deadline:return None,stats,"aggregate-work-or-time"
        z,st,why=factor_sum(n,ts,deadline,max_width=max_width,max_work=remaining,
                            max_live=max_live,streamed=True,order=plan["order"])
        stats["work"]+=st["work"]
        stats["width"]=max(stats["width"],st["width"])
        stats["peak_entries"]=max(stats["peak_entries"],st["peak_entries"])
        if z is None:return None,stats,"branch-"+why
        total=radd(total,z);stats["branches_done"]+=1
    return total,stats,"EXACT_CONDITIONED" if cut else "EXACT_PLANNED"


def conditioning_contract():
    import random
    rng=random.Random(2627)
    checks=0
    for k in range(96):
        n=1+k%6
        terms=[(rng.randrange(8),[(rng.randrange(1<<n),rng.randrange(2))
            for _ in range(rng.randrange(4))]) for _ in range(rng.randrange(10))]
        expected=RZERO
        for a in range(1<<n):
            e=sum(c for c,fs in terms if all(((a&m).bit_count()&1)^b for m,b in fs))%8
            expected=radd(expected,ROOTS[e])
        # Exercise every branch of a predetermined cut independent of the
        # heuristic, including complex partial sums (not leakage by itself).
        cut=tuple(sorted(rng.sample(range(n),min(2,n))))
        actual=RZERO
        for a in range(1<<len(cut)):
            m,ts=condition_terms(n,terms,cut,a)
            z,_,_=factor_sum(m,ts,time.monotonic()+2,streamed=True)
            assert z is not None
            actual=radd(actual,z)
        assert actual==expected;checks+=1
        z,_,_=planned_factor(n,terms,time.monotonic()+3)
        assert z==expected;checks+=1
    # K5 interaction graph requires width5 for unconditioned elimination;
    # a single fixed bit leaves K4. Exact sum from direct enumeration.
    terms=[(1,[(1<<i,0),(1<<j,0)]) for i in range(5) for j in range(i+1,5)]
    expected=RZERO
    for a in range(32):expected=radd(expected,ROOTS[(a.bit_count()*(a.bit_count()-1)//2)%8])
    z,_,_=planned_factor(5,terms,time.monotonic()+3,max_width=4,allow_cut=False)
    assert z is None;checks+=1
    z,st,_=planned_factor(5,terms,time.monotonic()+3,max_width=4)
    assert z==expected and st["branches_done"]==2 and len(st["cut"])==1;checks+=1
    z,st,_=planned_factor(5,terms,time.monotonic()+3,max_width=4,max_work=1)
    assert z is None and st["branches_done"]<st["branches"];checks+=1
    print("HOARE_CONDITIONING_CONTRACT checks="+str(checks),flush=True)


def run_conditioned_factor_pilot(directory,solve,deadline,metrics):
    factor_contract();conditioning_contract()
    fields="case hr scale primary terms status prep_us expected".split()
    with (directory/"factors.tsv").open() as f:
        plans=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    assert len(plans)==11
    rows=[]
    for i,r in enumerate(plans):
        name=r["case"];target=tuple(map(int,r["expected"].split(",")))
        primary=int(r["primary"]);scale=int(r["scale"])
        data=(directory/f"factors-{name}.tsv").read_bytes() if r["status"]=="READY" else None
        terms=[]
        if data is not None:
            for line in data.decode().splitlines():
                k,*fs=line.split("\t");terms.append((int(k),[tuple(map(int,x.split(":"))) for x in fs]))
            assert len(terms)==int(r["terms"])
        modes=["streamed","planned","conditioned"]
        if i%2:modes.reverse()
        for mode in modes+ (["conditioned-12m"] if name=="affine-mixing-15" else []):
            max_work=12_000_000 if mode.endswith("12m") else 4_000_000
            row=dict(case=name,mode=mode,work_cap=max_work,width_cap=16,live_cap=524288,
                     primary=primary,terms=int(r["terms"]),scale=scale,expected_raw=target,
                     coeff=None,verdict="UNKNOWN",status=r["status"],prep_proxy_s=int(r["prep_us"])/1e6,
                     factor_sha256=hashlib.sha256(data).hexdigest() if data is not None else None)
            start=time.monotonic();end=min(deadline,start+15)
            if r["status"]=="UNSAT_AFFINE":row.update(coeff=(0,0),status="EXACT_AFFINE_UNSAT")
            elif data is not None:
                if mode=="streamed":z,st,why=factor_sum(primary,terms,end,streamed=True)
                else:z,st,why=planned_factor(primary,terms,end,max_work=max_work,allow_cut=mode!="planned")
                row.update(stats=st,status=why)
                if z is not None:
                    assert z[2]==0 and z[3]==-z[1],(name,z)
                    row["coeff"]=(z[0]*(1<<scale),z[1]*(1<<scale))
            row["root_s"]=time.monotonic()-start
            row["decision_proxy_s"]=row["root_s"]+row["prep_proxy_s"]
            if row["coeff"] is not None:
                assert row["coeff"]==target,(name,mode,row["coeff"],target)
                assert not any(target) or positive_surd(target)
                row["verdict"]="REFUTED" if any(target) else "PROVED"
            if name.startswith("factor-"):assert row["verdict"]!="UNKNOWN",(name,row)
            rows.append(row)
            print("HOARE_CONDITIONED_FACTOR "+json.dumps(row),flush=True)
    assert len(rows)==34
    print("HOARE_CONDITIONED_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        mode:dict(decided=sum(r["mode"]==mode and r["verdict"]!="UNKNOWN" for r in rows),
                  scale_decided=sum(r["mode"]==mode and not r["case"].startswith("factor-") and r["verdict"]!="UNKNOWN" for r in rows))
        for mode in ("streamed","planned","conditioned","conditioned-12m")})),flush=True)




def run_property_factor_pilot(directory,solve,deadline,metrics):
    """Generalized affine conjunctions with a complete, original-guard
    GPMC fallback. Partial branch sums never establish a verdict."""
    factor_contract();conditioning_contract()
    fields="case n h hr scale post_count branch_count factor_status cnf_status vars clauses delta common_us base_us factor_us expected oracle".split()
    bf="case branch status primary terms".split()
    with (directory/"property-factor.tsv").open() as f:
        cases=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    with (directory/"property-factor-branches.tsv").open() as f:
        branches=list(csv.DictReader(f,fieldnames=bf,delimiter="\t"))
    assert len(cases)==20
    if os.environ.get("HOARE_R27A_FULL")!="1":
        cases=[r for r in cases if "mixing" not in r["case"]]
    rows=[]
    for i,r in enumerate(cases):
        name=r["case"];target=tuple(map(int,r["expected"].split(",")))
        cap=(120 if "15" in name else 60) if "mixing" in name else 30
        scale=int(r["scale"])
        bs=[b for b in branches if b["case"]==name]
        assert len(bs)==int(r["branch_count"])
        assert [int(b["branch"]) for b in bs]==list(range(len(bs)))
        for mode in (("hybrid","gpmc") if i%2==0 else ("gpmc","hybrid")):
            row=dict(case=name,mode=mode,oracle=r["oracle"],expected_raw=target,coeff=None,
                     verdict="UNKNOWN",status="NOT_RUN",scale=scale,post_count=int(r["post_count"]),
                     branch_count=len(bs),branches_done=0,branch_stats=[],factor_work=0,factor_s=0.0,
                     gpmc_s=0.0,queries=[],route="gpmc" if mode=="gpmc" else "factor",
                     vars=int(r["vars"]),clauses=int(r["clauses"]),gpmc_cap_s=cap,
                     source_sha256=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest(),
                     prep_proxy_s=int(r["common_us"])/1e6)
            if mode=="hybrid":
                start=time.monotonic()
                end=min(deadline,start+15)
                row["prep_proxy_s"]+=int(r["factor_us"])/1e6
                if r["factor_status"]=="READY":
                    total=RZERO
                    for b in bs:
                        st=dict(branch=int(b["branch"]),status=b["status"])
                        if b["status"]=="UNSAT_AFFINE":
                            z=RZERO
                        else:
                            remaining=4_000_000-row["factor_work"]
                            if remaining<=0 or time.monotonic()>=end:
                                row["status"]="BRANCH_AGGREGATE_LIMIT";break
                            data=(directory/f"property-factor-{name}-{b['branch']}.tsv").read_bytes()
                            terms=[]
                            for line in data.decode().splitlines():
                                k,*fs=line.split("\t");terms.append((int(k),[tuple(map(int,x.split(":"))) for x in fs]))
                            assert len(terms)==int(b["terms"])
                            z,stats,why=planned_factor(int(b["primary"]),terms,end,max_work=remaining)
                            row["factor_work"]+=stats["work"]
                            st.update(stats=stats,status=why,sha256=hashlib.sha256(data).hexdigest())
                        row["branch_stats"].append(st)
                        if z is None:
                            row["status"]="INCOMPLETE_BRANCH";break
                        assert z[2]==0 and z[3]==-z[1],(name,b,z)
                        assert not any(z) or positive_surd((z[0],z[1])),(name,b,z)
                        total=radd(total,z);row["branches_done"]+=1
                    if row["branches_done"]==len(bs):
                        row.update(coeff=(total[0]*(1<<scale),total[1]*(1<<scale)),status="EXACT_ALL_BRANCHES")
                else:row["status"]="UNSUPPORTED_FACTOR"
                row["factor_s"]=time.monotonic()-start
                row["factor_status"]=row["status"]
            if row["coeff"] is None:
                if mode=="hybrid":row["route"]="gpmc-fallback"
                row["prep_proxy_s"]+=int(r["base_us"])/1e6
                metrics.clear()
                start=time.monotonic()
                end=min(deadline,start+cap)
                if r["cnf_status"]!="READY":row["status"]=r["cnf_status"]
                elif end<=start:row["status"]="GLOBAL_BUDGET_NOT_RUN"
                else:
                    data=(directory/f"property-base-{name}.cnf").read_bytes()
                    row["cnf_sha256"]=hashlib.sha256(data).hexdigest()
                    try:
                        coeff=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                        row.update(coeff=tuple(v*(1<<scale) for v in coeff),status="EXACT_ROOT")
                    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
                    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
                row["gpmc_s"]=time.monotonic()-start
                row["queries"]=[dict(m) for m in metrics]
            if row["coeff"] is not None:
                assert row["coeff"]==target,(name,mode,row["coeff"],target)
                assert not any(target) or positive_surd(target)
                row["verdict"]="REFUTED" if any(target) else "PROVED"
            row["decision_proxy_s"]=row["prep_proxy_s"]+row["factor_s"]+row["gpmc_s"]
            rows.append(row)
            print("HOARE_PROPERTY_FACTOR "+json.dumps(row),flush=True)
    assert len(rows)==2*len(cases)
    print("HOARE_PROPERTY_FACTOR_SUMMARY "+json.dumps(dict(attempts=len(rows),modes={
        m:dict(decided=sum(r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows),
               proved=sum(r["mode"]==m and r["verdict"]=="PROVED" for r in rows),
               refuted=sum(r["mode"]==m and r["verdict"]=="REFUTED" for r in rows),
               factor_only=sum(r["mode"]==m and r["route"]=="factor" for r in rows),
               fallback=sum(r["mode"]==m and r["route"]=="gpmc-fallback" for r in rows))
        for m in ("hybrid","gpmc")})),flush=True)





def restrict_affine_terms(primary,terms,forms,prefix):
    """RREF original-input equations on existing free coordinates.
    Return an exact bijective reparameterization, or None for UNSAT."""
    rows=[(forms[i][0],forms[i][1]^b) for i,b in prefix]
    pivots=[]
    for j in reversed(range(primary)):
        k=next((k for k in range(len(pivots),len(rows)) if rows[k][0]>>j&1),None)
        if k is None:continue
        i=len(pivots);rows[i],rows[k]=rows[k],rows[i]
        m,b=rows[i]
        rows=[(a^m,c^b) if l!=i and a>>j&1 else (a,c) for l,(a,c) in enumerate(rows)]
        pivots.append(j)
    if any(not m and b for m,b in rows):return None
    free=[i for i in range(primary) if i not in pivots]
    substitution=[(0,0)]*primary
    for k,j in enumerate(free):substitution[j]=(1<<k,0)
    for i,j in enumerate(pivots):
        m,b=rows[i];mask=0
        for k in free:
            if m>>k&1:mask^=substitution[k][0]
        substitution[j]=(mask,b)
    result={}
    for k,fs in terms:
        key=[];vanish=False
        for m,b in fs:
            mask=0
            for j in mask_positions(m):
                a,c=substitution[j];mask^=a;b^=c
            if not mask:
                if not b:vanish=True;break
                continue
            if (mask,b^1) in key:vanish=True;break
            key.append((mask,b))
        if vanish:continue
        key=tuple(sorted(set(key)))
        result[key]=(result.get(key,0)+k)%8
    return len(free),[(k,list(fs)) for fs,k in sorted(result.items()) if k]


def witness_affine_contract():
    import random
    rng=random.Random(2804)
    for _ in range(128):
        n=rng.randrange(7);N=1<<n
        forms=[(rng.randrange(N),rng.randrange(2)) for _ in range(3)]
        terms=[(rng.randrange(8),[(rng.randrange(N),rng.randrange(2)) for _ in range(rng.randrange(4))]) for _ in range(8)]
        prefix=[(i,rng.randrange(2)) for i in range(rng.randrange(4))]
        expected=RZERO
        for x in range(N):
            if not all(((forms[i][0]&x).bit_count()%2)^forms[i][1]==b for i,b in prefix):continue
            e=sum(k for k,fs in terms if all(((m&x).bit_count()%2)^b for m,b in fs))%8
            expected=radd(expected,ROOTS[e])
        r=restrict_affine_terms(n,terms,forms,prefix)
        if r is None:assert expected==RZERO
        else:
            z,_,_=factor_sum(*r,time.monotonic()+2)
            assert z==expected,(r,z,expected)
    print("HOARE_WITNESS_AFFINE_CONTRACT checks=128",flush=True)


def dispatch_witness(directory,r,result,bs,n,ops,p,q,solve,deadline):
    from hoare_quokka_compare import evaluate,prefix_witness,verify_original_input
    start=time.monotonic();end=min(deadline,start+30)
    legal=lambda x:all(evaluate(f,x) for f in p)
    post=lambda z:all(evaluate(f,z) for f in q)
    name=r["case"];method=result["route"];calls=0;work=0
    # The unique legal input is determined solely from P, not the oracle.
    candidates=[]
    for x in range(1<<n):
        if x%1024==0 and time.monotonic()>=end:break
        if legal(x):
            candidates.append(x)
            if len(candidates)==2:break
    x=None;status="WITNESS_INCOMPLETE"
    if len(candidates)==1 and time.monotonic()<end:
        x=candidates[0];method="unique-legal-input"
    elif method=="rr":
        x=result["attempts"][-1].get("witness_input");method="rr-original-input"
    elif method=="frontier" and result["attempts"][-1].get("witness_input") is not None:
        x=result["attempts"][-1]["witness_input"];method="frontier-diagonal"
    elif method=="factor":
        # A fully summed positive disjoint branch is sufficient to select
        # a witness; never use a partially contracted cutset branch.
        hit=next((b for b in result["attempts"][-1]["branch_stats"] if any(b.get("coeff",[]))),None)
        if hit is not None:
            branch=hit["branch"]
            b=next(b for b in bs if int(b["branch"])==branch)
            data=(directory/f"property-factor-{name}-{branch}.tsv").read_text()
            terms=[]
            for line in data.splitlines():
                k,*fs=line.split("\t");terms.append((int(k),[tuple(map(int,f.split(":"))) for f in fs]))
            forms=[tuple(map(int,f.split(":"))) for f in (directory/f"property-input-{name}-{branch}.tsv").read_text().split("\t")]
            assert len(forms)==n
            def query(prefix,stop):
                nonlocal work
                a=restrict_affine_terms(int(b["primary"]),terms,forms,prefix)
                if a is None:return False
                if work>=12_000_000:return None
                z,st,_=planned_factor(*a,stop,max_work=12_000_000-work)
                work+=st["work"]
                if z is None:return None
                assert z[2]==0 and z[3]==-z[1] and (not any(z) or positive_surd((z[0],z[1])))
                return bool(any(z))
            x,calls,status=prefix_witness(n,legal,query,min(end,start+15))
            method="affine-prefix"
    elif method in ("gpmc","rr-wmc"):
        if method=="rr-wmc":
            rr=dispatch_rr_rows(directory)[name]
            data=(directory/f"dispatch-rr-{name}.cnf").read_text();delta=list(map(int,rr["delta"].split(",")))
        else:
            data=(directory/f"property-base-{name}.cnf").read_text();delta=list(map(int,r["delta"].split(",")))
        def query(prefix,stop):
            try:
                coeff=solve(data,delta,[i+2 if b else -(i+2) for i,b in prefix],stop)
                assert not any(coeff) or positive_surd(coeff)
                return bool(any(coeff))
            except (TimeoutError,subprocess.TimeoutExpired,SolverSignalKilled):return None
        x,calls,status=prefix_witness(n,legal,query,min(end,start+15))
        method="gpmc-prefix"
    if x is None:
        row=dict(status=status)
    else:
        row=verify_original_input(n,ops,legal,post,3,x,end)
        if row["status"] in ("ILLEGAL_INPUT","NO_VIOLATING_AMPLITUDE"):
            raise AssertionError(("invalid reconstructed witness",name,row,x))
    row.update(method=method,queries=calls,factor_work=work,witness_s=time.monotonic()-start)
    return row




def dispatch_rr_rows(directory,expected=21):
    fields="case h hr scale hits retained representation status reason witness vars clauses delta rr_us encoding_us pure_status pure_vars pure_clauses pure_delta build_us pure_us".split()
    with (directory/"dispatch-rr.tsv").open() as f:
        rows={r["case"]:r for r in csv.DictReader(f,fieldnames=fields,delimiter="\t")}
    assert len(rows)==expected
    return rows


def rr_terminal(r):
    if r["status"]=="PROVED":
        return dict(coeff=[0,0],status="RR_PROVED",terminal_verdict="PROVED")
    if r["status"]=="REFUTED":
        return dict(coeff=None,status="RR_REFUTED",terminal_verdict="REFUTED",witness_input=int(r["witness"]))
    return dict(coeff=None,status="RR_INCONCLUSIVE",reason=r["reason"])


def dispatch_count(directory,r,solve,deadline,metrics,reduced=False):
    status=r["status"] if reduced else r["pure_status"]
    if status!="READY":return dict(coeff=None,status=status)
    kind="rr" if reduced else "pure"
    data=(directory/f"dispatch-{kind}-{r['case']}.cnf").read_bytes()
    delta=list(map(int,r["delta" if reduced else "pure_delta"].split(",")))
    scale=int(r["scale"]) if reduced else 0
    metrics.clear()
    row=dict(coeff=None,status="UNKNOWN",cnf_sha256=hashlib.sha256(data).hexdigest())
    try:
        coeff=solve(data.decode(),delta,[],deadline)
        assert not any(coeff) or positive_surd(coeff)
        row.update(coeff=[v*(1<<scale) for v in coeff],status="EXACT_ROOT")
    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
    row["queries"]=[dict(m) for m in metrics]
    return row


def dispatch_three_mode_control(directory,r,solve,deadline,metrics):
    expected=list(map(int,(directory/"dispatch-rr-control-oracle.tsv").read_text().strip().split(",")))
    assert r["status"]=="READY" and int(r["hr"])<int(r["h"]),r
    pure=dispatch_count(directory,r,solve,min(deadline,time.monotonic()+10),metrics)
    residual=dispatch_count(directory,r,solve,min(deadline,time.monotonic()+10),metrics,True)
    assert pure["coeff"]==residual["coeff"]==expected,(r,pure,residual,expected)
    print("HOARE_RR_RESIDUAL_CONTROL "+json.dumps(dict(case=r["case"],h=int(r["h"]),hr=int(r["hr"]),
          scale=int(r["scale"]),pure=pure,residual=residual,expected=expected)),flush=True)



def run_structure_dispatch(directory,solve,deadline,metrics,*,heldout=False,gpmc_exe=None,tmp=None,heldout_long=False):
    from hoare_quokka_compare import (load_case,cube,dispatch_policy,
                                        execute_routes,frontier_contract)
    factor_contract();conditioning_contract();witness_affine_contract()
    fields="case n h hr scale post_count branch_count factor_status cnf_status vars clauses delta common_us base_us factor_us expected oracle".split()
    bf="case branch status primary terms".split()
    with (directory/"property-factor.tsv").open() as f:
        cases=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    with (directory/"property-factor-branches.tsv").open() as f:
        branches=list(csv.DictReader(f,fieldnames=bf,delimiter="\t"))
    assert len(cases)==(12 if heldout else 20)
    rr_rows=dispatch_rr_rows(directory,12 if heldout else 21)
    if heldout_long:
        assert heldout
        # Frozen from the 30s pilot before any longer solver invocation.
        selected={f"fourier-{n}-{v}-even" for n in (10,14) for v in ("safe","mutant")}
        cases=[r for r in cases if r["case"] in selected]
        assert {r["case"] for r in cases}==selected and len(cases)==4
    if not heldout:
        dispatch_three_mode_control(directory,rr_rows["rr-residual-control"],solve,deadline,metrics)
    pure_rows=[];rr_results=[];projected_rows=[]
    # Frozen R28E policy, unchanged 12M work, 15s factor, 5s RR-WMC,
    # shared 30s root cap. Held-out pilot excludes training controls.
    tasks=[(r,12_000_000,"heldout-frozen-12M" if heldout else "exploratory-12M") for r in cases]
    if not heldout:
        tasks.append((next(r for r in cases if r["case"]=="BV4-correct"),0,"forced-limit-control"))
    rows=[]
    for r,work_cap,configuration in tasks:
        start=time.monotonic()
        name=r["case"];target=tuple(map(int,r["expected"].split(",")))
        cap=(60 if int(r["n"])==10 else 120) if heldout_long else 30
        if heldout and deadline-start<3*(cap+3):
            raise RuntimeError("held-out global budget cannot provide all three root caps")
        scale=int(r["scale"])
        bs=[b for b in branches if b["case"]==name]
        assert len(bs)==int(r["branch_count"])
        assert [int(b["branch"]) for b in bs]==list(range(len(bs)))
        source=directory/f"quokka-{name}.tsv"
        n,gates,p,q=load_case(source)
        cp,cq=cube(p),cube(q)
        ops=[(op,None,list(args)) for op,*args in gates]
        admitted=cp is not None and cq is not None and all(op in ("h","x","cx","s","t","tdg") for op,_,_ in ops)
        routes,profile=dispatch_policy(n,int(r["h"]),len(ops),admitted,r["factor_status"]=="READY")
        rr=rr_rows[name]
        if configuration!="forced-limit-control":
            routes.insert(0,"rr")
            if rr["status"]=="READY" and (int(rr["hr"])<int(rr["h"]) or int(rr["retained"])>0):
                routes.insert(-1,"rr-wmc")
        # Existing exports prepared offline; charge their recorded costs
        # to a proxy, not to a falsely claimed online end-to-end deadline.
        prep={"frontier":0.0,"factor":int(r["factor_us"])/1e6,
              "gpmc":int(r["base_us"])/1e6,"rr":int(rr["rr_us"])/1e6,
              "rr-wmc":int(rr["encoding_us"])/1e6}
        def frontier(end):
            orientation="forward" if (1<<(n-len(cp))) < (1<<n)-(1<<(n-len(cq))) else "backward"
            v=frontier_contract(n,ops,cp,cq,3,orientation,min(end,time.monotonic()+15))
            coeff=v["coeff"]
            return dict(coeff=None if coeff is None else [coeff[0],coeff[1]],status=v["status"],stats=v["stats"],witness_input=v.get("witness_input"))
        def factor(end):
            end=min(end,time.monotonic()+15)
            total=RZERO;work=0;done=0;stats=[]
            for b in bs:
                if b["status"]=="UNSAT_AFFINE":
                    done+=1;continue
                remaining=work_cap-work
                if remaining<=0 or time.monotonic()>=end:break
                data=(directory/f"property-factor-{name}-{b['branch']}.tsv").read_bytes()
                terms=[]
                for line in data.decode().splitlines():
                    k,*fs=line.split("\t");terms.append((int(k),[tuple(map(int,x.split(":"))) for x in fs]))
                assert len(terms)==int(b["terms"])
                z,st,why=planned_factor(int(b["primary"]),terms,end,max_work=remaining)
                work+=st["work"]
                stats.append(dict(branch=int(b["branch"]),status=why,stats=st,sha256=hashlib.sha256(data).hexdigest()))
                if z is None:break
                assert z[2]==0 and z[3]==-z[1] and (not any(z) or positive_surd((z[0],z[1])))
                stats[-1]["coeff"]=list(z)
                total=radd(total,z);done+=1
            return dict(coeff=[total[0]*(1<<scale),total[1]*(1<<scale)] if done==len(bs) else None,
                        status="EXACT_ALL_BRANCHES" if done==len(bs) else "INCOMPLETE_BRANCH",
                        work=work,branches_done=done,branches=len(bs),branch_stats=stats)
        def gpmc(end):
            if r["cnf_status"]!="READY":return dict(coeff=None,status=r["cnf_status"])
            data=(directory/f"property-base-{name}.cnf").read_bytes()
            metrics.clear()
            row=dict(coeff=None,status="UNKNOWN",cnf_sha256=hashlib.sha256(data).hexdigest())
            try:
                coeff=tuple(solve(data.decode(),list(map(int,r["delta"].split(","))),[],end))
                row.update(coeff=[v*(1<<scale) for v in coeff],status="EXACT_ROOT")
            except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
            except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
            row["queries"]=[dict(m) for m in metrics]
            return row
        result=execute_routes(routes,{"frontier":frontier,"factor":factor,"gpmc":gpmc,
            "rr":lambda end:rr_terminal(rr),
            "rr-wmc":lambda end:dispatch_count(directory,rr,solve,min(end,time.monotonic()+5),metrics,True)},
                              min(deadline,start+cap))
        coeff=result["coeff"]
        if coeff is not None:assert tuple(coeff)==target,(name,result,target)
        terminal=result.get("terminal_verdict")
        if terminal is not None:assert terminal==("REFUTED" if any(target) else "PROVED")
        if configuration=="forced-limit-control":
            assert result["route"]=="gpmc" and len(result["attempts"])==2 and coeff==[0,0],result
        used=[a["route"] for a in result["attempts"]]
        proxy=sum(prep[x] for x in used)+(int(r["common_us"])/1e6 if any(x in ("factor","gpmc") for x in used) else 0)
        elapsed=time.monotonic()-start
        result.update(case=name,configuration=configuration,work_cap=work_cap,cap_s=cap,
                      n=n,h=int(r["h"]),gates=len(ops),profile=profile,planned_routes=routes,
                      expected_coeff=target,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      solve_dispatch_s=elapsed,prep_proxy_s=proxy,decision_proxy_s=elapsed+proxy,
                      verdict=terminal or ("UNKNOWN" if coeff is None else "REFUTED" if any(coeff) else "PROVED"))
        rows.append(result)
        print(("HOARE_FOURIER_HYBRID " if heldout else "HOARE_STRUCTURE_DISPATCH ")+json.dumps(result),flush=True)
        if not heldout and result["verdict"]=="REFUTED":
            witness=dispatch_witness(directory,r,result,bs,n,ops,p,q,solve,deadline)
            result["witness"]=witness
            print("HOARE_STRUCTURE_WITNESS "+json.dumps(dict(case=name,configuration=configuration,source_sha256=result["source_sha256"],**witness)),flush=True)
        if configuration!="forced-limit-control":
            rr_verdict=rr["status"] if rr["status"] in ("PROVED","REFUTED") else "UNKNOWN"
            rr_row=dict(case=name,mode="pure-rr",verdict=rr_verdict,status=rr["status"],h=int(rr["h"]),hr=int(rr["hr"]),hits=int(rr["hits"]),prep_s=int(rr["rr_us"])/1e6,witness=rr["witness"])
            if rr_verdict!="UNKNOWN":assert rr_verdict==("REFUTED" if any(target) else "PROVED")
            if heldout and rr_row["prep_s"]>cap and rr_verdict!="UNKNOWN":
                rr_row.update(verdict="UNKNOWN",status="LATE_EXACT_REJECTED")
            rr_results.append(rr_row);print(("HOARE_FOURIER_MODE " if heldout else "HOARE_THREE_MODE ")+json.dumps(rr_row),flush=True)
            # P1-C reverses direct-arm order across the safe/mutant pair.
            # This is one attempt per property, not repeated A/B-B/A trials.
            arms=("projected","full") if heldout_long and "-mutant-" in name else ("full","projected") if heldout else ("full",)
            prep_s=(int(rr["build_us"])+int(rr["pure_us"]))/1e6
            for position,arm in enumerate(arms):
                st=time.monotonic()
                if heldout and deadline-st<cap+2:
                    raise RuntimeError("held-out global budget cannot provide full arm cap")
                if arm=="full":
                    pure=dispatch_count(directory,rr,solve,min(deadline,st+cap),metrics)
                    if pure["coeff"] is not None:assert tuple(pure["coeff"])==target
                    if heldout and time.monotonic()-st>cap and pure["coeff"] is not None:
                        pure.update(coeff=None,status="LATE_EXACT_REJECTED")
                    pure.update(case=name,mode="pure-wmc",verdict="UNKNOWN" if pure["coeff"] is None else "REFUTED" if any(pure["coeff"]) else "PROVED",root_s=time.monotonic()-st,prep_s=prep_s,cap_s=cap,position=position)
                    pure_rows.append(pure)
                    print(("HOARE_FOURIER_MODE " if heldout else "HOARE_THREE_MODE ")+json.dumps(pure),flush=True)
                else:
                    from hoare_projected_count import projected_count
                    projected=dict(status=rr["pure_status"],mass=None,verdict="UNKNOWN",queries=[])
                    if rr["pure_status"]=="READY":
                        base=(directory/f"dispatch-pure-{name}.cnf").read_text()
                        bits=list(map(int,rr["pure_delta"].split(",")))
                        v=int(base.splitlines()[0].split()[2])
                        projected=projected_count(gpmc_exe,tmp,base,bits,v,st+cap)
                        if projected["mass"] is not None:
                            assert projected["mass"]==target[0] and projected["verdict"]==("REFUTED" if any(target) else "PROVED")
                            if time.monotonic()-st>cap:
                                projected.update(mass=None,verdict="UNKNOWN",status="LATE_EXACT_REJECTED")
                    projected.update(case=name,mode="pure-projected",root_s=time.monotonic()-st,prep_s=prep_s,cap_s=cap,position=position)
                    projected_rows.append(projected)
                    print("HOARE_FOURIER_MODE "+json.dumps(projected),flush=True)
    if heldout:
        modes=(("pure-rr",rr_results),("pure-wmc",pure_rows),("pure-projected",projected_rows),("hybrid-frozen",rows))
        assert all(len(xs)==(4 if heldout_long else 12) for _,xs in modes)
        print("HOARE_FOURIER_COMPARE_SUMMARY "+json.dumps(dict(modes={m:dict(cases=len(xs),
              proved=sum(x["verdict"]=="PROVED" for x in xs),refuted=sum(x["verdict"]=="REFUTED" for x in xs),
              unknown=sum(x["verdict"]=="UNKNOWN" for x in xs)) for m,xs in modes},
              cap_s=[60,120] if heldout_long else 30,root_only=True,offline_prep_proxy=True,
              fixed_arm_order=not heldout_long,hybrid_first=True,heldout_long=heldout_long,
              repetitions_per_property=1,dispatcher_tuned=False)),flush=True)
        return
    benchmark=rows[:-1]
    print("HOARE_THREE_MODE_SUMMARY "+json.dumps({m:dict(cases=len(xs),decided=sum(x["verdict"]!="UNKNOWN" for x in xs),proved=sum(x["verdict"]=="PROVED" for x in xs),refuted=sum(x["verdict"]=="REFUTED" for x in xs)) for m,xs in (("pure-rr",rr_results),("pure-wmc",pure_rows),("hybrid",benchmark))}),flush=True)
    assert len(benchmark)==20
    print("HOARE_STRUCTURE_DISPATCH_SUMMARY "+json.dumps(dict(cases=len(benchmark),
        decided=sum(r["verdict"]!="UNKNOWN" for r in benchmark),
        routes={k:sum(r["route"]==k for r in benchmark) for k in ("rr","frontier","factor","rr-wmc","gpmc","none")},
        forced_limit_fallback=rows[-1]["route"]=="gpmc",configuration="exploratory-12M",
        witnesses_verified=sum(r.get("witness",{}).get("status")=="VERIFIED" for r in benchmark),
        witnesses_required=sum(r["verdict"]=="REFUTED" for r in benchmark))),flush=True)



def parse_sat(rc, stdout, result, cnf):
    # MiniSat's SAT competition exit codes. UNSAT is trusted solver
    # evidence, not a proof certificate. SAT assignments are checked.
    lines = result.splitlines()
    statuses = [l.strip() for l in stdout.splitlines()
                if l.strip() in ("SATISFIABLE", "UNSATISFIABLE", "INDETERMINATE")]
    if rc == 20 and lines == ["UNSAT"] and statuses == ["UNSATISFIABLE"]:
        return False
    if rc != 10 or not lines or lines[0] != "SAT" or statuses != ["SATISFIABLE"]:
        raise ValueError("unqualified SAT output/exit")
    values = [int(v) for v in " ".join(lines[1:]).split()]
    if not values or values[-1] != 0 or 0 in values[:-1]:
        raise ValueError("malformed SAT assignment")
    header, *clauses = cnf.splitlines()
    p, typ, vs, cs = header.split()
    assert p == "p" and typ == "cnf" and len(clauses) == int(cs)
    model = set(values[:-1])
    if any(-l in model or abs(l) > int(vs) for l in model):
        raise ValueError("invalid SAT assignment")
    for clause in clauses:
        lits = list(map(int, clause.split()))
        if not lits or lits[-1] != 0 or not any(l in model for l in lits[:-1]):
            raise ValueError("SAT model fails CNF")
    return frozenset(model)

def sat_parser_tests():
    f = "p cnf 1 1\n1 0\n"
    assert parse_sat(10,"SATISFIABLE\n","SAT\n1 0\n",f) == frozenset({1})
    assert parse_sat(20,"UNSATISFIABLE\n","UNSAT\n",f) is False
    for rc,out,result in [(0,"UNSATISFIABLE\n","UNSAT\n"),
                          (20,"SATISFIABLE\n","UNSAT\n"),
                          (10,"SATISFIABLE\n","SAT\n-1 0\n"),
                          (10,"SATISFIABLE\n","SAT\n1 -1 0\n")]:
        try:
            parse_sat(rc,out,result,f)
        except ValueError:
            continue
        raise AssertionError("accepted invalid SAT response")


def decode_anfs(text):
    return tuple(tuple(map(int,f.split(","))) if f!="-" else ()
                 for f in text.split(";")) if text else ()

def load_symbolic(directory):
    symbols={}
    with (directory/"hybrid-symbolic.tsv").open() as f:
        for name,n,h,out,phase,pre,post in csv.reader(f,delimiter="\t"):
            symbols[name]=(int(n),int(h),decode_anfs(out),
                           tuple(tuple(map(int,t.split(":"))) for t in phase.split(",") if t),
                           decode_anfs(pre),decode_anfs(post))
    return symbols

def eval_anf(f,bits):
    return sum(bits&m==m for m in f)%2

class Countermodels:
    """Only reject candidates. A proof still requires actual solver UNSAT."""
    def __init__(self,symbolic,j):
        self.n,self.h,self.out,self.phase,self.pre,self.post=symbolic
        self.j=j
        self.models=[]
        self.path_cache={}
        self.live_cache={}
    def path(self,x,y):
        key=(x,y)
        if key not in self.path_cache:
            bits=x|(y<<self.n)
            z=sum(eval_anf(f,bits)<<i for i,f in enumerate(self.out))
            k=sum(c for m,c in self.phase if bits&m==m)%8
            self.path_cache[key]=(z,k)
        return self.path_cache[key]
    def survives(self,x,y,ds):
        key=(x,y,ds)
        if key not in self.live_cache:
            if not ds:
                live=True
            else:
                prev,d=ds[:-1],ds[-1]
                z,k=self.path(x,y)
                w,l=self.path(x,y^d)
                paired=z==w and (l-k)%8==4
                live=self.survives(x,y,prev) and not (
                    paired and self.survives(x,y^d,prev))
            self.live_cache[key]=live
        return self.live_cache[key]
    def add(self,model,ds):
        # The MiniSat model was checked on every CNF clause. Unassigned
        # variables can be completed with zero without falsifying clauses.
        x=sum((i+2 in model)<<i for i in range(self.n))
        y=sum((self.n+i+2 in model)<<i for i in range(self.h))
        z,_=self.path(x,y)
        assert all(eval_anf(f,x) for f in self.pre)
        assert not eval_anf(self.post[self.j],z)
        assert self.survives(x,y,ds),("countermodel does not survive",x,y,ds)
        if (x,y) not in self.models:
            self.models.append((x,y))
    def rejects(self,ds):
        return any(self.survives(x,y,ds) for x,y in self.models)

def screening_model_tests():
    # Paths 0..3; f=[0,4,4,4]. First survivor step removes one pair.
    cm=Countermodels((1,2,((),),((1,4),(2,4),(3,4)),((0,),),((),)),0)
    assert cm.path(0,0)==(0,0) and cm.path(0,3)==(0,4)
    cm.add(frozenset({2,3,4}),())
    assert cm.rejects((1,))
    assert cm.rejects((1,2)) # overlapping pairs cannot be removed twice
    # Countermodels belong only to their conjunct, never another post.

def run_hybrid(directory, tmp, deadline, two_weighted, sat_exe):
    sat_parser_tests()
    screening_model_tests()
    symbolic=load_symbolic(directory)
    sat_file = pathlib.Path(tmp)/"hybrid-sat.cnf"
    result_file = pathlib.Path(tmp)/"hybrid-sat.result"
    def sat(cnf, local_deadline):
        # No result is reused between subprocesses. Timeout is UNKNOWN,
        # never UNSAT. Other malformed responses fail the qualification.
        remaining=min(deadline,local_deadline)-time.monotonic()
        if remaining<=0:
            return None
        sat_file.write_text(cnf)
        result_file.unlink(missing_ok=True)
        try:
            r=subprocess.run([str(sat_exe),"-verb=0",str(sat_file),str(result_file)],
                             capture_output=True,text=True,timeout=min(1,remaining))
        except subprocess.TimeoutExpired:
            return None
        if not result_file.is_file():
            raise ValueError("missing MiniSat result")
        return parse_sat(r.returncode,r.stdout,result_file.read_text(),cnf)
    assert sat("p cnf 1 1\n1 0\n",time.monotonic()+2) == frozenset({1})
    assert sat("p cnf 1 2\n1 0\n-1 0\n",time.monotonic()+2) is False
    assert sat("p cnf 1 1\n1 0\n",time.monotonic()-1) is None
    plans={}
    with (directory/"hybrid-plan.tsv").open() as f:
        for name,j,kind,ds,file in csv.reader(f,delimiter="\t"):
            plans.setdefault((name,int(j)),[]).append((kind,ds,file))
    rr_plans={}
    with (directory/"hybrid-rr.tsv").open() as f:
        for name,status,h,scale,delta,variables,clauses,prep_us in csv.reader(f,delimiter="\t"):
            rr_plans[name]=(status,int(h),int(scale),delta,int(variables),int(clauses),int(prep_us))
    def wmc_verdict(base,delta,n):
        coeff=two_weighted(base,delta)
        if not any(coeff):
            return "PROVED",None,coeff,0.0
        t=time.monotonic()
        prefix=[];witness=0
        for i in range(n):
            l=i+2;prefix.append(-l)
            if not any(two_weighted(base,delta,prefix)):
                prefix[-1]=l;witness|=1<<i
        assert any(two_weighted(base,delta,prefix))
        return "REFUTED",witness,coeff,time.monotonic()-t
    records=[]
    with (directory/"hybrid.tsv").open() as f:
        for name,n,nq,delta,expected,witnesses,build_us,direct_us,plan_us in csv.reader(f,delimiter="\t"):
            n,nq,build_us,direct_us,plan_us=map(int,(n,nq,build_us,direct_us,plan_us))
            delta=list(map(int,delta.split(",")))
            base=(directory/f"hybrid-{name}-wmc.cnf").read_text()
            # Matched direct baseline, complete verdict and witness.
            t=time.monotonic()
            try:
                dv,dw,dc,dw_s=wmc_verdict(base,delta,n)
            except (TimeoutError,subprocess.TimeoutExpired):
                dv,dw,dc,dw_s="UNKNOWN",None,None,0.0
            direct_s=time.monotonic()-t
            status,rh,scale,rd,rv,rcs,rprep=rr_plans[name]
            rr_verdict,rr_witness,rr_coeff,rr_witness_s="UNKNOWN",None,None,0.0
            rr_solver_s=0.0
            if status=="READY":
                rr_base=(directory/f"hybrid-{name}-rr.cnf").read_text()
                t=time.monotonic()
                try:
                    rr_verdict,rr_witness,rr_coeff,rr_witness_s=wmc_verdict(rr_base,list(map(int,rd.split(","))),n)
                    rr_coeff=tuple(v*2**scale for v in rr_coeff)
                except (TimeoutError,subprocess.TimeoutExpired):
                    rr_verdict,rr_witness,rr_coeff,rr_witness_s="UNKNOWN",None,None,0.0
                rr_solver_s=time.monotonic()-t
            rr_row=dict(status=status,verdict=rr_verdict,witness=rr_witness,coeff=rr_coeff,
                        h=rh,scale=scale,vars=rv,clauses=rcs,prep_us=rprep,
                        solver_s=round(rr_solver_s,6),witness_s=round(rr_witness_s,6),
                        total_s=round(rprep/1e6+rr_solver_s,6))
            # Matched same-run ablation. Both policies use the same plan,
            # exact fallback and resource caps; pruning only avoids calls.
            def dispatch(screened):
                t=time.monotonic()
                local_deadline=min(deadline,t+0.5)
                queries=0;skipped=0;used=[];complete=True
                for j in range(nq):
                    cm=Countermodels(symbolic[name],j) if screened else None
                    proved=False
                    for kind,ds,file in plans.get((name,j),[]):
                        if queries>=24 or time.monotonic()>=local_deadline:
                            break
                        directions=() if kind=="guard" else tuple(map(int,ds.split("-")))
                        if cm is not None and cm.rejects(directions):
                            skipped+=1
                            continue
                        queries+=1
                        outcome=sat((directory/file).read_text(),local_deadline)
                        if outcome is False:
                            used.append((j,kind,ds));proved=True;break
                        if outcome is None:
                            break
                        if cm is not None:
                            cm.add(outcome,directions)
                    if not proved:
                        complete=False;break
                sat_s=time.monotonic()-t
                fallback_s=0.0;hw_s=0.0
                if complete:
                    hv,hw,hc="PROVED",None,(0,0)
                    route="SAT_"+max((x[1] for x in used),key=lambda k:{"guard":0,"single":1,"multi":2}[k],default="guard").upper()
                else:
                    route="DIRECT_WMC_FALLBACK"
                    t=time.monotonic()
                    try:
                        hv,hw,hc,hw_s=wmc_verdict(base,delta,n)
                    except (TimeoutError,subprocess.TimeoutExpired):
                        hv,hw,hc,hw_s="UNKNOWN",None,None,0.0
                    fallback_s=time.monotonic()-t
                return dict(route=route,verdict=hv,witness=hw,coeff=hc,
                            proofs=used,sat_queries=queries,skipped=skipped,
                            sat_s=round(sat_s,6),fallback_s=round(fallback_s,6),
                            witness_s=round(hw_s,6),
                            total_s=round((build_us+direct_us+plan_us)/1e6+sat_s+fallback_s,6))
            # Alternate order to reduce systematic warm-up bias.
            if len(records)%2:
                screened=dispatch(True);plain=dispatch(False)
            else:
                plain=dispatch(False);screened=dispatch(True)
            # Oracle check only after both routes finish.
            expected=tuple(map(int,expected.split(",")))
            witnesses=set() if witnesses=="-" else set(map(int,witnesses.split(",")))
            truth="REFUTED" if witnesses else "PROVED"
            for verdict,witness,coeff in [(dv,dw,dc),(rr_verdict,rr_witness,rr_coeff)]+[
                    (r["verdict"],r["witness"],r["coeff"]) for r in (plain,screened)]:
                if verdict=="UNKNOWN":
                    continue
                assert verdict==truth and tuple(coeff)==expected,(name,verdict,truth,coeff,expected)
                assert (witness in witnesses) if witnesses else witness is None
            row=dict(case=name,direct_verdict=dv,direct_witness=dw,
                     build_us=build_us,direct_encoding_us=direct_us,plan_export_us=plan_us,
                     direct_total_s=round((build_us+direct_us)/1e6+direct_s,6),
                     plain=plain,screened=screened,standard_rr=rr_row)
            print("HOARE_SCREENED_HYBRID "+json.dumps(row),flush=True)
            records.append(row)
    assert len(records)==16
    assert sum(r["screened"]["skipped"] for r in records)>0
    print("HOARE_SCREENED_HYBRID_SUMMARY "+json.dumps(dict(cases=len(records),
          completed=sum(r["direct_verdict"]!="UNKNOWN" and all(r[k]["verdict"]!="UNKNOWN" for k in ("plain","screened")) for r in records),
          standard_rr_completed=sum(r["standard_rr"]["verdict"]!="UNKNOWN" for r in records),
          all_four_completed=sum(r["direct_verdict"]!="UNKNOWN" and all(r[k]["verdict"]!="UNKNOWN" for k in ("plain","screened","standard_rr")) for r in records),
          plain_queries=sum(r["plain"]["sat_queries"] for r in records),
          screened_queries=sum(r["screened"]["sat_queries"] for r in records),
          skipped=sum(r["screened"]["skipped"] for r in records),
          plain_proofs=sum(r["plain"]["route"].startswith("SAT_") for r in records),
          screened_proofs=sum(r["screened"]["route"].startswith("SAT_") for r in records))),flush=True)


if __name__ == "__main__":
    main()
