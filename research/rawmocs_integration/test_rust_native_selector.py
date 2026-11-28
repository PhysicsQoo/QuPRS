"""Public PyO3 and Python wrapper native selection; short, explicit opt-in."""
from unittest.mock import patch
import json
import os
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from QuPRS import check_equivalence, _pathsum_rust
import QuPRS.utils
def forbidden(*a,**k):raise AssertionError("native solver executable resolution")
os.environ["QUPRS_STAGE_LEDGER"]="1"
id=QuantumCircuit(2)
eq=QuantumCircuit(2);eq.h(0);eq.t(0);eq.tdg(0);eq.h(0)
neq=QuantumCircuit(2);neq.h(0)
rows=[]
for name,c,expected in (("eq",eq,"equivalent"),("neq",neq,"not_equivalent")):
    for method in ("wmc_only","hybrid"):
        baseline=check_equivalence(id,c,backend="rust",tool_name="gpmc",method=method,timeout=10)
        for safe in (False,True):
            with patch.object(QuPRS.utils,"WMC",forbidden),patch.object(QuPRS.utils,"get_ganak_path",forbidden):
                r=check_equivalence(id,c,backend="rust",tool_name="rawmocs_rust_native",method=method,timeout=10,safe_mode=safe)
            assert r.equivalent==baseline.equivalent==expected,(name,method,safe,r.equivalent)
            assert r.wmc_solver_invoked==baseline.wmc_solver_invoked
            rows.append(dict(case=name,method=method,safe_mode=safe,verdict=r.equivalent,invoked=r.wmc_solver_invoked))
        d=_pathsum_rust.check_equivalence(qasm2.dumps(id),qasm2.dumps(c),tool_name="rawmocs_rust_native",method=method,timeout=10)
        ledger=d["stage_ledger"]
        assert ledger["solver_child_spawns"]==0
        assert ledger["stage_calls"].get("cnf_file_write",0)==0
        rows[-1]["direct_ffi_ledger"]=ledger
out=Path(os.environ["R3B_EVIDENCE"])
(out/"public-api.json").write_text(json.dumps({"status":"PASS","rows":rows},indent=2)+"\n")
print("R3B_PYO3_NATIVE_PASS cases=8 ffi_ledgers=4")
