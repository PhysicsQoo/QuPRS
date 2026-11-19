// Independent tiny-matrix oracle for source-controlled browser examples.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const add=([a,b],[c,d])=>[a+c,b+d],mul=([a,b],[c,d])=>[a*c-b*d,a*d+b*c];
const abs=([a,b])=>Math.hypot(a,b),conj=([a,b])=>[a,-b];
const z=[0,0],neg=[-1,0],h=1/Math.sqrt(2);
const exponent=angle=>[Math.cos(angle),Math.sin(angle)];
const phaseAngle=s=>s==='pi/2'?Math.PI/2:Number(s);
function parse(qasm){
 const statements=qasm.split(';').map(x=>x.trim()).filter(Boolean),ops=[];
 const reg=statements.find(x=>x.startsWith('qreg '));
 assert(reg,'Missing qreg');const n=Number(reg.match(/^qreg q\[(\d+)\]$/)?.[1]);
 assert(Number.isInteger(n)&&n>=1&&n<=3,'Oracle supports at most 3 qubits');
 for(const line of statements){
  if(line.startsWith('OPENQASM ')||line.startsWith('include ')||line.startsWith('qreg '))continue;
  const m=line.match(/^(h|x|z|s|t|tdg|cx|cz|u1|rz)(?:\(([^)]+)\))?\s+q\[(\d+)\](?:,\s*q\[(\d+)\])?$/);
  assert(m,'Unsupported example syntax '+line);
  const a=Number(m[3]),b=m[4]===undefined?null:Number(m[4]);
  assert(a<n&&(b===null||b<n&&b!==a),'Out-of-range/wrong operand');
  ops.push({gate:m[1],angle:m[2],a,b});
 }
 return {n,ops};
}
function matrixFor(qasm){
 const {n,ops}=parse(qasm),d=2**n,cols=[];
 for(let input=0;input<d;input++){
  let state=Array.from({length:d},(_,i)=>i===input?[1,0]:[0,0]);
  for(const {gate,angle,a,b} of ops){
   const abit=1<<a,bbit=b===null?0:1<<b;
   if(gate==='cx'||gate==='cz'){
    const next=state.map(c=>c.slice());
    for(let i=0;i<d;i++)if(i&abit){
     if(gate==='cz'&&(i&bbit))next[i]=mul(neg,state[i]);
     if(gate==='cx')next[i]=state[i^bbit];
    }
    state=next;continue;
   }
   const phase=gate==='u1'||gate==='rz'?phaseAngle(angle):null;
   assert(phase===null||Number.isFinite(phase),'Invalid gate angle');
   const gates={
    h:[[h,0],[h,0],[h,0],[-h,0]],
    x:[[0,0],[1,0],[1,0],[0,0]],
    z:[[1,0],[0,0],[0,0],[-1,0]],
    s:[[1,0],[0,0],[0,0],[0,1]],
    t:[[1,0],[0,0],[0,0],exponent(Math.PI/4)],
    tdg:[[1,0],[0,0],[0,0],exponent(-Math.PI/4)],
    u1:[[1,0],[0,0],[0,0],exponent(phase||0)],
    rz:[exponent(-(phase||0)/2),[0,0],[0,0],exponent((phase||0)/2)]
   };
   const m=gates[gate];assert(m,'Unsupported gate '+gate);
   for(let i=0;i<d;i++)if(!(i&abit)){
    const j=i|abit,x=state[i],y=state[j];
    state[i]=add(mul(m[0],x),mul(m[1],y));
    state[j]=add(mul(m[2],x),mul(m[3],y));
   }
  }
  cols.push(state);
 }
 return {n,cols};
}
function classify(a,b){
 const u=matrixFor(a),v=matrixFor(b);assert.equal(u.n,v.n,'Mismatched registers');
 const d=2**u.n,entries=[],other=[];
 for(let c=0;c<d;c++)for(let r=0;r<d;r++){entries.push(u.cols[c][r]);other.push(v.cols[c][r]);}
 const direct=Math.max(...entries.map((x,i)=>abs(add(x,mul(neg,other[i])))));
 const first=entries.findIndex(x=>abs(x)>1e-9);assert(first>=0);
 const numerator=mul(other[first],conj(entries[first]));
 const scale=abs(entries[first])**2;
 const factor=[numerator[0]/scale,numerator[1]/scale];
 const projective=Math.max(...entries.map((x,i)=>abs(add(mul(factor,x),mul(neg,other[i])))));
 let trace=z;
 for(let i=0;i<entries.length;i++)trace=add(trace,mul(conj(entries[i]),other[i]));
 const distance=Math.sqrt(Math.max(0,1-(abs(trace)/d)**2));
 return {direct,projective,distance};
}
async function readCatalog(){
 const code=fs.readFileSync(path.resolve(__dirname,'../examples.js'),'utf8');
 return (await import('data:text/javascript,'+encodeURIComponent(code))).EXAMPLES;
}
async function checkCatalog(){
 const pre='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n';
 const rotated=classify(pre+'h q[0];\nrz(pi/2) q[0];\nh q[0];',
                       pre+'h q[0];\nu1(pi/2) q[0];\nh q[0];');
 assert(rotated.projective<1e-9&&rotated.direct>1e-5,
   'Projective comparison must normalize a subunit reference amplitude');
 const list=await readCatalog();assert(list.length>=12,'At least twelve examples');
 assert.equal(new Set(list.map(x=>x.id)).size,list.length,'Stable unique IDs');
 const kinds=new Set(),source=[];
 for(const ex of list){
  assert(ex.title&&ex.description&&ex.category,'Complete example metadata');
  assert(ex.mode==='hybrid'||ex.mode==='wmc','Supported mode');
  const result=classify(ex.circuit1,ex.circuit2);
  assert.equal(matrixFor(ex.circuit1).n,ex.qubits);
  if(ex.expected==='equivalent')assert(result.direct<1e-9,ex.id+' not exactly equivalent');
  else if(ex.expected==='phase_equivalent')assert(result.projective<1e-9&&result.direct>1e-5,ex.id+' not globally phased');
  else if(ex.expected==='different')assert(result.distance>ex.distance_tolerance*1.01,ex.id+' not meaningfully distinct');
  else throw Error(ex.id+' has unrecognized expectation');
  kinds.add(ex.category);source.push({id:ex.id,category:ex.category,expected:ex.expected,projective_distance:result.distance});
 }
 for(const id of ['identity','phase','cz'])assert(list.some(x=>x.id===id),'Existing fixture missing');
 for(const kind of ['equivalent','decomposition','global_phase','different','tolerance'])assert(kinds.has(kind),'Category missing '+kind);
 return {examples:list,evidence:source};
}
module.exports={checkCatalog};
if(require.main===module)checkCatalog().then(x=>console.log(JSON.stringify({pass:true,count:x.examples.length,evidence:x.evidence}))).catch(e=>{console.error(e);process.exitCode=1});
