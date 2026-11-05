"""QOO-157 P9 research-only structural features. No timing; no shipping policy."""
import argparse, hashlib, heapq, json
from pathlib import Path

EXPECTED = {
    "grover4_eq": "e75f823656177295a5c10c3e2fc2bfd6608a20eb2b96f7477e586104e14f6a05",
    "qaoa7_neq": "66375ceba75cd7b02e8f4a723c534618d5206dc2ebfaf02255d4c863f79a3123",
    "qpeexact8_eq": "f747148c96c48bbb4349585652fac805117e964112cdb082feb096a28a80feb0",
    "qft16_eq": "c7fe1574adb4221bf890aa1f2181dbcdaf793fa54a4438c60a98e5b620e0c1fd",
}

def feature(path, expected):
    b = path.read_bytes()
    digest = hashlib.sha256(b).hexdigest()
    if digest != expected:
        raise ValueError("original QuPRS weighted CNF SHA drift")
    n, nc = None, None
    clauses, weights = [], {}
    for line in b.decode().splitlines():
        a = line.split()
        if not a: continue
        if a[:3] == ["c", "p", "weight"]:
            if len(a) != 7 or a[-1] != "0":
                raise ValueError("weight syntax")
            v = int(a[3])
            if v == 0 or v in weights: raise ValueError("duplicate literal weight")
            weights[v] = (a[4], a[5])
        elif a[0] == "c": continue
        elif a[:2] == ["p", "cnf"]:
            if n is not None or len(a) != 4: raise ValueError("header")
            n, nc = int(a[2]), int(a[3])
        else:
            if n is None or a[-1] != "0": raise ValueError("clause syntax")
            vs = [int(s) for s in a[:-1]]
            if any(v == 0 or abs(v) > n for v in vs): raise ValueError("literal bounds")
            clauses.append(vs)
    if n is None or len(clauses) != nc: raise ValueError("clause count")
    graph = {v:set() for v in range(1, n+1)}
    for cl in clauses:
        vars_ = list(set(abs(v) for v in cl))
        for i, v in enumerate(vars_):
            for w in vars_[i+1:]:
                graph[v].add(w); graph[w].add(v)
    ne = sum(map(len,graph.values())) // 2
    deg = {v:len(ws) for v,ws in graph.items()}
    heap = [(d,v) for v,d in deg.items()]
    heapq.heapify(heap)
    live = set(graph)
    k = 0
    while live:
        d, v = heapq.heappop(heap)
        if v not in live or d != deg[v]: continue
        k=max(k,d); live.remove(v)
        for w in graph[v]:
            if w in live:
                deg[w]-=1; heapq.heappush(heap,(deg[w],w))
    return dict(sha256=digest,vars=n,clauses=nc,edges=ne,
                primal_degeneracy=k,
                protected_text_weight_count=sum(weights.get(v) != weights.get(-v)
                    for v in range(1,n+1)))

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cnfs",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    found={case:feature(a.cnfs/(case+".cnf"),sha)
           for case,sha in EXPECTED.items()}
    if found["qaoa7_neq"]["primal_degeneracy"]!=2 or found["qft16_eq"]["primal_degeneracy"]!=11:
        raise ValueError("source structural anchors changed")
    result={"status":"P9_SOURCE_FEATURES_PASS_4_OF_4",
            "scope":"original CNF read only; no solver; no timing",
            "candidate_policy":"NOT_QUALIFIED_TO_SHIP",
            "held_out_QAOA9_11_QFT20_22":"MISSING_SOURCE_SCIENCE",
            "cases":found}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"k":{x:y["primal_degeneracy"] for x,y in found.items()}}))
