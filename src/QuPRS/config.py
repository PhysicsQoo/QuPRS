# config.py
TOLERANCE = 1e-10

# Solver-output acceptance is independent of symbolic reduction tolerance.
# These are Python public-API defaults; every call may override both values.
# Keep symbolic reduction TOLERANCE independent from WMC numerical policy.
WMC_MAGNITUDE_TOLERANCE = 1e-8
WMC_PHASE_TOLERANCE = 1e-8


def set_tolerance(new_tolerance: float):
    global TOLERANCE
    if not isinstance(new_tolerance, (int, float)):
        raise ValueError("Tolerance must be a numeric type")
    if new_tolerance <= 0:
        raise ValueError("Tolerance must be a positive number")
    TOLERANCE = new_tolerance


def get_tolerance() -> float:

    return TOLERANCE
