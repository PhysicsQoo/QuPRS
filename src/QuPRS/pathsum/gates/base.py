# src/QuPRS/pathsum/gates/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import PathSum


class Gate(ABC):
    gate_name: str

    def __init__(self):
        pass

    @abstractmethod
    def apply(self, pathsum: "PathSum", *args, **kwargs) -> "PathSum":
        raise NotImplementedError


# --- Single-Qubit Gates ---
class SingleQubitGate(Gate):
    """
    Intermediate class for all single-qubit gates.
    """

    pass


# --- Base Gate Class Definitions ---
# Note: The following base classes are assumed based on the request.


class TwoQubitGate(Gate):
    """
    Intermediate class for all two-qubit gates.
    """

    pass


class MultiQubitGate(Gate):
    """
    Base class for gates acting on three or more qubits.
    """

    pass
