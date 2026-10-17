//! Regression tests for logical-gate periodic reduction scheduling.
use super::*;
use crate::rational::Angle;
use crate::{check_equivalence, EquivalenceStatus, VerificationMethod};
use std::cell::RefCell;

#[derive(Clone, Debug, PartialEq, Eq)]
struct Reduction {
    after_gates: usize,
    inside_gate: bool,
}

#[derive(Default, Debug)]
struct Trace {
    gates: Vec<(QuantumOp, bool)>,
    completed: usize,
    depth: usize,
    attempts: Vec<(Reduction, bool)>,
    starts: Vec<Reduction>,
}

thread_local! {
    static TRACE: RefCell<Option<Trace>> = const { RefCell::new(None) };
}

// All hooks are private to this crate and compiled out completely outside cfg(test).
pub(crate) struct GateScope(bool);

pub(crate) fn gate_enter(gate: &QuantumOp, is_bra: bool) -> GateScope {
    GateScope(TRACE.with(|cell| {
        let mut state = cell.borrow_mut();
        if let Some(trace) = state.as_mut() {
            trace.gates.push((gate.clone(), is_bra));
            trace.depth += 1;
            true
        } else {
            false
        }
    }))
}

impl Drop for GateScope {
    fn drop(&mut self) {
        if self.0 {
            TRACE.with(|cell| {
                if let Some(trace) = cell.borrow_mut().as_mut() {
                    trace.depth -= 1;
                    trace.completed += 1;
                }
            });
        }
    }
}

fn position(trace: &Trace) -> Reduction {
    Reduction {
        after_gates: trace.completed,
        inside_gate: trace.depth != 0,
    }
}

pub(crate) fn reduction_attempt(enabled: bool) {
    TRACE.with(|cell| {
        if let Some(trace) = cell.borrow_mut().as_mut() {
            trace.attempts.push((position(trace), enabled));
        }
    });
}

pub(crate) fn reduction_start() {
    TRACE.with(|cell| {
        if let Some(trace) = cell.borrow_mut().as_mut() {
            trace.starts.push(position(trace));
        }
    });
}

fn observe<T>(f: impl FnOnce() -> T) -> (T, Trace) {
    struct Reset;
    impl Drop for Reset {
        fn drop(&mut self) {
            TRACE.with(|cell| *cell.borrow_mut() = None);
        }
    }
    TRACE.with(|cell| {
        assert!(
            cell.borrow().is_none(),
            "nested observation is not supported"
        );
        *cell.borrow_mut() = Some(Trace::default());
    });
    let _reset = Reset;
    let result = f();
    let trace = TRACE.with(|cell| cell.borrow_mut().take().unwrap());
    (result, trace)
}

fn strategies() -> [VerificationStrategy; 4] {
    [
        VerificationStrategy::Naive,
        VerificationStrategy::Straightforward,
        VerificationStrategy::Proportional,
        VerificationStrategy::Difference,
    ]
}

// No redundant final call at an exact checkpoint. Empty input still gets one
// final pass: the supplied PathSum might already contain unreduced state.
fn expected_reductions(total: usize, interval: usize, enabled: bool) -> Vec<Reduction> {
    assert!(interval > 0);
    if !enabled {
        return vec![];
    }
    let mut points: Vec<_> = (interval..=total).step_by(interval).collect();
    if total == 0 || total % interval != 0 {
        points.push(total);
    }
    points
        .into_iter()
        .map(|after_gates| Reduction {
            after_gates,
            inside_gate: false,
        })
        .collect()
}

struct Fixture {
    name: &'static str,
    ket: Vec<QuantumOp>,
    bra: Vec<QuantumOp>,
    // Literal hand-derived side schedules; consume each circuit in existing order.
    proportional: String,
    difference: String,
}

