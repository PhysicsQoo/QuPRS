// Bounded research-only probe of the exact MPFR stream printer bundled by
// pinned GPMC. No product source or solver behavior is modified.
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
#include <gmpxx.h>
#include "mpfr/mpreal.h"

int main() {
    constexpr int DECIMAL_DIGITS = 90;
    mpfr::mpreal::set_default_prec(mpfr::digits2bits(DECIMAL_DIGITS));
    const int actual_digits = mpfr::bits2digits(mpfr::mpreal::get_default_prec());
    std::cout << "PRINTER_PRECISION\t" << actual_digits << "\t"
              << mpfr::mpreal::get_default_prec() << "\n";
    const std::vector<std::pair<std::string,std::string>> cases = {
        {"exact_one", "1"},
        {"exact_negative_two", "-2"},
        {"near_one_above", "1.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001"},
        {"near_one_below", "0.999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"},
        {"small_positive", "0.000000000000000000000000000000000000000000000000000000000001234567890123456789"},
        {"huge_positive", "12345678901234567890123456789012345678901234567890123456789012345678901234567890"},
        {"negative_fractional", "-1.234567890123456789012345678901234567890123456789012345678901234567890123456789"},
        {"zero", "0"}
    };
    for (const auto& item : cases) {
        mpfr::mpreal x;
        if (mpfr_set_str(x.mpfr_ptr(), item.second.c_str(), 10, MPFR_RNDN) != 0) {
            // MPFR returns nonzero on inexact conversion; expected and useful.
        }
        if (!mpfr_number_p(x.mpfr_srcptr())) return 2;
        std::ostringstream stream;
        stream.precision(actual_digits);
        stream << x;  // GPMC's actual no-fixed/no-scientific mpreal printer.
        mpz_class significand;
        const mp_exp_t binary_exp = mpfr_get_z_2exp(
            significand.get_mpz_t(), x.mpfr_srcptr()
        );
        std::cout << "PRINTED_VALUE\t" << item.first << "\t"
                  << item.second << "\t" << stream.str() << "\t"
                  << significand << "\t" << binary_exp << "\n";
    }
}
