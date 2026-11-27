#!/usr/bin/env python3
"""E1b independent finite-weight replay. Requires Python 3.10+; do not run with -O."""
import ast, json, re, hashlib, time, argparse, tempfile, zipfile
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, localcontext, ROUND_CEILING
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCES={
    "d1d":("d0ec708935a8c412c90ad78dbe43a5f3a628778dc7b0181c665848fcfe7e1e12","8811544a462338569bc5a375e3df41fdd18ea3b8","b7ebfdcf3cfdac115bf971fddc92306bc66adde8"),
    "e1a":("5fd9f38c6b199b4acffe88dc6faf98c9e3c5dba5446d1d701b80bcf4ab8560f3","63bdd625796bf4b1e59cb5b82e2ee8239cde5937","2de05fba994a500bab873d392292e7e5d2558e5a"),
    "e1b":("3447cc97563b96e6dd4529e8b25e7af161a0895c51263435e554c97555d1b8cf","2addb665bd8015791c5ee7527a8ce0de5bf8e3a1","f3c63a58c6a7ab651e0117e2a847ffa52b1c0f47")
}
parser=argparse.ArgumentParser(description="Offline exact rational finite-weight discrepancy bound for the sealed E1b cohort. No WMC solver.")
for name in SOURCES:parser.add_argument("--"+name,type=Path,required=True)
parser.add_argument("--out",type=Path,required=True)
args=parser.parse_args();tmp=tempfile.TemporaryDirectory(prefix="dag-weight-bound-");root=Path(tmp.name)
for name,(digest,head,tree) in SOURCES.items():
    archive=getattr(args,name);assert sha(archive)==digest,name
    dest=root/name;dest.mkdir()
    with zipfile.ZipFile(archive) as z:z.extractall(dest)
    sealed=set()
    for line in (dest/"SHA256SUMS").read_text().splitlines():
        checksum,path=line.split(maxsplit=1);f=dest/path;assert f.is_file() and sha(f)==checksum,(name,path);sealed.add(f.resolve())
    assert sealed=={f.resolve() for f in dest.rglob("*") if f.is_file() and f!=dest/"SHA256SUMS"}
    assert (dest/"head.txt").read_text().strip()==head and (dest/"tree.txt").read_text().strip()==tree
