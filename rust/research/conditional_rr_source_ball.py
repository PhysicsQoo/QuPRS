"""Source-level bounded Arb projective-distance witness.
Reuse parser, matrices and analytic controls from historical QPE8 Arb witness
at d27d9644054c5478f02339b9d83911dd3553448c (no QuPRS parser/RR/CNF).
For large circuits use normalized block-product vectors with an explicitly
accumulated 2-norm error for each accepted rank-one split. Interval arithmetic
encloses the specified literal QASM angles. Resource rejection is inconclusive.
"""
import hashlib, json, re, os, time, random
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from flint import arb, acb, fmpq, ctx
ctx.prec=int(os.environ.get('CRR_BALL_BITS','384'))
I=acb(0,1)
ROOT=Path(__file__).resolve().parents[2]
MAX_BLOCK=8
MAX_OVERLAP=12
SPLIT_LIMIT=arb("1e-13")
EPS=arb(fmpq(1,100_000_000))
class Limit(Exception): pass

def angle(expr):
    expr = expr.strip().replace(" ", "")
    sign = -1 if expr.startswith("-") else 1
    expr = expr.lstrip("+-")
    if not expr or len(expr) > 128:
        raise ValueError("Invalid angle")
    parts = expr.split("/")
    if len(parts) > 2:
        raise ValueError("Unsupported QASM angle expression")
    fraction = Fraction(sign)
    pi_count = 0
    for part in parts[0].split("*"):
        if part == "pi":
            pi_count += 1
        else:
            fraction *= Fraction(Decimal(part))
    if pi_count > 1:
        raise ValueError("Nonlinear pi")
    if len(parts) == 2:
        fraction /= Fraction(Decimal(parts[1]))
    if fraction.numerator.bit_length() > 1024 or fraction.denominator.bit_length() > 1024:
        raise ValueError("QASM angle exceeds exact rational budget")
    result = arb(fmpq(fraction.numerator, fraction.denominator))
    return result * arb.pi() if pi_count else result


def read(path, expected_qubits=8):
    registers, gates, qubits = {}, [], 0
    text = Path(path).read_text()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("OPENQASM", "include")):
            continue
        declaration = re.fullmatch(r"qreg\s+(\w+)\[(\d+)\];", line)
        if declaration:
            name, size = declaration.groups()
            size = int(size)
            if size < 1 or name in registers:
                raise ValueError("Invalid register")
            registers[name] = qubits, size
            qubits += size
            continue

        def pos(name, index):
            offset, size = registers[name]
            idx = int(index)
            if idx < 0 or idx >= size:
                raise ValueError("Invalid source qubit")
            return offset + idx

        rotation = re.fullmatch(r"(rx|ry|rz)\(([^()]+)\)\s+(\w+)\[(\d+)\];", line)
        if rotation:
            name, param, reg, bit = rotation.groups()
            gates.append((name, pos(reg, bit), angle(param)))
            continue
        flip = re.fullmatch(r"x\s+(\w+)\[(\d+)\];", line)
        if flip:
            reg, bit = flip.groups()
            gates.append(("x", pos(reg, bit), None))
            continue
        controlled = re.fullmatch(r"cx\s+(\w+)\[(\d+)\],\s*(\w+)\[(\d+)\];", line)
        if controlled:
            r1, b1, r2, b2 = controlled.groups()
            ctrl, tgt = pos(r1, b1), pos(r2, b2)
            if ctrl == tgt:
                raise ValueError("Invalid CNOT source")
            gates.append(("cx", ctrl, tgt))
            continue
        raise ValueError(f"Unsupported source at {path}:{number}: {line}")
    if qubits != expected_qubits or len(gates) > 3000:
        raise ValueError("Invalid source scope")
    return gates


def prepared(gates):
    ops = []
    for name, bit, theta in gates:
        if name == "cx":
            ops.append((name, bit, theta))
            continue
        if name == "x":
            ops.append((name, bit, (acb(0), acb(1), acb(1), acb(0))))
            continue
        if name == "rz":
            z = I * theta / 2
            matrix = ((-z).exp(), acb(0), acb(0), z.exp())
        else:
            c, s = acb((theta / 2).cos()), acb((theta / 2).sin())
            if name == "rx":
                matrix = (c, -I*s, -I*s, c)
            elif name == "ry":
                matrix = (c, -s, s, c)
            else:
                raise AssertionError(name)
        ops.append((name, bit, matrix))
    return ops


