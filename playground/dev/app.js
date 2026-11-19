import {createWorkerHost} from './engines/host.js?v=20261115-quprs-source-mpfr-v2';
const $=id=>document.getElementById(id);let host,last,pendingUploads=0;
function busy(value){$('inputs').disabled=value;$('run').disabled=value||pendingUploads>0;$('stop').disabled=!value}
function setPair(a,b,n=1){const pre=`OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[${n}];\n`;$('left').value=pre+a;$('right').value=pre+b}
$('identity').onclick=()=>setPair('h q[0];\nh q[0];','');
$('phase').onclick=()=>setPair('u1(0.000001) q[0];','');
$('cz').onclick=()=>setPair('cz q[0],q[1];','h q[1];\ncx q[0],q[1];\nh q[1];',2);
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
