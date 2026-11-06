# src/QuPRS/pathsum/core.py

import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.cache_manager import cache_manager
from QuPRS.utils.util import find_new_variables, logical_to_algebraic

from .statistics import StatisticsManager


class Register:
    """Symbolic register identifying the input/output bit positions.

    Args:
        size: Register width. Ignored when `bits` is provided.
        name: Prefix for generated symbols (defaults to `"x"`).
        bits: Optional sequence of existing symbolic bits.

    Notes:
        Integer indexing returns the symbol at that register position. This is
        the Python Path-sum interface, not a Qiskit QuantumRegister.
    """

    def __init__(
        self, size: int | None = None, name: str | None = None, bits=None
    ) -> None:
        if bits is not None:
            size = len(bits)
        if name is None:
            name = "x"
        self._name = name
        self._size = size
        self._repr = f"{self.__class__.__name__}(name={self.name}, size={self.size})"
        self._bits = (
            tuple(bits) if bits is not None else tuple(se.symbols(f"{name}_:{size}"))
        )

    def __repr__(self) -> str:
        return self._repr

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> int:
        return self._size

    def __len__(self):
        return self._size

    def __getitem__(self, key: int):
        return self._bits[key]


class F:
    """Boolean output-state map for a symbolic Path-sum.

    `F[i]` identifies the Boolean expression used for output bit `i`.
    Expressions are normalized to algebraic normal form (ANF) when calling
    :meth:`sub`. Boolean substitution uses GF(2) semantics; this does not
    imply reducing phase-polynomial coefficients modulo two.

    Args:
        *regs: Symbolic :class:`Register` objects.
        data: Optional mapping from bit names to Boolean expressions.
        bits: Optional explicit output-bit order.
    """

    def __init__(self, *regs, data=None, bits=None) -> None:
        self._regs = tuple(regs)
        self._bits = tuple(bits) if bits is not None else list()
        self._data = data if data is not None else dict()
        if data is None:
            for reg in regs:
                for item in reg:
                    self._data[item.name] = item
                    self._bits.append(item.name)
        self._bits = tuple(self._bits)
        self._data = self._data

    def __repr__(self) -> str:
        repr_data = {
            self.bits[i]: (
                1
                if isinstance(item, sp.logic.boolalg.BooleanTrue)
                else 0 if isinstance(item, sp.logic.boolalg.BooleanFalse) else item
            )
            for i, item in enumerate(self)
        }
        return f"{self.__class__.__name__}(data={repr_data}, regs={self.regs})"

    def __hash__(self) -> int:
        return hash(self.data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, F):
            return False
        return self.data == other.data

    @property
    def regs(self):
        return self._regs

    @property
    def bits(self):
        return self._bits

    @property
    def data(self):
        return self._data

    def __len__(self):
        return len(self._bits)

    def __getitem__(self, key: int | se.Symbol | str):
        key_name = (
            self._bits[key]
            if isinstance(key, int)
            else key.name if isinstance(key, se.Symbol) else key
        )
        return self.data[key_name]

    def sub(self, arg1, arg2):
        """Substitute a Boolean variable or expression and normalize to ANF.

        Args:
            arg1: Symbol or expression being replaced.
            arg2: Replacement Boolean expression.

        Returns:
            F: A new output map; the original object is not modified.
        """
        # Only unchanged, already-normalized ANF expressions may bypass
        # SymPy substitution. A non-ANF expression must still run to_anf(),
        # even when the substituted variable is absent.
        target = sp.sympify(arg1)

        def is_anf(expr):
            if expr in (sp.true, sp.false) or isinstance(expr, sp.Symbol):
                return True
            if isinstance(expr, sp.And):
                return all(isinstance(item, sp.Symbol) for item in expr.args)
            if isinstance(expr, sp.Xor):
                return all(
                    isinstance(item, sp.Symbol)
                    or item is sp.true
                    or (isinstance(item, sp.And) and
                        all(isinstance(factor, sp.Symbol) for factor in item.args))
                    for item in expr.args
                )
            return False

        new_data = {}
        for key, value in self.data.items():
            expr = sp.sympify(value)
            if is_anf(expr) and target not in expr.free_symbols:
                new_data[key] = expr
            else:
                new_data[key] = to_anf(expr.subs(arg1, arg2))
        return self.update_data(new_data)

    def update(self, key: int | se.Symbol | str, value):
        """Return a new map with one output bit replaced by `value`."""
        key_name = (
            self._bits[key]
            if isinstance(key, int)
            else key.name if isinstance(key, se.Symbol) else key
        )
        new_data = dict(self.data)
        new_data[key_name] = value
        return F(*self.regs, data=new_data, bits=self.bits)

    def update_data(self, data):
        """Return a new map using `data` with the current bit ordering."""
        return F(*self.regs, data=data, bits=self.bits)

    def items(self):
        return self.data.items()


