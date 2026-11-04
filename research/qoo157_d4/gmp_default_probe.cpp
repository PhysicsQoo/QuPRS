// QOO-157 standalone read-only witness for jm62300/d4 C++/GMP arithmetic.
// Build: c++ -std=c++17 -O2 gmp_default_probe.cpp -lgmpxx -lgmp -o gmp-default-probe
// Important: this is NOT d4 and is NOT a solver accuracy certificate.
#include <gmpxx.h>
#include <iomanip>
#include <iostream>
#include <string>

int main() {
    std::cout << "GMP_VERSION=" << gmp_version
              << " DEFAULT_PREC_BITS=" << mpf_get_default_prec() << '\n';
    for (int k : {16, 19, 20, 24, 28, 32, 40, 60}) {
        const std::string re = "1." + std::string(k - 1, '0') + "1";
        const mpf_class positive(re, 10);
        const mpf_class negative("-1", 10);
        const mpf_class residual = positive + negative;
        std::cout << "k=" << k
                  << " operand_bits=" << positive.get_prec()
                  << " sum_bits=" << residual.get_prec()
                  << " residual=" << std::setprecision(65) << residual << '\n';
    }
    const mpf_class large("1000000000000000000000000000001", 10);
    const mpf_class opposite("-1000000000000000000000000000000", 10);
    const mpf_class diff = large + opposite;
    std::cout << "large_cancel_bits=" << diff.get_prec()
              << " residual=" << diff << '\n';
}
