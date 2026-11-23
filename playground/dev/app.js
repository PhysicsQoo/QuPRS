import {createWorkerHost} from './engines/host.js?v=20261115-quprs-source-mpfr-v2';
import {EXAMPLES,CATEGORIES} from './examples.js';
import {exportCase,importCase,normalizeRequest,assertCircuitText,MAX_CIRCUIT_BYTES,MAX_CASE_BYTES} from './case-io.js';
import {readBuildIdentity,reportProvenance} from './provenance.js';

const $=id=>document.getElementById(id);
let host=null,last=null,pendingUploads=0;
const timeoutMs=200000;
let elapsedTicker=null;
const editorIds=['left','right'];
const groups=new Map();

function state(message,kind='ready'){
  $('state').textContent=message;
  document.body.dataset.runState=kind;
}
function busy(value){
  $('inputs').disabled=value;
  $('run').disabled=value||pendingUploads>0;
  $('stop').disabled=!value;
  $('exportCase').disabled=value||pendingUploads>0;
  $('caseFile').disabled=value||pendingUploads>0;
}
function clearValidation(){
  $('inputError').hidden=true;
  $('inputError').textContent='';
  for(const id of [...editorIds,'epsilon','rr'])$(id).removeAttribute('aria-invalid');
}
function invalid(id,message){
  $('inputError').textContent=message;
  $('inputError').hidden=false;
  if(id){
    $(id).setAttribute('aria-invalid','true');
    if(id==='rr')$('advanced').open=true;
    $(id).focus();
  }
  state('Input requires attention. No computation started.','error');
  return null;
}
function clearResult(){
  last=null;
  $('download').disabled=true;
  $('distance').textContent='—';
  for(const id of ['verdict','warning','method','timing'])$(id).textContent='';
  $('results').removeAttribute('data-status');
}
// A previous verdict only applies to the exact circuit texts and settings used.
function invalidateResult(){
  if(host)return; // Active requests are read-only through the disabled fieldset.
  if(last!==null || $('results').hasAttribute('data-status')){
    clearResult();
    state('Inputs or settings changed. Run comparison again.','stale');
  }
}
const buildIdentity=readBuildIdentity(import.meta.url);
function showBuildInfo(){
  const match=location.pathname.match(/\/playground\/(dev|v\d+\.\d+\.\d+)\/?$/);
  const label=match?.[1]==='dev'?'Dev preview':
    match?.[1]?.startsWith('v')?'Stable '+match[1]:'Local preview';
  const target=$('buildInfo');
  target.textContent=label;
  // A same-origin source marker is useful identification, not a proof.
  buildIdentity.then(identity=>{
    if(identity.source_sha)target.textContent=label+' · source '+identity.source_sha.slice(0,12);
  }).catch(()=>{});
}
showBuildInfo();
for(const id of [...editorIds,'epsilon','rr','mode','strategy']){
  $(id).addEventListener('input',invalidateResult);
  $(id).addEventListener('change',invalidateResult);
}
// Keep native textareas: expose the cursor, keyboard shortcuts and indentation
// without a dependency on a code editor or off-device QASM parsing service.
function editorPosition(id){
  const field=$(id),prefix=field.value.slice(0,field.selectionStart);
  const line=prefix.split('\n').length;
  const col=prefix.length-prefix.lastIndexOf('\n');
  $(id+'Position').textContent='Ln '+line+' · Col '+col;
}
for(const id of editorIds){
  const field=$(id);
  const update=()=>editorPosition(id);
  for(const type of ['input','click','keyup','select'])field.addEventListener(type,update);
  field.addEventListener('keydown',event=>{
    if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){
      event.preventDefault();
      if(!host&&!pendingUploads)$('form').requestSubmit();
      return;
    }
    // Escape then Tab permits keyboard-only navigation out of the editor.
    if(event.key==='Escape'){field.dataset.nextTabLeaves='true';return;}
    if(event.key==='Enter'&&!event.shiftKey&&!event.altKey&&!event.ctrlKey&&!event.metaKey){
      const prefix=field.value.slice(field.value.lastIndexOf('\n',field.selectionStart-1)+1,field.selectionStart);
      const indent=prefix.match(/^[ \t]*/)?.[0]||'';
      if(indent){
        event.preventDefault();
        field.setRangeText('\n'+indent,field.selectionStart,field.selectionEnd,'end');
        field.dispatchEvent(new Event('input',{bubbles:true}));
      }
      return;
    }
    if(event.key!=='Tab')return;
    if(field.dataset.nextTabLeaves==='true'){
      delete field.dataset.nextTabLeaves;
      return;
    }
    if(event.altKey||event.ctrlKey||event.metaKey)return;
    event.preventDefault();
    const start=field.selectionStart,end=field.selectionEnd;
    const lineStart=field.value.lastIndexOf('\n',start-1)+1;
    const segment=field.value.slice(lineStart,end);
    const multiline=field.value.slice(start,end).includes('\n');
    if(event.shiftKey){
      const unindented=segment.replace(/^(?: {1,2}|\t)/gm,'');
      if(unindented===segment)return;
      field.setRangeText(unindented,lineStart,end,'end');
      if(multiline)field.setSelectionRange(lineStart,lineStart+unindented.length);
      else{
        const caret=Math.max(lineStart,start-(segment.length-unindented.length));
        field.setSelectionRange(caret,caret);
      }
    }else if(multiline){
      const indented=segment.replace(/^/gm,'  ');
      field.setRangeText(indented,lineStart,end,'end');
      field.setSelectionRange(lineStart,lineStart+indented.length);
    }else field.setRangeText('  ',start,end,'end');
    field.dispatchEvent(new Event('input',{bubbles:true}));
  });
  field.addEventListener('blur',event=>delete event.currentTarget.dataset.nextTabLeaves);
  update();
}
function validateRequest(){
  clearValidation();
  for(const id of editorIds){
    if(!$(id).value.trim())return invalid(id,'Both circuit editors need OpenQASM text. Circuit '+(id==='left'?'A':'B')+' is empty.');
  }
  const epsilonText=$('epsilon').value.trim();
  const rrText=$('rr').value.trim();
  const distance=Number(epsilonText),reduction=Number(rrText);
  if(!epsilonText||!Number.isFinite(distance)||distance<0||distance>1){
    return invalid('epsilon','Projective distance tolerance must be a finite number from 0 to 1.');
  }
  if(!rrText||!Number.isFinite(reduction)||reduction<0){
    return invalid('rr','Reduction coefficient tolerance must be a finite, non-negative number.');
  }
  const request={circuit1:$('left').value,circuit2:$('right').value,
    mode:$('mode').value,strategy:$('strategy').value,
    distance_tolerance:distance,rr_tolerance:reduction};
  try{return normalizeRequest(request);}
  catch(error){
    const message=String(error.message||error);
    const field=message.startsWith('Circuit A')?'left':
      message.startsWith('Circuit B')?'right':null;
    return invalid(field,message);
  }
}
function loadExample(example){
  if(host||pendingUploads)return;
  clearValidation();
  clearResult();
  $('left').value=example.circuit1;
  $('right').value=example.circuit2;
  editorIds.forEach(editorPosition);
  $('mode').value=example.mode;
  $('strategy').value=example.strategy;
  $('epsilon').value=String(example.distance_tolerance);
  $('rr').value=String(example.rr_tolerance);
  $('exampleDescription').textContent=example.title+' — '+example.description;
  state('Loaded example: '+example.description,'ready');
}
function filterExamples(){
  const category=$('exampleCategory').value;
  const query=$('exampleSearch').value.trim().toLocaleLowerCase();
  let visible=0;
  for(const example of EXAMPLES){
    const button=$('exampleButtons').querySelector('[data-example-id="'+example.id+'"]');
    const text=(example.title+' '+example.description).toLocaleLowerCase();
    const show=(category==='all'||category===example.category)&&text.includes(query);
    button.hidden=!show;
    if(show)visible++;
  }
  for(const group of groups.values()){
    group.hidden=!Array.from(group.querySelectorAll('button[data-example-id]')).some(button=>!button.hidden);
  }
  $('exampleEmpty').hidden=visible!==0;
}
for(const category of CATEGORIES){
  const option=document.createElement('option');
  option.value=category.id;
  option.textContent=category.title;
  $('exampleCategory').append(option);
  const section=document.createElement('section');
  section.className='example-group';
  const heading=document.createElement('h3');
  heading.textContent=category.title;
  section.append(heading);
  groups.set(category.id,section);
  $('exampleButtons').append(section);
}
for(const example of EXAMPLES){
  const button=document.createElement('button');
  button.type='button';
  button.textContent=example.title;
  button.dataset.exampleId=example.id;
  button.title=example.description;
  button.addEventListener('click',()=>loadExample(example));
  groups.get(example.category).append(button);
}
$('exampleSearch').addEventListener('input',filterExamples);
$('exampleSearch').addEventListener('keydown',event=>{
  // Search should never submit the comparison form or start a solver worker.
  if(event.key==='Enter')event.preventDefault();
});
$('exampleCategory').addEventListener('change',filterExamples);
$('resetExample').addEventListener('click',()=>{
  $('exampleCategory').value='all';
  $('exampleSearch').value='';
  filterExamples();
  loadExample(EXAMPLES.find(e=>e.id==='identity'));
});

