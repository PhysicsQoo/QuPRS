"""Paired CNF structure diagnostics, not a solver or runtime predictor.
Both encodings come from one source-locked native residual. Preserve
original precision and construction limits, and distinguish censored runs.
"""
import hashlib
import heapq
import itertools
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from conditional_rr_stitch import ROOT, GENERIC_NEGATIVE

SCOPE = [("qwalk-noancilla_5", "positive"),
         ("qwalk-noancilla_5", "random_rotation"),
         ("grover-noancilla_6", "positive"),
         ("grover-noancilla_6", "random_rotation")]
EDGE_CAP = 250_000
STEP_CAP = 4096

def parse(text):
    header = None
    clauses, weighted = [], set()
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "p":
            assert header is None and len(fields) == 4 and fields[1] == "cnf"
            header = tuple(map(int, fields[2:]))
        elif fields[:3] == ["c", "p", "weight"]:
            assert len(fields) == 7 and fields[-1] == "0"
            weighted.add(abs(int(fields[3])))
        elif fields[0] != "c":
            literals = list(map(int, fields))
            assert literals[-1] == 0 and 0 not in literals[:-1]
            clauses.append(literals[:-1])
    assert header is not None
    n, m = header
    assert n >= 0 and m == len(clauses)
    assert all(0 < abs(v) <= n for c in clauses for v in c)
    assert all(0 < v <= n for v in weighted)
    return n, clauses, weighted

def propagate(clauses):
    # Deterministic unit propagation, independent of weighted values.
    # Structural diagnostic only; does not change the emitted solver input.
    fixed = {}
    remaining = [set(c) for c in clauses if not any(-v in c for v in c)]
    while True:
        if any(not c for c in remaining):
            return fixed, remaining, True
        units = sorted({next(iter(c)) for c in remaining if len(c) == 1})
        if not units:
            return fixed, remaining, False
        for u in units:
            v, value = abs(u), u > 0
            if v in fixed and fixed[v] != value:
                return fixed, remaining, True
            fixed[v] = value
        remaining = [{v for v in c if abs(v) not in fixed}
                     for c in remaining
                     if not any(abs(v) in fixed and fixed[abs(v)] == (v > 0) for v in c)]

def graph_metrics(vertices, clauses, weighted):
    adj = {v: set() for v in vertices}
    for c in clauses:
        for u, v in itertools.combinations(sorted({abs(x) for x in c}), 2):
            adj[u].add(v)
            adj[v].add(u)
    unseen = set(adj)
    sizes = []
    while unseen:
        todo = [unseen.pop()]
        size = 0
        while todo:
            u = todo.pop()
            size += 1
            new = adj[u] & unseen
            unseen.difference_update(new)
            todo.extend(new)
        sizes.append(size)
    edges = sum(map(len, adj.values())) // 2
    result = dict(vertices=len(adj), edges=edges, components=len(sizes),
                  largest_component=max(sizes, default=0),
                  max_degree=max(map(len, adj.values()), default=0),
                  weighted_variables=len(weighted & adj.keys()),
                  weighted_degree_sum=sum(len(adj[v]) for v in weighted & adj.keys()))
    # Deterministic min-degree ordering, a heuristic width upper bound only
    # if the ordering completes. Cap fill and steps, never call it treewidth.
    heap = [(len(ns), v) for v, ns in adj.items()]
    heapq.heapify(heap)
    width = steps = 0
    fill = 0
    stop = "complete"
    while adj:
        if steps >= STEP_CAP or edges > EDGE_CAP:
            stop = "budget"
            break
        d, v = heapq.heappop(heap)
        if v not in adj or d != len(adj[v]):
            continue
        ns = sorted(adj[v])
        # Conservative bound on additional edges avoids an oversized fill.
        if edges + d*(d-1)//2 > EDGE_CAP:
            stop = "fill_preflight"
            break
        width = max(width, d)
        steps += 1
        for u in ns:
            adj[u].remove(v)
        del adj[v]
        edges -= d
        for u, z in itertools.combinations(ns, 2):
            if z not in adj[u]:
                adj[u].add(z)
                adj[z].add(u)
                edges += 1
                fill += 1
        for u in ns:
            heapq.heappush(heap, (len(adj[u]), u))
    result.update(ordering="min_degree_id_tie", ordering_stop=stop,
                  ordering_steps=steps, observed_width=width,
                  width_upper_bound=width if not adj else None, fill_edges=fill)
    return result

