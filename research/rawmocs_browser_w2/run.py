"""Exact artifact reuse; compile only original QuPRS phase bridge and GNU dependencies."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
W=Path(sys.argv[1]).resolve();E=W/"evidence";E.mkdir(exist_ok=True);SITE=W/"site";SITE.mkdir()
r={"status":"HOLD","rawmocs_artifact":15256299864,"gpmc_artifact":15256494232}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,args,cwd=None,seconds=180):
    with (E/(name+".log")).open("wb") as f:
        p=subprocess.run(args,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=seconds)
    print("W2_STEP",name,p.returncode,flush=True)
    if p.returncode:print((E/(name+".log")).read_text(errors="replace")[-6000:]);raise RuntimeError(name)
def unpack(name,checksum):
    archive=W/(name+".zip");assert sha(archive)==checksum
    dest=W/name;dest.mkdir()
    with zipfile.ZipFile(archive) as z:
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(dest)
    return dest
def find(d,name):
    matches=list(d.rglob(name));assert len(matches)==1,(name,matches);return matches[0]
def main():
    raw=unpack("rawmocs","d8ccbdb5a9ae50e2004da71eabdb91e37c19128cf149d863eb5f6c8e2c412454")
    gpmc=unpack("gpmc","e27788f404b895adb0d9224b7d9c89ccb19a16dc732b44097de502c6e198a215")
    rec=json.loads(find(raw,"receipt.json").read_text());assert rec["status"]=="W1B_SCOPED_BROWSER_REPRO_PASS"
    for n in ("rawmocs.js","rawmocs.wasm","worker.js"):
        p=find(raw,n);assert sha(p)==rec["artifacts"][n]
        shutil.copy2(p,SITE/("raw-worker.js" if n=="worker.js" else n))
    for n in ("gpmc.js","gpmc.wasm"):shutil.copy2(find(gpmc,n),SITE/n)
    for n in ("runner.js","output.js"):shutil.copy2(ROOT/"web/engines"/n,SITE/n)
    shutil.copy2(HERE/"phase-worker.js",SITE/"phase-worker.js")
    (SITE/"index.html").write_text("<!doctype html><title>W2 phase parity</title>")
    prefix=W/"prefix";prefix.mkdir()
    for name,checksum in [("gmp-6.3.0.tar.xz","a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898"),("mpfr-4.2.1.tar.xz","277807353a6726978996945af13e52829e3abd7a9a5b7fb2793894e18f1fcbb2")]:
        p=find(gpmc,name);assert sha(p)==checksum
        with tarfile.open(p) as t:t.extractall(W,filter="data")
    g=W/"gmp-6.3.0";m=W/"mpfr-4.2.1"
    run("gmp-configure",["emconfigure","./configure","--disable-assembly","--disable-shared","--enable-cxx","--host=wasm32",f"--prefix={prefix}","CC_FOR_BUILD=gcc","CFLAGS=-O2","CXXFLAGS=-O2"],g)
    run("gmp-build",["emmake","make","-j2"],g,300);run("gmp-install",["emmake","make","install"],g)
    run("mpfr-configure",["emconfigure","./configure","--host=wasm32","--disable-shared",f"--with-gmp={prefix}",f"--prefix={prefix}","CFLAGS=-O2 -fPIC"],m)
    run("mpfr-build",["emmake","make","-j2"],m,300);run("mpfr-install",["emmake","make","install"],m)
    bridge=ROOT/"rust/quprs/native/mpfr_weight_bridge.c"
    run("bridge-c",["emcc","-O2",f"-I{prefix}/include","-c",str(bridge),"-o",str(W/"bridge.o")])
    run("bridge-link",["em++","-O2","-fexceptions",f"-I{prefix}/include",f"-I{ROOT}/scripts/web",str(HERE/"phase_main.cc"),str(W/"bridge.o"),f"-L{prefix}/lib","-lmpfr","-lgmpxx","-lgmp","-sMODULARIZE=1","-sEXPORT_NAME=createPhaseBridge","-sENVIRONMENT=worker","-sEXPORTED_RUNTIME_METHODS=FS,callMain","-sALLOW_MEMORY_GROWTH=1","-sMAXIMUM_MEMORY=536870912","-sEXIT_RUNTIME=0","-o",str(SITE/"phase.js")])
    r["sha256"]={n:sha(SITE/n) for n in ("rawmocs.js","rawmocs.wasm","gpmc.js","gpmc.wasm","phase.js","phase.wasm")}
    r["bridge_sources"]={str(p.relative_to(ROOT)):sha(p) for p in (bridge,ROOT/"scripts/web/PhaseWeights.hpp")}
    run("browser",[sys.executable,str(HERE/"browser.py"),str(SITE),str(E)],seconds=150)
    assert "W2_SCOPED_PHASE_PARITY_PASS" in (E/"browser.log").read_text()
    r["status"]="W2_SCOPED_PHASE_PARITY_PASS"
try:main()
finally:
    (E/"receipt.json").write_text(json.dumps(r,indent=2)+"\n");print("W2_RESULT",r["status"],flush=True)
