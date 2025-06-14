# src/QuPRS/pathsum/reduction.py
from __future__ import annotations

from typing import TYPE_CHECKING

from QuPRS.utils.util import reduce_expression

from . import statistics
from .pattern_match import (HH_reduction, match_Elim, match_HH, match_omega,
                            omega_reduction)

if TYPE_CHECKING:
    from .core import F, PathSum


def apply_reduction(pathsum: "PathSum") -> "PathSum":
    """
    Apply simplification rules to a PathSum object.
    This logic is extracted from the original PathSum.reduction method.
    """
    from .core import PathSum  # Avoid circular import

    if not statistics.is_reduction_enabled():
        return pathsum

    new_P = reduce_expression(pathsum.P)

    # Find path variables that can be reduced
    free_symbols = set().union(
        *[pathsum.f[i].free_symbols for i in range(pathsum.num_qubits)]
    )
    f_var_names = {f_var.name for f_var in free_symbols}
    reducible_vars = tuple(filter(lambda x: x.name not in f_var_names, pathsum.pathvar))

    if reducible_vars:
        # Try Elim rule
        yo_val = match_Elim(new_P, reducible_vars)
        if yo_val is not None:
            new_pathvar = set(pathsum.pathvar)
            new_pathvar.remove(yo_val)
            new_pathsum = PathSum(new_P, pathsum.f, frozenset(new_pathvar))
            statistics.increment_reduction_count("Elim")
            return apply_reduction(
                new_pathsum
            )  # Recursive call to apply further reductions

        # Try omega rule
        pathvar_as_tuple = tuple(pathsum.pathvar)
        yo_val, Q_val, R_val, return_flag = match_omega(
            new_P, reducible_vars, pathvar_as_tuple, pathsum.bits
        )
        if yo_val is not None:
            new_pathsum = omega_reduction(pathsum, yo_val, Q_val, R_val, return_flag)
            statistics.increment_reduction_count("omega")
            return apply_reduction(new_pathsum)

        # Try HH rule
        yo_val, yi_val, Q_val, R_val = match_HH(
            new_P, reducible_vars, pathvar_as_tuple, pathsum.bits
        )
        if yo_val is not None:
            new_pathsum = HH_reduction(pathsum, yo_val, yi_val, Q_val, R_val)
            statistics.increment_reduction_count("HH")
            return apply_reduction(new_pathsum)

    # If no rules can be applied, return the current PathSum
    return PathSum(new_P, pathsum.f, pathsum.pathvar)
