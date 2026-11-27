#!/usr/bin/env python3
"""Independent archived/canonical Flat equivalence via decoded weighted phase/trace hypergraphs."""
import argparse, ast, collections, hashlib, json, time, zipfile
from fractions import Fraction
from pathlib import Path
D='d0ec708935a8c412c90ad78dbe43a5f3a628778dc7b0181c665848fcfe7e1e12'
B='3447cc97563b96e6dd4529e8b25e7af161a0895c51263435e554c97555d1b8cf'
def sha(b): return hashlib.sha256(b).hexdigest()
def archive(p, digest, head, tree):
    assert sha(p.read_bytes())==digest
    z=zipfile.ZipFile(p)
    names=z.namelist(); assert len(names)==len(set(names))
    sealed={}
    for l in z.read('SHA256SUMS').decode().splitlines():
        h,k=l.split(maxsplit=1); k=k.removeprefix('./'); assert k not in sealed; assert sha(z.read(k))==h; sealed[k]=h
    assert set(sealed)=={n for n in names if not n.endswith('/') and n!='SHA256SUMS'}
    assert z.read('head.txt').decode().strip()==head and z.read('tree.txt').decode().strip()==tree
    return z

def parse(data,n,domain):
    lines=data.decode().splitlines(); h0,h1,nv,nc=lines[0].split();assert (h0,h1)==('p','cnf');nv,nc=int(nv),int(nc)
    w={};cl=[]
    for l in lines[1:]:
        if l=='c t wmc':continue
        if l.startswith('c p weight '):
            _,_,_,z,re,im,zero=l.split();z=int(z);assert zero=='0' and 0<abs(z)<=nv and z not in w;w[z]=(Fraction(re),Fraction(im))
        else:
            c=tuple(map(int,l.split()));assert c[-1]==0 and all(0<abs(v)<=nv for v in c[:-1]);cl.append(c[:-1])
    assert len(cl)==nc and all(-z in w for z in w) and all(w[-z]==(1,0) for z in w if z>0)
    weighted={z for z in w if z>0};used=set();aux=set();prim=set();terms=[];defs={};i=0
    def reg(z,inputs):
        assert z>0 and z not in aux and z not in prim and z not in inputs
        aux.add(z)
        for v in inputs:
            assert v>0 and v not in weighted
            if v not in aux:prim.add(v)
    def andgate(weight=False):
        nonlocal i
        c=cl[i]
        if len(c)==1:
            z=abs(c[0]); assert not weight or c[0]>0
            reg(z,());i+=1;return z,{()} if c[0]>0 else set()
        assert len(c)==2 and c[0]<0 and c[1]>0
        z=-c[0];vs=[]
        while i<len(cl) and len(cl[i])==2 and cl[i][0]==-z and cl[i][1]>0:
            vs.append(cl[i][1]);i+=1
        assert vs and len(set(vs))==len(vs)
        assert cl[i]==(z,*(-v for v in vs)) or (weight and len(vs)==1 and cl[i]==(-vs[0],z))
        i+=1;reg(z,vs)
        assert all(v not in aux for v in vs)
        return z,{tuple(sorted(vs))}
    while used!=weighted:
        z,poly=andgate(True);assert z in weighted and z not in used and len(poly)==1;used.add(z);terms.append((next(iter(poly)),w[z]))
    outputs=[];anchors=[]
    def get(v):
        if v in defs:return defs[v]
        assert v not in aux and v not in weighted;prim.add(v);return {(v,)}
    for out_i in range(n):
        while True:
            c=cl[i];d=cl[i+1] if i+1<len(cl) else ()
            if len(c)==2 and c[0]<0 and c[1]>0 and d==tuple(-v for v in c):
                a,b=-c[0],c[1]; assert a not in aux and a not in weighted;prim.add(a);anchors.append(a);outputs.append(get(b));i+=2;break
            if len(c)==3:
                a,b,z=map(lambda v:-v,c);assert min(a,b,z)>0 and cl[i:i+4]==[(-a,-b,-z),(a,b,-z),(a,-b,z),(-a,b,z)]
                x,y=get(a),get(b);reg(z,(a,b));defs[z]=x^y;i+=4
            else:
                z,poly=andgate();assert z not in weighted;defs[z]=poly
    assert i==len(cl) and len(set(anchors))==n and not (prim&aux)
    allprim=set(range(1,nv+1))-aux
    assert prim<=allprim and len(allprim)==len(domain)
    # All non-primary variables defined by full biconditionals; unused primaries retained.
    return allprim,terms,outputs,anchors

def snapshot(data):
    out={};phase=[];meta={}
    for l in data.decode().splitlines():
        a=l.split('\t')
        if a[0]=='p':phase.append(tuple(ast.literal_eval(a[1])))
        elif a[0]=='output':out[int(a[1])]=set()
        elif a[0]=='f':out[int(a[1])].add(tuple(ast.literal_eval(a[2])))
        else:meta[a[0]]=a[1]
    n,h=int(meta['n']),int(meta['h']);domain=ast.literal_eval(meta['vars']);assert len(domain)==n+h
    return n,h,domain,phase,[out[i] for i in range(n)]
def canon_edges(terms,outputs):
    # Phase weights exact as serialized. Trace ANF terms colored by output position.
    return [(('phase',w),m) for m,w in terms]+[(('output',i),m) for i,f in enumerate(outputs) for m in f]
