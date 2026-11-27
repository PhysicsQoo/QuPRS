// Independent source QASM witness. No QuPRS/Qiskit or WMC code.
// Strict supported subset of original MQT gate language, Float64 only.
import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";
import {execFileSync} from "node:child_process";
const sha = x=>crypto.createHash("sha256").update(x).digest("hex");
function parse(s){
  let n=0,g=[];
  for(const l of s.split("\n").map(x=>x.trim()).filter(Boolean)){
    if(l==="OPENQASM 2.0;"||l==='include "qelib1.inc";')continue;
    let z=l.match(/^qreg q\[(\d+)\];$/);
    if(z){assert.equal(n,0);n=+z[1];continue}
    z=l.match(/^cx q\[(\d+)\],\s*q\[(\d+)\];$/);
    if(z){g.push(["cx",+z[1],+z[2]]);continue}
    z=l.match(/^h q\[(\d+)\];$/);
    if(z){g.push(["h",+z[1],0]);continue}
    z=l.match(/^r([xyz])\(([^)]+)\) q\[(\d+)\];$/);
    assert.ok(z,"unsupported source instruction: "+l);
    const a=z[2],k=a.match(/^(-?)(?:(\d+)\*)?pi(?:\/(\d+))?$/);
    assert.ok(k||/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(a));
    const theta=k?(k[1]?-1:1)*(+(k[2]||1))*Math.PI/(+(k[3]||1)):Number(a);
    assert.ok(Number.isFinite(theta));g.push(["r"+z[1],+z[3],theta]);
  }
  assert.ok(n>=1&&n<=16&&g.every(([op,q,t])=>q>=0&&q<n&&(op!=="cx"||t>=0&&t<n&&t!==q)));
  return {n,g};
}
function evolve({n,g},idx){
  const N=2**n,r=new Float64Array(N),im=new Float64Array(N);
  assert.ok(idx>=0&&idx<N);r[idx]=1;
  for(const [op,q,a] of g){
    const bit=1<<q;
    if(op==="cx"){
      const t=1<<a;
      for(let j=0;j<N;j++)if((j&bit)&&!(j&t)){
        const k=j|t,x=r[j],y=im[j];r[j]=r[k];im[j]=im[k];r[k]=x;im[k]=y;
      }
      continue;
    }
    const c=op==="h"?Math.SQRT1_2:Math.cos(a/2),s=op==="h"?Math.SQRT1_2:Math.sin(a/2);
    for(let base=0;base<N;base+=2*bit)for(let j=base;j<base+bit;j++){
      const k=j+bit,x=r[j],y=im[j],u=r[k],v=im[k];
      if(op==="h"){r[j]=c*(x+u);im[j]=c*(y+v);r[k]=c*(x-u);im[k]=c*(y-v)}
      else if(op==="ry"){r[j]=c*x-s*u;im[j]=c*y-s*v;r[k]=s*x+c*u;im[k]=s*y+c*v}
      else if(op==="rx"){r[j]=c*x+s*v;im[j]=c*y-s*u;r[k]=c*u+s*y;im[k]=c*v-s*x}
      else if(op==="rz"){r[j]=c*x+s*y;im[j]=c*y-s*x;r[k]=c*u-s*v;im[k]=c*v+s*u}
      else throw Error(op);
    }
  }
  return [r,im];
}
function overlap(a,b,idx){
  const [x,y]=[evolve(a,idx),evolve(b,idx)];
  let re=0,im=0,na=0,nb=0;
  for(let j=0;j<x[0].length;j++){
    const p=x[0][j],q=x[1][j],u=y[0][j],v=y[1][j];
    re+=p*u+q*v;im+=p*v-q*u;na+=p*p+q*q;nb+=u*u+v*v;
  }
  assert.ok(Math.abs(na-1)<1e-9&&Math.abs(nb-1)<1e-9);
  const abs_overlap=Math.hypot(re,im)/Math.sqrt(na*nb);
  return {idx,re,im,na,nb,abs_overlap,trace_gap_lower_estimate:(1-abs_overlap)/2**a.n};
}
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-12);
const one={n:1,g:[]};
near(overlap(one,{n:1,g:[["h",0,0],["h",0,0]]},0).abs_overlap,1);
near(overlap(one,{n:1,g:[["rx",0,Math.PI]]},0).abs_overlap,0);
near(overlap(one,{n:1,g:[["ry",0,Math.PI]]},0).abs_overlap,0);
near(overlap(one,{n:1,g:[["rz",0,Math.PI]]},0).abs_overlap,1);
near(overlap({n:2,g:[]},{n:2,g:[["cx",0,1]]},1).abs_overlap,0);
const manifest=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const selected=manifest.cases.filter(c=>["wstate_16_neq","vqe_16_neq"].includes(c.id));
assert.equal(selected.length,2);
const reports=[];
for(const c of selected){
  const circuits=[c.left,c.right].map(x=>{
    const b=fs.readFileSync(x.path);
    assert.equal(sha(b),x.sha256);
    assert.equal(execFileSync("git",["hash-object",x.path],{encoding:"utf8"}).trim(),x.git_blob_sha1);
    return parse(b.toString("utf8"));
  });
  assert.ok(circuits.every(x=>x.n===16));
  const samples=[0,21845,65535].map(i=>overlap(...circuits,i));
  assert.ok(samples.every(x=>x.trace_gap_lower_estimate>1e-8),"weak NEQ witness");
  const row={case:c.id,gate_counts:circuits.map(x=>x.g.length),source_sha256:[c.left.sha256,c.right.sha256],samples,scope:"Float64 source witness, analytic trace-gap inequality evaluated numerically; not rigorous rounding certificate"};
  reports.push(row);console.log("D6C_WITNESS",JSON.stringify(row));
}
fs.writeFileSync(process.argv[3],JSON.stringify({node:process.version,controls:5,rows:reports},null,2)+"\n");
