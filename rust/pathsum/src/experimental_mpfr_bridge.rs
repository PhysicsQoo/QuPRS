//! Experiment-only native MPFR boundary; no solver or public API changes.
use crate::rational::{Angle,PhaseCoeff,Rational};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, Zero};
use std::ffi::{CStr,CString,c_char};
use std::time::Instant;
use std::hint::black_box;

#[link(name="quprs_exp_mpfr", kind="static")]
unsafe extern "C" {
    fn quprs_exp_mpfr_phase_weight(
        cycles_num:*const c_char,cycles_den:*const c_char,
        radians_num:*const c_char,radians_den:*const c_char,
        bits:usize,out_re:*mut c_char,out_im:*mut c_char,cap:usize
    )->i32;
}

fn exact_special_weight(phase:&PhaseCoeff)->Option<(&'static str,&'static str)> {
    if !phase.symbols.is_empty() || phase.radians.is_some() {return None}
    match (phase.constant.numer,phase.constant.denom) {
        (0,1) => Some(("1.0","0.0")),
        (1,4) => Some(("0.0","1.0")),
        (1,2) => Some(("-1.0","0.0")),
        (3,4) => Some(("0.0","-1.0")),
        _ => None,
    }
}
pub(crate) fn mpfr_weight(phase:&PhaseCoeff)->(String,String) {
    if let Some((re,im))=exact_special_weight(phase) {
        return (re.into(),im.into());
    }
    assert!(phase.symbols.is_empty());
    let fraction=phase.radians.as_ref()
        .cloned().unwrap_or_else(BigRational::zero);
    let parts=[
        phase.constant.numer.to_string(),
        phase.constant.denom.to_string(),
        fraction.numer().to_string(),
        fraction.denom().to_string()
    ];
    let inputs:Vec<CString>=parts.iter()
        .map(|t|CString::new(t.as_str()).unwrap()).collect();
    let mut re=[0 as c_char;160];
    let mut im=[0 as c_char;160];
    let status=unsafe {quprs_exp_mpfr_phase_weight(
        inputs[0].as_ptr(),inputs[1].as_ptr(),inputs[2].as_ptr(),
        inputs[3].as_ptr(),192,re.as_mut_ptr(),im.as_mut_ptr(),160)};
    assert_eq!(status,0,"native MPFR failed to evaluate {phase:?}");
    (unsafe {CStr::from_ptr(re.as_ptr())}.to_str().unwrap().to_string(),
     unsafe {CStr::from_ptr(im.as_ptr())}.to_str().unwrap().to_string())
}
fn original_f64(phase:&PhaseCoeff)->(f64,f64) {
    use num_traits::ToPrimitive;
    let cycle=(phase.constant.numer as f64)/(phase.constant.denom as f64);
    let r=phase.radians.as_ref().map(|v|v.to_f64().unwrap()).unwrap_or(0.0);
    let angle=cycle*2.0*std::f64::consts::PI+2.0*r;
    (angle.cos(),angle.sin())
}
fn phase_from_angle(s:&str)->PhaseCoeff {
    (Angle::from_qasm_str(s).unwrap()/2).to_phase_coeff()
}
fn as_fraction_real_im(re:&str,im:&str)->(BigRational,BigRational) {
    let printed=crate::precision_count::parse_line(&format!(
        "c s exact double prec-sci {re} + {im}i"
    )).unwrap().unwrap();
    (printed.real,printed.imag)
}
fn reference(c:&PhaseCoeff)->(BigRational,BigRational) {
    // The previous independently validated 60-decimal BigInt reference.
    // Trigonometric reference is not evaluated by the MPFR library.
    use crate::experimental_weight_boundary::fixed_trig;
    let (r,i)=fixed_trig(c);
    let denom=BigInt::from(10_u8).pow(60);
    (BigRational::new(r,denom.clone()),BigRational::new(i,denom))
}

