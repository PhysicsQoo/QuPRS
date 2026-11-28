"""W2b: consume admitted candidate, stage original QuPRS BrowserJob, no UI deployment."""
import hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
W,Q=map(lambda x:Path(x).resolve(),sys.argv[1:])
E=W/"evidence";E.mkdir(exist_ok=True)
R={"status":"HOLD","quprs":"2a510a7bba0d5af612c84fc2822cc29bcea45daa","w2a_artifact":15259712439,"gpmc_artifact":15258630253,"timings_seconds":{}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,args,cwd=None,env=None,seconds=240):
    start=time.monotonic()
    print("W2B_STEP_START",name,flush=True)
    try:
        with (E/(name+".log")).open("wb") as f:
            r=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=seconds)
        if r.returncode:
            print((E/(name+".log")).read_text(errors="replace")[-6000:])
            raise RuntimeError(name)
    finally:
        R["timings_seconds"][name]=round(time.monotonic()-start,3)
        print("W2B_STEP_SECONDS",name,R["timings_seconds"][name],flush=True)
        (E/"receipt.json").write_text(json.dumps(R,indent=2)+"\n")
def main():
    assert sha(W/"w2a.zip")=="2cc356553c0da8d2d2170aa7cb50299c3089135ecbe84c71e25b9f207e002b49"
    P=W/"prior";P.mkdir()
    with zipfile.ZipFile(W/"w2a.zip") as z:
        for n in z.namelist():assert not Path(n).is_absolute() and ".." not in Path(n).parts
        z.extractall(P)
    receipts=[p for p in P.rglob("receipt.json") if json.loads(p.read_text()).get("status")=="W2A_SCOPED_PHASE_PARITY_PASS"]
    assert len(receipts)==1
    B=receipts[0].parent;prior=json.loads(receipts[0].read_text());candidate=prior["candidate"]
    D=W/"browser";D.mkdir()
    for n,h in candidate["distribution_sha256"].items():
        p=B/"candidate-distribution"/n;assert sha(p)==h;shutil.copy2(p,D/n)
    for n,h in prior["bridge_sha256"].items():
        p=B/n;assert sha(p)==h;shutil.copy2(p,D/n)
    R["solver_sha256"]=candidate["distribution_sha256"];R["bridge_sha256"]=prior["bridge_sha256"]
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=Q,text=True).strip()==R["quprs"]
    for n,h in prior["original_phase_sha256"].items():assert sha(Q/n)==h
    C=W/"native-candidate";shutil.copytree(B/"candidate-source",C)
    # Original normalized published manifest includes test paths; recover the
    # exact admitted source fixture files from the immutable candidate crate
    # only if needed for builds. Native bin itself uses src exclusively.
    shutil.copy2(B/"candidate-native.Cargo.toml",C/"Cargo.toml")
    shutil.copy2(B/"candidate-native.Cargo.lock",C/"Cargo.lock")
    # Cargo checks explicit test target existence even for bin builds.
    (C/"tests").mkdir(exist_ok=True)
    for n in ("native_stdio.rs","shared_core.rs"):
        (C/"tests"/n).write_text("fn main() {}\n" if n=="native_stdio.rs" else "")
    # These are not tested targets; native bin hash and all source files checked.
    for n,h in candidate["source_hashes"].items():assert sha(C/"src"/n)==h
    run("native-candidate",["cargo","build","--locked","--release","--bin","rawmocs","-j","2"],C,seconds=420)
    # Staged source extension only, original core untouched.
    lib=Q/"rust/web/src/lib.rs"
    R["original_browser_adapter_sha256"]=sha(lib)
    lib.write_text(lib.read_text()+"\n"+(ROOT/"adapter.rs").read_text())
    shutil.copy2(ROOT/"native.rs",Q/"rust/web/examples/w2b_check.rs")
    R["staged_adapter_sha256"]=sha(lib)
    env=dict(os.environ,QUPRS_WEB_SOURCE_REVISION=R["quprs"])
    run("quprs-native",["cargo","test","--locked","--manifest-path","rust/Cargo.toml","-p","quprs-web"],Q,env,seconds=420)
    run("quprs-native-example",["cargo","build","--locked","--manifest-path","rust/Cargo.toml","-p","quprs-web","--release","--example","w2b_check"],Q,env,seconds=420)
    bindgen=shutil.which("wasm-bindgen")
    if not bindgen:
        run("bindgen",["cargo","install","wasm-bindgen-cli","--locked","--version","0.2.100"],seconds=600)
    assert subprocess.check_output(["wasm-bindgen","--version"],text=True).strip()=="wasm-bindgen 0.2.100"
    R["bindgen_cache_hit"]=bindgen is not None
    run("quprs-wasm",["cargo","build","--locked","--manifest-path","rust/Cargo.toml","--release","--target","wasm32-unknown-unknown","-p","quprs-web"],Q,dict(env,RUSTFLAGS="-C link-arg=--max-memory=536870912"),seconds=420)
    run("bindgen-web",["wasm-bindgen",str(Q/"rust/target/wasm32-unknown-unknown/release/quprs_web.wasm"),"--target","web","--out-dir",str(D)],seconds=90)
    # Same-source exact artifact from successful Website Dev Deploy.
    assert sha(W/"gpmc.zip")=="9c3b6aded7fd0d186ad073128ab900b4eba182261774c0f8afb87b09783c00ec"
    G=W/"gpmc-admitted";G.mkdir()
    with zipfile.ZipFile(W/"gpmc.zip") as z:
        for n in z.namelist():assert not Path(n).is_absolute() and ".." not in Path(n).parts
        z.extractall(G)
    manifests=list(G.rglob("PROVENANCE.json"));assert len(manifests)==1
    prov=json.loads(manifests[0].read_text());counter=manifests[0].parent
    assert "93cae8dbf2da967e34fea8b7f40bc8f98362e2e0" in json.dumps(prov)
    assert "4.0.23" in json.dumps(prov)
    for n,h in prov["sha256"].items():
        p=Path(n);assert not p.is_absolute() and ".." not in p.parts
        assert sha(counter/p)==h,n
    for n in ("gpmc.js","gpmc.wasm","native-gpmc"):
        assert n in prov["sha256"],n
        shutil.copy2(counter/n,D/n)
    (D/"native-gpmc").chmod(0o755)
    for n in ("runner.js","output.js"):shutil.copy2(Q/"web/engines"/n,D/n)
    R["gpmc_sha256"]={n:prov["sha256"][n] for n in ("gpmc.js","gpmc.wasm","native-gpmc")}
    print("W2B_REUSED_ADMITTED_GPMC_PASS",flush=True)
    # Native bridge from original exact source; no browser rebuild.
    run("phase-c",["cc","-O2","-c",str(Q/"rust/quprs/native/mpfr_weight_bridge.c"),"-o",str(W/"phase.o")])
    run("phase-native",["c++","-O2","-I"+str(Q/"scripts/web"),str(ROOT/"bridge.cc"),str(W/"phase.o"),"-lmpfr","-lgmpxx","-lgmp","-o",str(W/"phase-native")])
    (D/"index.html").write_text("<!doctype html><title>W2b</title>")
    run("replay",[sys.executable,str(ROOT/"replay.py"),str(D),str(Q/"rust/target/release/examples/w2b_check"),str(D/"native-gpmc"),str(C/"target/release/rawmocs"),str(W/"phase-native"),str(E)],seconds=240)
    assert "W2B_SCOPED_REPLAY_PASS" in (E/"replay.log").read_text()
    R["status"]="W2B_SCOPED_REPLAY_PASS"
try:main()
finally:
    (E/"receipt.json").write_text(json.dumps(R,indent=2)+"\n")
    print("W2B_RESULT",R["status"],flush=True)
sys.exit(0 if R["status"]=="W2B_SCOPED_REPLAY_PASS" else 1)
