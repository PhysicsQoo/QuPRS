//! Opt-in, thread-local, exclusive Rust stage timing for scientific diagnostics.
//!
//! Disabled unless QUPRS_STAGE_LEDGER=1. All counters are owned by the current
//! verification's thread; the previous recorder is restored on every return,
//! including early Result::Err paths. No solver or reduction semantics change.

use std::cell::RefCell;
use std::collections::BTreeMap;
use std::time::Instant;

#[derive(Clone, Debug, Default)]
struct Recorder {
    durations: BTreeMap<&'static str, f64>,
    calls: BTreeMap<&'static str, u64>,
    reduction_depth: u32,
    max_reduction_depth: u32,
    solver_spawns: u64,
    structural_elim_attempts: Vec<ElimStructuralSample>,
    elim_timing_enabled: bool,
    elim_attempt_timings: Vec<ElimAttemptTiming>,
    other_rule_timing_enabled: bool,
    other_rule_timings: Vec<RuleTimingSample>,
}

thread_local! {
    static RECORDER: RefCell<Option<Recorder>> = const { RefCell::new(None) };
}

pub(crate) struct Session {
    previous: Option<Recorder>,
}

impl Session {
    pub(crate) fn from_environment() -> Option<Self> {
        let enabled = std::env::var("QUPRS_STAGE_LEDGER").ok().as_deref() == Some("1");
        // Timing is a second, independent opt-in: no timing allocations or
        // Instant reads if only the ordinary stage ledger is enabled.
        let timing_enabled = std::env::var("QUPRS_ELIM_TIMING").ok().as_deref() == Some("1");
        let other_timing_enabled = enabled &&
            std::env::var("QUPRS_OTHER_RULE_TIMING").ok().as_deref() == Some("1");
        Self::start_with_rule_timing(enabled, timing_enabled, other_timing_enabled)
    }

    fn start(enabled: bool) -> Option<Self> {
        Self::start_with_rule_timing(enabled, false, false)
    }

    fn start_with_elim_timing(enabled: bool, timing_enabled: bool) -> Option<Self> {
        Self::start_with_rule_timing(enabled, timing_enabled, false)
    }

    fn start_with_rule_timing(
        enabled: bool, elim_timing_enabled: bool, other_rule_timing_enabled: bool
    ) -> Option<Self> {
        if !enabled {
            return None;
        }
        let previous = RECORDER.with(|cell| {
            cell.replace(Some(Recorder {
                elim_timing_enabled,
                other_rule_timing_enabled,
                ..Recorder::default()
            }))
        });
        Some(Self { previous })
    }

    pub(crate) fn snapshot(&self, total_wall: f64, pathsum_total: f64) -> ExclusiveLedger {
        let raw = RECORDER.with(|cell| {
            cell.borrow().as_ref().cloned().expect("active stage recorder")
        });
        raw.into_exclusive(total_wall, pathsum_total)
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        let previous = self.previous.take();
        RECORDER.with(|cell| {
            cell.replace(previous);
        });
    }
}

pub(crate) struct Stage {
    name: &'static str,
    started: Instant,
    reduction_outermost: bool,
}

pub(crate) fn span(name: &'static str) -> Option<Stage> {
    let outermost = RECORDER.with(|cell| {
        let mut active = cell.borrow_mut();
        let record = active.as_mut()?;
        *record.calls.entry(name).or_default() += 1;
        if name == "reduction" {
            record.reduction_depth += 1;
            record.max_reduction_depth = record.max_reduction_depth.max(record.reduction_depth);
            Some(record.reduction_depth == 1)
        } else {
            Some(true)
        }
    })?;
    Some(Stage {
        name,
        started: Instant::now(),
        reduction_outermost: outermost,
    })
}

impl Drop for Stage {
    fn drop(&mut self) {
        let elapsed = self.started.elapsed().as_secs_f64();
        RECORDER.with(|cell| {
            if let Some(record) = cell.borrow_mut().as_mut() {
                if self.name == "reduction" {
                    debug_assert!(record.reduction_depth > 0);
                    record.reduction_depth -= 1;
                }
                if self.reduction_outermost {
                    *record.durations.entry(self.name).or_default() += elapsed;
                }
            }
        });
    }
}

/// Called only after OS child-process creation has succeeded. This separates
/// a solver truly launched from inferred solver time or zero-variable bypass.
pub(crate) fn child_spawned() {
    RECORDER.with(|cell| {
        if let Some(recorder) = cell.borrow_mut().as_mut() {
            recorder.solver_spawns += 1;
        }
    });
}

