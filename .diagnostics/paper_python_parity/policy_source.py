"""Unit-scale independent policy check: no QuPRS imports or native WMC."""
import argparse
import ast
from fractions import Fraction
import json
import math
from pathlib import Path

def original_statements(text):
    tree=ast.parse(text)
    return [node for node in ast.walk(tree) if isinstance(node,ast.Assign)]

def old_quantization_present(text):
    for node in original_statements(text):
        if any(isinstance(t,ast.Name) and t.id=="log_wmc" for t in node.targets):
            if (isinstance(node.value,ast.Call)
                    and isinstance(node.value.func,ast.Name)
                    and node.value.func.id=="round" and len(node.value.args)==2
                    and isinstance(node.value.args[1],ast.Constant)
                    and node.value.args[1].value==3):
                return True
    return False

def assign_constant(text,name):
    tree=ast.parse(text)
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id==name:
            return float(ast.literal_eval(node.value))
    raise ValueError("Missing pinned policy parameter: "+name)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--paper",type=Path,required=True)
    a.add_argument("--dev",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    o=a.parse_args()
    old=(o.paper/"src/QuPRS/interface/load_qiskit.py").read_text()
    new=(o.dev/"src/QuPRS/utils/wmc_solvers.py").read_text()
    if not old_quantization_present(old):
        raise ValueError("Historical rounded-log WMC predicate changed")
    if "math.expm1" not in new or not any(isinstance(n,ast.FunctionDef) and n.name=="classify_weighted_count" for n in ast.parse(new).body):
        raise ValueError("Current exact-source classifier not found")
    original_tolerance=assign_constant((o.paper/"src/QuPRS/config.py").read_text(),"TOLERANCE")
    current_tolerance=assign_constant((o.dev/"src/QuPRS/config.py").read_text(),"WMC_MAGNITUDE_TOLERANCE")
    if original_tolerance!=1e-10 or current_tolerance!=1e-6:
        raise ValueError("Historical/current source policy differs from pinned audit")
    delta=Fraction(1,1000)
    x=abs(delta)/2
    rigorous_lower=1-x*x/2
    rigorous_upper=rigorous_lower+x**4/24
    if not rigorous_upper < 1:
        raise AssertionError("Exact rational strict oracle failed")
    exact_float_log=math.log2(2.0*math.cos(float(delta)/2))
    old_rounded=round(exact_float_log,3)
    current_defect=abs(math.expm1((exact_float_log-1.0)*math.log(2)))
    comparison={
        "source_scope":"Static AST policy plus independent analytic RZ oracle, not actual native solver execution",
        "original_tolerance":original_tolerance,
        "original_log_wmc_is_rounded_to_three_decimals":True,
        "current_magnitude_tolerance":current_tolerance,
        "source_exact_decimal_radians":str(delta),
        "strict_operator_magnitude_lower":str(rigorous_lower),
        "strict_operator_magnitude_upper":str(rigorous_upper),
        "strict_source_non_equivalence_certified":rigorous_upper<1,
        "ideal_solver_float_log2_count":exact_float_log,
        "historical_formula_rounded_log":old_rounded,
        "historical_formula_accepts":abs(old_rounded-1.0)<original_tolerance,
        "current_formula_relative_magnitude_defect":current_defect,
        "current_formula_accepts":current_defect<current_tolerance,
        "do_not_extrapolate_to_native":"Neither source predicate exercise is an actual GPMC run",
    }
    o.output.mkdir(parents=True,exist_ok=True)
    (o.output/"source-policy.json").write_text(json.dumps(comparison,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"strict_source_nonequivalent":comparison["strict_source_non_equivalence_certified"],
                      "historic_formula_accepts":comparison["historical_formula_accepts"],
                      "current_formula_accepts":comparison["current_formula_accepts"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
