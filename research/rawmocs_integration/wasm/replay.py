"""Matched original BrowserJob native and Chromium residual capture/replay."""
import functools,http.server,json,os,subprocess,sys,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
root,check,gpmc,raw,phase,E=map(Path,sys.argv[1:])
def q(g,n=1):return f'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[{n}];\n'+g.replace(";",";\n")
cases=[("HH",q("h q[0];h q[0];"),q(""),"eq"),
       ("T",q("t q[0];"),q(""),"neq"),
       ("near",q("u1(0.000001) q[0];"),q(""),"neq"),
       ("tiny",q("u1(0."+"0"*399+"1) q[0];"),q(""),"eq"),
       ("CX_CZ",q("cx q[0],q[1];",2),q("cz q[0],q[1];",2),"neq"),
       ("CZ_decomp",q("cz q[0],q[1];",2),q("h q[1];cx q[0],q[1];h q[1];",2),"eq")]
def native(req,action,**kwargs):
    r=subprocess.run([str(check)],input=json.dumps(dict(request=req,action=action,**kwargs)),text=True,capture_output=True,timeout=20)
    assert r.returncode==0,(r.stdout,r.stderr)
    return json.loads(r.stdout)
def proc(args,t):
    return subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=20,env={**os.environ,"TMPDIR":str(t)})
def same(a,b):
    assert "report" in a and "report" in b,(a,b)
    for k in ("status","solver_invoked","rr_approximate","method","strategy","qubits","numerical_verdict"):
        assert a["report"][k]==b["report"][k],(k,a,b)
def expected(result,want):
    assert result["report"]["status"] in (("equivalent","equivalent*") if want=="eq" else ("not_equivalent",)),result
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Handler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
rows=[]; counts=0
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        page.evaluate("""async()=>{const m=await import('./quprs_web.js');await m.default();window.BrowserJob=m.BrowserJob;
        window.callCounter=(file,req)=>new Promise(resolve=>{const w=new Worker(file);let done=false;
        const end=r=>{if(done)return;done=true;clearTimeout(timer);w.terminate();resolve(r)};
        const timer=setTimeout(()=>end({type:'watchdog'}),15000);
        w.onerror=e=>end({type:'error',message:e.message});w.onmessage=({data})=>{
        if(data.progress)return;if(file!=='runner.js'&&data.id!==req.id)return end({type:'wrong-id'});
        if(data.type==='ready')w.postMessage({type:'solve',id:req.id});else end(data);
        };w.postMessage(req)})}""")
        for label,a,b,want in cases:
            for mode in ("wmc","hybrid"):
                for strategy in ("difference","proportional"):
                    req=dict(circuit1=a,circuit2=b,mode=mode,strategy=strategy,distance_tolerance=1e-8,rr_tolerance=1e-10)
                    n=native(req,"capture")
                    w=page.evaluate("""req=>{window.job?.free();window.job=new BrowserJob(JSON.stringify(req));return JSON.parse(job.job())}""",req)
                    if "report" in n:
                        same(n,w);expected(n,want);rows.append(dict(case=label,mode=mode,strategy=strategy,immediate=True,status=n["report"]["status"]));continue
                    assert n["engine"]==w["engine"]=="gpmc"
                    # Preserve exact mismatch evidence before admission failure. Do not
                    # assume differing native/browser variable IDs are equivalent.
                    if sorted(n["cnf"].splitlines())!=sorted(w["cnf"].splitlines()):
                        (E/"capture-mismatch.json").write_text(json.dumps(dict(case=label,mode=mode,strategy=strategy,request=req,native=n,browser=w),indent=2)+"\n")
                        raise AssertionError((label,mode,strategy,"CAPTURE_MISMATCH"))
                    with tempfile.TemporaryDirectory() as t:
                        t=Path(t);f=t/"source.cnf";f.write_text(w["cnf"]);m=t/"materialized.cnf"
                        g=proc([gpmc,"-mode=1","-prec=30","-cs=64",f],t);assert g.returncode==0,g.stderr
                        ng=native(req,"gpmc",stdout=g.stdout);expected(ng,want)
                        x=proc([phase,f,m],t);assert x.returncode==0,x.stderr
                        ack=x.stdout.strip()
                        y=proc([raw,"--digits",30,"--solver","auto","--timeout-ms",5000,m],t);assert y.returncode==0,y.stderr
                        nr=native(req,"rawmocs",engine="rawmocs",status=0,stdout=y.stdout,stderr=y.stderr,ack=ack)
                        same(ng,nr)
                        wb=page.evaluate("""async cnf=>{const phase=await callCounter('phase-worker.js',{id:1,cnf});
                        if(phase.type!=='materialized')throw Error(JSON.stringify(phase));
                        const result=await callCounter('worker.js',{type:'prepare',id:2,cnf:phase.cnf,digits:30,mode:'auto',timeout:5000});
                        if(result.type!=='count')throw Error(JSON.stringify(result));
                        const g=await callCounter('runner.js',{engine:'gpmc',cnf});
                        if(g.error)throw Error(g.error);
                        return {phase,result,g,raw:JSON.parse(job.finish_rawmocs('rawmocs',result.status,result.stdout,result.stderr,phase.ack||'')),gpmc:JSON.parse(job.finish(g.stdout))};
                        }""",w["cnf"])
                        assert wb["phase"]["cnf"]==m.read_text()
                        assert wb["result"]["stdout"].strip()==y.stdout.strip()
                        same(ng,wb["gpmc"]);same(nr,wb["raw"])
                        assert wb["raw"]["report"]["actual_solver"]=="rawmocs"
                        # Every failure is non-numerical; wrong engine, status,
                        # missing count/ack, wrong precision and UNSAT/nonzero.
                        if counts==0:
                            bad=[dict(engine="gpmc"),dict(status=4),dict(stdout=""),
                                 dict(stderr="RAWMOCS_COMPLETE route=general digits=60 bits=200"),
                                 dict(stdout="s UNSATISFIABLE\nc r mpfr 1 0")]
                            if ack:bad.append(dict(ack=""))
                            base=dict(engine="rawmocs",status=0,stdout=y.stdout,stderr=y.stderr,ack=ack)
                            for change in bad:
                                r=page.evaluate("""v=>JSON.parse(job.finish_rawmocs(v.engine,v.status,v.stdout,v.stderr,v.ack))""",{**base,**change})
                                assert "error" in r and "report" not in r,r
                        counts+=1
                        rows.append(dict(case=label,mode=mode,strategy=strategy,immediate=False,cnf=w["cnf"],native=nr,browser=wb["raw"],gpmc=ng))
                        print("W2B_CASE",label,mode,strategy,nr["report"]["status"],flush=True)
        assert counts>=8,counts
        # RR-only unresolved case must remain UNKNOWN without a counter.
        req=dict(circuit1=q("t q[0];"),circuit2=q(""),mode="reduction",strategy="difference")
        n=native(req,"capture")
        w=page.evaluate("""req=>{const j=new BrowserJob(JSON.stringify(req));try{return JSON.parse(j.job())}finally{j.free()}}""",req)
        same(n,w)
        assert n["report"]["status"]=="unknown" and not n["report"]["solver_invoked"],n
        rows.append(dict(case="rr_unknown",native=n,browser=w))
        browser.close()
        print("W2B_SCOPED_REPLAY_PASS",len(rows),counts,flush=True)
finally:
    (E/"replay.json").write_text(json.dumps(rows,indent=2)+"\n")
    server.shutdown()
