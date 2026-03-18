// src/strategy.rs
use crate::pathsum::PathSum;
use crate::ir::QuantumOp;
use std::cmp;
use similar::{Algorithm, DiffOp};

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
    ) -> PathSum {
        if gates2.is_empty() {
            return run_straightforward(ps, gates1, gates2);
        }
        match self {
            Self::Naive => run_naive(ps, gates1, gates2),
            Self::Straightforward => run_straightforward(ps, gates1, gates2),
            Self::Proportional => run_proportional(ps, gates1, gates2),
            Self::Difference => run_difference(ps, gates1, gates2),
        }
    }
}

// Apply all gates2 as Bra, then all gates1 as Ket
fn run_straightforward(mut ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
    for gate in gates2 {
        gate.apply(&mut ps, true);
    }
    for gate in gates1 {
        gate.apply(&mut ps, false);
    }
    if ps.is_auto_reduce() {
        ps.full_reduce();
    }
    ps
}

// Interleave gates until the shorter sequence ends, then apply remaining
fn run_naive(mut ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
    let min_len = cmp::min(gates1.len(), gates2.len());
    
    for i in 0..min_len {
        gates1[i].apply(&mut ps, false);
        gates2[i].apply(&mut ps, true);
    }
    
    if gates1.len() > gates2.len() {
        for i in min_len..gates1.len() {
            gates1[i].apply(&mut ps, false);
        }
    } else if gates2.len() > gates1.len() {
        for i in min_len..gates2.len() {
            gates2[i].apply(&mut ps, true);
        }
    }

    if ps.is_auto_reduce() {
        ps.full_reduce();
    }
    ps
}

// Mix operations based on length ratio between circuits
fn run_proportional(mut ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
    let l1 = gates1.len();
    let l2 = gates2.len();
    
    if l1 == 0 && l2 == 0 { return ps; }
    if l1 == 0 || l2 == 0 { return run_straightforward(ps, gates1, gates2); }

    let min_len = cmp::min(l1, l2);
    let diff = (l1 as isize) - (l2 as isize);
    let r = if diff > 0 { l1 / l2 } else { l2 / l1 };

    if r == 1 {
        for i in 0..min_len {
            gates1[i].apply(&mut ps, false);
            gates2[i].apply(&mut ps, true);
        }
        
        if diff > 0 {
            for i in 0..(diff as usize) {
                gates1[min_len + i].apply(&mut ps, false);
            }
        } else if diff < 0 {
            for i in 0..(diff.abs() as usize) {
                gates2[min_len + i].apply(&mut ps, true);
            }
        }
    } else if diff > 0 {
        // gates1 is longer: apply r Kets per Bra
        for i in 0..l2 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l1 { 
                    gates1[idx].apply(&mut ps, false); 
                }
            }
            gates2[i].apply(&mut ps, true);
        }
        
        let d2 = l1 - r * l2;
        if d2 > 0 {
            let start_idx = l2 * r;
            for i in 0..d2 {
                if start_idx + i < l1 {
                    gates1[start_idx + i].apply(&mut ps, false);
                }
            }
        }
    } else {
        // gates2 is longer: apply r Bras per Ket
        for i in 0..l1 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l2 { 
                    gates2[idx].apply(&mut ps, true); 
                }
            }
            gates1[i].apply(&mut ps, false);
        }
        
        let d2 = l2 - r * l1;
        if d2 > 0 {
            let start_idx = l1 * r;
            for i in 0..d2 {
                if start_idx + i < l2 {
                    gates2[start_idx + i].apply(&mut ps, true);
                }
            }
        }
    }

    if ps.is_auto_reduce() {
        ps.full_reduce();
    }
    ps
}

// Use diff algorithm to identify and process only differing parts
fn run_difference(mut ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
    let diff_ops = similar::capture_diff_slices(Algorithm::Myers, gates1, gates2);

    for op in diff_ops {
        match op {
            DiffOp::Equal { old_index, new_index, len } => {
                for i in 0..len {
                    gates1[old_index + i].apply(&mut ps, false);
                    gates2[new_index + i].apply(&mut ps, true);
                }
            },
            DiffOp::Delete { old_index, old_len, .. } => {
                for i in 0..old_len {
                    gates1[old_index + i].apply(&mut ps, false);
                }
            },
            DiffOp::Insert { new_index, new_len, .. } => {
                for i in 0..new_len {
                    gates2[new_index + i].apply(&mut ps, true);
                }
            },
            DiffOp::Replace { old_index, old_len, new_index, new_len } => {
                for i in 0..old_len {
                    gates1[old_index + i].apply(&mut ps, false);
                }
                for i in 0..new_len {
                    gates2[new_index + i].apply(&mut ps, true);
                }
            },
        }
    }

    if ps.is_auto_reduce() {
        ps.full_reduce();
    }
    ps
}