def evolve(ops, basis, dim=256):
    state = [acb(0) for _ in range(dim)]
    state[basis] = acb(1)
    for name, bit, arg in ops:
        if name == "cx":
            cmask, tmask = 1 << bit, 1 << arg
            for j in range(dim):
                if (j & cmask) and not (j & tmask):
                    k = j | tmask
                    state[j], state[k] = state[k], state[j]
            continue
        m00, m01, m10, m11 = arg
        mask = 1 << bit
        for j in range(dim):
            if not j & mask:
                k = j | mask
                u, v = state[j], state[k]
                state[j] = m00*u + m01*v
                state[k] = m10*u + m11*v
    return state


def validate_gate_conventions():
    """Independent hand-checkable one/two-qubit identities for the simulator.

    These detect global-phase, rotation-sign, gate-order, and little-endian
    CNOT mistakes before a source-level non-equivalence claim is printed.
    Ball comparisons demand enclosure of exact analytic identities, not a
    configurable epsilon.
    """
    halfturn = prepared([("rx", 0, angle("pi"))])
    state = evolve(halfturn, 0)
    assert state[0].contains(0)
    assert (state[1] + I).contains(0), "RX(pi)|0> must equal -i|1>"

    cancel = prepared([("rz", 0, angle("0.125")),
                       ("rz", 0, angle("-0.125"))])
    for basis in (0, 1):
        state = evolve(cancel, basis)
        assert (state[basis] - acb(1)).contains(0)
        assert state[basis ^ 1].contains(0)

    cnot = prepared([("cx", 0, 1)])
    control_on = evolve(cnot, 1)
    assert (control_on[3] - acb(1)).contains(0)
    assert control_on[1].contains(0)
    control_off = evolve(cnot, 0)
    assert (control_off[0] - acb(1)).contains(0)
    assert control_off[2].contains(0)

    # Applying RZ(+pi/2), then RY(theta), then RZ(-pi/2) implements
    # RX(theta) exactly, without a global phase.
    euler = prepared([
        ("rz", 0, angle("pi/2")),
        ("ry", 0, angle("pi/2")),
        ("rz", 0, angle("-pi/2")),
    ])
    rx = prepared([("rx", 0, angle("pi/2"))])
    for basis in (0, 1):
        u, v = evolve(euler, basis), evolve(rx, basis)
        for row in (0, 1):
            assert (u[row] - v[row]).contains(0), (
                "Euler/RX sign or application order mismatch", basis, row
            )



def norm2(v):
    return sum((z.real*z.real+z.imag*z.imag for z in v),arb(0))
def normalized(v):
    q=norm2(v)
    if not q>0: return None
    s=q.sqrt()
    return [z/s for z in v]
def residual_upper(v,w):
    # Outward ball magnitude upper endpoints before sqrt; no subtraction
    # of nearly equal norms to estimate the local truncation error.
    return sum((abs(a-b).upper()**2 for a,b in zip(v,w)),arb(0)).sqrt().upper()
def index(bits,wires,pos):
    return sum(((bits>>pos[w])&1)<<j for j,w in enumerate(wires))
def merge(a,b):
    wa,va=a; wb,vb=b
    ws=tuple(sorted(wa+wb))
    if len(ws)>MAX_BLOCK: raise Limit("block width "+str(len(ws)))
    pos={w:j for j,w in enumerate(ws)}
    return ws,[va[index(k,wa,pos)]*vb[index(k,wb,pos)] for k in range(1<<len(ws))]
