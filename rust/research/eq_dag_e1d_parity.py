#!/usr/bin/env python3
"""Exact sparse parity inversion of the rational-radian component only.
Research census; no numerical weights, solver, or production changes.
"""
import ast
from collections import Counter
from fractions import Fraction as F
from itertools import combinations, product
import hashlib
import heapq
import json
from pathlib import Path
import re
import sys
import zipfile

HEAD = '8811544a462338569bc5a375e3df41fdd18ea3b8'
TREE = 'b7ebfdcf3cfdac115bf971fddc92306bc66adde8'
ZIP_SHA = 'd0ec708935a8c412c90ad78dbe43a5f3a628778dc7b0181c665848fcfe7e1e12'
CAP = 3_000_000
RAD = re.compile(r'Some\(Ratio \{ numer: (-?\d+), denom: (\d+) \}\)')

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read_snapshot(b):
    p, f, meta = {}, {}, {}
    for line in b.decode().splitlines():
        a = line.split('\t')
        if a[0] == 'p':
            m = tuple(ast.literal_eval(a[1]))
            assert m == tuple(sorted(set(m))) and m not in p
            assert a[5] == '{}', 'symbolic coefficient unsupported'
            rad = RAD.fullmatch(a[4])
            assert rad or a[4] == 'None'
            p[m] = (F(int(a[2]), int(a[3])) % 1, F(int(rad[1]), int(rad[2])) if rad else F(0))
        elif a[0] == 'output':
            i = int(a[1]); assert i not in f; f[i] = []
        elif a[0] == 'f':
            f[int(a[1])].append(tuple(ast.literal_eval(a[2])))
        else:
            assert len(a) == 2 and a[0] not in meta; meta[a[0]] = a[1]
    n, h = int(meta['n']), int(meta['h'])
    domain = set(ast.literal_eval(meta['vars']))
    assert len(domain) == n+h and set(f) == set(range(n)) and set(range(n)) <= domain
    assert all(set(m) <= domain for m in list(p)+[m for v in f.values() for m in v])
    return n, h, p, f

def invert(source, cap=CAP):
    """Triangular inverse of XOR arithmetic expansion, largest degree first.
    A cap failure discards the entire candidate. Exact rationals, no tolerance.
    """
    pending = {m: v for m, v in source.items() if v}
    q = [(-len(m), m) for m in pending if m]; heapq.heapify(q)
    result, work = {}, 0
    if () in pending:
        result[()] = pending.pop(())  # constant is not XOR of empty set
    while q:
        _, m = heapq.heappop(q)
        v = pending.pop(m, F(0))
        if not v:
            continue
        d = len(m)
        work += (1 << d)-1
        if work > cap:
            return None, work
        c = v / ((-2)**(d-1))
        result[m] = c
        for k in range(1, d):
            dv = c * (-2)**(k-1)
            for s in combinations(m, k):
                if s not in pending:
                    heapq.heappush(q, (-k, s))
                pending[s] = pending.get(s, F(0))-dv
    assert not pending
    return result, work

def replay(parity):
    """Independent forward expansion by mask enumeration, not inverse code."""
    p = {}
    for m, c in parity.items():
        if not m:
            p[()] = p.get((), F(0))+c
            continue
        for mask in range(1, 1 << len(m)):
            s = tuple(v for i,v in enumerate(m) if mask >> i & 1)
            p[s] = p.get(s,F(0))+c*((-2)**(len(s)-1))
    return {m:c for m,c in p.items() if c}

