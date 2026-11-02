//! Native, solver-free Rust core diagnostics. Independent of the 32 historical
//! pytest benchmark identities. No Python/PyO3 or GPMC/Ganak subprocess calls.
use std::sync::OnceLock;
use std::collections::HashMap;
use pathsum::wmc::WmcManager;
use pathsum::{check_equivalence_with_options, PathSum, PhaseCoeff, Rational,
              VerificationMethod, VerificationOptions, VerificationStrategy};
use pathsum::gates::{QuantumGates, Side};
use pathsum::ir::QuantumOp;
use pathsum::rational::{Angle, FreeRational};

static DECIMAL: OnceLock<PhaseCoeff> = OnceLock::new();
static UNIQUE_DECIMALS: OnceLock<Vec<PhaseCoeff>> = OnceLock::new();
static SYMBOLIC: OnceLock<PhaseCoeff> = OnceLock::new();
fn decimal() -> &'static PhaseCoeff {
    DECIMAL.get_or_init(|| {
        Angle::from_qasm_str("1.2345678901234567").unwrap().to_phase_coeff()
    })
}
fn unique_decimals() -> &'static Vec<PhaseCoeff> {
    UNIQUE_DECIMALS.get_or_init(|| {
        (0..32).map(|i| {
            let literal = format!("1.234567890123{:04}", i);
            Angle::from_qasm_str(&literal).unwrap().to_phase_coeff()
        }).collect()
    })
}
fn symbolic() -> &'static PhaseCoeff {
    SYMBOLIC.get_or_init(|| PhaseCoeff::new_symbolic(7, FreeRational::HALF))
}

// Fixed source-phase fixtures are constructed once, outside all CodSpeed
// measured spans. The eight *distinct monomials* ensure repeated and unique
// source coefficients exercise exactly the same Boolean CNF topology.
static WMC_REPEAT: OnceLock<PathSum> = OnceLock::new();
static WMC_UNIQUE: OnceLock<PathSum> = OnceLock::new();
static WMC_PREENCODED: OnceLock<WmcManager> = OnceLock::new();

fn wmc_fixture(repeated: bool) -> &'static PathSum {
    let slot = if repeated { &WMC_REPEAT } else { &WMC_UNIQUE };
    slot.get_or_init(|| {
        let mut ps = PathSum::new(8);
        ps.set_auto_reduce(false);
        for index in 0..8 {
            let coeff = if repeated {
                decimal().clone()
            } else {
                unique_decimals()[index].clone()
            };
            ps.p.add_term(vec![index as u32], coeff);
        }
        assert_eq!(ps.p.terms.len(), 8);
        ps
    })
}

fn preencoded_mpfr96() -> &'static WmcManager {
    WMC_PREENCODED.get_or_init(|| {
        let mut cnf = WmcManager::new(wmc_fixture(false));
        cnf.enable_precise_gpmc_weights(96);
        cnf.encode_trace(wmc_fixture(false)).expect("pre-encode valid source");
        cnf
    })
}

fn main() {
    // Make decimal source parsing and fixture construction explicitly untimed.
    let _ = (decimal(), symbolic(), unique_decimals(),
             wmc_fixture(true), wmc_fixture(false), preencoded_mpfr96());
    divan::main();
}

#[divan::bench]
fn phase_clifford_add() {
    let mut phase = divan::black_box(PhaseCoeff::HALF);
    phase.add_logic(divan::black_box(&PhaseCoeff::QUARTER));
    divan::black_box(phase);
}

#[divan::bench]
fn phase_clifford_sub() {
    let mut phase = divan::black_box(PhaseCoeff::THREE_QUARTERS);
    phase.sub_logic(divan::black_box(&PhaseCoeff::QUARTER));
    divan::black_box(phase);
}

#[divan::bench]
fn phase_symbolic_add() {
    let mut phase = divan::black_box(symbolic().clone());
    phase.add_logic(divan::black_box(symbolic()));
    divan::black_box(phase);
}

#[divan::bench]
fn phase_decimal_add() {
    let mut phase = divan::black_box(decimal().clone());
    phase.add_logic(divan::black_box(decimal()));
    divan::black_box(phase);
}

#[divan::bench]
fn phase_decimal_sub() {
    let mut phase = divan::black_box(decimal().clone());
    phase.sub_logic(divan::black_box(decimal()));
    divan::black_box(phase);
}

#[divan::bench]
fn phase_decimal_scale() {
    let mut phase = divan::black_box(decimal().clone());
    phase.mul_scalar_logic(divan::black_box(3));
    divan::black_box(phase);
}

