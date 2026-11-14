#!/usr/bin/env python3
"""Reject missing memory ceilings and unresolved side-module dependencies."""
import json,pathlib,sys
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def u(self):
  n=shift=0
  while True:
   c=self.b[self.p];self.p+=1;n|=(c&127)<<shift
   if c<128:return n
   shift+=7
 def s(self):
  n=self.u();v=self.b[self.p:self.p+n];self.p+=n;return v.decode()
results=[]
for arg in sys.argv[1:]:
 p=pathlib.Path(arg);r=Reader(p.read_bytes());assert r.b[:8]==b'\0asm\1\0\0\0';r.p=8;mem=[];needed=[]
 while r.p<len(r.b):
  section=r.b[r.p];r.p+=1;n=r.u();end=r.p+n;t=Reader(r.b[r.p:end]);r.p=end
  if section==5:
   for _ in range(t.u()):
    flags=t.u();minimum=t.u();maximum=t.u() if flags&1 else None
    assert maximum is not None and maximum<=8192,(str(p),minimum,maximum)
    mem.append({'minimum_pages':minimum,'maximum_pages':maximum})
  elif section==0:
   name=t.s()
   if name=='dylink.0':
    while t.p<len(t.b):
     k=t.u();size=t.u();finish=t.p+size
     if k==2:
      needed.extend(t.s() for _ in range(t.u()))
     t.p=finish
 assert len(mem)==1,(str(p),'Expected one internally bounded memory',mem)
 assert not needed,(str(p),'Missing static dependencies',needed)
 results.append({'file':str(p),'memory':mem,'needed_dynamic_libraries':needed})
print(json.dumps(results,indent=2))
