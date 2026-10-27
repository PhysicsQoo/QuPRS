"""Solver-free contracts for opt-in, non-overlapping stage accounting."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def ledger_module():
    path = Path(__file__).resolve().parents[1] / ".diagnostics/stage_ledger/exclusive_ledger.py"
    spec = importlib.util.spec_from_file_location("quprs_exclusive_ledger", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_partition_accounts_for_explicit_residual(ledger_module):
    result = ledger_module.check_partition(1.0, {"setup": 0.1, "strategy": 0.6})
    assert result["exclusive_seconds"]["other_unattributed"] == pytest.approx(0.3)
    assert sum(result["exclusive_seconds"].values()) == pytest.approx(1.0)
    assert result["closure_error_seconds"] == pytest.approx(0.0)


def test_reject_overlapping_time_segments(ledger_module):
    with pytest.raises(AssertionError, match="Overlapping"):
        ledger_module.check_partition(0.4, {"strategy": 0.35, "wmc": 0.3})


def test_reject_negative_durations(ledger_module):
    with pytest.raises(ValueError, match="negative"):
        ledger_module.check_partition(1.0, {"stage": -0.01})


def test_recursion_only_counts_top_level_span(ledger_module):
    probe = ledger_module.PythonProbe()

    def original(n):
        return recurse(n - 1) if n else 7

    recurse = probe.wrap("reduction_roots", original, root_reduction=True)
    assert recurse(4) == 7
    assert probe.calls["reduction_roots"] == 5
    assert probe.reduction_max_depth == 5
    assert probe.reduction_depth == 0
    assert probe.durations_ns["reduction_roots"] > 0


def test_stage_partition_avoids_double_counting(ledger_module):
    probe = ledger_module.PythonProbe()
    probe.durations_ns.update({
        "strategy_total": 400_000_000,
        "reduction_roots": 100_000_000,
        "wmc_dispatch_and_parse": 200_000_000,
        "solver_supervision": 150_000_000,
        "cnf_encode_and_write": 50_000_000,
        "wmc_classification": 20_000_000,
        "setup_load_circuit": 30_000_000,
        "setup_initialize": 20_000_000,
        "setup_get_gates": 10_000_000,
    })
    report = probe.exclusive_ledger(0.9)
    spans = report["exclusive_seconds"]
    assert spans["reduction"] == pytest.approx(0.1)
    assert spans["gate_processing_except_reduction"] == pytest.approx(0.3)
    assert spans["solver_spawn_wait_output"] == pytest.approx(0.15)
    assert spans["solver_control_resolution_output_parse"] == pytest.approx(0.05)
    assert spans["other_unattributed"] == pytest.approx(0.17)
    assert sum(spans.values()) == pytest.approx(0.9)


def test_instrumentation_restores_package_calls(ledger_module):
    import QuPRS.pathsum.reduction as reduction
    import QuPRS.interface.ps2wmc as ps2wmc
    from QuPRS.utils.strategy import Strategy

    original_reduce = reduction.apply_reduction
    original_dimacs = ps2wmc.to_DIMACS
    original_factory = Strategy.__dict__["get"]
    probe = ledger_module.PythonProbe()
    with probe.installed():
        assert reduction.apply_reduction is not original_reduce
        assert ps2wmc.to_DIMACS is not original_dimacs
        assert Strategy.__dict__["get"] is not original_factory
    assert reduction.apply_reduction is original_reduce
    assert ps2wmc.to_DIMACS is original_dimacs
    assert Strategy.__dict__["get"] is original_factory
