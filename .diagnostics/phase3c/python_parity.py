import os,pathlib,json,hashlib
from QuPRS import check_equivalence
root=pathlib.Path(os.environ['QUPRS_CASE_ROOT']); out=pathlib.Path(os.environ['QUPRS_ATTR_ROOT'])/'results/python-parity.jsonl'
cases=[('qft16','qft_nativegates_ibm_qiskit_opt0_16.qasm','proportional',True),('qaoa7','qaoa_nativegates_ibm_qiskit_opt0_7.qasm','proportional',False),('ghz32','ghz_nativegates_ibm_qiskit_opt0_32.qasm','straightforward',True),('graphstate16','graphstate_nativegates_ibm_qiskit_opt0_16.qasm','naive',False),('grover4','grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm','proportional',True)]
with out.open('w',buffering=1) as log:
 for case,file,strategy,switch in cases:
  a,b=str(root/file),str(root/'h,ry,rz,cx'/file)
  if switch:a,b=b,a
  for solver in ['gpmc','ganak']:
   r=check_equivalence(a,b,method='hybrid',strategy=strategy,tool_name=solver,timeout=600,backend='python')
   row={'case':case,'solver':solver,'status':r.equivalent,'result':str(r)};log.write(json.dumps(row)+'\n');print(row,flush=True)
   assert r.equivalent in ('equivalent','equivalent*'),row
