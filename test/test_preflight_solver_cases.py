"""Pure preflight eligibility tests; never start GPMC or Ganak."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preflight_solver_cases.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = spec_from_file_location("preflight_solver_cases", SCRIPT)
module = module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def rows(case, *, all_valid=True):
    result = []
    for solver, backend in module.CELLS:
        result.append({
            "case": case, "solver": solver, "backend": backend,
            "status": "PASS", "native_execve": True,
            "positive_equivalence": True,
            "numeric_solver_time": True,
        })
    if not all_valid:
        result[0]["native_execve"] = False
    return result


def test_accepts_only_complete_native_execve_coverage():
    data = rows("vqe4") + rows("graphstate16")
    assert module.select_eligible(data, ("vqe4", "graphstate16")) == [
        "vqe4", "graphstate16"
    ]


def test_reduction_only_or_unobserved_solver_is_not_misclassified():
    data = rows("vqe4", all_valid=False) + rows("graphstate16")
    assert module.select_eligible(data, ("vqe4", "graphstate16")) == [
        "graphstate16"
    ]


def test_missing_solver_backend_case_is_rejected():
    assert module.select_eligible(rows("vqe4")[:-1], ("vqe4",)) == []


def test_equivalent_reduction_only_case_is_ineligible_for_solver_comparison():
    data = rows("graphstate16")
    for row in data:
        row["positive_equivalence"] = True
        row["numeric_solver_time"] = False
        row["native_execve"] = False
    assert module.select_eligible(data, ("graphstate16",)) == []
