# src/QuPRS/pathsum/__init__.py

import pkgutil
import importlib
import inspect

# --- 匯入與附加核心功能 (這部分保持不變) ---
from .core import PathSum, Register, F
from . import statistics
from . import reduction

PathSum.get_reduction_counts = staticmethod(statistics.get_reduction_counts)
# ... 其他統計方法的附加 ...
PathSum.reduction = reduction.apply_reduction

# --- 全自動發現並附加量子閘 ---
# 1. 指定量子閘模組所在的套件路徑
from . import gates
package = gates

# 2. 遍歷該套件中的所有模組
for _, module_name, _ in pkgutil.iter_modules(package.__path__):
    # 排除 base.py 或其他非量子閘檔案
    if module_name == 'base':
        continue
    
    # 3. 動態匯入找到的模組
    #    例如，import QuPRS.pathsum.gates.single_qubit
    module = importlib.import_module(f'{package.__name__}.{module_name}')
    
    # 4. 遍歷模組中的所有成員 (函式、類別等)
    for name, member in inspect.getmembers(module):
        # 5. 檢查成員是否是被 @gate 裝飾過的函式
        if inspect.isfunction(member) and hasattr(member, '_is_gate'):
            # 6. 將其附加到 PathSum 類別
            setattr(PathSum, name, member)

# (可選) 定義 __all__
__all__ = ['PathSum', 'Register', 'F']