D=root/"d1d";A=root/"e1a";B=root/"e1b"
ONE=(F(1),F(0)); ZERO=(F(0),F(0))
def mul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def diff(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def scale(c,k):return(c[0]*k%1,c[1]*k)
def coeff(a):
    n,d,rad,symbols=a; assert symbols=='{}'; m=re.fullmatch(r'Some\(Ratio \{ numer: (-?\d+), denom: (\d+) \}\)',rad)
    assert rad=='None' or m
    return (F(int(n),int(d))%1,F(int(m[1]),int(m[2])) if m else F(0))
def snapshot(p):
    meta={};phase={};out={}
    for l in p.read_text().splitlines():
        a=l.split('\t'); k=a[0]
        if k=='p':
            m=tuple(ast.literal_eval(a[1]));assert m not in phase;phase[m]=coeff(a[2:])
        elif k=='output':out[int(a[1])]=[]
        elif k=='f':out[int(a[1])].append(tuple(ast.literal_eval(a[2])))
        else:meta[k]=a[1]
    n,h=int(meta['n']),int(meta['h']);domain=ast.literal_eval(meta['vars']);assert len(domain)==n+h and set(out)==set(range(n));return n,h,domain,phase,out
class CNF:
    def __init__(self,path,domain):
        lines=path.read_text().splitlines(); header=lines[0].split(); assert header[:2]==['p','cnf'];self.nv,self.nc=map(int,header[2:]);self.weights={};self.clauses=[];self.cursor=0;self.n=len(domain);self.ids={v:i+1 for i,v in enumerate(domain)};self.used=set();self.xors={}
        for l in lines[1:]:
            if l.startswith('c p weight '):
                a=l.split();assert len(a)==7 and a[-1]=='0';z=int(a[3]);assert z not in self.weights and 0<abs(z)<=self.nv;self.weights[z]=tuple(map(F,a[4:6]))
            elif l=='c t wmc':pass
            else:
                a=tuple(map(int,l.split()));assert a[-1]==0 and all(0<abs(x)<=self.nv for x in a[:-1]);self.clauses.append(a[:-1])
        assert len(self.clauses)==self.nc
        assert all(self.weights[-z]==ONE for z in self.weights if z>0) and all(-z in self.weights for z in self.weights)
    def check(self,cl):
        cl=list(cl);assert self.clauses[self.cursor:self.cursor+len(cl)]==cl,(self.cursor,cl,self.clauses[self.cursor:self.cursor+len(cl)]);self.cursor+=len(cl)
    def gate(self,kind,ops,weighted=False):
        self.n+=1;z=self.n;assert all(0<abs(x)<z for x in ops)
        if kind=='and':self.check([(-z,x) for x in ops]+[(z,*(-x for x in ops))])
        elif kind=='xor':a,b=ops;self.check([(-a,-b,-z),(a,b,-z),(a,-b,z),(-a,b,z)])
        else:assert kind=='false' and not ops;self.check([(-z,)])
        assert (z in self.weights)==weighted
        if weighted:self.used.add(z)
        return z
    def mono(self,m,weighted=False):
        ops=[self.ids[v] for v in m];return ops[0] if len(ops)==1 and not weighted else self.gate('and',ops,weighted)
    def xor(self,a,b,share=False):
        key=tuple(sorted((a,b)))
        if not share:return self.gate('xor',key)
        if key not in self.xors:self.xors[key]=self.gate('xor',key)
        return self.xors[key]
    def outputs(self,n,outputs):
        for i in range(n):
            f=sorted(outputs[i]);zz=[self.mono(m) for m in f]
            if not zz:z=self.gate('false',())
            else:
                z=zz[0]
                for y in zz[1:]:z=self.xor(z,y)
            a=self.ids[i];self.check([(-a,z),(a,-z)])
        assert self.cursor==self.nc and self.n==self.nv and self.used=={z for z in self.weights if z>0}
    def weight(self,z):return self.weights[z]
def pos_weights(p):
    return Counter(tuple(map(F,a[4:6])) for l in p.read_text().splitlines() if l.startswith('c p weight ') and int((a:=l.split())[3])>0)
def trace_rank(n,domain,outputs):
    # Select variables that never occur in nonlinear trace monomials.
    # Fix all other variables; remaining trace equations are affine with a fixed matrix.
    nonlinear={v for f in outputs.values() for m in f if len(m)>1 for v in m}
    columns={v:i for i,v in enumerate(v for v in domain if v not in nonlinear)}
    pivots={}
    for i in range(n):
        terms=Counter(outputs[i]+[(i,)])
        mask=0
        for m,k in terms.items():
            if k%2 and len(m)==1 and m[0] in columns:mask ^= 1<<columns[m[0]]
        while mask:
            p=mask.bit_length()-1
            if p not in pivots:pivots[p]=mask;break
            mask ^= pivots[p]
    return len(pivots)
def ceilstr(x):
    with localcontext() as ctx:
        ctx.prec=8;ctx.rounding=ROUND_CEILING
        return str(Decimal(x.numerator)/Decimal(x.denominator))
receipts=json.loads((B/'receipts.json').read_text())['rows'];plans={r['case']:r for r in json.loads((A/'phase_factor_census.json').read_text())['rows'] if r['source_head']==(D/'head.txt').read_text().strip()};source={r['case']:r for r in map(json.loads,(D/'rows.jsonl').read_text().splitlines())}
results=[]
for r in receipts:
    t=time.monotonic();case=r['case'];snap=D/(case+'-hybrid')/'residual.tsv';archived=snap.parent/'actual.cnf';flat=B/(case+'-flat.cnf');fact=B/(case+'-factored.cnf');assert sha(snap)==r['source_residual_sha256']==source[case]['residual_sha256']==plans[case]['residual_sha256'];assert sha(archived)==r['original_cnf_sha256']==source[case]['cnf']['sha256'];assert sha(flat)==r['flat_sha256'] and sha(fact)==r['factored_sha256']
    n,h,domain,p,out=snapshot(snap);fc=CNF(flat,domain);gc=CNF(fact,domain);wf={m:fc.weight(fc.mono(m,True)) for m in sorted(p)};fc.outputs(n,out);assert Counter(wf.values())==pos_weights(archived)
    rem=dict(p);errors=[];bad=0;maxerr=F(0);plan=plans[case]['plans']['mixed'];assert plan['status']=='OK'
    for choice in plan['choices']:
        a,b=tuple(choice['a']),tuple(choice['b']);c=tuple(map(F,choice['coefficient']));u=tuple(sorted(set(a)|set(b)))
        if choice['kind']=='xor':
            C=tuple(sorted(set(a)&set(b)));xx=tuple(set(a)-set(b));yy=tuple(set(b)-set(a));assert len(xx)==len(yy)==1 and len(u)==len(a)+1==len(b)+1
            x,y=xx[0],yy[0];z=gc.xor(gc.ids[x],gc.ids[y],True);w=gc.weight(gc.gate('and',[gc.ids[v] for v in C]+[z],True));exp={a:c,b:c,u:scale(c,-2)}
            e=max(diff(wf[a],w),diff(wf[b],w),diff(mul(mul(wf[a],wf[b]),wf[u]),ONE))
        else:
            assert choice['kind']=='complement' and len(b)==1 and b[0] not in a;w=gc.weight(gc.gate('and',[gc.ids[v] for v in a]+[-gc.ids[b[0]]],True));exp={a:c,u:scale(c,-1)};e=max(diff(wf[a],w),diff(mul(wf[a],wf[u]),ONE))
        for m,k in exp.items():assert rem.pop(m)==k
        errors.append(e);bad+=bool(e);maxerr=max(maxerr,e)
    remaining_errors=[]
    for m in sorted(rem):remaining_errors.append(diff(wf[m],gc.weight(gc.mono(m,True))))
    gc.outputs(n,out);assert len(gc.used)==r['factored_weighted'] and len(fc.used)==r['flat_weighted']
    # |w| <= 1 + ||w|^2 - 1|. Any subproduct of weights in both encoders <= 1/(1-S), S<1.
    S=sum((abs(a*a+b*b-1) for q in (fc,gc) for z,(a,b) in q.weights.items() if z>0),F(0));assert S<1
    assign_bound=(sum(errors,F(0))+sum(remaining_errors,F(0)))/(1-S)
    # At most 2^(n+h) satisfying primary assignments, normalization 2^(-n-h/2).
    rank=trace_rank(n,domain,out)
    normalized=assign_bound*2**((h+1)//2)
    refined=normalized/2**rank
    res=dict(case=case,n=n,h=h,blocks=len(errors),nonzero_block_errors=bad,nonzero_unchanged_errors=sum(bool(e) for e in remaining_errors),max_block_error=ceilstr(maxerr),sum_local_error=ceilstr(sum(errors,F(0))+sum(remaining_errors,F(0))),sum_norm_defect=ceilstr(S),assignment_bound=ceilstr(assign_bound),normalized_bound=ceilstr(normalized),trace_affine_rank=rank,refined_bound=ceilstr(refined),passes_1e20=refined<=F(1,10**20),passes_1e8=refined<=F(1,10**8),bound_is_exact_rational_test=True,seconds=round(time.monotonic()-t,3));results.append(res);print(json.dumps(res),flush=True)
assert len(results)==12 and len({r['case'] for r in results})==12
summary=dict(cases=12,certified_serialized_delta_1e20=sum(r['passes_1e20'] for r in results),certified_serialized_delta_1e8=sum(r['passes_1e8'] for r in results),solver_calls=0,scope="canonical flat vs factored exact decimal-weight WMC; not archived variable correspondence, solver arithmetic, verdict or E2E")
args.out.write_text(json.dumps(dict(sources=SOURCES,summary=summary,rows=results),indent=2)+'\n')
print(json.dumps(summary),flush=True)
