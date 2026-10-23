"""Source-pinned Python-only verification. Invoked as a clean subprocess."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def pair(name, paper_root):
    from qiskit import QuantumCircuit, qasm2
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    if name == "identical_empty":
        pass
    elif name == "identical_h":
        a.h(0)
        b.h(0)
    elif name == "hh_identity":
        a.h(0)
        a.h(0)
    elif name == "identity_x":
        b.x(0)
    elif name == "identity_rz_001":
        b.rz(0.001, 0)
    elif name == "identity_rz_01":
        b.rz(0.1, 0)
    elif name == "grover4_transpiled":
        base = Path(paper_root) / "benchmarks/MQTBench"
        p1 = base / "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
        p2 = base / "h,ry,rz,cx/grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
        raw1, raw2 = p1.read_bytes(), p2.read_bytes()
        return qasm2.loads(raw1.decode()), qasm2.loads(raw2.decode()), raw1, raw2
    else:
        raise ValueError("Unsupported fixture: " + name)
    return a, b, qasm2.dumps(a).encode(), qasm2.dumps(b).encode()

def main():
    ap = argparse.ArgumentParser()
    for opt in ("label", "source", "paper-root", "case", "method", "output"):
        ap.add_argument("--" + opt, required=True)
    args = ap.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    from QuPRS import check_equivalence
    from QuPRS.interface import ps2wmc
    from QuPRS.utils import WMC
    import QuPRS
    import qiskit
    if Path(QuPRS.__file__).resolve() != (Path(args.source)/"src/QuPRS/__init__.py").resolve():
        raise RuntimeError("QuPRS imported from wrong source tree: " + QuPRS.__file__)
    c1, c2, q1, q2 = pair(args.case, args.paper_root)
    cm = WMC("gpmc") if args.label == "dev" else WMC()
    with cm as binary:
        exe = Path(binary)
        gpmc = {"sha256": digest(exe.read_bytes()), "filename": exe.name,
                "executable": os.access(exe, os.X_OK)}
    trace = {"solver_calls": 0, "encoder_calls": 0,
             "solver_count": None, "cnf_sha256": None, "cnf_bytes": None}
    original_run = ps2wmc.run_wmc
    original_encode = ps2wmc.to_DIMACS
    def observed_run(*a, **kw):
        trace["solver_calls"] += 1
        value = original_run(*a, **kw)
        trace["solver_count"] = {"real":float(value[0]), "imag":float(value[1])}
        return value
    def observed_encode(*a, **kw):
        trace["encoder_calls"] += 1
        retval = original_encode(*a, **kw)
        filepath = kw.get("filename", a[1] if len(a)>1 else None)
        if filepath is not None and Path(filepath).is_file():
            data = Path(filepath).read_bytes()
            trace["cnf_sha256"] = digest(data)
            trace["cnf_bytes"] = len(data)
            if len(data) <= 300000:
                (output.parent/(output.stem+".cnf")).write_bytes(data)
        return retval
    ps2wmc.run_wmc, ps2wmc.to_DIMACS = observed_run, observed_encode
    try:
        kw = dict(method=args.method, timeout=30,
                  strategy="Proportional" if args.case=="grover4_transpiled" else "Naive")
        if args.label=="dev":
            kw.update(tool_name="gpmc", backend="python", safe_mode=False)
        result = check_equivalence(c1, c2, **kw)
        error, status = None, "RETURNED"
    except Exception as exc:
        result, status = None, "ERROR"
        error = {"type":type(exc).__name__, "message":str(exc),
                 "traceback":traceback.format_exc()}
    finally:
        ps2wmc.run_wmc, ps2wmc.to_DIMACS = original_run, original_encode
    info = {
        "source_label":args.label,"case":args.case,"method":args.method,
        "source_root":str(Path(args.source).resolve()),
        "package_source":str(Path(QuPRS.__file__).resolve()),
        "qiskit_version":qiskit.__version__,
        "gpmc":gpmc,"qasm_sha256":[digest(q1),digest(q2)],
        "qubits":c1.num_qubits,"gate_counts":[len(c1.data),len(c2.data)],
        "status":status,"error":error,"inspection":trace,
        "verdict":getattr(result,"equivalent",None),
        "expected_log2":getattr(result,"expect",None),
        "reported_log_wmc":getattr(result,"log_wmc",None),
        "wmc_executed":trace["solver_calls"]>0,
        "reduction_counts":(result.Statistics.get_reduction_counts()
                            if result is not None and hasattr(result.Statistics,"get_reduction_counts")
                            else None),
        "final_pathsum_excerpt":(str(result.final_pathsum)[:800] if result is not None else None),
        "observational_scope":"Real source code in selected version, real GPMC, no verdict mocks",
    }
    output.write_text(json.dumps(info,indent=2,sort_keys=True,default=str)+"\n")
    print(json.dumps({"source":args.label,"case":args.case,"method":args.method,
                      "status":status,"verdict":info["verdict"],
                      "solver_calls":trace["solver_calls"]}),flush=True)
    return 0 if status=="RETURNED" else 2

if __name__=="__main__":
    raise SystemExit(main())
