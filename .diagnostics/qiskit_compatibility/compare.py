"""Cross-version Qiskit 1.4.6 / 2.6.1 compatibility evidence comparison.

Differences are observations; no attempt to certify tiny angles using
floating operator equivalence or to compare hosted compilation walltime
as if it were a fixed-hardware publication benchmark.
"""
import argparse
import json
from pathlib import Path

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--v1",type=Path,required=True)
    a.add_argument("--v2",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    old=json.loads(args.v1.read_text())
    new=json.loads(args.v2.read_text())
    if old["qiskit_actual"]!="1.4.6" or new["qiskit_actual"]!="2.6.1":
        raise ValueError("Exact Qiskit source versions required")
    rows=[]
    by_version=[{r["name"]:r for r in v["cases"]} for v in (old,new)]
    if set(by_version[0])!=set(by_version[1]):
        raise ValueError("Missing circuit case for cross-version comparison")
    for name in sorted(by_version[0]):
        l=by_version[0][name]
        r=by_version[1][name]
        for level in range(4):
            first=l["transpiled"][level]
            second=r["transpiled"][level]
            if first["level"]!=level or second["level"]!=level:
                raise ValueError("Transpiler level missing")
            rows.append({
                "case":name,
                "level":level,
                "1x_status":first["status"],
                "2x_status":second["status"],
                "1x_gate_count":first.get("gate_count"),
                "2x_gate_count":second.get("gate_count"),
                "1x_depth":first.get("depth"),
                "2x_depth":second.get("depth"),
                "1x_frobenius_float":first.get("matrix_frobenius_difference_float"),
                "2x_frobenius_float":second.get("matrix_frobenius_difference_float"),
                "1x_walltime_observational":first.get("compilation_wall_seconds_observational"),
                "2x_walltime_observational":second.get("compilation_wall_seconds_observational"),
                "note":"Same hosted runner type, distinct allocated hosts; not a paired fixed-host speedup",
            })
    diff_qasm={}
    for name in sorted(by_version[0]):
        x,y=by_version[0][name],by_version[1][name]
        diff_qasm[name]={}
        for fmt in ("qasm2","qasm2_legacy_basis_bridge","qasm3"):
            diff_qasm[name][fmt]={
                "1x_status":x[fmt]["status"],
                "2x_status":y[fmt]["status"],
                "1x_global_phase":x[fmt].get("imported_global_phase_float"),
                "2x_global_phase":y[fmt].get("imported_global_phase_float"),
                "1x_registers_preserved":x[fmt].get("qreg_partition_preserved"),
                "2x_registers_preserved":y[fmt].get("qreg_partition_preserved"),
                "1x_explicit_global_phase_preserved":x[fmt].get("explicit_global_phase_preserved"),
                "2x_explicit_global_phase_preserved":y[fmt].get("explicit_global_phase_preserved"),
                "1x_raw_matrix_difference_float":x[fmt].get("matrix_frobenius_difference_float"),
                "2x_raw_matrix_difference_float":y[fmt].get("matrix_frobenius_difference_float"),
                "1x_source_to_serialized_matrix_difference_float":(
                    x[fmt].get("composite_source_to_qasm2") or {}
                ).get("matrix_frobenius_difference_float"),
                "2x_source_to_serialized_matrix_difference_float":(
                    y[fmt].get("composite_source_to_qasm2") or {}
                ).get("matrix_frobenius_difference_float"),
            }
    o=args.output.resolve()
    o.mkdir(parents=True,exist_ok=True)
    summary={
        "schema":"qiskit-1x-2x-source-pinned-compatibility-comparison-v1",
        "qiskit_versions":["1.4.6","2.6.1"],
        "cases":len(by_version[0]),
        "transpile_pairs":len(rows),
        "observed_transpile_errors":sum(1 for z in rows if z["1x_status"]!="OK" or z["2x_status"]!="OK"),
        "qasm":diff_qasm,
        "quprs_baseline_import":old["quprs"],
        "quprs_2x_import":new["quprs"],
        "exact_radian_source_oracle_unchanged":old["exact_radian_oracle"]==new["exact_radian_oracle"],
        "metadata_compatibility_warning":"project pyproject.toml currently requires qiskit<2.0: 2.6.1 test is intentional isolated --no-deps research override",
        "timing_limitation":"Hosted CI timings are exploratory. Gate count and fidelity of compiler output need separate evaluation; do not claim publication speedup.",
        "rows":rows,
    }
    (o/"comparison.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    import csv
    with (o/"comparison.csv").open("w",newline="") as file:
        w=csv.DictWriter(file,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("QISKIT_COMPARE",json.dumps({"cases":len(by_version[0]),
                                      "transpile_pairs":len(rows),
                                      "observed_transpile_errors":summary["observed_transpile_errors"],
                                      "exact_oracle_unchanged":summary["exact_radian_source_oracle_unchanged"]}),flush=True)
    return 0 if summary["exact_radian_source_oracle_unchanged"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
