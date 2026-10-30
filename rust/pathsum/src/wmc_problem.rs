//! Borrowed solver-neutral CNF problem view.
//!
//! Deliberately retains the source numeric representation and does not claim
//! that floating-point solver output is a mathematical certificate.
use std::collections::HashMap;
use num_complex::Complex;
use anyhow::{anyhow, Result};
use crate::solver_adapter::SolverAdapter;

pub(crate) struct WmcProblem<'a> {
    pub variables: i32,
    pub clauses: &'a [Vec<i32>],
    pub weights: &'a HashMap<i32, Complex<f64>>,
}

impl<'a> WmcProblem<'a> {
    pub(crate) fn new(
        variables: i32,
        clauses: &'a [Vec<i32>],
        weights: &'a HashMap<i32, Complex<f64>>,
    ) -> Self {
        Self { variables, clauses, weights }
    }

    pub(crate) fn validate(&self) -> Result<()> {
        if self.variables < 0 {
            return Err(anyhow!("Invalid negative CNF variable count"));
        }
        for clause in self.clauses {
            if clause.iter().any(|lit| *lit == 0 || lit.unsigned_abs() > self.variables as u32) {
                return Err(anyhow!("Invalid CNF clause literal"));
            }
        }
        for (var, weight) in self.weights {
            if *var <= 0 || *var > self.variables {
                return Err(anyhow!("Invalid weighted CNF variable"));
            }
            if !weight.re.is_finite() || !weight.im.is_finite() {
                return Err(anyhow!("Non-finite weighted CNF component"));
            }
        }
        Ok(())
    }

    /// Render exactly the historical solver-specific DIMACS bytes.
    /// Adapter dispatch, numerical tolerances and solver process behavior
    /// remain owned by their existing components.
    pub(crate) fn serialize(&self, adapter: &dyn SolverAdapter) -> String {
        let _timed_serialize = crate::diagnostics::span("cnf_serialize");
        let mut out = String::new();
        out.push_str(&format!("p cnf {} {}\nc t wmc\n", self.variables, self.clauses.len()));
        // Canonical order for reproducible CNF input and paired profiling.
        // This does not change the Boolean constraints or weighted models.
        let mut sorted_weights: Vec<_> = self.weights.iter().collect();
        sorted_weights.sort_unstable_by_key(|(var, _)| **var);
        for (var, weight) in sorted_weights {
            let (positive, negative) = adapter.weight_lines(*var, *weight);
            out.push_str(&positive);
            out.push_str(&negative);
        }
        for clause in self.clauses {
            let values: Vec<String> = clause.iter().map(|lit| lit.to_string()).collect();
            out.push_str(&format!("{} 0\n", values.join(" ")));
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::solver_adapter::adapter_for;
    #[test]
    fn neutral_problem_renders_independent_solver_dialects() {
        let mut weights=HashMap::new();
        weights.insert(2, Complex::new(1.5, -0.25));
        let clauses=vec![vec![1, -2],vec![2]];
        let problem=WmcProblem::new(2, &clauses, &weights);
        problem.validate().unwrap();
        let gpmc=problem.serialize(adapter_for("gpmc").unwrap());
        let ganak=problem.serialize(adapter_for("ganak").unwrap());
        assert!(gpmc.starts_with("p cnf 2 2\nc t wmc\n"));
        assert!(ganak.starts_with("p cnf 2 2\nc t wmc\n"));
        assert!(gpmc.contains("c p weight 2 1.5000000000000000e0 -2.5000000000000000e-1 0\n"));
        assert!(ganak.contains("c p weight 2 1.5000000000000000e0 - 2.5000000000000000e-1i 0\n"));
        assert!(gpmc.ends_with("1 -2 0\n2 0\n"));
        assert!(ganak.ends_with("1 -2 0\n2 0\n"));
    }
    #[test]
    fn canonical_weight_lines_are_independent_of_insertion_order() {
        let mut one = HashMap::new();
        one.insert(3, Complex::new(0.75, 0.125));
        one.insert(1, Complex::new(-0.5, 0.25));
        let mut two = HashMap::new();
        two.insert(1, Complex::new(-0.5, 0.25));
        two.insert(3, Complex::new(0.75, 0.125));
        let clauses = vec![vec![1, -3], vec![3]];
        for solver in ["gpmc", "ganak"] {
            let adapter = adapter_for(solver).unwrap();
            let lhs = WmcProblem::new(3, &clauses, &one).serialize(adapter);
            let rhs = WmcProblem::new(3, &clauses, &two).serialize(adapter);
            assert_eq!(lhs, rhs);
            let positive_ids: Vec<_> = lhs.lines()
                .filter(|line| line.starts_with("c p weight ") && !line.starts_with("c p weight -"))
                .map(|line| line.split_whitespace().nth(3).unwrap().parse::<i32>().unwrap())
                .collect();
            assert_eq!(positive_ids, vec![1, 3]);
        }
    }

    #[test]
    fn invalid_literal_weight_and_nonfinite_fail_closed() {
        let mut weights=HashMap::new();
        weights.insert(2, Complex::new(1.0, f64::NAN));
        let clauses=vec![vec![3]];
        assert!(WmcProblem::new(2, &clauses, &weights).validate().is_err());
        weights.insert(2, Complex::new(1.0, 0.0));
        assert!(WmcProblem::new(2, &clauses, &weights).validate().is_err());
        let good=vec![vec![1]];
        assert!(WmcProblem::new(2, &good, &weights).validate().is_ok());
    }
}
