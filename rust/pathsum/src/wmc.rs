// src/wmc.rs
use std::fs::File;
use std::io::Write;
use std::process::Command;
use std::collections::HashMap;
use std::f64::consts::PI;

use log::{info, debug, trace};
use num_complex::Complex;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};
use anyhow::{Result, Context, anyhow};

use crate::pathsum::PathSum;
use crate::pathsum::phase_poly::Monomial;

fn solver_arguments(tool_name: &str) -> Result<&'static [&'static str]> {
    Ok(crate::solver_adapter::adapter_for(tool_name)?.arguments())
}

// BigRational conversion handles ratios whose individual components exceed f64.
fn parse_real_count(value: &str) -> Result<f64> {
    let result = if value.contains('/') {
        value.parse::<BigRational>()
            .map_err(|e| anyhow!("Invalid rational count: {}", e))?
            .to_f64().ok_or_else(|| anyhow!("Count outside f64 range"))?
    } else {
        value.parse::<f64>().map_err(|e| anyhow!("Invalid decimal count: {}", e))?
    };
    if !result.is_finite() {
        return Err(anyhow!("Non-finite weighted count"));
    }
    Ok(result)
}

pub(crate) fn parse_count_line(line: &str) -> Result<Option<Complex<f64>>> {
    let prefixes = ["c s exact double prec-sci", "c s exact arb cpx",
        "c s exact half float", "c s exact single float",
        "c s exact double float", "c s exact quadruple float",
        "c s exact octuple float", "c s exact arb frac"];
    let Some(value) = prefixes.iter().find_map(|prefix| {
        line.strip_prefix(prefix).filter(|rest| rest.is_empty() || rest.starts_with(char::is_whitespace))
    }) else { return Ok(None); };
    let clean = value.chars().filter(|c| !c.is_whitespace()).collect::<String>().replace("+-", "-");
    let Some(value) = clean.strip_suffix('i') else {
        return Ok(Some(Complex::new(parse_real_count(&clean)?, 0.0)));
    };
    let split = value.char_indices().rev().find(|&(i, c)| {
        i > 0 && (c == '+' || c == '-') && !matches!(value.as_bytes()[i - 1], b'e' | b'E')
    }).map(|(i, _)| i);
    let (real, imaginary) = split.map(|i| (&value[..i], &value[i..])).unwrap_or(("0", value));
    let im = match imaginary {
        "" | "+" => 1.0,
        "-" => -1.0,
        _ => parse_real_count(imaginary)?,
    };
    Ok(Some(Complex::new(parse_real_count(real)?, im)))
}

pub struct WmcManager {
    clauses: Vec<Vec<i32>>,
    weights: HashMap<i32, Complex<f64>>, 
    var_map: HashMap<u32, i32>,
    next_var_id: i32,
}

impl WmcManager {
    pub fn new(_ps: &PathSum) -> Self {
        let manager = WmcManager {
            clauses: Vec::new(),
            weights: HashMap::new(),
            var_map: HashMap::new(),
            next_var_id: 1, 
        };
        manager
    }

    fn get_dimacs_var(&mut self, ps_var: u32) -> i32 {
        if let Some(&id) = self.var_map.get(&ps_var) {
            id
        } else {
            let id = self.next_var_id;
            self.next_var_id += 1;
            self.var_map.insert(ps_var, id);
            id
        }
    }

