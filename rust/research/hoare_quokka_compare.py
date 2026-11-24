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
import os
import re
import subprocess
import tarfile
import zipfile

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



def general_pre_monitor(n,gates,pre,post):
    """Retain a reversible flag for P before U; compute bad=P AND NOT Q
    afterwards. Free original inputs: native mean is L/2^n, not L/rank(P).
    All monitor scratch starts clean and conjunction work is uncomputed."""
    m=Monitor(n)
    pf=[m.predicate(f,n) for f in pre]
    a=m.fresh()
    m.toggle(pf,a)
    before=list(m.gates)
    m.gates=[]
    qf=[m.predicate(f,n) for f in post]
    q=m.fresh()
    m.toggle(qf,q)
    bad=m.fresh()
    m.gates.extend([("x",q),("ccx",a,q,bad),("x",q)])
    after=list(m.gates)
    xs=range(1<<n) if n<=12 else (0,1,(1<<n)-1,(1<<n)-2)
    for x in xs:
        y=classical(before,x)
        assert y&((1<<n)-1)==x
        assert (y>>a&1)==all(evaluate(f,x) for f in pre)
        for av in (0,1):
            z=classical(after,x|(av<<a))
            assert z&((1<<n)-1)==x and (z>>a&1)==av
            assert (z>>bad&1)==(av and not all(evaluate(f,x) for f in post))
    return m.n,before+gates+after,{i:0 for i in range(n,m.n)},{bad:0},"general-pre-bad-monitor",len(before)+len(after)


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


def compare(directory,gpmc,extended=False):
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
    if extended:
        directory=directory/"scale-discovery"
        fields="case n h hr scale post_count branch_count factor_status cnf_status vars clauses delta common_us base_us factor_us expected oracle".split()
        with (directory/"property-factor.tsv").open() as f:
            cases=[(r["case"],tuple(map(int,r["expected"].split(",")))) for r in csv.DictReader(f,fieldnames=fields,delimiter="\t")]
        assert len(cases)==20
    deadline=time.monotonic()+(600 if extended else 90)
    rows=[]
    with tempfile.TemporaryDirectory(prefix="hoare-quokka-") as tmp:
        qasm=pathlib.Path(tmp)/"property.qasm"
        for name,coeff in cases:
            n,gates,pre,post=load_case(directory/f"quokka-{name}.tsv")
            t=time.monotonic()
            adapted=adapt(n,gates,pre,post)
            if extended and adapted is None:adapted=general_pre_monitor(n,gates,pre,post)
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
                         exact_expected="REFUTED" if any(coeff) else "PROVED",
                         source_sha256=hashlib.sha256((directory/f"quokka-{name}.tsv").read_bytes()).hexdigest())
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    row["status"]="UNKNOWN_TIMEOUT"
                else:
                    cap=((120 if "15" in name else 60) if "mixing" in name else 30) if extended else 5
                    row["solver_cap_s"]=cap
                    config.CONFIG.update(FPE=D(tol),TIMEOUT=min(cap,remaining))
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
                                native_expected=expected*D(rank)/D(2**n) if route=="general-pre-bad-monitor" else expected
                                row["rank_pre"]=rank
                                row["exact_mean_leakage"]=str(expected)
                                row["native_expected_leakage"]=str(native_expected)
                                row["abs_numeric_error"]=str(abs((1-prob)-native_expected))
                                row["normalized_numeric_leakage"]=str((1-prob)*D(2**n)/D(rank) if route=="general-pre-bad-monitor" else 1-prob)
                            row["agrees_exact"]=(str(verdict)=="True")== (not any(coeff))
                    except Exception as e:
                        row.update(status="UNKNOWN_API_ERROR",error=type(e).__name__,detail=str(e)[-500:])
                rows.append(row)
                print(("HOARE_QUOKKA_EXTENDED " if extended else "HOARE_QUOKKA ")+json.dumps(row),flush=True)
    default=[r for r in rows if r.get("fpe")=="1e-12"]
    def tally(rs):
        return dict(cases=len(rs),agree=sum(r.get("agrees_exact") is True for r in rs),
                    disagree=sum(r.get("agrees_exact") is False for r in rs),
                    unknown=sum("agrees_exact" not in r for r in rs))
    print(("HOARE_QUOKKA_EXTENDED_SUMMARY " if extended else "HOARE_QUOKKA_SUMMARY ")+json.dumps(dict(version=importlib.metadata.version("quokka_sharp"),
          default=tally(default),tolerances={t:tally([r for r in rows if r.get("fpe")==t])
          for t in ("1e-12","1e-16","1e-20")},unsupported=sum(r.get("status")=="UNSUPPORTED_NONCUBE_PRE" for r in rows),
          gpmc_sha256=hashlib.sha256(gpmc.read_bytes()).hexdigest())),flush=True)

    vm.Simulate=native_sim



