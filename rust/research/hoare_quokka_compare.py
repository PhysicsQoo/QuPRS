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



# R28A: research-only gate-local paired path encoding and natural-weight
# phase histogram. No change to QuPRS's native admission or phase IR.
class WidePairCNF:
    def __init__(self):
        self.n=1
        self.clauses=[(1,)]
        self.cache={}
    def fresh(self):
        self.n+=1
        return self.n
    def enforce(self,l):
        self.clauses.append((l,))
    def eq(self,a,b):
        if a!=b:self.clauses.extend(((-a,b),(a,-b)))
    def and_(self,a,b):
        if a==1:return b
        if b==1:return a
        if a==-1 or b==-1 or a==-b:return -1
        if a==b:return a
        key=("and",*sorted((a,b)))
        if key not in self.cache:
            c=self.fresh()
            self.clauses.extend(((-c,a),(-c,b),(c,-a,-b)))
            self.cache[key]=c
        return self.cache[key]
    def xor(self,a,b):
        if a==b:return -1
        if a==-b:return 1
        if a==1:return -b
        if b==1:return -a
        if a==-1:return b
        if b==-1:return a
        key=("xor",*sorted((a,b)))
        if key not in self.cache:
            c=self.fresh()
            self.clauses.extend(((-a,-b,-c),(a,b,-c),(-a,b,c),(a,-b,c)))
            self.cache[key]=c
        return self.cache[key]
    def or_(self,a,b):
        return -self.and_(-a,-b)
    def add(self,a,b):
        carry=-1;out=[]
        for x,y in zip(a,b):
            z=self.xor(x,y)
            out.append(self.xor(z,carry))
            carry=self.or_(self.and_(x,y),self.and_(z,carry))
        return out


WIDE_ANGLES={"-3*pi/2":-24,"pi/8":2,"pi/16":1,"-pi/16":-1,"-pi/8":-2,
             "pi/4":4,"pi/2":8,"-pi/4":-4,"-pi/2":-8}


