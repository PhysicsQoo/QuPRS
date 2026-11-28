// Thin CLI around the existing QuPRS MPFR bridge; no numerical reimplementation.
#include "PhaseWeights.hpp"
int main(int argc, char **argv) {
  try {
    if(argc != 2) return 2;
    const auto path=quprs_source_weights(argv[1]);
    std::ifstream in(path);
    if(!in) return 2;
    std::ofstream out("/materialized.cnf");
    out << in.rdbuf();
    out.close();
    return out ? 0 : 2;
  } catch(const std::exception& e) { std::cerr<<e.what()<<std::endl; return 2; }
}