#[test]
fn experimental_native_mpfr_precision_and_exact_clifford_fast_path() {
    for (r,expected) in [
        (Rational::ZERO,("1.0","0.0")),
        (Rational::QUARTER,("0.0","1.0")),
        (Rational::HALF,("-1.0","0.0")),
        (Rational::THREE_QUARTERS,("0.0","-1.0"))
    ] {
        assert_eq!(mpfr_weight(&PhaseCoeff::new_constant(r)),
            (expected.0.to_string(),expected.1.to_string()));
    }
    let source="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz(0.000000025) q[0];\n";
    let pathsum=crate::pathsum::PathSum::load_from_qasm_str(source,None).unwrap();
    let mut terms=0_u32;
    let mut max_diff=BigRational::zero();
    for (name,c) in [
        ("theta=2.5e-8",phase_from_angle("0.000000025")),
        ("theta=1e-4",phase_from_angle("0.0001")),
        ("theta=2.0330832984526417",phase_from_angle("2.0330832984526417"))
    ].into_iter().chain(pathsum.p.terms.iter()
        .filter(|(_,c)|c.radians.is_some())
        .map(|(m,c)|(if m.is_empty() {"qasm_constant"}else{"qasm_monomial"},c.clone())))
    {
        let (re,im)=mpfr_weight(&c);
        let (r,i)=as_fraction_real_im(&re,&im);
        let (ref_r,ref_i)=reference(&c);
        let diff_r=(r-ref_r).abs();
        let diff_i=(i-ref_i).abs();
        max_diff=max_diff.max(diff_r.clone()).max(diff_i.clone());
        let tolerance=BigRational::new(BigInt::from(1),BigInt::from(10_u8).pow(42));
        assert!(diff_r<tolerance && diff_i<tolerance,
            "native MPFR deviates from independent reference for {name}: re={diff_r},im={diff_i}");
        let (f64r,f64i)=original_f64(&c);
        eprintln!("EXPERIMENT_MPFR_WEIGHT case={} f64_re={:.17e} f64_im={:.17e} mpfr_re={} mpfr_im={} source_decimal_ref_match_lt_1e-42=true",
            name,f64r,f64i,re,im);
        terms+=1;
    }
    assert!(terms>=5);
    eprintln!("EXPERIMENT_MPFR_ACCURACY checks={} max_component_error_rational={} source_qasm=true",
        terms,max_diff);
}
#[test]
fn experimental_native_mpfr_selective_paired_cost() {
    let phases:Vec<PhaseCoeff>=(1..=24_u32)
        .map(|k| phase_from_angle(&format!("0.{:016}",k*317))).collect();
    let mut fast=Vec::new();
    let mut high=Vec::new();
    for rep in 0..7 {
        // Alternate order every replicate to mitigate warmup bias.
        let orders=if rep%2==0 {[0,1]}else{[1,0]};
        for mode in orders {
            let rounds=if mode==0 {800}else{30};
            let start=Instant::now();
            for _ in 0..rounds {
                for coeff in &phases {
                    if mode==0 {
                        let (r,i)=original_f64(black_box(coeff));
                        black_box(format!("{r:.16e} {i:.16e}"));
                    }else{
                        black_box(mpfr_weight(black_box(coeff)));
                    }
                }
            }
            let each=(start.elapsed().as_nanos() as f64)/(rounds*phases.len()) as f64;
            if mode==0 {fast.push(each)}else{high.push(each)}
        }
    }
    fast.sort_by(|a,b|a.partial_cmp(b).unwrap());
    high.sort_by(|a,b|a.partial_cmp(b).unwrap());
    eprintln!("EXPERIMENT_MPFR_COST phase_samples=24 paired_reps=7 f64_plus_text_median_ns={:.3} mpfr_192bit_plus_48digit_text_median_ns={:.3} ratio={:.3}",
        fast[3],high[3],high[3]/fast[3]);
    assert!(fast[3]>0.0 && high[3]>0.0);
}


#[cfg(target_os="linux")]
mod end_to_end {
    use super::*;
    use crate::wmc::WmcManager;
    use crate::pathsum::PathSum;
    use crate::strategy::VerificationStrategy;
    use crate::precision_count::{PrintedCount,PrintedVerdict};
    use std::fs;
    use std::path::{Path,PathBuf};
    use std::process::Command;
    use std::sync::atomic::{AtomicUsize,Ordering};
    use std::time::{Duration,Instant};
    static TRIAL_ID:AtomicUsize=AtomicUsize::new(0);

