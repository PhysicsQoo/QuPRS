# src/QuPRS/pathsum/gates/base.py


def gate(type: str):
    """
    A parameterized decorator to mark a function as a quantum gate and specify its type.
    Usage: @gate(type='single')
    """

    def decorator(func):
        func._is_gate = True
        func._gate_type = type
        return func

    return decorator
