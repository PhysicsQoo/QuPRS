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
fn mpfr_weight(phase:&PhaseCoeff)->(String,String) {
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
