import re
import subprocess

import symengine as se
import sympy as sp
from sympy.logic.boolalg import And, Not, Or, Xor

from QuPRS.utils import WMC
from QuPRS.utils.util import algebraic_to_logical

counter = {"idx": 0}


def fresh_var():
    counter["idx"] += 1
    return sp.Symbol(f'e_{counter["idx"]-1}')


def extend_symbols_map(symbols_map, new_symbol):
    if new_symbol not in symbols_map:
        symbols_map[new_symbol] = len(symbols_map) + 1
    return symbols_map


# Convert a logical equivalence to CNF
def a_eq_b_cnf(a, b):
    if a == b:
        return sp.true
    return sp.to_cnf(Or(And(a, b), And(Not(a), Not(b))), simplify=True, force=True)


def encode_equivalence(c, cnf):
    if c == cnf:
        return sp.true
    cnf_clauses = []
    # cnf = and(a1, a2, ...) or or(o1, o2, ...), a1 = or(o1, o2, ...)
    if isinstance(cnf, And):
        args = cnf.args
        new_args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Or):
                args2 = arg.args
                new_args[i] = fresh_var()
                cnf_clauses.append(Or(Not(new_args[i]), *args2))  # e -> or(o1, o2, ...)
                cnf_clauses.extend(
                    [Or(Not(arg2), new_args[i]) for arg2 in args2]
                )  # or(o1, o2, ...) -> e
            elif isinstance(arg, sp.Symbol) or isinstance(arg, Not):
                continue
            else:
                raise ValueError(f"Unsupported CNF clause {arg} type {type(arg)}")

        cnf_clauses.append(
            Or(c, *[Not(arg) for arg in new_args])
        )  # and(a1, a2, ...) -> c
        cnf_clauses.extend(
            [Or(Not(c), arg) for arg in new_args]
        )  # c-> and(a1, a2, ...)
    elif isinstance(cnf, Or):
        args = cnf.args
        cnf_clauses.append(Or(Not(c), *args))  # c -> or(o1, o2, ...)
        cnf_clauses.extend([Or(Not(arg), c) for arg in args])  # or(o1, o2, ...) -> c
    elif (
        isinstance(cnf, Not) or isinstance(cnf, sp.Symbol) or isinstance(cnf, se.Symbol)
    ):
        cnf_clauses.append(Or(Not(c), cnf))  # c -> o1
        cnf_clauses.append(Or(Not(cnf), c))  # o1 -> c
    elif cnf == sp.true:
        cnf_clauses.append(c)  # c -> True
    elif cnf == sp.false:
        cnf_clauses.append(Not(c))  # c -> False
    else:
        raise ValueError(f"Unsupported CNF clause {cnf} type {type(cnf)}")
    return And(*cnf_clauses)


def anf_to_cnf(anf):
    """
    Convert ANF to CNF using Tseitin transformation.
    """
    if (
        anf == sp.true
        or anf == sp.false
        or isinstance(anf, sp.Symbol)
        or isinstance(anf, se.Symbol)
        or isinstance(anf, And)
    ):
        return (anf,)

    clauses = []

    def tseitin(c, anf):  # c <-> anf
        # print(f"tseitin: {c} <-> {anf}")
        if anf == sp.true:
            clauses.append(c)
        elif anf == sp.false:
            clauses.append(Not(c))
        elif isinstance(anf, Not):
            args = anf.args
            if isinstance(args[0], And):
                a = fresh_var()
                tseitin(a, args[0])
            elif isinstance(args[0], Xor):
                a = fresh_var()
                tseitin(a, Xor(*args[0].args))
            else:
                a = args[0]
            clauses.append(Or(Not(c), Not(a)))  # c -> Not(a)
            clauses.append(Or(c, a))  # Not(a) -> c
        elif isinstance(anf, Xor):
            args = anf.args
            if isinstance(args[0], And):
                a = fresh_var()
                tseitin(a, args[0])
            else:
                a = args[0]

            if len(args) > 2:
                b = fresh_var()
                tseitin(b, Xor(*args[1:]))
            elif isinstance(args[1], And):
                b = fresh_var()
                tseitin(b, args[1])
            else:
                b = args[1]

            clauses.extend(
                [
                    Or(Not(a), Not(b), Not(c)),
                    Or(a, b, Not(c)),
                    Or(a, Not(b), c),
                    Or(Not(a), b, c),
                ]
            )  # c <-> a xor b

        elif isinstance(anf, And):
            args = anf.args
            clauses.extend([Or(Not(c), arg) for arg in args])  # c -> anf
            clauses.append(Or(c, *[Not(arg) for arg in args]))  # anf -> c
        elif isinstance(anf, sp.Symbol) or isinstance(anf, se.Symbol):
            clauses.append(Or(Not(c), anf))  # c -> anf
            clauses.append(Or(c, Not(anf)))  # anf -> c
        else:
            raise ValueError(f"Unsupported ANF clause {anf} type {type(anf)}")

    new_var = fresh_var()
    tseitin(new_var, anf)
    # print(f"clauses: {clauses}")
    return (new_var, And(*clauses))


# Convert polynomial P to weighted logical expressions
def P_to_wlogi(P):
    if P == 0:
        return []
    args = P.as_coefficients_dict()
    output = [
        (
            (v, algebraic_to_logical(k))
            if v != 0 and v != 1
            else (k, algebraic_to_logical(v))
        )
        for k, v in args.items()
        if v != 0
    ]
    return output


