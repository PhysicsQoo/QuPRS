// src/stats.rs

use std::fmt;

/// Statistics for a single reduction rule
#[derive(Debug, Clone, Copy, Default)]
pub struct RuleStats {
    pub attempts: usize,
    pub successes: usize,
}

impl RuleStats {
    pub fn reset(&mut self) {
        self.attempts = 0;
        self.successes = 0;
    }
}

/// Manages statistics and state for all reduction rules
#[derive(Debug, Clone)]
pub struct StatisticsManager {
    pub hh: RuleStats,
    pub omega: RuleStats,
    pub elim: RuleStats,
    reduction_enabled: bool,
}

impl StatisticsManager {
    /// Create a new StatisticsManager
    pub fn new() -> Self {
        Self {
            hh: RuleStats::default(),
            omega: RuleStats::default(),
            elim: RuleStats::default(),
            reduction_enabled: true,
        }
    }

    /// Reset all counters
    pub fn reset(&mut self) {
        self.hh.reset();
        self.omega.reset();
        self.elim.reset();
    }

    /// Set the global reduction switch
    pub fn set_enabled(&mut self, enabled: bool) {
        self.reduction_enabled = enabled;
    }

    /// Check if reduction is enabled
    pub fn is_enabled(&self) -> bool {
        self.reduction_enabled
    }

    /// Record an attempt for a rule
    pub fn record_attempt(&mut self, rule: RuleType) {
        match rule {
            RuleType::HH => self.hh.attempts += 1,
            RuleType::Omega => self.omega.attempts += 1,
            RuleType::Elim => self.elim.attempts += 1,
        }
    }

    /// Record a successful reduction
    pub fn record_success(&mut self, rule: RuleType) {
        match rule {
            RuleType::HH => self.hh.successes += 1,
            RuleType::Omega => self.omega.successes += 1,
            RuleType::Elim => self.elim.successes += 1,
        }
    }

    /// Get overall hit rate as a percentage
    pub fn get_hit_rate(&self) -> f64 {
        let total_attempts = self.hh.attempts + self.omega.attempts + self.elim.attempts;
        let total_successes = self.hh.successes + self.omega.successes + self.elim.successes;

        if total_attempts == 0 {
            0.0
        } else {
            (total_successes as f64 / total_attempts as f64) * 100.0
        }
    }
}

impl Default for StatisticsManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Enum to identify reduction rule types
#[derive(Debug, Clone, Copy)]
pub enum RuleType {
    HH,
    Omega,
    Elim,
}

impl fmt::Display for StatisticsManager {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "StatisticsManager(enabled={}, hit_rate={:.2}%)",
            self.reduction_enabled,
            self.get_hit_rate()
        )
    }
}
