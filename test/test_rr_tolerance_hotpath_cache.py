"""Tolerance propagation/cache fast-path contracts (solver-free)."""
import pytest
import symengine as se

from QuPRS.cache_manager.cache_decorator import tracked_lru_cache
from QuPRS.utils.util import (
    _reduce_expression_cached, _process_term_cached,
    process_term, reduce_expression,
)
from QuPRS.utils.verification_tolerances import scoped_rr_tolerance


def test_exempt_exact_normalization_reuses_cache_across_rr_tolerances():
    x = se.Symbol("rr_exact_cache_canonicalization_probe")
    tiny = se.Rational(1, 2_000_000) * x
    with scoped_rr_tolerance(1e-10):
        source = reduce_expression(tiny, drop_small=False)
        term = process_term(tiny, drop_small=False)
    stats_expr = _reduce_expression_cached.cache_info()
    stats_term = _process_term_cached.cache_info()
    with scoped_rr_tolerance(1e-6):
        assert reduce_expression(tiny, drop_small=False) == source
        assert process_term(tiny, drop_small=False) == term
        assert reduce_expression(tiny) == se.S.Zero
        assert process_term(tiny) == se.S.Zero
    assert _reduce_expression_cached.cache_info().hits >= stats_expr.hits + 1
    assert _process_term_cached.cache_info().hits >= stats_term.hits + 1


@pytest.mark.parametrize("invalid", [-1, float("nan"), "1e-10", True])
def test_explicit_invalid_tolerance_still_rejected_when_not_dropping(invalid):
    x = se.Symbol("rr_cache_invalid_arg_probe")
    with pytest.raises(ValueError, match="rr_tolerance"):
        reduce_expression(x, drop_small=False, rr_tolerance=invalid)
    with pytest.raises(ValueError, match="rr_tolerance"):
        process_term(x, drop_small=False, rr_tolerance=invalid)


def test_preserve_scalar_and_matcher_keys_remain_independent():
    x = se.Symbol("rr_cache_preserve_scalar_probe")
    phase = se.Rational(1, 10**11)
    with scoped_rr_tolerance(1e-8):
        assert reduce_expression(phase, preserve_scalar=True) == phase
        assert reduce_expression(phase) == se.S.Zero
        assert reduce_expression(phase + phase * x, preserve_scalar=True) == phase


def test_tracked_lru_cache_preserves_registration_and_metadata():
    from QuPRS.cache_manager import cache_manager
    calls = []
    @tracked_lru_cache(maxsize=2)
    def probe_unique_rr_lru(value):
        calls.append(value)
        return value + 1

    assert probe_unique_rr_lru(10) == 11
    assert probe_unique_rr_lru(10) == 11
    assert calls == [10]
    assert probe_unique_rr_lru.cache_info().hits >= 1
    assert probe_unique_rr_lru.__wrapped__(10) == 11
    assert calls == [10, 10]
    cache_manager.clear_cache(probe_unique_rr_lru)
    assert probe_unique_rr_lru.cache_info().currsize == 0
