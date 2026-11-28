"""Compare original GPMC source-phase input with identical materialized CNF in both engines."""
import functools,http.server,json,sys,threading,re,hashlib
from decimal import Decimal,localcontext
from pathlib import Path
from playwright.sync_api import sync_playwright
site,evidence=map(Path,sys.argv[1:])
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(site)))
threading.Thread(target=server.serve_forever,daemon=True).start()
js="""async ({worker,cnf,raw})=>new Promise(resolve=>{
 const w=new Worker(worker); let settled=false;
 const finish=x=>{if(settled)return;settled=true;clearTimeout(timer);w.terminate();resolve(x)};
 const timer=setTimeout(()=>finish({error:"watchdog"}),15000);
 w.onerror=e=>finish({error:e.message});
 w.onmessage=({data})=>{
   if(data.type==="ready"){w.postMessage({type:"solve",id:1});return}
   if(data.progress)return;
   finish(data);
 };
 w.postMessage(raw?{type:"prepare",id:1,cnf,digits:30,mode:"auto",timeout:10000}:{engine:"gpmc",cnf});
})"""
def components(s):
    lines=[x for x in s.splitlines() if x.startswith("c s exact double prec-sci ")]
    assert len(lines)==1,s
    v=lines[0].split("prec-sci ",1)[1].replace(" ","").replace("+-","-")
    if not v.endswith("i"):return Decimal(v),Decimal(0)
    v=v[:-1];split=[m.start() for m in re.finditer(r"(?<![eE])[+-]",v) if m.start()>0]
    if not split:return Decimal(0),Decimal(v if v not in ("+","-") else v+"1")
    i=split[-1];return Decimal(v[:i]),Decimal(v[i:] if v[i:] not in ("+","-") else v[i:]+"1")
def raw_count(r):
    assert r["type"]=="count",r
    a,b=r["stdout"].splitlines()[1].split()[3:5];return Decimal(a),Decimal(b)
def close(a,b):
    with localcontext() as c:
        c.prec=100
        return all(abs(x-y)<=Decimal("1e-26")*max(abs(x),abs(y),Decimal("1e-80")) for x,y in zip(a,b))
def cnf(desc,clauses="1 0\n",n=1,count=1):
    return f"p cnf {n} {count}\nc t wmc\n"+desc+"c p weight 1 1.0 0.0 0\nc p weight -1 1.0 0.0 0\n"+clauses
cases=[("clifford","c p quprs-phase 1 1 4 0 1 0 100\n"),("negative","c p quprs-phase 1 1 2 0 1 0 100\n"),("nonclifford","c p quprs-phase 1 1 7 0 1 0 128\n"),("tiny","c p quprs-phase 1 0 1 1 1000000000000000000000000000000 1 160\n")]
rows=[]
try:
 with sync_playwright() as p:
    b=p.chromium.launch(headless=True);page=b.new_page();page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
    def call(worker,source,raw=False):return page.evaluate(js,dict(worker=worker,cnf=source,raw=raw))
    for label,desc in cases:
        source=cnf(desc);converted=call("phase-worker.js",source);assert converted.get("ack")==1,converted
        material=converted["cnf"];assert "c p quprs-phase " not in material
        original=call("runner.js",source);same=call("runner.js",material);raw=call("raw-worker.js",material,True)
        assert "c o quprs-phase-weights 1" in original["stdout"],original
        a,c,d=components(original["stdout"]),components(same["stdout"]),raw_count(raw)
        assert close(a,c) and close(c,d),(label,a,c,d)
        if label=="tiny":assert d[1]!=0
        row=dict(case=label,source=source,materialized=material,cnf_sha256=hashlib.sha256(material.encode()).hexdigest(),gpmc_original=original,gpmc_materialized=same,rawmocs=raw)
        rows.append(row);print("W2_CASE",label,flush=True)
    for label,source in [("duplicate",cnf(cases[0][1]*2)),("zero_denominator",cnf("c p quprs-phase 1 1 0 0 1 0 100\n")),("missing_placeholder",cnf(cases[0][1]).replace("c p weight 1 1.0 0.0 0\n",""))]:
        r=call("phase-worker.js",source);assert "error" in r,r;rows.append(dict(case=label,result=r))
    b.close()
    print("W2_SCOPED_PHASE_PARITY_PASS cases=4 malformed=3")
finally:
    (evidence/"browser-results.json").write_text(json.dumps(rows,indent=2)+"\n");server.shutdown()
