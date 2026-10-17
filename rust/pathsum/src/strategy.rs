// src/strategy.rs
use crate::ir::QuantumOp;
use crate::pathsum::PathSum;
use similar::{Algorithm, DiffOp};
use std::cmp;
use std::num::NonZeroUsize;

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
    /// Interleave both circuits and reduce after every ten logical gates.
    pub fn run(&self, ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
        self.run_with_interval(ps, gates1, gates2, NonZeroUsize::new(10).unwrap())
    }

    fn run_with_interval(
        &self,
        ps: PathSum,
        gates1: &[QuantumOp],
        gates2: &[QuantumOp],
        interval: NonZeroUsize,
    ) -> PathSum {
        let mut checkpoint = ReductionCheckpoint::new(ps, interval);
        if gates2.is_empty() {
            run_straightforward(&mut checkpoint, gates1, gates2);
        } else {
            match self {
                Self::Naive => run_naive(&mut checkpoint, gates1, gates2),
                Self::Straightforward => run_straightforward(&mut checkpoint, gates1, gates2),
                Self::Proportional => run_proportional(&mut checkpoint, gates1, gates2),
                Self::Difference => run_difference(&mut checkpoint, gates1, gates2),
            }
        }
        checkpoint.finish()
    }
}

// Own reduction timing for one entire strategy, including batches and tails.
struct ReductionCheckpoint {
    ps: PathSum,
    enabled: bool,
    interval: NonZeroUsize,
    pending: usize,
    dirty: bool,
}

impl ReductionCheckpoint {
    fn new(mut ps: PathSum, interval: NonZeroUsize) -> Self {
        let enabled = ps.is_auto_reduce();
        ps.set_auto_reduce(false);
        // Even an empty gate stream may receive an unreduced PathSum.
        Self {
            ps,
            enabled,
            interval,
            pending: 0,
            dirty: true,
        }
    }

    fn apply(&mut self, gate: &QuantumOp, is_bra: bool) {
        gate.apply(&mut self.ps, is_bra);
        self.pending += 1;
        self.dirty = true;
        if self.pending == self.interval.get() {
            if self.enabled {
                self.reduce();
            } else {
                self.pending = 0;
            }
        }
    }

    fn reduce(&mut self) {
        // full_reduce itself checks this flag; suppression alone is insufficient.
        self.ps.set_auto_reduce(true);
        self.ps.full_reduce();
        self.ps.set_auto_reduce(false);
        self.pending = 0;
        self.dirty = false;
    }

    fn finish(mut self) -> PathSum {
        if self.enabled && self.dirty {
            self.reduce();
        }
        self.ps.set_auto_reduce(self.enabled);
        self.ps
    }
}

// Apply all gates2 as Bra, then all gates1 as Ket
fn run_straightforward(
    checkpoint: &mut ReductionCheckpoint,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
) {
    for gate in gates2 {
        checkpoint.apply(gate, true);
    }
    for gate in gates1 {
        checkpoint.apply(gate, false);
    }
}

// Interleave gates until the shorter sequence ends, then apply remaining
fn run_naive(checkpoint: &mut ReductionCheckpoint, gates1: &[QuantumOp], gates2: &[QuantumOp]) {
    let min_len = cmp::min(gates1.len(), gates2.len());

    for i in 0..min_len {
        checkpoint.apply(&gates1[i], false);
        checkpoint.apply(&gates2[i], true);
    }

    if gates1.len() > gates2.len() {
        for i in min_len..gates1.len() {
            checkpoint.apply(&gates1[i], false);
        }
    } else if gates2.len() > gates1.len() {
        for i in min_len..gates2.len() {
            checkpoint.apply(&gates2[i], true);
        }
    }
}

// Mix operations based on length ratio between circuits
fn run_proportional(
    checkpoint: &mut ReductionCheckpoint,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
) {
    let l1 = gates1.len();
    let l2 = gates2.len();

    if l1 == 0 && l2 == 0 {
        return;
    }
    if l1 == 0 || l2 == 0 {
        return run_straightforward(checkpoint, gates1, gates2);
    }

    let min_len = cmp::min(l1, l2);
    let diff = (l1 as isize) - (l2 as isize);
    let r = if diff > 0 { l1 / l2 } else { l2 / l1 };

    if r == 1 {
        for i in 0..min_len {
            checkpoint.apply(&gates1[i], false);
            checkpoint.apply(&gates2[i], true);
        }

        if diff > 0 {
            for i in 0..(diff as usize) {
                checkpoint.apply(&gates1[min_len + i], false);
            }
        } else if diff < 0 {
            for i in 0..(diff.abs() as usize) {
                checkpoint.apply(&gates2[min_len + i], true);
            }
        }
    } else if diff > 0 {
        // gates1 is longer: apply r Kets per Bra
        for i in 0..l2 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l1 {
                    checkpoint.apply(&gates1[idx], false);
                }
            }
            checkpoint.apply(&gates2[i], true);
        }

        let d2 = l1 - r * l2;
        if d2 > 0 {
            let start_idx = l2 * r;
            for i in 0..d2 {
                if start_idx + i < l1 {
                    checkpoint.apply(&gates1[start_idx + i], false);
                }
            }
        }
    } else {
        // gates2 is longer: apply r Bras per Ket
        for i in 0..l1 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l2 {
                    checkpoint.apply(&gates2[idx], true);
                }
            }
            checkpoint.apply(&gates1[i], false);
        }

        let d2 = l2 - r * l1;
        if d2 > 0 {
            let start_idx = l1 * r;
            for i in 0..d2 {
                if start_idx + i < l2 {
                    checkpoint.apply(&gates2[start_idx + i], true);
                }
            }
        }
    }
}

// Use diff algorithm to identify and process only differing parts
fn run_difference(
    checkpoint: &mut ReductionCheckpoint,
    gates1: &[QuantumOp],
    gates2: &[QuantumOp],
) {
    let diff_ops = similar::capture_diff_slices(Algorithm::Myers, gates1, gates2);

    for op in diff_ops {
        match op {
            DiffOp::Equal {
                old_index,
                new_index,
                len,
            } => {
                for i in 0..len {
                    checkpoint.apply(&gates1[old_index + i], false);
                    checkpoint.apply(&gates2[new_index + i], true);
                }
            }
            DiffOp::Delete {
                old_index, old_len, ..
            } => {
                for i in 0..old_len {
                    checkpoint.apply(&gates1[old_index + i], false);
                }
            }
            DiffOp::Insert {
                new_index, new_len, ..
            } => {
                for i in 0..new_len {
                    checkpoint.apply(&gates2[new_index + i], true);
                }
            }
            DiffOp::Replace {
                old_index,
                old_len,
                new_index,
                new_len,
            } => {
                for i in 0..old_len {
                    checkpoint.apply(&gates1[old_index + i], false);
                }
                for i in 0..new_len {
                    checkpoint.apply(&gates2[new_index + i], true);
                }
            }
        }
    }
}

#[cfg(test)]
pub(crate) mod periodic_red_tests;
