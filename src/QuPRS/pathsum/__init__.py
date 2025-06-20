# src/QuPRS/pathsum/__init__.py


from . import reduction
from .core import F, PathSum, Register
from .gates import (
    get_all_gates,
    get_gates_by_type,
    list_supported_gates,
    support_gate_set,
)
from .statistics import statistics_manager

PathSum.get_reduction_counts = staticmethod(statistics_manager.get_reduction_counts)
PathSum.get_reduction_count = staticmethod(statistics_manager.get_reduction_count)
PathSum.get_reduction_hitrate = staticmethod(statistics_manager.get_reduction_hitrate)
PathSum.reset_reduction_counts = staticmethod(statistics_manager.reset_reduction_counts)
PathSum.set_reduction_switch = staticmethod(statistics_manager.set_reduction_switch)
PathSum.is_reduction_enabled = staticmethod(statistics_manager.is_reduction_enabled)

set_reduction_switch = statistics_manager.set_reduction_switch
is_reduction_enabled = statistics_manager.is_reduction_enabled


PathSum.reduction = reduction.apply_reduction


__all__ = [
    # Core classes
    "PathSum",
    "Register",
    "F",
    # Gates API
    "get_all_gates",
    "get_gates_by_type",
    "list_supported_gates",
    "support_gate_set",
    # Statistics API
    "statistics_manager",
    "set_reduction_switch",
    "is_reduction_enabled",
]
