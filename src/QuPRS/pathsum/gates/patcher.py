# src/QuPRS/pathsum/gates/patcher.py
from __future__ import annotations

import inspect
from functools import wraps
from inspect import Parameter
from typing import TYPE_CHECKING, Callable, List, Type

if TYPE_CHECKING:
    from ..core import PathSum

from .base import Gate, MultiQubitGate, SingleQubitGate, TwoQubitGate


def _create_gate_method(gate_cls: Type["Gate"]) -> Callable:
    """
    Factory function: Creates a method for a given Gate class.
    This version dynamically generates a new signature and docstring
    to provide an optimal IDE experience.
    """

    # Step 1: Dynamically build a new function signature.
    init_sig = inspect.signature(gate_cls.__init__)
    apply_sig = inspect.signature(gate_cls.apply)

    # Extract parameters from __init__, excluding 'self'.
    init_params = [p for p in init_sig.parameters.values() if p.name != "self"]

    # Extract parameters from apply, excluding 'self' and 'pathsum'.
    apply_params = [
        p for p in apply_sig.parameters.values() if p.name not in ("self", "pathsum")
    ]

    # Combine parameter lists for the new signature.
    combined_params: List[Parameter] = init_params + apply_params
    new_signature = inspect.Signature(parameters=combined_params)

    # Step 2: Dynamically build a new docstring.
    class_doc = inspect.getdoc(gate_cls)

    # Check and provide a meaningful default docstring if needed.
    generic_docs = {
        inspect.getdoc(Gate),
        inspect.getdoc(SingleQubitGate),
        inspect.getdoc(TwoQubitGate),
        inspect.getdoc(MultiQubitGate),
    }
    if not class_doc or class_doc in generic_docs:
        class_doc = f"Applies the {gate_cls.gate_name} gate."

    docstring_parts = [class_doc, "\n"]
    if combined_params:
        docstring_parts.append("\nArgs:\n")
        for param in combined_params:
            docstring_parts.append(f"    {param.name}: The parameter description.\n")

    new_docstring = "".join(docstring_parts)

    # Step 3: Define the wrapper function and attach metadata.
    @wraps(gate_cls.apply)
    def gate_method(pathsum_instance: "PathSum", *args, **kwargs) -> "PathSum":
        # Parse init parameters from args and kwargs.
        init_param_names_list = [p.name for p in init_params]
        init_kwargs = {}
        for name in init_param_names_list:
            if name in kwargs:
                init_kwargs[name] = kwargs.pop(name)
        args_list = list(args)
        needed_init_params = len(init_param_names_list) - len(init_kwargs)
        if needed_init_params > 0 and len(args_list) >= needed_init_params:
            init_args = args_list[:needed_init_params]
            del args_list[:needed_init_params]
            remaining_init_names = [
                name for name in init_param_names_list if name not in init_kwargs
            ]
            init_kwargs.update(zip(remaining_init_names, init_args))
        gate_instance = gate_cls(**init_kwargs)
        return gate_instance.apply(pathsum_instance, *args_list, **kwargs)

    # Attach metadata for IDE support.
    gate_method.__signature__ = new_signature
    gate_method.__doc__ = new_docstring
    gate_method.__name__ = gate_cls.gate_name
    gate_method.source_gate_class = gate_cls

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
