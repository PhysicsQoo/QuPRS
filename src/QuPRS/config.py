# config.py
TOLERANCE = 1e-10  

def set_tolerance(new_tolerance: float):
    global TOLERANCE
    if not isinstance(new_tolerance, (int, float)):
        raise ValueError("Tolerance must be a numeric type")
    if new_tolerance <= 0:
        raise ValueError("Tolerance must be a positive number")
    TOLERANCE = new_tolerance

def get_tolerance() -> float:

    return TOLERANCE