"""Solver-neutral bounded weighted-CNF contract.

Keep real/imag components as original numeric objects; never implicitly
convert a SymEngine 113-bit component into Python float.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class WmcWeight:
    variable: int
    real: object
    imag: object


@dataclass(frozen=True)
class WmcProblem:
    variables: int
    clauses: tuple[tuple[int, ...], ...]
    weights: tuple[WmcWeight, ...] = ()

    def __post_init__(self):
        if type(self.variables) is not int or self.variables < 0:
            raise ValueError("CNF variable count must be nonnegative integer")
        for clause in self.clauses:
            if not isinstance(clause, tuple):
                raise ValueError("CNF clauses must be tuples")
            for literal in clause:
                if type(literal) is not int or not 1 <= abs(literal) <= self.variables:
                    raise ValueError("CNF literal outside declared variable range")
        seen = set()
        for weight in self.weights:
            if not isinstance(weight, WmcWeight):
                raise ValueError("Invalid CNF weight")
            if type(weight.variable) is not int or not 1 <= weight.variable <= self.variables:
                raise ValueError("Weighted variable outside declared range")
            if weight.variable in seen:
                raise ValueError("Duplicate weighted CNF variable")
            seen.add(weight.variable)

    def serialize(self, adapter):
        """Adapt the source precision without changing its numeric type.

        A weighted variable's negative literal always has weight 1+0i,
        matching the current native PathSum encodings. This initial contract
        does not support independently weighted negative literals.
        """
        if not adapter.capabilities.complex_weights:
            raise ValueError("Selected solver cannot encode complex weights")
        lines = [f"p cnf {self.variables} {len(self.clauses)}", "c t wmc"]
        for weight in self.weights:
            positive, negative = adapter.format_weights(weight.real, weight.imag)
            lines.append(f"c p weight {weight.variable} {positive}")
            lines.append(f"c p weight -{weight.variable} {negative}")
        for clause in self.clauses:
            lines.append(" ".join([*(str(literal) for literal in clause), "0"]))
        return "\n".join(lines)