fn fixtures() -> Vec<Fixture> {
    let mut out = Vec::new();
    for (name, k, b, prop, diff) in [
        ("empty", 0, 0, "".into(), "".into()),
        ("ket_only", 11, 0, "K".repeat(11), "K".repeat(11)),
        ("bra_only", 0, 11, "B".repeat(11), "B".repeat(11)),
        (
            "equal_exact_boundary",
            10,
            10,
            "KB".repeat(10),
            "KB".repeat(10),
        ),
        (
            "ket_batches_and_tail",
            26,
            6,
            "KKKKB".repeat(6) + "KK",
            "KB".repeat(6) + &"K".repeat(20),
        ),
        (
            "bra_batches_and_tail",
            6,
            26,
            "BBBBK".repeat(6) + "BB",
            "KB".repeat(6) + &"B".repeat(20),
        ),
        (
            "ratio_one_ket_tail",
            12,
            10,
            "KB".repeat(10) + "KK",
            "KB".repeat(10) + "KK",
        ),
        (
            "ratio_one_bra_tail",
            10,
            12,
            "KB".repeat(10) + "BB",
            "KB".repeat(10) + "BB",
        ),
    ] {
        out.push(Fixture {
            name,
            ket: vec![QuantumOp::X(0); k],
            bra: vec![QuantumOp::X(0); b],
            proportional: prop,
            difference: diff,
        });
    }
    for (name, gate) in [
        ("H_gate_must_not_reduce", QuantumOp::H(0)),
        (
            "U_gate_must_not_reduce",
            QuantumOp::U(0, Angle::ZERO, Angle::ZERO, Angle::ZERO),
        ),
        ("composite_SWAP_counts_once", QuantumOp::SWAP(0, 1)),
    ] {
        out.push(Fixture {
            name,
            ket: vec![gate.clone(); 6],
            bra: vec![gate; 6],
            proportional: "KB".repeat(6),
            difference: "KB".repeat(6),
        });
    }
    // Force each Myers opcode with an unambiguous common prefix and distinct suffix.
    let prefix = vec![QuantumOp::X(0); 4];
    let mut extended = prefix.clone();
    extended.extend(vec![QuantumOp::Z(0); 7]);
    out.push(Fixture {
        name: "diff_insert",
        ket: prefix.clone(),
        bra: extended.clone(),
        proportional: "BBK".repeat(4) + "BBB",
        difference: "KB".repeat(4) + "BBBBBBB",
    });
    out.push(Fixture {
        name: "diff_delete",
        ket: extended,
        bra: prefix,
        proportional: "KKB".repeat(4) + "KKK",
        difference: "KB".repeat(4) + "KKKKKKK",
    });
    out.push(Fixture {
        name: "diff_replace",
        ket: vec![QuantumOp::X(0); 6],
        bra: vec![QuantumOp::Z(0); 7],
        proportional: "KB".repeat(6) + "B",
        difference: "KKKKKKBBBBBBB".into(),
    });
    out
}

fn expected_gates(f: &Fixture, strategy: VerificationStrategy) -> Vec<(QuantumOp, bool)> {
    let sides = match strategy {
        VerificationStrategy::Straightforward => "B".repeat(f.bra.len()) + &"K".repeat(f.ket.len()),
        VerificationStrategy::Naive => {
            let common = f.ket.len().min(f.bra.len());
            "KB".repeat(common)
                + &"K".repeat(f.ket.len() - common)
                + &"B".repeat(f.bra.len() - common)
        }
        VerificationStrategy::Proportional => f.proportional.clone(),
        VerificationStrategy::Difference => f.difference.clone(),
    };
    let mut ket = f.ket.iter();
    let mut bra = f.bra.iter();
    let expected = sides
        .chars()
        .map(|side| match side {
            'K' => (
                ket.next().expect("invalid fixture Ket schedule").clone(),
                false,
            ),
            'B' => (
                bra.next().expect("invalid fixture Bra schedule").clone(),
                true,
            ),
            _ => unreachable!(),
        })
        .collect();
    assert!(ket.next().is_none() && bra.next().is_none());
    expected
}

