//! Experimental-only native Rust weight boundary. No public path changes.
//! Fixed-point BigInt Taylor reference, deliberately slower than MPFR;
//! it diagnoses f64 input loss and measures cost, NOT a production proposal.
use crate::rational::{Angle, PhaseCoeff, Rational};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, ToPrimitive, Zero};
use std::str::FromStr;
use std::time::Instant;

const DECIMALS: u32 = 60;
const PRINT_DIGITS: u32 = 42;
// Truncated pi with 60 correct fractional decimal digits, not f64.
const PI_SCALED: &str = "3141592653589793238462643383279502884197169399375105820974944";

fn scale() -> BigInt { BigInt::from(10_u8).pow(DECIMALS) }
fn pi_scaled() -> BigInt { BigInt::from_str(PI_SCALED).unwrap() }
fn exact_ratio_scaled(r: &BigRational, s: &BigInt) -> BigInt {
    (r.numer() * s) / r.denom()
}

fn fixed_trig(coeff: &PhaseCoeff) -> (BigInt, BigInt) {
    assert!(coeff.symbols.is_empty(), "unbound source symbols cannot be weights");
    let s = scale();
    let pi = pi_scaled();
    let tau = &pi * 2;
    let rational = (BigInt::from(coeff.constant.numer) * &tau) / coeff.constant.denom;
    let source = coeff.radians.as_ref().map(|v| exact_ratio_scaled(v, &s) * 2)
        .unwrap_or_else(BigInt::zero);
    let mut angle = (rational + source) % &tau;
    if angle.is_negative() { angle += &tau; }
    if angle > pi { angle -= &tau; }
    let squared = (&angle * &angle) / &s;
    let mut sin_term = angle.clone();
    let mut cos_term = s.clone();
    let mut sin_sum = sin_term.clone();
    let mut cos_sum = cos_term.clone();
    for k in 1..55_u32 {
        let sine_div = BigInt::from((2*k)*(2*k+1));
        let cosine_div = BigInt::from((2*k-1)*(2*k));
        sin_term = -(sin_term * &squared) / (&s * sine_div);
        cos_term = -(cos_term * &squared) / (&s * cosine_div);
        sin_sum += &sin_term;
        cos_sum += &cos_term;
        if sin_term.is_zero() && cos_term.is_zero() { break; }
    }
    (cos_sum,sin_sum)
}
fn decimal(value: &BigInt) -> String {
    let digits = PRINT_DIGITS as usize;
    let divisor = BigInt::from(10_u8).pow(DECIMALS - PRINT_DIGITS);
    // Round half away from zero; this is an output encoding, not solver error.
    let rounded = (value.abs() + &divisor/2) / &divisor;
    let format_scale = BigInt::from(10_u8).pow(PRINT_DIGITS);
    let whole = &rounded / &format_scale;
    let fractional = (&rounded % &format_scale).to_string();
    let sign = if value.is_negative() && !rounded.is_zero() { "-" } else { "" };
    format!("{}{}.{:0>width$}",sign,whole,fractional,width=digits)
}
fn exact_decimal_to_fixed(src: &str) -> BigInt {
    let negative=src.starts_with('-');
    let t=src.trim_start_matches('-');
    let (w,f)=t.split_once('.').unwrap_or((t,""));
    assert!(f.len() <= DECIMALS as usize);
    let mut digits = w.to_owned();
    digits.push_str(f);
    digits.push_str(&"0".repeat(DECIMALS as usize - f.len()));
    let magnitude=BigInt::from_str(&digits).unwrap();
    if negative { -magnitude } else { magnitude }
}
fn phase_from_radian_angle(angle: &str) -> PhaseCoeff {
    // A phase polynomial term weight is exp(2*pi*i*c + 2*i*radians);
    // source physical theta must therefore be halved to encode exp(i*theta).
    (Angle::from_qasm_str(angle).unwrap() / 2).to_phase_coeff()
}
fn baseline(coeff: &PhaseCoeff) -> (f64,f64) {
    let cycles=(coeff.constant.numer as f64)/(coeff.constant.denom as f64);
    let radians=coeff.radians.as_ref().map(|x|x.to_f64().unwrap()).unwrap_or(0.0);
    let theta=2.0*std::f64::consts::PI*cycles+2.0*radians;
    (theta.cos(),theta.sin())
}
fn quantized_error(value: &BigInt, expected: &str) -> BigInt {
    (value-exact_decimal_to_fixed(expected)).abs()
}

