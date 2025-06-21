# src/QuPRS/pathsum/gates/builder.py (Final version with Args type hints)
import inspect
from inspect import Parameter
from typing import Any, List, Type

# Import all Gate base classes from base for use in build_docstring.
from .base import Gate

# --- This file contains shared logic for building method metadata ---


def _cleanup_type_str(type_obj: Any) -> str:
    """
    Helper function to convert a type object to a clean string representation.
    """
    if type_obj is None or type_obj is inspect.Parameter.empty:
        return "Any"
    s = str(type_obj)
    s = s.replace("QuPRS.pathsum.core.", "")
    s = s.replace("symengine.lib.symengine_wrapper.", "se.")
    s = s.replace("sympy.core.expr.", "sp.")
    s = s.replace("typing.", "")
    s = s.replace("<class '", "").replace("'>", "")
    return s


def build_signature(
    gate_cls: Type[Gate], include_self: bool = False
) -> inspect.Signature:
    """
    Build a function signature object based on the Gate class.

    Args:
        gate_cls (Type[Gate]): The Gate class to inspect.
        include_self (bool): Whether to include 'self' in the signature.

    Returns:
        inspect.Signature: The constructed function signature.
    """
    init_sig = inspect.signature(gate_cls.__init__)
    apply_sig = inspect.signature(gate_cls.apply)

    init_params = [p for p in init_sig.parameters.values() if p.name != "self"]
    apply_params = [
        p for p in apply_sig.parameters.values() if p.name not in ("self", "pathsum")
    ]

    combined_params: List[Parameter] = init_params + apply_params

    if include_self:
        self_param = Parameter("self", Parameter.POSITIONAL_OR_KEYWORD)
        combined_params.insert(0, self_param)

    return inspect.Signature(parameters=combined_params)


def build_docstring(gate_cls: Type[Gate], signature: inspect.Signature) -> str:
    """
    Generate a standardized docstring with type hints for a Gate class.

    Args:
        gate_cls (Type[Gate]): The Gate class for which to build the docstring.
        signature (inspect.Signature): The function signature to document.

    Returns:
        str: The generated docstring.
    """

    # --- Standardized template definitions ---

    main_desc_template = (
        f"Applies the {gate_cls.gate_name.upper()} gate to the specified qubit."
    )

    arg_descriptions = {
        "pathsum": "The input PathSum object.",
        "qubit": "The qubit to which the gate is applied.",
        "qubit1": "The first qubit.",
        "qubit2": "The second qubit.",
        "control_qubit": "The control qubit.",
        "control_qubit1": "The first control qubit.",
        "control_qubit2": "The second control qubit.",
        "qubits": "A list of qubits to which the gate is applied.",
        "target_qubit": "The target qubit.",
        "is_bra": "Whether the input is a bra state. Defaults to False.",
        "theta": "The rotation angle theta in radians.",
        "phi": "The rotation angle phi in radians.",
        "lam": "The rotation angle lambda in radians.",
        "gamma": "The global phase factor.",
        "k": "The integer parameter for the controlled rotation.",
    }

    returns_description = (
        f"PathSum: The resulting PathSum object after applying the "
        f"{gate_cls.gate_name.upper()} gate."
    )

    # --- Assemble the docstring ---

    docstring_parts = [main_desc_template]

    user_params = [p for p in signature.parameters.values() if p.name != "self"]
    if user_params:
        docstring_parts.append("\n\nArgs:\n")
        for param in user_params:
            param_name = param.name.replace("*", "")
            description = arg_descriptions.get(param_name, "No description available.")

            # Get type hint from signature and format it.
            param_type_str = _cleanup_type_str(param.annotation)

            # Format as `param_name (type): description`
            docstring_parts.append(
                f"    {param_name} ({param_type_str}): {description}\n"
            )

    docstring_parts.append("\nReturns:\n")
    docstring_parts.append(f"    {returns_description}\n")

    return "".join(docstring_parts).strip()
