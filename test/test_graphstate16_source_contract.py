"""Graphstate16 strict source vs opt-in approximate distance controls.

Exact mathematical conclusions are conditional on the native reduction's
faithful representation of the SHA-pinned full 16-qubit miter. An independent
NumPy source-QASM statevector checks representative inputs numerically, never
claims that floating equality certifies exact equivalence.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from QuPRS import check_equivalence

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
B = ROOT / "benchmarks/MQTBench/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
BLOBS = (
    "ab34308febb31ea9a49e9761a988aad7017f3487",
    "c2c6f9d04f6a8c2778415572aa247ee93e138c09",
)
ANGLE_PAIRS = {
    Fraction(Decimal("3.1415926535897931")):
        ("2.0330832984526417", "1.1085093551371514"),
    Fraction(Decimal("3.1415926535897911")):
        ("2.8600220891857973", "0.2815705644039938"),
}
TERM = re.compile(
    r"\+\s*\(([-+]?\d+/\d+)\s*\+\s*\(([-+]?\d+/\d+)\)/pi\)"
    r"\s*\*\s*\[x_(\d+)\]"
)
SCALAR = re.compile(r"\+\s*0\s*\+\s*\(([-+]?\d+/\d+)\)/pi")


def git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def pi_bounds(terms=40):
    """Rigorous rational bounds: pi=16 atan(1/5)-4 atan(1/239)."""
    def atan(x):
        p = sum(((-1)**k*x**(2*k+1)/ (2*k+1) for k in range(terms)), Fraction())
        rem = x**(2*terms+1)/(2*terms+1)
        return (p,p+rem) if terms%2==0 else (p-rem,p)
    al,ah=atan(Fraction(1,5))
    bl,bh=atan(Fraction(1,239))
    return 16*al-4*bh,16*ah-4*bl


def independent_source_contract():
    assert [git_blob_sha(p) for p in (A,B)] == list(BLOBS)
    x,y=A.read_text(),B.read_text()
    edges=lambda s: re.findall(r"^cx q\[(\d+)\],q\[(\d+)\];$",s,re.M)
    assert edges(x)==edges(y) and len(edges(x))==16
    for total,pair in ANGLE_PAIRS.items():
        assert all(v in y for v in pair)
        assert sum(map(lambda s: Fraction(Decimal(s)),pair))==total
    return x,y


def certificate_from_reduced(full_text):
    """Reject incomplete/unsupported PathSum forms, do not silently ignore."""
    assert "Active Path Vars (Count: 0): None" in full_text
    assert "Phase Polynomial P:" in full_text and "Basis F:" in full_text
    poly=full_text.split("Phase Polynomial P:",1)[1].split("Basis F:",1)[0]
    terms={}
    scalar_count=0
    for raw in poly.splitlines():
        line=raw.strip()
        if not line:
            continue
        m=TERM.fullmatch(line)
        if m:
            c,r,bit=Fraction(m[1]),Fraction(m[2]),int(m[3])
            assert bit not in terms and 0<=bit<16 and c==Fraction(1,2)
            terms[bit]=(c,r)
            continue
        m=SCALAR.fullmatch(line)
        if m:
            assert scalar_count==0
            Fraction(m[1])
            scalar_count+=1
            continue
        raise AssertionError(f"Unsupported reduced phase: {line}")
    assert scalar_count==1 and len(terms)==8
    basis=full_text.split("Basis F:",1)[1]
    pairs=re.findall(r"^\s*\|q_(\d+)>\s*=\s*x_(\d+)\s*$",basis,re.M)
    assert sorted((int(a),int(b)) for a,b in pairs)==[(i,i) for i in range(16)]
    lo_pi,hi_pi=pi_bounds()
    counts={k:0 for k in ANGLE_PAIRS}
    residuals={}
    for bit,(c,r) in terms.items():
        source_sum=-2*r
        assert source_sum in ANGLE_PAIRS
        counts[source_sum]+=1
        # A computational basis with this one bit set differs by
        # e^(i delta); delta=pi-source_sum is provably nonzero modulo 2pi.
        lo,hi=lo_pi-source_sum,hi_pi-source_sum
        assert Fraction(0)<lo<hi<Fraction(1,10**10)
        residuals[bit]=(lo,hi)
    assert sorted(counts.values())==[4,4]
    # Full-unitary metric for diagonal miter:
    # |Tr(U†V)/2^16| = prod_j cos(delta_j/2).
    # 1 - prod cos²(delta_j/2) <= sum delta_j²/4, exactly.
    distance_upper_sq=sum((hi**2 for _,hi in residuals.values()),Fraction())/4
    return residuals,distance_upper_sq


@lru_cache(maxsize=1)
def get_graphstate_reduced_certificate():
    """Obtain a source-pinned, independently invoked Rust reduction certificate.

    This is a conditional reducer certificate, not an independent proof of the
    source-to-PathSum translation. It is never part of benchmark timing.
    """
    independent_source_contract()
    res = check_equivalence(
        str(A), str(B), backend="rust", method="reduction_rules",
        strategy="Naive", tool_name="gpmc", timeout=30,
    )
    assert res.equivalent == "not_equivalent"
    assert res.tool_time is None
    return certificate_from_reduced(str(res.final_pathsum))


@pytest.fixture(scope="module")
def full_graphstate_certificate():
    return get_graphstate_reduced_certificate()


def test_graphstate_source_literal_identity():
    independent_source_contract()


def test_graphstate_strict_non_equivalence_up_to_phase(full_graphstate_certificate):
    residuals,_=full_graphstate_certificate
    bit=min(residuals)
    lo,hi=residuals[bit]
    # Full 16-qubit basis witness: |0> versus |1<<bit>.
    assert 0<lo<hi<Fraction(1,10**10)


def test_graphstate_independent_approximate_contract(full_graphstate_certificate):
    _,d_sq=full_graphstate_certificate
    # Opt-in approximate distance threshold, not legacy WMC magnitude tolerance.
    assert d_sq <= Fraction(Decimal("1e-8"))**2
    assert d_sq < Fraction(1,10**28)
    # A tighter configurable threshold is not certified by this upper bound.
    assert d_sq > Fraction(Decimal("1e-16"))**2


ANGLE = re.compile(r"^(r[xyz])\(([^)]+)\) q\[(\d+)\];$")
CX = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")
PI = re.compile(r"([+-]?)(?:(\d+(?:\.\d+)?)\*?)?pi(?:/(\d+(?:\.\d+)?))?")


def parse_minimal_source(s):
    ops=[]
    for line in s.splitlines():
        line=line.strip()
        if not line or line.startswith("//") or line.startswith(("OPENQASM","include ","qreg ")):
            continue
        m=CX.fullmatch(line)
        if m:
            ops.append(("cx",int(m[1]),int(m[2])))
            continue
        m=ANGLE.fullmatch(line)
        if m:
            raw=m[2]
            if "pi" in raw:
                r=PI.fullmatch(raw)
                assert r,raw
                theta=(-1 if r[1]=="-" else 1)*float(r[2] or "1")/float(r[3] or "1")*math.pi
            else:
                theta=float(raw)
            ops.append((m[1],int(m[3]),theta))
            continue
        raise AssertionError(f"Unsupported QASM: {line}")
    assert len([x for x in ops if x[0]=="cx"])==16
    return ops


def statevector_from_source(s, x):
    psi=np.zeros(1<<16,dtype=np.complex128)
    psi[x]=1
    indices=np.arange(1<<16,dtype=np.int32)
    for op,q,v in parse_minimal_source(s):
        if op=="cx":
            mask=((indices>>q)&1).astype(bool) & ~((indices>>v)&1).astype(bool)
            a=indices[mask];b=a^(1<<v)
            swap=psi[a].copy()
            psi[a]=psi[b];psi[b]=swap
            continue
        c,t=math.cos(v/2),math.sin(v/2)
        stride=1<<q
        view=psi.reshape(-1,2*stride)
        left,right=view[:,:stride].copy(),view[:,stride:].copy()
        if op=="rx":
            view[:,:stride]=c*left-1j*t*right
            view[:,stride:]=-1j*t*left+c*right
        elif op=="ry":
            view[:,:stride]=c*left-t*right
            view[:,stride:]=t*left+c*right
        else:
            view[:,:stride]=complex(c,-t)*left
            view[:,stride:]=complex(c,t)*right
    return psi


def test_graphstate_independent_source_statevector_smoke():
    src_a,src_b=independent_source_contract()
    for basis in (0,1,1<<3,1<<12,0xffff):
        a,b=statevector_from_source(src_a,basis),statevector_from_source(src_b,basis)
        assert abs(np.vdot(a,a)-1)<1e-12
        assert abs(np.vdot(b,b)-1)<1e-12
        # Binary64 cannot distinguish a ~1e-15 distance, only corroborates it.
        assert abs(abs(np.vdot(a,b))-1)<1e-11
    mutated=src_b.replace("ry(2.0330832984526417) q[1];",
                          "ry(2.0340832984526417) q[1];",1)
    assert mutated!=src_b
    a,b=statevector_from_source(src_a,0),statevector_from_source(mutated,0)
    assert abs(np.vdot(a,b))<0.999999999  # Nontrivial positive control.
