"""GPMC precision-replay error model and solver transport contracts.

Numerical verdicts below are explicitly conditional on the MPFR operation
allowance and the source-weight precision assumption, never formal proofs.
"""
from fractions import Fraction
import pytest

from QuPRS.utils.gpmc_distance_budget import classify_gpmc_budgeted_count
from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata
from QuPRS.utils.precision_count import parse_printed_count_line


def result(real):
    return parse_printed_count_line(
        "c s exact double prec-sci " + real + " + 0.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00i"
    )


def classify(observed, *, vars=5, replay=None, weights=2):
    return classify_gpmc_budgeted_count(
        result(observed), expected_twice_log2=0,
        distance_tolerance=1e-8, precision_digits=90,
        cnf_vars=vars, number_of_weights=weights,
        maximum_weight_magnitude_squared=Fraction(1),
        independent_count=result(replay if replay is not None else observed),
    )


def test_model_distinguishes_far_outside_with_long_printed_count():
    r=classify("9.9999999999995065197799455360500000000000000000000000000000000000000000000000000000000000000000000e-01")
    assert r.printed_status == "not_equivalent"
    assert r.status == "not_equivalent"
    assert r.reason == "modelled_count_below_distance_threshold"
    assert not r.solver_arithmetic_certified
    assert not r.source_weight_certified


def test_model_fails_closed_on_missing_replay_and_larger_cnf():
    r=classify_gpmc_budgeted_count(
        result("9.99999999999950000000000000000000000000000000000000000e-01"),
        expected_twice_log2=0, distance_tolerance=1e-8,
        precision_digits=90, cnf_vars=5, number_of_weights=1,
        maximum_weight_magnitude_squared=Fraction(1),
        independent_count=None
    )
    assert r.status=="unknown"
    assert classify("9.99999999999950000000000000000000000000000000000000000e-01",
                    vars=19).status == "unknown"


def test_model_fails_closed_on_replay_disagreement():
    r=classify(
        "9.999999999999500000000000000000000000000000000000000000000e-01",
        replay="9.999999999999400000000000000000000000000000000000000000000e-01",
    )
    assert r.status=="unknown"
    assert r.reason=="precision_replay_disagreement"


def test_model_inside_threshold_is_numerical_not_a_certificate():
    r=classify("1.000000000000000000000000000000000000000000000000000000000000e+00")
    assert r.status == "equivalent"
    assert r.reason == "modelled_count_inside_distance_threshold"
    assert not r.solver_arithmetic_certified


def test_gpmc_cnf_metadata_validates_literal_weights():
    cnf="""p cnf 3 1
c t wmc
c p weight 1 1.0 0.0 0
c p weight -1 1.0 0.0 0
c p weight 2 0.6 0.8 0
c p weight -2 1.0 0.0 0
1 2 0
"""
    assert gpmc_cnf_budget_metadata(cnf) == (3, 2, Fraction(1))
    with pytest.raises(ValueError):
        gpmc_cnf_budget_metadata("p cnf 2 0\nc p weight 9 1.0 0.0 0")


def test_gpmc_precision_transport_uses_selected_adapter_no_switch(monkeypatch):
    from QuPRS.interface import ps2wmc
    called=[]
    class FakeResult:
        count=result("9.99999999999950000000000000000000000000000000000000000000e-01")

    def fake_exec(adapter,file,timeout,**kw):
        called.append((adapter.solver_id,adapter.arguments,kw["capture_decimal"]))
        return FakeResult()
    monkeypatch.setattr("QuPRS.utils.solver_adapter.execute_solver",fake_exec)
    assert ps2wmc.run_wmc("sample.cnf",tool_name="gpmc",preserve_count=True,
                          precision_digits=90) == FakeResult.count
    assert called==[("gpmc",("-mode=1","-prec=90"),True)]
    with pytest.raises(ValueError):
        ps2wmc.run_wmc("sample.cnf",tool_name="ganak",precision_digits=90)
