// D7b full source operator trace oracle: independent of QuPRS/WMC.
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
function parse(s){
  let n=0,regs=new Map(),g=[];
  for(let l of s.split("\n").map(x=>x.split("//")[0].trim()).filter(Boolean)){
    if(l==="OPENQASM 2.0;"||l==='include "qelib1.inc";')continue;
    let z=l.match(/^qreg (\w+)\[(\d+)\];$/);
    if(z){assert.ok(!regs.has(z[1]));regs.set(z[1],[n,+z[2]]);n+=+z[2];continue}
    z=l.match(/^(\w+)(?:\(([^)]+)\))?\s+(.+);$/);assert.ok(z,l);
    const [,op,theta,ops]=z;
    assert.ok(["h","x","y","z","t","tdg","rx","ry","rz","cx","ccx"].includes(op),op);
    const bits=ops.split(",").map(t=>{const q=t.trim().match(/^(\w+)\[(\d+)\]$/);assert.ok(q&&regs.has(q[1]),t);const [b,size]=regs.get(q[1]);assert.ok(+q[2]<size);return b+(+q[2])});
    assert.equal(bits.length,op==="cx"?2:op==="ccx"?3:1);assert.equal(new Set(bits).size,bits.length);
    assert.equal(Boolean(theta),["rx","ry","rz"].includes(op));
    let a=0;
    if(theta){const k=theta.match(/^(-?)(?:(\d+(?:\.\d+)?)\*)?pi(?:\/(\d+))?$/);assert.ok(k||/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(theta));a=k?(k[1]?-1:1)*+(k[2]||1)*Math.PI/+(k[3]||1):Number(theta);assert.ok(Number.isFinite(a));}
    g.push({op,bits,a,c:Math.cos(a/2),s:Math.sin(a/2)});
  }
  assert.ok(n>=1&&n<=9);return {n,g};
}
function evolve({n,g},idx){
  const N=2**n,r=new Float64Array(N),im=new Float64Array(N);r[idx]=1;
  for(let {op,bits,c,s} of g){
    if(op==="cx"||op==="ccx"){
      const mask=bits.slice(0,-1).reduce((v,x)=>v|(1<<x),0),t=1<<bits.at(-1);
      for(let j=0;j<N;j++)if((j&mask)===mask&&!(j&t)){const k=j|t,x=r[j],y=im[j];r[j]=r[k];im[j]=im[k];r[k]=x;im[k]=y}
      continue;
    }
    const bit=1<<bits[0];
    for(let base=0;base<N;base+=2*bit)for(let j=base;j<base+bit;j++){
      const k=j+bit,x=r[j],y=im[j],u=r[k],v=im[k];
      switch(op){
        case"h":r[j]=Math.SQRT1_2*(x+u);im[j]=Math.SQRT1_2*(y+v);r[k]=Math.SQRT1_2*(x-u);im[k]=Math.SQRT1_2*(y-v);break;
        case"x":r[j]=u;im[j]=v;r[k]=x;im[k]=y;break;
        case"y":r[j]=v;im[j]=-u;r[k]=-y;im[k]=x;break;
        case"z":r[k]=-u;im[k]=-v;break;
        case"t":r[k]=Math.SQRT1_2*(u-v);im[k]=Math.SQRT1_2*(u+v);break;
        case"tdg":r[k]=Math.SQRT1_2*(u+v);im[k]=Math.SQRT1_2*(v-u);break;
        case"ry":r[j]=c*x-s*u;im[j]=c*y-s*v;r[k]=s*x+c*u;im[k]=s*y+c*v;break;
        case"rx":r[j]=c*x+s*v;im[j]=c*y-s*u;r[k]=c*u+s*y;im[k]=c*v-s*x;break;
        case"rz":r[j]=c*x+s*y;im[j]=c*y-s*x;r[k]=c*u-s*v;im[k]=c*v+s*u;break;
        default:throw Error(op);
      }
    }
  }
  return [r,im];
}
function trace(a,b){
  assert.equal(a.n,b.n);const N=2**a.n;
  let re=0,im=0,norm_error=0;
  for(let k=0;k<N;k++){
    const [x,y]=[evolve(a,k),evolve(b,k)];let na=0,nb=0,dr=0,di=0;
    for(let j=0;j<N;j++){const p=x[0][j],q=x[1][j],u=y[0][j],v=y[1][j];dr+=p*u+q*v;di+=p*v-q*u;na+=p*p+q*q;nb+=u*u+v*v}
    re+=dr;im+=di;norm_error=Math.max(norm_error,Math.abs(na-1),Math.abs(nb-1));
  }
  assert.ok(norm_error<1e-9);
  return {basis_inputs:N,trace_real:re,trace_imag:im,normalized_trace_abs:Math.hypot(re,im)/N,norm_error,scope:"full Float64 source trace; no rigorous rounding certificate"};
}
const c=parse("qreg q[1];\nh q[0];\nh q[0];");
const id=parse("qreg q[1];");
assert.ok(Math.abs(trace(c,id).normalized_trace_abs-1)<1e-12);
assert.ok(trace(parse("qreg q[1];\nx q[0];"),id).normalized_trace_abs<1e-12);
assert.ok(Math.abs(trace(parse("qreg q[1];\ny q[0];\nz q[0];"),parse("qreg q[1];\nx q[0];")).normalized_trace_abs-1)<1e-12);
assert.ok(Math.abs(trace(parse("qreg q[1];\nt q[0];\ntdg q[0];"),id).normalized_trace_abs-1)<1e-12);
const m=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const rows=[];
for(const c of m.cases.filter(c=>["grover-noancilla_5_random_pauli","feynman_grover_5_eq"].includes(c.id))){
  const [a,b]=[c.left,c.right].map(x=>{assert.equal(execFileSync("git",["hash-object",x.path],{encoding:"utf8"}).trim(),x.git_blob_sha1);return parse(fs.readFileSync(x.path,"utf8"))});
  const row={case:c.id,gate_counts:[a.g.length,b.g.length],...trace(a,b)};
  rows.push(row);console.log("D7B_ORACLE",JSON.stringify(row));
}
assert.equal(rows.length,2);
fs.writeFileSync(process.argv[3],JSON.stringify({controls:4,rows},null,2)+"\n");
