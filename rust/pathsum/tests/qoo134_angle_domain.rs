//! QOO-134 research-only exact angle-domain algebra.
//!
//! This standalone integration test models *input expression semantics*;
//! it DOES NOT replace Angle, FreeRational, PhaseCoeff or native verification.
//! Decimal radians and rational multiples of pi are disjoint bases.
//! The reasoning about 2π congruence is valid only for this declared exact
//! source-literal interpretation, not automatically for Qiskit rounded f64.
use num_bigint::BigInt;
use num_integer::Integer;
use num_rational::BigRational;
use num_traits::{Pow, Zero};
use std::ops::{Add, Neg, Sub};

#[derive(Clone, Debug, Eq, PartialEq)]
struct ExactAngle {
    /// The exact coefficient of symbolic π.
    pi: BigRational,
    /// An exact rational number of radians, parsed from decimal tokens.
    radians: BigRational,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum SourceSemantics {
    /// Decimal tokens are rational numbers in radians, and π is symbolic.
    ExactQasmLiterals,
    /// A numeric simulator may round or evaluate expressions as f64.
    /// That interpretation needs a separately certified error contract.
    RoundedNumericUncertified,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Conclusion {
    EquivalentProof,
    DifferentProof,
    Unknown,
}

impl ExactAngle {
    fn zero() -> Self {
        Self {
            pi: BigRational::zero(),
            radians: BigRational::zero(),
        }
    }

    fn rational_radians(decimal: &str) -> Result<Self, String> {
        Ok(Self {
            pi: BigRational::zero(),
            radians: parse_decimal_rational(decimal)?,
        })
    }

    fn pi_ratio(numer: i64, denom: i64) -> Result<Self, String> {
        if denom == 0 {
            return Err("invalid zero denominator for pi fraction".into());
        }
        Ok(Self {
            pi: BigRational::new(BigInt::from(numer), BigInt::from(denom)),
            radians: BigRational::zero(),
        })
    }

    /// A deliberately strict subset of QASM phase syntax, with no f64 path.
    /// Accepted: exact decimal radians; pi; -pi; pi/8; 3*pi/4; -2*pi.
    /// Unsupported mixed/nonlinear expressions return an error, not a guess.
    fn parse_source_token(token: &str) -> Result<Self, String> {
        let token = token.trim().to_ascii_lowercase().replace(' ', "");
        if !token.contains("pi") {
            return Self::rational_radians(&token);
        }
        let Some((prefix, suffix)) = token.split_once("pi") else {
            return Err("expected pi".into());
        };
        let numerator = match prefix {
            "" | "+" => BigRational::from_integer(BigInt::from(1)),
            "-" => BigRational::from_integer(BigInt::from(-1)),
            _ => {
                let coeff = prefix
                    .strip_suffix('*')
                    .ok_or_else(|| "expected rational*pi".to_string())?;
                parse_decimal_rational(coeff)?
            }
        };
        let denominator = if suffix.is_empty() {
            BigRational::from_integer(BigInt::from(1))
        } else {
            let literal = suffix
                .strip_prefix('/')
                .ok_or_else(|| "unsupported expression after pi".to_string())?;
            let d = parse_decimal_rational(literal)?;
            if d <= BigRational::zero() {
                return Err("pi denominator must be positive".into());
            }
            d
        };
        Ok(Self {
            pi: numerator / denominator,
            radians: BigRational::zero(),
        })
    }

    fn divided_by(&self, denominator: i64) -> Result<Self, String> {
        if denominator == 0 {
            return Err("division by zero".into());
        }
        let divisor = BigRational::from_integer(BigInt::from(denominator));
        Ok(Self {
            pi: &self.pi / &divisor,
            radians: &self.radians / &divisor,
        })
    }

    /// A relative RZ phase is periodic in 2π when *global phase is ignored*.
    /// For exact rational radians, a + bπ = 2kπ implies a=0, b=2k,
    /// since π is irrational. This is not an f64 approximation.
    fn equivalent_rz_up_to_global_phase(
        &self,
        other: &Self,
        source: SourceSemantics,
    ) -> Conclusion {
        if source == SourceSemantics::RoundedNumericUncertified {
            return Conclusion::Unknown;
        }
        let difference = self.clone() - other.clone();
        let modulus = BigInt::from(2) * difference.pi.denom();
        let pi_remainder = difference.pi.numer().mod_floor(&modulus);
        if difference.radians.is_zero() && pi_remainder.is_zero() {
            Conclusion::EquivalentProof
        } else {
            Conclusion::DifferentProof
        }
    }
}

impl Add for ExactAngle {
    type Output = Self;
    fn add(self, rhs: Self) -> Self::Output {
        Self {
            pi: self.pi + rhs.pi,
            radians: self.radians + rhs.radians,
        }
    }
}

impl Neg for ExactAngle {
    type Output = Self;
    fn neg(self) -> Self::Output {
        Self {
            pi: -self.pi,
            radians: -self.radians,
        }
    }
}

impl Sub for ExactAngle {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self::Output {
        self + (-rhs)
    }
}

/// Exactly parse a bounded decimal/scientific QASM literal to BigRational.
/// No binary float and no arbitrarily large input exponent allocation.
/// The bound rejects unsupported inputs rather than silently rounding.
fn parse_decimal_rational(literal: &str) -> Result<BigRational, String> {
    let literal = literal.trim().to_ascii_lowercase();
    let (mantissa, exponent) = match literal.split_once('e') {
        Some((m, e)) => {
            if e.contains('e') {
                return Err("multiple exponent markers".into());
            }
            let parsed = e
                .parse::<i32>()
                .map_err(|_| "invalid exponent".to_string())?;
            (m, parsed)
        }
        None => (literal.as_str(), 0),
    };
    let (sign, unsigned) = if let Some(rest) = mantissa.strip_prefix('-') {
        (-1, rest)
    } else if let Some(rest) = mantissa.strip_prefix('+') {
        (1, rest)
    } else {
        (1, mantissa)
    };
    let (int, fract) = match unsigned.split_once('.') {
        Some((i, f)) => {
            if f.contains('.') {
                return Err("multiple decimal points".into());
            }
            (i, f)
        }
        None => (unsigned, ""),
    };
    if (int.is_empty() && fract.is_empty())
        || !int.bytes().chain(fract.bytes()).all(|c| c.is_ascii_digit())
        || int.len() + fract.len() > 512
    {
        return Err("unsupported decimal literal".into());
    }
    let combined = format!("{int}{fract}");
    let numerator = BigInt::parse_bytes(combined.as_bytes(), 10)
        .ok_or_else(|| "invalid decimal digits".to_string())?
        * BigInt::from(sign);
    let net_power = exponent
        .checked_sub(fract.len() as i32)
        .ok_or_else(|| "decimal exponent overflows supported range".to_string())?;
    if !(-256..=256).contains(&net_power) {
        return Err("decimal exponent exceeds bounded research domain".into());
    }
    let power = BigInt::from(10u8).pow(net_power.unsigned_abs());
    if net_power >= 0 {
        Ok(BigRational::from_integer(numerator * power))
    } else {
        Ok(BigRational::new(numerator, power))
    }
}

fn angle(s: &str) -> ExactAngle {
    ExactAngle::parse_source_token(s).unwrap()
}

#[test]
fn exact_qpe_decimal_additivity_and_half_angle_cancellation() {
    let cases = [
        (
            "-2.5802058126763807",
            "-2.5802058126763807",
            "-5.1604116253527614",
        ),
        (
            "1.6198837120072371",
            "-2.5802058126763807",
            "-0.9603221006691436",
        ),
        (
            "1.3499030933393643",
            "0.125",
            "1.4749030933393643",
        ),
    ];
    for (left, right, sum) in cases {
        let composite = angle(left) + angle(right);
        let single = angle(sum);
        assert_eq!(composite, single, "literal-angle additivity: {left},{right}");
        assert_eq!(
            composite.equivalent_rz_up_to_global_phase(
                &single,
                SourceSemantics::ExactQasmLiterals
            ),
            Conclusion::EquivalentProof
        );
        assert_eq!(
            composite.divided_by(2).unwrap() - single.divided_by(2).unwrap(),
            ExactAngle::zero()
        );
    }
}

#[test]
fn pi_fractions_preserve_exact_symbolic_arithmetic() {
    let eighth = angle("pi/8");
    assert_eq!(eighth.clone() + eighth, angle("pi/4"));
    assert_eq!(angle("-2*pi") + angle("3*pi/4"), angle("-5*pi/4"));
    assert_eq!(ExactAngle::pi_ratio(1, 4).unwrap(), angle("pi/4"));
    assert_ne!(angle("pi/4"), angle("0.7853981633974483"));
}

#[test]
fn rz_global_phase_equivalence_only_modulo_exact_two_pi() {
    let exact = SourceSemantics::ExactQasmLiterals;
    assert_eq!(
        angle("0").equivalent_rz_up_to_global_phase(&angle("2*pi"), exact),
        Conclusion::EquivalentProof
    );
    assert_eq!(
        angle("3*pi").equivalent_rz_up_to_global_phase(&angle("pi"), exact),
        Conclusion::EquivalentProof
    );
    assert_eq!(
        angle("0").equivalent_rz_up_to_global_phase(&angle("pi"), exact),
        Conclusion::DifferentProof
    );
    assert_eq!(
        angle("pi/8").equivalent_rz_up_to_global_phase(&angle("-15*pi/8"), exact),
        Conclusion::EquivalentProof
    );
}

#[test]
fn preserve_near_identity_non_equivalent_controls_without_tolerance() {
    let exact = SourceSemantics::ExactQasmLiterals;
    for delta in ["0.000001", "0.0001", "0.001", "0.01", "0.2", "3"] {
        assert_eq!(
            angle("0").equivalent_rz_up_to_global_phase(&angle(delta), exact),
            Conclusion::DifferentProof,
            "non-equivalent RZ delta={delta}"
        );
    }
    assert_ne!(angle("0.125"), angle("0.126"));
}

#[test]
fn mixed_decimal_and_pi_bases_cannot_cancel_approximately() {
    assert_eq!(
        (angle("0.7853981633974483") - angle("pi/4"))
            .equivalent_rz_up_to_global_phase(
                &ExactAngle::zero(),
                SourceSemantics::ExactQasmLiterals
            ),
        Conclusion::DifferentProof
    );
    assert_eq!(
        angle("2*pi").equivalent_rz_up_to_global_phase(
            &angle("6.283185307179586"),
            SourceSemantics::ExactQasmLiterals
        ),
        Conclusion::DifferentProof
    );
}

#[test]
fn binary_rounded_numeric_input_is_explicitly_unproven() {
    let sum = angle("-2.5802058126763807") + angle("-2.5802058126763807");
    assert_eq!(
        sum.equivalent_rz_up_to_global_phase(
            &angle("-5.1604116253527614"),
            SourceSemantics::RoundedNumericUncertified
        ),
        Conclusion::Unknown
    );
    // Even a mathematical exact-decimal non-equality is not claimed as a
    // numeric input-semantic certificate until rounding is specified.
    assert_eq!(
        angle("0.125").equivalent_rz_up_to_global_phase(
            &angle("0.126"),
            SourceSemantics::RoundedNumericUncertified
        ),
        Conclusion::Unknown
    );
}

#[test]
fn arbitrary_precision_exceeds_old_i64_and_cf_denominator_caps() {
    let exact = angle("-2.5802058126763807");
    assert!(exact.radians.denom() > &BigInt::from(1_000_000_000u64));
    let mut accumulated = ExactAngle::zero();
    for _ in 0..1024 {
        accumulated = accumulated + exact.clone();
    }
    assert_eq!(accumulated, ExactAngle {
        radians: &exact.radians * BigRational::from_integer(BigInt::from(1024)),
        pi: BigRational::zero(),
    });
    assert_eq!(
        accumulated - exact.clone() - (0..1023).fold(
            ExactAngle::zero(), |sum, _| sum + exact.clone()
        ),
        ExactAngle::zero()
    );
}

#[test]
fn exact_exponent_and_negative_fraction_parsing() {
    assert_eq!(angle("1.25e-3"), angle("0.00125"));
    assert_eq!(angle("+3*pi/4"), angle("0.75*pi"));
    assert_eq!(angle("-pi/8"), -angle("pi/8"));
    assert_eq!(angle("000.000000"), ExactAngle::zero());
}

#[test]
fn reject_unrecognised_qasm_expressions_and_budget_overflow() {
    for invalid in ["1+pi/8", "sqrt(2)", "pi*pi", "pi/0", "abc", "1e99999", "1.2.3"] {
        assert!(ExactAngle::parse_source_token(invalid).is_err(), "{invalid}");
    }
    assert!(angle("pi/8").divided_by(0).is_err());
    assert!(ExactAngle::pi_ratio(1, 0).is_err());
}

#[test]
fn deterministic_large_integer_addition_is_exact() {
    for a in -12i64..=12 {
        for b in -12i64..=12 {
            let a_token = format!("{a}.12345678901234567");
            let b_token = format!("{b}.12345678901234567");
            let a_exact = angle(&a_token);
            let b_exact = angle(&b_token);
            assert_eq!(
                (a_exact.clone() + b_exact.clone()) - a_exact - b_exact,
                ExactAngle::zero()
            );
        }
    }
    println!("QOO134_EXACT_ANGLE_MODEL_PASS: 10 tests; research domain only");
}
