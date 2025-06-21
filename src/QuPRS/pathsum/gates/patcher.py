# src/QuPRS/pathsum/gates/patcher.py
from __future__ import annotations

import inspect
from functools import wraps
from typing import TYPE_CHECKING, Callable, Type

if TYPE_CHECKING:
    from ..core import PathSum

from .base import Gate
from .builder import build_docstring, build_signature


def _create_gate_method(gate_cls: Type["Gate"]) -> Callable:
    """
    Factory function to create a gate method for the PathSum class.

    This function generates a method that wraps the given gate class,
    automatically handling argument parsing and metadata generation for
    runtime introspection. The generated method can be attached to the
    PathSum class as a quantum gate operation.
    """
    # Key call: build_docstring is called here with two arguments to generate
    # the signature and the docstring.
    signature = build_signature(gate_cls, include_self=False)
    docstring = build_docstring(gate_cls, signature)
    init_param_names = [
        p.name
        for p in inspect.signature(gate_cls.__init__).parameters.values()
        if p.name != "self"
    ]

    @wraps(gate_cls)
    def gate_method(pathsum_instance: "PathSum", *args, **kwargs) -> "PathSum":
        """
        Dynamically generated gate method for PathSum.

        This method parses positional and keyword arguments, instantiates the
        gate class, and applies it to the given PathSum instance.
        """
        init_kwargs = {}
        for name in init_param_names:
            if name in kwargs:
                init_kwargs[name] = kwargs.pop(name)
        args_list = list(args)
        needed_init_params = len(init_param_names) - len(init_kwargs)
        if needed_init_params > 0 and len(args_list) >= needed_init_params:
            init_args = args_list[:needed_init_params]
            del args_list[:needed_init_params]
            remaining_init_names = [
                name for name in init_param_names if name not in init_kwargs
            ]
            init_kwargs.update(zip(remaining_init_names, init_args))
        gate_instance = gate_cls(**init_kwargs)
        return gate_instance.apply(pathsum_instance, *args_list, **kwargs)

    gate_method.__signature__ = signature
    gate_method.__doc__ = docstring
    gate_method.__name__ = gate_cls.gate_name
    return gate_method


def attach_gate_methods(gate_class_map: dict[str, type["Gate"]]):
    """
    Attach all discovered quantum gate methods to the PathSum class.

    Each gate class in the provided mapping must define a 'gate_name'
    class attribute. This function injects a corresponding method into
    the PathSum class for each gate, unless a method with the same name
    already exists.
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
        method.__name__ = method_name
        setattr(PathSum, method_name, method)
