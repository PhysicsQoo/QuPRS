/* Experiment-only MPFR weight bridge, never linked into production.
 * Accepts decimal integer numerators/denominators from native PhaseCoeff.
 * Returns exp(i*(2*pi*cycles+2*radians)) with MPFR precision, not f64.
 */
#include <stdio.h>
#include <mpfr.h>
#include <stddef.h>
#include <string.h>

static int set_ratio(mpfr_t result, const char *numer, const char *denom) {
    mpfr_prec_t p = mpfr_get_prec(result);
    mpfr_t n, d;
    mpfr_init2(n, p);
    mpfr_init2(d, p);
    int status = 0;
    if (mpfr_set_str(n, numer, 10, MPFR_RNDN) != 0) status = -1;
    if (mpfr_set_str(d, denom, 10, MPFR_RNDN) != 0 || mpfr_zero_p(d)) status = -2;
    if (status == 0) mpfr_div(result, n, d, MPFR_RNDN);
    mpfr_clear(d);
    mpfr_clear(n);
    return status;
}

int quprs_exp_mpfr_phase_weight(
    const char *cycles_num, const char *cycles_den,
    const char *radians_num, const char *radians_den,
    unsigned long precision_bits, char *out_real, char *out_imag, size_t cap
) {
    if (!cycles_num || !cycles_den || !radians_num || !radians_den ||
        !out_real || !out_imag || cap < 64 || precision_bits < 128 ||
        precision_bits > 1024) return -3;
    mpfr_t pi, cycles, radians, angle, sine, cosine;
    mpfr_init2(pi, precision_bits);
    mpfr_init2(cycles, precision_bits);
    mpfr_init2(radians, precision_bits);
    mpfr_init2(angle, precision_bits);
    mpfr_init2(sine, precision_bits);
    mpfr_init2(cosine, precision_bits);
    int status = 0;
    if (set_ratio(cycles, cycles_num, cycles_den) != 0 ||
        set_ratio(radians, radians_num, radians_den) != 0) {
        status = -4;
        goto done;
    }
    mpfr_const_pi(pi, MPFR_RNDN);
    mpfr_mul(angle, cycles, pi, MPFR_RNDN);
    mpfr_add(angle, angle, radians, MPFR_RNDN);
    mpfr_mul_ui(angle, angle, 2u, MPFR_RNDN);
    mpfr_sin_cos(sine, cosine, angle, MPFR_RNDN);
    int nr = mpfr_snprintf(out_real, cap, "%.47Re", cosine);
    int ni = mpfr_snprintf(out_imag, cap, "%.47Re", sine);
    if (nr < 0 || ni < 0 || (size_t)nr >= cap || (size_t)ni >= cap)
        status = -5;
done:
    mpfr_clear(cosine);
    mpfr_clear(sine);
    mpfr_clear(angle);
    mpfr_clear(radians);
    mpfr_clear(cycles);
    mpfr_clear(pi);
    return status;
}
