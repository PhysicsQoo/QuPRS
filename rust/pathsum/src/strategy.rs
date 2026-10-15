// src/strategy.rs
use crate::ir::QuantumOp;
use crate::pathsum::PathSum;
use similar::{Algorithm, DiffOp};
use std::cmp;

const REDUCE_INTERVAL: usize = 10;

/// Verification strategy enum
/// Determines how to interleave operations from two circuits to maximize cancellation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerificationStrategy {
    /// One-to-one interleaving: (Ket, Bra, Ket, Bra...)
    Naive,
    /// Execute all Bra (reverse) then all Ket (forward)
    Straightforward,
    /// Mix uniformly based on circuit length ratio
    Proportional,
    /// Use LCS algorithm to find differences (requires similar crate)
    Difference,
}

impl VerificationStrategy {
    /// Execute the selected strategy
    ///
    /// # Arguments
    /// * `ps` - Initial PathSum state
    /// * `gates1` - Circuit 1 operations (reference/Ket)
    /// * `gates2` - Circuit 2 operations (verification/Bra, treated as Inverse)
    pub fn run(
        &self,
        ps: PathSum,
        gates1: &[QuantumOp],
        gates2: &[QuantumOp],
        deadline: Option<std::time::Instant>,
    ) -> PathSum {
        if gates2.is_empty() {
            return run_straightforward(ps, gates1, gates2, deadline, REDUCE_INTERVAL);
        }
        match self {
            Self::Naive => run_naive(ps, gates1, gates2, deadline, REDUCE_INTERVAL),
            Self::Straightforward => {
                run_straightforward(ps, gates1, gates2, deadline, REDUCE_INTERVAL)
            }
            Self::Proportional => run_proportional(ps, gates1, gates2, deadline, REDUCE_INTERVAL),
            Self::Difference => run_difference(ps, gates1, gates2, deadline, REDUCE_INTERVAL),
        }
    }
}

// Keep gate-level reduction disabled and enable it only at timed checkpoints.
struct ReductionCheckpoint {
    pending: usize,
    enabled: bool,
    deadline: Option<std::time::Instant>,
    interval: usize,
}

impl ReductionCheckpoint {
    fn apply(&mut self, ps: &mut PathSum, gate: &QuantumOp, is_bra: bool) -> bool {
        if self.expired() {
            return false;
        }
        gate.apply(ps, is_bra);
        self.pending += 1;
        if self.pending >= self.interval {
            self.pending = 0;
            if self.enabled {
                ps.set_auto_reduce(true);
                ps.full_reduce(self.deadline);
                ps.set_auto_reduce(false);
            }
        }
        !self.expired()
    }

    fn expired(&self) -> bool {
        self.deadline.is_some_and(|d| std::time::Instant::now() > d)
    }

    fn finish(&self, mut ps: PathSum) -> PathSum {
        ps.set_auto_reduce(self.enabled);
        if self.enabled {
            ps.full_reduce(self.deadline);
        }
        ps
    }
}

// Apply all gates2 as Bra, then all gates1 as Ket
fn run_straightforward(
    mut ps: PathSum,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    deadline: Option<std::time::Instant>,
    interval: usize,
) -> PathSum {
    if let Some(d) = deadline {
        if std::time::Instant::now() > d {
            return ps;
        }
    }
    let original_auto_reduce = ps.is_auto_reduce();
    ps.set_auto_reduce(false); // Disable auto-reduce to avoid untimed calls in gates.rs

    let mut checkpoint = ReductionCheckpoint {
        pending: 0,
        enabled: original_auto_reduce,
        deadline,
        interval,
    };

    for gate in gates2 {
        if !checkpoint.apply(&mut ps, gate, true) {
            return checkpoint.finish(ps);
        }
    }
    for gate in gates1 {
        if !checkpoint.apply(&mut ps, gate, false) {
            return checkpoint.finish(ps);
        }
    }

    checkpoint.finish(ps)
}