    fn encode_phase_polynomial(&mut self, ps: &PathSum) -> Result<()> {
        for (mono, coeff) in &ps.p.terms {
            let phase_val = (coeff.constant.numer as f64) / (coeff.constant.denom as f64);
            // Convert exact source radians only at the floating solver boundary.
            // These weights are observations, not mathematical certificates.
            let radian_component = match coeff.radians.as_ref() {
                Some(value) => {
                    let rad = value.to_f64().ok_or_else(|| anyhow!(
                        "Exact source radians cannot be represented at the WMC weight boundary"
                    ))?;
                    // A nonzero rational can round to binary64 zero (or be lost
                    // on the subsequent 2x phase conversion). Neither case is
                    // usable evidence for strict equivalence.
                    if !rad.is_finite() || (!value.is_zero() && 2.0 * rad == 0.0) {
                        return Err(anyhow!(
                            "Nonzero exact source radians underflow at the WMC weight boundary"
                        ));
                    }
                    rad
                }
                None => 0.0,
            };
            let angle = phase_val * 2.0 * PI + 2.0 * radian_component;
            if !angle.is_finite() {
                return Err(anyhow!("Non-finite angle at the WMC weight boundary"));
            }
            let weight = Complex::new(angle.cos(), angle.sin());

            let z_i = self.next_var_id;
            self.next_var_id += 1;
            
            self.weights.insert(z_i, weight);

            if mono.is_empty() {
                self.clauses.push(vec![z_i]);
            } else {
                let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();
                
                if dimacs_lits.len() == 1 {
                    // z_i <-> x
                    let x = dimacs_lits[0];
                    self.clauses.push(vec![-z_i, x]);
                    self.clauses.push(vec![-x, z_i]);
                } else {
                    // z_i <-> AND(x_1, x_2, ...)
                    let mut long_clause = vec![z_i];
                    for &lit in &dimacs_lits {
                        self.clauses.push(vec![-z_i, lit]); // z_i -> lit
                        long_clause.push(-lit);             // AND -> z_i
                    }
                    self.clauses.push(long_clause);
                }
            }
        }
        Ok(())
    }

    fn encode_anf(&mut self, anf: &[Monomial]) -> i32 {
        if anf.is_empty() {
            let f_var = self.next_var_id;
            self.next_var_id += 1;
            self.clauses.push(vec![-f_var]); 
            return f_var;
        }

        let mut mono_vars = Vec::new();
        for mono in anf {
            let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();
            if dimacs_lits.is_empty() {
                let t_var = self.next_var_id;
                self.next_var_id += 1;
                self.clauses.push(vec![t_var]); 
                mono_vars.push(t_var);
            } else if dimacs_lits.len() == 1 {
                mono_vars.push(dimacs_lits[0]);
            } else {
                let and_var = self.next_var_id;
                self.next_var_id += 1;
                let mut long_clause = vec![and_var];
                for &lit in &dimacs_lits {
                    self.clauses.push(vec![-and_var, lit]);
                    long_clause.push(-lit);
                }
                self.clauses.push(long_clause);
                mono_vars.push(and_var);
            }
        }

        if mono_vars.len() == 1 {
            return mono_vars[0];
        }

        // Xor : c <-> a Xor b
        let mut current_var = mono_vars[0];
        for i in 1..mono_vars.len() {
            let next_var = mono_vars[i];
            let c = self.next_var_id;
            self.next_var_id += 1;
            
            //  Xor Tseitin 
            self.clauses.push(vec![-current_var, -next_var, -c]); // Or(Not(a), Not(b), Not(c))
            self.clauses.push(vec![current_var, next_var, -c]);   // Or(a, b, Not(c))
            self.clauses.push(vec![current_var, -next_var, c]);   // Or(a, Not(b), c)
            self.clauses.push(vec![-current_var, next_var, c]);   // Or(Not(a), b, c)
            
            current_var = c;
        }
        current_var
    }

    pub fn encode_trace(&mut self, ps: &PathSum) -> Result<()> {
        self.encode_trace_experimental(ps, 2)
    }

    // 0=unmodified lazy mapping; 1=eager reservation; 2=lazy finalization.
    // Experiment branch only; final mode avoids changing active variable IDs.
    fn encode_trace_experimental(&mut self, ps: &PathSum, reserve_mode: u8) -> Result<()> {
        if reserve_mode == 1 {
            let mut path_vars: Vec<u32> = ps.v.path_vars.iter().copied().collect();
            path_vars.sort_unstable();
            for path_var in path_vars { self.get_dimacs_var(path_var); }
        }
        self.encode_phase_polynomial(ps)?;

        for i in 0..ps.v.num_qubits {
            let a = self.get_dimacs_var(i as u32);
            
            let anf_vec: Vec<Monomial> = ps.f.functions[i].iter().cloned().collect();
            let b = self.encode_anf(&anf_vec); 
            
            self.clauses.push(vec![-a, b]); // a -> b
            self.clauses.push(vec![a, -b]); // b -> a
        }
        if reserve_mode == 2 && self.var_map.len() < ps.v.path_vars.len() {
            // Only genuinely orphaned path variables are added. The normal
            // path keeps its previous numbering and allocation behavior.
            let mut unused: Vec<u32> = ps.v.path_vars.iter()
                .filter(|v| !self.var_map.contains_key(v))
                .copied().collect();
            unused.sort_unstable();
            for path_var in unused { self.get_dimacs_var(path_var); }
        }
        Ok(())
    }

