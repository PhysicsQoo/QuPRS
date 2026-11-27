#!/usr/bin/env python3
"""E1b research-only canonical source-phase CNF, with shared common-factor XOR.
Uses the original native MPFR C bridge, original input-weight precision budget.
Canonical Flat is a new order, not the archived production DIMACS byte stream.
"""
import ast,ctypes,itertools,json,math,sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from eq_dag_e1a_census import coeff,add,scale,ZERO,scan,controls
from eq_dag_phase_screen import read_snapshot,flat_counts
from eq_dag_d2a_rewrite import parse
from eq_dag_d3_ab import sha

D1="8811544a462338569bc5a375e3df41fdd18ea3b8"
E1="63bdd625796bf4b1e59cb5b82e2ee8239cde5937"

def weight_fn(lib):
    f=ctypes.CDLL(str(lib.resolve())).quprs_mpfr_phase_weight
    f.argtypes=[ctypes.c_char_p]*4+[ctypes.c_ulong,ctypes.POINTER(ctypes.c_char),ctypes.POINTER(ctypes.c_char),ctypes.c_size_t]
    f.restype=ctypes.c_int
    def weight(c,bits):
        a,b=c
        if not b and a in (Fraction(0),Fraction(1,2),Fraction(1,4),Fraction(3,4)):
            return {Fraction(0):("1.0","0.0"),Fraction(1,2):("-1.0","0.0"),Fraction(1,4):("0.0","1.0"),Fraction(3,4):("0.0","-1.0")}[a]
        x,y=ctypes.create_string_buffer(512),ctypes.create_string_buffer(512)
        parts=[str(v).encode() for v in (a.numerator,a.denominator,b.numerator,b.denominator)]
        assert f(*parts,bits,x,y,512)==0
        return x.value.decode(),y.value.decode()
    return weight

class Encoder:
    def __init__(self,domain,weight,bits):
        self.ids={v:i+1 for i,v in enumerate(domain)}
        self.n=len(domain);self.c=[];self.w={};self.defs={};self.xors={}
        self.weight=weight;self.bits=bits
    def gate(self,kind,ops,c=None):
        self.n+=1;z=self.n;ops=tuple(ops)
        assert all(0<abs(v)<z for v in ops)
        self.defs[z]=(kind,ops)
        if kind=="and":
            self.c.extend((-z,x) for x in ops)
            self.c.append((z,*(-x for x in ops)))
        elif kind=="xor":
            a,b=ops
            self.c.extend([(-a,-b,-z),(a,b,-z),(a,-b,z),(-a,b,z)])
        else:
            assert kind=="false" and not ops
            self.c.append((-z,))
        if c is not None: self.w[z]=self.weight(c,self.bits)
        return z
    def xor(self,a,b,share=False):
        key=tuple(sorted((a,b)))
        if not share: return self.gate("xor",key)
        if key not in self.xors: self.xors[key]=self.gate("xor",key)
        return self.xors[key]
    def mono(self,m,c=None):
        ops=[self.ids[v] for v in m]
        return ops[0] if len(ops)==1 and c is None else self.gate("and",ops,c)
    def outputs(self,n,outputs):
        for i in range(n):
            f=sorted(outputs[i])
            if not f: z=self.gate("false",())
            else:
                zz=[self.mono(m) for m in f];z=zz[0]
                for y in zz[1:]: z=self.xor(z,y)
            a=self.ids[i]
            self.c.extend([(-a,z),(a,-z)])
    def render(self):
        lines=[f"p cnf {self.n} {len(self.c)}","c t wmc"]
        for z,(re,im) in sorted(self.w.items()):
            lines.extend((f"c p weight {z} {re} {im} 0",f"c p weight {-z} 1.0 0.0 0"))
        lines.extend(" ".join(map(str,(*c,0))) for c in self.c)
        return "\n".join(lines)+"\n"

def build(domain,n,p,outputs,choices,weight,bits):
    e=Encoder(domain,weight,bits)
    # Independent coefficient ledger; consumes complete original support
    # entries only, compares the resulting polynomial exactly.
    remaining=dict(p);restored={}
    for row in choices:
        a,b=tuple(row["a"]),tuple(row["b"])
        c=tuple(map(Fraction,row["coefficient"]))
        u=tuple(sorted(set(a)|set(b)))
        if row["kind"]=="xor":
            common=tuple(sorted(set(a)&set(b)))
            x=tuple(set(a)-set(b));y=tuple(set(b)-set(a))
            assert len(x)==len(y)==1 and len(u)==len(a)+1==len(b)+1
            exp={a:c,b:c,u:scale(c,-2)}
            z=e.xor(e.ids[x[0]],e.ids[y[0]],True)
            e.gate("and",[e.ids[v] for v in common]+[z],c)
        else:
            assert row["kind"]=="complement" and len(b)==1 and b[0] not in a
            exp={a:c,u:scale(c,-1)}
            e.gate("and",[e.ids[v] for v in a]+[-e.ids[b[0]]],c)
        for m,k in exp.items():
            assert remaining.pop(m)==k and m not in restored
            restored[m]=k
    for m,c in sorted(remaining.items()): e.mono(m,c)
    assert {**restored,**remaining}==p
    e.outputs(n,outputs)
    return e