def cost(n,h,p,f,parity):
    # Keep original turns as monomials, merge identical singleton/constant
    # predicates with radian component. Share sorted-prefix XOR gate chains.
    turns = {m:c[0] for m,c in p.items() if c[0]}
    monomial = {m:(v,parity.get(m,F(0)) if len(m)<=1 else F(0)) for m,v in turns.items()}
    for m,v in parity.items():
        if len(m)<=1 and m not in monomial:
            monomial[m]=(F(0),v)
    multi = {m:v for m,v in parity.items() if len(m)>=2}
    prefixes = {m[:k] for m in multi for k in range(2,len(m)+1)}
    # Each prefix one neutral XOR (4 clauses); each multi parity factor has
    # a separate weighted alias (2 clauses). This deliberately avoids moving
    # weights onto shared neutral roots. All trace costs unchanged.
    trace_v = trace_c = 0
    for terms in f.values():
        if not terms:
            trace_v += 1; trace_c += 1
        else:
            trace_v += sum(len(m)!=1 for m in terms)+len(terms)-1
            trace_c += sum(len(m)+1 for m in terms if len(m)!=1)+4*(len(terms)-1)
        trace_c += 2
    factors = len(monomial)+len(multi)
    return dict(factors=factors,variables=n+h+trace_v+factors+len(prefixes),clauses=trace_c+sum(len(m)+1 for m in monomial)+2*len(multi)+4*len(prefixes),shared_xor_nodes=len(prefixes),flat_variables=n+h+trace_v+len(p),flat_clauses=trace_c+sum(len(m)+1 for m in p))

def controls():
    q = {():F(7,13),(0,1,2,3):F(19,23),(1,2):F(-5,11),(4,):F(3,7)}
    p = replay(q)
    candidate,work = invert(p)
    assert candidate == q and replay(candidate)==p
    assert invert(p,0)[0] is None
    for b in product((0,1),repeat=5):
        x=sum(c*int(all(b[i] for i in m)) for m,c in p.items())
        y=sum(c*(sum(b[i] for i in m)%2 if m else 1) for m,c in q.items())
        assert x==y
    wrong=dict(q);wrong[(0,1,2,3)]+=F(1,10**40)
    assert replay(wrong)!=p

def main():
    controls()
    src,out=map(Path,sys.argv[1:])
    assert sha(src.read_bytes())==ZIP_SHA
    rows=[]
    with zipfile.ZipFile(src) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        for line in z.read('SHA256SUMS').decode().splitlines():
            digest,name=line.split('  ',1)
            assert sha(z.read(name.removeprefix('./')))==digest
        assert z.read('head.txt').decode().strip()==HEAD and z.read('tree.txt').decode().strip()==TREE
        prov=json.loads(z.read('provenance.json'))
        assert prov['head']==HEAD and prov['tree']==TREE
        for r in map(json.loads,z.read('rows.jsonl').decode().splitlines()):
            if not(r['cnf'] and r['residual_sha256']): continue
            arm=r['case']+'-hybrid/'
            snap=z.read(arm+'residual.tsv');cnf=z.read(arm+'actual.cnf')
            assert sha(snap)==r['residual_sha256'] and sha(cnf)==r['cnf']['sha256']
            n,h,p,f=read_snapshot(snap)
            rad={m:c[1] for m,c in p.items() if c[1]}
            parity,work=invert(rad)
            row=dict(case=r['case'],source_status=r['status'],source_residual_sha256=sha(snap),original_phase_terms=len(p),original_radian_terms=len(rad),subset_work=work,status='WORK_CAP' if parity is None else 'OK')
            if parity is not None:
                assert replay(parity)==rad
                c=cost(n,h,p,f,parity)
                assert (c['flat_variables'],c['flat_clauses'])==(r['cnf']['variables'],r['cnf']['clauses'])
                row.update(c,parity_terms=len(parity),parity_degree_hist=dict(Counter(map(len,parity))),exact_radian_replay=True,parities=[dict(support=m,coefficient=str(v)) for m,v in sorted(parity.items())])
            rows.append(row)
            print('E1D_ARM',json.dumps({k:v for k,v in row.items() if k!='parities'}),flush=True)
    assert len(rows)==12
    summary=dict(arms=len(rows),eligible=sum(r['status']=='OK' for r in rows),factor_positive=sum(r['status']=='OK' and r['factors']<r['original_phase_terms'] for r in rows),solver_calls=0,scope='exact radian parity inversion; structural model only')
    out.write_text(json.dumps(dict(source_zip_sha256=ZIP_SHA,head=HEAD,tree=TREE,summary=summary,rows=rows),indent=2)+'\n')
    print('E1D_SUMMARY',json.dumps(summary),flush=True)
if __name__=='__main__':
    main()