    pub fn to_dimacs_string(&self, tool_name: &str) -> String {
        self.try_to_dimacs_string(tool_name).expect("Unsupported WMC solver")
    }
    pub fn try_to_dimacs_string(&self, tool_name: &str) -> Result<String> {
        Ok(self.to_dimacs_with_adapter(crate::solver_adapter::adapter_for(tool_name)?))
    }
    pub(crate) fn to_dimacs_with_adapter(
        &self, adapter: &dyn crate::solver_adapter::SolverAdapter
    ) -> String {
        crate::wmc_problem::WmcProblem::new(
            self.next_var_id - 1, &self.clauses, &self.weights
        ).serialize(adapter)
    }
    /// Backward-compatible entrypoint for callers that do not own a deadline.
    /// The public verification path uses solve_with_deadline instead.
    pub fn solve(&self, tool_name: &str) -> Result<Complex<f64>> {
        self.solve_with_deadline(
            tool_name,
            std::time::Instant::now().checked_add(std::time::Duration::from_secs(600)),
        )
    }

    pub fn solve_with_deadline(
        &self,
        tool_name: &str,
        deadline: Option<std::time::Instant>,
    ) -> Result<Complex<f64>> {
        let adapter = crate::solver_adapter::adapter_for(tool_name)?;
        self.solve_with_adapter(adapter, deadline)
    }
    /// Opt-in typed native measurement; ordinary solve APIs remain compatible.
    pub fn observe_with_deadline(
        &self,
        tool_name: &str,
        deadline: Option<std::time::Instant>,
    ) -> Result<crate::solver_result::SolverObservation> {
        let selected = crate::solver_adapter::adapter_for(tool_name)?;
        let started = std::time::Instant::now();
        let count = self.solve_with_adapter(selected, deadline)?;
        Ok(crate::solver_result::SolverObservation {
            solver_id: selected.id().to_string(),
            arguments: selected.arguments().iter().map(|arg| (*arg).to_string()).collect(),
            count,
            exit_code: 0,
            elapsed_seconds: started.elapsed().as_secs_f64(),
            exact_count_certificate: false,
        })
    }
    /// Preserve the solver's original decimal result through a typed boundary.
    /// The returned precision interval covers printed digits only.
    pub fn solve_with_deadline_printed(
        &self,
        tool_name: &str,
        deadline: Option<std::time::Instant>,
    ) -> Result<crate::precision_count::PrintedCount> {
        let selected = crate::solver_adapter::adapter_for(tool_name)?;
        self.solve_with_adapter_printed(selected, deadline)
    }

    /// Typed result for the public distance-mode verifier, preserving the
    /// selected solver (GPMC -prec=90, native Ganak mode 6).
    pub fn solve_with_deadline_distance_printed(
        &self, tool_name: &str, deadline: Option<std::time::Instant>,
    ) -> Result<crate::precision_count::PrintedCount> {
        self.solve_with_adapter_printed(
            crate::solver_adapter::distance_adapter_for(tool_name)?, deadline,
        )
    }

    /// Number of phase-weight literals used in a conditional f64 input budget.
    pub fn numerical_weight_count(&self) -> usize { self.weights.len() }

    pub(crate) fn solve_with_adapter_printed(
        &self,
        adapter: &dyn crate::solver_adapter::SolverAdapter,
        deadline: Option<std::time::Instant>,
    ) -> Result<crate::precision_count::PrintedCount> {
        self.run_solver_with_parser(adapter, deadline, crate::precision_count::parse_stdout_optional)
    }

    pub(crate) fn solve_with_adapter(
        &self,
        adapter: &dyn crate::solver_adapter::SolverAdapter,
        deadline: Option<std::time::Instant>,
    ) -> Result<Complex<f64>> {
        self.run_solver_with_parser(adapter, deadline, |stdout| adapter.parse_count(stdout))
    }

