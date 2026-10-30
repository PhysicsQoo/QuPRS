"""Per-verification numerical reduction settings (no process-global mutable policy)."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature
from math import isfinite

DEFAULT_RR_TOLERANCE = 1e-10
_rr_tolerance = ContextVar("quprs_rr_tolerance", default=DEFAULT_RR_TOLERANCE)


def validate_rr_tolerance(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("rr_tolerance must be a finite positive number")
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError("rr_tolerance must be a finite positive number")
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
        with scoped_rr_tolerance(value):
            return fn(*args, **kwargs)

    return wrapper
