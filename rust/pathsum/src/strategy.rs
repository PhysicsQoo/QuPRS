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
        self.run_with_deadline(ps, gates1, gates2, None)
    }

    /// Cooperatively abort the request at gate/reduction safe points.
    /// The returned PathSum is partial whenever deadline_exceeded is true.
    pub(crate) fn run_with_deadline(
        &self,
        mut ps: PathSum,
        gates1: &[QuantumOp],
        gates2: &[QuantumOp],
        deadline: Option<std::time::Instant>,
    ) -> PathSum {
        ps.set_verification_deadline(deadline);
        if !ps.poll_verification_deadline() { return ps; }
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

/// Applies one gate without changing the existing automatic reduction cadence.
/// Gate-internal auto-reduction observes the same request deadline.
fn apply_checked(ps: &mut PathSum, gate: &QuantumOp, bra: bool) -> bool {
    if !ps.poll_verification_deadline() { return false; }
    gate.apply(ps, bra);
    ps.poll_verification_deadline()
}

// Apply all gates2 as Bra, then all gates1 as Ket
fn run_straightforward(mut ps: PathSum, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> PathSum {
    for gate in gates2 {
        if !apply_checked(&mut ps, &gate, true) { return ps; }
    }
    for gate in gates1 {
        if !apply_checked(&mut ps, &gate, false) { return ps; }
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
        if !apply_checked(&mut ps, &gates1[i], false) { return ps; }
        if !apply_checked(&mut ps, &gates2[i], true) { return ps; }
    }
    
    if gates1.len() > gates2.len() {
        for i in min_len..gates1.len() {
            if !apply_checked(&mut ps, &gates1[i], false) { return ps; }
        }
    } else if gates2.len() > gates1.len() {
        for i in min_len..gates2.len() {
            if !apply_checked(&mut ps, &gates2[i], true) { return ps; }
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
            if !apply_checked(&mut ps, &gates1[i], false) { return ps; }
            if !apply_checked(&mut ps, &gates2[i], true) { return ps; }
        }
        
        if diff > 0 {
            for i in 0..(diff as usize) {
                if !apply_checked(&mut ps, &gates1[min_len + i], false) { return ps; }
            }
        } else if diff < 0 {
            for i in 0..(diff.abs() as usize) {
                if !apply_checked(&mut ps, &gates2[min_len + i], true) { return ps; }
            }
        }
    } else if diff > 0 {
        // gates1 is longer: apply r Kets per Bra
        for i in 0..l2 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l1 { 
                    if !apply_checked(&mut ps, &gates1[idx], false) { return ps; } 
                }
            }
            if !apply_checked(&mut ps, &gates2[i], true) { return ps; }
        }
        
        let d2 = l1 - r * l2;
        if d2 > 0 {
            let start_idx = l2 * r;
            for i in 0..d2 {
                if start_idx + i < l1 {
                    if !apply_checked(&mut ps, &gates1[start_idx + i], false) { return ps; }
                }
            }
        }
    } else {
        // gates2 is longer: apply r Bras per Ket
        for i in 0..l1 {
            for j in 0..r {
                let idx = i * r + j;
                if idx < l2 { 
                    if !apply_checked(&mut ps, &gates2[idx], true) { return ps; } 
                }
            }
            if !apply_checked(&mut ps, &gates1[i], false) { return ps; }
        }
        
        let d2 = l2 - r * l1;
        if d2 > 0 {
            let start_idx = l1 * r;
            for i in 0..d2 {
                if start_idx + i < l2 {
                    if !apply_checked(&mut ps, &gates2[start_idx + i], true) { return ps; }
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
    // Myers is a non-interruptible library call; poll before/after and do not
    // claim a hard wall-clock bound for large diffs.
    if !ps.poll_verification_deadline() { return ps; }
    let diff_ops = similar::capture_diff_slices(Algorithm::Myers, gates1, gates2);
    if !ps.poll_verification_deadline() { return ps; }

    for op in diff_ops {
        match op {
            DiffOp::Equal { old_index, new_index, len } => {
                for i in 0..len {
                    if !apply_checked(&mut ps, &gates1[old_index + i], false) { return ps; }
                    if !apply_checked(&mut ps, &gates2[new_index + i], true) { return ps; }
                }
            },
            DiffOp::Delete { old_index, old_len, .. } => {
                for i in 0..old_len {
                    if !apply_checked(&mut ps, &gates1[old_index + i], false) { return ps; }
                }
            },
            DiffOp::Insert { new_index, new_len, .. } => {
                for i in 0..new_len {
                    if !apply_checked(&mut ps, &gates2[new_index + i], true) { return ps; }
                }
            },
            DiffOp::Replace { old_index, old_len, new_index, new_len } => {
                for i in 0..old_len {
                    if !apply_checked(&mut ps, &gates1[old_index + i], false) { return ps; }
                }
                for i in 0..new_len {
                    if !apply_checked(&mut ps, &gates2[new_index + i], true) { return ps; }
                }
            },
        }
    }

    if ps.is_auto_reduce() {
        ps.full_reduce();
    }
    ps
}
#[cfg(test)]
mod cooperative_deadline_tests {
    use super::*;
    use std::time::{Duration, Instant};

    #[test]
    fn expired_before_first_gate_never_applies_a_partial_circuit() {
        let expired = Instant::now() - Duration::from_millis(1);
        for strategy in [
            VerificationStrategy::Naive,
            VerificationStrategy::Straightforward,
            VerificationStrategy::Proportional,
            VerificationStrategy::Difference,
        ] {
            let before = PathSum::new(1);
            let result = strategy.run_with_deadline(
                before.clone(), &[QuantumOp::H(0)], &[QuantumOp::H(0)],
                Some(expired),
            );
            assert!(result.deadline_exceeded, "{strategy:?}");
            assert_eq!(result.p.terms, before.p.terms, "{strategy:?}");
            assert_eq!(result.f.functions, before.f.functions, "{strategy:?}");
        }
    }

    #[test]
    fn unbounded_checked_run_preserves_legacy_gate_order_and_rr() {
        let reference = [QuantumOp::H(0), QuantumOp::X(0), QuantumOp::H(0)];
        let verification = [QuantumOp::X(0)];
        for strategy in [
            VerificationStrategy::Naive,
            VerificationStrategy::Straightforward,
            VerificationStrategy::Proportional,
            VerificationStrategy::Difference,
        ] {
            let base = PathSum::new(1);
            let legacy = strategy.run(base.clone(), &reference, &verification);
            let checked = strategy.run_with_deadline(
                base, &reference, &verification, Some(Instant::now() + Duration::from_secs(30)),
            );
            assert!(!checked.deadline_exceeded);
            assert_eq!(checked.p.terms, legacy.p.terms);
            assert_eq!(checked.f.functions, legacy.f.functions);
            assert_eq!(checked.v.path_vars, legacy.v.path_vars);
        }
    }

    #[test]
    fn reduction_does_not_continue_after_expiration() {
        let mut ps = PathSum::new(1);
        ps.set_verification_deadline(Some(Instant::now() - Duration::from_millis(1)));
        ps.full_reduce();
        assert!(ps.deadline_exceeded);
        assert!(!ps.poll_verification_deadline());
    }
}

#[cfg(test)]
mod cooperative_request_isolation_tests {
    use super::*;
    use std::thread;
    use std::time::{Duration, Instant};

    #[test]
    fn concurrent_requests_do_not_share_deadline_or_timeout_state() {
        let reference = vec![QuantumOp::H(0), QuantumOp::T(0), QuantumOp::H(0)];
        let expired = Instant::now() - Duration::from_millis(1);
        let run_a = reference.clone();
        let run_b = reference.clone();
        let a = thread::spawn(move || {
            VerificationStrategy::Straightforward.run_with_deadline(
                PathSum::new(1), &run_a, &[], Some(expired),
            )
        });
        let b = thread::spawn(move || {
            VerificationStrategy::Straightforward.run_with_deadline(
                PathSum::new(1), &run_b, &[], Some(Instant::now() + Duration::from_secs(30)),
            )
        });
        let a = a.join().expect("expired request");
        let b = b.join().expect("unexpired request");
        assert!(a.deadline_exceeded);
        assert!(!b.deadline_exceeded);
        assert!(a.p.terms.is_empty());
        let legacy = VerificationStrategy::Straightforward.run(
            PathSum::new(1), &reference, &[],
        );
        assert_eq!(b.p.terms, legacy.p.terms);
        assert_eq!(b.f.functions, legacy.f.functions);
    }
}
