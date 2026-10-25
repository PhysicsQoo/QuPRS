"""Stdlib-only exact source-RZ proof and raw weighted-CNF Boolean witness check.

This deliberately does not import the reference interval library. It proves
the ideal one-qubit source-model non-equivalence conditional on the checked
CNF Boolean structure, NOT compiler soundness or printed-weight accuracy.
"""
from decimal import Decimal, InvalidOperation
from fractions import Fraction as F
from hashlib import sha256
import re

SOURCE = ('OPENQASM 2.0;\ninclude "qelib1.inc";\n'
          'qreg q[1];\nrz(0.0002) q[0];\n').encode("ascii")
UNIT = (F(1), F(0))
_DEC = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def decimal(token):
    require(len(token) <= 120 and _DEC.fullmatch(token) is not None,
            "Unsupported complex weight decimal")
    try:
        number = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("Invalid complex weight") from exc
    require(number.is_finite() and abs(number.as_tuple().exponent) <= 120,
            "Unsafe complex weight")
    return F(number)


def parse_weight(fields, dialect):
    if dialect == "gpmc":
        require(len(fields) == 3 and fields[-1] == "0",
                "Malformed GPMC weight")
        return decimal(fields[0]), decimal(fields[1])
    require(dialect == "ganak" and len(fields) == 4
            and fields[1] in ("+", "-") and fields[2].endswith("i")
            and fields[-1] == "0", "Malformed Ganak weight")
    imag = decimal(fields[2][:-1])
    require(imag >= 0, "Ganak imaginary magnitude must be positive")
    return decimal(fields[0]), imag if fields[1] == "+" else -imag


def parse_raw_cnf(raw, dialect):
    require(isinstance(raw, bytes) and 0 < len(raw) < 400_000
            and dialect in ("gpmc", "ganak"), "Unsupported raw CNF")
    lines = raw.decode("ascii").splitlines()
    n = expected = None
    marked = False
    clauses, weight_records = [], {}
    for line in lines:
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "p":
            require(n is None and len(fields) == 4
                    and fields[:2] == ["p", "cnf"], "Invalid CNF header")
            n, expected = int(fields[2]), int(fields[3])
            require(1 <= n <= 12 and 0 <= expected <= 1000, "Oversized CNF")
        elif fields[:2] == ["c", "t"]:
            require(n is not None and not marked
                    and fields == ["c", "t", "wmc"], "Invalid WMC marker")
            marked = True
        elif fields[:3] == ["c", "p", "weight"]:
            require(n is not None and marked and len(fields) >= 7,
                    "Weight before WMC marker")
            lit = int(fields[3])
            require(lit != 0 and abs(lit) <= n and lit not in weight_records,
                    "Duplicate or out-of-range literal weight")
            weight_records[lit] = parse_weight(fields[4:], dialect)
        else:
            require(n is not None and marked and fields[0] != "c"
                    and fields[-1] == "0", "Invalid CNF clause")
            clause = tuple(int(x) for x in fields[:-1])
            require(all(x and abs(x) <= n for x in clause),
                    "Invalid CNF literal")
            clauses.append(clause)
    require(n is not None and marked and len(clauses) == expected,
            "Incorrect CNF clause count")
    weights = tuple((weight_records.get(i, UNIT), weight_records.get(-i, UNIT))
                    for i in range(1, n+1))
    return clauses, weights


def parse_rust_roles(tsv):
    require(isinstance(tsv, bytes) and len(tsv) < 4096, "Missing Rust phases")
    rows = tsv.decode("ascii").splitlines()
    require(len(rows) == 3 and rows[0] ==
            "weight_lit\tphase_numerator\tphase_denominator\tmonomial",
            "Invalid Rust phase header/count")
    roles = {}
    for row in rows[1:]:
        f = row.split("\t")
        require(len(f) == 4 and f[3] in ("", "0") and f[3] not in roles,
                "Invalid Rust phase monomial")
        lit, numerator, denominator = map(int, f[:3])
        require(lit > 0 and denominator > 0 and 0 <= numerator < denominator,
                "Invalid Rust phase rational")
        roles["constant" if f[3] == "" else "bit"] = lit
    require(set(roles) == {"constant", "bit"}, "Incomplete Rust phases")
    return roles


def independent_source_check(qasm, raw_cnf, backend, dialect, rust_tsv=None):
    require(isinstance(qasm, bytes) and qasm == SOURCE,
            "Unsupported exact source QASM")
    require(backend in ("python", "rust"), "Unsupported backend")
    # No sin, cos, pi, square-root or interval library calls.
    delta = F("0.0002")
    x = delta / 2
    lower = 1 - x*x/2
    upper = lower + x**4/24
    require(0 < lower < upper < 1, "Source strict cosine bound failed")
    clauses, weights = parse_raw_cnf(raw_cnf, dialect)
    nonunit = {i for i,(p,neg) in enumerate(weights,1) if p != UNIT}
    require(len(nonunit) == 2 and all(neg == UNIT for _,neg in weights),
            "Unattributed positive or negative phase weight")
    if backend == "python":
        source_var, roles = 1, {}
        require(weights[0] == (UNIT, UNIT), "Python input bit has weight")
    else:
        roles = parse_rust_roles(rust_tsv)
        remaining = set(range(1, len(weights)+1)) - nonunit
        require(len(weights) == 3 and set(roles.values()) == nonunit
                and len(remaining) == 1, "Invalid Rust phase binding")
        source_var = remaining.pop()
        require(weights[source_var-1] == (UNIT,UNIT),
                "Rust input is nonunit weighted")
    witnesses = [[], []]
    for bits in range(1 << len(weights)):
        if all(any(bool(bits & (1 << (abs(lit)-1))) == (lit > 0)
                   for lit in clause) for clause in clauses):
            witnesses[int(bool(bits & (1 << (source_var-1))))].append(bits)
    require(all(len(x) == 1 for x in witnesses),
            "CNF does not have a unique extension for each input")
    zero, one = witnesses[0][0], witnesses[1][0]
    active = lambda bits, i: bool(bits & (1 << (i-1)))
    if backend == "python":
        for var in nonunit:
            pattern = (active(zero,var), active(one,var))
            kind = {(True, True):"constant", (False, True):"bit"}.get(pattern)
            require(kind is not None and kind not in roles,
                    "Unattributed Python phase activation")
            roles[kind] = var
        require(set(roles) == {"constant", "bit"}, "Missing phase variables")
    require(active(zero,roles["constant"]) and active(one,roles["constant"])
            and not active(zero,roles["bit"]) and active(one,roles["bit"]),
            "CNF activation does not follow source bit")
    return {
        "kind": "independent_source_analytic_negative",
        "source_sha256": sha256(qasm).hexdigest(),
        "cnf_sha256": sha256(raw_cnf).hexdigest(),
        "backend": backend, "solver": dialect,
        "source_angle_radians": str(delta),
        "analytic_cosine_lower": str(lower),
        "analytic_cosine_upper": str(upper),
        "unique_witnesses": [str(zero), str(one)],
        "constant_phase_literal": roles["constant"],
        "bit_phase_literal": roles["bit"],
        "source_semantics_conditional": True,
        "printed_weight_bound_claimed": False,
        "general_compiler_certified": False,
        "native_solver_certified": False,
    }
