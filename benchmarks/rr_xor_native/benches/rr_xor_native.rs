//! Solver-free CodSpeed Simulation. Input construction and cloning run
//! in Divan with_inputs (outside the measured operation). Every benchmark
//! calls the real production PhasePolynomial::substitute_var_with_poly.
use divan::Bencher;
use quprs_rr_xor_native::{fixture, Case, TARGET};

fn run_case(bencher: Bencher, case: Case) {
    bencher.with_inputs(|| fixture(case))
        .bench_values(|(mut polynomial, replacement)| {
            polynomial.substitute_var_with_poly(
                divan::black_box(TARGET),
                divan::black_box(&replacement),
            );
            divan::black_box(polynomial);
        });
}

fn main() {
    divan::main();
}

#[divan::bench]
fn rr_xor_shared_clifford3(bencher: Bencher) {
    run_case(bencher, Case::Clifford3);
}

#[divan::bench]
fn rr_xor_shared_decimal5(bencher: Bencher) {
    run_case(bencher, Case::Decimal5);
}

#[divan::bench]
fn rr_xor_shared_mixed5(bencher: Bencher) {
    run_case(bencher, Case::Mixed5);
}

#[divan::bench]
fn rr_xor_shared_symbolic5(bencher: Bencher) {
    run_case(bencher, Case::Symbolic5);
}