    struct ScopedFile(PathBuf);
    impl Drop for ScopedFile { fn drop(&mut self){let _=fs::remove_file(&self.0);} }
    fn temporary(ext:&str)->ScopedFile {
        let n=TRIAL_ID.fetch_add(1,Ordering::Relaxed);
        ScopedFile(std::env::temp_dir().join(format!(
            "quprs-exp-e2e-{}-{n}.{ext}",std::process::id())))
    }
    fn gpmc_once(cnf:&str,limit:Duration)->anyhow::Result<(PrintedCount,f64,u64)> {
        // Existing supervised child process; /usr/bin/time provides peak child
        // RSS (KiB) without a second WMC invocation or solver source patch.
        let input=temporary("cnf");
        let usage=temporary("usage");
        fs::write(&input.0,cnf)?;
        let adapter=crate::solver_adapter::distance_adapter_for("gpmc")?;
        let mut cmd=Command::new("/usr/bin/time");
        cmd.args(["-f","%M %e","-o"]).arg(&usage.0)
            .arg(adapter.executable_path())
            .args(adapter.arguments())
            .arg(&input.0);
        let begin=Instant::now();
        let result=crate::solver_process::run(&mut cmd,Some(begin+limit));
        let elapsed=begin.elapsed().as_secs_f64();
        match result {
            Ok(out)=>{
                if !out.status.success() {
                    return Err(anyhow::anyhow!("real GPMC failed: status={} stderr={}",
                        out.status,String::from_utf8_lossy(&out.stderr)));
                }
                let printed=crate::precision_count::parse_stdout(
                    &String::from_utf8_lossy(&out.stdout))?;
                let time_txt=fs::read_to_string(&usage.0)?;
                let fields:Vec<_>=time_txt.split_whitespace().collect();
                if fields.len()<2 {return Err(anyhow::anyhow!("missing /usr/bin/time RSS"))}
                let rss=fields[0].parse::<u64>()?;
                Ok((printed,elapsed,rss))
            }
            Err(error)=>Err(error)
        }
    }
    fn strip_nonunitary_qasm(source:&str)->String {
        source.lines().filter(|line|{
            let s=line.trim();
            !s.starts_with("measure ") && !s.starts_with("barrier ")
                && !s.starts_with("reset ") && !s.starts_with("creg ")
        }).collect::<Vec<_>>().join("\n")
    }
    fn normalized_verdict(count:&PrintedCount, n:usize, npaths:usize)->anyhow::Result<PrintedVerdict> {
        let twice= n.checked_add(npaths).ok_or_else(||anyhow::anyhow!("overflow"))?;
        Ok(crate::precision_count::classify(count,twice.try_into()?,"1e-8")?)
    }
    fn median(v:&mut [f64])->f64 {
        v.sort_by(|a,b|a.partial_cmp(b).unwrap());v[v.len()/2]
    }
    fn trim_weight(cnf:&str)->Vec<&str> {
        cnf.lines().filter(|line| !line.starts_with("c p weight ")).collect()
    }
    fn benchmark_one(name:&str,qasm_path:&Path, repeats:usize, solve_seconds:u64)->anyhow::Result<()> {
        let qasm=strip_nonunitary_qasm(&fs::read_to_string(qasm_path)?);
        let (base,n)=crate::qasm::parse_qasm_str(&qasm)
            .map_err(|s|anyhow::anyhow!("{} qasm parse: {}",name,s))?;
        // Independent physical oracle: V = Rz(theta) U, so
        // |Tr(U†V)|/2^n = |cos(theta/2)| for every circuit U.
        const THETA:&str="0.000000025";
        let mut perturbed=base.clone();
        perturbed.push(crate::ir::QuantumOp::RZ(
            0,crate::rational::Angle::from_qasm_str(THETA)
                .map_err(|s|anyhow::anyhow!(s))?));
        let t0=Instant::now();
        let mut ps=PathSum::new(n);
        ps.set_auto_reduce(true);
        let miter=VerificationStrategy::Difference.run(ps,&base,&perturbed);
        let pathsum_s=t0.elapsed().as_secs_f64();
        let mut manager=WmcManager::new(&miter);
        let enc=Instant::now();
        manager.encode_trace(&miter)?;
        let encoding_s=enc.elapsed().as_secs_f64();
        let serial=Instant::now();
        let low=manager.to_dimacs_string("gpmc");
        let low_serial_s=serial.elapsed().as_secs_f64();
        let serial=Instant::now();
        let high=manager.experimental_precise_gpmc_cnf();
        let high_serial_s=serial.elapsed().as_secs_f64();
        assert_eq!(trim_weight(&low),trim_weight(&high),
            "MPFR candidate must not modify logical clauses or variable IDs");
        let weight_terms=manager.numerical_weight_count();
        let nonclifford=manager.experimental_phase_weights.iter()
            .filter(|(_,phase)|phase.radians.is_some()
                || !matches!((phase.constant.numer,phase.constant.denom),
                    (0,1)|(1,4)|(1,2)|(3,4)))
            .count();
        let mut timings=[Vec::new(),Vec::new()];
        let mut rss=[Vec::new(),Vec::new()];
        let mut verdicts=[Vec::new(),Vec::new()];
        let mut timeout=[false,false];
        for k in 0..repeats {
            for idx in if k%2==0 {[0,1]} else {[1,0]} {
                let selected=if idx==0 {&low}else{&high};
                match gpmc_once(selected,Duration::from_secs(solve_seconds)) {
                    Ok((count,elapsed,r))=>{
                        let observed=normalized_verdict(&count,n,miter.v.path_vars.len())?;
                        assert_ne!(observed,PrintedVerdict::Equivalent,
                            "incorrect positive equivalence for D=1.25e-8 case={name} variant={idx}");
                        eprintln!("EXPERIMENT_END_TO_END_SAMPLE case={name} n={n} rep={k} variant={} gpmc_wall_s={elapsed:.6} rss_kib={r} verdict={observed:?}",
                            if idx==0 {"f64"} else {"mpfr"});
                        timings[idx].push(elapsed);
                        rss[idx].push(r as f64);
                        verdicts[idx].push(format!("{observed:?}"));
                    }
                    Err(e)=>{
                        let message=format!("{e:#}");
                        if e.downcast_ref::<crate::solver_process::SolverTimeout>().is_some() {
                            timeout[idx]=true;
                            eprintln!("EXPERIMENT_END_TO_END_TIMEOUT case={name} n={n} rep={k} variant={} seconds={solve_seconds}",
                                if idx==0 {"f64"} else {"mpfr"});
                        } else {return Err(anyhow::anyhow!("case={name} variant={idx} {message}"))}
                    }
                }
                if timeout[idx] {break;}
            }
            if timeout.iter().any(|x|*x) {break;}
        }
        let baseline=if !timings[0].is_empty(){median(&mut timings[0])}else{f64::NAN};
        let candidate=if !timings[1].is_empty(){median(&mut timings[1])}else{f64::NAN};
        let baseline_rss=if !rss[0].is_empty(){median(&mut rss[0])}else{f64::NAN};
        let candidate_rss=if !rss[1].is_empty(){median(&mut rss[1])}else{f64::NAN};
        let overhead=high_serial_s-low_serial_s;
        let ratio=if baseline.is_finite(){(candidate+high_serial_s)/(baseline+low_serial_s)}else{f64::NAN};
        eprintln!("EXPERIMENT_END_TO_END_SUMMARY case={name} gates={} n={} pathsum_s={pathsum_s:.6} cnf_encode_s={encoding_s:.6} weights={} expensive_weights={} cnf_vars={} cnf_clauses={} cnf_bytes_f64={} cnf_bytes_mpfr={} f64_serialize_s={low_serial_s:.6} mpfr_serialize_s={high_serial_s:.6} delta_serialize_s={overhead:.6} f64_solver_median_s={baseline:.6} mpfr_solver_median_s={candidate:.6} f64_rss_kib={baseline_rss:.0} mpfr_rss_kib={candidate_rss:.0} solver_plus_serialize_ratio={ratio:.5} f64_verdict={:?} mpfr_verdict={:?} timeout_f64={} timeout_mpfr={} oracle_D=1.25e-8",
            base.len(),weight_terms,manager.to_dimacs_string("gpmc").lines().next().unwrap_or(""),
            low.len(),high.len(),verdicts[0],verdicts[1],timeout[0],timeout[1]);
        Ok(())
    }
    #[test]
    fn experimental_end_to_end_algorithm_weight_ab() {
        let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let cases=[
            ("grover4","benchmarks/MQTBench/grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"),
            ("qaoa7","benchmarks/MQTBench/qaoa_nativegates_ibm_qiskit_opt0_7.qasm"),
            ("graphstate16","benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm"),
            ("qft16","benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_16.qasm"),
        ];
        for (name,file) in cases {
            let path=root.join(file);
            if let Err(e)=benchmark_one(name,&path,2,12) {
                panic!("bounded public-corpus end-to-end experiment {name}: {e:#}");
            }
        }
    }
}
