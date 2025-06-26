# src/QuPRS/pathsum/__init__.py


from . import reduction
from .core import F, PathSum, Register
from .gates import (
    get_all_gates,
    get_gates_by_type,
    list_supported_gates,
    support_gate_set,
)
from .gates.patcher import attach_gate_methods

attach_gate_methods(get_all_gates())


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
]
