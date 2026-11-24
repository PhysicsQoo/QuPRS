"""Research-only native Quokka# numerical Hoare comparison, same GPMC release."""
import csv
import decimal
import hashlib
import importlib
import importlib.metadata
import json
import pathlib
import sys
import tempfile
import time

D=decimal.Decimal


def decode(text):
    return [tuple(map(int,f.split(","))) if f!="-" else () for f in text.split(";")] if text else []


def cube(fs):
    out={}
    for f in fs:
        nonzero=[m for m in f if m]
        if len(nonzero)!=1 or nonzero[0].bit_count()!=1:
            return None
        i=nonzero[0].bit_length()-1
        b=int(0 not in f)
        if i in out and out[i]!=b:
            return None
        out[i]=b
    return out


def evaluate(f,x):
    return sum((m&x)==m for m in f)%2


class Monitor:
    def __init__(self,n):
        self.n=n
        self.gates=[]
    def fresh(self):
        q=self.n
        self.n+=1
        return q
    def toggle(self,controls,target):
        if not controls:
            self.gates.append(("x",target))
        elif len(controls)==1:
            self.gates.append(("cx",controls[0],target))
        elif len(controls)==2:
            self.gates.append(("ccx",*controls,target))
        else:
            # Compute the conjunction into clean scratch, toggle target,
            # and uncompute the scratch. All gates self-inverse.
            work=[self.fresh() for _ in range(len(controls)-2)]
            chain=[("ccx",controls[0],controls[1],work[0])]
            for i in range(1,len(work)):
                chain.append(("ccx",work[i-1],controls[i+1],work[i]))
            self.gates.extend(chain)
            self.gates.append(("ccx",work[-1],controls[-1],target))
            self.gates.extend(reversed(chain))
    def predicate(self,f,n):
        flag=self.fresh()
        for m in f:
            assert 0<=m<1<<n
            self.toggle([i for i in range(n) if m>>i&1],flag)
        return flag


def classical(gates,x):
    for op,*qs in gates:
        assert op in ("x","cx","ccx")
        if all(x>>q&1 for q in qs[:-1]):
            x^=1<<qs[-1]
    return x


def adapt(n,gates,pre,post):
    # The matched corpus has cube preconditions. For a nonlinear post
    # condition, compute each conjunct into a clean flag and check all
    # flags. No precondition dilution or auxiliary postselection.
    a=cube(pre);b=cube(post)
    if a is None:
        return None
    if b is not None:
        return n,gates,a,b,"native-cube",0
    m=Monitor(n)
    flags=[m.predicate(f,n) for f in post]
    # Test exact classical monitor semantics independently of Quokka#.
    xs=range(1<<n) if n<=8 else (0,1,(1<<n)-1,(1<<n)-2)
    for x in xs:
        y=classical(m.gates,x)
        assert y&((1<<n)-1)==x
        assert all((y>>q&1)==evaluate(f,x) for q,f in zip(flags,post))
        assert all(not (y>>i&1) for i in range(n,m.n) if i not in flags)
    a={**a,**{i:0 for i in range(n,m.n)}}
    return m.n,gates+m.gates,a,{q:1 for q in flags},"post-anf-monitor",len(m.gates)


def load_case(path):
    head,*lines=path.read_text().splitlines()
    n,p,q=head.split("\t")
    gates=[]
    for line in lines:
        op,*args=line.split()
        gates.append((op,*map(int,args)))
    return int(n),gates,decode(p),decode(q)


def write_qasm(path,n,gates):
    lines=["OPENQASM 2.0;",'include "qelib1.inc";',f"qreg q[{n}];"]
    lines.extend(op+" "+",".join(f"q[{q}]" for q in qs)+";" for op,*qs in gates)
    path.write_text("\n".join(lines)+"\n")


