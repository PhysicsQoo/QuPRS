"""Bounded first P4 experiment on actual QuPRS run_wmc and public Python API."""
import hashlib
import json
import os
from pathlib import Path
from fractions import Fraction
import subprocess
import time
from unittest.mock import patch

import rawmocs
from qiskit import QuantumCircuit
from QuPRS import check_equivalence
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process
from QuPRS.utils.solver_adapter import get_solver_adapter, execute_solver, SolverExecutionError
from rawmocs_quprs import registered_rawmocs
from native_adapter import registered_native

ROOT = Path(".p4-native-evidence").resolve()
RAW = Path(".rawmocs-candidate/crates/rawmocs-cli/target/release/rawmocs").resolve()
GPMC = Path(".gpmc/build/gpmc").resolve()
FIXTURES = {
    "complex": ("p cnf 1 1\nc t wmc\nc p weight 1 0.1 -0.3 0\n1 0\n", True),
    "sat-zero": ("p cnf 1 0\nc t wmc\nc p weight 1 -1 0 0\nc p weight -1 1 0 0\n", True),
    "unsat": ("p cnf 1 2\nc t wmc\n1 0\n-1 0\n", False),
}
def forbidden(*args, **kwargs):
    raise AssertionError("Native adapter invoked subprocess or resource resolver")

def main():
    ROOT.mkdir(exist_ok=True)
    os.environ["QUPRS_GPMC_PATH"] = str(GPMC)
    default = get_solver_adapter("gpmc")
    report = {"status":"IN_PROGRESS", "fixtures":[], "e2e":[],
              "quprs_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
              "rawmocs_sha":subprocess.check_output(["git","-C",".rawmocs-candidate","rev-parse","HEAD"],text=True).strip()}
    def save():
        (ROOT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        for name,(source,sat) in FIXTURES.items():
            path=ROOT/(name+".cnf")
            path.write_text(source)
            for digits in (30,60,100,130):
                captures = {}
                original = solver_process.run
                def observed(command, timeout):
                    result = original(command, timeout)
                    arm = "rawmocs" if Path(command[0]).resolve() == RAW else "gpmc"
                    assert Path(command[0]).resolve() in (RAW, GPMC)
                    assert Path(command[-1]).read_bytes() == source.encode()
                    assert arm not in captures
                    captures[arm] = result
                    (ROOT/f"{name}-{digits}-{arm}.stdout").write_text(result.stdout)
                    (ROOT/f"{name}-{digits}-{arm}.stderr").write_text(result.stderr)
                    return result
                with registered_rawmocs(RAW,digits=digits,timeout_ms=10000,address_space_bytes=None):
                    with patch.object(solver_process,"run",observed):
                        cli=run_wmc(path,"rawmocs",timeout=10,preserve_count=True)
                with registered_native(digits) as adapter:
                    with patch.object(solver_process,"run",forbidden):
                        native=run_wmc(path,"rawmocs_native",timeout=10,preserve_count=True)
                    detail=execute_solver(adapter,path,10,resource_resolver=forbidden,process_runner=forbidden,capture_decimal=True)
                with patch.object(solver_process,"run",observed):
                    gpmc=run_wmc(path,"gpmc",timeout=10,preserve_count=True,precision_digits=digits)
                from rawmocs_quprs import RawAdapter
                import re
                cli_sat, cli_count = RawAdapter.parse_protocol(captures["rawmocs"].stdout)
                assert cli_sat is sat and cli_count == cli
                bits = {30:100,60:200,100:333,130:432}[digits]
                route, actual_digits, actual_bits = re.findall(
                    r"^RAWMOCS_COMPLETE route=(\w+) digits=(\d+) bits=(\d+) ",
                    captures["rawmocs"].stderr, re.M
                )[0]
                assert (int(actual_digits),int(actual_bits)) == (digits,bits)
                # GPMC can omit MPFR precision only for the analytic UNSAT control.
                headers = re.findall(r"^c o precision (\d+)\s*$", captures["gpmc"].stdout, re.M)
                assert headers == [str(digits)] or (name=="unsat" and not headers and gpmc.real==gpmc.imag==0)
                gpmc_sat = re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)\s*$", captures["gpmc"].stdout,re.M)
                assert gpmc_sat == ["SATISFIABLE" if sat else "UNSATISFIABLE"]
                assert cli==native==detail.count and detail.sat is sat
                scale=max(Fraction(1),abs(cli.real),abs(cli.imag))
                assert max(abs(cli.real-gpmc.real),abs(cli.imag-gpmc.imag)) <= scale*Fraction(1,10**24)
                report["fixtures"].append(dict(case=name,digits=digits,bits=bits,cli_route=route,gpmc_reported_precision=headers,sat=sat,real=str(native.real),imag=str(native.imag),cnf_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                save()
        report["failure_controls"]={}
        with registered_native():
            for name,source,kind in (
                ("invalid","not a CNF\n","INVALID_INPUT"),
                ("unsupported","p cnf 1 0\nc t pwmc\n","UNSUPPORTED_INPUT"),
                ("resource","p cnf 4097 0\nc t wmc\n","RESOURCE_LIMIT"),
            ):
                bad=ROOT/(name+".cnf");bad.write_text(source)
                try:run_wmc(bad,"rawmocs_native",timeout=10,preserve_count=True)
                except SolverExecutionError as exc:
                    assert exc.kind==kind and not hasattr(exc,"count")
                    report["failure_controls"][name]=exc.kind
                else:raise AssertionError(f"{name} input accepted")
            try:run_wmc(ROOT/"complex.cnf","rawmocs_native",timeout=0,preserve_count=True)
            except solver_process.SolverTimeout:report["failure_controls"]["zero_budget"]="TIMEOUT_BEFORE_LAUNCH"
            else:raise AssertionError("expired budget accepted")
            assert run_wmc(ROOT/"complex.cnf","rawmocs_native",timeout=10,preserve_count=True).real != 0
        save()
        identity=QuantumCircuit(2)
        eq=QuantumCircuit(2);eq.h(0);eq.t(0);eq.tdg(0);eq.h(0)
        neq=QuantumCircuit(2);neq.h(0)
        for name,circuit,expected in (("eq",eq,"equivalent"),("neq",neq,"not_equivalent")):
            for method in ("wmc_only","hybrid"):
                row={"case":name,"method":method}
                for arm in ("gpmc","rawmocs","rawmocs_native"):
                    from contextlib import nullcontext
                    ctx=registered_native() if arm=="rawmocs_native" else registered_rawmocs(RAW,digits=30,address_space_bytes=None) if arm=="rawmocs" else nullcontext()
                    with ctx:
                        result=check_equivalence(identity,circuit,method=method,strategy="Naive",backend="python",tool_name=arm,timeout=10,safe_mode=False,gpmc_precision_digits=30)
                    row[arm]={"verdict":result.equivalent,"invoked":result.wmc_solver_invoked}
                assert all(row[a]["verdict"]==expected for a in ("gpmc","rawmocs","rawmocs_native")),row
                assert row["rawmocs"]==row["rawmocs_native"],row
                report["e2e"].append(row);save()
        assert get_solver_adapter("gpmc") is default
        try:get_solver_adapter("rawmocs_native")
        except ValueError:pass
        else:raise AssertionError("registration leaked")
        report["status"]="PASS"
    finally:
        save()
    print("P4_NATIVE_FIRST_PASS",json.dumps(report),flush=True)

if __name__=="__main__":
    main()