# Paper-first source admission. GitHub candidates are NOT identified as
# the paper fixture solely by a matching gate count.
PAPER_REPO="System-Verification-Lab/quokka-sharp-artifacts"
PAPER_HEAD="53777d525719486eba1038901fbef4a8d8d782ce"
PAPER_FILES=(
    ("noancilla","qwalk-noancilla_nativegates_ibm_qiskit_opt0_5.qasm",
     "447ec29073718da096b283ed6916b717a8362ad1",1305,16),
    ("v-chain","qwalk-v-chain_nativegates_ibm_qiskit_opt0_5.qasm",
     "f0929d665b438229a566a9378d6f939c4f644f6f",417,0),
)
ARCHIVE_MD5="eb5171400bc9087660a9176b5eb6e606"


def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def paper_parse(data):
    regs={};ops=[];n=0
    for raw in data.decode().splitlines():
        l=raw.split("//",1)[0].strip()
        if not l or l in ('OPENQASM 2.0;','include "qelib1.inc";'):continue
        m=re.fullmatch(r"qreg (\w+)\[(\d+)\];",l)
        if m:
            name,size=m[1],int(m[2])
            assert name not in regs and size>0
            regs[name]=(n,size);n+=size;continue
        m=re.fullmatch(r"(\w+)(?:\(([^)]*)\))?\s+(.+);",l)
        assert m,l
        op,angle,args=m.groups()
        qs=[]
        for a in args.split(","):
            x=re.fullmatch(r"(\w+)\[(\d+)\]",a.strip())
            assert x and x[1] in regs
            offset,size=regs[x[1]];idx=int(x[2]);assert idx<size
            qs.append(offset+idx)
        assert op in ("s","t","tdg","x","cx","rx","rz")
        assert len(qs)==(2 if op=="cx" else 1)
        assert angle is None if op not in ("rx","rz") else angle is not None
        ops.append((op,angle,qs))
    return n,regs,ops


