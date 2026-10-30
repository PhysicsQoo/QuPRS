#!/usr/bin/env python3
"""Standalone solver-free Path-sum -> weighted-CNF experiment.

Source-structure emulator of ps2wmc.py and wmc.rs, NOT native QuPRS.
All weights are exact Gaussian integers (quarter-turn phases). No external
solver, no extra production WMC calls, and no numerical equivalence claims.
"""
from __future__ import annotations
import argparse, json, statistics, time
from dataclasses import dataclass
from itertools import product
from pathlib import Path

ONE=(1,0)
QUARTER=((1,0),(0,1),(-1,0),(0,-1))

def mul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def mono_eval(mono, bits):return all(bits[i] for i in mono)
def anf_eval(anf,bits):return sum(mono_eval(m,bits) for m in anf)%2

@dataclass(frozen=True)
class Case:
    name:str
    n:int
    m:int
    outputs:tuple
    phase:tuple=()

CASES=(
 Case('identity_1',1,0,(((0,),),)),
 Case('identity_2',2,0,(((0,),),((1,),))),
 Case('unused_path_1',1,1,(((0,),),)),
 Case('unused_path_2',2,2,(((0,),),((1,),))),
 Case('scalar_phase',1,0,(((0,),),),((1,()),)),
 Case('phase_controlled_y',1,1,(((0,),),),((1,(1,)),)),
 Case('xor_output',2,1,(((0,),(1,),(2,)),((1,),))),
 Case('and_output',2,1,(((0,2),),((1,),)),((1,(2,)),)),
 Case('constant_zero',2,0,((),((1,),))),
 Case('boolean_with_phase',2,1,(((0,),(2,)),((1,2),)),((1,(0,2)),(2,()))),
)

class Encoder:
    def __init__(self,case:Case,mode:str):
        self.case=case
        self.mode=mode
        self.clauses=[]
        self.mapping={}
        self.next_id=1
        self.weights={}
        if mode in ('python','rust_reserved'):
            for v in range(case.n+case.m): self.var(v)
    def fresh(self):
        v=self.next_id;self.next_id+=1;return v
    def var(self,x):
        if x not in self.mapping:self.mapping[x]=self.fresh()
        return self.mapping[x]
    def clause(self,*lits):self.clauses.append(tuple(lits))
    def eq(self,c,b):
        if self.mode=='python' and c==b:return
        self.clause(-c,b);self.clause(c,-b)
    def and_var(self,lits):
        if not lits:
            z=self.fresh();self.clause(z);return z
        if len(lits)==1:return lits[0]
        z=self.fresh()
        for x in lits:self.clause(-z,x)
        self.clause(z,*(-x for x in lits))
        return z
    def xor_var(self,a,b):
        c=self.fresh()
        for lits in ((-a,-b,-c),(a,b,-c),(a,-b,c),(-a,b,c)):
            self.clause(*lits)
        return c
    def phase_var(self,mono):
        z=self.fresh()
        if not mono:self.clause(z)
        else:
            lits=[self.var(x) for x in mono]
            for x in lits:self.clause(-z,x)
            self.clause(z,*(-x for x in lits))
        return z
    def compile(self):
        c=self.case
        for quarter,mono in c.phase:
            if quarter%4==0:continue
            z=self.phase_var(mono)
            self.weights[z]=QUARTER[quarter%4]
        for i,anf in enumerate(c.outputs):
            a=self.var(i)
            parts=[]
            for mono in anf:parts.append(self.and_var([self.var(x) for x in mono]))
            if not parts:
                b=self.fresh();self.clause(-b)
            else:
                b=parts[0]
                for x in parts[1:]:b=self.xor_var(b,x)
            self.eq(a,b)
        return self
    def count(self):
        n=self.next_id-1
        if n>17:raise ValueError('too many CNF variables for exhaustive audit')
        z=(0,0);sat=0
        for bits in product((False,True),repeat=n):
            if not all(any((lit>0)==bits[abs(lit)-1] for lit in clause) for clause in self.clauses):continue
            w=ONE
            for i,v in self.weights.items():
                if bits[i-1]:w=mul(w,v)
            z=add(z,w);sat+=1
        return z,sat

def direct(case):
    total=(0,0);sat=0
    for bits in product((False,True),repeat=case.n+case.m):
        if any(bits[i]!=bool(anf_eval(case.outputs[i],bits)) for i in range(case.n)):continue
        w=ONE
        for q,m in case.phase:
            if mono_eval(m,bits):w=mul(w,QUARTER[q%4])
        total=add(total,w);sat+=1
    return total,sat

def check_cases():
    rows=[]
    for case in CASES:
        oracle,ntrue=direct(case)
        out={'case':case.name,'direct':oracle,'n_direct_satisfying':ntrue,'n':case.n,'m':case.m}
        for mode in ('python','rust','rust_reserved'):
            e=Encoder(case,mode).compile()
            v,nsat=e.count()
            out[mode]={'count':v,'satisfying':nsat,'nvars':e.next_id-1,
                       'nclauses':len(e.clauses),'nweights':len(e.weights),'matches_direct':v==oracle}
            if mode!='rust':assert v==oracle,(case.name,mode,oracle,v)
        rows.append(out)
    return rows

def benchmark(rounds=1200):
    cases=(Case('identity_16',16,0,tuple(((i,),) for i in range(16))),
           Case('unused_paths_16_8',16,8,tuple(((i,),) for i in range(16))),
           Case('xor_16',16,0,tuple(((i,),((i+1)%16,)) for i in range(16))))
    output=[]
    for case in cases:
        result={'case':case.name,'rounds':rounds}
        for mode in ('python','rust','rust_reserved'):
            times=[]
            for rep in range(5):
                start=time.perf_counter_ns()
                for _ in range(rounds): Encoder(case,mode).compile()
                times.append((time.perf_counter_ns()-start)/rounds)
            enc=Encoder(case,mode).compile()
            result[mode]={'median_encoding_ns':round(statistics.median(times),1),
                          'nvars':enc.next_id-1,'nclauses':len(enc.clauses)}
        output.append(result)
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--rounds',type=int,default=1200)
    p.add_argument('--json',type=Path)
    args=p.parse_args()
    out={'model':'source-level-encoder-emulation-not-native',
         'cases':check_cases(),'microbench':benchmark(args.rounds)}
    if args.json:args.json.write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
