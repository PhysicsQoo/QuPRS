//! Identical source in Base and HEAD; exactly actual QASM Miter + RR.
use divan::Bencher;
use pathsum::{PathSum, VerificationStrategy};
use quprs_rr_cx_qft16_paired::{source, bra_cx_fixture, Case, CoeffCase};
use pathsum::gates::{QuantumGates, Side};

fn bench_case(bencher: Bencher, case: Case) {
    let c = source(case);
    // QASM parse, input materialization and cloning are OUTSIDE the
    // measured CodSpeed Simulation span, in both identical-source versions.
    bencher.with_inputs(|| (c.n, c.left.clone(), c.right.clone()))
        .bench_values(|(n, left, right)| {
            let mut ps = PathSum::new(n);
            ps.rr_tolerance = 1e-10;
            let mut residual = VerificationStrategy::Proportional.run(
                ps, divan::black_box(&left), divan::black_box(&right));
            residual.full_reduce();
            divan::black_box(residual);
        });
}

fn main() {
    for case in Case::ALL { let _ = source(case); }
    divan::main();
}

#[divan::bench]
fn real_qft16_miter_rr(bencher: Bencher) { bench_case(bencher, Case::Qft16); }

#[divan::bench]
fn real_qpeexact8_miter_rr(bencher: Bencher) { bench_case(bencher, Case::QpeExact8); }

fn bench_bra_cx_coeff(bencher: Bencher, which: CoeffCase) {
    // The fixed-source coefficients and PhasePolynomial are constructed in
    // setup, not in the official CodSpeed CPU measured interval.
    bencher.with_inputs(|| bra_cx_fixture(which))
        .bench_values(|mut state| {
            state.apply_cx(1, 0, Side::Bra);
            divan::black_box(state);
        });
}

#[divan::bench]
fn exact_bra_cx_decimal(bencher: Bencher) {
    bench_bra_cx_coeff(bencher, CoeffCase::Decimal);
}

#[divan::bench]
fn exact_bra_cx_mixed(bencher: Bencher) {
    bench_bra_cx_coeff(bencher, CoeffCase::Mixed);
}