fn contract(strategy: VerificationStrategy, interval: usize) {
    let mut failures = Vec::new();
    for fixture in fixtures() {
        for enabled in [true, false] {
            let mut input = PathSum::new(2);
            input.set_auto_reduce(enabled);
            let (output, trace) = observe(|| {
                strategy.run_with_interval(
                    input,
                    &fixture.ket,
                    &fixture.bra,
                    NonZeroUsize::new(interval).unwrap(),
                )
            });
            let expected_gates = expected_gates(&fixture, strategy);
            assert_eq!(
                trace.gates, expected_gates,
                "gate stream: {strategy:?}/{}",
                fixture.name
            );
            assert_eq!(trace.completed, fixture.ket.len() + fixture.bra.len());
            assert_eq!(trace.depth, 0);
            assert_eq!(
                output.is_auto_reduce(),
                enabled,
                "original flag must be restored"
            );
            let expected = expected_reductions(trace.completed, interval, enabled);
            let attempts: Vec<_> = trace
                .attempts
                .iter()
                .map(|(point, _)| point.clone())
                .collect();
            if trace.starts != expected || attempts != expected {
                failures.push(format!(
                    "{} auto={enabled} interval={interval}: expected={expected:?}; effective={:?}; attempts={:?}",
                    fixture.name, trace.starts, trace.attempts));
            }
        }
    }
    assert!(
        failures.is_empty(),
        "{strategy:?}: {} schedule violations:\n{}",
        failures.len(),
        failures.join("\n")
    );
}

macro_rules! interval_contracts {
    ($strategy:ident; $($name:ident => $interval:expr),+) => {$ (
        #[test]
        fn $name() { contract(VerificationStrategy::$strategy, $interval); }
    )+};
}
interval_contracts!(Naive; naive_i1=>1, naive_i3=>3, naive_i10=>10, naive_i11=>11, naive_i100=>100);
interval_contracts!(Straightforward; straightforward_i1=>1, straightforward_i3=>3, straightforward_i10=>10, straightforward_i11=>11, straightforward_i100=>100);
interval_contracts!(Proportional; proportional_i1=>1, proportional_i3=>3, proportional_i10=>10, proportional_i11=>11, proportional_i100=>100);
interval_contracts!(Difference; difference_i1=>1, difference_i3=>3, difference_i10=>10, difference_i11=>11, difference_i100=>100);

#[test]
fn observers_distinguish_skipped_attempt_from_actual_reduction() {
    let mut ps = PathSum::new(1);
    ps.set_auto_reduce(false);
    QuantumOp::H(0).apply(&mut ps, false);
    QuantumOp::H(0).apply(&mut ps, false);
    let vars_before = ps.v.path_vars.len();
    let (_, disabled) = observe(|| ps.full_reduce());
    assert!(disabled.starts.is_empty());
    assert_eq!(disabled.attempts.len(), 1);
    assert!(!disabled.attempts[0].1);
    assert_eq!(ps.v.path_vars.len(), vars_before);
    ps.set_auto_reduce(true);
    let (_, enabled) = observe(|| ps.full_reduce());
    assert_eq!(enabled.starts.len(), 1);
    assert!(
        ps.v.path_vars.len() < vars_before,
        "a real HH reduction must occur"
    );
}

#[test]
fn difference_fixtures_really_cover_all_four_opcodes() {
    let mut seen = [false; 4];
    for f in fixtures() {
        for op in similar::capture_diff_slices(Algorithm::Myers, &f.ket, &f.bra) {
            seen[match op {
                DiffOp::Equal { .. } => 0,
                DiffOp::Insert { .. } => 1,
                DiffOp::Delete { .. } => 2,
                DiffOp::Replace { .. } => 3,
            }] = true;
        }
    }
    assert_eq!(seen, [true; 4]);
}