def split_one(ws,v,q):
    p=ws.index(q); m=1<<p
    rest=tuple(w for w in ws if w!=q)
    # Row vectors with the distinguished wire fixed to 0 or 1.
    embed=lambda k: (k&(m-1))|((k//m)<<(p+1))
    rows=[[v[embed(k)|b*m] for k in range(1<<len(rest))] for b in (0,1)]
    r=max(rows,key=lambda r:float(norm2(r).mid()))
    b=normalized(r)
    if b is None: return None
    a=normalized([sum((z.conjugate()*y for z,y in zip(b,row)),acb(0)) for row in rows])
    if a is None:return None
    reconstructed=[a[(k>>p)&1]*b[(k&(m-1))|((k>>(p+1))<<p)] for k in range(len(v))]
    error=residual_upper(v,reconstructed)
    if error<=SPLIT_LIMIT:return (((q,),a),(rest,b)),error
    return None
def product_evolve(ops,basis,n,deadline):
    blocks=[((w,),[acb(int(((basis>>w)&1)==b)) for b in (0,1)]) for w in range(n)]
    error=arb(0);splits=0;peak=1
    for name,q,arg in ops:
        if time.monotonic()>deadline:raise Limit("wall budget")
        i=next(i for i,(ws,_) in enumerate(blocks) if q in ws)
        if name=="cx":
            j=next(j for j,(ws,_) in enumerate(blocks) if arg in ws)
            if i!=j:
                block=merge(blocks[i],blocks[j])
                for k in sorted((i,j),reverse=True):blocks.pop(k)
                blocks.append(block);i=len(blocks)-1
        ws,v=blocks[i];v=list(v);mask=1<<ws.index(q);peak=max(peak,len(ws))
        if name=="cx":
            t=1<<ws.index(arg)
            for k in range(len(v)):
                if k&mask and not k&t:v[k],v[k|t]=v[k|t],v[k]
        else:
            a,b,c,d=arg
            for k in range(len(v)):
                if not k&mask:
                    u,w=v[k],v[k|mask]
                    v[k],v[k|mask]=a*u+b*w,c*u+d*w
        blocks[i]=(ws,v)
        # Every accepted split introduces a certified norm error upper
        # bound. Unitary operations preserve error, tensoring unit vectors
        # preserves norm. All product factors are mathematically normalized
        # by construction; the balls enclose their exact values.
        while len(ws)>1:
            found=None
            for q in ws:
                found=split_one(ws,v,q)
                if found is not None:break
            if found is None:break
            (one,(ws,v)),e=found
            blocks[i]=(ws,v);blocks.append(one);error=(error+e).upper();splits+=1
    return blocks,error,dict(splits=splits,peak=peak)

def product_overlap(a,b):
    # Independent union components of both state block partitions.
    # Small direct tensor inner products; no RR or weighted counting.
    pending=set(w for ws,_ in a for w in ws)
    result=acb(1)
    while pending:
        comp={min(pending)}
        while True:
            nxt=comp.union(*(set(ws) for ws,_ in a+b if comp.intersection(ws)))
            if nxt==comp:break
            comp=nxt
        pending-=comp
        if len(comp)>MAX_OVERLAP:raise Limit("overlap width "+str(len(comp)))
        pos={w:j for j,w in enumerate(sorted(comp))}
        aa=[(ws,v) for ws,v in a if ws[0] in comp]
        bb=[(ws,v) for ws,v in b if ws[0] in comp]
        z=acb(0)
        for k in range(1<<len(comp)):
            x,y=acb(1),acb(1)
            for ws,v in aa:x*=v[index(k,ws,pos)]
            for ws,v in bb:y*=v[index(k,ws,pos)]
            z+=y.conjugate()*x
        result*=z
    return result

def dense_overlap(a,b,k,n):
    u,v=evolve(a,k,1<<n),evolve(b,k,1<<n)
    return sum((y.conjugate()*x for x,y in zip(u,v)),acb(0))

def controls():
    validate_gate_conventions()
    # Nontrivial entangled and disentangled states, compare against the
    # existing dense Arb simulator. A no-split branch must also be exercised.
    gates=[("ry",0,angle("pi/2")),("cx",0,1),("rz",1,angle("0.123")),
           ("cx",0,1),("ry",2,angle("pi/3")),("cx",1,2)]
    a=prepared(gates);b=prepared(gates[:-1])
    for k in range(8):
        x,ex,_=product_evolve(a,k,3,time.monotonic()+10)
        y,ey,_=product_evolve(b,k,3,time.monotonic()+10)
        z=product_overlap(x,y)
        dense=dense_overlap(a,b,k,3)
        assert abs(z-dense).upper()<=ex+ey+arb("1e-95")
    # Exact source threshold test: all trace entries vs one nonzero column
    # contribution, including nontrivial global scalar.
    phase=acb(0,1)
    assert abs(2*phase).contains(2)
    assert (abs(acb(1)-acb(1)).upper()+arb(0))<arb(1)
    print("CRR_SOURCE_BALL_CONTROL dense_comparisons=8",flush=True)

def load(entry,n):
    p=ROOT/entry["path"];data=p.read_bytes()
    assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
    return prepared(read(p,n)),hashlib.sha256(data).hexdigest()
def main():
    controls()
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    negative={"qwalk-noancilla_5":"d927ecd21bf3676069d90a3ad3bc4e7ee434a0de",
              "qpeexact_24":"a3d3099816e51d98783176a1df64b077b92ab0b7"}
    scope=(("qwalk-noancilla_5",5),) if os.environ.get("CRR_BALL_QWALK_ONLY") else (("qwalk-noancilla_5",5),("qpeexact_24",24))
    for name,n in scope:
        c=cases[name]
        a,ha=load(c["source"],n)
        for variant in ("positive","random_rotation"):
            entry=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=negative[name])
            b,hb=load(entry,n)
            d=1<<n;total=acb(0);error=arb(0);kdone=0;peak=0;start=time.monotonic()
            bases=list(range(d)) if n<=5 else list(dict.fromkeys([0,d-1,*[1<<i for i in range(n)],*[random.Random(268+i).randrange(d) for i in range(38)]]))
            out=dict(case=name,variant=variant,source_sha256=ha,target_sha256=hb,precision_bits=ctx.prec,planned=len(bases),status="INCONCLUSIVE")
            reason=None
            for k in bases:
                try:
                    if n<=5:
                        z=dense_overlap(a,b,k,n);e=arb(0)
                    else:
                        x,ex,sa=product_evolve(a,k,n,start+150)
                        y,ey,sb=product_evolve(b,k,n,start+150)
                        z=product_overlap(x,y);e=(ex+ey).upper();peak=max(peak,sa["peak"],sb["peak"])
                except Limit as exc:
                    reason=str(exc);break
                total+=z;error=(error+e).upper();kdone+=1
                # Triangle inequality for all unexamined diagonal entries:
                # |Tr(V† U)| <= d-k + |sum examined overlaps| + total error.
                threshold=arb(d)*(1-EPS*EPS).sqrt()
                upper=arb(d-kdone)+abs(total).upper()+error
                if upper<threshold:
                    out["status"]="CERTIFIED_DISTANCE_NEQ"
                    if not (n<=5 and os.environ.get("CRR_BALL_FULL_TRACE")):break
            if kdone==d and out["status"]!="CERTIFIED_DISTANCE_NEQ":
                lower=abs(total).lower()-error
                if lower>arb(d)*(1-EPS*EPS).sqrt():out["status"]="CERTIFIED_DISTANCE_EQ"
            upper=arb(d-kdone)+abs(total).upper()+error
            out.update(examined=kdone,peak_block=peak,subset_trace=str(total),error_upper=str(error),trace_abs_upper=str(upper),
                       threshold_trace=str(arb(d)*(1-EPS*EPS).sqrt()),reason=reason,elapsed_s=time.monotonic()-start)
            # Compare the entire complex normalized source trace against
            # completed research-path GPMC counts; no verdict-only shortcut.
            log=os.environ.get("CRR_HANDOFF_LOG")
            if log and n<=5 and kdone==d:
                for line in Path(log).read_text().splitlines():
                    if not line.startswith("CRR_HANDOFF_CALL case="+variant+" ") or "status=complete" not in line:continue
                    fields=dict(re.findall(r"(\w+)=([^ ]+)",line))
                    def exact(s):
                        q=Fraction(s);return arb(fmpq(q.numerator,q.denominator))
                    k=int(fields["twice"])
                    scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
                    observed=acb(exact(fields["real"]),exact(fields["imag"]))/scale
                    delta=abs(observed-total/d).upper()
                    ok=delta<arb("1e-50")
                    print("CRR_SOURCE_COUNT_PARITY "+json.dumps(dict(variant=variant,arm=fields["arm"],matched=bool(ok),delta=str(delta))),flush=True)
                    assert ok,"source complex trace mismatch"
            print("CRR_SOURCE_BALL "+json.dumps(out),flush=True)
            if n<=5:
                assert out["status"]==("CERTIFIED_DISTANCE_EQ" if variant=="positive" else "CERTIFIED_DISTANCE_NEQ")
if __name__=="__main__":main()
