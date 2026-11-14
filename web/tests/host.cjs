const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class W {constructor(){this.messages=[];W.all.push(this)}postMessage(data){this.messages.push(data)}terminate(){this.terminated=true}emit(data){this.onmessage({data})}}W.all=[];
const context={URL,Worker:W,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('web/engines/host.js','utf8').replaceAll('export ', '')+'\nglobalThis.createHost=createWorkerHost;',context);
(async()=>{
 const root=new W(),host=context.createHost(root,'https://example.com/engines/',1000);
 root.emit({count_request:{id:1,engine:'gpmc',cnf:'p cnf 1 0'}});const child=W.all.at(-1);
 child.emit({stdout:'count'});assert(child.terminated);assert.equal(root.messages[0].count_result.stdout,'count');
 root.emit({report:{verdict:'ok'}});assert.equal((await host.result).report.verdict,'ok');assert(root.terminated);
 const r2=new W(),h2=context.createHost(r2,'https://example.com/engines/',1000);
 r2.emit({count_request:{id:2,engine:'ganak',cnf:'p cnf 1 0'}});const c2=W.all.at(-1);
 h2.cancel();await assert.rejects(h2.result,e=>e.code==='STOPPED');assert(r2.terminated&&c2.terminated);
 const r3=new W(),h3=context.createHost(r3,'https://example.com/engines/',5);
 r3.emit({count_request:{id:3,engine:'gpmc',cnf:'p cnf 1 0'}});const c3=W.all.at(-1);
 await assert.rejects(h3.result,e=>e.code==='TIMEOUT');assert(r3.terminated&&c3.terminated);
 console.log('Explicit worker ownership / cancellation / timeout PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