def match(a,b):
    va,ta,oa,aa=a;vb,tb,ob,ab=b
    es=[canon_edges(ta,oa),canon_edges(tb,ob)]
    colors=[{v:0 for v in va},{v:0 for v in vb}]
    for idx,anchors in enumerate((aa,ab)):
        for i,v in enumerate(anchors): colors[idx][v]=i+1
    labels={l:i for i,l in enumerate(dict.fromkeys(l for e in es for l,_ in e))}
    def signatures(idx):
        col=colors[idx];sig={v:[] for v in col}
        for l,m in es[idx]:
            key=(labels[l],tuple(sorted(col[v] for v in m)))
            for v in m:sig[v].append(key)
        return {v:(col[v],tuple(sorted(s))) for v,s in sig.items()}
    iterations=0
    for _ in range(len(va)):
        s=[signatures(0),signatures(1)];lookup={};new=[]
        for q in s:new.append({v:lookup.setdefault(k,len(lookup)) for v,k in q.items()})
        assert collections.Counter(new[0].values())==collections.Counter(new[1].values()),'incompatible colored hypergraphs'
        iterations+=1
        old_n=len(set(colors[0].values()));colors=new
        if len(set(new[0].values()))==old_n:break
    groups=[collections.defaultdict(list),collections.defaultdict(list)]
    for j,col in enumerate(colors):
        for v,c in col.items():groups[j][c].append(v)
    mapping={v:w for c,g in groups[0].items() for v,w in zip(sorted(g),sorted(groups[1][c]))}
    def valid(m):
        return ([m[v] for v in aa]==ab and collections.Counter((l,tuple(sorted(m[v] for v in e))) for l,e in es[0])==collections.Counter((l,tuple(sorted(e))) for l,e in es[1]))
    # Color refinement is only a candidate generator; verify full witness independently.
    ok=valid(mapping)
    return ok,mapping,iterations,sorted((len(g) for g in groups[0].values() if len(g)>1),reverse=True)

def controls():
    # Tiny exact weighted CNF: phase root 4 iff primary 1, trace 1=2, free 3.
    cnf=b"p cnf 4 4\nc t wmc\nc p weight 4 0 1 0\nc p weight -4 1 0 0\n-4 1 0\n-1 4 0\n-1 2 0\n1 -2 0\n"
    x=parse(cnf,1,[0,1,2]); assert x[0]=={1,2,3}
    assert match(x,x)[0]
    def reject(fn):
        try: res=fn()
        except AssertionError: return
        assert res[0] is False, 'invalid witness accepted'
    reject(lambda: parse(cnf.replace(b'-1 4 0',b'1 4 0'),1,[0,1,2]))
    reject(lambda: parse(cnf.replace(b'p cnf 4 4',b'p cnf 3 4'),1,[0,1,2]))
    reject(lambda: parse(cnf.replace(b'p cnf 4 4',b'p cnf 5 4'),1,[0,1,2]))
    reject(lambda: parse(cnf.replace(b'weight -4 1 0',b'weight -4 0 1'),1,[0,1,2]))
    a=({1,2},[((1,),(Fraction(0),Fraction(1))),((2,),(Fraction(1),Fraction(0)))],[{(1,)},{(2,)}],[1,2])
    b=(a[0],[(a[1][0][0],a[1][1][1]),(a[1][1][0],a[1][0][1])],a[2],a[3])
    reject(lambda: match(a,b))  # same weight multiset, wrong anchored support
    reject(lambda: match(a,(a[0],a[1],[{(2,)},{(2,)}],a[3])))
    print('ARCHIVE_REPLAY_CONTROLS_PASS negatives=6',flush=True)


def main():
    controls()
    p=argparse.ArgumentParser();p.add_argument('--d1d',type=Path,required=True);p.add_argument('--e1b',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    dz=archive(a.d1d,D,'8811544a462338569bc5a375e3df41fdd18ea3b8','b7ebfdcf3cfdac115bf971fddc92306bc66adde8');bz=archive(a.e1b,B,'2addb665bd8015791c5ee7527a8ce0de5bf8e3a1','f3c63a58c6a7ab651e0117e2a847ffa52b1c0f47');receipts=json.loads(bz.read('receipts.json'))['rows'];result=[]
    for r in receipts:
        t=time.monotonic();case=r['case'];snap=dz.read(case+'-hybrid/residual.tsv');orig=dz.read(case+'-hybrid/actual.cnf');flat=bz.read(case+'-flat.cnf');assert sha(snap)==r['source_residual_sha256'] and sha(orig)==r['original_cnf_sha256'] and sha(flat)==r['flat_sha256']
        n,h,domain,phase,output=snapshot(snap);x=parse(orig,n,domain);y=parse(flat,n,domain)
        ids={v:i+1 for i,v in enumerate(domain)};assert y[0]==set(ids.values()) and y[3]==[ids[i] for i in range(n)];assert [m for m,w in y[1]]==[tuple(ids[v] for v in m) for m in sorted(phase)];assert y[2]==[{tuple(ids[v] for v in m) for m in f} for f in output]
        ok,mapping,iterations,ambiguous=match(x,y);row=dict(case=case,status='PASS' if ok else 'INCONCLUSIVE',n=n,h=h,phase_terms=len(phase),refinement_rounds=iterations,ambiguous_color_classes=ambiguous,archived_to_canonical_primary=mapping if ok else None,seconds=round(time.monotonic()-t,3));result.append(row);print({k:v for k,v in row.items() if k!='archived_to_canonical_primary'},flush=True)
    summary=dict(cases=len(result),pass_count=sum(r['status']=='PASS' for r in result),solver_calls=0,negative_controls=6,scope='exact serialized decimal weighted-sum equality under primary bijection; not solver arithmetic or EQ verdict')
    a.out.write_text(json.dumps(dict(summary=summary,rows=result),indent=2)+'\n');print(summary)
if __name__=='__main__':main()