// Interleave gates until the shorter sequence ends, then apply remaining
fn run_naive(
    mut ps: PathSum,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    deadline: Option<std::time::Instant>,
    interval: usize,
) -> PathSum {
    if let Some(d) = deadline {
        if std::time::Instant::now() > d {
            return ps;
        }
    }
    let original_auto_reduce = ps.is_auto_reduce();
    ps.set_auto_reduce(false);

    let min_len = cmp::min(gates1.len(), gates2.len());
    let mut checkpoint = ReductionCheckpoint {
        pending: 0,
        enabled: original_auto_reduce,
        deadline,
        interval,
    };

    for i in 0..min_len {
        if !checkpoint.apply(&mut ps, &gates1[i], false) {
            return checkpoint.finish(ps);
        }
        if !checkpoint.apply(&mut ps, &gates2[i], true) {
            return checkpoint.finish(ps);
        }
    }

    if gates1.len() > gates2.len() {
        for i in min_len..gates1.len() {
            if !checkpoint.apply(&mut ps, &gates1[i], false) {
                return checkpoint.finish(ps);
            }
        }
    } else if gates2.len() > gates1.len() {
        for i in min_len..gates2.len() {
            if !checkpoint.apply(&mut ps, &gates2[i], true) {
                return checkpoint.finish(ps);
            }
        }
    }

    checkpoint.finish(ps)
}

// Mix operations based on length ratio between circuits
fn run_proportional(
    mut ps: PathSum,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    deadline: Option<std::time::Instant>,
    interval: usize,
) -> PathSum {
    if let Some(d) = deadline {
        if std::time::Instant::now() > d {
            return ps;
        }
    }
    let l1 = gates1.len();
    let l2 = gates2.len();

    if l1 == 0 && l2 == 0 {
        return ps;
    }
    if l1 == 0 || l2 == 0 {
        return run_straightforward(ps, gates1, gates2, deadline, interval);
    }

    let original_auto_reduce = ps.is_auto_reduce();
    ps.set_auto_reduce(false);

    let mut checkpoint = ReductionCheckpoint {
        pending: 0,
        enabled: original_auto_reduce,
        deadline,
        interval,
    };

    let min_len = cmp::min(l1, l2);
    let diff = (l1 as isize) - (l2 as isize);
    let r = if diff > 0 { l1 / l2 } else { l2 / l1 };

    if r == 1 {
        for i in 0..min_len {
            if !checkpoint.apply(&mut ps, &gates1[i], false) {
                return checkpoint.finish(ps);
            }
            if !checkpoint.apply(&mut ps, &gates2[i], true) {
                return checkpoint.finish(ps);
            }
        }

        if diff > 0 {
            for i in 0..(diff as usize) {
                if !checkpoint.apply(&mut ps, &gates1[min_len + i], false) {
                    return checkpoint.finish(ps);
                }
            }
        } else if diff < 0 {
            for i in 0..(diff.abs() as usize) {
                if !checkpoint.apply(&mut ps, &gates2[min_len + i], true) {
                    return checkpoint.finish(ps);
                }
            }
        }
    } else if diff > 0 {
        // gates1 is longer: apply r Kets per Bra
        for i in 0..l2 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l1 {
                    if !checkpoint.apply(&mut ps, &gates1[idx], false) {
                        return checkpoint.finish(ps);
                    }
                }
            }
            if !checkpoint.apply(&mut ps, &gates2[i], true) {
                return checkpoint.finish(ps);
            }
        }

        let d2 = l1 - r * l2;
        if d2 > 0 {
            let start_idx = l2 * r;
            for i in 0..d2 {
                if start_idx + i < l1 {
                    if !checkpoint.apply(&mut ps, &gates1[start_idx + i], false) {
                        return checkpoint.finish(ps);
                    }
                }
            }
        }
    } else {
        // gates2 is longer: apply r Bras per Ket
        for i in 0..l1 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l2 {
                    if !checkpoint.apply(&mut ps, &gates2[idx], true) {
                        return checkpoint.finish(ps);
                    }
                }
            }
            if !checkpoint.apply(&mut ps, &gates1[i], false) {
                return checkpoint.finish(ps);
            }
        }

        let d2 = l2 - r * l1;
        if d2 > 0 {
            let start_idx = l1 * r;
            for i in 0..d2 {
                if start_idx + i < l2 {
                    if !checkpoint.apply(&mut ps, &gates2[start_idx + i], true) {
                        return checkpoint.finish(ps);
                    }
                }
            }
        }
    }

    checkpoint.finish(ps)
}

