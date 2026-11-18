const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');const {open}=require('./harness.cjs');
const out=process.env.QUWEB_QA_OUT||'web/test-results';fs.mkdirSync(out,{recursive:true});
const q=(g,n=1)=>`OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[${n}];\n${g.replaceAll(';',';\n')}`;
const requests=[
 ['HH',q('h q[0]; h q[0];'),q('')],
 ['T',q('t q[0];'),q('')],
 ['near_phase',q('u1(0.000001) q[0];'),q('')],
 ['RZ/P global phase',q('rz(pi/2) q[0];'),q('p(pi/2) q[0];')],
 ['CX/CZ unequal',q('cx q[0],q[1];',2),q('cz q[0],q[1];',2)],
 ['CZ decomposition',q('cz q[0],q[1];',2),q('h q[1];cx q[0],q[1];h q[1];',2)],
];
function native(request){
 const r=spawnSync('prlimit',['--as=4294967296','--stack=16777216',process.env.QUWEB_NATIVE_CHECK,process.env.QUWEB_NATIVE_GPMC],{input:JSON.stringify(request),encoding:'utf8',timeout:30000,maxBuffer:8000000,env:{...process.env,OMP_NUM_THREADS:'1',OPENBLAS_NUM_THREADS:'1'}});
 assert.equal(r.status,0,r.stderr||r.stdout);const v=JSON.parse(r.stdout);assert(!v.error,v.error);return v;
}
(async()=>{
 const h=await open();const results=[];let calls=0;
 try{
  const errors=[];h.page.on('pageerror',e=>errors.push(String(e)));
  for(const [id,a,b] of requests)for(const mode of ['hybrid','wmc'])for(const strategy of ['difference','proportional']){
   const request={circuit1:a,circuit2:b,mode,strategy,distance_tolerance:1e-8,rr_tolerance:1e-10};
   const n=native(request),w=await h.run(request);assert(!w.error,`${id}: ${w.error}`);
   const context=`${id}/${mode}/${strategy}`;
   for(const key of ['status','qubits','gates1','gates2','method','strategy',
      'rr_approximate','solver_invoked','numerical_verdict','distance_kind',
      'distance_metric','certified_distance_interval']) {
     assert.deepEqual(w.report[key],n.report[key],`${context}: ${key} native/WASM mismatch`);
   }
   assert.equal(w.report.certified_distance_interval,false);
   assert.equal(w.report.distance_metric,'projective_hilbert_schmidt');
   for(const report of [n.report,w.report])for(const key of ['core_seconds','pathsum_seconds','counter_seconds']){
     const value=report[key];assert(Number.isFinite(value)&&value>=0,`${context}: invalid ${key}=${value}`);
   }
   assert(Number.isFinite(w.request_ms)&&w.request_ms>=0,`${context}: invalid elapsed time`);
   assert(w.report.core_seconds<=w.request_ms/1000+1,`${context}: WASM core time exceeds observed request wall time`);
   if(w.report.solver_invoked)calls++;
   const wd=w.report.distance_estimate,nd=n.report.distance_estimate;
   if(wd!==null && nd!==null)assert(Math.abs(wd-nd)<=1e-8,`${id} distance mismatch ${wd}/${nd}`);
   if(id==='near_phase'&&mode==='wmc')assert(wd>4.9e-7&&wd<5.1e-7,`Incorrect near-phase distance ${wd}`);
   if(id==='T'&&mode==='wmc')assert(Math.abs(wd-Math.sin(Math.PI/8))<1e-8,`Projective distance must match native threshold metric: ${wd}`);
   results.push({id,mode,strategy,native:n,wasm:w});
  }
  assert(calls>=8,'Actual MPFR weighted counting was not exercised');
  // Exercise both sides of a genuine WMC distance-tolerance boundary.
  const thresholdOutcomes=[];
  for(const epsilon of [0.37,0.40]){
   const request={circuit1:q('t q[0];'),circuit2:q(''),mode:'wmc',strategy:'difference',
     distance_tolerance:epsilon,rr_tolerance:1e-10};
   const n=native(request),w=await h.run(request);
   assert(!w.error,w.error);
   assert.equal(w.report.status,n.report.status,`native/WASM tolerance ${epsilon}`);
   assert(Math.abs(w.report.distance_estimate-Math.sin(Math.PI/8))<1e-8);
   thresholdOutcomes.push(w.report.status);
  }
  assert.notEqual(thresholdOutcomes[0],thresholdOutcomes[1],
    'Verifier must distinguish two sides of a projective-distance threshold');
  const invalid=await h.run({circuit1:q('measure q[0];'),circuit2:q(''),mode:'hybrid'});assert(invalid.error);
  const q3=await h.run({circuit1:'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\nh q[0];\n',circuit2:'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n',mode:'hybrid'});assert(!q3.error,q3.error);assert.equal(q3.report.distance_estimate,0);
  const timed=await h.run({circuit1:q('h q[0];'),circuit2:q(''),mode:'wmc'},1);
  assert.equal(timed.code,'TIMEOUT');
  assert(Number.isFinite(timed.request_ms)&&timed.request_ms>=0&&timed.request_ms<10000,
    `Watchdog failed to terminate a timed-out WASM request: ${timed.request_ms} ms`);
  // A timed-out job must not poison the following worker and solver session.
  const afterTimeout=await h.run({circuit1:q('h q[0];h q[0];'),circuit2:q(''),mode:'hybrid'});
  assert(!afterTimeout.error,afterTimeout.error);
  assert.equal(afterTimeout.report.status,'equivalent');
  await h.page.locator('#run').click();await h.page.waitForFunction(()=>document.querySelector('#state').textContent==='Completed.');
  assert((await h.page.locator('#distance').textContent()).includes('0'));
  const download=h.page.waitForEvent('download');await h.page.locator('#download').click();await (await download).saveAs(path.join(out,'downloaded-report.json'));
  const file=path.join(out,'input.qasm');fs.writeFileSync(file,q('u1(0.000001) q[0];'));await h.page.locator('#leftFile').setInputFiles(file);await h.page.waitForFunction(()=>document.querySelector('#left').value.includes('0.000001'));
  await h.page.locator('#mode').selectOption('wmc');await h.page.locator('#run').click();await h.page.waitForFunction(()=>document.querySelector('#state').textContent==='Completed.');
  assert((await h.page.locator('#distance').textContent()).includes('e-7'));
  await h.page.evaluate(()=>{document.querySelector('#form').requestSubmit();document.querySelector('#stop').click()});await h.page.waitForFunction(()=>document.querySelector('#state').textContent.includes('Stopped.'));assert.equal(await h.page.locator('#distance').textContent(),'—');
  await h.page.locator('#run').click();await h.page.waitForFunction(()=>document.querySelector('#state').textContent==='Completed.');
  await h.page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});await h.page.setViewportSize({width:390,height:844});
  assert(await h.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await h.page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({pass:true,differential_cases:results.length,actual_counter_calls:calls,qasm3:true,invalid_input:true,timeout:true,stop:true,upload_download:true,mobile_390px:true,results},null,2));
 }finally{await h.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
