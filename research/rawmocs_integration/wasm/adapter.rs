// Scoped BrowserJob adapter: reject malformed, wrong-engine, incomplete or
// unacknowledged count responses before the original QuPRS replay.
fn rawmocs_replay_stdout(job: &Job, engine: &str, status: i32, stdout: &str, stderr: &str, ack: &str) -> Result<String, String> {
    if engine != "rawmocs" || job.tool != "gpmc" || status != 0 {
        return Err("Unexpected engine or unsuccessful counter".into());
    }
    if stdout.len() > 16384 || stderr.len() > 32768 {
        return Err("Counter output capacity exceeded".into());
    }
    let lines: Vec<_> = stdout.lines().collect();
    if lines.len() != 2 || !matches!(lines[0], "s SATISFIABLE" | "s UNSATISFIABLE") {
        return Err("Invalid RaWMoCS SAT status".into());
    }
    let words: Vec<_> = lines[1].split_whitespace().collect();
    if words.len() != 5 || words[..3] != ["c", "r", "mpfr"] {
        return Err("Invalid RaWMoCS count record".into());
    }
    let complete: Vec<_> = stderr.lines().filter(|l| l.starts_with("RAWMOCS_COMPLETE ")).collect();
    if complete.len() != 1 || stderr.lines().any(|l| l.starts_with("RAWMOCS_FAILURE")) ||
        !complete[0].split_whitespace().any(|t| t == "digits=30") ||
        !complete[0].split_whitespace().any(|t| t == "bits=100") {
        return Err("Missing or incorrect RaWMoCS precision receipt".into());
    }
    let phases = job.cnf.lines().filter(|l| l.starts_with("c p quprs-phase ")).count();
    if (phases == 0 && !ack.is_empty()) || (phases != 0 && ack != format!("c o quprs-phase-weights {phases}")) {
        return Err("Missing or incorrect phase acknowledgement".into());
    }
    // Existing QuPRS parser uses the pair grammar as a complex decimal.
    // Preserve all printed digits, and conservatively use the requested 30
    // significant digits for the printed-rounding diagnostic. This label is
    // internal compatibility transport, not an assertion of GPMC execution.
    for word in &words[3..] {
        if word.len() > 512 || word.contains('/') ||
           !word.chars().all(|c| c.is_ascii_digit() || matches!(c, '+' | '-' | '.' | 'e' | 'E')) {
            return Err("Invalid decimal count token".into());
        }
    }
    let imaginary = words[4].strip_prefix('+').unwrap_or(words[4]);
    let sign = if imaginary.starts_with('-') { "" } else { "+" };
    let normalized = format!("c o precision 30\nc s exact double prec-sci {} {}{}i\n", words[3], sign, imaginary);
    let count = quprs::precision_count::parse_stdout(&normalized).map_err(|e| e.to_string())?;
    if lines[0] == "s UNSATISFIABLE" && (!count.real.is_zero() || !count.imag.is_zero()) {
        return Err("UNSAT with nonzero count".into());
    }
    Ok(if ack.is_empty() { normalized } else { format!("{ack}\n{normalized}") })
}

#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
impl BrowserJob {
    pub fn finish_rawmocs(&self, engine: &str, status: i32, stdout: &str, stderr: &str, ack: &str) -> String {
        let result = (|| -> Result<Value, String> {
            let job = self.job.as_ref().ok_or("No counter job prepared")?;
            let normalized = rawmocs_replay_stdout(job, engine, status, stdout, stderr, ack)?;
            let mut value: Value = serde_json::from_str(&self.finish(&normalized)).map_err(|e| e.to_string())?;
            if let Some(report) = value.get_mut("report") {
                report["actual_solver"] = json!("rawmocs");
                report["solver_candidate_version"] = json!("0.4.1-alpha.1");
                report["solver_precision_digits"] = json!(30);
                report["solver_sat"] = json!(stdout.lines().next() == Some("s SATISFIABLE"));
            }
            Ok(value)
        })();
        match result {
            Ok(value) => value.to_string(),
            Err(e) => json!({"error":e}).to_string(),
        }
    }
}
