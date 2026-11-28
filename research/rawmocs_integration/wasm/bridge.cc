// Thin transport wrapper for the original QuPRS PhaseWeights.hpp and MPFR C bridge.
// No solver arithmetic or phase reimplementation.
#include "PhaseWeights.hpp"
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    try {
        std::ifstream probe(argv[1]);
        if (!probe) return 2;
        probe.close();
        const auto path = quprs_source_weights(argv[1]);
        std::ifstream input(path, std::ios::binary);
        std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
        if (!input || !output) return 2;
        output << input.rdbuf();
        output.close();
        return input.bad() || !output ? 2 : 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 2;
    }
}
