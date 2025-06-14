# src/QuPRS/pathsum/statistics.py

# Use a dictionary to track reduction counts
_reduction_counts = {
    "total": 0,
    "Elim": 0,
    "HH": 0,
    "omega": 0,
}
# Control whether reduction functionality is enabled
_reduction_enabled = True


def get_reduction_counts():
    """Get a copy of all reduction rule counts."""
    return _reduction_counts.copy()


def get_reduction_count(key: str):
    """Get the count for a specific reduction rule."""
    return _reduction_counts.get(key, 0)


def increment_reduction_count(key: str, value: int = 1):
    """Increase the count for a specific reduction rule."""
    if key in _reduction_counts:
        _reduction_counts[key] += value


def get_reduction_hitrate():
    """Calculate the hit rate of reduction rules."""
    total = _reduction_counts["total"]
    if total == 0:
        return 1.0
    else:
        hit = (
            _reduction_counts["Elim"]
            + _reduction_counts["HH"]
            + _reduction_counts["omega"]
        )
        return hit / total


def reset_reduction_counts():
    """Reset all reduction rule counts to 0."""
    for key in _reduction_counts:
        _reduction_counts[key] = 0


def set_reduction_switch(value: bool) -> None:
    """Set the global switch for reduction functionality."""
    global _reduction_enabled
    _reduction_enabled = value


def is_reduction_enabled() -> bool:
    """Check if reduction functionality is enabled."""
    return _reduction_enabled