/// Observations at entry to Elim, before it mutates PathSum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ElimStructuralSample {
    pub k_r: usize,
    pub l_r: usize,
    pub v_r: usize,
    pub d_r: usize,
    pub w_redundant_estimated: usize,
}

/// Rule discovery/HH/Omega timing is a third, independent opt-in stream.
/// These clocks are nested in the root Reduction wall and never added to it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RuleTimingSample {
    pub rule: &'static str,
    pub elapsed_ns: u64,
    pub success: bool,
    pub candidate_count: usize,
    pub within_reduction: bool,
}

pub(crate) struct RuleTimingGuard {
    rule: &'static str,
    started: Instant,
    success: bool,
    candidate_count: usize,
    within_reduction: bool,
}

impl RuleTimingGuard {
    pub(crate) fn mark_success(&mut self) { self.success = true; }
    pub(crate) fn set_candidates(&mut self, count: usize) {
        self.candidate_count = count;
    }
}

impl Drop for RuleTimingGuard {
    fn drop(&mut self) {
        let elapsed_ns = self.started.elapsed().as_nanos().min(u64::MAX as u128) as u64;
        RECORDER.with(|cell| {
            if let Some(recorder) = cell.borrow_mut().as_mut() {
                if recorder.other_rule_timing_enabled {
                    recorder.other_rule_timings.push(RuleTimingSample {
                        rule: self.rule,
                        elapsed_ns,
                        success: self.success,
                        candidate_count: self.candidate_count,
                        within_reduction: self.within_reduction,
                    });
                }
            }
        });
    }
}

/// No Instant read or allocation when no active session or the third flag
/// QUPRS_OTHER_RULE_TIMING is absent. The label is restricted to known stages.
pub(crate) fn time_rule(
    rule: &'static str, candidate_count: usize
) -> Option<RuleTimingGuard> {
    debug_assert!(matches!(rule, "candidate_discovery" | "hh" | "omega"));
    let within_reduction = RECORDER.with(|cell| {
        let borrow = cell.borrow();
        let recorder = borrow.as_ref()?;
        recorder.other_rule_timing_enabled.then_some(recorder.reduction_depth > 0)
    })?;
    Some(RuleTimingGuard {
        rule,
        started: Instant::now(),
        success: false,
        candidate_count,
        within_reduction,
    })
}

/// A dedicated elapsed clock for the Elim rule body, excluding structural
/// snapshot scans. Each timing references the corresponding structural sample.
pub(crate) struct ElimAttemptGuard {
    structural_index: usize,
    started: Instant,
    success: bool,
}

impl ElimAttemptGuard {
    pub(crate) fn mark_success(&mut self) {
        self.success = true;
    }
}

