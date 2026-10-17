#!/usr/bin/env python3
"""Serial same-host interleaved attribution. Probe warmup/build are excluded.
Binary directory contains A, B1, B3, B5, B10, B20 executables.
"""
import argparse, hashlib, json, os, pathlib, platform, statistics, subprocess, time


def stats(xs):
    m = statistics.median(xs)
    return {'n': len(xs), 'median': m, 'mad': statistics.median(abs(x-m) for x in xs), 'raw': xs}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def command(*a):
    try:
        return subprocess.run(a, text=True, capture_output=True, check=False).stdout.strip()
    except OSError as e:
        return str(e)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--binary-dir', required=True, type=pathlib.Path)
    p.add_argument('--output', required=True, type=pathlib.Path)
    p.add_argument('--case-root', required=True, type=pathlib.Path)
    p.add_argument('--blocks', type=int, default=5)
    p.add_argument('--cases', nargs='+', default=['qft16','qaoa7','ghz32','graphstate16','grover4'])
    p.add_argument('--solvers', nargs='+', default=['gpmc','ganak'])
    p.add_argument('--intervals', nargs='+', type=int, default=[1,3,5,10,20])
    p.add_argument('--warmups', type=int, default=1)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--cpu', type=int)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else []
    cpu = args.cpu if args.cpu is not None else (allowed[0] if allowed else None)
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    env = os.environ.copy()
    env.update(QUPRS_CASE_ROOT=str(args.case_root.resolve()), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env.pop('QUPRS_TRACE_PATH', None)
    variants = ['A'] + ['B'+str(n) for n in args.intervals]
    binaries = {v: (args.binary_dir / v).resolve() for v in variants}
    manifest = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), 'platform':platform.platform(), 'python':platform.python_version(), 'uname':command('uname','-a'), 'lscpu':command('lscpu'), 'rustc':command('rustc','-Vv'), 'cargo':command('cargo','-V'), 'cpu_affinity_original':allowed, 'cpu_affinity_measurement':[cpu], 'flags': {k:env.get(k) for k in ('RUSTFLAGS','CARGO_PROFILE_RELEASE_DEBUG','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}, 'binaries': {v:{'path':str(x),'sha256':sha(x)} for v,x in binaries.items()}, 'solvers':{}, 'method':'hybrid', 'blocks':args.blocks, 'warmups_per_process':args.warmups, 'rss_note':'Process VmHWM after best-effort reset; excludes solver child process RSS.', 'encoding_note':'wmc_encoding_and_management_seconds = wmc minus DIMACS serialization minus solver; includes manager setup and normalization.'}
    for s in args.solvers:
        key='QUPRS_'+s.upper()+'_PATH'
        f=env.get(key)
        manifest['solvers'][s]={'path':f,'sha256':sha(f) if f else None}
        if not f:
            raise RuntimeError(key+' must be explicit; no implicit solver selection permitted')
    manifest['qasm_sha256']={str(x.relative_to(args.case_root)):sha(x) for x in args.case_root.rglob('*.qasm')}
    (args.output/'environment.json').write_text(json.dumps(manifest,indent=2)+'\n')
    results=[]
    with (args.output/'samples.jsonl').open('w', buffering=1) as raw, (args.output/'stderr.log').open('w', buffering=1) as logs:
        for case in args.cases:
            for solver in args.solvers:
                for interval in args.intervals:
                    b='B'+str(interval)
                    for block in range(args.blocks):
                        order=['A',b,b,'A'] if block%2==0 else [b,'A','A',b]
                        for position,variant in enumerate(order):
                            cmd=[str(binaries[variant]),case,solver,str(args.warmups)]
                            meta={'case':case,'solver':solver,'interval':interval,'block':block,'position':position,'order':'ABBA' if block%2==0 else 'BAAB','variant':variant,'command':cmd,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'loadavg':os.getloadavg()}
                            run=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=args.timeout)
                            logs.write(json.dumps(meta)+'\n'+run.stderr+'\n')
                            try:
                                row=json.loads(run.stdout.strip().splitlines()[-1])
                            except (ValueError,IndexError):
                                raw.write(json.dumps({**meta,'returncode':run.returncode,'stdout':run.stdout,'error':'invalid probe output'})+'\n')
                                raise RuntimeError('invalid probe output '+str(meta))
                            record={**meta,**row,'returncode':run.returncode}
                            raw.write(json.dumps(record)+'\n');results.append(record)
                            if run.returncode or row['status'] not in ('equivalent','equivalent*'):
                                raise RuntimeError('verification failure; stopping '+str(record))
                        print(f'{case} {solver} interval={interval} block={block+1}/{args.blocks}',flush=True)
    summary=[]
    fields=['strategy_seconds','engine_total_seconds','outer_seconds','dimacs_seconds','solver_seconds','wmc_seconds','wmc_encoding_and_management_seconds','process_peak_rss_kib']
    for case in args.cases:
        for solver in args.solvers:
            for interval in args.intervals:
                rows=[r for r in results if r['case']==case and r['solver']==solver and r['interval']==interval]
                b='B'+str(interval)
                item={'case':case,'solver':solver,'interval':interval,'status_consistent':len({r['status'] for r in rows})==1,'metrics':{},'paired_block_ratios':{}}
                for field in fields:
                    aa=[r[field] for r in rows if r['variant']=='A' and r[field] is not None]
                    bb=[r[field] for r in rows if r['variant']==b and r[field] is not None]
                    item['metrics'][field]={'A':stats(aa) if aa else None,'B':stats(bb) if bb else None}
                    ratios=[]
                    for block in range(args.blocks):
                        av=[r[field] for r in rows if r['variant']=='A' and r['block']==block and r[field] is not None]
                        bv=[r[field] for r in rows if r['variant']==b and r['block']==block and r[field] is not None]
                        if av and bv and statistics.median(av)>0: ratios.append(statistics.median(bv)/statistics.median(av))
                    item['paired_block_ratios'][field]=stats(ratios) if ratios else None
                summary.append(item)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    md=['| Case | Solver | Interval | A total median ± MAD (s) | B total median ± MAD (s) | Paired B/A median ± MAD |','|---|---|---:|---:|---:|---:|']
    for r in summary:
        a=r['metrics']['engine_total_seconds']['A'];b=r['metrics']['engine_total_seconds']['B'];ratio=r['paired_block_ratios']['engine_total_seconds']
        md.append(f"| {r['case']} | {r['solver']} | {r['interval']} | {a['median']:.6f} ± {a['mad']:.6f} | {b['median']:.6f} ± {b['mad']:.6f} | {ratio['median']:.4f} ± {ratio['mad']:.4f} |")
    (args.output/'summary.md').write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
