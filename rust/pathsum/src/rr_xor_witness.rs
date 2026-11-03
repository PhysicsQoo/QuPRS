//! Opt-in, RR-only witness of **actual HH substitution events**.
//!
//! This module exists solely for the isolated CodSpeed experiment. It is
//! disabled in every production/default build. No timing is performed here;
//! costs must come from native CodSpeed Simulation/flamegraphs, not Instants.
//! Sampling/cloning happens only with a collector active, outside timed benches.
use std::cell::RefCell;
use rustc_hash::FxHashSet;
use crate::pathsum::{Monomial, PhasePolynomial};

#[derive(Clone, Debug, Default)]
pub struct Counts {
    pub hh_substitutions: usize,
    pub phase_affected: usize,
    pub no_affected_terms: usize,
    pub zero_replacements: usize,
    pub singleton_replacements: usize,
    pub shared_xor_hits: usize,
    pub shared_symbolic_hits: usize,
    pub parity_xor_hits: usize,
    pub parity_exact_radian_hits: usize,
    pub total_affected_terms: usize,
    pub max_affected_terms: usize,
    pub max_replacement_terms: usize,
    pub sample_truncations: usize,
}

/// Untimed classification of real Bra-CX phase substitutions. Only
/// collected when the HH witness session is explicitly active.
#[derive(Clone, Debug, Default)]
pub struct BraCxCounts {
    pub calls: usize,
    pub touched_calls: usize,
    pub unaffected_calls: usize,
    pub affected_terms: usize,
    /// Actual generic PhasePolynomial shared path triggered by Bra-CX.
    pub shared_xor_calls: usize,
    pub shared_affected_terms: usize,
    pub shared_call_indices: Vec<usize>,
    pub parity_xor_calls: usize,
    pub parity_affected_terms: usize,
    pub exact_radian_parity_calls: usize,
    pub exact_radian_terms: usize,
    pub symbolic_terms: usize,
    pub control_overlap_terms: usize,
    pub peak_phase_terms: usize,
    pub peak_affected_terms: usize,
    /// Number of calls touching 0, 1, 2-4, 5-16, 17-64, 65-256, >256 terms.
    pub affected_histogram: [usize; 7],
    /// Small and lossless for the bounded source-pinned QASM fixtures.
    pub affected_per_call: Vec<usize>,
}

#[derive(Clone, Debug)]
pub struct Snapshot {
    pub polynomial: PhasePolynomial,
    pub target: u32,
    pub replacement: FxHashSet<Monomial>,
}

#[derive(Clone, Debug, Default)]
pub struct Witness {
    pub counts: Counts,
    pub bra_cx: BraCxCounts,
    pub samples: Vec<Snapshot>,
    pub sample_limit: usize,
}

thread_local! {
    static ACTIVE: RefCell<Option<Witness>> = const { RefCell::new(None) };
}

/// Start tracing *one* real verifier miter on the current thread.
pub fn begin(sample_limit: usize) {
    ACTIVE.with(|slot| *slot.borrow_mut() = Some(Witness {
        sample_limit, ..Witness::default()
    }));
}

/// Stop tracing and return all counters and a bounded set of exact input
/// snapshots. `sample_truncations` never silently disappears.
pub fn finish() -> Witness {
    ACTIVE.with(|slot| slot.borrow_mut().take().expect("RR witness not started"))
}

/// Called solely from try_reduce_hh, at its real substitution site after
/// the integration-variable phase terms have been removed.
pub(crate) fn observe_hh(
    phase: &PhasePolynomial,
    target: u32,
    replacement: &FxHashSet<Monomial>,
) {
    ACTIVE.with(|slot| {
        let mut guard = slot.borrow_mut();
        let Some(w) = guard.as_mut() else { return; };
        let mut affected = 0usize;
        let mut exact_radians = false;
        let mut symbolic = false;
        for (mono, coeff) in &phase.terms {
            if mono.contains(&target) {
                affected += 1;
                exact_radians |= coeff.radians.is_some();
                symbolic |= !coeff.symbols.is_empty();
            }
        }
        let c = &mut w.counts;
        c.hh_substitutions += 1;
        c.total_affected_terms += affected;
        c.max_affected_terms = c.max_affected_terms.max(affected);
        c.max_replacement_terms = c.max_replacement_terms.max(replacement.len());
        if affected == 0 {
            c.no_affected_terms += 1;
            return;
        }
        c.phase_affected += 1;
        if replacement.is_empty() {
            c.zero_replacements += 1;
        } else if replacement.len() == 1 {
            c.singleton_replacements += 1;
        } else if affected > 1 && replacement.len() <= 12 && !exact_radians {
            // Exactly the production should_share_xor_expansion predicate.
            c.shared_xor_hits += 1;
            if symbolic { c.shared_symbolic_hits += 1; }
        } else {
            c.parity_xor_hits += 1;
            if exact_radians { c.parity_exact_radian_hits += 1; }
        }
        if w.samples.len() < w.sample_limit {
            w.samples.push(Snapshot {
                polynomial: phase.clone(), target,
                replacement: replacement.clone(),
            });
        } else {
            c.sample_truncations += 1;
        }
    });
}

