#!/usr/bin/env python3
"""TACAS26 Qiskit 1.4.2 versus 2.6.1 fixed-input transpiler fidelity."""
import argparse
import csv
import hashlib
import json
import math
import os
import platform
from importlib.metadata import PackageNotFoundError, version as installed_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASIS = ["h", "ry", "rz", "cx"]
LEVELS = (0, 3)
SEED = 42
CASE_IDS = {
    "grover4": "grover-noancilla_4",
    "qnn8": "qnn_8",
    "qpeinexact8": "qpeinexact_8",
    "qaoa9": "qaoa_9",
    "qft16": "qft_16",
    "vqe16": "vqe_16",
    "qft20": "qft_20",
    "qft22": "qft_22",
    "qpeexact20": "qpeexact_20",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(src, target, np, Operator, Statevector):
    n = src.num_qubits
    if n <= 8:
        a, b = Operator(src).data, Operator(target).data
        inner = complex(np.vdot(a, b) / (2 ** n))
        phase = inner/abs(inner) if inner else 1
        f = float(np.linalg.norm(a-b/phase) / math.sqrt(2**n))
        return {"metric": f * math.sqrt(max(0.,1-f*f/4)),
                "metric_kind": "float_projective_operator",
                "aligned_frobenius":f}
    samples = []
    for name, psi in (("zero", "0"*n),("uniform_plus","+"*n)):
        s = Statevector.from_label(psi)
        a, b = s.evolve(src).data, s.evolve(target).data
        inner = complex(np.vdot(a,b))
        phase = inner/abs(inner) if inner else 1
        samples.append({"input":name,
                        "aligned_l2":float(np.linalg.norm(a-b/phase)),
                        "overlap_abs":float(abs(inner))})
    return {"metric":max(s["aligned_l2"] for s in samples),
            "metric_kind":"two_sample_statevector_max_not_projective",
            "samples":samples}


def run(version, output):
    import numpy as np
    import qiskit
    from qiskit import qasm2, transpile
    from qiskit.quantum_info import Operator, Statevector
    if qiskit.__version__ != version:
        raise RuntimeError("Installed Qiskit is not pinned exact version")
    corpus=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    pairs={x["id"]:x for x in corpus["cohorts"]["table2_mqt"]["cases"]}
    records=[]
    for short, key in CASE_IDS.items():
        item=pairs[key]
        a=(ROOT/item["source"]["path"]).read_bytes()
        b=(ROOT/item["transpiled"]["path"]).read_bytes()
        def git_blob(data):
            return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
        if (git_blob(a)!=item["source"]["git_blob_sha1"] or
            git_blob(b)!=item["transpiled"]["git_blob_sha1"]):
            raise RuntimeError("Paper QASM Git blob mismatch")
        original=qasm2.loads(a.decode()).remove_final_measurements(inplace=False)
        historical=qasm2.loads(b.decode())
        if original.num_qubits!=historical.num_qubits:
            raise RuntimeError("Qubit count mismatch")
        if any(original.count_ops().get(x,0) for x in ("measure","reset")):
            raise RuntimeError("Non-terminal original measurement not supported")
        baseline=compare(original,historical,np,Operator,Statevector)
        r={"case":short,"qubits":original.num_qubits,
           "original_file":item["source"]["path"],
           "historical_transpiled_file":item["transpiled"]["path"],
           "original_sha256":sha(a),"historic_sha256":sha(b),
           "original_gates":original.size(),"historic_gates":historical.size(),
           "historical_saved":baseline,"transpiles":[]}
        for level in LEVELS:
            try:
                qc=transpile(original,basis_gates=BASIS,optimization_level=level,
                            seed_transpiler=SEED,approximation_degree=1.0)
                compiled=compare(original,qc,np,Operator,Statevector)
                packed=qasm2.dumps(qc)
                # Save the actual bytes passed to future QuPRS v0.9.1/v0.14.0.
                # A SHA256 alone cannot reconstruct the compiled circuit.
                qasm2_relative=Path("generated-qasm") / ("qiskit-"+version) / (short+"-opt"+str(level)+".qasm")
                qasm2_path=output.parent / qasm2_relative
                qasm2_path.parent.mkdir(parents=True,exist_ok=True)
                qasm2_path.write_bytes(packed.encode("utf-8"))
                serial=compare(original,qasm2.loads(packed),np,Operator,Statevector)
                r["transpiles"].append({
                    "level":level,"status":"OK",
                    "compiled_in_memory":compiled,"serialized":serial,
                    "qasm2_sha256":sha(packed.encode("utf-8")),
                    "qasm2_file":qasm2_relative.as_posix(),
                    "gates":qc.size(),"depth":qc.depth(),
                    "global_phase":float(qc.global_phase)})
            except Exception as ex:
                r["transpiles"].append({
                    "level":level,"status":"ERROR",
                    "error_type":type(ex).__name__,
                    "error":str(ex)[:300]})
        records.append(r)
        print("QISKIT_VERSION_FIDELITY",version,short,
              baseline["metric"],
              [(x["level"],x.get("serialized",{}).get("metric"))
               for x in r["transpiles"]],flush=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    dependencies = {}
    for package in ("qiskit", "numpy", "rustworkx", "scipy", "sympy"):
        try:
            dependencies[package] = installed_version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    output.write_text(json.dumps({
        "schema":"tacas26-qiskit-version-fidelity-v2",
        "qiskit_version":version,"numpy_version":np.__version__,
        "python_version":platform.python_version(),
        "platform":platform.platform(),
        "runner_architecture":platform.machine(),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "github_source_sha":os.getenv("GITHUB_SHA"),
        "installed_dependencies":dependencies,
        "basis":BASIS,"levels":LEVELS,"seed":SEED,
        "approximation_degree":1.0,"source_sha":corpus["reference_git_commit"],
        "historical_transpile_configuration":"NOT_DOCUMENTED_OR_ASSUMED",
        "numerical_certified":False,"performance_certified":False,
        "cases":records},indent=2,sort_keys=True)+"\n")
    successful=sum(z["status"]=="OK" for r in records for z in r["transpiles"])
    if successful<14: raise RuntimeError("Too few successful transpiler results")


def aggregate(old,new,output):
    a,b=(json.loads(p.read_text()) for p in (old,new))
    if (a["qiskit_version"],b["qiskit_version"])!=("1.4.2","2.6.1"):
        raise RuntimeError("Expected exact historical/latest comparison")
    for k in ("basis","levels","seed","approximation_degree","source_sha"):
        if a[k]!=b[k]: raise RuntimeError("Mismatched comparison configuration: "+k)
    first={x["case"]:x for x in a["cases"]}
    second={x["case"]:x for x in b["cases"]}
    if set(first)!=set(second) or set(first)!=set(CASE_IDS):
        raise RuntimeError("Missing cross-version benchmark")
    results=[]
    for case in CASE_IDS:
        x,y=first[case],second[case]
        if (x["original_sha256"]!=y["original_sha256"] or
            x["historic_sha256"]!=y["historic_sha256"]):
            raise RuntimeError("Not the same source-pinned QASM")
        for i in range(len(LEVELS)):
            s,t=x["transpiles"][i],y["transpiles"][i]
            row={"case":case,"qubits":x["qubits"],"level":LEVELS[i],
                 "kind":x["historical_saved"]["metric_kind"],
                 "historical_saved":x["historical_saved"]["metric"],
                 "status":"OK" if s["status"]==t["status"]=="OK" else "ERROR"}
            if row["status"]=="OK":
                u,v=s["serialized"]["metric"],t["serialized"]["metric"]
                row.update({"qiskit142":u,"qiskit261":v,"difference":v-u,
                    "qiskit142_gates":s["gates"],"qiskit261_gates":t["gates"],
                    "qasm2_vs_memory142":u-s["compiled_in_memory"]["metric"],
                    "qasm2_vs_memory261":v-t["compiled_in_memory"]["metric"]})
                floor=1e-12 if x["qubits"]<=8 else 1e-11
                if max(u,v)<=floor:
                    row["comparison"]="BOTH_AT_FLOAT_NOISE_FLOOR"
                elif v<u-max(floor,u*1e-6):
                    row["comparison"]="LATEST_SMALLER"
                elif v>u+max(floor,u*1e-6):
                    row["comparison"]="LATEST_LARGER"
                else:row["comparison"]="COMPARABLE_WITHIN_THRESHOLD"
            results.append(row)
    output.mkdir(parents=True,exist_ok=True)
    (output/"comparison.json").write_text(json.dumps({
        "source_versions":["1.4.2","2.6.1"],
        "fixed_config":{"basis":BASIS,"seed":SEED,"levels":LEVELS,
                        "approximation_degree":1.0},
        "numerical_certified":False,"performance_certified":False,
        "rows":results},indent=2,sort_keys=True)+"\n")
    fields=["case","qubits","level","kind","historical_saved","status",
            "qiskit142","qiskit261","difference","comparison",
            "qiskit142_gates","qiskit261_gates"]
    with (output/"comparison.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader();w.writerows(results)
    table=["| Case | Qubit | Opt | Saved historic | Qiskit 1.4.2 | Qiskit 2.6.1 | Conclusion |",
           "|---|---:|---:|---:|---:|---:|---|"]
    for r in results:
        if r["status"]=="OK":
            fmt=lambda v:format(v,".7g")
            table.append("| "+r["case"]+" | "+str(r["qubits"])+" | "+
                         str(r["level"])+" | "+fmt(r["historical_saved"])+" | "+
                         fmt(r["qiskit142"])+" | "+fmt(r["qiskit261"])+" | "+
                         r["comparison"]+" |")
        else:
            table.append("| "+r["case"]+" | "+str(r["qubits"])+" | "+
                         str(r["level"])+" | - | - | - | ERROR |")
    text=[
        "# TACAS26 Qiskit 1.4.2 versus 2.6.1 transpiler numerical fidelity",
        "",
        "Source QASM: original paper MQTBench inputs, fixed Git blobs and SHA256.",
        "Each Qiskit version receives the same source, terminal measurements",
        "removed, same target H/Ry/Rz/CX basis, same seed 42, optimization",
        "levels 0 and 3, approximation degree 1.0. Each result is QASM2",
        "serialized and reloaded before comparison with original.",
        "The original paper's saved transpiled QASM is a third comparator",
        "with UNKNOWN original optimization settings.",
        "",
        "Qubits 1-8: full operator projective trace distance from stabilized",
        "phase-aligned normalized Frobenius. Qubits 9-22: maximum of the",
        "phase-aligned state distances for |0> and |+> inputs; these are NOT",
        "the trace-based projective operator distance and do NOT bound it.",
        "Float64 computation does NOT certify mathematically exact equality.",
        "",*table,"",
        "No performance timings are claimed. CodSpeed required for timing.",
        "Graphstate64 intentionally excluded due to simulation resource",
        "constraints. The historical source QASM is NOT rewritten.",
        "Full diagnostics in qiskit142.json, qiskit261.json and comparison.json."
    ]
    (output/"README.md").write_text("\n".join(text)+"\n")
    print("QISKIT_VERSION_FIDELITY_SUMMARY",{
        k:sum(r.get("comparison")==k for r in results)
        for k in ("LATEST_SMALLER","LATEST_LARGER","BOTH_AT_FLOAT_NOISE_FLOOR",
                  "COMPARABLE_WITHIN_THRESHOLD")},flush=True)
    if sum(r["status"]=="OK" for r in results)<14:
        raise RuntimeError("Missing cross-version evidence")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    x=sub.add_parser("run")
    x.add_argument("--version",choices=["1.4.2","2.6.1"],required=True)
    x.add_argument("--output",type=Path,required=True)
    y=sub.add_parser("aggregate")
    y.add_argument("--old",type=Path,required=True)
    y.add_argument("--new",type=Path,required=True)
    y.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.mode=="run":run(args.version,args.output)
    else:aggregate(args.old,args.new,args.output)
