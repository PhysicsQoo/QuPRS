// Experimental one-shot same-runner Stable/Dev comparison.
// Uses actual original GPMC and source-built Rust WASM in disposable Workers.
// Not a substitute for the independent matrix oracle or an exact proof.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {open}=require('./harness.cjs');
const {checkCatalog}=require('./catalog.cjs');

const stableSHA='733a8177eb1f0da47d09ab934f81d1ddf47ecd67';
const SHA=/^[0-9a-f]{40}$/;
const DIGEST=/^[0-9a-f]{64}$/;
const sha256=data=>createHash('sha256').update(data).digest('hex');
const hashFile=p=>sha256(fs.readFileSync(p));
const classification=status=>status==='equivalent'||status==='equivalent*'?'EQ':
  status==='not_equivalent'?'NEQ':status==='unknown'?'UNKNOWN':'INVALID';
const canonical=(ex,mode)=>({
  circuit1:ex.circuit1,circuit2:ex.circuit2,mode,strategy:ex.strategy,
  distance_tolerance:ex.distance_tolerance,rr_tolerance:ex.rr_tolerance
});
const EXTRA_WMC=new Set(['identity','cz','ss','ghz-order']);
const source=root=>fs.readFileSync(path.join(root,'source-sha.txt'),'utf8').trim();

function describeBuild(root,expectedSha){
  const actual=source(root);
  assert(SHA.test(actual),'Invalid browser source SHA');
  assert.equal(actual,expectedSha,'Source mismatch: do not compare unpinned builds');
  const origin=JSON.parse(fs.readFileSync(path.join(root,'engines/PROVENANCE.json'),'utf8'));
  const gpmcWasm=hashFile(path.join(root,'engines/gpmc.wasm'));
  assert(DIGEST.test(gpmcWasm));
  assert.equal(gpmcWasm,origin.sha256['gpmc.wasm'],'GPMC binary no longer matches pinned source metadata');
  const coreWasm=hashFile(path.join(root,'pkg/quprs_web_bg.wasm'));
  return {source_sha:actual,core_wasm_sha256:coreWasm,gpmc_wasm_sha256:gpmcWasm,
    gpmc_revision:origin.revision,gpmc_version:origin.version};
}

async function runVersion(root,prefix,requestList){
  process.env.QUWEB_DIST=root;
  process.env.QUWEB_BASE_PATH=prefix;
  const h=await open();
  const reports=[];
  try{
    for(const item of requestList){
      const output=await h.run(item.request,30000);
      const r=output.report;
      reports.push({
        id:item.id,request_sha256:item.request_sha256,
        error:output.error??null,error_code:output.code??null,
        status:r?.status??null,rr_approximate:r?.rr_approximate??null,
        distance_estimate:r?.distance_estimate??null,
        solver_invoked:r?.solver_invoked??null,
        method:r?.method??null,strategy:r?.strategy??null,
        core_seconds:r?.core_seconds??null,counter_seconds:r?.counter_seconds??null,
        request_wall_ms:output.request_ms,
      });
    }
  }finally{await h.close();}
  return reports;
}