fn method_contract(method: VerificationMethod) {
    let mut failures = Vec::new();
    for strategy in strategies() {
        // X contributes no path variables: WmcOnly bypasses external solver.
        // An invalid tool name would error if this fixture accidentally invoked it.
        let gates = vec![QuantumOp::X(0); 12];
        let (result, trace) = observe(|| {
            check_equivalence(
                1,
                &gates,
                &gates,
                method,
                strategy,
                "periodic-red-no-external-solver",
                0,
            )
        });
        let result = result.expect("fixture must never invoke an external solver");
        assert_eq!(result.status, EquivalenceStatus::Equivalent);
        assert_eq!(trace.gates.len(), 24);
        let enabled = method != VerificationMethod::WmcOnly;
        assert_eq!(result.final_ps.is_auto_reduce(), enabled);
        let expected = expected_reductions(24, 10, enabled);
        if trace.starts != expected {
            failures.push(format!(
                "{strategy:?}: expected {expected:?}, actual {:?}",
                trace.starts
            ));
        }
        if !enabled {
            assert!(trace.attempts.is_empty());
        }
    }
    assert!(failures.is_empty(), "{method:?}:\n{}", failures.join("\n"));
}

#[test]
fn reduction_rules_entrypoint_default10() {
    method_contract(VerificationMethod::ReductionRules);
}
#[test]
fn hybrid_entrypoint_default10() {
    method_contract(VerificationMethod::Hybrid);
}
#[test]
fn wmc_only_never_reduces() {
    method_contract(VerificationMethod::WmcOnly);
}

#[test]
fn empty_input_still_reduces_preexisting_state_and_restores_flag() {
    for strategy in strategies() {
        for enabled in [true, false] {
            let mut ps = PathSum::new(1);
            ps.set_auto_reduce(false);
            QuantumOp::H(0).apply(&mut ps, false);
            QuantumOp::H(0).apply(&mut ps, false);
            let unreduced_vars = ps.v.path_vars.len();
            ps.set_auto_reduce(enabled);
            let (result, trace) = observe(|| strategy.run(ps, &[], &[]));
            assert!(trace.gates.is_empty());
            assert_eq!(result.is_auto_reduce(), enabled);
            assert_eq!(trace.starts, expected_reductions(0, 10, enabled));
            if enabled {
                assert!(result.v.path_vars.len() < unreduced_vars);
                assert!(result.is_identity());
            } else {
                assert_eq!(result.v.path_vars.len(), unreduced_vars);
            }
        }
    }
}

#[test]
fn existing_identity_global_phase_and_non_equivalence_are_not_redefined() {
    for strategy in strategies() {
        for (tail, expected) in [
            (vec![], EquivalenceStatus::Equivalent),
            (
                vec![
                    QuantumOp::X(0),
                    QuantumOp::Z(0),
                    QuantumOp::X(0),
                    QuantumOp::Z(0),
                ],
                EquivalenceStatus::EquivalentUpToGlobalPhase,
            ),
            (vec![QuantumOp::X(0)], EquivalenceStatus::NotEquivalent),
        ] {
            let mut gates = vec![QuantumOp::H(0), QuantumOp::H(0)];
            gates.extend(tail);
            let result = check_equivalence(
                1,
                &gates,
                &[],
                VerificationMethod::ReductionRules,
                strategy,
                "periodic-red-no-external-solver",
                0,
            )
            .unwrap();
            assert_eq!(result.status, expected, "{strategy:?}");
            if expected == EquivalenceStatus::EquivalentUpToGlobalPhase {
                assert_eq!(
                    result.final_ps.get_global_phase().unwrap().constant,
                    crate::rational::Rational::HALF
                );
            }
        }
    }
}

