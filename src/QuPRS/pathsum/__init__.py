# src/QuPRS/pathsum/__init__.py

from . import gates, reduction, statistics
from .core import F, PathSum, Register

# Make reduction and statistics methods available on PathSum
PathSum.get_reduction_counts = staticmethod(statistics.get_reduction_counts)
PathSum.get_reduction_count = staticmethod(statistics.get_reduction_count)
PathSum.get_reduction_hitrate = staticmethod(statistics.get_reduction_hitrate)
PathSum.reset_reduction_counts = staticmethod(statistics.reset_reduction_counts)
PathSum.set_reduction_switch = staticmethod(statistics.set_reduction_switch)
PathSum.is_reduction_enabled = staticmethod(statistics.is_reduction_enabled)
PathSum.reduction = reduction.apply_reduction

# --- Automatically discover and attach quantum gates ---
# 1. Specify the package where quantum gate modules are located


package = gates

# --- Retrieve and attach quantum gates from the gates package ---
# 1. Get all available quantum gate functions
all_gate_functions = gates.get_all_gates()

# 2. Attach each gate function to the PathSum class
for name, func in all_gate_functions.items():
    setattr(PathSum, name, func)

# Make list_supported_gates and get_gates_by_type available on PathSum
PathSum.list_supported_gates = staticmethod(gates.list_supported_gates)
PathSum.get_gates_by_type = staticmethod(gates.get_gates_by_type)
PathSum.support_gate_set = staticmethod(gates.support_gate_set)

# (Optional) Define __all__
__all__ = ["PathSum", "Register", "F"]
