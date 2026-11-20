import {createWorkerHost} from './engines/host.js?v=20261115-quprs-source-mpfr-v2';
import {EXAMPLES,CATEGORIES} from './examples.js';

const $=id=>document.getElementById(id);
let host=null,last=null,pendingUploads=0;
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
  return {circuit1:$('left').value,circuit2:$('right').value,
    mode:$('mode').value,strategy:$('strategy').value,
    distance_tolerance:distance,rr_tolerance:reduction};
}
function loadExample(example){
  if(host||pendingUploads)return;
  clearValidation();
  clearResult();
  $('left').value=example.circuit1;
  $('right').value=example.circuit2;
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

for(const side of editorIds){
  $(side+'File').addEventListener('change',async event=>{
    const file=event.target.files[0];
    if(!file)return;
    clearValidation();
    if(file.size>256*1024||!/\.(qasm|txt)$/i.test(file.name)){
      invalid(null,'Upload a .qasm or .txt file no larger than 256 KiB.');
      event.target.value='';
      return;
    }
    pendingUploads++;
    busy(false);
    try{
      $(side).value=await file.text();
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
    host=createWorkerHost(root,new URL('engines/',import.meta.url).href,200000);
    root.postMessage({request});
    const {report}=await host.result;
    last={...report,wall_ms:performance.now()-start};
    state('Completed.','completed');
    $('results').dataset.status=report.status||'unknown';
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
    if(report.rr_approximate&&(report.status==='equivalent'||report.status==='equivalent*')){
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
    $('timing').textContent='Wall time: '+(last.wall_ms/1000).toFixed(3)+' s · '+(report.solver_invoked?'GPMC invoked':'No external counter invoked');
    $('download').disabled=false;
  }catch(error){
    if(error.code==='STOPPED')state('Stopped. No result assigned.','stopped');
    else if(error.code==='TIMEOUT')state('Time limit reached. No result assigned.','timeout');
    else state('Error: '+String(error.message||error),'error');
  }finally{
    host=null;
    busy(false);
  }
});
$('download').addEventListener('click',()=>{
  if(!last)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(last,null,2)],{type:'application/json'}));
  const a=document.createElement('a');
  a.href=url;
  a.download='quprs-browser-report.json';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
