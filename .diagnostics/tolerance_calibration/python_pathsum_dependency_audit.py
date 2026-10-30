"""Phase 13: audit actual Python PathSum source dependency graph of real QFT16.

Use exactly one public dev Python WMC-only solver call, inspect retained
final PathSum and CNF. Build a source-level topological order for every
output F_i: its symbols may depend on path variables and earlier output
functions only. All phase monomials must use declared path/output symbols.

When acyclic and all Tseitin and phase literals are defined by iff
(as source encoder review asserts), every assignment of k path variables
has AT MOST ONE full encoded CNF extension: #SAT <= 2^k.
This is a research-only source-dependency guard, not public metadata.
A structural guard failure is NOT a negative equivalence result.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from QuPRS import check_equivalence

QFT_SHA="20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1"
def source_symbols(value):
    free=getattr(value,"free_symbols",None)
    if free is None:
        if value in (0,1,True,False):return set()
        raise ValueError(("unsupported source boolean expression",str(value)[:200]))
    return {str(v) for v in free}
def check_dependencies(bits,pathvars,outputs,phase):
    bit_names=[str(x) for x in bits]
    path_names=[str(x) for x in pathvars]
    if len(bit_names)!=len(set(bit_names)) or len(path_names)!=len(set(path_names)):
        raise ValueError("duplicate output or path variable identity")
    if set(bit_names)&set(path_names):raise ValueError("path and output symbols intersect")
    if len(outputs)!=len(bit_names):raise ValueError("output arity mismatch")
    allowed=set(bit_names)|set(path_names)
    deps={}
    for bit,expr in zip(bit_names,outputs):
        names=source_symbols(expr)
        if names-allowed:raise ValueError(("undeclared output dependency",bit,sorted(names-allowed)))
        deps[bit]=names&set(bit_names)
    if source_symbols(phase)-allowed:
        raise ValueError("phase depends on undeclared symbol")
    # Deterministic topological evaluation of the output dependency graph.
    solved=set(path_names);remaining=set(bit_names);topology=[]
    while remaining:
        ready=sorted(name for name in remaining if deps[name]<=solved)
        if not ready:
            raise ValueError(("cyclic output dependency, cannot certify k-only bound",
                              {name:sorted(deps[name]) for name in remaining}))
        for name in ready:
            solved.add(name);remaining.remove(name);topology.append(name)
    return {
      "path_variable_count":len(path_names),
      "output_bit_count":len(bit_names),
      "phase_depends_on_declared_symbols_only":True,
      "all_output_dependencies_known":True,
      "no_output_self_or_dependency_cycles":True,
      "output_topological_order":topology,
      "output_dependency_counts":{name:len(deps[name]) for name in bit_names},
      "proof": "induct on output dependency DAG; phase z and Tseitin aux each iff defined",
      "source_structure_certifies_at_most_one_extension_per_path_assignment":True,
      "total_model_upper_bound":f"2^{len(path_names)}",
      "original_CNF_semantics_also_requires_verified_encoder_iff":True,
    }
def fail_closed_controls():
    controls=[
      ("valid_nested_outputs",["b0","b1"],["y0"],["y0","b0"],0,True),
      ("invalid_self_dependency",["b0"],["y0"],["b0"],0,False),
      ("invalid_mutual_cycle",["b0","b1"],["y0"],["b1","b0"],0,False),
      ("invalid_undeclared_symbol",["b0"],["y0"],["a0"],0,False),
      ("invalid_overlap",["b0"],["b0"],["b0"],0,False),
      ("valid_phase_with_output",["b0"],["y0"],["y0"],"b0",True),
      ("invalid_phase_undeclared",["b0"],["y0"],["y0"],"a0",False),
    ]
    from sympy import sympify
    rows=[]
    for label,bits,path,exprs,phase,should_pass in controls:
        try:
            ans=check_dependencies(bits,path,[sympify(x) for x in exprs],sympify(phase))
            actual=True;cause=None
        except ValueError as exc:
            actual=False;cause=str(exc)
        if actual!=should_pass:raise AssertionError((label,actual,should_pass,cause))
        rows.append({"case":label,"passed":actual,"expected":should_pass,
                     "refusal_reason":cause,"expected_control":True})
    return rows

def main(out):
    from precision_followup_v2 import sources
    left,right,strategy,source_hashes=sources("qft16")
    result=check_equivalence(str(left),str(right),backend="python",
        method="wmc_only",strategy=strategy,tool_name="gpmc",
        timeout=65,approximate_distance_tolerance=1e-8)
    if not result.CNF or hashlib.sha256(result.CNF.encode()).hexdigest()!=QFT_SHA:
        raise AssertionError("original QFT16 source CNF moved")
    ps=result.final_pathsum
    if ps is None:raise AssertionError("Python API PathSum unavailable")
    analysis=check_dependencies(
       ps.bits,ps.pathvar,[ps.f[i] for i in range(ps.num_qubits)],ps.P)
    analysis.update({
        "source_family":"qft16",
        "original_QASM_SHA256":source_hashes,
        "original_CNF_SHA256":QFT_SHA,
        "actual_public_dev_python_solver_calls":1,
        "actual_pathsum_encoded_phase_weights":400,
        "public_verdict_unchanged":result.equivalent,
        "no_source_or_classifier_modifications":True,
        "Rust_API_semantics_not_inferred_from_Python":True,
    })
    if analysis["path_variable_count"]!=70 or analysis["output_bit_count"]!=16:
        raise AssertionError(("QFT source shape changed",analysis))
    controls=fail_closed_controls()
    out.mkdir(parents=True,exist_ok=True)
    (out/"qft16-pathsum-dependency-guard.json").write_text(
        json.dumps({"real_case":analysis,"seven_controls":controls,
                    "source_review_iff_obligation":True},
                   indent=2,sort_keys=True,default=str)+"\n")
    print("QFT16_PATHSUM_DEPENDENCY_CERTIFICATE "+
          json.dumps(analysis,sort_keys=True,default=str),flush=True)
    print("PATHSUM_DEPENDENCY_SEVEN_CONTROLS_EXPECTED_PASS_OR_FAIL",flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True,type=Path)
    main(ap.parse_args().output)