def paper_exact_oracle(data):
    # zeta=exp(i*pi/16), zeta^16=-1. Rz replaced by its phase-gate
    # representative (global phase only), Rx(pi/2) numerator I-iX
    # divided by sqrt(2). No rounded coefficients or tolerance.
    n,regs,ops=paper_parse(data)
    assert n==5
    zero=(0,)*16
    def shift(v,k):
        out=[0]*16
        for j,a in enumerate(v):
            i=(j+k)%32
            out[i%16]+=a if i<16 else -a
        return tuple(out)
    def add(a,b):return tuple(x+y for x,y in zip(a,b))
    angles={"-3*pi/2":-24,"pi/8":2,"pi/16":1,"-pi/16":-1,"-pi/8":-2}
    bad_inputs=[];first=None
    for x in range(16):
        v=[zero]*(1<<n);v[x]=(1,)+(0,)*15;h=0
        for op,angle,qs in ops:
            b=1<<qs[0]
            if op=="rx":
                assert angle=="pi/2";h+=1
                for i in range(len(v)):
                    if i&b:continue
                    j=i|b;p,s=v[i],v[j]
                    v[i]=add(p,shift(s,-8));v[j]=add(s,shift(p,-8))
            elif op in ("x","cx"):
                target=b if op=="x" else 1<<qs[1]
                for i in range(len(v)):
                    if not i&target and (op=="x" or i&b):
                        j=i|target;v[i],v[j]=v[j],v[i]
            else:
                k=angles[angle] if op=="rz" else {"s":8,"t":4,"tdg":-4}[op]
                for i in range(len(v)):
                    if i&b:v[i]=shift(v[i],k)
        bad=[z for z in range(16,32) if any(v[z])]
        if bad:
            bad_inputs.append(x)
            if first is None:first=dict(x=x,z=bad[0],numerator=list(v[bad[0]]),sqrt2_denominator_power=h)
    return dict(n=n,registers=regs,gates=len(ops),legal_inputs=16,bad_amplitudes_checked=256,
                bad_inputs=bad_inputs,first_witness=first,verdict="REFUTED" if bad_inputs else "PROVED",
                z8_admission=not any(op=="rz" and angles[a]%4 for op,a,_ in ops))


def scan_paper_archive(tmp,known):
    # Data only; do not unpack to the working tree, execute artifact code
    # or publish the archive. Fixed URL and checksum, bounded transfer.
    path=tmp/"paper-quokka.zip"
    start=time.monotonic()
    receipt=dict(status="NOT_RUN",doi="10.5281/zenodo.19833587",expected_md5=ARCHIVE_MD5)
    try:
        if os.environ.get("HOARE_SKIP_PAPER_ARCHIVE")=="1":
            receipt["status"]="OPT_OUT";return receipt
        subprocess.run(["curl","--proto","=https","--tlsv1.2","--fail","--location",
            "--silent","--show-error","--max-time","180","--max-filesize","1300000000",
            "https://zenodo.org/records/19833587/files/quokka.zip?download=1","-o",str(path)],
            check=True,timeout=190)
        with path.open("rb") as f:actual=hashlib.file_digest(f,"md5").hexdigest()
        receipt["md5"]=actual;receipt["bytes"]=path.stat().st_size
        if actual!=ARCHIVE_MD5:
            receipt["status"]="CHECKSUM_MISMATCH";return receipt
        matches=[];scripts=[];members=0
        scan_end=time.monotonic()+150
        with zipfile.ZipFile(path) as z:
            nested=[i for i in z.infolist() if i.filename=="quokka/quokka-cavae26.tar.gz"]
            assert len(nested)==1 and nested[0].file_size<1_300_000_000
            with z.open(nested[0]) as stream,tarfile.open(fileobj=stream,mode="r|gz") as t:
                for member in t:
                    members+=1
                    if time.monotonic()>=scan_end or members>250000:
                        receipt.update(status="SCAN_LIMIT",members=members,matches=matches,scripts=scripts);return receipt
                    if not member.isfile() or member.size>2_000_000:continue
                    name=member.name.lower()
                    base=pathlib.PurePosixPath(name).name
                    if name.endswith(".qasm") and ("qwalk" in name or "quantum_walk" in name or "quantumwalk" in name):
                        if len(matches)>=200:continue
                        data=t.extractfile(member).read()
                        blob=git_blob(data)
                        row=dict(path=member.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                                 git_blob=blob,github_match=known.get(blob))
                        try:
                            n,regs,ops=paper_parse(data)
                            row.update(n=n,gates=len(ops),registers=regs)
                            if n==5 and len(ops) in (417,1305):row["exact_oracle"]=paper_exact_oracle(data)
                        except (AssertionError,ValueError,UnicodeError,KeyError):pass
                        matches.append(row)
                    elif base.endswith((".py",".sh",".md",".txt")) and member.size<=100000:
                        data=t.extractfile(member).read()
                        text=data.decode(errors="replace")
                        lines=[l.strip()[:250] for l in text.splitlines() if re.search(r"qwalk|quantum.walk|verify\(",l,re.I)]
                        if lines and len(scripts)<60:
                            scripts.append(dict(path=member.name,sha256=hashlib.sha256(data).hexdigest(),lines=lines[:12]))
        receipt.update(status="SCANNED",members=members,matches=matches,scripts=scripts)
    except (subprocess.SubprocessError,OSError,zipfile.BadZipFile,tarfile.TarError,AssertionError) as e:
        receipt.update(status="ARCHIVE_UNAVAILABLE",error=type(e).__name__,detail=str(e)[-300:])
    finally:
        receipt["wall_s"]=time.monotonic()-start
        path.unlink(missing_ok=True)
    return receipt


