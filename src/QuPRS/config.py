# config.py
import math

TOLERANCE = 1e-10

# Solver-output acceptance is independent of symbolic reduction tolerance.
# These are Python public-API defaults; every call may override both values.
# Keep symbolic reduction TOLERANCE independent from WMC numerical policy.
WMC_MAGNITUDE_TOLERANCE = 1e-8
WMC_PHASE_TOLERANCE = 1e-8


def set_tolerance(new_tolerance: float):
    """Change the local RR tolerance and invalidate dependent memoized results.

    Process-global configuration is not a concurrent per-call tolerance policy.
    """
    global TOLERANCE
    if isinstance(new_tolerance, bool) or not isinstance(new_tolerance, (int, float)):
        raise ValueError("Tolerance must be a finite positive number")
    try:
        new_tolerance = float(new_tolerance)
    except (OverflowError, ValueError):
        raise ValueError("Tolerance must be a finite positive number") from None
    if not math.isfinite(new_tolerance) or new_tolerance <= 0:
        raise ValueError("Tolerance must be a finite positive number")
    if TOLERANCE == new_tolerance:
        return
    from QuPRS.cache_manager import cache_manager

    # process_term/reduce_expression are cached without config.TOLERANCE in
    # the cache key; invalidating on actual changes preserves API semantics.
    cache_manager.clear_all_caches()
    TOLERANCE = new_tolerance


def get_tolerance() -> float:

    return TOLERANCE
