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


def run_gpmc_pure(directory, exe, tmp, deadline):
    """Two exact natural-weight queries, with arbitrary-precision packed counts.

    Packing avoids negative weights and does not require complex MPFR
    or a floating-point near-zero threshold. Every model contributes
    either 1 or radix. radix=2^(CNF variables+1) exceeds either bucket.
    """
    query_file=pathlib.Path(tmp)/"gpmc-pure.cnf"
    query_cap=5
    long_metrics=None
    def count(base, assumptions, weighted_lit, end):
        header,*clauses=base.splitlines()
        p,kind,v,c=header.split();v,c=int(v),int(c)
        assert (p,kind)==("p","cnf") and len(clauses)==c
        assert all(0<abs(l)<=v for l in assumptions)
        radix=1<<(v+1)
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
        result=parse_gpmc_integer(stdout,mode,(1<<v)*(radix if mode=="wmc" else 1))
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
    deadline=time.monotonic()+45
    run_residual_hybrid(directory,solve,deadline,rows)
    # Preserve the original discovery protocol on explicit request. Default
    # to the frozen long cohort rather than rerunning all 19 known timeouts.
    if os.environ.get("HOARE_SCALE_DISCOVERY")=="1":
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
            else:
                run_affine_pilot(directory/"scale-discovery",solve,deadline,long_metrics)
        long_metrics=None
    return rows



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