def metrics(path):
    start = time.monotonic()
    data = path.read_bytes()
    n, clauses, weighted = parse(data.decode())
    fixed, remaining, conflict = propagate(clauses)
    full = graph_metrics(range(1, n+1), clauses, weighted)
    reduced = None if conflict else graph_metrics(
        set(range(1, n+1)) - fixed.keys(), remaining, weighted)
    return dict(sha256=hashlib.sha256(data).hexdigest(), variables=n,
                clauses=len(clauses), literals=sum(map(len, clauses)),
                unit_fixed=len(fixed), conflict=conflict,
                after_unit_clauses=len(remaining), full=full, after_unit=reduced,
                diagnostic_s=time.monotonic()-start)

def controls():
    n, c, w = parse("p cnf 4 3\nc p weight 1 1.0 0.0 0\n1 0\n-1 2 0\n3 4 0\n")
    fixed, rem, conflict = propagate(c)
    assert n == 4 and fixed == {1: True, 2: True} and not conflict and rem == [{3, 4}]
    g = graph_metrics(range(1,5), c, w)
    assert (g["edges"], g["components"], g["largest_component"], g["width_upper_bound"]) == (2,2,2,1)
    assert propagate([[1],[-1]])[2]
    assert graph_metrics(range(1,4), [[1,2,3]], set())["width_upper_bound"] == 2
    print("CPR_STRUCTURE_CONTROLS_PASS", flush=True)

def main(out):
    controls()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases = {x["id"]: x for x in manifest["cohorts"]["table2_mqt"]["cases"]}
    results = []
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))
    for name, variant in SCOPE:
        c = cases[name]
        target = c["transpiled"] if variant == "positive" else dict(
            path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,
            git_blob_sha1=GENERIC_NEGATIVE[name])
        paths, hashes = [], []
        for entry in (c["source"], target):
            path = ROOT/entry["path"]
            data = path.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() == entry["git_blob_sha1"]
            paths.append(path)
            hashes.append(hashlib.sha256(data).hexdigest())
        dest = out/(name+"-"+variant)
        dest.mkdir()
        env = dict(os.environ, CRR_CASE=name, CRR_VARIANT=variant, CRR_SOURCE=str(paths[0]),
                   CRR_TARGET=str(paths[1]), CRR_POLICY="strict", CRR_SCHEDULE="difference",
                   CRR_GENERIC_ARM="conditional", CRR_LIFT_INDEXED="1", CRR_BRA_RESCUE="1",
                   CPR_CNF_DIR=str(dest))
        cmd = ["timeout","--kill-after=2s","35s","cargo","test","--release","--locked",
               "--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment",
               "conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
        r = subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
        (dest/"native.stdout").write_text(r.stdout)
        (dest/"native.stderr").write_text(r.stderr)
        row = dict(case=name,variant=variant,source_sha256=hashes,returncode=r.returncode)
        files = [dest/"raw.cnf",dest/"extracted.cnf"]
        if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():
            row.update(status="censored")
        else:
            assert r.returncode == 0, r.stderr[-4000:]
            emitted = [l for l in r.stdout.splitlines() if l.startswith("CPR_CNF_EMITTED ")]
            if not emitted and not any(f.exists() for f in files):
                row.update(status="construction_incomplete")
            else:
                assert len(emitted) == 2 and all(f.exists() for f in files)
                assert any(" mode=raw " in l for l in emitted) and any(" mode=extracted " in l for l in emitted)
                row.update(status="paired",receipts=emitted,raw=metrics(files[0]),extracted=metrics(files[1]))
        results.append(row)
        print("CPR_STRUCTURE "+json.dumps(row,sort_keys=True),flush=True)
    (out/"cpr-structure.json").write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    # Three prior completed coordinates must yield paired encodings; the
    # Grover negative is diagnostic, not an imposed solver-verdict gate.
    assert all(row["status"]=="paired" for row in results[:3]), results
    print("CPR_STRUCTURE_GATE=PASS solver_invocations=0 paired="+str(sum(row["status"]=="paired" for row in results)),flush=True)

if __name__ == "__main__":
    main(Path(sys.argv[1]))
