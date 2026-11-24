"""Research-only exact external #SAT experiment; not a production adapter."""
import csv
import decimal
import hashlib
from fractions import Fraction
import json
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
        def count(base, assumptions, negative_lit=None):
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
            remaining = deadline - time.monotonic()
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
        def two_weighted(base, delta, prefix=()):
            # A=N0-N4: d0=d1=0, sign (-1)^d2.
            # B=N1-N3: d0=1,d2=0, sign (-1)^d1.
            # delta entries are signed literals; assign weights to literals
            # rather than variable IDs to support negated selectors.
            d0,d1,d2 = delta
            return (count(base, list(prefix)+[-d0,-d1], negative_lit=d2),
                    count(base, list(prefix)+[d0,-d2], negative_lit=d1))

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
            for name, route, n, h, scale, delta, expected, witness, vars_, clauses, encoding_us, status in csv.reader(fh, delimiter="\t"):
                n,h,scale,vars_,clauses,encoding_us = map(int,(n,h,scale,vars_,clauses,encoding_us))
                delta = list(map(int,delta.split(",")))
                expected = tuple(map(int,expected.split(",")))
                row = dict(case=name,route=route,n=n,h=h,vars=vars_,clauses=clauses,
                           encoding_us=encoding_us,expected_raw=expected,known_witness=witness,
                           status=status,two_status="NOT_RUN",four_status="NOT_RUN",witness_status="NOT_REQUIRED" if witness=="-" else "NOT_RUN")
                if status=="READY":
                    base=(directory/f"scale-{name}-{route}.cnf").read_text()
                    for method,fn in [("two",two_weighted),("four",four_counts)]:
                        start=time.monotonic()
                        try:
                            coeff=fn(base,delta)
                            assert tuple(v*2**scale for v in coeff)==expected,(name,route,method,coeff,expected)
                            row[method+"_status"]="PASS"
                            row[method+"_coeff"]=coeff
                        except (subprocess.TimeoutExpired,TimeoutError):
                            row[method+"_status"]="UNKNOWN_TIMEOUT"
                        row[method+"_root_s"]=round(time.monotonic()-start,6)
                    if witness!="-" and row["two_status"]=="PASS":
                        x=int(witness)
                        prefix=[i+2 if x>>i&1 else -(i+2) for i in range(n)]
                        try:
                            assert any(two_weighted(base,delta,prefix))
                            row["witness_status"]="PASS"
                        except (subprocess.TimeoutExpired,TimeoutError):
                            row["witness_status"]="UNKNOWN_TIMEOUT"
                    row["status"]="PASS" if row["two_status"]==row["four_status"]=="PASS" and row["witness_status"] in ("PASS","NOT_REQUIRED") else "UNKNOWN_RESOURCE"
                scaled.append(row)
                print("HOARE_GANAK_SCALE "+json.dumps(row),flush=True)
        assert len(scaled)==32
        ok=sum(r["status"]=="PASS" for r in scaled)
        print(f"HOARE_GANAK_SCALE_SUMMARY variants={len(scaled)} pass={ok} unknown={len(scaled)-ok} calls={calls} solver_wall_s={solver_seconds:.6f}")


if __name__ == "__main__":
    main()
