//! QuPRS browser adapter. Upstream verification and numeric classifications are
//! reused; returned estimates are NOT end-to-end certified distance intervals.
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, ToPrimitive, Zero};
use quprs::browser_transport::{self, Job};
use quprs::{
    EquivalenceCheckResult, QuantumCircuit, VerificationMethod, VerificationOptions,
    VerificationStrategy,
};
use serde::Deserialize;
use serde_json::{json, Value};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;
#[derive(Clone, Deserialize)]
struct Request {
    circuit1: String,
    circuit2: String,
    #[serde(default = "hybrid")]
    mode: String,
    #[serde(default = "difference")]
    strategy: String,
    #[serde(default = "epsilon")]
    distance_tolerance: f64,
    #[serde(default = "rr_epsilon")]
    rr_tolerance: f64,
}
fn hybrid() -> String {
    "hybrid".into()
}
fn difference() -> String {
    "difference".into()
}
fn epsilon() -> f64 {
    1e-8
}
fn rr_epsilon() -> f64 {
    1e-10
}
fn verify(req: &Request) -> Result<EquivalenceCheckResult, anyhow::Error> {
    let left = QuantumCircuit::from_qasm_str(&req.circuit1)?;
    let right = QuantumCircuit::from_qasm_str(&req.circuit2)?;
    let method = match req.mode.as_str() {
        "hybrid" => VerificationMethod::Hybrid,
        "wmc" => VerificationMethod::WmcOnly,
        "reduction" => VerificationMethod::ReductionRules,
        _ => return Err(anyhow::anyhow!("Unsupported verification mode")),
    };
    let strategy = match req.strategy.as_str() {
        "difference" => VerificationStrategy::Difference,
        "proportional" => VerificationStrategy::Proportional,
        "naive" => VerificationStrategy::Naive,
        "straightforward" => VerificationStrategy::Straightforward,
        _ => return Err(anyhow::anyhow!("Unsupported strategy")),
    };
    let options = VerificationOptions {
        method,
        strategy,
        timeout_secs: 200,
        rr_tolerance: req.rr_tolerance,
        approximate_distance_tolerance: Some(req.distance_tolerance),
        ..VerificationOptions::default()
    };
    quprs::verification::check_equivalence(&left, &right, &options)
}
fn report(result: EquivalenceCheckResult, stdout: Option<&str>) -> Result<Value, String> {
    let mut distance = None;
    let mut kind = "not_computed";
    let mut warning = String::new();
    if let Some(stdout) = stdout {
        let count = quprs::precision_count::parse_stdout(stdout).map_err(|e| e.to_string())?;
        let active = result
            .final_ps
            .v
            .path_vars
            .len()
            .checked_sub(result.qubit_num)
            .ok_or("Invalid WMC normalization")?;
        let power = result
            .qubit_num
            .checked_mul(2)
            .and_then(|n| n.checked_add(active))
            .ok_or("WMC normalization capacity exceeded")?;
        let norm2 = (&count.real * &count.real + &count.imag * &count.imag)
            / BigRational::from_integer(BigInt::one() << power);
        let defect = BigRational::one() - &norm2;
        if defect < BigRational::zero() {
            warning="Printed count exceeds the unitary magnitude limit; no distance estimate is assigned.".into();
        } else {
            let d = defect
                .to_f64()
                .ok_or("Distance outside numeric display range")?;
            // Match the core's projective Hilbert-Schmidt distance, not
            // phase-minimized chordal Frobenius distance.
            distance = Some(d.sqrt());
            kind = "printed_count_estimate";
            if distance == Some(0.0) && !defect.is_zero() {
                warning="Distance is below binary64 display resolution; zero is not an exact-equivalence certificate.".into();
            }
        }
    } else if !result.rr_approximate
        && (result.final_ps.is_identity_up_to_phase()
            || result.wmc_precision_reason == Some("analytic_unweighted_tautology"))
    {
        distance = Some(0.0);
        kind = "symbolic_identity";
    } else if result.rr_approximate {
        warning="QuPRS accepted under its reduction tolerance. A numerical distance was not computed; no exact equality is claimed.".into();
    }
    Ok(
        json!({"status":result.equivalent(),"qubits":result.qubit_num,"gates1":result.gate_num1,"gates2":result.gate_num2,
  "method":result.method.as_str(),"strategy":format!("{:?}",result.strategy),"distance_estimate":distance,"distance_kind":kind,
  "distance_metric":"projective_hilbert_schmidt","global_phase_ignored":true,"certified_distance_interval":false,
  "rr_approximate":result.rr_approximate,"solver_invoked":result.solver_invoked,
  "numerical_verdict":result.wmc_printed_verdict,"precision_reason":result.wmc_precision_reason,
  "distance_tolerance":result.approximate_distance_tolerance,"warning":warning,
  "core_seconds":result.verification_time,"pathsum_seconds":result.pathsum_time,"counter_seconds":result.tool_time,
  "source_revision":option_env!("QUPRS_WEB_SOURCE_REVISION").unwrap_or("source checkout"),"web_weight_precision":"upstream MPFR source-phase weights (96–1024 bits), generated in counter worker; MPFR complex counting, 30 decimal digits"}),
    )
}
#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
pub struct BrowserJob {
    request: Request,
    job: Option<Job>,
    immediate: Option<Value>,
}
#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
impl BrowserJob {
    #[cfg_attr(target_arch = "wasm32", wasm_bindgen(constructor))]
    pub fn new(request_json: &str) -> Result<BrowserJob, String> {
        let request: Request = serde_json::from_str(request_json).map_err(|e| e.to_string())?;
        let (result, job) =
            browser_transport::capture_with_epsilon(request.distance_tolerance, || {
                verify(&request)
            });
        let immediate = match (result, job.as_ref()) {
            (Ok(result), None) => Some(report(result, None)?),
            (Err(error), Some(_))
                if error.downcast_ref::<browser_transport::Pending>().is_some() =>
            {
                None
            }
            (Err(error), _) => return Err(error.to_string()),
            _ => return Err("Unexpected browser counter preparation state".into()),
        };
        Ok(BrowserJob {
            request,
            job,
            immediate,
        })
    }
    pub fn job(&self) -> String {
        if let Some(report) = &self.immediate {
            return json!({"report":report}).to_string();
        }
        let job = self.job.as_ref().unwrap();
        json!({"cnf":job.cnf,"engine":job.tool,"arguments":["-mode=1","-prec=30","-cs=64"]})
            .to_string()
    }
    pub fn finish(&self, stdout: &str) -> String {
        let result = (|| -> Result<Value, String> {
            if let Some(report) = &self.immediate {
                return Ok(report.clone());
            }
            let result = browser_transport::replay(self.job.as_ref().unwrap(), stdout, || {
                verify(&self.request)
            })
            .map_err(|e| e.to_string())?;
            report(result, Some(stdout))
        })();
        match result {
            Ok(report) => json!({"report":report}).to_string(),
            Err(e) => json!({"error":e}).to_string(),
        }
    }
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen(start)]
pub fn start() {
    console_error_panic_hook::set_once();
}
#[cfg(test)]
mod tests {
    use super::*;
    fn req(gates: &str, mode: &str) -> String {
        json!({"circuit1":format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n{}",gates.replace(';',";\n")),"circuit2":"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n","mode":mode}).to_string()
    }
    #[test]
    fn symbolic_identity_is_not_labelled_general_certificate() {
        let j = BrowserJob::new(&req("h q[0]; h q[0];", "hybrid")).unwrap();
        let v: Value = serde_json::from_str(&j.job()).unwrap();
        assert_eq!(v["report"]["distance_estimate"].as_f64(), Some(0.0));
        assert_eq!(v["report"]["certified_distance_interval"], false);
    }
    #[test]
    fn prepare_count_finish_and_reject_missing_count() {
        let j = BrowserJob::new(&req("h q[0]; h q[0];", "wmc")).unwrap();
        let v: Value = serde_json::from_str(&j.job()).unwrap();
        assert!(v["cnf"].is_string());
        assert!(j.finish("").contains("error"));
    }
    #[test]
    fn tiny_source_phase_is_not_replaced_by_unweighted_identity() {
        let tiny = format!("u1(0.{}1) q[0];", "0".repeat(399));
        let j = BrowserJob::new(&req(&tiny, "wmc")).unwrap();
        let v: Value = serde_json::from_str(&j.job()).unwrap();
        let cnf = v["cnf"].as_str().unwrap();
        assert!(cnf.contains("c p quprs-phase "));
        assert!(cnf.len() > 400);
        assert!(j
            .finish("c s exact double prec-sci 2+0i")
            .contains("acknowledge"));
    }
    #[test]
    fn validation_and_transport_restore_on_error() {
        assert!(BrowserJob::new(&req("measure q[0];", "wmc")).is_err());
        assert!(!browser_transport::active());
        assert!(BrowserJob::new(&req("", "invalid")).is_err());
        assert!(!browser_transport::active());
    }
}
