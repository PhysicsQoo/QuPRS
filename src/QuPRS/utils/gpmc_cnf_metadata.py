"""Read the exact decimal weight magnitudes and variable count for GPMC.

Only a conservative workload eligibility check. The GPMC result is still
verified from a separately collected, precision-replayed PrintedCount.
"""
from decimal import Decimal, InvalidOperation
from fractions import Fraction


def gpmc_cnf_budget_metadata(dimacs: str):
    n = None
    weight_ids = set()
    max_sq = Fraction(0)
    for line in dimacs.splitlines():
        if line.startswith("p cnf "):
            tokens = line.split()
            if len(tokens) != 4 or n is not None:
                raise ValueError("Malformed CNF header")
            n = int(tokens[2])
            if n < 0:
                raise ValueError("Negative CNF variable count")
        elif line.startswith("c p weight "):
            tokens=line.split()
            if len(tokens) != 7 or tokens[-1] != "0":
                raise ValueError("Malformed GPMC literal weight")
            var=int(tokens[3])
            if var < 0:
                continue
            if var == 0 or var in weight_ids:
                raise ValueError("Duplicate or invalid positive GPMC weight")
            weight_ids.add(var)
            try:
                real=Fraction(Decimal(tokens[4]))
                imag=Fraction(Decimal(tokens[5]))
            except (InvalidOperation, ValueError, OverflowError) as exc:
                raise ValueError(
                    "Invalid decimal CNF weight: "
                    + repr((tokens[4][:64], tokens[5][:64]))
                ) from exc
            max_sq=max(max_sq, real*real+imag*imag)
    if n is None or any(i > n for i in weight_ids):
        raise ValueError("CNF weight metadata inconsistent")
    return n,len(weight_ids),max_sq
