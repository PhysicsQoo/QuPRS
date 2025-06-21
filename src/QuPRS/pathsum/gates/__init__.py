# src/QuPRS/pathsum/gates/__init__.py

import importlib
import inspect
import pkgutil
from collections import defaultdict
from typing import Dict, Type

# Import base gate classes for type checking and inheritance checks
from .base import Gate, MultiQubitGate, SingleQubitGate, TwoQubitGate

_gate_map: Dict[str, Type[Gate]] = dict()


def get_all_gates() -> Dict[str, Type[Gate]]:
    """
    Dynamically discovers all Gate subclasses within this package.

    This function scans all modules in the 'gates' package, finds classes
    that inherit from the base 'Gate' class, and returns a map of
    {gate_name: gate_class}.

    Returns:
        A dictionary mapping the gate_name attribute of each gate class
        to the class itself.
    """
    if _gate_map:
        return _gate_map

    base_classes = {Gate, SingleQubitGate, TwoQubitGate, MultiQubitGate}
    package = __import__(__name__, fromlist=[""])

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        # Skip utility and base modules
        if module_name in ["base", "utils", "applier", "patcher"]:
            continue
        module = importlib.import_module(f".{module_name}", package.__name__)
        for name, member in inspect.getmembers(module, inspect.isclass):
            # Register only subclasses of Gate that are not base classes themselves
            if issubclass(member, Gate) and member not in base_classes:
                _gate_map[name] = member

    return _gate_map


def get_gates_by_type(gate_type: str) -> list[str]:
    """Returns a sorted list of gate class names filtered by the specified type.

    The type should be one of: 'single', 'two', or 'multi'.
    """
    all_gates = get_all_gates()
    type_map = {
        "single": SingleQubitGate,
        "two": TwoQubitGate,
        "multi": MultiQubitGate,
    }
    base_class = type_map.get(gate_type)
    if not base_class:
        return []
    return sorted(
        [name for name, cls in all_gates.items() if issubclass(cls, base_class)]
    )


def list_supported_gates():
    """Prints all supported quantum gate classes, grouped by their base class type."""
    print("--- Supported Gate Classes ---")
    all_gates = get_all_gates()
    gates_by_type = defaultdict(list)
    for name, cls in all_gates.items():
        if issubclass(cls, MultiQubitGate):
            gates_by_type["Multi-Qubit"].append(name)
        elif issubclass(cls, TwoQubitGate):
            gates_by_type["Two-Qubit"].append(name)
        elif issubclass(cls, SingleQubitGate):
            gates_by_type["Single-Qubit"].append(name)
    print(f"Single-Qubit: {sorted(gates_by_type['Single-Qubit'])}")
    print(f"Two-Qubit: {sorted(gates_by_type['Two-Qubit'])}")
    print(f"Multi-Qubit: {sorted(gates_by_type['Multi-Qubit'])}")
    print("------------------------------")


def support_gate_set() -> set:
    """Returns a set containing the names of all supported quantum gate methods (e.g.,
    'h', 'cx').

    The names are extracted from the 'gate_name' attribute of each gate class.
    """
    all_gates = get_all_gates()
    gate_names = {
        cls.gate_name for cls in all_gates.values() if hasattr(cls, "gate_name")
    }
    return gate_names