    fn run_solver_with_parser<T, F>(
        &self,
        adapter: &dyn crate::solver_adapter::SolverAdapter,
        deadline: Option<std::time::Instant>,
        parser: F,
    ) -> Result<T>
    where
        F: Fn(&str) -> Result<Option<T>>,
    {
        let tool_name = adapter.id();
        use std::fs::OpenOptions;
        use std::sync::atomic::{AtomicU64, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};

        struct TempCnf {
            path: std::path::PathBuf,
            preserve: bool,
        }
        impl Drop for TempCnf {
            fn drop(&mut self) {
                if !self.preserve {
                    let _ = std::fs::remove_file(&self.path);
                }
            }
        }

        static NEXT_CNF_ID: AtomicU64 = AtomicU64::new(0);
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let pid = std::process::id();
        let nonce = NEXT_CNF_ID.fetch_add(1, Ordering::Relaxed);
        let temp_cnf_path = std::env::temp_dir()
            .join(format!("temp_eqcheck_{}_{}_{}.cnf", pid, timestamp, nonce));
        let cnf_content = self.to_dimacs_with_adapter(adapter);
        trace!(target: "wmc", "Generated CNF for {}:\n{}", tool_name, cnf_content);

        let _timed_write = crate::diagnostics::span("cnf_file_write");
        let mut cnf_options = OpenOptions::new();
        cnf_options.write(true).create_new(true);
        #[cfg(unix)]
        {
            // A CNF can encode a user's circuit. Restrict temporary files to
            // the current user regardless of the host process umask.
            use std::os::unix::fs::OpenOptionsExt;
            cnf_options.mode(0o600);
        }
        let mut file = cnf_options.open(&temp_cnf_path)?;
        let mut artifact = TempCnf { path: temp_cnf_path.clone(), preserve: false };
        file.write_all(cnf_content.as_bytes())?;
        drop(file);
        drop(_timed_write);

        let result = (|| -> Result<T> {
            let exe_path = adapter.executable_path();
            adapter.preflight(&exe_path, deadline)?;
            let args: Vec<String> = adapter.arguments()
                .iter().map(|value| value.to_string()).collect();
            debug!(target: "wmc", "Spawning {} solver: {} {:?} {}",
                tool_name, exe_path, args, temp_cnf_path.display());
            let mut command = Command::new(&exe_path);
            command.args(&args).arg(&temp_cnf_path);
            let output = crate::solver_process::run(&mut command, deadline)
                .with_context(|| format!("{} solver executable {}", tool_name, exe_path))?;

            let stdout_str = String::from_utf8_lossy(&output.stdout);
            let stderr_str = String::from_utf8_lossy(&output.stderr);
            if !output.status.success() {
                return Err(anyhow!(crate::solver_result::SolverFailure::new(
                    crate::solver_result::SolverFailureKind::NonzeroExit,
                    tool_name,
                    format!(
                        "{} failed: status={}, command={} {:?}, stdout={}, stderr={}",
                        tool_name, output.status, exe_path, args, stdout_str, stderr_str
                    ),
                )));
            }
            trace!(target: "wmc", "{} raw stdout:\n{}", tool_name, stdout_str);
            if !stderr_str.is_empty() {
                trace!(target: "wmc", "{} raw stderr:\n{}", tool_name, stderr_str);
            }

            let result_val = parser(&stdout_str).map_err(|error| {
                anyhow!(crate::solver_result::SolverFailure::new(
                    crate::solver_result::SolverFailureKind::MalformedCount,
                    tool_name,
                    error.to_string(),
                ))
            })?;
            if result_val.is_some() {
                info!(target: "wmc", "{} result parsed", tool_name);
            }
            result_val.ok_or_else(|| anyhow!(crate::solver_result::SolverFailure::new(
                crate::solver_result::SolverFailureKind::MissingCount,
                tool_name,
                format!(
                    "{} Error!\nCNF Path: {}\n--- STDOUT ---\n{}\n--- STDERR ---\n{}",
                    tool_name, temp_cnf_path.display(), stdout_str, stderr_str
                ),
            )))
        })();

        // Sensitive circuit data is removed on all paths by default. Preserve
        // only on an explicit opt-in failure, never for successful solves.
        if result.is_err() && std::env::var("QUPRS_KEEP_FAILED_CNF").as_deref() == Ok("1") {
            artifact.preserve = true;
            log::warn!(target: "wmc", "Retained failed solver CNF by explicit opt-in: {}",
                artifact.path.display());
        }
        result
    }

}
#[cfg(test)]
mod count_parser_tests {
    use super::{parse_real_count, solver_arguments, WmcManager, Complex};
    use crate::pathsum::PathSum;
    static GPMC_OVERRIDE_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    #[test]
    fn solvers_use_independent_floating_modes() {
        assert_eq!(solver_arguments("ganak").unwrap(), &["--mode=6"]);
        assert_eq!(solver_arguments("gpmc").unwrap(), &["-mode=1"]);
        assert!(solver_arguments("unsupported").is_err());
    }

