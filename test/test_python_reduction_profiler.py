"""Fast, solver-free contracts for the optional Python reduction profiler."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def profile_module():
    path = Path(__file__).resolve().parents[1] / ".diagnostics/python_reduction/profile.py"
    spec = importlib.util.spec_from_file_location("quprs_profiler_profile", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.COUNTERS.clear()
    module.STACK.clear()
    module.DEPTH.update(current=0, max=0, calls=0)
    return module


def test_exclusive_time_and_nested_call_accounting(profile_module):
    profiler = profile_module

    def original_child():
        return 42

    child = profiler.wrapped("child", original_child)

    def original_parent():
        return child()

    parent = profiler.wrapped("parent", original_parent)

    assert parent() == 42
    assert profiler.COUNTERS["parent"]["calls"] == 1
    assert profiler.COUNTERS["child"]["calls"] == 1
    assert profiler.COUNTERS["parent"]["inclusive_ns"] >= profiler.COUNTERS["parent"]["exclusive_ns"]
    assert profiler.COUNTERS["parent"]["exclusive_ns"] >= 0
    assert not profiler.STACK


def test_wrapped_exception_restores_stack(profile_module):
    profiler = profile_module

    def original_failure():
        raise RuntimeError("expected")

    failure = profiler.wrapped("failure", original_failure)

    with pytest.raises(RuntimeError, match="expected"):
        failure()
    assert not profiler.STACK
    assert profiler.COUNTERS["failure"]["calls"] == 1


def test_reduction_recursion_depth(profile_module):
    profiler = profile_module

    def original_recurse(n):
        return recurse(n - 1) if n else 0

    recurse = profiler.wrapped("apply_reduction", original_recurse)

    assert recurse(3) == 0
    assert profiler.DEPTH["calls"] == 4
    assert profiler.DEPTH["max"] == 4
    assert profiler.DEPTH["current"] == 0
    assert not profiler.STACK


def test_free_symbols_timed_at_actual_matcher_callsite(profile_module):
    import symengine as se
    import QuPRS.pathsum.reduction as reduction

    y, z = se.symbols("quprs_profiler_y quprs_profiler_z")
    original = reduction.match_Elim
    with profile_module.instrument():
        assert reduction.match_Elim(y, (y, z)) == z
        assert profile_module.COUNTERS["free_symbols.phase"]["calls"] == 1
        assert profile_module.COUNTERS["reduction_match_Elim"]["calls"] == 1
        assert not profile_module.STACK
    assert reduction.match_Elim is original
    assert "_quprs_profiler_timed_symbols" not in reduction.__dict__


def test_output_free_symbols_and_elim_preserve_pathsum(profile_module):
    import symengine as se
    import QuPRS.pathsum.reduction as reduction
    from QuPRS.pathsum.core import PathSum

    baseline = PathSum.QuantumCircuit(1)
    y = se.Symbol("quprs_profiler_unused_y")
    ps = PathSum(se.S.Zero, baseline.f, frozenset({y}))
    original = reduction.apply_reduction
    expected = reduction.apply_reduction(ps)
    with profile_module.instrument():
        actual = reduction.apply_reduction(ps)
        assert actual == expected
        assert profile_module.COUNTERS["free_symbols.output"]["calls"] >= 1
        assert profile_module.COUNTERS["free_symbols.phase"]["calls"] >= 1
        assert profile_module.DEPTH["calls"] >= 2
        assert profile_module.DEPTH["current"] == 0
        assert not profile_module.STACK
    assert reduction.apply_reduction is original
