import os,subprocess,pathlib,json
root=pathlib.Path(os.environ['QUPRS_ATTR_ROOT']); out=root/'results/diagnostics';out.mkdir(exist_ok=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for case in ['qft16','qaoa7','ghz32','graphstate16','grover4']:
 for solver in ['gpmc','ganak']:
  for variant in ['A','B1','B3','B5','B10','B20']:
   stem=f'{case}-{solver}-{variant}'
   env=os.environ.copy();env['QUPRS_TRACE_PATH']=str(out/(stem+'.jsonl'))
   cmd=['/usr/bin/time','-v','-o',str(out/(stem+'.time.txt')),str(root/'results/bin'/('diag-'+variant)),case,solver,'0']
   r=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=600)
   (out/(stem+'.stdout')).write_text(r.stdout);(out/(stem+'.stderr')).write_text(r.stderr)
   if r.returncode:raise RuntimeError((stem,r.returncode,r.stderr))
   print(stem,flush=True)
