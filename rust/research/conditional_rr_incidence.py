"""Source-locked CRR-0 pilot; each original pair receives a process timeout."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
IDS = ("grover-noancilla_4", "qwalk-noancilla_3", "qwalk-noancilla_4",
       "qpeexact_8", "wstate_4", "qnn_4", "vqe_4", "ghz_32")
manifest = json.loads((ROOT / "docs/development/paper-corpus-manifest.json").read_text())
cases = {x["id"]: x for x in manifest["cohorts"]["table2_mqt"]["cases"]}
failed = False
for case_id in IDS:
    case = cases[case_id]
    paths = {}
    hashes = {}
    for side in ("source", "transpiled"):
        entry = case[side]
        p = ROOT / entry["path"]
        data = p.read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        assert blob == entry["git_blob_sha1"], (case_id, side, blob)
        paths[side] = str(p)
        hashes[side] = hashlib.sha256(data).hexdigest()
    env = dict(os.environ, CRR_CASE=case_id, CRR_SOURCE=paths["source"],
               CRR_TARGET=paths["transpiled"])
    cmd = ["timeout", "--kill-after=3s", "35s", "cargo", "test", "--locked",
           "--manifest-path", "rust/Cargo.toml", "-p", "quprs",
           "--test", "conditional_rr_experiment", "native_eq_residual_incidence",
           "--", "--exact", "--nocapture"]
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    records = [l for l in run.stdout.splitlines() if l.startswith("CRR_")]
    status = "COMPLETE" if run.returncode == 0 and sum(l.startswith("CRR_BASE ") for l in records) == 1 and sum(l.startswith(("CRR_INCIDENCE ", "CRR_SKIP ")) for l in records) == 1 else (
        "TIMEOUT" if run.returncode in (124, 137) else "ERROR")
    failed |= status == "ERROR"
    print(json.dumps(dict(case=case_id, status=status, returncode=run.returncode,
                          sha256=hashes, records=records,
                          stderr=run.stderr[-3000:], stdout_tail=run.stdout[-1500:])),
          flush=True)
if failed:
    raise SystemExit(1)
