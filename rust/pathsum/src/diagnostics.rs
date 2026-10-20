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
        Self::start(enabled)
    }

    fn start(enabled: bool) -> Option<Self> {
        if !enabled {
            return None;
        }
        let previous = RECORDER.with(|cell| cell.replace(Some(Recorder::default())));
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

#[derive(Debug, Clone)]
pub struct ExclusiveLedger {
    pub schema: &'static str,
    pub total_native_wall_seconds: f64,
    pub seconds: BTreeMap<&'static str, f64>,
    pub calls: BTreeMap<&'static str, u64>,
    pub solver_child_spawns: u64,
    pub reduction_max_depth: u32,
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
}