def paper_compare(gpmc):
    import quokka_sharp as qs
    from quokka_sharp import config
    config.CONFIG.update(ToolInvocation=f"{gpmc} -mode=1 -prec=50",Precision=50,DEBUG=False,FPE=D("1e-12"),TIMEOUT=30)
    decimal.getcontext().prec=50
    known={}
    with tempfile.TemporaryDirectory(prefix="hoare-paper-") as tmp:
        tmp=pathlib.Path(tmp)
        for name,file,blob,gates,bad_count in PAPER_FILES:
            path=tmp/file
            url=f"https://raw.githubusercontent.com/{PAPER_REPO}/{PAPER_HEAD}/benchmark/algorithm/origin/{file}"
            subprocess.run(["curl","--proto","=https","--tlsv1.2","--fail","--location","--silent","--show-error",
                "--max-time","30",url,"-o",str(path)],check=True,timeout=35)
            data=path.read_bytes();assert git_blob(data)==blob
            known[blob]=name
            t=time.monotonic();oracle=paper_exact_oracle(data)
            assert oracle["gates"]==gates and len(oracle["bad_inputs"])==bad_count
            print("HOARE_PAPER_SOURCE "+json.dumps(dict(case=name,head=PAPER_HEAD,blob=blob,
                  sha256=hashlib.sha256(data).hexdigest(),oracle_s=time.monotonic()-t,**oracle)),flush=True)
            for comp in (True,False):
                row=dict(case=name,basis="comp" if comp else "pauli",source_blob=blob,expected=oracle["verdict"])
                try:
                    t=time.monotonic();circuit=qs.QASMparser(str(path))
                    assert circuit.n==5
                    row["parsed_gates"]=len(circuit.circ)
                    assert len(circuit.circ)==gates
                    cnf=qs.QASM2CNF(circuit,computational_basis=comp,weighted=True)
                    row["encoding_s"]=time.monotonic()-t
                    t=time.monotonic();v=qs.Verify(cnf,{4:0},{4:0})
                    row.update(verify_s=time.monotonic()-t,native_verdict=str(v),
                               status={"True":"PROVED_NUMERIC","False":"REFUTED_NUMERIC","TIMEOUT":"UNKNOWN_TIMEOUT"}.get(str(v),"UNKNOWN_API"))
                    if str(v) in ("True","False"):row["agrees_exact"]=(str(v)=="True")==(bad_count==0)
                except Exception as e:
                    row.update(status="UNKNOWN_API_ERROR",error=type(e).__name__,detail=str(e)[-400:])
                print("HOARE_PAPER_QUOKKA "+json.dumps(row),flush=True)
        receipt=scan_paper_archive(tmp,known)
        # Keep machine-readable provenance; no untrusted archive execution.
        print("HOARE_PAPER_ARCHIVE "+json.dumps(receipt),flush=True)



if __name__=="__main__":
    directory=pathlib.Path(sys.argv[1]);gpmc=pathlib.Path(sys.argv[2]).resolve()
    compare(directory,gpmc)
    compare(directory,gpmc,extended=True)
    paper_compare(gpmc)
