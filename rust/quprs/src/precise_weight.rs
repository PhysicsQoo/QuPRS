//! Source-exact high-resolution GPMC weight boundary.
//! The raw MPFR result is a numerical observation, not a Solver error bound.
use crate::rational::{PhaseCoeff,Rational};
use anyhow::{anyhow,Result};
use num_rational::BigRational;
use num_traits::Zero;
use std::ffi::{CStr,CString,c_char};

#[link(name="quprs_phase_mpfr",kind="static")]
unsafe extern "C" {
    fn quprs_mpfr_phase_weight(
        cycle_num:*const c_char,cycle_den:*const c_char,
        rad_num:*const c_char,rad_den:*const c_char,
        bits:usize,out_re:*mut c_char,out_im:*mut c_char,cap:usize)->i32;
}
/// Choose enough input-weight precision to resolve a projective-distance
/// threshold whose corresponding trace-magnitude defect is O(epsilon^2).
///
/// 32 guard bits plus log2(number of phase terms) reserve headroom for
/// input conversion and accumulation. This is an engineering precision
/// budget, NOT a certified error bound for arbitrary WMC cancellation or
/// the external solver. Never silently cap a smaller requested tolerance.
pub(crate) fn bits_for_distance(epsilon: f64, phase_terms: usize) -> Result<usize> {
    if !epsilon.is_finite() || epsilon <= 0.0 || epsilon >= 1.0 {
        return Err(anyhow!("approximate_distance_tolerance must be finite and in (0, 1)"));
    }
    const GUARD_BITS: f64 = 32.0;
    const GRANULARITY: f64 = 32.0;
    const MIN_BITS: f64 = 96.0;
    const MAX_BITS: f64 = 1024.0;
    let term_margin = (phase_terms.max(1) as f64).log2().ceil();
    let required = -2.0 * epsilon.log2() + term_margin + GUARD_BITS;
    let selected = (required / GRANULARITY).ceil() * GRANULARITY;
    if !selected.is_finite() || selected > MAX_BITS {
        return Err(anyhow!(
            "approximate_distance_tolerance requires more than 1024-bit MPFR input weights; \
             cannot meet the requested precision with this backend"
        ));
    }
    Ok(selected.max(MIN_BITS) as usize)
}

/// Generate one complex source-phase weight without converting through f64.
/// The working precision is selected by the verification request.
pub(crate) fn from_phase(phase:&PhaseCoeff, precision_bits:usize)->Result<(String,String)> {
    if !(64..=1024).contains(&precision_bits) {
        return Err(anyhow!("Unsupported MPFR input-weight precision"));
    }
    if !phase.symbols.is_empty() {
        return Err(anyhow!("Unbound phase symbol cannot become a numerical GPMC weight"));
    }
    if phase.radians.is_none() {
        let exact=match phase.constant {
            Rational::ZERO=>Some(("1.0","0.0")),
            Rational::HALF=>Some(("-1.0","0.0")),
            Rational::QUARTER=>Some(("0.0","1.0")),
            Rational::THREE_QUARTERS=>Some(("0.0","-1.0")),
            _=>None
        };
        if let Some((re,im))=exact {return Ok((re.into(),im.into()))}
    }
    let radians=phase.radians.as_ref().cloned().unwrap_or_else(BigRational::zero);
    let parts=[
        phase.constant.numer.to_string(),phase.constant.denom.to_string(),
        radians.numer().to_string(),radians.denom().to_string()
    ];
    let args=parts.iter().map(|s|CString::new(s.as_str()))
        .collect::<std::result::Result<Vec<_>,_>>()?;
    // 1024 bits need at most 312 significant decimal digits, plus exponent.
    let mut re=[0 as c_char;512];
    let mut im=[0 as c_char;512];
    let code=unsafe{quprs_mpfr_phase_weight(
        args[0].as_ptr(),args[1].as_ptr(),args[2].as_ptr(),args[3].as_ptr(),
        precision_bits,re.as_mut_ptr(),im.as_mut_ptr(),512)};
    if code!=0{return Err(anyhow!("MPFR source-phase weight computation failed ({code})"))}
    let re=unsafe{CStr::from_ptr(re.as_ptr())}.to_str()?.to_string();
    let im=unsafe{CStr::from_ptr(im.as_ptr())}.to_str()?.to_string();
    Ok((re,im))
}
#[cfg(test)]
mod tests {
    use super::*;
    use num_bigint::BigInt;
    #[test]
    fn mpfr_precision_tracks_distance_and_phase_count() {
        assert_eq!(bits_for_distance(1e-8, 1).unwrap(), 96);
        assert_eq!(bits_for_distance(1e-8, 1024).unwrap(), 96);
        assert_eq!(bits_for_distance(1e-12, 1).unwrap(), 128);
        assert_eq!(bits_for_distance(1e-16, 1).unwrap(), 160);
        assert_eq!(bits_for_distance(1e-20, 1).unwrap(), 192);
        assert!(bits_for_distance(1e-12, 1024).unwrap() >= 128);
        assert!(bits_for_distance(1e-40, 1).unwrap() > 192);
        assert!(bits_for_distance(1e-200, 1).is_err());
        for bad in [0.0, 1.0, f64::NAN, f64::INFINITY] {
            assert!(bits_for_distance(bad, 1).is_err());
        }
    }

    #[test]
    fn mpfr_weight_digits_scale_with_working_precision() {
        let phase = PhaseCoeff {
            constant: Rational::new(1, 8),
            radians: Some(BigRational::new(BigInt::from(1), BigInt::from(10u8).pow(20))),
            symbols: Default::default(),
        };
        let (re96, im96) = from_phase(&phase, 96).unwrap();
        let (re192, im192) = from_phase(&phase, 192).unwrap();
        assert!(re192.len() > re96.len());
        assert!(im192.len() > im96.len());
        assert!((re96.parse::<f64>().unwrap() - re192.parse::<f64>().unwrap()).abs() < 1e-14);
        assert!((im96.parse::<f64>().unwrap() - im192.parse::<f64>().unwrap()).abs() < 1e-14);
    }

    #[test]
    fn native_source_exact_clifford_and_underflow_control() {
        assert_eq!(from_phase(&PhaseCoeff::QUARTER, 96).unwrap(),("0.0".into(),"1.0".into()));
        let mut tiny=PhaseCoeff::ZERO;
        tiny.radians=Some(BigRational::new(BigInt::from(1),BigInt::from(10u8).pow(400)));
        let (re,im)=from_phase(&tiny, 96).unwrap();
        assert_ne!(im,"0.0");
        assert!(im.contains("e-"),"nonzero tiny source phase was truncated: {im}");
        assert!(re.starts_with("1."),"unexpected real component {re}");
    }
}
