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

    @profiler.wrapped("child", lambda: 42)
    def child():
        return 42

    @profiler.wrapped("parent", lambda: child())
    def parent():
        return child()

    assert parent() == 42
    assert profiler.COUNTERS["parent"]["calls"] == 1
    assert profiler.COUNTERS["child"]["calls"] == 1
    assert profiler.COUNTERS["parent"]["inclusive_ns"] >= profiler.COUNTERS["parent"]["exclusive_ns"]
    assert not profiler.STACK


def test_wrapped_exception_restores_stack(profile_module):
    profiler = profile_module

    @profiler.wrapped("failure", lambda: None)
    def failure():
        raise RuntimeError("expected")

    with pytest.raises(RuntimeError, match="expected"):
        failure()
    assert not profiler.STACK
    assert profiler.COUNTERS["failure"]["calls"] == 1


def test_reduction_recursion_depth(profile_module):
    profiler = profile_module

    @profiler.wrapped("apply_reduction", lambda n: n)
    def recurse(n):
        return recurse(n - 1) if n else 0

    assert recurse(3) == 0
    assert profiler.DEPTH["calls"] == 4
    assert profiler.DEPTH["max"] == 4
    assert profiler.DEPTH["current"] == 0
