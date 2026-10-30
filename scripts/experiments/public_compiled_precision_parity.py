"""Public Python/Rust sensitivity probe against independent full-unitary oracles.

A result inconsistent with the oracle is a RED gate, even when GPMC exits 0.
The exact same original and transpiled QASM bytes are supplied to both backends.
"""
import argparse
import json
from pathlib import Path
from QuPRS import check_equivalence

NAMES={
    "grover4":"grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    "qaoa7":"qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
}
ORACLE_DIST={"grover4":2.06698031233642e-15,"qaoa7":2.70265561422122e-15}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=NAMES,required=True)
    parser.add_argument("--backend",choices=("python","rust"),required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]/"benchmarks/MQTBench"
    name=NAMES[args.case]
    src=(root/name).read_text()
    comp=(root/"h,ry,rz,cx"/name).read_text()
    obj=check_equivalence(src,comp,backend=args.backend,
        method="wmc_only",strategy="Difference",tool_name="gpmc",
        approximate_distance_tolerance=1e-8,timeout=50)
    status=obj.equivalent
    assert status in ("equivalent","equivalent*","not_equivalent","unknown"),status
    calls=bool(obj.wmc_solver_invoked)
    good=status in ("equivalent","equivalent*")
    report={"case":args.case,"backend":args.backend,"status":status,
        "oracle_distance":ORACLE_DIST[args.case],"epsilon":1e-8,
        "scientifically_consistent":good,"solver_invoked":calls,
        "numerical_reason":getattr(obj,"wmc_precision_reason",None),
        "printed_verdict":getattr(obj,"wmc_printed_verdict",None)}
    args.out.write_text(json.dumps(report,indent=2,default=str)+"\n")
    print("PUBLIC_COMPILED_CHECK case={} backend={} status={} valid={} one_solver={}".format(
        args.case,args.backend,status,good,calls),flush=True)
    assert calls
    if not good:raise SystemExit(2)
if __name__=="__main__":
    main()
