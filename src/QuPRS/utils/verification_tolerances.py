"""Per-verification numerical reduction settings (no process-global mutable policy)."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature
from math import isfinite

DEFAULT_RR_TOLERANCE = 1e-10
_rr_tolerance = ContextVar("quprs_rr_tolerance", default=DEFAULT_RR_TOLERANCE)
# Per-call evidence, not part of the cache key or a process-global flag.
_rr_approximation_used = ContextVar("quprs_rr_approximation_used", default=False)


def record_rr_approximation():
    """Mark a tolerance-dependent RR transformation in the current call."""
    _rr_approximation_used.set(True)


def rr_approximation_used():
    return _rr_approximation_used.get()


def validate_rr_tolerance(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("rr_tolerance must be a finite non-negative number")
    try:
        value = float(value)
    except (OverflowError, ValueError):
        raise ValueError("rr_tolerance must be a finite non-negative number") from None
    if not isfinite(value) or value < 0:
        raise ValueError("rr_tolerance must be a finite non-negative number")
    return value


def current_rr_tolerance():
    return _rr_tolerance.get()


@contextmanager
def scoped_rr_tolerance(value):
    token = _rr_tolerance.set(validate_rr_tolerance(value))
    try:
        yield
    finally:
        _rr_tolerance.reset(token)


def per_call_rr_tolerance(fn):
    """Scope the RR threshold to one verification; positional calls also work."""
    sig = signature(fn)

    @wraps(fn)
    def wrapper(*args, **kwargs):
        bound = sig.bind_partial(*args, **kwargs)
        value = bound.arguments.get("rr_tolerance")
        if value is None:
            value = DEFAULT_RR_TOLERANCE
        token = _rr_approximation_used.set(False)
        try:
            with scoped_rr_tolerance(value):
                return fn(*args, **kwargs)
        finally:
            _rr_approximation_used.reset(token)

    return wrapper