def evaluate(e,bits):
    d=dict(zip(range(1,len(bits)+1),bits))
    for z,(kind,ops) in e.defs.items():
        vals=[d[abs(x)] if x>0 else not d[abs(x)] for x in ops]
        d[z]=all(vals) if kind=="and" else vals[0]^vals[1] if kind=="xor" else False
    sat=all(any(d[abs(v)] if v>0 else not d[abs(v)] for v in c) for c in e.c)
    # exact Gaussian rational product of the synthetic control's weights
    re,im=Fraction(1),Fraction(0)
    for z,(a,b) in e.w.items():
        if d[z]: re,im=re*Fraction(a)-im*Fraction(b),re*Fraction(b)+im*Fraction(a)
    return sat,(re,im) if sat else None

def test(weight):
    controls()
    # sign-only control: exact finite weights, common-factor XOR, complement,
    # repeated XOR pair, output parity and one free primary.
    c=(Fraction(1,4),Fraction(0))
    p={(0,1):c,(0,2):c,(0,1,2):scale(c,-2),(1,3):c,(2,3):c,(1,2,3):scale(c,-2),(4,):c,(4,5):scale(c,-1)}
    choice=scan(p,"mixed")["choices"]
    a=build(list(range(7)),1,p,{0:[(0,),(1,)]},[],weight,96)
    b=build(list(range(7)),1,p,{0:[(0,),(1,)]},choice,weight,96)
    assert len(b.w)<len(a.w)
    for bits in itertools.product((False,True),repeat=7):
        assert evaluate(a,bits)==evaluate(b,bits)

def positive_weights(text):
    return Counter(tuple(map(Fraction,l.split()[4:6])) for l in text.splitlines() if l.startswith("c p weight ") and int(l.split()[3])>0)

def main():
    src,census,lib,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==D1
    assert (src/"tree.txt").read_text().strip()=="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"
    assert (census/"head.txt").read_text().strip()==E1
    assert (census/"tree.txt").read_text().strip()=="2de05fba994a500bab873d392292e7e5d2558e5a"
    weight=weight_fn(lib);test(weight)
    plans={x["case"]:x for x in json.loads((census/"phase_factor_census.json").read_text())["rows"] if x["source_head"]==D1}
    rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
    reports=[]
    for r in rows:
        if not (r["cnf"] and r["residual_sha256"]): continue
        case=r["case"];arm=src/(case+"-hybrid");snap=arm/"residual.tsv";original=arm/"actual.cnf"
        assert sha(snap)==r["residual_sha256"]==plans[case]["residual_sha256"] and sha(original)==r["cnf"]["sha256"]
        n,h,raw,outputs=read_snapshot(snap)
        p={m:coeff(v) for m,v in raw.items()};assert all(c is not None for c in p.values())
        domain=ast.literal_eval(next(s.split("\t")[1] for s in snap.read_text().splitlines() if s.startswith("vars\t")))
        assert len(domain)==n+h and domain==sorted(set(domain))
        bits=max(96,32*math.ceil((-2*math.log2(1e-8)+math.ceil(math.log2(max(1,len(p))))+32)/32))
        plan=plans[case]["plans"]["mixed"]
        assert plan["status"]=="OK" and plan["exact_replay"]
        flat=build(domain,n,p,outputs,[],weight,bits)
        cand=build(domain,n,p,outputs,plan["choices"],weight,bits)
        f=flat.render();g=cand.render()
        assert (flat.n,len(flat.c))==flat_counts(n,h,raw,outputs)==(r["cnf"]["variables"],r["cnf"]["clauses"])
        # Same exact serialized numerical weight multiset as original source.
        # This is NOT an ID-by-ID mapping to archived production order.
        assert positive_weights(f)==positive_weights(original.read_text()),case
        assert len(flat.w)-len(cand.w)==plan["weighted_factor_saving"]
        assert cand.n<=flat.n and len(cand.c)<=len(flat.c)
        for name,e,t in (("flat",flat,f),("factored",cand,g)):
            q=out/(case+"-"+name+".cnf");q.write_text(t)
        z=dict(case=case,source_residual_sha256=sha(snap),original_cnf_sha256=sha(original),weight_bits=bits,flat_weight_multiset_parity=True,exact_phase_replay=True,flat_vars=flat.n,factored_vars=cand.n,flat_clauses=len(flat.c),factored_clauses=len(cand.c),flat_weighted=len(flat.w),factored_weighted=len(cand.w),shared_xor_nodes=len(cand.xors),flat_sha256=sha(out/(case+"-flat.cnf")),factored_sha256=sha(out/(case+"-factored.cnf")))
        reports.append(z);print("E1B_ARM",json.dumps(z),flush=True)
    assert len(reports)==12
    summary=dict(arms=len(reports),exact_phase_replay=len(reports),flat_weight_multiset_parity=len(reports),solver_calls=0,scope="canonical research encoder; not production refinement or solver parity")
    (out/"receipts.json").write_text(json.dumps(dict(summary=summary,rows=reports),indent=2)+"\n")
    print("E1B_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":
    main()