class PathSum:
    """Symbolic quantum-circuit Path-sum representation.

    Stores the phase polynomial `P`, Boolean output-state mapping `f`,
    summation variables `pathvar`, and reduction statistics `stats`.
    See the Path-sum and reduction guide for the mathematical conventions,
    including the distinction between Boolean substitutions and phase
    coefficients.

    Args:
        P: SymEngine phase expression. Do not implicitly reduce coefficients
            modulo two when constructing this value.
        f: Boolean output-state map, with output-bit ordering defined by `F`.
        pathvar: Set of internal summation variables.
        stats: Optional :class:`StatisticsManager` shared across operations.

    Notes:
        Gate methods such as `h`, `cx`, `rz` and `mcx` are installed from
        Gate subclasses by `attach_gate_methods` at import time. Their
        source-derived signatures and docstrings are also recorded in the
        generated `core.pyi` stub so that static API documentation and type
        tooling can discover them without executing the package.
    """

    def __init__(
        self,
        P: se.Expr,
        f: F,
        pathvar: frozenset | set = frozenset(),
        stats: StatisticsManager | None = None,
    ) -> None:
        """Initialize a Path-sum from its phase, output map and path variables."""
        self._P = P
        self._f = f
        self._pathvar = frozenset(pathvar) if isinstance(pathvar, set) else pathvar
        self._num_qubits = len(f)
        self._stats = stats if stats is not None else StatisticsManager()

    def __repr__(self) -> str:
        return f"P:{self.P}\nf: {self.f}\npathvar: {self.pathvar}"

    def __hash__(self) -> int:
        return hash((self.P, self.f, self.pathvar))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathSum):
            return False
        return (
            (self.P == other.P)
            and (self.f == other.f)
            and (self.pathvar == other.pathvar)
        )

    # --- Properties ---
    @property
    def regs(self) -> tuple:
        return self.f.regs

    @property
    def bits(self) -> tuple:
        return self.f.bits

    @property
    def P(self) -> se.Expr:
        return self._P

    @property
    def f(self) -> F:
        return self._f

    @property
    def pathvar(self) -> frozenset:
        return self._pathvar

    @property
    def num_qubits(self) -> int:
        return self._num_qubits

    @property
    def num_pathvar(self) -> int:
        return len(self.pathvar)

    @property
    def stats(self) -> StatisticsManager:
        return self._stats
        # --- Instance methods for statistics ---

    def get_reduction_counts(self) -> dict:
        """Get a copy of all reduction rule counts for this instance."""
        return self._stats.get_reduction_counts()

    def get_reduction_count(self, key: str) -> int:
        """Get the count for a specific reduction rule for this instance."""
        return self._stats.get_reduction_count(key)

    def get_reduction_hitrate(self) -> float:
        """Calculate the hit rate of reduction rules for this instance."""
        return self._stats.get_reduction_hitrate()

    def reset_reduction_counts(self):
        """Reset all reduction rule counts for this instance to 0."""
        self._stats.reset_reduction_counts()

    def set_reduction_switch(self, value: bool) -> None:
        """Set the reduction switch for this instance."""
        self._stats.set_reduction_switch(value)

    def is_reduction_enabled(self) -> bool:
        """Check if reduction is enabled for this instance."""
        return self._stats.is_reduction_enabled()

    # --- Static Constructors ---
    @staticmethod
    def QuantumCircuit(
        *regs: Register | int, initial_state: bool | list | tuple = None
    ) -> "PathSum":
        """Create the identity Path-sum for the supplied registers or width.

        Args:
            *regs: A width integer or one or more symbolic Register objects.
            initial_state: Optional sequence of initial Boolean output values.

        Returns:
            PathSum: New symbolic circuit, initially with zero phase.
        """
        cache_manager.clear_all_caches()
        P = se.S.Zero
        if len(regs) == 1 and isinstance(regs[0], int):
            regs = [Register(regs[0])]
        f = F(*regs)
        if initial_state is not None:
            f_data = {f.bits[i]: to_anf(initial_state[i]) for i in range(len(f))}
            f = f.update_data(f_data)
        return PathSum(P, f)

    @staticmethod
    def load_from_qasm_file(
        filename: str, initial_state: bool | list | tuple = None
    ) -> "PathSum":
        from qiskit import qasm2, qasm3

        from QuPRS.interface.load_qiskit import build_circuit

        with open(filename, "r") as f:
            data = f.read()
        qiskit_circuit = (
            qasm3.load(filename) if "OPENQASM 3.0" in data else qasm2.load(filename)
        )
        return build_circuit(qiskit_circuit, initial_state)

    @staticmethod
    def load_from_qasm_str(
        program: str, initial_state: bool | list | tuple = None
    ) -> "PathSum":
        from qiskit import qasm2, qasm3

        from QuPRS.interface.load_qiskit import build_circuit

        qiskit_circuit = (
            qasm3.loads(program) if "OPENQASM 3.0" in program else qasm2.loads(program)
        )
        return build_circuit(qiskit_circuit, initial_state)

    def compose(self, other_pathsum: "PathSum") -> "PathSum":
        """Compose two Path-sums with compatible ordered input/output bits.

        Returns a new simplified object, alpha-renaming overlapping summation
        variables before substitution to avoid variable capture. Raises
        AssertionError if the bit order does not match.
        """
        assert (
            self.bits == other_pathsum.bits
        ), f"Bits mismatch: {self.bits} != {other_pathsum.bits}"
        intersect = self.pathvar.intersection(other_pathsum.pathvar)
        temp_P = other_pathsum.P
        temp_f = other_pathsum.f
        new_vars_set = set()
        if intersect:
            temp_pathvar = self.pathvar.union(other_pathsum.pathvar)
            new_vars = find_new_variables(temp_pathvar, len(intersect))
            new_vars_set = set(new_vars)
            sub_dict = {old: new for old, new in zip(intersect, new_vars)}
            temp_P = temp_P.subs(sub_dict)
            for old, new in sub_dict.items():
                temp_f = temp_f.sub(old, new)

        sub_map = {
            se.symbols(f"{self.bits[i]}"): logical_to_algebraic(self.f[i])
            for i in range(self.num_qubits)
        }
        temp_P = temp_P.subs(sub_map)
        for i in range(self.num_qubits):
            symbol = se.symbols(f"{self.bits[i]}")
            temp_f = temp_f.sub(symbol, self.f[i])

        new_P = self.P + temp_P
        new_f = temp_f
        new_pathvar = self.pathvar.union(other_pathsum.pathvar, new_vars_set)
        new_pathsum = PathSum(new_P, new_f, new_pathvar, self._stats)

        from . import reduction

        return reduction.apply_reduction(new_pathsum)
