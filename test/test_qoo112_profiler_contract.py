"""Fast, solver-free contracts for the optional Python reduction profiler."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def profile_module():
    path = Path(__file__).resolve().parents[1] / ".diagnostics/qoo112/python_reduction_profile.py"
    spec = importlib.util.spec_from_file_location("qoo112_profile", path)
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