    #[test]
    fn mode6_complex_scientific_output() {
        use super::*;
        for (value, expected) in [
            ("9.28154511e-01 + 2.42960040e+10i", Complex::new(0.928154511, 2.42960040e10)),
            ("-1.25E+03 - 2.5E-11i", Complex::new(-1250.0, -2.5e-11)),
            ("1e-12 + -2e+03i", Complex::new(1e-12, -2000.0)),
            ("+i", Complex::new(0.0, 1.0)),
            ("-i", Complex::new(0.0, -1.0)),
            ("1\t+\t2i", Complex::new(1.0, 2.0)),
        ] {
            assert_eq!(parse_count_line(&format!("c s exact quadruple float {value}")).unwrap(), Some(expected));
        }
        // Ganak mode 6 prefixes depend on MPFR bits; this only fixes the
        // transport grammar. The value is still converted to f64.
        for label in ["half", "single", "double", "quadruple", "octuple"] {
            let line = format!("c s exact {label} float 1.00000000e+00 - 2.50000000e-21i");
            assert_eq!(parse_count_line(&line).unwrap(), Some(Complex::new(1.0, -2.5e-21)));
        }
        assert!(parse_count_line("c s exact quadruple floating 1").unwrap().is_none());
        assert!(parse_count_line("c s exact octuple floating 1").unwrap().is_none());
        for value in ["nan", "inf", "1e999", "1 + infi", "1e-2-3e+i"] {
            assert!(parse_count_line(&format!("c s exact quadruple float {value}")).is_err());
        }
    }


    #[test]
    fn parses_exact_fraction_and_scientific_notation() {
        assert_eq!(parse_real_count("-3/2").unwrap(), -1.5);
        assert_eq!(parse_real_count("1.25e-10").unwrap(), 1.25e-10);
    }

    #[test]
    fn parses_fraction_with_components_larger_than_f64() {
        let value = format!("1{}", "0".repeat(5000));
        assert_eq!(parse_real_count(&format!("{}/{}", value, value)).unwrap(), 1.0);
    }

    #[test]
    fn rejects_invalid_counts_instead_of_returning_zero() {
        assert!(parse_real_count("malformed").is_err());
        assert!(parse_real_count("1/0").is_err());
        assert!(parse_real_count("inf").is_err());
    }
    #[test]
    fn ganak_exact_complex_counts_match_hand_computed_models() {
        use super::*;
        for (re, im) in [(1.5, 0.25), (-1.5, -0.25), (0.0, 1.0), (0.0, 0.0), (1e-5, -2.5e-6)] {
            let mut manager = WmcManager::new(&PathSum::new(0));
            manager.next_var_id = 2;
            manager.clauses.push(vec![1]);
            manager.weights.insert(1, Complex::new(re, im));
            assert_eq!(manager.solve("ganak").unwrap(), Complex::new(re, im));
        }
        let mut manager = WmcManager::new(&PathSum::new(0));
        manager.next_var_id = 2;
        manager.weights.insert(1, Complex::new(-1.0, 0.0));
        assert_eq!(manager.solve("ganak").unwrap(), Complex::new(0.0, 0.0));
    }

