#!/usr/bin/env python3
"""L0 synthetic exact semantic smoke: no compiler build, corpus, MPFR, or WMC solver.
Exhaustive serialized-CNF oracle on tiny Clifford fixtures, not native EQ or E2E.
"""
import itertools
from fractions import Fraction
from eq_dag_e1a_census import scan,scale,ZERO,add
from eq_dag_e1b_encode import build,test
from eq_dag_d2a_rewrite import parse
from eq_dag_d3_ab import controls as count_controls

ROOTS={Fraction(0):(1,0),Fraction(1,4):(0,1),
       Fraction(1,2):(-1,0),Fraction(3,4):(0,-1)}

def weight(c,bits):
    assert c[1]==0 and c[0] in ROOTS
    return tuple(str(x) for x in ROOTS[c[0]])

def multiply(a,b):
    return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])

def enumerate_cnf(text,n):
    nv,comments,_,clauses=parse(text)
    assert nv<=12
    weights={}
    for line in comments:
        if line.startswith("c p weight "):
            s=line.split()
            weights[int(s[3])]=tuple(map(Fraction,s[4:6]))
    result={}
    for bits in itertools.product((0,1),repeat=nv):
        def sat(lit): return bool(bits[abs(lit)-1])==(lit>0)
        if not all(any(sat(lit) for lit in clause) for clause in clauses):
            continue
        key=bits[:n]
        assert key not in result,"nonunique auxiliary extension"
        z=(1,0)
        for lit,w in weights.items():
            if sat(lit): z=multiply(z,w)
        result[key]=z
    return result

def oracle(p,outputs,n):
    result={}
    for bits in itertools.product((0,1),repeat=n):
        def ev(m): return all(bits[x] for x in m)
        if any(bits[i] != sum(ev(m) for m in f)%2 for i,f in outputs.items()):
            continue
        c=ZERO
        for m,v in p.items():
            if ev(m): c=add(c,v)
        assert c[1]==0
        result[bits]=ROOTS[c[0]]
    return result

def main():
    test(weight)
    count_controls()
    c=(Fraction(1,4),Fraction(0))
    fixtures=(
        ("xor", {(0,1):c,(0,2):c,(0,1,2):scale(c,-2)}, {0:[(1,)]}),
        ("complement", {(1,):c,(1,2):scale(c,-1)}, {0:[(1,),(2,)]}),
    )
    for policy,p,outputs in fixtures:
        choices=scan(p,policy)["choices"]
        assert len(choices)==1 and choices[0]["kind"]==policy
        expected=oracle(p,outputs,4)
        assert expected and len(set(expected.values()))>1
        for plan in ([],choices):
            e=build(list(range(4)),1,p,outputs,plan,weight,96)
            actual=enumerate_cnf(e.render(),4)
            assert actual==expected,policy
        print("L0_FIXTURE",policy,"primary_models",len(expected))
    print("DAG_CI_L0_PASS synthetic_exact=true solver_calls=0 native_eq=false")

if __name__=="__main__":
    main()
