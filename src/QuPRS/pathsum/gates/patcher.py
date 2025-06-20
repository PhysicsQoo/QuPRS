# src/QuPRS/pathsum/gates/patcher.py
from __future__ import annotations

import inspect
from functools import wraps
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..core import PathSum
    from .base import Gate


def _create_gate_method(gate_cls: type["Gate"]) -> Callable:
    """
    Factory function: Creates a method for a given Gate class that can be injected
    into PathSum. This version correctly handles both positional and keyword
    arguments for gate initialization.
    """
    # Retrieve the parameter names for the Gate class's __init__ method
    init_sig = inspect.signature(gate_cls.__init__)
    init_param_names = [
        p.name for p in init_sig.parameters.values() if p.name != "self"
    ]

    @wraps(gate_cls.apply)
    def gate_method(pathsum_instance: "PathSum", *args, **kwargs) -> "PathSum":
        """
        Wrapper function to be injected as a new PathSum method, e.g., PathSum.rz().

        Handles argument parsing and gate instantiation.
        """
        init_kwargs = {}

        # 1. Prioritize extracting __init__ parameters from keyword arguments.
        #    This allows users to always override defaults explicitly.
        for name in init_param_names:
            if name in kwargs:
                init_kwargs[name] = kwargs.pop(name)

        # 2. Next, extract remaining __init__ parameters from the beginning of
        #    positional arguments.
        args_list = list(args)

        # Calculate how many __init__ parameters are still needed
        needed_init_params = len(init_param_names) - len(init_kwargs)

        if needed_init_params > 0 and len(args_list) >= needed_init_params:
            # Take the required number of arguments from the start of args_list
            init_args = args_list[:needed_init_params]
            # Remove these from args_list, leaving only those for the apply method
            del args_list[:needed_init_params]

            # Map the extracted positional arguments to their parameter names
            remaining_init_names = [
                name for name in init_param_names if name not in init_kwargs
            ]
            init_kwargs.update(zip(remaining_init_names, init_args))

        # 3. Instantiate the gate (e.g., RzGate(theta=1.5707))
        gate_instance = gate_cls(**init_kwargs)

        # 4. Call the gate instance's apply method, passing remaining arguments
        return gate_instance.apply(pathsum_instance, *args_list, **kwargs)

    return gate_method


def attach_gate_methods(gate_class_map: dict[str, type["Gate"]]):
    """
    Injects all discovered quantum gates as methods into the PathSum class.

    Each gate class must define a 'gate_name' class attribute.
    """
    from ..core import PathSum

    for gate_cls in gate_class_map.values():
        if not hasattr(gate_cls, "gate_name"):
            print(
                f"Warning: Skipping gate class '{gate_cls.__name__}' "
                "because it is missing the 'gate_name' class attribute."
            )
            continue

        method_name = gate_cls.gate_name
        if hasattr(PathSum, method_name):
            continue

        method = _create_gate_method(gate_cls)
        setattr(PathSum, method_name, method)