impl Drop for ElimAttemptGuard {
    fn drop(&mut self) {
        let elapsed_ns = self.started.elapsed().as_nanos().min(u64::MAX as u128) as u64;
        RECORDER.with(|cell| {
            if let Some(recorder) = cell.borrow_mut().as_mut() {
                if recorder.elim_timing_enabled {
                    recorder.elim_attempt_timings.push(ElimAttemptTiming {
                        structural_index: self.structural_index,
                        elapsed_ns,
                        success: self.success,
                    });
                }
            }
        });
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ElimAttemptTiming {
    pub structural_index: usize,
    pub elapsed_ns: u64,
    pub success: bool,
}

/// The closure is never called unless an explicit stage-ledger session exists.
/// The rule-body clock starts only *after* pre-Elim feature extraction.
pub(crate) fn observe_elim_attempt<F>(measure: F) -> Option<ElimAttemptGuard>
where
    F: FnOnce() -> (usize, usize, usize, usize),
{
    let timing_enabled = RECORDER.with(|cell| {
        cell.borrow().as_ref().map(|r| r.elim_timing_enabled)
    })?;
    let (k_r, l_r, v_r, d_r) = measure();
    let sample = ElimStructuralSample {
        k_r, l_r, v_r, d_r,
        // Historical pre-Hoist redundant scan proxy; never measured time.
        w_redundant_estimated: k_r.saturating_sub(1).saturating_mul(l_r),
    };
    let structural_index = RECORDER.with(|cell| {
        let mut borrow = cell.borrow_mut();
        let recorder = borrow.as_mut().expect("active Elim stage recorder");
        let index = recorder.structural_elim_attempts.len();
        recorder.structural_elim_attempts.push(sample);
        index
    });
    timing_enabled.then(|| ElimAttemptGuard {
        structural_index,
        started: Instant::now(),
        success: false,
    })
}

#[derive(Debug, Clone)]
pub struct ExclusiveLedger {
    pub schema: &'static str,
    pub total_native_wall_seconds: f64,
    pub seconds: BTreeMap<&'static str, f64>,
    pub calls: BTreeMap<&'static str, u64>,
    pub solver_child_spawns: u64,
    pub reduction_max_depth: u32,
    pub structural_elim_attempts: Vec<ElimStructuralSample>,
    pub elim_timing_enabled: bool,
    pub elim_attempt_timings: Vec<ElimAttemptTiming>,
    pub other_rule_timing_enabled: bool,
    pub other_rule_timings: Vec<RuleTimingSample>,
    pub closure_error_seconds: f64,
    pub has_stage_overlap: bool,
}

impl Recorder {
    fn into_exclusive(self, total_wall: f64, strategy_total: f64) -> ExclusiveLedger {
        let get = |name: &str| self.durations.get(name).copied().unwrap_or(0.0);
        let reduction = get("reduction");
        let wmc_total = get("wmc_total");
        let cnf_encode = get("cnf_encode");
        let cnf_serialize = get("cnf_serialize");
        let cnf_file_write = get("cnf_file_write");
        let solver_supervision = get("solver_supervision");
        let classification = get("classification");

        // Use precisely disjoint parent/child deltas. Do not add published
        // legacy to_dimacs_time/tool_time, which have other boundaries.
        let gate_except_reduction = strategy_total - reduction;
        let wmc_control = wmc_total
            - cnf_encode
            - cnf_serialize
            - cnf_file_write
            - solver_supervision
            - classification;
        let residual = total_wall - strategy_total - wmc_total;
        let overlap = gate_except_reduction < -0.001
            || wmc_control < -0.001
            || residual < -0.001
            || self.reduction_depth != 0;
        let mut seconds = BTreeMap::new();
        seconds.insert("strategy_except_reduction", gate_except_reduction);
        seconds.insert("reduction", reduction);
        seconds.insert("cnf_encode", cnf_encode);
        seconds.insert("cnf_serialize", cnf_serialize);
        seconds.insert("cnf_file_write", cnf_file_write);
        seconds.insert("solver_supervision", solver_supervision);
        seconds.insert("classification", classification);
        seconds.insert("wmc_other", wmc_control);
        seconds.insert("native_setup_status_other", residual);
        let closure = total_wall - seconds.values().sum::<f64>();
        ExclusiveLedger {
            schema: "quprs-rust-native-exclusive-v0",
            total_native_wall_seconds: total_wall,
            seconds,
            calls: self.calls,
            solver_child_spawns: self.solver_spawns,
            reduction_max_depth: self.max_reduction_depth,
            structural_elim_attempts: self.structural_elim_attempts,
            elim_timing_enabled: self.elim_timing_enabled,
            elim_attempt_timings: self.elim_attempt_timings,
            other_rule_timing_enabled: self.other_rule_timing_enabled,
            other_rule_timings: self.other_rule_timings,
            closure_error_seconds: closure,
            has_stage_overlap: overlap,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nested_reduction_counts_only_outer_wall_and_restores_session() {
        {
            let session = Session::start(true).unwrap();
            {
                let _root = span("reduction");
                {
                    let _nested = span("reduction");
                }
            }
            let observed = session.snapshot(1.0, 0.3);
            assert_eq!(observed.calls["reduction"], 2);
            assert_eq!(observed.reduction_max_depth, 2);
            assert!(!observed.has_stage_overlap);
            assert_eq!(observed.solver_child_spawns, 0);
            assert!(observed.seconds["reduction"] >= 0.0);
            assert!((observed.closure_error_seconds).abs() < 1e-10);
        }
        assert!(span("reduction").is_none(), "session must restore the disabled default");
    }

    #[test]
    fn disjoint_children_and_solver_spawn_are_attributed() {
        let session = Session::start(true).unwrap();
        {
            let _wmc = span("wmc_total");
            {
                let _cnf = span("cnf_encode");
            }
            {
                let _solver = span("solver_supervision");
                child_spawned();
            }
        }
        let result = session.snapshot(1.0, 0.2);
        assert!(!result.has_stage_overlap);
        assert_eq!(result.solver_child_spawns, 1);
        assert!((result.seconds.values().sum::<f64>() - 1.0).abs() < 1e-10);
        assert!(result.seconds["wmc_other"] >= -0.001);
    }

    #[test]
    fn disabled_recorder_does_not_count_anything() {
        assert!(Session::start(false).is_none());
        assert!(span("wmc_total").is_none());
        child_spawned();
    }
    #[test]
    fn zero_candidates_do_not_enter_elim_unless_explicitly_called() {
        use crate::pathsum::PathSum;
        let session = Session::start(true).unwrap();
        let mut ps = PathSum::new(1);
        ps.full_reduce();
        assert!(session.snapshot(1.0, 0.1).structural_elim_attempts.is_empty());
        assert!(!ps.try_reduce_elim(&[]));
        assert_eq!(session.snapshot(1.0, 0.1).structural_elim_attempts,
            vec![ElimStructuralSample {
                k_r: 0, l_r: 0, v_r: 0, d_r: 0, w_redundant_estimated: 0,
            }]);
    }

    #[test]
    fn multiple_candidates_and_elim_success_capture_pre_mutation_work() {
        use crate::pathsum::PathSum;
        use crate::rational::{PhaseCoeff, Rational};
        let session = Session::start(true).unwrap();
        let mut ps = PathSum::new(1);
        ps.v.path_vars.extend([2, 3, 4]);
        ps.p.add_term(vec![2, 3], PhaseCoeff::new_constant(Rational::new(1, 2)));
        let vars = ps.get_reducible_vars();
        assert_eq!(vars.len(), 3);
        assert!(ps.try_reduce_elim(&vars));
        assert!(!ps.v.path_vars.contains(&4));
        assert!(ps.v.path_vars.contains(&2));
        assert!(ps.v.path_vars.contains(&3));
        assert_eq!(session.snapshot(1.0, 0.1).structural_elim_attempts,
            vec![ElimStructuralSample {
                k_r: 3, l_r: 2, v_r: 3, d_r: 1, w_redundant_estimated: 4,
            }]);
    }

    #[test]
    fn empty_phase_means_zero_redundant_scan_proxy() {
        use crate::pathsum::PathSum;
        let session = Session::start(true).unwrap();
        let mut ps = PathSum::new(1);
        ps.v.path_vars.extend([5, 6]);
        assert!(ps.p.terms.is_empty());
        let vars = ps.get_reducible_vars();
        assert_eq!(vars.len(), 2);
        assert!(ps.try_reduce_elim(&vars));
        assert!(!ps.v.path_vars.contains(&5));
        assert!(!ps.v.path_vars.contains(&6));
        assert_eq!(session.snapshot(1.0, 0.1).structural_elim_attempts,
            vec![ElimStructuralSample {
                k_r: 2, l_r: 0, v_r: 2, d_r: 0, w_redundant_estimated: 0,
            }]);
    }

    #[test]
    fn default_off_does_not_change_elim_outcome_or_leak_samples() {
        use crate::pathsum::PathSum;
        let mut off = PathSum::new(1);
        off.v.path_vars.insert(9);
        let mut on = off.clone();
        assert!(Session::start(false).is_none());
        let vars = off.get_reducible_vars();
        let original = off.try_reduce_elim(&vars);
        let session = Session::start(true).unwrap();
        let vars = on.get_reducible_vars();
        assert_eq!(original, on.try_reduce_elim(&vars));
        assert_eq!(off.v.path_vars, on.v.path_vars);
        assert_eq!(off.stats.elim.attempts, on.stats.elim.attempts);
        assert_eq!(off.stats.elim.successes, on.stats.elim.successes);
        assert_eq!(session.snapshot(1.0, 0.1).structural_elim_attempts.len(), 1);
        drop(session);
        assert!(span("reduction").is_none());
    }

    #[test]
    fn elim_body_timing_indices_and_success_outcomes_are_separate_from_features() {
        use crate::pathsum::PathSum;
        use crate::rational::{PhaseCoeff, Rational};
        let session = Session::start_with_elim_timing(true, true).unwrap();
        let mut success = PathSum::new(1);
        success.v.path_vars.insert(7);
        let candidates = success.get_reducible_vars();
        assert!(success.try_reduce_elim(&candidates));

        let mut failure = PathSum::new(1);
        failure.v.path_vars.insert(9);
        failure.p.add_term(vec![9], PhaseCoeff::new_constant(Rational::new(1, 2)));
        let candidates = failure.get_reducible_vars();
        assert!(!failure.try_reduce_elim(&candidates));
        assert!(!failure.try_reduce_elim(&[]));

        let ledger = session.snapshot(1.0, 0.2);
        assert!(ledger.elim_timing_enabled);
        assert_eq!(ledger.structural_elim_attempts.len(), 3);
        assert_eq!(ledger.elim_attempt_timings.len(), 3);
        for (index, sample) in ledger.elim_attempt_timings.iter().enumerate() {
            assert_eq!(sample.structural_index, index);
        }
        assert_eq!(ledger.elim_attempt_timings.iter().map(|t| t.success)
            .collect::<Vec<_>>(), vec![true, false, false]);
        drop(session);
        assert!(span("reduction").is_none());
    }

    #[test]
    fn ordinary_stage_ledger_has_no_elim_body_clocks() {
        use crate::pathsum::PathSum;
        let session = Session::start(true).unwrap();
        let mut ps = PathSum::new(1);
        ps.v.path_vars.insert(9);
        let candidates = ps.get_reducible_vars();
        assert!(ps.try_reduce_elim(&candidates));
        let ledger = session.snapshot(1.0, 0.1);
        assert!(!ledger.elim_timing_enabled);
        assert!(ledger.elim_attempt_timings.is_empty());
        assert_eq!(ledger.structural_elim_attempts.len(), 1);
    }

    #[test]
    fn timing_flag_without_stage_session_never_scans_or_records() {
        use std::cell::Cell;
        let invoked = Cell::new(false);
        let session = Session::start_with_elim_timing(false, true);
        assert!(session.is_none());
        let guard = observe_elim_attempt(|| {
            invoked.set(true);
            (1, 1, 1, 1)
        });
        assert!(guard.is_none());
        assert!(!invoked.get());
    }

    #[test]
    fn independent_rule_timers_cover_discovery_hh_and_omega_with_nested_scope() {
        use crate::pathsum::PathSum;
        use crate::rational::{PhaseCoeff, Rational};
        use crate::gates::{QuantumGates, Side};
        let session = Session::start_with_rule_timing(true, true, true).unwrap();

        let mut ps = PathSum::new(1);
        ps.v.path_vars.insert(9);
        {
            let _root = span("reduction");
            let vars = ps.get_reducible_vars();
            assert_eq!(vars, vec![9]);
        }

        let mut hh = PathSum::new(1);
        hh.set_auto_reduce(false);
        hh.apply_h(0, Side::Ket);
        hh.apply_h(0, Side::Ket);
        let hh_candidates = hh.get_reducible_vars();
        assert!(hh.try_reduce_hh(&hh_candidates));
        assert!(!hh.try_reduce_hh(&[]));

        let mut omega = PathSum::new(1);
        omega.v.path_vars.insert(7);
        omega.p.add_term(vec![7], PhaseCoeff::new_constant(Rational::new(1, 4)));
        assert!(omega.try_reduce_omega(&[7]));
        assert!(!omega.try_reduce_omega(&[]));

        let ledger = session.snapshot(1.0, 0.5);
        assert!(ledger.other_rule_timing_enabled);
        assert!(ledger.other_rule_timings.iter().any(|t|
            t.rule == "candidate_discovery" && t.candidate_count == 1
            && t.success && t.within_reduction));
        assert!(ledger.other_rule_timings.iter().any(|t| t.rule == "hh" && t.success));
        assert!(ledger.other_rule_timings.iter().any(|t| t.rule == "hh" && !t.success));
        assert!(ledger.other_rule_timings.iter().any(|t| t.rule == "omega" && t.success));
        assert!(ledger.other_rule_timings.iter().any(|t| t.rule == "omega" && !t.success));
        for t in &ledger.other_rule_timings {
            assert!(t.elapsed_ns > 0);
            assert!(matches!(t.rule, "candidate_discovery" | "hh" | "omega"));
        }
        drop(session);
        assert!(time_rule("hh", 0).is_none());
    }

    #[test]
    fn rule_timing_without_active_opt_in_does_not_emit_any_record() {
        let session = Session::start_with_rule_timing(true, false, false).unwrap();
        assert!(time_rule("omega", 5).is_none());
        let ledger = session.snapshot(1.0, 0.1);
        assert!(!ledger.other_rule_timing_enabled);
        assert!(ledger.other_rule_timings.is_empty());
        drop(session);
        assert!(Session::start_with_rule_timing(false, false, true).is_none());
        assert!(time_rule("candidate_discovery", 0).is_none());
    }

}