    #[test]
    fn concurrent_ganak_fixtures_keep_their_own_weights() {
        use super::*;
        use std::sync::{Arc, Barrier};

        // Reproduce the parallel cargo-test pattern that can otherwise
        // attribute the answer for a different CNF to this fixture. Include
        // both forced and free variables, which have different exact counts.
        let fixtures = [
            (Complex::new(1.5, 0.25), true),
            (Complex::new(-1.5, -0.25), true),
            (Complex::new(0.0, 1.0), true),
            (Complex::new(0.5, -0.125), true),
            (Complex::new(0.25, 0.75), false),
            (Complex::new(-0.5, 0.5), false),
            (Complex::new(0.0, -1.0), false),
            (Complex::new(1.25, -0.25), false),
        ];
        let barrier = Arc::new(Barrier::new(fixtures.len()));
        std::thread::scope(|scope| {
            let handles: Vec<_> = fixtures.into_iter().map(|(weight, forced)| {
                let barrier = barrier.clone();
                scope.spawn(move || {
                    let mut manager = WmcManager::new(&PathSum::new(0));
                    manager.next_var_id = 2;
                    if forced {
                        manager.clauses.push(vec![1]);
                    }
                    manager.weights.insert(1, weight);
                    barrier.wait();
                    let actual = manager.solve("ganak").unwrap();
                    let expected = if forced { weight } else { weight + Complex::new(1.0, 0.0) };
                    let error = (actual - expected).norm();
                    assert!(
                        error <= 1e-8 * expected.norm() + 1e-10,
                        "Cross-fixture solver result: forced={forced}, weight={weight:?}, expected={expected:?}, actual={actual:?}, error={error:e}"
                    );
                })
            }).collect();
            for handle in handles {
                handle.join().unwrap();
            }
        });
    }

    #[test]
    fn solver_inputs_preserve_f64_roundtrip_precision() {
        use super::*;
        let re = -1.0 + 1e-12;
        let im = -2.5e-11;
        let mut manager = WmcManager::new(&PathSum::new(0));
        manager.next_var_id = 2;
        manager.weights.insert(1, Complex::new(re, im));
        for solver in ["ganak", "gpmc"] {
            let text = manager.to_dimacs_string(solver);
            let line = text.lines().find(|l| l.starts_with("c p weight 1 ")).unwrap();
            let fields: Vec<_> = line.split_whitespace().collect();
            assert_eq!(fields[4].parse::<f64>().unwrap().to_bits(), re.to_bits(), "{solver}: {line}");
            if solver == "gpmc" {
                assert_eq!(fields[5].parse::<f64>().unwrap().to_bits(), im.to_bits(), "{line}");
            } else {
                assert_eq!(fields[6].trim_end_matches('i').parse::<f64>().unwrap().to_bits(), im.abs().to_bits(), "{line}");
                assert_eq!(fields[5], "-");
            }
        }
    }

    #[test]
    fn floating_solvers_match_complex_and_cancellation_fixtures() {
        use super::*;
        // Preserve failure isolation: a preceding assertion may poison this
        // lock, but does not change the solver override in that fixture.
        let _guard = GPMC_OVERRIDE_LOCK.lock().unwrap_or_else(|err| err.into_inner());
        for positive in [
            Complex::new(1.23456789123, -2.34567891234),
            Complex::new(1e-12, -2.5e-11),
            Complex::new(-1.0, 0.0),
            Complex::new(-1.0 + 1e-8, 0.0),
        ] {
            let expected = positive + Complex::new(1.0, 0.0);
            let mut manager = WmcManager::new(&PathSum::new(0));
            manager.next_var_id = 2;
            manager.weights.insert(1, positive);
            let ganak = manager.solve("ganak").unwrap();
            let gpmc = manager.solve("gpmc").unwrap();
            // Keep solver-specific diagnostics: a failing numerical fixture
            // must identify which executable/weight/count breached the budget.
            let tolerance = 1e-8 * expected.norm() + 2e-9;
            for (solver, value) in [("ganak", ganak), ("gpmc", gpmc)] {
                let error = (value - expected).norm();
                assert!(
                    error <= tolerance,
                    "solver={solver}, input={positive:?}, expected={expected:?}, actual={value:?}, error={error:e}, tolerance={tolerance:e}, cnf={} ",
                    manager.to_dimacs_string(solver),
                );
            }
            let cross_error = (ganak - gpmc).norm();
            assert!(
                cross_error <= tolerance,
                "ganak={ganak:?}, gpmc={gpmc:?}, input={positive:?}, cross_error={cross_error:e}, tolerance={tolerance:e}",
            );
        }
    }

