// One exact upstream counter invocation per disposable classic worker.
// MIT licensed adapter; the loaded engines retain their own licenses.
self.addEventListener('unhandledrejection',e=>{self.postMessage({error:`Counter initialization failed: ${e.reason}`});e.preventDefault()});
self.onmessage = async ({data}) => {
  if (!['gpmc','ganak'].includes(data.engine) || typeof data.cnf !== 'string') {
    self.postMessage({error:'Invalid counter request.'}); return;
  }
  const version=new URL(self.location.href).searchParams.get('v')||'20261115-quprs-source-mpfr-v2';
  const asset=name=>{const url=new URL(name,self.location.href);url.searchParams.set('v',version);return url.href};
  importScripts(asset('output.js'));
  const output=self.createCounterOutput();
  const start=performance.now();
  self.Module={
    noInitialRun:true,
    locateFile:name=>asset(name),
    print:line=>output.append('out',line),
    printErr:line=>output.append('err',line),
    onAbort:reason=>self.postMessage({error:`Counter aborted: ${reason}. ${output.stderr()} ${output.stdout().slice(-1500)} [WASM heap ${typeof HEAPU8!=="undefined"?HEAPU8.buffer.byteLength:"unknown"} bytes]`}),
    onRuntimeInitialized:()=>{
      const loaded=performance.now();
      self.postMessage({progress:true,phase:'runtime-ready',engine:data.engine});
      try {
        Module.FS.writeFile('/input.cnf',data.cnf);
        const args=data.engine==='gpmc'
          ? ['-mode=1','-prec=30','-cs=64','/input.cnf']
          : ['--verb','0','--arjunverb','0','--maxcache','128','--mode','2','--prob','0','/input.cnf'];
        let status=0;
        try { status=Module.callMain(args) || 0; }
        catch(e) { if(e && e.name==='ExitStatus') status=e.status; else throw e; }
        if(status!==0) throw new Error(`Counter exited with status ${status}. ${output.stderr()}`);
        self.postMessage({stdout:output.stdout(),stderr:output.stderr(),elapsed_ms:performance.now()-loaded,load_ms:loaded-start,
          heap_bytes:typeof HEAPU8!=='undefined'?HEAPU8.buffer.byteLength:null,engine:data.engine});
      } catch(e) { self.postMessage({error:String(e),stdout:output.stdout(),stderr:output.stderr()}); }
    }
  };
  try { importScripts(asset(`${data.engine}.js`)); }
  catch(e) { self.postMessage({error:String(e)}); }
};