fn pathsum_matrix(ps: &PathSum) -> Vec<num_complex::Complex64> {
    use num_complex::Complex64;
    let mut internal: Vec<_> =
        ps.v.path_vars
            .iter()
            .copied()
            .filter(|&v| v as usize >= ps.v.num_qubits)
            .collect();
    internal.sort_unstable();
    assert!(internal.len() <= 12, "matrix fixture must stay small");
    let dim = 1 << ps.v.num_qubits;
    let mut matrix = vec![Complex64::default(); dim * dim];
    for input in 0..dim {
        for path in 0..(1 << internal.len()) {
            let mut assignment = input as u64;
            for (bit, var) in internal.iter().enumerate() {
                assignment |= (((path >> bit) & 1) as u64) << var;
            }
            let monomial = |vars: &[u32]| vars.iter().all(|v| assignment & (1u64 << v) != 0);
            let output =
                ps.f.functions
                    .iter()
                    .enumerate()
                    .fold(0, |out, (bit, poly)| {
                        out | ((poly.iter().filter(|vars| monomial(vars)).count() % 2) << bit)
                    });
            let phase: f64 =
                ps.p.terms
                    .iter()
                    .filter(|(vars, _)| monomial(vars))
                    .map(|(_, coeff)| {
                        assert!(coeff.symbols.is_empty());
                        coeff.constant.numer as f64 / coeff.constant.denom as f64
                    })
                    .sum();
            matrix[output * dim + input] += Complex64::from_polar(
                2f64.powf(-(internal.len() as f64) / 2.0),
                std::f64::consts::TAU * phase,
            );
        }
    }
    matrix
}

// Independent dense unitary oracle, including exact global phase.
fn dense_circuit(gates: &[QuantumOp], qubits: usize) -> Vec<num_complex::Complex64> {
    use num_complex::Complex64 as C;
    let dim = 1 << qubits;
    let mut matrix = vec![C::default(); dim * dim];
    for i in 0..dim {
        matrix[i * dim + i] = C::new(1.0, 0.0);
    }
    for gate in gates {
        let mut next = vec![C::default(); dim * dim];
        for row in 0..dim {
            let mut entries = Vec::new();
            match gate {
                QuantumOp::H(q) => {
                    let scale = std::f64::consts::FRAC_1_SQRT_2;
                    entries.push((row & !(1 << q), C::new(scale, 0.0)));
                    entries.push((
                        row | (1 << q),
                        C::new(if row & (1 << q) == 0 { scale } else { -scale }, 0.0),
                    ));
                }
                QuantumOp::X(q) => entries.push((row ^ (1 << q), C::new(1.0, 0.0))),
                QuantumOp::Z(q) => entries.push((
                    row,
                    C::new(if row & (1 << q) == 0 { 1.0 } else { -1.0 }, 0.0),
                )),
                QuantumOp::S(q) | QuantumOp::T(q) => {
                    let phase = if row & (1 << q) == 0 {
                        0.0
                    } else if matches!(gate, QuantumOp::S(_)) {
                        std::f64::consts::FRAC_PI_2
                    } else {
                        std::f64::consts::FRAC_PI_4
                    };
                    entries.push((row, C::from_polar(1.0, phase)));
                }
                QuantumOp::CX(c, t) => entries.push((
                    if row & (1 << c) != 0 {
                        row ^ (1 << t)
                    } else {
                        row
                    },
                    C::new(1.0, 0.0),
                )),
                QuantumOp::CZ(c, t) => entries.push((
                    row,
                    C::new(
                        if row & (1 << c) != 0 && row & (1 << t) != 0 {
                            -1.0
                        } else {
                            1.0
                        },
                        0.0,
                    ),
                )),
                QuantumOp::SWAP(a, b) => entries.push((
                    if ((row >> a) ^ (row >> b)) & 1 != 0 {
                        row ^ (1 << a) ^ (1 << b)
                    } else {
                        row
                    },
                    C::new(1.0, 0.0),
                )),
                QuantumOp::U(q, theta, phi, lam) => {
                    let radians = |a: &Angle| {
                        assert!(a.symbols.is_empty());
                        std::f64::consts::PI * a.constant.numer as f64 / a.constant.denom as f64
                    };
                    let (s, c) = (radians(theta) / 2.0).sin_cos();
                    let (p, l) = (radians(phi), radians(lam));
                    if row & (1 << q) == 0 {
                        entries.push((row, C::new(c, 0.0)));
                        entries.push((row | (1 << q), C::from_polar(s, p)));
                    } else {
                        entries.push((row & !(1 << q), -C::from_polar(s, l)));
                        entries.push((row, C::from_polar(c, p + l)));
                    }
                }
                _ => panic!("unsupported dense fixture gate"),
            }
            for (out, weight) in entries {
                for col in 0..dim {
                    next[out * dim + col] += weight * matrix[row * dim + col];
                }
            }
        }
        matrix = next;
    }
    matrix
}

