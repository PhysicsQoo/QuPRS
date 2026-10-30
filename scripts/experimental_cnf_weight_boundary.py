"""Diagnostic only: compare the source-verified Rust f64 CNF phase-weight
formula to a 130-decimal-digit reference and a 113-bit Python-side surrogate.

No native Rust, SymEngine, emitted CNF, GPMC or Ganak execution is performed.
Run: python scripts/experimental_cnf_weight_boundary.py
Requires: mpmath 1.3+.
"""
from fractions import Fraction
import json
import math
import mpmath as mp

# Pi coefficients and additional radians are exact rational strings.
CASES = (
    ("small_nonzero", "0", "0.00000002"),
    ("rz_scale", "0", "0.0002"),
    ("pi_half_small_residual", "1/2", "1e-20"),
    ("pi_half_tiny_residual", "1/2", "1e-40"),
    ("pi_half_exact", "1/2", "0"),
    ("quarter_pi_tiny_residual", "1/4", "1e-40"),
    ("tiny_radian_only", "0", "1e-40"),
    ("small_negative", "0", "-1e-9"),
)

def exact_mp(x):
    return mp.mpf(x.numerator) / mp.mpf(x.denominator)

def investigate(name, pi_string, rad_string):
    p, r = Fraction(pi_string), Fraction(rad_string)
    # These operations match rust/pathsum/src/wmc.rs's f64 boundary.
    p64 = float(p.numerator) / float(p.denominator)
    r64 = float(r)
    base64 = p64 * 2.0 * math.pi
    angle64 = base64 + 2.0 * r64
    real64, imag64 = math.cos(angle64), math.sin(angle64)
    # Rust {:.16e} emits 17 significant digits: enough for f64 round-trip.
    re_text, im_text = f"{real64:.16e}", f"{imag64:.16e}"
    assert float(re_text).hex() == real64.hex()
    assert float(im_text).hex() == imag64.hex()
    with mp.workdps(130):
        true_angle = 2 * mp.pi * exact_mp(p) + 2 * exact_mp(r)
        ref = mp.mpc(mp.cos(true_angle), mp.sin(true_angle))
        printed = mp.mpc(mp.mpf(re_text), mp.mpf(im_text))
        err64 = mp.nstr(abs(ref - printed), 12)
        defect = mp.nstr(abs(printed.real**2 + printed.imag**2 - 1), 12)
        # mpmath at 113 bits is only a surrogate, NOT SymEngine evalf.
        with mp.workprec(113):
            angle113 = 2 * mp.pi * exact_mp(p) + 2 * exact_mp(r)
            re113, im113 = +mp.cos(angle113), +mp.sin(angle113)
            re113_text, im113_text = mp.nstr(re113, 35), mp.nstr(im113, 35)
        surrogate = mp.mpc(mp.mpf(re113_text), mp.mpf(im113_text))
        err113 = mp.nstr(abs(ref - surrogate), 12)
        return {
            "case": name, "pi_coefficient": str(p), "additional_radians": str(r),
            "rust_f64_real_text": re_text, "rust_f64_imag_text": im_text,
            "rust_f64_roundtrip": True,
            "f64_residual_swallowed_by_addition": r != 0 and angle64 == base64,
            "rust_f64_emitted_absolute_error": err64,
            "rust_f64_emitted_unit_norm_squared_defect": defect,
            "surrogate_113_bit_real": re113_text,
            "surrogate_113_bit_imag": im113_text,
            "surrogate_113_bit_absolute_error": err113,
        }

def main():
    result = {
        "scope": "isolated phase weight numerical boundary; no actual CNF or solver",
        "python_high_precision": "mpmath surrogate, not SymEngine",
        "reference_digits": 130,
        "formula": "angle = 2*pi*float(exact_pi_coeff) + 2*float(exact_radians)",
        "cases": [investigate(*row) for row in CASES],
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
