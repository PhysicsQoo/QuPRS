"""Verify same-job ordering without starting solver binaries or running benchmarks."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "hosted_solver_comparison.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = spec_from_file_location("hosted_solver_comparison", SCRIPT)
module = module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_balanced_full_plan_covers_original_cases_and_solver_backend_pairs():
    plan = module.schedule(("grover4", "qaoa7", "qft16"), warmups=1, repeats=4)
    assert len(plan) == 60
    assert [step["trial_index"] for step in plan] == list(range(60))
    for case in ("grover4", "qaoa7", "qft16"):
        for solver, backend in module.CELLS:
            rows = [x for x in plan if (x["case"], x["solver"], x["backend"]) ==
                    (case, solver, backend)]
            assert len(rows) == 5
            assert sum(x["warmup"] for x in rows) == 1
            assert [x["repetition"] for x in rows if not x["warmup"]] == [0, 1, 2, 3]


def test_abba_order_reverses_both_solver_backend_and_case_sequence():
    plan = module.schedule(("grover4", "qaoa7"), warmups=1, repeats=4)
    blocks = [[x for x in plan if x["round"] == r] for r in range(5)]
    assert [(x["solver"], x["backend"]) for x in blocks[1][:4]] == list(module.CELLS)
    assert [(x["solver"], x["backend"]) for x in blocks[2][:4]] == list(reversed(module.CELLS))
    assert [(x["solver"], x["backend"]) for x in blocks[3][:4]] == list(reversed(module.CELLS))
    assert [(x["solver"], x["backend"]) for x in blocks[4][:4]] == list(module.CELLS)
    assert [block[0]["case"] for block in blocks] == [
        "grover4", "grover4", "qaoa7", "qaoa7", "grover4"
    ]


def test_missing_repeats_or_duplicate_inputs_fail_before_scheduling():
    with pytest.raises(ValueError, match="four repeats"):
        module.schedule(("grover4",), warmups=1, repeats=3)
    with pytest.raises(ValueError, match="warmup"):
        module.schedule(("grover4",), warmups=0, repeats=4)
    with pytest.raises(ValueError, match="unique"):
        module.schedule(("grover4", "grover4"), warmups=1, repeats=4)
    with pytest.raises(ValueError, match="unique"):
        module.schedule(("unknown",), warmups=1, repeats=4)


def test_optional_existing_paper_cases_have_balanced_solver_backend_schedule():
    plan = module.schedule(("vqe4", "graphstate16"), warmups=1, repeats=4)
    assert len(plan) == 40
    assert {(row["case"], row["solver"], row["backend"]) for row in plan} == {
        (case, solver, backend) for case in ("vqe4", "graphstate16")
        for solver, backend in module.CELLS
    }
    assert module.DEFAULT_CASES == ("grover4", "qaoa7", "qft16")
