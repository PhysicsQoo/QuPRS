"""Pure contract tests: no external solver process or numerical verdict policy."""
import pytest
import symengine as se
from QuPRS.utils.solver_adapter import SolverAdapter, SolverCapabilities, get_solver_adapter
from QuPRS.utils.wmc_problem import WmcProblem, WmcWeight


def test_neutral_ir_has_solver_specific_serialization_and_no_float_coercion():
    real = se.sqrt(2).evalf(113)
    imag = -se.Rational(1, 4)
    problem = WmcProblem(
        2, ((1, -2), (2,)),
        (WmcWeight(2, real, imag),),
    )
    assert problem.weights[0].real is real
    assert problem.weights[0].imag is imag
    for name in ("gpmc", "ganak"):
        text = problem.serialize(get_solver_adapter(name))
        assert text.startswith("p cnf 2 2\nc t wmc\n")
        assert text.endswith("1 -2 0\n2 0")
        assert f"c p weight 2 {real}" in text
        assert "c p weight -2 " in text
    assert " -1/4 0" in problem.serialize(get_solver_adapter("gpmc"))
    assert " - 1/4i 0" in problem.serialize(get_solver_adapter("ganak"))


@pytest.mark.parametrize("bad", [
    lambda: WmcProblem(-1, ()),
    lambda: WmcProblem(True, ()),
    lambda: WmcProblem(1, ((2,),)),
    lambda: WmcProblem(1, ((0,),)),
    lambda: WmcProblem(1, ((1.0,),)),
    lambda: WmcProblem(1, (), (WmcWeight(2, 1, 0),)),
    lambda: WmcProblem(1, (), (WmcWeight(1, 1, 0), WmcWeight(1, 2, 0))),
])
def test_reject_unsupported_ir(bad):
    with pytest.raises(ValueError):
        bad()


def test_empty_and_unsatisfiable_clause_are_distinct():
    assert WmcProblem(0, ()).serialize(get_solver_adapter("gpmc")) == "p cnf 0 0\nc t wmc"
    assert WmcProblem(0, ((),)).serialize(get_solver_adapter("gpmc")) == "p cnf 0 1\nc t wmc\n0"


def test_declared_solver_capability_is_required():
    adapter = SolverAdapter("unsupported-complex", (), SolverCapabilities("pair", complex_weights=False))
    with pytest.raises(ValueError, match="complex"):
        WmcProblem(1, ((1,),)).serialize(adapter)
