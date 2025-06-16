# src/QuPRS/pathsum/gates/__init__.py
import importlib
import inspect
import pkgutil

# Private variable to store discovered gates and avoid redundant lookups
_all_gates = {}


def _discover_gates():
    """
    Private function to perform one-time discovery and collection of quantum gates.
    """
    # Return immediately if discovery has already been done
    if _all_gates:
        return

    package = __import__(__name__, fromlist=[""])

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name == "base" or module_name == "utils":
            continue

        module = importlib.import_module(f".{module_name}", package.__name__)

        for name, member in inspect.getmembers(module):
            if inspect.isfunction(member) and getattr(member, "_is_gate", False):
                _all_gates[name] = member


def get_all_gates() -> dict:
    """
    Public function to retrieve a dictionary of all quantum gates {name: function}.
    """
    _discover_gates()  # Ensure discovery is performed
    return _all_gates.copy()


def get_gates_by_type(gate_type: str) -> list[str]:
    """
    Retrieve a sorted list of quantum gate names by type.
    """
    all_gates = get_all_gates()
    return sorted(
        [
            name
            for name, func in all_gates.items()
            if getattr(func, "_gate_type", None) == gate_type
        ]
    )


def list_supported_gates():
    """
    Print all supported quantum gates, grouped by type.
    """
    print("--- Supported Gates ---")
    print(f"Single-Qubit: {get_gates_by_type('single')}")
    print(f"Two-Qubit: {get_gates_by_type('two')}")
    print(f"Multi-Qubit: {get_gates_by_type('multi')}")
    print("-----------------------")


def support_gate_set() -> set:
    """
    Return a set containing the names of all supported quantum gates.
    This set is generated dynamically.
    """
    all_gates = get_all_gates()
    return set(all_gates.keys())
