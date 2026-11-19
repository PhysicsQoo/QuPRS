// MIT licensed worker ownership / cancellation boundary for PathsumWMC.
// The page owns every worker, so Stop/timeout explicitly terminates the solver
// and its counter workers. No reliance on nested-worker lifetime propagation.
export const runtimeVersion='20261115-quprs-source-mpfr-v2';
export function createWorkerHost(root,engineRoot,timeoutMs=200000,options={}) {
  const WorkerCtor=options.WorkerCtor||Worker;
  const children=new Set();let settled=false,resolve,reject;
  const result=new Promise((a,b)=>{resolve=a;reject=b});
  const failure=(message,code='ERROR')=>Object.assign(new Error(message),{code});
  const finish=(data,error)=>{
    if(settled)return;settled=true;clearTimeout(timer);
    root.terminate();for(const child of children)child.terminate();children.clear();
    error?reject(error):resolve(data);
  };
  const timer=setTimeout(()=>finish(null,failure(`Time limit reached (${timeoutMs/1000} seconds).`,'TIMEOUT')),timeoutMs);
  root.onerror=e=>{e.preventDefault?.();finish(null,failure(e.message))};
  root.onmessage=({data})=>{
    if(settled)return;
    if(data.count_request) {
      const job=data.count_request;
      let child;
      try {
        const url=new URL('runner.js',engineRoot);url.searchParams.set('v',runtimeVersion);
        child=new WorkerCtor(url);children.add(child);
        const reply=response=>{
          if(!children.delete(child))return;child.terminate();
          if(!settled)root.postMessage({count_result:{id:job.id,...response}});
        };
        child.onerror=e=>{e.preventDefault?.();reply({error:e.message})};
        child.onmessage=({data:response})=>{if(!response.progress)reply(response)};
        child.postMessage({engine:job.engine,cnf:job.cnf});
      } catch(e) {
        if(child){children.delete(child);child.terminate()}
        root.postMessage({count_result:{id:job.id,error:String(e)}});
      }
      return;
    }
    if(data.error)finish(null,failure(data.error));
    else if(data.report)finish(data);
  };
  return {result,cancel:()=>finish(null,failure('Computation stopped.','STOPPED'))};
}
