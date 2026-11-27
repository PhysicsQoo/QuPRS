// Run with Node.js >=18; exact finite reference, not production HSL frontend.
const cases = [
  {
    "name": "BV/03",
    "files": {
      "pre.hsl": {
        "blob": "c5d58ba0764d33099613e49aea8a20f174be9ca0",
        "source": "Constants\nc1 := 1\nExtended Dirac\n{c1 |0000>}\n"
      },
      "post.hsl": {
        "blob": "3bcc54d9fc6bf3ca618a67808f2d3da3c3fb86b6",
        "source": "Constants\nc1 := 1\nExtended Dirac\n{c1 |1011>}\n"
      },
      "circuit.qasm": {
        "blob": "f399669db5b5e8ac469f70de179491e2008694fb",
        "source": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg qubits[4];\n\nh qubits[0];\nh qubits[1];\nh qubits[2];\nh qubits[3];\nz qubits[3];\ncx qubits[0], qubits[3];\ncx qubits[2], qubits[3];\nh qubits[0];\nh qubits[1];\nh qubits[2];\nh qubits[3];\n"
      }
    }
  },
  {
    "name": "Grover/03",
    "files": {
      "pre.hsl": {
        "blob": "9c369a362f5e504cd5d4cc64b4b5297a06661b42",
        "source": "Constants\nc1 := 1\nExtended Dirac\n{c1 |00000>}\n"
      },
      "post.hsl": {
        "blob": "5d45f38067d9e95ff0afe997c5f175cc1082e7e4",
        "source": "Constants\naH := 11 / (sqrt2 ^ 7)\naL := -1 / (sqrt2 ^ 7)\nExtended Dirac\n{aH |01001> + aL ∑ |i|=3, i≠010 |i01>}\n"
      },
      "circuit.qasm": {
        "blob": "79604029953261a0cd419b9ec932b055dd9ea0c8",
        "source": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg qubits[5];\nx qubits[4];\n\nh qubits[0];\nh qubits[1];\nh qubits[2];\nh qubits[4];\n\nx qubits[0];\nx qubits[2];\nccx qubits[0], qubits[1], qubits[3];\ncz qubits[3], qubits[2];\nccx qubits[0], qubits[1], qubits[3];\nx qubits[0];\nx qubits[2];\nh qubits[0];\nh qubits[1];\nh qubits[2];\nx qubits[0];\nx qubits[1];\nx qubits[2];\nccx qubits[0], qubits[1], qubits[3];\ncz qubits[3], qubits[2];\nccx qubits[0], qubits[1], qubits[3];\nx qubits[0];\nx qubits[1];\nx qubits[2];\nh qubits[0];\nh qubits[1];\nh qubits[2];\nx qubits[4];\n\nx qubits[0];\nx qubits[2];\nccx qubits[0], qubits[1], qubits[3];\ncz qubits[3], qubits[2];\nccx qubits[0], qubits[1], qubits[3];\nx qubits[0];\nx qubits[2];\nh qubits[0];\nh qubits[1];\nh qubits[2];\nx qubits[0];\nx qubits[1];\nx qubits[2];\nccx qubits[0], qubits[1], qubits[3];\ncz qubits[3], qubits[2];\nccx qubits[0], qubits[1], qubits[3];\nx qubits[0];\nx qubits[1];\nx qubits[2];\nh qubits[0];\nh qubits[1];\nh qubits[2];\nx qubits[4];\n\nh qubits[4];\n"
      }
    }
  }
];
const run = function run(cases) {
  // Exact real dyadic coefficients a / sqrt(2)^k; signs represented as phase 0 or pi.
  const fail=m=>{throw Error(m)}, assert=(b,m)=>{if(!b)fail(m)};
  function coeff(s,cs){s=s.trim();if(s in cs)return cs[s];if(/^[+-]?\d+$/.test(s))return [BigInt(s),0];let m=s.match(/^([+-]?\d+)\s*\/\s*(?:\(\s*sqrt2\s*\^\s*(\d+)\s*\)|sqrt2)$/);if(m)return [BigInt(m[1]),Number(m[2]||1)];fail("unsupported coefficient: "+s)}
  function parse(hsl){
    let lines=hsl.trim().split(/\r?\n/);let cs={},mode="",expr=[];
    for(let line of lines){line=line.trim();if(!line)continue;if(line==="Constants"||line==="Extended Dirac"){mode=line;continue}if(mode==="Constants"){let m=line.match(/^([A-Za-z][A-Za-z0-9]*)\s*:=\s*(.+)$/);assert(m&&!(m[1] in cs),"bad constant");cs[m[1]]=coeff(m[2],cs)}else if(mode==="Extended Dirac"){expr.push(line)}else fail("section");}
    let s=expr.join(" ");assert(s.startsWith("{")&&s.endsWith("}"),"only explicit brace set");s=s.slice(1,-1);
    // split commas only if followed by another ket term (sum clauses use commas followed by binder inequality)
    let states=s.split(/,\s*(?=(?:[A-Za-z][A-Za-z0-9]*\s+|[-+]?\d+\s+)?\|[01]+>)/);
    let k=0,n=null,templates=states.map(st=>{
      let toks=st.trim().split(/\s+([+-])\s+/),out=[];
      for(let t=0;t<toks.length;t+=2){let sign=t===0||toks[t-1]==="+"?1n:-1n,term=toks[t].trim();
        let m=term.match(/^(?:(\S+)\s+)?\|([01]+)>$/);
        if(m){let [a,kk]=coeff(m[1]||"1",cs);k=Math.max(k,kk);out.push({a:sign*a,k:kk,fixed:m[2]});n=n??m[2].length;assert(n===m[2].length,"width");continue}
        m=term.match(/^(\S+)\s+[∑Σ]\s*\|([a-z])\|=(\d+)\s*,\s*\2(?:≠|!=)([01]+)\s*\|\2([01]*)>$/);
        assert(m,"unsupported term "+term);let [a,kk]=coeff(m[1],cs),w=Number(m[3]);assert(w>0&&w<=12&&m[4].length===w,"binder width");k=Math.max(k,kk);n=n??w+m[5].length;assert(n===w+m[5].length,"width");out.push({a:sign*a,k:kk,w,exclude:m[4],suffix:m[5]});
      }return out;
    });
    // restrict same parity to avoid odd sqrt2 factor in this first real-integer prototype.
    assert(templates.every(s=>s.every(t=>(k-t.k)%2===0)),"mixed scale parity unsupported");
    return {k,n,templates:templates.map(st=>st.map(t=>({...t,a:t.a*(1n<<BigInt((k-t.k)/2))})))};
  }
  function cps(spec){let {k,n,templates}=spec;return templates.map(st=>{let a=Array(2**n).fill(0n),paths=0;for(const t of st){let targets=t.fixed?[t.fixed]:Array.from({length:2**t.w},(_,i)=>i.toString(2).padStart(t.w,"0")).filter(v=>v!==t.exclude).map(v=>v+t.suffix);let mag=t.a<0n?-t.a:t.a;assert(mag<=100000n,"multiplicity cap");for(const z of targets)for(let j=0n;j<mag;j++){a[parseInt(z,2)]+=t.a<0n?-1n:1n;paths++}}return {a,k,paths}})}
  function gates(src){let m=src.match(/qreg qubits\[(\d+)\];/);assert(m,"qreg");let n=+m[1],gs=[];for(let line of src.split(/\r?\n/)){line=line.trim();if(!line||/^OPENQASM |^include |^qreg /.test(line))continue;let a=line.match(/^(h|x|z|cx|cz|ccx) (qubits\[\d+\](?:,\s*qubits\[\d+\])*)\s*;$/);assert(a,"unsupported gate "+line);let idx=[...a[2].matchAll(/\[(\d+)\]/g)].map(x=>+x[1]);assert(idx.length===({h:1,x:1,z:1,cx:2,cz:2,ccx:3}[a[1]])&&new Set(idx).size===idx.length&&idx.every(i=>i<n),"gate args");gs.push([a[1],idx.map(i=>1<<(n-1-i))]);}return {n,gs}}
  function dense(a,k,gs){let v=a.slice(),visits=0;for(const [g,b] of gs){let w=Array(v.length).fill(0n);for(let i=0;i<v.length;i++){visits++;let m=b[0],amp=v[i];if(g==="h"){w[i&~m]+=amp;w[i|m]+=(i&m)?-amp:amp}else if(g==="z")w[i]+=(i&m)?-amp:amp;else if(g==="cz")w[i]+=(i&m)&&(i&b[1])?-amp:amp;else if(g==="x")w[i^m]+=amp;else if(g==="cx")w[i^((i&m)?b[1]:0)]+=amp;else if(g==="ccx")w[i^((i&m)&&(i&b[1])?b[2]:0)]+=amp;}v=w;if(g==="h")k++}return {a:v,k,visits}}
  function pathsum(initial,gs){let n=initial.a.length,a=Array(n).fill(0n),h=gs.filter(([g])=>g==="h").length,leaves=0;function go(i,s,j){if(j===gs.length){a[i]+=s;leaves++;return}let [g,b]=gs[j],m=b[0];if(g==="h"){go(i&~m,s,j+1);go(i|m,(i&m)?-s:s,j+1);return}if(g==="z")s=(i&m)?-s:s;else if(g==="cz")s=(i&m)&&(i&b[1])?-s:s;else if(g==="x")i^=m;else if(g==="cx"&&(i&m))i^=b[1];else if(g==="ccx"&&(i&m)&&(i&b[1]))i^=b[2];go(i,s,j+1)}
    // Each input integer coefficient is a multiplicity, not arbitrary amplitude function.
    initial.a.forEach((w,i)=>{for(let t=0n;t<(w<0n?-w:w);t++)go(i,w<0n?-1n:1n,0)});return {a,k:initial.k+h,leaves}}
  const nonzero=a=>a.some(v=>v!==0n);
  function ray(a,b){if(!nonzero(a)||!nonzero(b))return false;let i=a.findIndex(v=>v!==0n);return b[i]!==0n&&a.every((v,j)=>v*b[i]===b[j]*a[i])}
  const norm=(v,k)=>v.reduce((s,x)=>s+x*x,0n)===(1n<<BigInt(k));
  const controls=[];
  const check=(name,cond)=>{assert(cond,name);controls.push(name)};
  const bell=cps(parse("Constants\nc := 1 / sqrt2\nExtended Dirac\n{c |00> + c |11>, c |00> - c |11>, c |01> + c |10>, c |01> - c |10>}"));
  check("bell-four-exact",bell.length===4&&bell.every((v,x)=>v.k===1&&v.a.every((w,z)=>w===BigInt(z===(x>>1)?1:z===(3^(x>>1))?(x&1?-1:1):0))));
  check("coherent-cancellation",!nonzero(cps(parse("Extended Dirac\n{|0> - |0>}"))[0].a));
  check("zero-not-ray",!ray([0n,0n],[1n,0n]));
  check("support-not-ray",!ray([1n,1n],[1n,-1n]));
  check("nonzero-scale",ray([1n,-2n],[-3n,6n]));
  for(const [name,s] of [["symbolic-reject","Extended Dirac\n{a |0>}"],["width-reject","Extended Dirac\n{|0> + |11>}"],["unsupported-union","Extended Dirac\n{|0>} ∪ {|1>}"],["odd-parity-reject","Constants\nc := 1 / sqrt2\nExtended Dirac\n{|0> + c |1>}"]]){let rejected=false;try{parse(s)}catch{rejected=true}check(name,rejected)}
  const results=[];
  for(const c of cases){let pre=cps(parse(c.files["pre.hsl"].source)),post=cps(parse(c.files["post.hsl"].source)),q=gates(c.files["circuit.qasm"].source);assert(pre.length===1&&post.length===1&&pre[0].a.length===2**q.n&&post[0].a.length===2**q.n,"case shape");let p=pre[0],b=post[0],d=dense(p.a,p.k,q.gs),s=pathsum(p,q.gs);
    let manual=Array(2**q.n).fill(0n);if(c.name==="BV/03")manual[parseInt("1011",2)]=1n;else for(let i=0;i<8;i++)manual[i*4+1]=i===2?11n:-1n;
    assert(b.a.every((v,i)=>v===manual[i]),"independent post fixture");assert(norm(p.a,p.k)&&norm(b.a,b.k),"normalization");
    assert(d.k===s.k&&d.a.every((v,i)=>v===s.a[i]),"dense vs paths");assert(norm(d.a,d.k),"unitary norm");
    let good=ray(s.a,b.a);let mutant=b.a.slice();let nz=mutant.findIndex(v=>v!==0n);if(mutant.filter(v=>v!==0n).length>1)mutant[nz]*=-1n;else{mutant[nz]=0n;mutant[nz^1]=1n}let bad=ray(s.a,mutant);
    assert(good&&!bad,"positive or negative");results.push({name:c.name,qubits:q.n,gates:q.gs.length,hadamards:q.gs.filter(([g])=>g==="h").length,preScale:p.k,postScale:b.k,outputScale:s.k,prePaths:p.paths,postPaths:b.paths,circuitPaths:s.leaves,denseVisits:d.visits,exactAmplitudeChecks:s.a.length,positive:"PROVED_REFERENCE",mutant:"REFUTED_REFERENCE",output:s.a.map(String),post:b.a.map(String)})}
  // LSTA independent run enumeration vs root-choice tuple for 2-level tiny masks:
  // full run enumerates root and both leaf transitions, intersects leaf tags;
  // direct lookup chooses tag bit at each layer, rejects missing child.
  let lstaCases=0,lstaAssignments=0,lstaMismatch=0,lstaDistinct=0;
  for(let mask0=0;mask0<4;mask0++)for(let mask1=0;mask1<4;mask1++){
    // state 0 leaf value +1 on mask0, -1 on complement; state 1 leaf value +2 on mask1 (missing otherwise).
    const tr0=[{mask:mask0,v:1},{mask:3^mask0,v:-1}].filter(t=>t.mask),tr1=[{mask:mask1,v:2}].filter(t=>t.mask);
    const ref=new Set();for(const a of tr0)for(const b of tr1)if(a.mask&b.mask)ref.add(`${a.v},${b.v}`);
    const cand=new Set();for(let c=0;c<2;c++){lstaAssignments++;let a=tr0.find(t=>t.mask&(1<<c)),b=tr1.find(t=>t.mask&(1<<c));if(a&&b)cand.add(`${a.v},${b.v}`)}lstaCases++;lstaDistinct+=ref.size;if(ref.size!==cand.size||[...ref].some(t=>!cand.has(t)))lstaMismatch++;
  }
  assert(lstaMismatch===0,"LSTA oracle mismatch");
  return {scope:"bounded real dyadic, explicit sets and one restricted sum; fixed unitary gates; no AutoQ binary/native RR/WMC; reference only",controls,results,lsta:{cases:lstaCases,choiceAssignments:lstaAssignments,distinctAcceptedVectors:lstaDistinct,mismatch:lstaMismatch}}
};
console.log(JSON.stringify(run(cases),null,2));
