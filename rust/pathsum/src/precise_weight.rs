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
pub(crate) fn from_phase(phase:&PhaseCoeff)->Result<(String,String)> {
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
    let mut re=[0 as c_char;160];
    let mut im=[0 as c_char;160];
    let code=unsafe{quprs_mpfr_phase_weight(
        args[0].as_ptr(),args[1].as_ptr(),args[2].as_ptr(),args[3].as_ptr(),
        192,re.as_mut_ptr(),im.as_mut_ptr(),160)};
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
    fn native_source_exact_clifford_and_underflow_control() {
        assert_eq!(from_phase(&PhaseCoeff::QUARTER).unwrap(),("0.0".into(),"1.0".into()));
        let mut tiny=PhaseCoeff::ZERO;
        tiny.radians=Some(BigRational::new(BigInt::from(1),BigInt::from(10u8).pow(400)));
        let (re,im)=from_phase(&tiny).unwrap();
        assert_ne!(im,"0.0");
        assert!(im.contains("e-"),"nonzero tiny source phase was truncated: {im}");
        assert!(re.starts_with("1."),"unexpected real component {re}");
    }
}
