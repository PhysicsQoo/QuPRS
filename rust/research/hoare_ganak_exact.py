"""Research-only exact external #SAT experiment; not a production adapter."""
import csv
import decimal
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

EXPECTED_SHA = "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"

def parse_count(stdout, bound):
    lines = stdout.splitlines()
    def single(prefix):
        rows = [l[len(prefix):].strip() for l in lines if l.startswith(prefix)]
        if len(rows) != 1:
            raise ValueError("missing or conflicting " + prefix)
        return rows[0]
    if any(l.startswith("c s approx") for l in lines):
        raise ValueError("approximate result")
    if single("c s type ") != "mc":
        raise ValueError("wrong counting mode")
    count = single("c s exact arb int ")
    if not re.fullmatch(r"[0-9]+", count):
        raise ValueError("not an exact unsigned integer")
    n = int(count)
    if n > bound:
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
        def count(base, assumptions):
            nonlocal calls, solver_seconds
            lines = base.splitlines()
            _, _, vs, cs = lines[0].split()
            v, c = int(vs), int(cs)
            assert len(lines) == c + 1
            assert all(0 < abs(l) <= v for l in assumptions)
            query.write_text(f"c t mc\np cnf {v} {c+len(assumptions)}\n" +
                             "\n".join(lines[1:]) + "\n" +
                             "".join(f"{l} 0\n" for l in assumptions))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("experiment budget")
            t = time.monotonic()
            r = subprocess.run([str(exe), "--mode", "0", "--prob", "0", str(query)],
                               capture_output=True, text=True, timeout=min(5, remaining),
                               check=True)
            solver_seconds += time.monotonic() - t
            calls += 1
            return parse_count(r.stdout, 2**v)
        def buckets(base, delta, prefix=()):
            return [count(base, list(prefix) + [l if j >> i & 1 else -l
                     for i, l in enumerate(delta)]) for j in range(8)]
        def signed(ns):
            return tuple(ns[j]-ns[j+4] for j in range(4))
        # Qualify unweighted free variables, UNSAT and large integers.
        assert count("p cnf 3 1\n1 0\n", []) == 4
        assert count("p cnf 1 2\n1 0\n-1 0\n", []) == 0
        assert count("p cnf 61 1\n1 0\n", []) == 2**60
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
                assert ns == expected, (name, route, ns, expected)
                coefficients = signed(ns)
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
                        if not any(signed(buckets(base, delta, prefix))):
                            prefix[-1] = l
                            witness |= 1 << i
                    assert any(signed(buckets(base, delta, prefix)))
                    assert witness in witnesses
                else:
                    assert not witnesses
                row = dict(case=name, route=route, counts=ns,
                           verdict="PROVED" if witness is None else "REFUTED",
                           witness=witness, solver_wall_s=round(solver_seconds-start, 6))
                records.append(row)
                print("HOARE_GANAK_EXACT " + json.dumps(row), flush=True)
        assert len(records) == 14 and len(direct) == 7
        print(f"HOARE_GANAK_PASS variants={len(records)} calls={calls} solver_wall_s={solver_seconds:.6f} mode=0 prob=0")

if __name__ == "__main__":
    main()
