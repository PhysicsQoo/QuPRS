"""Minimal Native API solver-boundary entrypoint for CodSpeed (no QuPRS imports)."""
import json
import sys

import rawmocs

result = rawmocs.solve_file(sys.argv[1], digits=30, timeout_ms=120000)
print(json.dumps(dict(sat=result.sat, real=result.real, imag=result.imag,
                      route=result.route, digits=result.digits, bits=result.precision_bits)))
