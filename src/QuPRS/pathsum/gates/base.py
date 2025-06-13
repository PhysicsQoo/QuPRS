# src/QuPRS/pathsum/gates/base.py

def gate(type: str):
    """
    一個參數化的裝飾器，用來標記函式為量子閘，並註明其類型。
    用法: @gate(type='single')
    """
    def decorator(func):
        func._is_gate = True
        func._gate_type = type
        return func
    return decorator