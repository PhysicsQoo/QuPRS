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

#[derive(Clone, Debug)]
pub struct Snapshot {
    pub polynomial: PhasePolynomial,
    pub target: u32,
    pub replacement: FxHashSet<Monomial>,
}

#[derive(Clone, Debug, Default)]
pub struct Witness {
    pub counts: Counts,
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
        let w = finish();
        assert_eq!(w.counts.hh_substitutions, 2);
        assert_eq!(w.counts.shared_xor_hits, 2);
        assert_eq!(w.samples.len(), 1);
        assert_eq!(w.counts.sample_truncations, 1);
    }
}