// Reordering the two source circuits is an editor operation, not a solver
// invocation. Discard any report computed for the previous operand order.
$('swapCircuits').addEventListener('click',()=>{
  if(host||pendingUploads)return;
  const left=$('left').value;
  $('left').value=$('right').value;
  $('right').value=left;
  editorIds.forEach(editorPosition);
  clearValidation();
  clearResult();
  $('exampleDescription').textContent='Circuit order changed. Select an example to restore its original orientation.';
  state('Circuit A and Circuit B swapped. Ready to compare.','ready');
});

for(const side of editorIds){
  $(side+'File').addEventListener('change',async event=>{
    const file=event.target.files[0];
    if(!file)return;
    clearValidation();
    if(file.size>MAX_CIRCUIT_BYTES||!/\.(qasm|txt)$/i.test(file.name)){
      invalid(null,'Upload a .qasm or .txt file no larger than 256 KiB.');
      event.target.value='';
      return;
    }
    pendingUploads++;
    busy(false);
    try{
      // Reject malformed UTF-8, empty files and oversized decoded content
      // before mutating the active editor or replacing a prior result.
      const text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
      assertCircuitText(text,side==='left'?'Circuit A':'Circuit B');
      $(side).value=text;
      editorPosition(side);
      clearResult();
      state('Loaded Circuit '+(side==='left'?'A':'B')+' from a local file.','ready');
    }catch(e){
      invalid(null,'Could not read the local file: '+String(e.message||e));
    }finally{
      pendingUploads--;
      busy(false);
      event.target.value='';
    }
  });
}
// Import only data from user-selected local JSON. A prior report's claimed
// verdict, timings and distance are discarded; a fresh Worker run is required.
$('caseFile').addEventListener('change',async event=>{
  const file=event.target.files?.[0];
  if(!file)return;
  if(host||pendingUploads){event.target.value='';return;}
  if(!/\.json$/i.test(file.name)||file.size>MAX_CASE_BYTES){
    invalid(null,'Import a .json case or report no larger than 768 KiB.');
    event.target.value='';
    return;
  }
  pendingUploads++;
  busy(false);
  try{
    const {request,kind}=importCase(await file.text());
    clearValidation();
    clearResult();
    $('left').value=request.circuit1;
    $('right').value=request.circuit2;
    $('mode').value=request.mode;
    $('strategy').value=request.strategy;
    $('epsilon').value=String(request.distance_tolerance);
    $('rr').value=String(request.rr_tolerance);
    editorIds.forEach(editorPosition);
    $('exampleDescription').textContent='Imported '+kind+' inputs. The imported result is not trusted.';
    state('Imported '+kind+' inputs and settings. Run comparison to verify locally.','ready');
  }catch(e){
    invalid(null,'Cannot import comparison: '+String(e.message||e));
  }finally{
    pendingUploads--;
    busy(false);
    event.target.value='';
  }
});
$('stop').addEventListener('click',()=>host?.cancel());
$('form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(host||pendingUploads)return;
  clearResult();
  const request=validateRequest();
  if(!request)return;
  busy(true);
  state('Computing locally…','running');
  const start=performance.now();
  try{
    const root=new Worker(new URL('worker.js?v=20261115-quprs-source-mpfr-v2',import.meta.url),{type:'module'});
    host=createWorkerHost(root,new URL('engines/',import.meta.url).href,timeoutMs);
    const tick=()=>{
      $('progress').hidden=false;
      $('progress').textContent='Elapsed '+((performance.now()-start)/1000).toFixed(1)+' s / '+(timeoutMs/1000)+' s limit';
    };
    tick();
    elapsedTicker=setInterval(tick,1000);
    root.postMessage({request});
    const {report}=await host.result;
    // Keep the request used for the report so a downloaded file can be reproduced.
    const provenance=await reportProvenance(request,buildIdentity);
    last={...report,wall_ms:performance.now()-start,request,provenance};
    state('Completed.','completed');
    const approximateEq=report.rr_approximate &&
      (report.status==='equivalent'||report.status==='equivalent*');
    $('results').dataset.status=approximateEq?'approximate':
      report.status==='equivalent*'?'equivalent-global':(report.status||'unknown');
    const d=report.distance_estimate;
    $('distance').textContent=typeof d==='number'&&Number.isFinite(d)
      ?'≈ '+(d===0?'0':d.toExponential(5)):'Not computed';
    const labels={
      equivalent:'Equivalent',
      'equivalent*':'Equivalent up to global phase',
      not_equivalent:'Different beyond tolerance',
      unknown:'Inconclusive — not proof of inequivalence'
    };
    let verdict=labels[report.status]||'Result status unavailable';
    if(approximateEq){
      verdict='Within reduction tolerance (approximate)';
    }
    $('verdict').textContent=verdict;
    const explanation=report.status==='unknown'
      ?'The computation is inconclusive. UNKNOWN does not mean different.'
      :report.rr_approximate
      ?'Reduction tolerance was applied. This is not a certificate of exact equality.'
      :'A numerical estimate alone is not a certificate of exact equality.';
    $('warning').textContent=[report.warning,explanation].filter(Boolean).join(' ');
    $('method').textContent='Method: '+String(report.method||request.mode)+' · Strategy: '+String(report.strategy||request.strategy);
    $('timing').textContent='Wall time: '+(last.wall_ms/1000).toFixed(3)+' s · '+
      (report.solver_invoked?'Local GPMC weighted counter used':'No weighted counter used');
    $('download').disabled=false;
    $('results').scrollIntoView({block:'nearest',behavior:
      matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  }catch(error){
    if(error.code==='STOPPED')state('Stopped. No result assigned.','stopped');
    else if(error.code==='TIMEOUT')state('Time limit reached. No result assigned.','timeout');
    else state('Error: '+String(error.message||error),'error');
  }finally{
    clearInterval(elapsedTicker);
    elapsedTicker=null;
    $('progress').hidden=true;
    host=null;
    busy(false);
  }
});
function downloadJSON(data,name){
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'}));
  const a=document.createElement('a');
  a.href=url;
  a.download=name;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('exportCase').addEventListener('click',()=>{
  if(host||pendingUploads)return;
  const request=validateRequest();
  if(!request)return;
  try{downloadJSON(exportCase(request),'quprs-browser-case.json');}
  catch(e){invalid(null,'Cannot export comparison: '+String(e.message||e));}
});
$('download').addEventListener('click',()=>{
  if(last)downloadJSON(last,'quprs-browser-report.json');
});