(async()=>{
  const devRoot=path.resolve(process.env.QUWEB_DIST||'');
  const stableRoot=path.resolve(process.env.QUWEB_STABLE_ROOT||'');
  const devSHA=process.env.QUWEB_EXPECTED_DEV_SHA;
  assert(devSHA&&SHA.test(devSHA),'Require exact dev source SHA');
  const stable=describeBuild(stableRoot,stableSHA);
  const dev=describeBuild(devRoot,devSHA);
  const gallery=await checkCatalog(); // independent tiny-matrix oracle
  const requests=[];
  for(const ex of gallery.examples){
    const modes=ex.mode==='wmc'||!EXTRA_WMC.has(ex.id)?[ex.mode]:[ex.mode,'wmc'];
    for(const mode of modes){
      const request=canonical(ex,mode);
      requests.push({id:ex.id+'/'+mode,example_id:ex.id,expected:ex.expected,
        request,request_sha256:sha256(JSON.stringify(request))});
    }
  }
  // A mathematically different unitary can be considered within a user-supplied
  // tolerance. Keep that tolerant verdict separate from exact matrix class.
  for(const [id,epsilon,expectedClass] of [
    ['t-different',0.37,'NEQ'],['t-different',0.40,'EQ'],
    ['phase',4.9e-7,'NEQ'],['phase',5.1e-7,'EQ'],
  ]){
    const example=gallery.examples.find(x=>x.id===id);
    const request={...canonical(example,'wmc'),distance_tolerance:epsilon};
    requests.push({id:id+'/wmc/boundary-'+epsilon,example_id:id,
      expected:example.expected,expected_verdict_class:expectedClass,
      request,request_sha256:sha256(JSON.stringify(request))});
  }
  const stableReports=await runVersion(stableRoot,'/QuPRS/playground/v0.17.2/',requests);
  const devReports=await runVersion(devRoot,'/QuPRS/playground/dev/',requests);
  const semanticChanges=[],distanceDrifts=[],rawChanges=[],errors=[],cases=[];
  for(let i=0;i<requests.length;i++){
    const item=requests[i],a=stableReports[i],b=devReports[i];
    assert.equal(a.request_sha256,b.request_sha256);
    const classA=classification(a.status),classB=classification(b.status);
    const expectedClass=item.expected_verdict_class??(item.expected==='different'?'NEQ':'EQ');
    const report={id:item.id,request_sha256:item.request_sha256,
      expected_matrix_category:item.expected,expected_tolerance_verdict:expectedClass,
      stable:a,dev:b,
      category_stable:classA,category_dev:classB,
      semantic_agreement:classA===classB&&classA!=='INVALID'};
    cases.push(report);
    if(a.error||b.error||classA==='INVALID'||classB==='INVALID')
      errors.push({id:item.id,stable_error:a.error,dev_error:b.error,classA,classB});
    if(classA!==classB)semanticChanges.push(item.id);
    if(a.status!==b.status||a.rr_approximate!==b.rr_approximate)
      rawChanges.push(item.id);
    // Matrix expectations are independent of either QuPRS implementation.
    if(classA!==expectedClass||classB!==expectedClass)
      errors.push({id:item.id,reason:'oracle category mismatch',expectedClass,classA,classB});
    if(typeof a.distance_estimate==='number'&&typeof b.distance_estimate==='number'){
      const delta=Math.abs(a.distance_estimate-b.distance_estimate);
      report.distance_absolute_delta=delta;
      // Observation only: this bound is not a certified equality interval.
      if(delta>5e-8)distanceDrifts.push({id:item.id,stable:a.distance_estimate,
        dev:b.distance_estimate,absolute_delta:delta});
    }else report.distance_absolute_delta=null;
  }
  const output={
    schema:1,
    kind:'quprs-same-runner-version-reproduction',
    limitation:'Numerical distance deltas and matching verdicts are observations, not proof certificates.',
    stable,dev,
    environment:{runner:'same GitHub Actions Chromium/host',clock:'worker-local reported wall time'},
    cases,summary:{
      paired:cases.length,semantic_disagreements:semanticChanges,
      raw_verdict_or_approximation_changes:rawChanges,
      numeric_distance_drift_over_5e_minus_8:distanceDrifts,
      invalid_or_oracle_disagreements:errors,
      distinct_requests:new Set(cases.map(x=>x.request_sha256)).size,
      maximum_observed_distance_delta:Math.max(0,...cases.map(x=>x.distance_absolute_delta??0)),
      stable_gpmc_invocations:stableReports.filter(x=>x.solver_invoked===true).length,
      dev_gpmc_invocations:devReports.filter(x=>x.solver_invoked===true).length,
      stable_unknown_count:stableReports.filter(x=>x.status==='unknown').length,
      dev_unknown_count:devReports.filter(x=>x.status==='unknown').length,
    }
  };
  const out=process.env.QUWEB_QA_OUT||'web/test-results';
  fs.mkdirSync(out,{recursive:true});
  const filename=path.join(out,'version-reproduction.json');
  fs.writeFileSync(filename,JSON.stringify(output,null,2)+'\n');
  console.log(JSON.stringify({report:filename,stable_sha:stable.source_sha,dev_sha:dev.source_sha,
    ...output.summary},null,2));
  if(errors.length||semanticChanges.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