    #[test]
    #[cfg(unix)]
    fn timed_out_gpmc_solver_is_not_a_weighted_count() {
        use super::*;
        use std::os::unix::fs::PermissionsExt;
        use std::time::{Duration, Instant};

        let _guard = GPMC_OVERRIDE_LOCK.lock().unwrap_or_else(|err| err.into_inner());
        let path = std::env::temp_dir().join(format!(
            "quprs-timeout-gpmc-{}",
            std::process::id(),
        ));
        std::fs::write(&path, "#!/bin/sh\nsleep 30\n").unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
        let previous = std::env::var_os("QUPRS_GPMC_PATH");
        std::env::set_var("QUPRS_GPMC_PATH", &path);

        let started = Instant::now();
        let result = WmcManager::new(&PathSum::new(0)).solve_with_deadline(
            "gpmc",
            Some(started + Duration::from_millis(250)),
        );
        match previous {
            Some(old) => std::env::set_var("QUPRS_GPMC_PATH", old),
            None => std::env::remove_var("QUPRS_GPMC_PATH"),
        }
        std::fs::remove_file(&path).unwrap();

        let error = result.expect_err("hanging solver must not yield a count");
        assert!(error.downcast_ref::<crate::solver_process::SolverTimeout>().is_some(),
            "{error:#}");
        assert!(started.elapsed() < Duration::from_secs(4));
    }

    #[test]
    #[cfg(unix)]
    fn nonzero_solver_exit_cannot_become_a_weighted_count() {
        use super::*;
        use std::os::unix::fs::PermissionsExt;
        let path = std::env::temp_dir().join(format!("quprs-failed-gpmc-{}", std::process::id()));
        // Preserve failure isolation: a preceding assertion may poison this
        // lock, but does not change the solver override in that fixture.
        let _guard = GPMC_OVERRIDE_LOCK.lock().unwrap_or_else(|err| err.into_inner());
        let previous = std::env::var_os("QUPRS_GPMC_PATH");
        for (body, message) in [
            ("echo 'c s exact quadruple float 999'; exit 7", "status="),
            ("echo 'c s exact quadruple float 999'; kill -TERM $$", "status="),
            ("echo 'no count'", "Error!"),
            ("echo 'c s exact quadruple float nan'", "Non-finite"),
            ("echo 'c s exact quadruple float malformed'", "Invalid decimal"),
        ] {
            std::fs::write(&path, format!("#!/bin/sh\n{body}\n")).unwrap();
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
            std::env::set_var("QUPRS_GPMC_PATH", &path);
            let result = WmcManager::new(&PathSum::new(0)).solve("gpmc");
            match &previous {
                Some(value) => std::env::set_var("QUPRS_GPMC_PATH", value),
                None => std::env::remove_var("QUPRS_GPMC_PATH"),
            }
            assert!(result.unwrap_err().to_string().contains(message));
        }
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn typed_invalid_solver_does_not_dispatch() {
        use crate::solver_result::{SolverFailure, SolverFailureKind};
        let manager = WmcManager::new(&PathSum::new(0));
        let err=manager.observe_with_deadline("missing_solver", None).unwrap_err();
        let typed=err.downcast_ref::<SolverFailure>().unwrap();
        assert_eq!(typed.kind, SolverFailureKind::Unsupported);
        assert_eq!(typed.solver_id, "missing_solver");
    }

    #[test]
    #[cfg(unix)]
    fn typed_numeric_observation_and_negative_failures() {
        use crate::solver_adapter::{SolverAdapter, SolverCapabilities, WeightGrammar};
        use crate::solver_result::{SolverFailure, SolverFailureKind};
        struct Mock(&'static str);
        impl SolverAdapter for Mock {
            fn id(&self) -> &'static str { "mock" }
            fn arguments(&self) -> &'static [&'static str] {
                match self.0 {
                    "ok" => &["-c", "printf 'c s exact quadruple float 1.5 - 0.25i\\n'"],
                    "nonzero" => &["-c", "echo 'c s exact quadruple float 9'; exit 7"],
                    "missing" => &["-c", "echo 'no weighted count'"],
                    "conflict" => &["-c", "printf 'c s exact quadruple float 1.5 - 0.25i\\nc s exact quadruple float 7.5 - 0.25i\\n'"],
                    _ => &["-c", "echo 'c s exact quadruple float nan'"],
                }
            }
            fn capabilities(&self) -> SolverCapabilities {
                SolverCapabilities { complex_weights:true,exact_count_certificate:false,grammar:WeightGrammar::Pair }
            }
            fn executable_path(&self) -> String { "sh".into() }
            fn weight_lines(&self, var:i32, weight:Complex<f64>)->(String,String) {
                crate::solver_adapter::GpmcAdapter.weight_lines(var,weight)
            }
        }
        let manager=WmcManager::new(&PathSum::new(0));
        let deadline=|| Some(std::time::Instant::now()+std::time::Duration::from_secs(10));
        let selected=Mock("ok");
        let result=manager.solve_with_adapter(&selected,deadline()).unwrap();
        assert_eq!(result,Complex::new(1.5,-0.25));
        for (case,kind) in [
            ("nonzero",SolverFailureKind::NonzeroExit),
            ("missing",SolverFailureKind::MissingCount),
            ("malformed",SolverFailureKind::MalformedCount),
            ("conflict",SolverFailureKind::MalformedCount)
        ] {
            let err=manager.solve_with_adapter(&Mock(case),deadline()).unwrap_err();
            let typed=err.downcast_ref::<SolverFailure>().expect("category must be typed");
            assert_eq!(typed.kind,kind,"case={case}");
            assert_eq!(typed.solver_id,"mock");
        }
    }

}

#[cfg(test)]
mod experiment_free_var_contract {
    use super::{PathSum, WmcManager};
    #[test]
    fn orphan_path_var_is_preserved_as_a_free_cnf_variable() {
        let mut ps = PathSum::new(1);
        let _unused_y = ps.v.get_fresh_var();
        assert_eq!(ps.v.path_vars.len(), 2);
        let mut legacy = WmcManager::new(&ps);
        legacy.encode_trace_experimental(&ps, 0).unwrap();
        assert_eq!(legacy.next_var_id - 1, 1);
        let mut eager = WmcManager::new(&ps);
        eager.encode_trace_experimental(&ps, 1).unwrap();
        assert_eq!(eager.next_var_id - 1, 2);
        let mut wmc = WmcManager::new(&ps);
        wmc.encode_trace(&ps).unwrap();
        let text = wmc.to_dimacs_string("gpmc");
        assert!(text.starts_with("p cnf 2 2\nc t wmc\n"), "{}", text);
        let n = (wmc.next_var_id - 1) as usize;
        assert_eq!(n, 2);
        let mut satisfying = 0_usize;
        for bits in 0..(1_usize << n) {
            let ok = wmc.clauses.iter().all(|clause| clause.iter().any(|lit| {
                let bit = (bits & (1_usize << (lit.unsigned_abs() as usize - 1))) != 0;
                bit == (*lit > 0)
            }));
            if ok { satisfying += 1; }
        }
        assert_eq!(satisfying, 4, "input x and unused path y must both be free");
    }

