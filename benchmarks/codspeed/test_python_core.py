"""Source-exact Python hot-path CPU microbenchmarks (no external Solver).

All fixture construction is deliberately outside the timed CodSpeed window.
The Rust verifier is NEVER entered by these benchmark functions.
"""
import symengine as se
import sympy as sp
import pytest

from QuPRS.pathsum.core import F
from QuPRS.pathsum.pattern_match import match_Elim, match_HH


def _anf_absent():
    x, y, z = sp.symbols("x y z")
    f = F(bits=("a", "b"), data={
        "a": sp.Xor(y, z), "b": sp.And(y, z),
    })
    return f, x, sp.true


def _anf_replace():
    x, y, z = sp.symbols("x y z")
    f = F(bits=("a", "b"), data={
        "a": sp.Xor(x, sp.And(y, z)), "b": sp.Xor(x, y),
    })
    return f, x, sp.true


def _hh_match():
    u, v = se.symbols("u v")
    phase = u * v / 2
    return phase, {u}, {u, v}, ()


def _elim_hit():
    u, v = se.symbols("u v")
    return u / 4, {v}


def _elim_miss():
    u, v = se.symbols("u v")
    return u / 4, {u}


@pytest.mark.parametrize("name,setup,func,expect", (
    ("anf_target_absent", _anf_absent, "f_sub", "F"),
    ("anf_target_present", _anf_replace, "f_sub", "F"),
    ("hh_pair_match", _hh_match, "hh", "MATCH"),
    ("elim_candidate", _elim_hit, "elim", "MATCH"),
    ("elim_no_candidate", _elim_miss, "elim", "NONE"),
), ids=["anf_target_absent", "anf_target_present", "hh_pair_match", "elim_candidate", "elim_no_candidate"])
def test_python_algorithm_cpu(benchmark, name, setup, func, expect):
    args = setup()
    if func == "f_sub":
        result = benchmark(args[0].sub, *args[1:])
    elif func == "hh":
        result = benchmark(match_HH, *args)
    else:
        result = benchmark(match_Elim, *args)
    if expect == "F":
        assert isinstance(result, F)
    elif expect == "MATCH":
        assert (result[0] is not None if func == "hh" else result is not None)
    else:
        assert result is None
    benchmark.extra_info.update({
        "benchmark_scope": "python_algorithm_only",
        "fixture": name,
        "solver_invoked": "False",
        "backend": "python",
        "codspeed_instrument": "simulation",
    })
