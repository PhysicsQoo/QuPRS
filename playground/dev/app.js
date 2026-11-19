import {createWorkerHost} from './engines/host.js?v=20261115-quprs-source-mpfr-v2';
import {EXAMPLES,CATEGORIES} from './examples.js';
const $=id=>document.getElementById(id);let host,last,pendingUploads=0;
function busy(value){$('inputs').disabled=value;$('run').disabled=value||pendingUploads>0;$('stop').disabled=!value}
const groups=new Map(CATEGORIES.map(category=>[category.id,category.title]));
for(const [category,title] of groups){
  const items=EXAMPLES.filter(example=>example.category===category);
  if(!items.length)continue;
  const section=document.createElement('section');
  const heading=document.createElement('h3');heading.textContent=title;section.append(heading);
  for(const example of items){
    const button=document.createElement('button');button.type='button';
    button.textContent=example.title;button.dataset.exampleId=example.id;
    button.title=example.description;
    button.addEventListener('click',()=>{
      $('left').value=example.circuit1;$('right').value=example.circuit2;
      $('mode').value=example.mode;$('strategy').value=example.strategy;
      $('epsilon').value=String(example.distance_tolerance);
      $('rr').value=String(example.rr_tolerance);
      $('state').textContent='Loaded example: '+example.description;
    });
    section.append(button);
  }
  $('exampleButtons').append(section);
}
for(const side of ['left','right'])$(side+'File').onchange=async e=>{const file=e.target.files[0];if(!file)return;pendingUploads++;$('run').disabled=true;try{$(side).value=await file.text()}finally{pendingUploads--;$('run').disabled=Boolean(host)||pendingUploads>0}};
$('stop').onclick=()=>host?.cancel();
$('form').onsubmit=async e=>{
 e.preventDefault();last=null;$('download').disabled=true;$('distance').textContent='—';$('verdict').textContent='';$('warning').textContent='';$('timing').textContent='';
 const request={circuit1:$('left').value,circuit2:$('right').value,mode:$('mode').value,strategy:$('strategy').value,distance_tolerance:Number($('epsilon').value),rr_tolerance:Number($('rr').value)};
 busy(true);$('state').textContent='Computing locally…';const start=performance.now();
 try{
  const root=new Worker(new URL('worker.js?v=20261115-quprs-source-mpfr-v2',import.meta.url),{type:'module'});host=createWorkerHost(root,new URL('engines/',import.meta.url).href,200000);root.postMessage({request});
  const {report}=await host.result;last={...report,wall_ms:performance.now()-start};$('state').textContent='Completed.';
  const d=report.distance_estimate;$('distance').textContent=typeof d==='number'?`≈ ${d===0?'0':d.toExponential(5)}`:'Not computed';
  const labels={equivalent:'Equivalent',"equivalent*":'Equivalent up to global phase',not_equivalent:'Different beyond tolerance',unknown:'Inconclusive'};
  $('verdict').textContent=report.rr_approximate?'Within reduction tolerance':(labels[report.status]||report.status);
  $('warning').textContent=report.warning||'Numerical estimate.';
  $('timing').textContent=`Wall time: ${(last.wall_ms/1000).toFixed(3)} s${report.solver_invoked?' · GPMC invoked':' · completed by reduction/analytic check'}`;
  $('download').disabled=false;
 }catch(error){$('state').textContent=error.code==='STOPPED'?'Stopped. No result assigned.':`Error: ${error.message}`}
 finally{host=null;busy(false)}
};
$('download').onclick=()=>{if(!last)return;const url=URL.createObjectURL(new Blob([JSON.stringify(last,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='quprs-browser-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
