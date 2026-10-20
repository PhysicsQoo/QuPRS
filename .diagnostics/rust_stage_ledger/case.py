"""Opt-in raw Rust FFI diagnostic per isolated process."""
import argparse, hashlib, json, os, platform, time
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

def get_pair(case, root):
    if case == "qaoa7":
        name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
        a = qasm2.load(str(root / name))
        b = qasm2.load(str(root / "h,ry,rz,cx" / name))
    else:
        a = QuantumCircuit(4)
        a.h(0)
        for i in range(3):
            a.cx(i, i+1)
        b = a.copy()
        b.z(0)
        b.z(0)
    strings = [qasm2.dumps(x) for x in (a,b)]
    oracle = "equivalent" if Operator(a) == Operator(b) else ("equivalent*" if Operator(a).equiv(Operator(b)) else "not_equivalent")
    return strings, oracle

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=["qaoa7", "ghz4"])
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    from QuPRS import _pathsum_rust
    from QuPRS.utils import WMC
    if args.profile:
        os.environ["QUPRS_STAGE_LEDGER"] = "1"
    else:
        os.environ.pop("QUPRS_STAGE_LEDGER", None)
    qasm, oracle = get_pair(args.case, Path("benchmarks/MQTBench"))
    with WMC("gpmc") as binary:
        original = os.environ.get("QUPRS_GPMC_PATH")
        os.environ["QUPRS_GPMC_PATH"] = str(binary)
        try:
            start = time.perf_counter()
            raw = _pathsum_rust.check_equivalence(qasm[0], qasm[1], method="hybrid" if args.case == "qaoa7" else "wmc_only", strategy="Proportional", tool_name="gpmc", timeout=75)
            wall = time.perf_counter() - start
        finally:
            if original is None: os.environ.pop("QUPRS_GPMC_PATH", None)
            else: os.environ["QUPRS_GPMC_PATH"] = original
    status = {"Equivalent":"equivalent","Equivalent (Up to Global Phase)":"equivalent*", "Not Equivalent":"not_equivalent"}.get(raw["status"],raw["status"])
    assert status == oracle, (status,oracle)
    stage = raw.get("stage_ledger")
    assert (stage is not None) == args.profile
    if stage is not None:
        assert stage["solver_child_spawns"] > 0, "No actual native solver launch"
        assert not stage["has_stage_overlap"]
        assert abs(stage["closure_error_seconds"]) < 1e-6
        assert abs(sum(stage["exclusive_seconds"].values()) - stage["total_native_wall_seconds"]) < 1e-6
        for name in ("cnf_encode","cnf_serialize","cnf_file_write","solver_supervision","classification"):
            assert stage["stage_calls"].get(name,0) > 0, name
        if args.case == "qaoa7":
            assert stage["stage_calls"].get("reduction",0) > 0
    result={"case":args.case,"profile":args.profile,"status":status,"oracle":oracle,"qasm_sha256":[hashlib.sha256(s.encode()).hexdigest() for s in qasm],"wrapper_wall_seconds":wall,"native":{k:raw.get(k) for k in ("status","verification_time_sec","pathsum_time_sec","wmc_time_sec","wmc_dimacs_time_sec","wmc_solver_time_sec","stage_ledger")},"environment":{"python":platform.python_version(),"platform":platform.platform()}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"case":args.case,"profile":args.profile,"status":status,"native":result["native"]["verification_time_sec"],"spawn":stage["solver_child_spawns"] if stage else None}),flush=True)

if __name__=="__main__":
    main()
