import symengine as se
import sympy as sp
import math
from sympy.logic.boolalg import to_anf
from QuPRS.utils.util import logical_to_algebraic, reduce_expression, div_pi, find_new_variables
from QuPRS.utils.reduction import match_Elim, match_HH, match_omega, HH_reduction, omega_reduction
from QuPRS.cache_manager import cache_manager
from QuPRS import config

class Register:
    def __init__(self, size: int | None = None, name: str | None = None, bits=None) -> None:
        if bits is not None:
            size = len(bits)
        if name is None:
            name = 'x'
        else:
            name = name
        self._name = name
        self._size = size
        self._repr = f'{self.__class__.__name__}(name={self.name}, size={self.size})'
        self._bits = tuple(bits) if bits is not None else tuple(se.symbols(f'{name}_:{size}'))

    def __repr__(self) -> str:
        return self._repr

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> int:
        return self._size

    def __len__(self):
        """Return register size."""
        return self._size

    def __getitem__(self, key: int):
        """Return a bit from the register."""
        return self._bits[key]

class F:
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
        repr_data = {self.bits[i]: 1 if isinstance(item, sp.logic.boolalg.BooleanTrue) else 0 if isinstance(item, sp.logic.boolalg.BooleanFalse) else item for i, item in enumerate(self)}
        return f'{self.__class__.__name__}(data={repr_data}, regs={self.regs})'

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
        key_name = self._bits[key] if isinstance(key, int) else key.name if isinstance(key, se.Symbol) else key
        return self.data[key_name]
    
    def sub(self, arg1, arg2):
        new_data = {key: to_anf(sp.sympify(value).subs(arg1, arg2)) for key, value in self.data.items()}
        self = self.update_data(new_data)
        return self
    def update(self, key: int | se.Symbol | str, value):
        key_name = self._bits[key] if isinstance(key, int) else key.name if isinstance(key, se.Symbol) else key
        new_data = dict(self.data)
        new_data[key_name] = value
        return F(*self.regs, data=new_data, bits=self.bits)

    def update_data(self, data):
        return F(*self.regs, data=data, bits=self.bits)

    def items(self):
        return self.data.items()


