// src/wmc.rs
use std::fs::File;
use std::io::Write;
use std::process::Command;
use std::collections::HashMap;
use std::f64::consts::PI;

use log::{info, debug, trace};
use num_complex::Complex;
use num_rational::BigRational;
use num_traits::ToPrimitive;
use anyhow::{Result, Context, anyhow};

use crate::pathsum::PathSum;
use crate::pathsum::phase_poly::Monomial;

fn solver_arguments(tool_name: &str) -> Result<&'static [&'static str]> {
    match tool_name {
        "gpmc" => Ok(&["-mode=1"]),
        "ganak" => Ok(&["--mode=6"]),
        _ => Err(anyhow!("Unsupported tool name: {}", tool_name)),
    }
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

fn parse_count_line(line: &str) -> Result<Option<Complex<f64>>> {
    let prefixes = ["c s exact double prec-sci", "c s exact arb cpx",
        "c s exact quadruple float", "c s exact arb frac"];
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

    fn encode_phase_polynomial(&mut self, ps: &PathSum) {
        for (mono, coeff) in &ps.p.terms {
            let phase_val = (coeff.constant.numer as f64) / (coeff.constant.denom as f64);
            let angle = phase_val * 2.0 * PI;
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

    pub fn encode_trace(&mut self, ps: &PathSum) {
        self.encode_phase_polynomial(ps);

        for i in 0..ps.v.num_qubits {
            let a = self.get_dimacs_var(i as u32);
            
            let anf_vec: Vec<Monomial> = ps.f.functions[i].iter().cloned().collect();
            let b = self.encode_anf(&anf_vec); 
            
            self.clauses.push(vec![-a, b]); // a -> b
            self.clauses.push(vec![a, -b]); // b -> a
        }
    }

    pub fn to_dimacs_string(&self, tool_name: &str) -> String {
        let _timed_serialize = crate::diagnostics::span("cnf_serialize");
        let mut out = String::new();
        let num_vars = self.next_var_id - 1;
        let num_clauses = self.clauses.len();

        out.push_str(&format!("p cnf {} {}\nc t wmc\n", num_vars, num_clauses));
        
        for (var, weight) in &self.weights {
            // Round-trip every finite f64 component rather than quantizing to
            // a fixed number of decimal places before MPFR-based counting.
            // 16 digits after the leading digit = 17 significant digits.
            if tool_name == "gpmc" {
                out.push_str(&format!("c p weight {} {:.16e} {:.16e} 0\n", var, weight.re, weight.im));
                out.push_str(&format!("c p weight -{} 1.0 0.0 0\n", var));
            } else {
                let op = if weight.im >= 0.0 { "+" } else { "-" };
                out.push_str(&format!("c p weight {} {:.16e} {} {:.16e}i 0\n", var, weight.re, op, weight.im.abs()));
                out.push_str(&format!("c p weight -{} 1.0 + 0.0i 0\n", var));
            }
        }

        for clause in &self.clauses {
            let clause_str: Vec<String> = clause.iter().map(|lit| lit.to_string()).collect();
            out.push_str(&format!("{} 0\n", clause_str.join(" ")));
        }
        out
    }
    fn find_gpmc_path() -> String {
        if let Ok(path) = std::env::var("QUPRS_GPMC_PATH") {
            return path;
        }

        if let Some(compile_path) = option_env!("GPMC_BIN_PATH") {
            if std::path::Path::new(compile_path).exists() {
                return compile_path.to_string();
            }
        }

        if cfg!(windows) {
            "gpmc.exe".to_string()
        } else {
            "gpmc".to_string()
        }
    }
    fn find_ganak_path() -> String {
        if let Ok(path) = std::env::var("QUPRS_GANAK_PATH") {
            return path;
        }

        if let Some(compile_path) = option_env!("GANAK_BIN_PATH") {
            if std::path::Path::new(compile_path).exists() {
                return compile_path.to_string();
            }
        }

        if cfg!(windows) {
            "ganak.exe".to_string()
        } else {
            "ganak".to_string()
        }
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
        let cnf_content = self.to_dimacs_string(tool_name);
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

        let result = (|| -> Result<Complex<f64>> {
            let exe_path = match tool_name {
                "gpmc" => Self::find_gpmc_path(),
                "ganak" => Self::find_ganak_path(),
                _ => return Err(anyhow!("Unsupported tool name: {}", tool_name)),
            };
            if tool_name == "ganak" {
                let provenance = crate::ganak_distribution::diagnostics_with_deadline(
                    std::path::Path::new(&exe_path),
                    std::env::var_os("QUPRS_GANAK_PATH").is_some(),
                    deadline,
                ).map_err(|e| if e.starts_with("SolverTimeout:") {
                    anyhow!(crate::solver_process::SolverTimeout)
                } else { anyhow!(e) })?;
                info!(target: "wmc", "{}", provenance);
            }
            let args: Vec<String> = solver_arguments(tool_name)?
                .iter().map(|arg| arg.to_string()).collect();
            debug!(target: "wmc", "Spawning {} solver: {} {:?} {}",
                tool_name, exe_path, args, temp_cnf_path.display());
            let mut command = Command::new(&exe_path);
            command.args(&args).arg(&temp_cnf_path);
            let output = crate::solver_process::run(&mut command, deadline)
                .with_context(|| format!("{} solver executable {}", tool_name, exe_path))?;

            let stdout_str = String::from_utf8_lossy(&output.stdout);
            let stderr_str = String::from_utf8_lossy(&output.stderr);
            if !output.status.success() {
                return Err(anyhow!(
                    "{} failed: status={}, command={} {:?}, stdout={}, stderr={}",
                    tool_name, output.status, exe_path, args, stdout_str, stderr_str
                ));
            }
            trace!(target: "wmc", "{} raw stdout:\n{}", tool_name, stdout_str);
            if !stderr_str.is_empty() {
                trace!(target: "wmc", "{} raw stderr:\n{}", tool_name, stderr_str);
            }

            let mut result_val = None;
            for line in stdout_str.lines() {
                if let Some(count) = parse_count_line(line)? {
                    info!(target: "wmc", "{} result parsed: {}", tool_name, count);
                    result_val = Some(count);
                }
            }
            result_val.ok_or_else(|| anyhow!(
                "{} Error!\nCNF Path: {}\n--- STDOUT ---\n{}\n--- STDERR ---\n{}",
                tool_name, temp_cnf_path.display(), stdout_str, stderr_str
            ))
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
    use super::{parse_real_count, solver_arguments};
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
        assert!(parse_count_line("c s exact quadruple floating 1").unwrap().is_none());
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

}