// Creation of PathSum and gate application are intentionally inside the
// measured operation: this is a whole native RR construction+reduction
// workload, NOT an isolated cost attribution to an individual rule.
#[divan::bench]
fn rr_hh_pipeline() {
    let mut ps = PathSum::new(1);
    ps.set_auto_reduce(false);
    ps.apply_h(0, Side::Ket);
    ps.apply_h(0, Side::Ket);
    ps.set_auto_reduce(true);
    ps.full_reduce();
    divan::black_box(ps);
}

#[divan::bench]
fn rr_nonclifford_pipeline() {
    let mut ps = PathSum::new(1);
    ps.set_auto_reduce(false);
    ps.apply_h(0, Side::Ket);
    ps.apply_t(0, Side::Ket);
    ps.apply_h(0, Side::Ket);
    ps.set_auto_reduce(true);
    ps.full_reduce();
    divan::black_box(ps);
}

// Exercise the exact same native verifier API as QuPRS; no Python wrapper.
#[divan::bench(args = [0.0_f64, 1e-10_f64, 1e-8_f64])]
fn native_rr_tolerance(tolerance: f64) {
    let ops = [QuantumOp::H(0), QuantumOp::H(0)];
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        strategy: VerificationStrategy::Naive,
        rr_tolerance: divan::black_box(tolerance),
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(1, divan::black_box(&ops),
                                               divan::black_box(&[]), &options).unwrap();
    divan::black_box(result.status);
}


// Independent PhaseCoeff hash-lookup patterns: setup and exact decimal
// parsing are OUTSIDE the timed function. These are NOT WMC encoder timings.
#[divan::bench]
fn phase_decimal_hash_repeated() {
    let mut map = HashMap::with_capacity(32);
    for i in 0..32 {
        map.insert(divan::black_box(decimal().clone()), i);
    }
    divan::black_box(map);
}

#[divan::bench]
fn phase_decimal_hash_unique() {
    let mut map = HashMap::with_capacity(32);
    for (i, phase) in unique_decimals().iter().enumerate() {
        map.insert(divan::black_box(phase.clone()), i);
    }
    divan::black_box(map);
}

#[divan::bench]
fn phase_decimal_hash_mixed() {
    let mut map = HashMap::with_capacity(32);
    for i in 0..32 {
        let phase = &unique_decimals()[i % 8];
        map.insert(divan::black_box(phase.clone()), i);
    }
    divan::black_box(map);
}


// Native WMC/CNF source processing only. Every function does exactly one
// encode_trace; no external GPMC process, subprocess, Python or PyO3 code.
// 96-bit is a relevant fine-distance precision example, whereas 192-bit
// measures a deliberately tighter precision request; neither is forced as a
// blanket default. These do NOT claim MPFR-to-Solver error certification.
#[divan::bench]
fn wmc_trace_cnf_unweighted() {
    let ps = wmc_fixture(false);
    let mut no_phase = PathSum::new(ps.v.num_qubits);
    no_phase.set_auto_reduce(false);
    let mut cnf = WmcManager::new(&no_phase);
    cnf.encode_trace(&no_phase).expect("unweighted encoding");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_f64_repeated() {
    let ps = wmc_fixture(true);
    let mut cnf = WmcManager::new(ps);
    cnf.encode_trace(ps).expect("f64 repeated source weights");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_f64_unique() {
    let ps = wmc_fixture(false);
    let mut cnf = WmcManager::new(ps);
    cnf.encode_trace(ps).expect("f64 unique source weights");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_mpfr96_repeated() {
    let ps = wmc_fixture(true);
    let mut cnf = WmcManager::new(ps);
    cnf.enable_precise_gpmc_weights(96);
    cnf.encode_trace(ps).expect("MPFR96 repeated source weights");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_mpfr96_unique() {
    let ps = wmc_fixture(false);
    let mut cnf = WmcManager::new(ps);
    cnf.enable_precise_gpmc_weights(96);
    cnf.encode_trace(ps).expect("MPFR96 unique source weights");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_mpfr192_repeated() {
    let ps = wmc_fixture(true);
    let mut cnf = WmcManager::new(ps);
    cnf.enable_precise_gpmc_weights(192);
    cnf.encode_trace(ps).expect("MPFR192 repeated source weights");
    divan::black_box(cnf);
}

#[divan::bench]
fn wmc_trace_mpfr192_unique() {
    let ps = wmc_fixture(false);
    let mut cnf = WmcManager::new(ps);
    cnf.enable_precise_gpmc_weights(192);
    cnf.encode_trace(ps).expect("MPFR192 unique source weights");
    divan::black_box(cnf);
}

// Isolated DIMACS serialization: the manager was fully encoded during
// once-only setup (not inside the measured callable).
#[divan::bench]
fn wmc_dimacs_mpfr96_unique() {
    let dimacs = preencoded_mpfr96()
        .try_to_dimacs_string("gpmc")
        .expect("source-aligned precise GPMC encoding");
    divan::black_box(dimacs);
}
