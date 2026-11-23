// Browser adapter for the original QuPRS core. MIT licensed.
import init,{BrowserJob} from './pkg/quprs_web.js?v=20261115-quprs-source-mpfr-v2';
const ready=init({module_or_path:new URL('./pkg/quprs_web_bg.wasm?v=20261115-quprs-source-mpfr-v2',import.meta.url)});let resolveCount,rejectCount;
self.onmessage=async({data})=>{
 if(data.count_result){const r=data.count_result;r.error?rejectCount?.(new Error(r.error)):resolveCount?.(r);return}
 let prepared;
 try{
  await ready;prepared=new BrowserJob(JSON.stringify(data.request));const job=JSON.parse(prepared.job());
  if(job.report){self.postMessage({report:job.report});return}
  const result=await new Promise((resolve,reject)=>{resolveCount=resolve;rejectCount=reject;self.postMessage({count_request:{id:1,engine:job.engine,cnf:job.cnf}})});
  const finished=JSON.parse(prepared.finish(result.stdout));if(finished.error)throw new Error(finished.error);
  finished.report.engine_timing={load_ms:result.load_ms,solve_ms:result.elapsed_ms,heap_bytes:result.heap_bytes};
  self.postMessage(finished);
 }catch(e){self.postMessage({error:String(e)})}finally{prepared?.free();resolveCount=rejectCount=undefined}
};