#[test]
fn experimental_rust_weight_boundary_accuracy_and_source_terms() {
    let controls=[
        ("0.000000025",
         "0.9999999999999996875000000000000162760416666666663275825",
         "0.00000002499999999999999739583333333333341471354166666666545565"),
        ("0.0001",
         "0.9999999950000000041666666652777777780257936507660934744",
         "0.00009999999983333333341666666664682539682815255731897346481"),
        ("2.0330832984526417",
         "-0.4459961908679448925028174921462047437482224889885132426",
         "0.895034858388925357766890682451523131671048595425616525"),
    ];
    // Match 35 digits in the result, well below the 42-digit output precision.
    let limit=BigInt::from(10_u8).pow(DECIMALS-35);
    for (angle,re,im) in controls {
        let coeff=phase_from_radian_angle(angle);
        let (high_re,high_im)=fixed_trig(&coeff);
        assert!(quantized_error(&high_re,re)<limit,"real mismatch for {angle}");
        assert!(quantized_error(&high_im,im)<limit,"imag mismatch for {angle}");
        let (lo_re,lo_im)=baseline(&coeff);
        eprintln!("EXPERIMENT_NATIVE_WEIGHT angle={} f64_re={:.17e} f64_im={:.17e} hp_re={} hp_im={} f64_re_error={:.6e} f64_im_error={:.6e}",
            angle,lo_re,lo_im,decimal(&high_re),decimal(&high_im),
            (lo_re-high_re.to_f64().unwrap()/1e60).abs(),
            (lo_im-high_im.to_f64().unwrap()/1e60).abs());
        let residue=(&high_re*&high_re+&high_im*&high_im-scale().pow(2_u32)).abs();
        assert!(residue < BigInt::from(10_u8).pow(2*DECIMALS-35),
                "significant unit-modulus drift for {angle}");
    }
    // Check actual native PathSum, not lexical gate-angle proxies.
    let qasm="OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz(0.000000025) q[0];\n";
    let ps=crate::pathsum::PathSum::load_from_qasm_str(qasm,None).unwrap();
    assert!(!ps.p.terms.is_empty());
    let mut source_radian_terms=0;
    for (monomial,coeff) in &ps.p.terms {
        if coeff.radians.is_some() {
            source_radian_terms+=1;
            let (r,i)=fixed_trig(coeff);
            eprintln!("EXPERIMENT_NATIVE_PATHSUM monomial={:?} source_fraction={:?} phase_constant={} hp_re={} hp_im={}",
                monomial,coeff.radians,coeff.constant,decimal(&r),decimal(&i));
        }
    }
    assert!(source_radian_terms>0,"source radians must reach real PathSum phase terms");
}

#[test]
fn experimental_rust_weight_boundary_paired_cost() {
    use std::hint::black_box;
    let phases: Vec<PhaseCoeff>=(1..=24_u32)
        .map(|k| phase_from_radian_angle(&format!("0.{:016}",k*317)))
        .collect();
    let mut b_ns=Vec::new();let mut hp_ns=Vec::new();
    // Interleaved replicates on a single runner; benchmark is a microcost only.
    for rep in 0..5 {
        let start=Instant::now();
        for _ in 0..1000 {
            for coeff in &phases { black_box(baseline(black_box(coeff))); }
        }
        b_ns.push(start.elapsed().as_nanos() as f64/(1000*phases.len()) as f64);
        let start=Instant::now();
        for _ in 0..12 {
            for coeff in &phases {
                let (r,i)=fixed_trig(black_box(coeff));
                black_box((decimal(&r),decimal(&i)));
            }
        }
        hp_ns.push(start.elapsed().as_nanos() as f64/(12*phases.len()) as f64);
        if rep==0 { eprintln!("EXPERIMENT_NATIVE_WEIGHT_COST warm_first_replicate=true"); }
    }
    b_ns.sort_by(|a,b|a.partial_cmp(b).unwrap());
    hp_ns.sort_by(|a,b|a.partial_cmp(b).unwrap());
    eprintln!("EXPERIMENT_NATIVE_WEIGHT_COST f64_median_ns={} bigint_reference_median_ns={} bigint_over_f64={} phases={} replicates=5",
        b_ns[2],hp_ns[2],hp_ns[2]/b_ns[2],phases.len());
}