def gate_local_pair(n,ops,pre,post,m):
    """Cube pre/post only, shared input, full output equality.
    RX/H choices are independent Boolean summation variables. All
    other variables, including phase bits, are unique extensions.
    Phase coefficient unit is pi/(2^(m-1)). Global Rz phases cancel."""
    M=1<<m
    assert 3<=m<=6 and n<=16
    assert all(0<=i<n and b in (0,1) for pred in (pre,post) for i,b in pred.items())
    c=WidePairCNF()
    inputs=[(1 if pre[i] else -1) if i in pre else c.fresh() for i in range(n)]
    primary=n-len(pre)
    left=inputs[:];right=inputs[:]
    phase={};constant=0
    def term(l,k):
        nonlocal constant
        if l==1:constant=(constant+k)%M;return
        if l==-1:return
        if l<0:constant=(constant+k)%M;l=-l;k=-k
        phase[l]=(phase.get(l,0)+k)%M
    def angle_k(angle):
        # Scale integer pi/16 coefficient exactly; reject non-integral.
        v=WIDE_ANGLES[angle]*M
        if v%32:raise ValueError("angle outside exact phase modulus")
        return v//32
    for op,a,qs in ops:
        for wires,sign in ((left,1),(right,-1)):
            i=qs[0];old=wires[i]
            if op in ("rx","h"):
                if op=="rx" and a!="pi/2":raise ValueError("unsupported rx")
                new=c.fresh();primary+=1
                l=c.xor(old,new) if op=="rx" else c.and_(old,new)
                term(l,sign*(-M//4 if op=="rx" else M//2))
                wires[i]=new
            elif op=="x":wires[i]=-old
            elif op=="cx":wires[qs[1]]=c.xor(old,wires[qs[1]])
            elif op in ("s","t","tdg","rz"):
                k=angle_k(a) if op=="rz" else {"s":M//4,"t":M//8,"tdg":-M//8}[op]
                term(old,sign*k)
            else:raise ValueError("unsupported gate "+op)
    for a,b in zip(left,right):c.eq(a,b)
    ok=1
    for i,b in post.items():ok=c.and_(ok,left[i] if b else -left[i])
    c.enforce(-ok)
    # Balanced tree of modular sums. Merge identical literal terms first.
    parts=[[1 if constant>>i&1 else -1 for i in range(m)]]
    parts.extend([l if k>>i&1 else -1 for i in range(m)] for l,k in sorted(phase.items()) if k)
    terms=len(parts)-1
    while len(parts)>1:
        parts=[c.add(parts[i],parts[i+1]) if i+1<len(parts) else parts[i] for i in range(0,len(parts),2)]
    # Fresh positive, distinct phase-bit IDs even for constant/aliased bits.
    bits=[c.fresh() for _ in range(m)]
    for a,b in zip(bits,parts[0]):c.eq(a,b)
    return c,bits,primary,terms


def unpack_histogram(value,radix,M,max_models):
    if value<0 or radix<=max_models:raise ValueError("invalid radix")
    hist=[]
    for _ in range(M):
        value,digit=divmod(value,radix);hist.append(digit)
    if value or sum(hist)>max_models:raise ValueError("histogram bound")
    return hist


def wide_count(gpmc,tmp,c,bits,primary,seconds):
    from hoare_ganak_exact import parse_gpmc_integer,profile_gpmc,SolverSignalKilled
    M=1<<len(bits);max_models=1<<primary;radix=max_models*2
    # The bound uses true independent choices, not Tseitin variable count.
    # Positive natural weights, no floating-point or negative coefficients.
    weights="".join(f"c p weight {l} {radix**(1<<i)} 0\nc p weight {-l} 1 0\n" for i,l in enumerate(bits))
    data=f"c t wmc\np cnf {c.n} {len(c.clauses)}\n"+weights+"".join(" ".join(map(str,cl))+" 0\n" for cl in c.clauses)
    path=tmp/"wide-pair.cnf";path.write_text(data)
    metrics=[];start=time.monotonic()
    row=dict(primary=primary,vars=c.n,clauses=len(c.clauses),modulus=M,
             radix_bits=primary+2,max_weight_bits=(radix**(M//2)).bit_length(),
             cnf_sha256=hashlib.sha256(data.encode()).hexdigest(),status="UNKNOWN",coeff=None,hist=None)
    try:
        stdout=profile_gpmc([str(gpmc),"-mode=1","-natw",str(path)],seconds,tmp/"wide-resource.tsv",metrics)
        packed=parse_gpmc_integer(stdout,"wmc",radix**M-1)
        hist=unpack_histogram(packed,radix,M,max_models)
        d=M//2;coeff=[hist[j]-hist[j+d] for j in range(d)]
        row.update(status="EXACT_HISTOGRAM",hist=hist,coeff=coeff)
    except (TimeoutError,subprocess.TimeoutExpired):row["status"]="ROOT_TIMEOUT"
    except SolverSignalKilled:row["status"]="ROOT_SIGNAL_KILL"
    row.update(root_s=time.monotonic()-start,queries=metrics)
    return row


def enumerate_hist(n,ops,pre,post,m):
    """Small independent path enumeration, not CNF evaluation."""
    M=1<<m;hist=[0]*M
    for x in range(1<<n):
        if not all(x>>i&1==b for i,b in pre.items()):continue
        paths=[(x,0)]
        for op,a,qs in ops:
            i=qs[0];b=1<<i;nxt=[]
            for z,p in paths:
                old=int(bool(z&b))
                if op in ("h","rx"):
                    for new in (0,1):
                        delta=(M//2)*old*new if op=="h" else (-M//4)*(old^new)
                        nxt.append(((z&~b)|(new<<i),(p+delta)%M))
                elif op=="x":nxt.append((z^b,p))
                elif op=="cx":nxt.append((z^((1<<qs[1]) if old else 0),p))
                else:
                    k={"s":M//4,"t":M//8,"tdg":-M//8}.get(op)
                    if op=="rz":k=WIDE_ANGLES[a]*M//32
                    assert k is not None
                    nxt.append((z,(p+k*old)%M))
            paths=nxt
        for z,p in paths:
            if all(z>>i&1==b for i,b in post.items()):continue
            for zz,q in paths:
                if zz==z:hist[(p-q)%M]+=1
    return hist


def wide_contract(gpmc,tmp):
    cases=[
        ("hh",1,[("h",None,[0]),("h",None,[0])],{0:0},{0:0}),
        ("hth",1,[("h",None,[0]),("t",None,[0]),("h",None,[0])],{0:0},{0:0}),
        ("rx-rz",1,[("rx","pi/2",[0]),("rz","pi/16",[0]),("rx","pi/2",[0])],{0:0},{0:0}),
        ("free-cx",2,[("h",None,[0]),("cx",None,[0,1]),("rz","-pi/8",[1]),("h",None,[1])],{},{1:0}),
        ("free-unused",2,[("x",None,[0])],{},{0:0}),
        ("empty-post",1,[("h",None,[0])],{},{}),
    ]
    checks=0
    for m in (3,4,5,6):
        for name,n,ops,p,q in cases:
            try:c,bits,primary,terms=gate_local_pair(n,ops,p,q,m)
            except ValueError:
                assert name=="rx-rz" and m<5 or name=="free-cx" and m<4
                continue
            expected=enumerate_hist(n,ops,p,q,m)
            row=wide_count(gpmc,tmp,c,bits,primary,10)
            assert row["hist"]==expected,(name,m,row,expected)
            checks+=1
    print("HOARE_WIDE_CONTRACT "+json.dumps(dict(checks=checks,exact_histograms=True)),flush=True)


def wide_paper_pilot(gpmc,tmp,data,name,blob):
    n,_,ops=paper_parse(data)
    m=5 if name=="noancilla" else 3
    t=time.monotonic()
    c,bits,primary,terms=gate_local_pair(n,ops,{4:0},{4:0},m)
    prep=time.monotonic()-t
    row=wide_count(gpmc,tmp,c,bits,primary,60)
    h=sum(op=="rx" for op,_,_ in ops)
    expected=[((4<<h) if name=="noancilla" else 0)]+[0]*((1<<(m-1))-1)
    if row["coeff"] is not None:
        assert row["coeff"]==expected,(name,row["coeff"],expected)
    row.update(case=name,source_blob=blob,h=h,phase_terms=terms,encoding_s=prep,
               expected_coeff=expected,verdict=("REFUTED" if any(expected) else "PROVED") if row["coeff"] is not None else "UNKNOWN")
    # Full histogram can contain hundreds of large integers in future.
    row.pop("hist")
    print("HOARE_WIDE_PAPER "+json.dumps(row),flush=True)




# R28B: gate-local frontier contraction of the SAME paired path domain.
# Forward: unnormalized U P U^dagger. Backward: U^dagger (I-Q) U.
# Each H/RX gate contributes its numerator on both copies; defer 2^-h.
# Exact dense/sparse density-operator propagation is established prior
# art. This is a bounded alternative path-sum summation schedule, not a
# claim of a novel density-matrix algorithm or large-width scalability.
class FrontierLimit(Exception):
    pass


def frontier_contract(n,ops,pre,post,m,orientation,deadline,
                      max_work=5_000_000,max_live=65536):
    assert 3<=m<=6 and 0<n<=16 and orientation in ("forward","backward")
    assert all(0<=i<n and b in (0,1) for p in (pre,post) for i,b in p.items())
    M=1<<m;D=M//2;N=1<<n
    zero=(0,)*D;one=(1,)+(0,)*(D-1)
    stats=dict(work=0,peak_entries=0,peak_frontier=0,gates_done=0,h_done=0,
               width_bound=2*n,orientation=orientation)
    def matches(x,p):return all(x>>i&1==b for i,b in p.items())
    def check():
        if time.monotonic()>=deadline:raise FrontierLimit("time")
    def charge(k):
        stats["work"]+=k
        if stats["work"]>max_work:raise FrontierLimit("work")
        check()
    def observe(old,new):
        stats["peak_entries"]=max(stats["peak_entries"],old+new)
        stats["peak_frontier"]=max(stats["peak_frontier"],old,new)
        if old+new>max_live:raise FrontierLimit("live-entries")
    def shift(a,k):
        k%=M
        if not k:return a
        neg=k>=D;k%=D
        out=tuple(-x for x in a[D-k:])+a[:D-k] if k else a
        return tuple(-x for x in out) if neg else out
    def add(a,b):return tuple(x+y for x,y in zip(a,b))
    def accum(dst,key,val,old):
        if val==zero:return
        if key in dst:
            val=add(dst[key],val)
            if val==zero:del dst[key]
            else:dst[key]=val
        else:
            observe(old,len(dst)+1)
            dst[key]=val
    def step_mix(front,bit,kind,sign):
        # One local copy contraction. Every old wire value is summed
        # exactly once into either new value; opposite copy retained.
        charge(2*len(front))
        out={}
        for key,val in front.items():
            old=int(bool(key&bit));base=key&~bit
            if kind=="h":
                accum(out,base,val,len(front))
                accum(out,base|bit,shift(val,sign*(M//2)*old),len(front))
            else:
                accum(out,base,shift(val,sign*(-M//4)*old),len(front))
                accum(out,base|bit,shift(val,sign*(-M//4)*(1-old)),len(front))
        return out
    start=time.monotonic()
    front={}
    try:
        # No projection or averaging here: each legal basis input has
        # coefficient one. A backward seed uses the entire bad projector.
        for x in range(N):
            if x%1024==0:check()
            if (matches(x,pre) if orientation=="forward" else not matches(x,post)):
                observe(0,len(front)+1);front[x|(x<<n)]=one
        sign=1 if orientation=="forward" else -1
        for op,a,qs in (ops if orientation=="forward" else reversed(ops)):
            check();i=qs[0];b=1<<i
            if op in ("h","rx"):
                if op=="rx" and a!="pi/2":raise ValueError("unsupported rx")
                front=step_mix(front,b,op,sign)
                front=step_mix(front,b<<n,op,-sign)
                stats["h_done"]+=1
            elif op in ("x","cx"):
                charge(len(front))
                out={}
                target=b if op=="x" else 1<<qs[1]
                for key,val in front.items():
                    flip=target if op=="x" or key&b else 0
                    if op=="x" or key&(b<<n):flip|=target<<n
                    observe(len(front),len(out)+1);out[key^flip]=val
                front=out
            elif op in ("s","t","tdg","rz"):
                if op=="rz":
                    v=WIDE_ANGLES[a]*M
                    if v%32:raise ValueError("angle outside exact phase modulus")
                    k=v//32
                else:k={"s":M//4,"t":M//8,"tdg":-M//8}[op]
                charge(len(front))
                # Same pair key; only its root-of-unity coefficient changes.
                # No second frontier map is allocated.
                for key in front:
                    delta=int(bool(key&b))-int(bool(key&(b<<n)))
                    if delta:front[key]=shift(front[key],sign*k*delta)
            else:raise ValueError("unsupported gate "+op)
            stats["gates_done"]+=1
        charge(N)
        total=zero
        trace=zero
        for x in range(N):
            v=front.get(x|(x<<n),zero)
            trace=add(trace,v)
            if (not matches(x,post) if orientation=="forward" else matches(x,pre)):
                total=add(total,v)
        seed_rank=(1<<(n-len(pre))) if orientation=="forward" else N-(1<<(n-len(post)))
        assert trace==(seed_rank*(1<<stats["h_done"]),)+(0,)*(D-1),("trace",orientation,trace)
        assert total[D//2]==0 and all(total[j]==-total[D-j] for j in range(1,D))
        assert stats["h_done"]==sum(op in ("h","rx") for op,_,_ in ops)
        return dict(status="EXACT_FRONTIER",coeff=list(total),stats=stats,root_s=time.monotonic()-start,
                    verdict="REFUTED" if any(total) else "PROVED",trace_check=True)
    except FrontierLimit as e:
        return dict(status="FRONTIER_"+str(e).upper().replace("-","_"),coeff=None,stats=stats,
                    root_s=time.monotonic()-start,verdict="UNKNOWN",trace_check=False)


def frontier_contract_tests():
    import random
    rng=random.Random(2802)
    checks=0
    for m in (3,4,5,6):
        for j in range(32):
            n=1+j%3
            ops=[]
            for _ in range(1+j%8):
                op=rng.choice(("h","rx","x","s","t","tdg","rz")+(("cx",) if n>1 else ()))
                i=rng.randrange(n)
                qs=[i];a=None
                if op=="cx":qs.append(rng.choice([k for k in range(n) if k!=i]))
                if op=="rx":a="pi/2"
                if op=="rz":a=rng.choice([a for a,k in WIDE_ANGLES.items() if (k*(1<<m))%32==0])
                ops.append((op,a,qs))
            p={i:rng.randrange(2) for i in range(n) if rng.randrange(2)}
            q={i:rng.randrange(2) for i in range(n) if rng.randrange(2)}
            hist=enumerate_hist(n,ops,p,q,m);D=1<<(m-1)
            expected=[hist[k]-hist[k+D] for k in range(D)]
            for orientation in ("forward","backward"):
                row=frontier_contract(n,ops,p,q,m,orientation,time.monotonic()+3)
                assert row["coeff"]==expected and row["trace_check"],(n,m,ops,p,q,row,expected)
                checks+=1
    for kwargs in (dict(max_work=0),dict(max_live=1)):
        row=frontier_contract(2,[("h",None,[0])],{}, {0:0},3,"forward",time.monotonic()+3,**kwargs)
        assert row["coeff"] is None and row["verdict"]=="UNKNOWN"
        checks+=1
    row=frontier_contract(2,[],{}, {0:0},3,"forward",time.monotonic()-1)
    assert row["status"]=="FRONTIER_TIME" and row["coeff"] is None
    print("HOARE_FRONTIER_CONTRACT "+json.dumps(dict(checks=checks+1,exact_coefficients=True)),flush=True)


def frontier_paper_pilot(data,name,blob):
    n,_,ops=paper_parse(data);m=5 if name=="noancilla" else 3
    h=sum(op=="rx" for op,_,_ in ops)
    expected=[((4<<h) if name=="noancilla" else 0)]+[0]*((1<<(m-1))-1)
    for orientation in ("forward","backward"):
        row=frontier_contract(n,ops,{4:0},{4:0},m,orientation,time.monotonic()+30)
        if row["coeff"] is not None:assert row["coeff"]==expected,(name,row,expected)
        row.update(case=name,source_blob=blob,source_sha256=hashlib.sha256(data).hexdigest(),
                   h=h,n=n,gates=len(ops),modulus=1<<m,expected_coeff=expected)
        print("HOARE_FRONTIER_PAPER "+json.dumps(row),flush=True)




# R28C: deterministic, oracle-independent routing. Conservative structural
# upper bounds, not learned performance predictions. Factor eligibility
# comes from exact admission; full GPMC fallback never uses partial sums.
def dispatch_policy(n,h,gates,frontier_admitted,factor_admitted):
    bound=4**n
    frontier_work=bound*(gates+3*h)+(1<<n)
    routes=[]
    if frontier_admitted and h>=24 and 2*bound<=65536 and frontier_work<=5_000_000:
        routes.append("frontier")
    if factor_admitted:routes.append("factor")
    routes.append("gpmc")
    return routes,dict(frontier_work_bound=frontier_work,frontier_entries_bound=2*bound,
                      frontier_admitted=frontier_admitted,factor_admitted=factor_admitted)


def execute_routes(routes,callbacks,deadline):
    """Common solve deadline. No failed/partial result is reused. An exact
    result arriving after the deadline is explicitly rejected."""
    attempts=[]
    for route in routes:
        start=time.monotonic()
        if start>=deadline:break
        row=callbacks[route](deadline)
        stop=time.monotonic()
        assert "coeff" in row
        if stop>deadline and row["coeff"] is not None:
            row=dict(row,coeff=None,status="LATE_EXACT_REJECTED")
        attempts.append(dict(route=route,elapsed_s=stop-start,**row))
        if row["coeff"] is not None:
            return dict(route=route,status=row["status"],coeff=row["coeff"],attempts=attempts)
    return dict(route="none",status="UNKNOWN_ALL_ROUTES",coeff=None,attempts=attempts)


def dispatch_contract_tests():
    assert dispatch_policy(5,183,1305,True,False)[0]==["frontier","gpmc"]
    assert dispatch_policy(15,45,175,True,True)[0]==["factor","gpmc"]
    assert dispatch_policy(3,2,10,False,False)[0]==["gpmc"]
    seen=[]
    def incomplete(end):seen.append("factor");return dict(coeff=None,status="LIMIT")
    def exact(end):seen.append("gpmc");return dict(coeff=[0,0],status="EXACT")
    r=execute_routes(["factor","gpmc"],{"factor":incomplete,"gpmc":exact},time.monotonic()+1)
    assert seen==["factor","gpmc"] and r["coeff"]==[0,0] and r["route"]=="gpmc"
    seen.clear()
    r=execute_routes(["gpmc"],{"gpmc":exact},time.monotonic()-1)
    assert not seen and r["coeff"] is None
    def late(end):
        while time.monotonic()<end:pass
        return dict(coeff=[0,0],status="EXACT")
    r=execute_routes(["factor","gpmc"],{"factor":late,"gpmc":exact},time.monotonic()+.001)
    assert r["coeff"] is None and r["attempts"][0]["status"]=="LATE_EXACT_REJECTED"
    print("HOARE_DISPATCH_CONTRACT checks=6",flush=True)


def dispatch_paper(gpmc,tmp,data,name,blob):
    start=time.monotonic()
    n,_,ops=paper_parse(data);m=5 if name=="noancilla" else 3
    h=sum(op=="rx" for op,_,_ in ops)
    routes,profile=dispatch_policy(n,h,len(ops),True,False)
    expected=[((4<<h) if name=="noancilla" else 0)]+[0]*((1<<(m-1))-1)
    def frontier(end):
        r=frontier_contract(n,ops,{4:0},{4:0},m,"backward",min(end,time.monotonic()+15))
        return dict(coeff=r["coeff"],status=r["status"],stats=r["stats"])
    def wmc(end):
        c,bits,primary,_=gate_local_pair(n,ops,{4:0},{4:0},m)
        remaining=end-time.monotonic()
        if remaining<=0:return dict(coeff=None,status="ENCODING_DEADLINE")
        row=wide_count(gpmc,tmp,c,bits,primary,remaining)
        row.pop("hist",None)
        return row
    row=execute_routes(routes,{"frontier":frontier,"gpmc":wmc},start+30)
    if row["coeff"] is not None:assert row["coeff"]==expected,(name,row)
    row.update(case=name,source_blob=blob,n=n,h=h,gates=len(ops),modulus=1<<m,
               profile=profile,planned_routes=routes,expected_coeff=expected,cap_s=30,
               elapsed_s=time.monotonic()-start,
               verdict="UNKNOWN" if row["coeff"] is None else "REFUTED" if any(row["coeff"]) else "PROVED")
    print("HOARE_DISPATCH_PAPER "+json.dumps(row),flush=True)



def paper_compare(gpmc):
    import quokka_sharp as qs
    from quokka_sharp import config
    config.CONFIG.update(ToolInvocation=f"{gpmc} -mode=1 -prec=50",Precision=50,DEBUG=False,FPE=D("1e-12"),TIMEOUT=30)
    decimal.getcontext().prec=50
    known={}
    with tempfile.TemporaryDirectory(prefix="hoare-paper-") as tmp:
        tmp=pathlib.Path(tmp)
        wide_contract(gpmc,tmp)
        frontier_contract_tests()
        dispatch_contract_tests()
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
            dispatch_paper(gpmc,tmp,data,name,blob)
            if os.environ.get("HOARE_FRONTIER_REPEAT")=="1":
                frontier_paper_pilot(data,name,blob)
            if os.environ.get("HOARE_WIDE_PAPER_REPEAT")=="1":
                wide_paper_pilot(gpmc,tmp,data,name,blob)
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
        receipt=scan_paper_archive(tmp,known) if os.environ.get("HOARE_RETRY_PAPER_ARCHIVE")=="1" else dict(status="DEFERRED_AFTER_TIMEOUT",doi="10.5281/zenodo.19833587")
        # Keep machine-readable provenance; no untrusted archive execution.
        print("HOARE_PAPER_ARCHIVE "+json.dumps(receipt),flush=True)



if __name__=="__main__":
    directory=pathlib.Path(sys.argv[1]);gpmc=pathlib.Path(sys.argv[2]).resolve()
    compare(directory,gpmc)
    compare(directory,gpmc,extended=True)
    paper_compare(gpmc)