# Convert CNF to clauses
def cnf_to_clauses(cnf, symbols_map, flag=False):
    if isinstance(cnf, And):
        return [cnf_to_clauses(arg, symbols_map, flag) for arg in cnf.args]
    elif isinstance(cnf, Or):
        clause = (
            " ".join(cnf_to_clauses(arg, symbols_map, flag=True) for arg in cnf.args)
            + " 0"
        )
        return clause
    elif isinstance(cnf, Not):
        return f"-{cnf_to_clauses(cnf.args[0], symbols_map, flag)}"
    elif isinstance(cnf, sp.Symbol):
        clause = f"{symbols_map[cnf] }"
        return clause if flag else [clause + " 0"]
    elif cnf == sp.true:
        return []
    else:
        raise ValueError(f"Invalid CNF: {cnf}")


# Convert weighted logical expressions to clauses
def wlogi_to_clauses(wlogi_list, symbols_map):
    clauses = []
    weights = []
    z = sp.symbols(f"z_:{len(wlogi_list)}")
    l = len(symbols_map)
    for symbol in z:
        extend_symbols_map(symbols_map, symbol)
    for i, (w, logi) in enumerate(wlogi_list):
        weights.append(
            f"c p weight {l + i + 1} {se.cos(2*se.pi*w).evalf()} {se.sin(2*se.pi*w).evalf()} 0"
        )
        idx = counter["idx"]
        temp = encode_equivalence(z[i], logi)
        for i in range(idx, counter["idx"]):
            extend_symbols_map(symbols_map, sp.Symbol(f"e_{i}"))
        clauses.extend(cnf_to_clauses(temp, symbols_map))
    return weights, clauses, symbols_map


# Convert PathSum object to DIMACS format
def to_DIMACS(pathsum, filename="wmc.cnf"):
    counter["idx"] = 0
    free_symbols_list = [sp.Symbol(item) for item in pathsum.bits]
    free_symbols_list.extend(sp.sympify(free_symbol) for free_symbol in pathsum.pathvar)
    symbols_map = {}
    for symbol in free_symbols_list:
        extend_symbols_map(symbols_map, symbol)

    weights, clauses, symbols_map = wlogi_to_clauses(P_to_wlogi(pathsum.P), symbols_map)
    for qubit in range(pathsum.num_qubits):
        a = sp.Symbol(pathsum.bits[qubit])
        idx = counter["idx"]
        b = anf_to_cnf(pathsum.f[qubit])
        if len(b) == 1:
            b = b[0]
        else:
            for i in range(idx, counter["idx"]):
                extend_symbols_map(symbols_map, sp.Symbol(f"e_{i}"))
            clauses.extend(cnf_to_clauses(b[1], symbols_map))
            b = b[0]
        temp = encode_equivalence(a, b)
        clauses.extend(cnf_to_clauses(temp, symbols_map))

    DIMACS_text = f"p cnf {len(symbols_map)} {len(clauses)}\nc t wmc"
    DIMACS_text += "\n" + "\n".join(weights + clauses)
    with open(filename, "w") as file:
        file.write(DIMACS_text.strip())
    return DIMACS_text


def run_wmc(file="wmc.cnf"):
    result = subprocess.run(
        [str(WMC()), "-mode=1", file], capture_output=True, text=True
    )

    output_lines = result.stdout.split("\n")

    for line in output_lines:
        if line.startswith("c s exact double prec-sci"):
            match = re.search(
                r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)([-+]\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)i",
                line,
            )
            if match:
                real_part = float(match.group(1))
                imag_part = float(match.group(2))
                return real_part, imag_part
            match = re.search(r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", line)
            if match:
                real_part = float(match.group(1))
                imag_part = 0
                return real_part, imag_part
            match = re.search(r"([-+]\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)i", line)
            if match:
                real_part = 0
                imag_part = float(match.group(1))
                return real_part, imag_part
    assert False, "WMC output format error, result: {}".format(result.stdout)


if __name__ == "__main__":
    # from pathsum.pathsum import PathSum, F, Register
    # y = se.symbols('y_:2')
    # x = se.symbols('x_:2')
    # P = se.Rational(1, 2) * x[0] * y[0] + se.Rational(1, 2) * y[0] * y[1]

    # reg = Register(2)
    # data = {reg[0].name: y[1]}
    # bits = tuple(data.keys())
    # f = F(reg, data=data, bits=bits)

    # pathvar = frozenset(y)
    # circuit = PathSum(P, f, pathvar)

    # print(to_DIMACS(circuit, filename='wmc.cnf'))
    # print("result:",run_wmc(file='wmc.cnf'))

    x = sp.symbols("x_:10")
    # A = sp.Symbol('A')
    # B = And(Or(x,y),z)
    A = x[0]
    B = (x[3] | x[4] | ~x[1]) & (x[3] | x[1] | ~x[4]) & (x[4] | x[1] | ~x[3])
    # & (x[4] | x[2] | ~x[5]) & (x[4] | x[5] | ~x[2]) & (x[2] | x[5] | ~x[4]) & (~x[3] | ~x[4] | ~x[1]) & (~x[4] | ~x[2] | ~x[5])

    eq_cnf = encode_equivalence(A, B)
    print(eq_cnf)

    # anf = Xor(*x)
    # print('anf:', anf)
    # cnf = anf_to_cnf(anf)
    # print('cnf:', cnf)
