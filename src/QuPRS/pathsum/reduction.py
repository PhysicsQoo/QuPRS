# src/QuPRS/pathsum/reduction.py
from __future__ import annotations
from typing import TYPE_CHECKING
import symengine as se
from QuPRS.utils.util import reduce_expression
from .pattern_match import match_Elim, match_HH, match_omega, HH_reduction, omega_reduction
from . import statistics

if TYPE_CHECKING:
    from .core import PathSum, F

def apply_reduction(pathsum: 'PathSum') -> 'PathSum':
    """
    對一個 PathSum 物件應用簡化規則。
    這段邏輯是從原本的 PathSum.reduction 方法中提取出來的。
    """
    from .core import PathSum  # 避免循環匯入

    if not statistics.is_reduction_enabled():
        return pathsum

    new_P = reduce_expression(pathsum.P)
    
    # 找出可以被簡化的路徑變數 (path variables)
    free_symbols = set().union(*[pathsum.f[i].free_symbols for i in range(pathsum.num_qubits)])
    f_var_names = {f_var.name for f_var in free_symbols}
    reducible_vars = tuple(filter(lambda x: x.name not in f_var_names, pathsum.pathvar))

    if reducible_vars:
        # 嘗試 Elim 規則
        yo_val = match_Elim(new_P, reducible_vars)
        if yo_val is not None:
            new_pathvar = set(pathsum.pathvar)
            new_pathvar.remove(yo_val)
            new_pathsum = PathSum(new_P, pathsum.f, frozenset(new_pathvar))
            statistics.increment_reduction_count('Elim')
            return apply_reduction(new_pathsum)  # 遞迴呼叫以應用更多簡化

        # 嘗試 omega 規則
        pathvar_as_tuple = tuple(pathsum.pathvar)
        yo_val, Q_val, R_val, return_flag = match_omega(new_P, reducible_vars, pathvar_as_tuple, pathsum.bits)
        if yo_val is not None:
            new_pathsum = omega_reduction(pathsum, yo_val, Q_val, R_val, return_flag)
            statistics.increment_reduction_count('omega')
            return apply_reduction(new_pathsum)

        # 嘗試 HH 規則
        yo_val, yi_val, Q_val, R_val = match_HH(new_P, reducible_vars, pathvar_as_tuple, pathsum.bits)
        if yo_val is not None:
            new_pathsum = HH_reduction(pathsum, yo_val, yi_val, Q_val, R_val)
            statistics.increment_reduction_count('HH')
            return apply_reduction(new_pathsum)

    # 如果沒有任何規則可以應用，返回目前的 PathSum
    return PathSum(new_P, pathsum.f, pathsum.pathvar)