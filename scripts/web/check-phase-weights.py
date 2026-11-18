"""Cross-check native/WASM source-phase transport against upstream MPFR C bridge."""
import ctypes,decimal,json,os,pathlib,re,subprocess,sys,tempfile
D=decimal.Decimal;decimal.getcontext().prec=110
cases=[('0','1','0','1',0,96),('1','2','0','1',0,96),('1','4','0','1',0,96),('3','4','0','1',0,96),('1','8','0','1',0,96),('0','1','1','7',1,256),('1','8','-1','7',1,1024),('0','1','1','1'+'0'*400,1,1024)]
def components(stdout):
 line=next(l for l in stdout.splitlines() if l.startswith('c s exact '))
 value=re.sub(r'^c s exact (double prec-sci|arb cpx)\s+','',line).replace(' ','').replace('+-','-')
 if not value.endswith('i'):return D(value),D(0)
 value=value[:-1];places=[i for i in range(1,len(value)) if value[i] in '+-' and value[i-1] not in 'eE'];i=places[-1];return D(value[:i]),D(value[i:])
def check(case,stdout):
 assert f'c o quprs-phase-weights 1' in stdout,stdout
 actual=components(stdout)
 for a,e in zip(actual,map(D,case['expected'])):
  assert a==e if not e else abs(a-e)<=abs(e)*D('1e-26'),(case,a,e)
def prepare(shared,counter,destination):
 lib=ctypes.CDLL(shared);fn=lib.quprs_mpfr_phase_weight
 fn.argtypes=[ctypes.c_char_p]*4+[ctypes.c_ulong,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t];fn.restype=ctypes.c_int
 out=[]
 for cn,cd,rn,rd,present,bits in cases:
  r=ctypes.create_string_buffer(512);i=ctypes.create_string_buffer(512)
  assert fn(*[v.encode() for v in [cn,cd,rn,rd]],bits,r,i,512)==0
  expected=[r.value.decode(),i.value.decode()]
  if not present and (cn,cd) in [('0','1'),('1','2'),('1','4'),('3','4')]:expected={('0','1'):['1','0'],('1','2'):['-1','0'],('1','4'):['0','1'],('3','4'):['0','-1']}[(cn,cd)]
  cnf=f'p cnf 1 1\nc t wmc\nc p weight 1 1 0 0\nc p weight -1 1 0 0\n1 0\nc p quprs-phase 1 {cn} {cd} {rn} {rd} {present} {bits}\n'
  case={'cnf':cnf,'expected':expected}
  with tempfile.TemporaryDirectory() as tmp:
   f=pathlib.Path(tmp)/'input.cnf';f.write_text(cnf)
   run=subprocess.run([counter,str(f),'-mode=1','-prec=30','-cs=64'],env={**os.environ,'TMPDIR':tmp},capture_output=True,text=True,timeout=20)
   assert run.returncode==0,run.stderr;check(case,run.stdout);case['native_stdout']=run.stdout
  out.append(case)
 pathlib.Path(destination).write_text(json.dumps({'cases':out},indent=2)+'\n')
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare(*sys.argv[2:])
 else:
  data=json.loads(pathlib.Path(sys.argv[2]).read_text())
  for case in data['cases']:check(case,case['wasm_stdout'])
  print(f'MPFR source-phase transport: {len(data["cases"])} native and WASM cases PASS (including 1e-400)')
