#!/usr/bin/env python3
"""Independent phase-to-complex-weight precision/serialization experiment.

Read lexical QASM angles without passing through binary64. Compare Rust-style
binary64 cos/sin with 17-digit decimal serialization against high-precision
trigonometry. This is a source-angle PROXY, not PathSum phase-term capture;
timings are Python/maths emulations, not native Rust or GPMC walltime.
"""
from __future__ import annotations
import argparse, ast, json, math, statistics, time, re
from pathlib import Path
import mpmath as mp

GATE=re.compile(r'^\s*(?:rx|ry|rz|p|u1)\(([^)]+)\)')
SAMPLES=("0.000000025","0.00010","0.00020","pi/2","pi/4","pi/8","pi/256",
         "-pi/2","-3*pi/4","2.0330832984526417","1.1085093551371514",
         "2.8600220891857973","3.141592653589793","0.7415468052361485",
         "-1.57089220059414")

def eval_exact_decimal(expr:str):
    node=ast.parse(expr,mode='eval').body
    def visit(z):
        if isinstance(z,ast.BinOp) and isinstance(z.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=visit(z.left),visit(z.right)
            return (a+b if isinstance(z.op,ast.Add) else a-b if isinstance(z.op,ast.Sub)
                    else a*b if isinstance(z.op,ast.Mult) else a/b)
        if isinstance(z,ast.UnaryOp) and isinstance(z.op,(ast.UAdd,ast.USub)):
            v=visit(z.operand);return -v if isinstance(z.op,ast.USub) else v
        if isinstance(z,ast.Name) and z.id=='pi':return mp.pi
        if isinstance(z,ast.Constant) and isinstance(z.value,(int,float)) and not isinstance(z.value,bool):
            segment=ast.get_source_segment(expr,z)
            return mp.mpf(segment)
        raise ValueError(f'Invalid phase formula {expr!r}')
    return visit(node)

def source_angles(paths):
    tokens=[]
    for path in paths:
        for line in path.read_text().splitlines():
            match=GATE.match(line)
            if match:tokens.append(match.group(1).strip())
    return tokens

def single(angle,prec=90):
    with mp.workdps(prec):
        exact=eval_exact_decimal(angle)
        ideal=(mp.cos(exact),mp.sin(exact))
        low=float(exact)
        lossy=(math.cos(low),math.sin(low))
        printed=(mp.mpf(format(lossy[0],'.16e')),mp.mpf(format(lossy[1],'.16e')))
        with mp.workdps(35):hi=(mp.cos(exact),mp.sin(exact))
        hi=tuple(mp.mpf(mp.nstr(v,34)) for v in hi)
        f64_error=mp.sqrt(sum((p-v)**2 for p,v in zip(printed,ideal)))
        hp_error=mp.sqrt(sum((p-v)**2 for p,v in zip(hi,ideal)))
        f64_drift=sum(v*v for v in printed)-1
        hp_drift=sum(v*v for v in hi)-1
        return {'angle':angle,'f64_abs_weight_error':mp.nstr(f64_error,18),
                'hp34_abs_weight_error':mp.nstr(hp_error,18),
                'f64_unit_drift':mp.nstr(f64_drift,18),
                'hp34_unit_drift':mp.nstr(hp_drift,18),
                'f64_print_real':format(lossy[0],'.16e'),
                'f64_print_imag':format(lossy[1],'.16e')}

def benchmarks(tokens,rounds):
    samples=tokens[:min(100,len(tokens))]
    if not samples:return {}
    times={}
    for mode in ('binary64','mp_35dps','mp_90dps'):
        runs=[]
        for rep in range(5):
            start=time.perf_counter_ns()
            for _ in range(rounds):
                for s in samples:
                    if mode=='binary64':
                        x=float(eval_exact_decimal(s));math.cos(x);math.sin(x)
                    else:
                        with mp.workdps(35 if mode=='mp_35dps' else 90):
                            x=eval_exact_decimal(s);mp.cos(x);mp.sin(x)
            runs.append((time.perf_counter_ns()-start)/(len(samples)*rounds))
        times[mode]=round(statistics.median(runs),1)
    return times

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('qasm',nargs='*',type=Path)
    a.add_argument('--json',type=Path)
    a.add_argument('--rounds',type=int,default=50)
    args=a.parse_args()
    source=source_angles(args.qasm) if args.qasm else list(SAMPLES)
    tokens=list(dict.fromkeys(source))
    results=[single(s) for s in tokens]
    risks=sorted(results,key=lambda x:abs(mp.mpf(x['f64_unit_drift'])),reverse=True)
    summary={'source':'qasm-angle-proxy-not-the-encoded-pathsum-phase'
                        if args.qasm else 'representative-angle-samples',
             'qasm_files':[str(p) for p in args.qasm],
             'n_tokens':len(source),'n_distinct_angles':len(tokens),
             'max_f64_abs_weight_error':max((x['f64_abs_weight_error'] for x in results),
                                          key=lambda x:mp.mpf(x),default=None),
             'max_hp34_abs_weight_error':max((x['hp34_abs_weight_error'] for x in results),
                                           key=lambda x:mp.mpf(x),default=None),
             'max_f64_unit_drift':max((x['f64_unit_drift'] for x in results),
                                    key=lambda x:abs(mp.mpf(x)),default=None),
             'n_f64_unit_overshoots':sum(mp.mpf(x['f64_unit_drift'])>0 for x in results),
             'most_drifted':risks[:12],
             'timing_ns_per_phase_weight':benchmarks(tokens,args.rounds)}
    if args.json:args.json.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