/// Observe a genuine Bra-side CX before its exact phase substitution.
/// Distinguish it from HH and from the Ket-side BooleanState-only CX.
/// Counts, sizes and coefficient classes have no CPU timer and are never
/// evaluated inside the official CodSpeed measured path.
pub(crate) fn observe_bra_cx(phase: &PhasePolynomial, target: u32, control: u32) {
    ACTIVE.with(|slot| {
        let mut guard = slot.borrow_mut();
        let Some(w) = guard.as_mut() else { return; };
        let b = &mut w.bra_cx;
        b.calls += 1;
        b.peak_phase_terms = b.peak_phase_terms.max(phase.terms.len());
        let mut affected = 0;
        let mut has_exact_radians = false;
        for (mono, coeff) in &phase.terms {
            if !mono.contains(&target) { continue; }
            affected += 1;
            has_exact_radians |= coeff.radians.is_some();
            b.exact_radian_terms += usize::from(coeff.radians.is_some());
            b.symbolic_terms += usize::from(!coeff.symbols.is_empty());
            b.control_overlap_terms += usize::from(mono.contains(&control));
        }
        if affected == 0 {
            b.unaffected_calls += 1;
        } else {
            b.touched_calls += 1;
            // Bra CX always substitutes exactly two distinct single
            // monomials: [target] XOR [control]. This exactly matches the
            // existing production predicate for 2-source XOR expansion.
            if affected > 1 && !has_exact_radians {
                b.shared_xor_calls += 1;
                b.shared_affected_terms += affected;
                b.shared_call_indices.push(b.calls - 1);
            } else {
                b.parity_xor_calls += 1;
                b.parity_affected_terms += affected;
                b.exact_radian_parity_calls += usize::from(has_exact_radians);
            }
        }
        b.affected_terms += affected;
        b.peak_affected_terms = b.peak_affected_terms.max(affected);
        b.affected_per_call.push(affected);
        let bucket = match affected {
            0 => 0, 1 => 1, 2..=4 => 2, 5..=16 => 3,
            17..=64 => 4, 65..=256 => 5, _ => 6,
        };
        b.affected_histogram[bucket] += 1;
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PhaseCoeff;
    #[test]
    fn feature_witness_counts_only_when_started_and_never_times() {
        let mut p = PhasePolynomial::new();
        p.add_term(vec![0], PhaseCoeff::HALF);
        p.add_term(vec![0, 2], PhaseCoeff::QUARTER);
        let sub: FxHashSet<Monomial> = [vec![1], vec![3]].into_iter().collect();
        observe_hh(&p, 0, &sub); // disabled
        begin(1);
        observe_hh(&p, 0, &sub);
        observe_hh(&p, 0, &sub);
        observe_bra_cx(&p, 0, 2);
        let w = finish();
        assert_eq!(w.counts.hh_substitutions, 2);
        assert_eq!(w.counts.shared_xor_hits, 2);
        assert_eq!(w.samples.len(), 1);
        assert_eq!(w.counts.sample_truncations, 1);
        assert_eq!(w.bra_cx.calls, 1);
        assert_eq!(w.bra_cx.affected_terms, 2);
        assert_eq!(w.bra_cx.control_overlap_terms, 1);
        assert_eq!(w.bra_cx.affected_histogram[2], 1);
        assert_eq!(w.bra_cx.shared_xor_calls, 1);
        assert_eq!(w.bra_cx.shared_call_indices, vec![0]);
        assert_eq!(w.bra_cx.parity_xor_calls, 0);
    }
}