def compare(directory,gpmc):
    import quokka_sharp as qs
    from quokka_sharp import config
    vm=importlib.import_module("quokka_sharp.veri")
    assert importlib.metadata.version("quokka_sharp")=="2.7.5"
    # Capture the unmodified native Simulate return value once; Verify
    # still decides using its own FPE. No replacement of encoder/solver.
    native_sim=vm.Simulate
    observation={}
    def observe(cnf):
        observation["vars"]=cnf.vars.var
        observation["clauses"]=cnf.clause
        t=time.monotonic()
        result=native_sim(cnf)
        observation["simulate_s"]=time.monotonic()-t
        observation["prob"]=str(result)
        return result
    vm.Simulate=observe
    config.CONFIG.update(ToolInvocation=f"{gpmc} -mode=1 -prec=50",Precision=50,DEBUG=False)
    # Check adapter independently, including cubic monomials and constants.
    for f in [(0,),(1,2),(3,),(7,),(0,15)]:
        m=Monitor(4);q=m.predicate(f,4)
        for x in range(16):
            assert (classical(m.gates,x)>>q&1)==evaluate(f,x)
    cases=[]
    with (directory/"hybrid.tsv").open() as f:
        for name,n,nq,delta,expected,witnesses,build_us,direct_us,plan_us in csv.reader(f,delimiter="\t"):
            cases.append((name,tuple(map(int,expected.split(",")))))
    with (directory/"pure-rare.tsv").open() as f:
        for name,n,h,delta,expected,witnesses,build_us,encoding_us,status in csv.reader(f,delimiter="\t"):
            cases.append((name,tuple(map(int,expected.split(",")))))
    assert len(cases)==26
    deadline=time.monotonic()+90
    rows=[]
    with tempfile.TemporaryDirectory(prefix="hoare-quokka-") as tmp:
        qasm=pathlib.Path(tmp)/"property.qasm"
        for name,coeff in cases:
            n,gates,pre,post=load_case(directory/f"quokka-{name}.tsv")
            t=time.monotonic()
            adapted=adapt(n,gates,pre,post)
            adapter_s=time.monotonic()-t
            if adapted is None:
                rows.append(dict(case=name,status="UNSUPPORTED_NONCUBE_PRE"))
                continue
            width,ops,p,q,route,extra=adapted
            # Default tolerance on all cases; stricter numerical sensitivity
            # only on rare cases. FPE also affects the upstream result parser.
            for tol in (("1e-12","1e-16","1e-20") if name.startswith("rare-") else ("1e-12",)):
                row=dict(case=name,adapter=route,source_n=n,n=width,source_gates=len(gates),
                         monitor_gates=extra,adapter_s=adapter_s,fpe=tol,basis="comp",
                         exact_expected="REFUTED" if any(coeff) else "PROVED")
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    row["status"]="UNKNOWN_TIMEOUT"
                else:
                    config.CONFIG.update(FPE=D(tol),TIMEOUT=min(5,remaining))
                    decimal.getcontext().prec=50
                    t=time.monotonic()
                    try:
                        write_qasm(qasm,width,ops)
                        circuit=qs.QASMparser(str(qasm))
                        assert circuit.n==width
                        assert [tuple(g) for g in circuit.circ]==ops
                        cnf=qs.QASM2CNF(circuit,computational_basis=True,weighted=True)
                        row["encoding_s"]=time.monotonic()-t
                        observation.clear()
                        t=time.monotonic()
                        verdict=qs.Verify(cnf,p,q)
                        row.update(observation,verify_s=time.monotonic()-t,native_verdict=str(verdict))
                        row["status"]={"True":"PROVED_NUMERIC","False":"REFUTED_NUMERIC",
                                       "TIMEOUT":"UNKNOWN_TIMEOUT"}.get(str(verdict),"UNKNOWN_API")
                        if verdict in ("True","False"):
                            prob=D(observation["prob"])
                            row["numeric_leakage"]=str(1-prob)
                            with decimal.localcontext() as ctx:
                                ctx.prec=80
                                h=sum(op=="h" for op,*_ in gates)
                                rank=sum(all(evaluate(f,x) for f in pre) for x in range(1<<n))
                                assert rank>0
                                expected=(D(coeff[0])+D(coeff[1])*D(2).sqrt())/(D(2)**h*rank)
                                row["exact_mean_leakage"]=str(expected)
                                row["abs_numeric_error"]=str(abs((1-prob)-expected))
                            row["agrees_exact"]=(str(verdict)=="True")== (not any(coeff))
                    except Exception as e:
                        row.update(status="UNKNOWN_API_ERROR",error=type(e).__name__,detail=str(e)[-500:])
                rows.append(row)
                print("HOARE_QUOKKA "+json.dumps(row),flush=True)
    default=[r for r in rows if r.get("fpe")=="1e-12"]
    def tally(rs):
        return dict(cases=len(rs),agree=sum(r.get("agrees_exact") is True for r in rs),
                    disagree=sum(r.get("agrees_exact") is False for r in rs),
                    unknown=sum("agrees_exact" not in r for r in rs))
    print("HOARE_QUOKKA_SUMMARY "+json.dumps(dict(version=importlib.metadata.version("quokka_sharp"),
          default=tally(default),tolerances={t:tally([r for r in rows if r.get("fpe")==t])
          for t in ("1e-12","1e-16","1e-20")},unsupported=sum(r.get("status")=="UNSUPPORTED_NONCUBE_PRE" for r in rows),
          gpmc_sha256=hashlib.sha256(gpmc.read_bytes()).hexdigest())),flush=True)


if __name__=="__main__":
    compare(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]).resolve())
