// Exact dyadic small-CNF oracle for the real original MPFR engine.
const assert=require('node:assert/strict'),fs=require('node:fs');const {open}=require('./harness.cjs');
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]];
function parse(stdout){const line=stdout.split('\n').find(x=>/^c s exact /.test(x));assert(line,stdout);let s=line.replace(/^c s exact (?:double prec-sci|arb cpx)\s+/,'').replaceAll(' ','').replaceAll('+-','-');if(!s.endsWith('i'))return [Number(s),0];s=s.slice(0,-1);let j=-1;for(let i=1;i<s.length;i++)if('+-'.includes(s[i])&&!/[eE]/.test(s[i-1]))j=i;assert(j>0,s);return [Number(s.slice(0,j)),Number(s.slice(j))]}
(async()=>{const h=await open();let seed=0x6512;const next=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed};const pool=[[-1,0],[-.5,.5],[0,0],[0,1],[.5,-.5],[1,0]];const results=[];
 try{for(let caseId=0;caseId<48;caseId++){
  const n=1+next()%5,clauses=[],w0=[],w1=[];for(let v=0;v<n;v++){w0.push(pool[next()%pool.length]);w1.push(pool[next()%pool.length])}
  for(let c=0;c<next()%7;c++){const clause=[];for(let k=0;k<1+next()%3;k++)clause.push((1+next()%n)*(next()%2?1:-1));clauses.push(clause)}
  let expected=[0,0];for(let bits=0;bits<1<<n;bits++){if(!clauses.every(c=>c.some(l=>Boolean(bits&(1<<(Math.abs(l)-1)))===(l>0))))continue;let z=[1,0];for(let v=0;v<n;v++)z=mul(z,bits&(1<<v)?w1[v]:w0[v]);expected=add(expected,z)}
  const lines=['c t wmc',`p cnf ${n} ${clauses.length}`];for(let v=0;v<n;v++)for(const [lit,w]of[[v+1,w1[v]],[-v-1,w0[v]]])lines.push(`c p weight ${lit} ${w[0]} ${w[1]} 0`);for(const c of clauses)lines.push(c.join(' ')+' 0');
  const result=await h.page.evaluate(({base,cnf})=>new Promise((resolve,reject)=>{const worker=new Worker(new URL('engines/runner.js',base));const timer=setTimeout(()=>{worker.terminate();reject(Error('counter oracle timeout'))},20000);worker.onerror=e=>{clearTimeout(timer);worker.terminate();reject(Error(e.message))};worker.onmessage=({data})=>{if(data.progress)return;clearTimeout(timer);worker.terminate();resolve(data)};worker.postMessage({engine:'gpmc',cnf})}),{base:h.base,cnf:lines.join('\n')+'\n'});
  assert(!result.error,result.error);assert(!result.stderr.includes('unsupported syscall'),result.stderr);const actual=parse(result.stdout);assert(Math.abs(actual[0]-expected[0])<1e-12&&Math.abs(actual[1]-expected[1])<1e-12,JSON.stringify({caseId,expected,actual}));results.push({caseId,expected,actual});
 }
 const phases=JSON.parse(fs.readFileSync(process.env.QUWEB_QA_OUT+'/phase-reference.json','utf8'));
 for(const c of phases.cases){const result=await h.page.evaluate(({base,cnf})=>new Promise((resolve,reject)=>{const w=new Worker(new URL('engines/runner.js',base));const t=setTimeout(()=>{w.terminate();reject(Error('phase timeout'))},20000);w.onerror=e=>{clearTimeout(t);w.terminate();reject(Error(e.message))};w.onmessage=({data})=>{if(data.progress)return;clearTimeout(t);w.terminate();resolve(data)};w.postMessage({engine:'gpmc',cnf})}),{base:h.base,cnf:c.cnf});assert(!result.error,result.error);c.wasm_stdout=result.stdout;}
 fs.writeFileSync(process.env.QUWEB_QA_OUT+'/phase-results.json',JSON.stringify(phases,null,2));
 fs.writeFileSync(process.env.QUWEB_QA_OUT+'/counter.json',JSON.stringify({pass:true,cases:results.length,results},null,2));}finally{await h.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