#[test]
fn intervals_preserve_small_complex_matrices_and_global_phase() {
    use QuantumOp::*;
    let circuits = [
        (1, vec![], vec![]),
        (1, vec![H(0), T(0), H(0), S(0)], vec![H(0), T(0)]),
        (2, vec![CX(0, 1)], vec![H(1), CZ(0, 1), H(1)]),
        (2, vec![SWAP(0, 1)], vec![CX(0, 1), CX(1, 0), CX(0, 1)]),
        (1, vec![X(0), Z(0), X(0), Z(0)], vec![]),
        (
            2,
            vec![H(0), T(0), H(1), CX(0, 1), H(0), S(1)],
            vec![H(1), T(1), CX(1, 0)],
        ),
        (
            1,
            vec![U(0, Angle::HALF, Angle::QUARTER, Angle::HALF), H(0)],
            vec![T(0)],
        ),
    ];
    for (qubits, ket, bra) in circuits {
        let dim = 1 << qubits;
        let a = dense_circuit(&ket, qubits);
        let b = dense_circuit(&bra, qubits);
        let mut expected = vec![num_complex::Complex64::default(); dim * dim];
        for row in 0..dim {
            for col in 0..dim {
                for k in 0..dim {
                    expected[row * dim + col] += a[row * dim + k] * b[col * dim + k].conj();
                }
            }
        }
        for strategy in strategies() {
            let mut raw = PathSum::new(qubits);
            raw.set_auto_reduce(false);
            let raw = pathsum_matrix(&strategy.run(raw, &ket, &bra));
            for (actual, expected) in raw.iter().zip(&expected) {
                assert!((actual - expected).norm() < 1e-10);
            }
            for interval in [1, 3, 10, 11, 100] {
                let ps = strategy.run_with_interval(
                    PathSum::new(qubits),
                    &ket,
                    &bra,
                    NonZeroUsize::new(interval).unwrap(),
                );
                let actual = pathsum_matrix(&ps);
                for (actual, expected) in actual.iter().zip(&expected) {
                    assert!((actual-expected).norm()<1e-10,"{strategy:?}, interval={interval}, ket={ket:?}, bra={bra:?}: {actual} != {expected}");
                }
            }
        }
    }
}

#[test]
fn checkpoints_preserve_accumulated_rule_statistics() {
    for strategy in strategies() {
        for interval in [1, 3, 10, 11, 100] {
            for enabled in [true, false] {
                let mut ps = PathSum::new(1);
                ps.stats.hh.attempts = 7;
                ps.stats.hh.successes = 3;
                ps.set_auto_reduce(enabled);
                let out = strategy.run_with_interval(
                    ps,
                    &vec![QuantumOp::H(0); 12],
                    &vec![QuantumOp::H(0); 2],
                    NonZeroUsize::new(interval).unwrap(),
                );
                assert_eq!(out.is_auto_reduce(), enabled);
                if enabled {
                    assert!(out.stats.hh.attempts > 7);
                    assert!(out.stats.hh.successes > 3);
                    assert!(out.is_identity());
                } else {
                    assert_eq!(out.stats.hh.attempts, 7);
                    assert_eq!(out.stats.hh.successes, 3);
                }
            }
        }
    }
}