// Use diff algorithm to identify and process only differing parts
fn run_difference(
    mut ps: PathSum,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
    deadline: Option<std::time::Instant>,
    interval: usize,
) -> PathSum {
    if let Some(d) = deadline {
        if std::time::Instant::now() > d {
            return ps;
        }
    }
    let original_auto_reduce = ps.is_auto_reduce();
    ps.set_auto_reduce(false); // Disable gate-level auto-reduce

    let diff_ops = similar::capture_diff_slices(Algorithm::Myers, gates1, gates2);
    let mut checkpoint = ReductionCheckpoint {
        pending: 0,
        enabled: original_auto_reduce,
        deadline,
        interval,
    };

    for op in diff_ops {
        if let Some(d) = deadline {
            if std::time::Instant::now() > d {
                break;
            }
        }
        match op {
            DiffOp::Equal {
                old_index,
                new_index,
                len,
            } => {
                for i in 0..len {
                    if !checkpoint.apply(&mut ps, &gates1[old_index + i], false) {
                        return checkpoint.finish(ps);
                    }
                    if !checkpoint.apply(&mut ps, &gates2[new_index + i], true) {
                        return checkpoint.finish(ps);
                    }
                }
            }
            DiffOp::Delete {
                old_index, old_len, ..
            } => {
                for i in 0..old_len {
                    if !checkpoint.apply(&mut ps, &gates1[old_index + i], false) {
                        return checkpoint.finish(ps);
                    }
                }
            }
            DiffOp::Insert {
                new_index, new_len, ..
            } => {
                for i in 0..new_len {
                    if !checkpoint.apply(&mut ps, &gates2[new_index + i], true) {
                        return checkpoint.finish(ps);
                    }
                }
            }
            DiffOp::Replace {
                old_index,
                old_len,
                new_index,
                new_len,
            } => {
                for i in 0..old_len {
                    if !checkpoint.apply(&mut ps, &gates1[old_index + i], false) {
                        return checkpoint.finish(ps);
                    }
                }
                for i in 0..new_len {
                    if !checkpoint.apply(&mut ps, &gates2[new_index + i], true) {
                        return checkpoint.finish(ps);
                    }
                }
            }
        }
    }

    checkpoint.finish(ps)
}
#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::cell::RefCell;

    thread_local! {
        pub static REDUCTION_STARTS: RefCell<Vec<u32>> = const { RefCell::new(Vec::new()) };
    }

    fn strategies() -> [VerificationStrategy; 4] {
        [
            VerificationStrategy::Naive,
            VerificationStrategy::Straightforward,
            VerificationStrategy::Proportional,
            VerificationStrategy::Difference,
        ]
    }

    fn run_with_interval(
        strategy: VerificationStrategy,
        ps: PathSum,
        a: &[QuantumOp],
        b: &[QuantumOp],
        interval: usize,
    ) -> PathSum {
        match strategy {
            VerificationStrategy::Naive => run_naive(ps, a, b, None, interval),
            VerificationStrategy::Straightforward => run_straightforward(ps, a, b, None, interval),
            VerificationStrategy::Proportional => run_proportional(ps, a, b, None, interval),
            VerificationStrategy::Difference => run_difference(ps, a, b, None, interval),
        }
    }

    #[test]
    fn periodic_reduction_runs_before_the_last_gate() {
        for strategy in strategies() {
            for (a, b) in [
                (26, 6),
                (6, 26),
                (12, 10),
                (10, 12),
                (0, 32),
                (32, 0),
                (16, 16),
            ] {
                for replace in [false, true] {
                    let a = vec![QuantumOp::H(0); a];
                    let b = vec![QuantumOp::H(usize::from(replace)); b];
                    REDUCTION_STARTS.with(|starts| starts.borrow_mut().clear());
                    let ps = strategy.run(PathSum::new(2), &a, &b, None);
                    let total = a.len() + b.len();
                    let mut expected: Vec<u32> =
                        (10..=total).step_by(10).map(|n| n as u32 + 2).collect();
                    expected.push(total as u32 + 2);
                    REDUCTION_STARTS.with(|starts| {
                        assert_eq!(
                            *starts.borrow(),
                            expected,
                            "{strategy:?}, lengths {:?}, replace {replace}",
                            (a.len(), b.len())
                        )
                    });
                    assert!(ps.is_identity());
                    assert!(ps.is_auto_reduce());
                }
            }
        }
    }

    #[test]
    fn intervals_preserve_exact_phase_and_non_equivalence() {
        for strategy in strategies() {
            for interval in [1, 3, 10, 11, 100] {
                for (tail, identity, phase) in [
                    (vec![], true, false),
                    (
                        vec![
                            QuantumOp::X(0),
                            QuantumOp::Z(0),
                            QuantumOp::X(0),
                            QuantumOp::Z(0),
                        ],
                        true,
                        true,
                    ),
                    (vec![QuantumOp::X(0)], false, false),
                ] {
                    let mut a = vec![QuantumOp::H(0); 26];
                    a.extend(tail);
                    let ps = run_with_interval(
                        strategy,
                        PathSum::new(1),
                        &a,
                        &vec![QuantumOp::H(0); 6],
                        interval,
                    );
                    assert_eq!(
                        ps.is_identity_up_to_phase(),
                        identity,
                        "{strategy:?}, interval {interval}"
                    );
                    if identity {
                        assert_eq!(ps.is_identity(), !phase);
                    }
                }
            }
        }
    }

    fn matrix(ps: &PathSum) -> Vec<num_complex::Complex64> {
        let internal: Vec<_> =
            ps.v.path_vars
                .iter()
                .copied()
                .filter(|&var| var as usize >= ps.v.num_qubits)
                .collect();
        let dim = 1 << ps.v.num_qubits;
        let mut result = vec![num_complex::Complex64::default(); dim * dim];
        for input in 0..dim {
            for path in 0..(1 << internal.len()) {
                let mut assignment = input as u64;
                for (bit, var) in internal.iter().enumerate() {
                    assignment |= (((path >> bit) & 1) as u64) << var;
                }
                let monomial = |vars: &[u32]| vars.iter().all(|var| assignment & (1 << var) != 0);
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
                result[output * dim + input] += num_complex::Complex64::from_polar(
                    2.0_f64.powf(-(internal.len() as f64) / 2.0),
                    std::f64::consts::TAU * phase,
                );
            }
        }
        result
    }

    #[test]
    fn intervals_preserve_nontrivial_circuit_matrix() {
        let a = [
            QuantumOp::H(0),
            QuantumOp::T(0),
            QuantumOp::H(1),
            QuantumOp::CX(0, 1),
            QuantumOp::H(0),
            QuantumOp::S(1),
            QuantumOp::H(1),
            QuantumOp::T(1),
            QuantumOp::H(0),
            QuantumOp::CX(1, 0),
            QuantumOp::H(1),
        ];
        let b = [QuantumOp::H(1), QuantumOp::T(1), QuantumOp::CX(1, 0)];
        for strategy in strategies() {
            let mut raw = PathSum::new(2);
            raw.set_auto_reduce(false);
            let expected = matrix(&strategy.run(raw, &a, &b, None));
            for interval in [1, 3, 10, 11, 100] {
                let ps = run_with_interval(strategy, PathSum::new(2), &a, &b, interval);
                let actual = matrix(&ps);
                for (actual, expected) in actual.iter().zip(&expected) {
                    assert!(
                        (actual - expected).norm() < 1e-10,
                        "{strategy:?}, interval {interval}"
                    );
                }
            }
        }
    }

    #[test]
    fn disabled_reduction_never_runs_at_checkpoints_or_finish() {
        for strategy in strategies() {
            let mut ps = PathSum::new(1);
            ps.set_auto_reduce(false);
            REDUCTION_STARTS.with(|starts| starts.borrow_mut().clear());
            let ps = strategy.run(
                ps,
                &vec![QuantumOp::H(0); 26],
                &vec![QuantumOp::H(0); 6],
                None,
            );
            assert_eq!(ps.stats.total_attempts(), 0);
            assert_eq!(ps.v.path_vars.len(), 33);
            assert!(!ps.is_auto_reduce());
            REDUCTION_STARTS.with(|starts| assert!(starts.borrow().is_empty()));
        }
    }

    #[test]
    fn expired_checkpoint_does_not_apply_the_next_gate() {
        let mut checkpoint = ReductionCheckpoint {
            pending: 9,
            enabled: true,
            deadline: Some(std::time::Instant::now() - std::time::Duration::from_secs(1)),
            interval: 10,
        };
        let mut ps = PathSum::new(1);
        ps.set_auto_reduce(false);
        assert!(!checkpoint.apply(&mut ps, &QuantumOp::X(0), false));
        let ps = checkpoint.finish(ps);
        assert!(ps.is_identity());
        assert_eq!(ps.stats.total_attempts(), 0);
        assert!(ps.is_auto_reduce());
    }
}
