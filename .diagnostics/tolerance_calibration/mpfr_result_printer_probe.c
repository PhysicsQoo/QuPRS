/* Diagnostic-only reproduction of the Ganak mode-6 MPFR result printer.
 * This does not alter the pinned Ganak binary or its output contract. */
#include <mpfr.h>
#include <stdio.h>

int main(void) {
    mpfr_t count;
    mpfr_init2(count, 256);
    if (mpfr_set_str(count, "0.99999999999999994746875", 10, MPFR_RNDN) != 0) {
        mpfr_clear(count);
        return 1;
    }
    mpfr_printf("short %.8Re\n", count);
    mpfr_printf("long %.40Re\n", count);
    mpfr_clear(count);
    return 0;
}
