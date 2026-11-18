const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require(process.env.QUWEB_PLAYWRIGHT||'playwright');
async function open(){
 const dist=path.resolve(process.env.QUWEB_DIST||'web'),prefix=process.env.QUWEB_BASE_PATH||'/QuPRS/';
 const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json'};
 const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');if(!u.pathname.startsWith(prefix)){res.writeHead(404);res.end();return}
  const f=path.resolve(dist,decodeURIComponent(u.pathname.slice(prefix.length))||'index.html');
  if(!f.startsWith(dist+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile()){res.writeHead(404);res.end();return}
  res.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(res);
 });await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser=await chromium.launch({args:['--js-flags=--max-old-space-size=2048']});let page=await browser.newPage();
 const base=`http://127.0.0.1:${server.address().port}${prefix}`;await page.goto(base);
 const run=async(request,limit=200000)=>page.evaluate(async({base,request,limit})=>{
  const {createWorkerHost}=await import(new URL('engines/host.js',base).href);const start=performance.now();
  const root=new Worker(new URL('worker.js',base),{type:'module'});const host=createWorkerHost(root,new URL('engines/',base).href,limit);root.postMessage({request});
  try {const d=await host.result;return {...d,request_ms:performance.now()-start}}
  catch(e){return {error:e.message,code:e.code,request_ms:performance.now()-start}}
 },{base,request,limit});
 return {base,page,browser,run,close:async()=>{await browser.close();await new Promise(r=>server.close(r))}};
}
module.exports={open};