class PathSum:
    reduction_counts = {
        'total': 0,
        'Elim': 0,
        'HH': 0,
        'omega': 0,
    }
    _reduction_enabled = True

    def __init__(self, P: se.Expr, f: F, pathvar: frozenset | set = frozenset()) -> None:
        self._P = P
        self._f = f
        self._pathvar = frozenset(pathvar) if isinstance(pathvar, set) else pathvar
        self._num_qubits = len(f)

    def __repr__(self) -> str:
        return f'P:{self.P}\nf: {self.f}\npathvar: {self.pathvar}'

    def __hash__(self) -> int:
        return hash((self.P, self.f, self.pathvar))

    def __eq__(self, other: object) -> bool:
        return (self.P == other.P) and (self.f == other.f) and (self.pathvar == other.pathvar)

    @property
    def regs(self):
        return self.f.regs

    @property
    def bits(self):
        return self.f.bits

    @property
    def P(self) -> se.Expr:
        return self._P

    @property
    def f(self):
        return self._f

    @property
    def pathvar(self):
        return self._pathvar

    @property
    def num_qubits(self) -> int:
        '''return the number of qubits'''
        return self._num_qubits

    @property
    def num_pathvar(self) -> int:
        '''return the number of pathvar'''
        return len(self.pathvar)

    @classmethod
    def get_reduction_counts(cls):
        return cls.reduction_counts.copy()
    @classmethod
    def get_reduction_count(cls, key: str):
        return cls.reduction_counts.get(key, 0)
    @classmethod
    def get_reduction_hitrate(cls):
        total = cls.reduction_counts['total']
        if total == 0:
            return 1
        else:
            hit = 0
            for key, value in cls.reduction_counts.items():
                if key == 'total':
                    continue
                hit += value
            return hit / total
    @classmethod
    def reset_reduction_counts(cls):
        for key in cls.reduction_counts:
            cls.reduction_counts[key] = 0
    @classmethod
    def set_reduction_switch(cls, value: bool) -> None:
        cls._reduction_enabled = value
    @classmethod
    def is_reduction_enabled(cls) -> bool:
        return cls._reduction_enabled
    @staticmethod
    def QuantumCircuit(*regs: Register | int, initial_state: bool | list | tuple = None) -> 'PathSum':
        '''initialize'''
        cache_manager.clear_all_caches()
        P = se.S.Zero
        if len(regs) == 1 and isinstance(*regs, int):
            regs = [Register(*regs)]
        f = F(*regs)
        if initial_state is not None:
            f_data = {f.bits[i]: to_anf(initial_state[i]) for i in range(len(f))}
            f = f.update_data(f_data)
        PathSum.reset_reduction_counts()
        return PathSum(P, f)

    @staticmethod
    def load_from_qasm_file(filename: str, initial_state: bool | list | tuple = None):
        '''load a PathSum item from qasm file'''
        from qiskit import qasm2, qasm3
        from QuPRS.interface.load_qiskit import build_circuit
        with open(filename, 'r') as f:
            data = f.read()
        qiskit_circuit = qasm3.load(filename) if 'OPENQASM 3.0' in data else qasm2.load(filename)
        return build_circuit(qiskit_circuit, initial_state)

    @staticmethod
    def load_from_qasm_str(program: str, initial_state: bool | list | tuple = None):
        '''load a PathSum item from qasm str'''
        from qiskit import qasm2, qasm3
        from QuPRS.interface.load_qiskit import build_circuit
        qiskit_circuit = qasm3.loads(program) if 'OPENQASM 3.0' in program else qasm2.loads(program)
        return build_circuit(qiskit_circuit, initial_state)

    # Apply H gate
    def h(self, qubit: int | str, is_bra: bool = False) -> 'PathSum':
        # index = 0
        # while se.Symbol(f'y_{index}') in self.pathvar:
        #     index += 1
        # new_var = se.Symbol(f'y_{index}')
        new_var = find_new_variables(self.pathvar)[0]
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 1)
            new_P = self.P + se.Rational(1, 2) * new_var * x_i
            new_f = self.f.update(qubit, new_var)
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P.subs(x_i, new_var) + se.Rational(1, 2) * new_var * x_i
            new_f = self.f.sub(x_i, logical_to_algebraic(new_var))
        new_pathvar = frozenset(set(self.pathvar).union({new_var}))
        new_pathsum = PathSum(new_P, new_f, new_pathvar).reduction()
        return new_pathsum

    # Apply X gate
    def x(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            new_P = self.P
            new_f = self.f.update(qubit, to_anf(sp.Not(self.f[qubit])))
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P.subs(x_i, 1 - x_i)
            new_f = self.f.sub(x_i, sp.Not(x_i))
        new_P = reduce_expression(new_P)
        return PathSum(new_P, new_f, self.pathvar)

    # Apply Y gate
    def y(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 1)
            new_P = (self.P + se.Rational(3, 4) + se.Rational(1, 2) * x_i).expand()
            new_f = self.f.update(qubit, to_anf(sp.Not(self.f[qubit])))
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = (self.P.subs(x_i, 1 - x_i) + se.Rational(3, 4) + se.Rational(1, 2) * x_i).expand()
            new_f = self.f.sub(x_i, sp.Not(x_i))
        new_P = reduce_expression(new_P)
        return PathSum(new_P, new_f, self.pathvar)

    # Apply Z gate
    def z(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 1)
            new_P = (self.P + se.Rational(1, 2) * x_i).expand()
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = (self.P + se.Rational(1, 2) * x_i).expand()
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply S gate
    def s(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 2)
            new_P = (self.P + se.Rational(1, 4) * x_i).expand()
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = (self.P + se.Rational(-1, 4) * x_i).expand()
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Sdg gate
    def sdg(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 2)
            new_P = (self.P + se.Rational(-1, 4) * x_i).expand()
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = (self.P + se.Rational(1, 4) * x_i).expand()
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply T gate
    def t(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 3)
            new_P = (self.P + se.Rational(1, 8) * x_i).expand()
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = (self.P + se.Rational(-1, 8) * x_i).expand()
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Tdg gate
    def tdg(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[qubit], 3)
            new_P = (self.P + se.Rational(-1, 8) * x_i).expand()
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P + se.Rational(1, 8) * x_i
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Sx gate
    def sx(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        self = self.rx(se.pi / 2, qubit, is_bra)
        new_P = self.P + se.Rational(1, 8) if not is_bra else self.P - se.Rational(1, 8)
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Sxdg gate
    def sxdg(self, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        self = self.rx(-se.pi / 2, qubit, is_bra)
        new_P = self.P - se.Rational(1, 8) if not is_bra else self.P + se.Rational(1, 8)
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply P gate
    def p(self, theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        theta = div_pi(theta)
        if not is_bra:
            if theta.is_number:
                max_order = math.log2(theta.as_numer_denom()[1])
                max_order = int(max_order) + 1 if int(max_order) == max_order else None
            else:
                max_order = None
            x_i = logical_to_algebraic(self.f[qubit], max_order=max_order)
            new_P = self.P + se.Rational(1, 2) * theta * x_i
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P - se.Rational(1, 2) * theta * x_i
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Rz gate
    def rz(self, theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        theta = div_pi(theta)
        if not is_bra:
            if theta.is_number:
                max_order = math.log2(theta.as_numer_denom()[1])
                max_order = int(max_order) + 2 if int(max_order) == max_order else None
            else:
                max_order = None
            x_i = logical_to_algebraic(self.f[qubit], max_order=max_order)
            new_P = self.P + se.Rational(1, 4) * (-theta + 2 * theta * x_i)
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P + se.Rational(1, 4) * (theta - 2 * theta * x_i)
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply Rx gate
    def rx(self, theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        return self.u(theta, -se.pi / 2, se.pi / 2, qubit, is_bra)

    # Apply Ry gate
    def ry(self, theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        return self.u(theta, 0, 0, qubit, is_bra)

    # Apply U gate
    def u(self, theta, phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        theta, phi, lam = map(div_pi, [theta, phi, lam])
        new_vars = find_new_variables(self.pathvar, 2)
        if not is_bra:
            if lam.is_number:
                max_order = math.log2(lam.as_numer_denom()[1]) 
                max_order = int(max_order) +1 if int(max_order) == max_order else None
            else:
                max_order = None
            x_i_lam = logical_to_algebraic(self.f[qubit], max_order=max_order)
            x_i = logical_to_algebraic(self.f[qubit], max_order=2 )
            new_P = self.P + se.Rational(1, 2) * lam * x_i_lam + \
                      se.Rational(1, 2) * phi * new_vars[1] + \
                      se.Rational(1, 4) * theta * (2 * new_vars[0] - 1) + \
                      se.Rational(3, 4) * x_i + \
                      se.Rational(1, 4) * new_vars[1] + \
                      se.Rational(1, 2) * x_i * new_vars[0] + \
                      se.Rational(1, 2) * new_vars[0] * new_vars[1]
            new_f = self.f.update(qubit, new_vars[1])
        else:
            x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
            new_P = self.P.subs(x_i, new_vars[1]) + \
                      se.Rational(-1, 2) * phi * x_i + \
                      se.Rational(-1, 2) * lam * new_vars[1] + \
                      se.Rational(1, 4) * theta * (2 * new_vars[0] - 1) + \
                      se.Rational(1, 4) * x_i + \
                      se.Rational(3, 4) * new_vars[1] + \
                      se.Rational(1, 2) * x_i * new_vars[0] + \
                      se.Rational(1, 2) * new_vars[0] * new_vars[1]
            new_f = self.f.sub(x_i, logical_to_algebraic(new_vars[1]))
        new_pathvar = frozenset(set(self.pathvar).union(new_vars))
        new_pathsum = PathSum(new_P, new_f, new_pathvar)
        new_pathsum = new_pathsum.reduction()
        return new_pathsum

    def u1(self, theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        return self.p(theta, qubit, is_bra)

    def u2(self, phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        return self.u(se.Rational(1, 2) * se.pi, phi, lam, qubit, is_bra)

    def u3(self, theta, phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        return self.u(theta, phi, lam, qubit, is_bra)

    # Apply CX gate
    def cx(self, control_qubit: int | str | se.Symbol, target_qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            new_f = self.f.update(target_qubit, to_anf(sp.Xor(self.f[control_qubit], self.f[target_qubit])))
            return PathSum(self.P, new_f, self.pathvar)
        else:
            x_i = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            x_j = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            new_var = sp.Xor(x_i, x_j)
            update_var = logical_to_algebraic(new_var)
            new_P = self.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = self.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, self.pathvar)

    # Apply CH gate
    def ch(self, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        new_pathsum = self.s(target_qubit, is_bra)
        new_pathsum = new_pathsum.h(target_qubit, is_bra)
        new_pathsum = new_pathsum.t(target_qubit, is_bra)
        new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.tdg(target_qubit, is_bra)
        new_pathsum = new_pathsum.h(target_qubit, is_bra)
        new_pathsum = new_pathsum.sdg(target_qubit, is_bra)
        return new_pathsum

    # Apply CZ gate
    def cz(self, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[control_qubit], 1)
            x_j = logical_to_algebraic(self.f[target_qubit], 1)
            new_P = self.P + se.Rational(1, 2) * x_i * x_j
        else:
            x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            new_P = self.P + se.Rational(1, 2) * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply CRk gate
    def CRk(self, k: int, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[control_qubit], k)
            x_j = logical_to_algebraic(self.f[target_qubit], k)
            new_P = self.P + se.Rational(1, 2**k) * x_i * x_j
        else:
            x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            new_P = self.P + se.Rational(-1, 2**k) * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply CRk dagger gate
    def CRkdg(self, k: int, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            x_i = logical_to_algebraic(self.f[control_qubit], k)
            x_j = logical_to_algebraic(self.f[target_qubit], k)
            new_P = self.P + se.Rational(-1, 2**k) * x_i * x_j
        else:
            x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            new_P = self.P + se.Rational(1, 2**k) * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply CRZ gate
    def crz(self, theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        theta = div_pi(theta)
        if not is_bra:
            if theta.is_number:
                max_order = math.log2(theta.as_numer_denom()[1]) 
                max_order = int(max_order) +2 if int(max_order) == max_order else None
            else:
                max_order = None
            x_i = logical_to_algebraic(self.f[control_qubit], max_order=max_order)
            x_j = logical_to_algebraic(self.f[target_qubit], max_order=max_order)
            new_P = self.P + se.Rational(1, 4) * x_i * (-theta + 2 * theta * x_j)
        else:
            x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            new_P = self.P + se.Rational(1, 4) * x_i * (theta - 2 * theta * x_j)
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    # Apply CRY gate
    def cry(self, theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        
        # angle = se.pi / 2 
        # new_pathsum = self.crz(-angle, control_qubit, target_qubit, is_bra)
        # new_pathsum = new_pathsum.crx(theta, control_qubit, target_qubit, is_bra)
        # new_pathsum = new_pathsum.crz(angle, control_qubit, target_qubit, is_bra)
        # print('0',self)
        new_pathsum = self.ry(theta/2, target_qubit, is_bra)
        new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.ry(-theta/2, target_qubit, is_bra)
        new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
        return new_pathsum

    # Apply CRX gate
    def crx(self, theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        new_pathsum = self.h(target_qubit, is_bra)
        new_pathsum = new_pathsum.crz(theta, control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.h(target_qubit, is_bra)
        return new_pathsum

    # Apply CP gate
    def cp(self, theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        theta = div_pi(theta)
        if not is_bra:
            if theta.is_number:
                max_order = math.log2(theta.as_numer_denom()[1]) 
                max_order = int(max_order) +1 if int(max_order) == max_order else None
            else:
                max_order = None
            x_i = logical_to_algebraic(self.f[control_qubit], max_order=max_order)
            x_j = logical_to_algebraic(self.f[target_qubit], max_order=max_order)
            new_P = self.P + se.Rational(1, 2) * theta * x_i * x_j
        else:
            x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
            x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            new_P = self.P - se.Rational(1, 2) * theta * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, self.f, self.pathvar)

    def cu1(self, theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        return self.cp(theta, control_qubit, target_qubit, is_bra)

    def cu3(self, theta, phi, lam, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        new_pathsum = self.crz(lam, control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.cry(theta, control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.crz(phi, control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.cp(se.Rational(1, 2) * (phi + lam), control_qubit, target_qubit, is_bra)  # global phase
        return new_pathsum

    def cu(self, theta, phi, lam, gamma, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
        new_pathsum = self.cu3(theta, phi, lam, control_qubit, target_qubit, is_bra)
        new_pathsum = new_pathsum.cp(gamma, control_qubit, target_qubit, is_bra)
        return new_pathsum

    # Apply CCX gate
    def ccx(self, control_qubit1: int | str | se.Symbol, control_qubit2: int | str | se.Symbol, target_qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            new_f = self.f.update(target_qubit, to_anf(sp.Xor(self.f[target_qubit], sp.And(self.f[control_qubit1], self.f[control_qubit2]))))
            return PathSum(self.P, new_f, self.pathvar)
        else:
            x_i = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            x_j = se.symbols(f'{self.bits[control_qubit1]}' if isinstance(control_qubit1, int) else str(control_qubit1))
            x_k = se.symbols(f'{self.bits[control_qubit2]}' if isinstance(control_qubit2, int) else str(control_qubit2))
            new_var = sp.Xor(x_i, sp.And(x_j, x_k))
            update_var = logical_to_algebraic(new_var)
            new_P = self.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = self.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, self.pathvar)

    # Apply MCX gate
    def mcx(self, *qubits, is_bra: bool = False) -> 'PathSum':
        target_qubit = qubits[-1]
        control_qubits = qubits[0:-1]
        if not is_bra:
            new_f = self.f.update(target_qubit, to_anf(sp.Xor(self.f[target_qubit], sp.And([self.f[i] for i in control_qubits]))))
            return PathSum(self.P, new_f, self.pathvar)
        else:
            x_i = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
            x_j_list = [se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit)) for control_qubit in control_qubits]
            new_var = sp.Xor(x_i, sp.And(*x_j_list))
            update_var = logical_to_algebraic(new_var)
            new_P = self.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = self.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, self.pathvar)

    # Apply SWAP gate
    def swap(self, qubit1: int | str | se.Symbol, qubit2: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
        if not is_bra:
            new_P = self.P
            new_f = self.f.update(qubit1, self.f[qubit2])
            new_f = new_f.update(qubit2, self.f[qubit1])
        else:
            x_i = se.symbols(f'{self.bits[qubit1]}' if isinstance(qubit1, int) else str(qubit1))
            x_j = se.symbols(f'{self.bits[qubit2]}' if isinstance(qubit2, int) else str(qubit2))
            temp_sym = se.symbols('temp')
            new_P = self.P.subs({x_i:x_j, x_j:x_i})
            new_P = reduce_expression(new_P)
            # new_f = self.f.sub({x_i:temp_sym, x_j:x_i, temp_sym:x_j})
            new_f = self.f.sub(x_i,temp_sym)
            new_f = self.f.sub(x_j,x_i)
            new_f = self.f.sub(temp_sym,x_j)
        return PathSum(new_P, new_f, self.pathvar)

    def compose(self, other_pathsum: 'PathSum')-> 'PathSum':
        assert self.bits == other_pathsum.bits, f"Bits mismatch: {self.bits} != {other_pathsum.bits}"
        intersect = self.pathvar.intersection(other_pathsum.pathvar)
        temp_P = other_pathsum.P
        temp_f = other_pathsum.f
        new_vars_set = {}
        if intersect:
            temp_pathvar = self.pathvar.union(other_pathsum.pathvar)
            new_vars = find_new_variables(temp_pathvar, len(intersect))
            new_vars_set = set(new_vars)
            for var in intersect:
                new_var = new_vars.pop(0)
                temp_P = temp_P.subs(var, new_var)
                temp_f = temp_f.sub(var, new_var)
        for i in range(self.num_qubits):
            symbol = se.symbols(f'{self.bits[i]}')
            temp_P = temp_P.subs(symbol, logical_to_algebraic(self.f[i]))
            temp_f = temp_f.sub(symbol, self.f[i])
        new_P = self.P + temp_P
        new_f = temp_f
        new_pathvar = self.pathvar.union(other_pathsum.pathvar)
        if new_vars_set:
            new_pathvar = new_pathvar.union(new_vars_set)
        new_pathsum = PathSum(new_P, new_f, new_pathvar)
        new_pathsum = new_pathsum.reduction()
        return new_pathsum
    # Apply reduction
    def reduction(self) -> 'PathSum':
        if not self.is_reduction_enabled():
            return self
        
        new_P = reduce_expression(self.P)
        free_symbols = set().union(*map(lambda i: self.f[i].free_symbols, range(self.num_qubits)))
        f_var_names = {f_var.name for f_var in free_symbols}
        reducible_vars = tuple(filter(lambda x: x.name not in f_var_names, self.pathvar))
        if reducible_vars:
            # PathSum.reduction_counts['total'] += 1
            yo_val = match_Elim(new_P, reducible_vars)
            if yo_val is not None:
                new_pathvar = set(self.pathvar)
                new_pathvar.remove(yo_val)
                new_pathsum = PathSum(new_P, self.f, frozenset(new_pathvar))
                PathSum.reduction_counts['Elim'] += 1
                return new_pathsum.reduction()
            pathvar_as_tuple = tuple(self.pathvar)
            yo_val, Q_val, R_val, return_flag = match_omega(new_P, reducible_vars, pathvar_as_tuple, self.bits)
            if yo_val is not None:
                new_pathsum = omega_reduction(self, yo_val, Q_val, R_val, return_flag)
                PathSum.reduction_counts['omega'] += 1
                return new_pathsum.reduction()
            yo_val, yi_val, Q_val, R_val = match_HH(new_P, reducible_vars, pathvar_as_tuple, self.bits)
            if yo_val is not None:
                new_pathsum = HH_reduction(self, yo_val, yi_val, Q_val, R_val)
                PathSum.reduction_counts['HH'] += 1
                return new_pathsum.reduction()
        
        new_pathsum = PathSum(new_P, self.f, self.pathvar)
        return new_pathsum
# TODO: inverse (dagger), simulation, measure