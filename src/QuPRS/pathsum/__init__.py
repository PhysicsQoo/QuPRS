# src/QuPRS/pathsum/__init__.py

import pkgutil
import importlib
import inspect

# --- Import and attach core functionalities (keep this part unchanged) ---
from .core import PathSum, Register, F
from . import statistics
from . import reduction

PathSum.get_reduction_counts = staticmethod(statistics.get_reduction_counts)
# ... attach other statistics methods ...
PathSum.reduction = reduction.apply_reduction

# --- Automatically discover and attach quantum gates ---
# 1. Specify the package path where quantum gate modules are located
from . import gates
package = gates

# 2. Iterate over all modules in the package
for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
    # Exclude base.py or other non-gate files
    if module_name == 'base':
        continue

    # 3. Dynamically import the found module
    #    e.g., import QuPRS.pathsum.gates.single_qubit
    module = importlib.import_module(f'{package.__name__}.{module_name}')

    # 4. Iterate over all members (functions, classes, etc.) in the module
    for name, member in inspect.getmembers(module):
        # 5. Check if the member is a function decorated with @gate
        if inspect.isfunction(member) and getattr(member, '_is_gate', False):
            # 6. Attach it to the PathSum class
            setattr(PathSum, name, member)

# (Optional) Define __all__
__all__ = ['PathSum', 'Register', 'F']