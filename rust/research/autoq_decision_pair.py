#!/usr/bin/env python3
"""AQ-R7 decision compatibility, not a matched runtime benchmark."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

PIN = "7eed39ad7ba5615a87c3f532a24f866e08967c12"
BLOBS = {
    "bv03": ("c5d58ba0764d33099613e49aea8a20f174be9ca0","3bcc54d9fc6bf3ca618a67808f2d3da3c3fb86b6","f399669db5b5e8ac469f70de179491e2008694fb"),
    "grover03": ("9c369a362f5e504cd5d4cc64b4b5297a06661b42","5d45f38067d9e95ff0afe997c5f175cc1082e7e4","79604029953261a0cd419b9ec932b055dd9ea0c8"),
    "mogrover03": ("286d24f8d0e43e07535658526682566d4897823d","413ee90158043d0e17dc9285261b05de694793d1","4a5cc0a405f2c67172de5a7fe2ca16fcfac77bdc"),
}
SHAPES = {"bv03": (4,11), "grover03": (5,52), "mogrover03": (8,62)}
VARIANTS = ("source","relative-mutant","global-sign")
MODES = ("rr","wmc","hybrid")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def replace_once(s,a,b):
    if s.count(a)!=1:
        raise ValueError("unexpected mutation anchor: "+a)
    return s.replace(a,b)

def mutant(family,source,variant):
    if variant=="source":
        return source
    if family=="bv03":
        return replace_once(source,b"|1011>",b"|0011>") if variant=="relative-mutant" else replace_once(source,b"c1 := 1\n",b"c1 := -1\n")
    s=replace_once(source,b"aH := 11 /",b"aH := -11 /")
    return s if variant=="relative-mutant" else replace_once(s,b"aL := -1 /",b"aL := 1 /")

def aggregate(rows):
    if any(r["verdict"]=="REFUTED" for r in rows):
        return "REFUTED"
    if all(r["verdict"]=="PROVED" for r in rows):
        return "PROVED"
    return "UNKNOWN"

def classify(stdout,stderr,rc,shape):
    if rc in (124,137):
        return "TIMEOUT_OR_KILL"
    if rc!=0 or "[ERROR]" in stdout+stderr:
        return "ERROR"
    matches=re.findall(r"The quantum program has \[(\d+)\] qubits and \[(\d+)\] gates\. The verification process \[(OK|failed)\] in \[([^\]\r\n]+)\] with \[(\d+)MB\] memory usage\.",stdout+"\n"+stderr)
    if len(matches)!=1 or tuple(map(int,matches[0][:2]))!=shape:
        return "ERROR"
    return "PROVED" if matches[0][2]=="OK" else "REFUTED"

def main():
    exe,fixtures,log,out=map(lambda s:pathlib.Path(s).resolve(),sys.argv[1:5])
    out.mkdir(parents=True,exist_ok=True)
    version=subprocess.run(["timeout","--kill-after=2s","10s",str(exe),"-v"],capture_output=True,text=True,check=True)
    assert re.findall(r"\b[0-9a-f]{40}\b",version.stdout+"\n"+version.stderr)==[PIN], "AutoQ binary pin mismatch"
    source_hash=sha(exe.read_bytes())
    records=[]
    for line in log.read_text().splitlines():
        if line.startswith("AQ_HSL_P0_ARM "):
            records.append(json.loads(line.removeprefix("AQ_HSL_P0_ARM ")))
    assert len(records)==90 and len({(r["case"],r["variant"],r["mode"]) for r in records})==90
    assert {r["case"] for r in records}=={"bv03","grover03",*(f"mogrover03-label{i}" for i in range(8))}
    summary=[]
    for family,hashes in BLOBS.items():
        files=[fixtures/f"aq-source-{family}-{suffix}" for suffix in ("pre.hsl","post.hsl","circuit.qasm")]
        pre,post,circuit=[p.read_bytes() for p in files]
        assert tuple(map(blob,(pre,post,circuit)))==hashes
        for variant in VARIANTS:
            target=out/f"{family}-{variant}.hsl"
            target.write_bytes(mutant(family,post,variant))
            key=f"{family}-{variant}"
            argv=[str(exe),"ver",str(files[0]),str(files[2]),str(target)]
            timefile=out/f"{key}.resource.txt"
            start=time.monotonic()
            proc=subprocess.run(["/usr/bin/time","-f","wall_s=%e\nmax_rss_kib=%M","-o",str(timefile),
                                 "timeout","--kill-after=2s","10s",*argv],capture_output=True,text=True,errors="replace")
            wall=time.monotonic()-start
            (out/f"{key}.stdout").write_text(proc.stdout)
            (out/f"{key}.stderr").write_text(proc.stderr)
            actual=classify(proc.stdout,proc.stderr,proc.returncode,SHAPES[family])
            native={}
            for mode in MODES:
                group=[r for r in records if r["case"].split("-label")[0]==family and r["variant"]==variant and r["mode"]==mode]
                assert len(group)==(8 if family=="mogrover03" else 1)
                native[mode]=aggregate(group)
            expected="REFUTED" if variant=="relative-mutant" else "PROVED"
            definite=actual in ("PROVED","REFUTED")
            row=dict(family=family,variant=variant,autoq=actual,native=native,expected=expected,
                     autoq_binary_sha256=source_hash,autoq_pin=PIN,source_blobs=hashes,
                     mutant_sha256=sha(target.read_bytes()),returncode=proc.returncode,wall_s=wall,
                     resource=timefile.read_text() if timefile.exists() else None,
                     verdict_agreement=definite and actual==native["wmc"]==native["hybrid"]==expected)
            summary.append(row)
            print("AQ_AUTOQ_PAIR "+json.dumps(row),flush=True)
    receipt=dict(scope="decision compatibility only; shared native preparation and per-label budgets prevent runtime comparison",
                 cases=len(summary),agreed=sum(r["verdict_agreement"] for r in summary),rows=summary)
    (out/"summary.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("AQ_AUTOQ_PAIR_SUMMARY "+json.dumps({k:v for k,v in receipt.items() if k!="rows"}),flush=True)
    # Failure remains a diagnostic failure, never interpreted as a refutation.
    if receipt["agreed"]!=9:
        raise SystemExit("AQ-R7 compatibility incomplete or mismatch")
    if len(sys.argv)==7:
        ghz_pair(exe,pathlib.Path(sys.argv[5]).resolve(),pathlib.Path(sys.argv[6]).resolve(),out,source_hash)
    elif len(sys.argv)!=5:
        raise SystemExit("expected optional pinned source root and property log")


GHZ_BLOBS = {
    3: ("01a7d8579b1a6079fde76991cd3af5c4c7b3952c","ba24ec21eef82940d34ca90822aedc3650293ac5","f1f040ec26312825a56db1f0ac735f81cad5dd9f"),
    4: ("f735cf6987e054b53d2682edb43abb00463182e9","b47769284fba9e93c8de087848c2b5188a418235","34b355874a3658e45307c44529473a93258e5bd3"),
    5: ("b67b488134a71aabb55f8277d3e91c52f2fcd014","f4122a5fffab2806442e925a2d768f28ec26fa40","ad462048e1513e80d53c397d215ad1e2dafe6a3e"),
    8: ("a712713768d9605514ff30208785b5bfdbffad06","7a2693425da63470feca65ca62d93e9d19d3a461","f2c88eaf5779c0bd340a501514432290369fdf7f"),
}

def ghz_pair(exe, source_root, native_log, out, binary_hash):
    """Source-locked decision comparison; never infer speedup."""
    markers = {}
    for line in native_log.read_text().splitlines():
        if line.startswith("AQ_GHZALL_SYMBOLIC "):
            row = dict(token.split("=", 1) for token in line.split()[1:])
            n = int(row["n"])
            assert n not in markers
            assert int(row["matched"]) == 2**n and int(row["full_pairs"]) == 4**n
            assert int(row["symbolic_pairs"]) == 0 and int(row["plus_matches"]) == 2**(n-1)
            assert all(row[k] == "true" for k in ("plus_only_refuted", "dense_oracle", "raw_residual_agree"))
            markers[n] = row
    assert set(markers) == set(GHZ_BLOBS), "missing native GHZall receipts"
    rows = []
    for n, hashes in GHZ_BLOBS.items():
        folder = source_root / "benchmarks" / "all" / "GHZall" / f"{n:03d}"
        pre, post, circuit = (folder / name for name in ("pre.hsl","post.hsl","circuit.qasm"))
        original = post.read_bytes()
        assert tuple(blob(p.read_bytes()) for p in (pre,post,circuit)) == hashes
        parts = original.split(" ∪\n".encode())
        assert len(parts) == 2 and b"cn |1i'>" in parts[1]
        plus_only = replace_once(parts[0]+b"\n",b"cn := -1/sqrt2\n",b"")
        for variant, data, expected in (("source",original,"PROVED"),
                                        ("plus-only",plus_only,"REFUTED")):
            key=f"ghzall{n:03d}-{variant}"
            target=out/f"{key}.hsl"
            target.write_bytes(data)
            timing=out/f"{key}.resource.txt"
            start=time.monotonic()
            proc=subprocess.run(["/usr/bin/time","-f","wall_s=%e\nmax_rss_kib=%M","-o",str(timing),
                                 "timeout","--kill-after=2s","10s",str(exe),"ver",str(pre),str(circuit),str(target)],
                                capture_output=True,text=True,errors="replace")
            (out/f"{key}.stdout").write_text(proc.stdout)
            (out/f"{key}.stderr").write_text(proc.stderr)
            actual=classify(proc.stdout,proc.stderr,proc.returncode,(n,n))
            native = "PROVED" if variant=="source" and int(markers[n]["matched"])==2**n else (
                "REFUTED" if variant=="plus-only" and markers[n]["plus_only_refuted"]=="true" else "UNKNOWN")
            row=dict(n=n,variant=variant,autoq=actual,native=native,expected=expected,
                     autoq_pin=PIN,autoq_binary_sha256=binary_hash,source_blobs=hashes,
                     post_sha256=sha(data),returncode=proc.returncode,
                     wall_s=time.monotonic()-start,resource=timing.read_text() if timing.exists() else None,
                     verdict_agreement=actual==native==expected)
            rows.append(row)
            print("AQ_GHZALL_AUTOQ_PAIR "+json.dumps(row),flush=True)
    receipt=dict(scope="decision compatibility; no matched runtime claim",cases=len(rows),
                 agreed=sum(r["verdict_agreement"] for r in rows),rows=rows)
    (out/"ghzall-summary.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("AQ_GHZALL_AUTOQ_SUMMARY "+json.dumps({k:v for k,v in receipt.items() if k!="rows"}),flush=True)
    assert receipt["agreed"]==8, "GHZall decision compatibility incomplete"

if __name__=="__main__":
    main()
