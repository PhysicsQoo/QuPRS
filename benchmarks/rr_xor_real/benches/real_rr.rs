//! Native CodSpeed Simulation of whole actual-QASM miter+RR, and sampled
//! HH-only phase-polynomial substitution replay from the same miter.
//! The replay is a bounded diagnostic workload: its ratio to whole miter+RR
//! is a cost proxy, NOT an exact fraction of RR stage CPU. The official
//! CodSpeed flamegraph of the whole benchmark is the preferred attribution.
use divan::Bencher;
use quprs_rr_xor_real_witness::{case_data, trace, Case};
use pathsum::{PathSum, VerificationStrategy};

fn run_real(bencher: Bencher, which: Case) {
    // Parsing and cloning the QASM IR are outside the timed span.
    let source = case_data(which);
    bencher.with_inputs(|| (source.n, source.base.clone(), source.candidate.clone()))
        .bench_values(|(n, left, right)| {
            let mut ps = PathSum::new(n);
            ps.rr_tolerance = 1e-10;
            let mut residual = VerificationStrategy::Proportional.run(
                ps, divan::black_box(&left), divan::black_box(&right));
            residual.full_reduce();
            divan::black_box(residual)
        });
}

fn replay_hh(bencher: Bencher, which: Case) {
    bencher.with_inputs(|| trace(which).samples.clone())
        .bench_values(|mut samples| {
            for entry in &mut samples {
                entry.polynomial.substitute_var_with_poly(
                    divan::black_box(entry.target),
                    divan::black_box(&entry.replacement),
                );
            }
            divan::black_box(samples);
        });
}

fn main() {
    for case in Case::ALL {
        let _ = (case_data(case), trace(case));
    }
    divan::main();
}

#[divan::bench] fn qft16_miter_rr(bencher: Bencher) { run_real(bencher, Case::Qft16); }
#[divan::bench] fn qft16_hh_phase_replay(bencher: Bencher) { replay_hh(bencher, Case::Qft16); }

#[divan::bench] fn qpeexact8_miter_rr(bencher: Bencher) { run_real(bencher, Case::QpeExact8); }
#[divan::bench] fn qpeexact8_hh_phase_replay(bencher: Bencher) { replay_hh(bencher, Case::QpeExact8); }

#[divan::bench] fn qpeinexact8_miter_rr(bencher: Bencher) { run_real(bencher, Case::QpeInexact8); }
#[divan::bench] fn qpeinexact8_hh_phase_replay(bencher: Bencher) { replay_hh(bencher, Case::QpeInexact8); }

#[divan::bench] fn vqe4_miter_rr(bencher: Bencher) { run_real(bencher, Case::Vqe4); }
#[divan::bench] fn vqe4_hh_phase_replay(bencher: Bencher) { replay_hh(bencher, Case::Vqe4); }