    #[test]
    fn compare_single_runner_encoding_cost_only() {
        use std::time::Instant;
        let mut ps = PathSum::new(16);
        for _ in 0..8 { ps.v.get_fresh_var(); }
        let reps = 2400;
        for mode in [0_u8, 1, 2] {
            let mut samples = Vec::new();
            for _ in 0..5 {
                let start = Instant::now();
                for _ in 0..reps {
                    let mut manager = WmcManager::new(&ps);
                    manager.encode_trace_experimental(&ps, mode).unwrap();
                    let expected = if mode == 0 { 16 } else { 24 };
                    assert_eq!(manager.next_var_id - 1, expected);
                }
                samples.push(start.elapsed().as_nanos() / reps);
            }
            samples.sort();
            eprintln!(
                "EXPERIMENT_SOURCE_ENCODING mode={} median_ns={} nvars={} nclauses=32",
                mode, samples[2], if mode == 0 { 16 } else { 24 }
            );
        }
        // Normal PathSum: reservation should not incur the pathological
        // orphan-allocation cost on every CNF conversion.
        let normal = PathSum::new(16);
        for mode in [0_u8, 2] {
            let start = Instant::now();
            for _ in 0..reps {
                let mut manager = WmcManager::new(&normal);
                manager.encode_trace_experimental(&normal, mode).unwrap();
            }
            eprintln!("EXPERIMENT_NORMAL_ENCODING mode={} mean_ns={}",
                mode, start.elapsed().as_nanos() / reps);
        }
    }
}
