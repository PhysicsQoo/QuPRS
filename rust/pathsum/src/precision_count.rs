//! Exact-rational WMC stdout transport and printed-rounding intervals.
//!
//! This module does NOT certify source-angle, WMC arithmetic, or RR error.
//! An interval verdict describes only the observed solver's printed digits.

use anyhow::{anyhow, Result};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, Zero};
use std::str::FromStr;

const LIMIT: usize = 8192;
const MAX_EXP: i32 = 2048;
const LABELS: [&str; 8] = [
    "c s exact double prec-sci", "c s exact arb cpx",
    "c s exact half float", "c s exact single float",
    "c s exact double float", "c s exact quadruple float",
    "c s exact octuple float", "c s exact arb frac",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PrintedCount {
    pub real: BigRational,
    pub imag: BigRational,
    pub real_half_unit: BigRational,
    pub imag_half_unit: BigRational,
    pub format_name: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PrintedVerdict {
    Equivalent,
    NotEquivalent,
    UnknownResolution,
    UnknownOvershoot,
}

fn power_ten(n: i32) -> Result<BigRational> {
    if n.abs() > MAX_EXP {
        return Err(anyhow!("Exponent outside bounded transport range"));
    }
    let ten = BigInt::from(10);
    if n >= 0 {
        Ok(BigRational::from_integer(ten.pow(n as u32)))
    } else {
        Ok(BigRational::new(BigInt::from(1), ten.pow((-n) as u32)))
    }
}

fn component(text: &str) -> Result<(BigRational, BigRational)> {
    if text.len() > LIMIT {
        return Err(anyhow!("Count token too long"));
    }
    if let Some((numerator, denominator)) = text.split_once('/') {
        let n = BigInt::from_str(numerator)?;
        let d = BigInt::from_str(denominator)?;
        if d.is_zero() { return Err(anyhow!("Zero denominator")); }
        if denominator.contains('/') { return Err(anyhow!("Malformed rational")); }
        return Ok((BigRational::new(n, d), BigRational::zero()));
    }

    let (mantissa, exponent) = if let Some(i) = text.find(|c| c == 'e' || c == 'E') {
        (&text[..i], text[i + 1..].parse::<i32>()?)
    } else { (text, 0) };
    if exponent.abs() > MAX_EXP { return Err(anyhow!("Count exponent too large")); }

    let mantissa = mantissa.strip_prefix('+').unwrap_or(mantissa);
    let unsigned = mantissa.strip_prefix('-').unwrap_or(mantissa);
    if unsigned.is_empty() || unsigned.chars().filter(|&c| c == '.').count() > 1 {
        return Err(anyhow!("Malformed decimal count"));
    }
    if !unsigned.chars().all(|c| c.is_ascii_digit() || c == '.') {
        return Err(anyhow!("Invalid decimal count"));
    }
    let digit_string = unsigned.replace('.', "");
    if digit_string.is_empty() { return Err(anyhow!("Missing decimal digits")); }
    let digits = unsigned.split_once('.').map(|(_, frac)| frac.len()).unwrap_or(0);
    let mut n = BigInt::from_str(&digit_string)?;
    if mantissa.starts_with('-') { n = -n; }
    if n.is_zero() {
        return Ok((BigRational::zero(), BigRational::zero()));
    }
    let decimal_shift = exponent - digits as i32;
    let value = BigRational::from_integer(n) * power_ten(decimal_shift)?;
    let half = BigRational::from_integer(BigInt::from(5))
        * power_ten(decimal_shift - 1)?;
    Ok((value, half))
}

pub fn parse_line(line: &str) -> Result<Option<PrintedCount>> {
    let Some(prefix) = LABELS.iter().find(|prefix| {
        line.strip_prefix(**prefix)
            .is_some_and(|tail| tail.is_empty() || tail.starts_with(char::is_whitespace))
    }) else { return Ok(None); };
    let value = line.strip_prefix(*prefix).unwrap_or("");
    let clean: String = value.chars().filter(|c| !c.is_whitespace()).collect::<String>()
        .replace("+-", "-");
    if clean.is_empty() { return Err(anyhow!("Empty solver count")); }
    let (real, imag, real_half_unit, imag_half_unit) = if let Some(body) = clean.strip_suffix('i') {
        let split = body.char_indices().rev().find(|&(j, c)| {
            j > 0 && (c == '+' || c == '-') && !matches!(body.as_bytes()[j - 1], b'e' | b'E')
        }).map(|(j, _)| j);
        let (r, i) = split.map(|j| (&body[..j], &body[j..])).unwrap_or(("0", body));
        let imaginary = match i { "+" => "1", "-" => "-1", _ => i };
        let (real, ru) = component(r)?;
        let (imag, iu) = component(imaginary)?;
        (real, imag, ru, iu)
    } else {
        let (real, ru) = component(&clean)?;
        (real, BigRational::zero(), ru, BigRational::zero())
    };
    Ok(Some(PrintedCount {
        real, imag, real_half_unit, imag_half_unit, format_name: prefix.to_string(),
    }))
}

pub fn parse_stdout(stdout: &str) -> Result<PrintedCount> {
    let mut found: Option<PrintedCount> = None;
    for line in stdout.lines() {
        if let Some(value) = parse_line(line)? {
            if found.as_ref().is_some_and(|prev| {
                prev.real != value.real || prev.imag != value.imag
            }) {
                return Err(anyhow!("Solver output has conflicting exact-decimal counts"));
            }
            if found.is_none() { found = Some(value); }
        }
    }
    found.ok_or_else(|| anyhow!("No recognizable high-precision solver count"))
}

pub fn classify(
    count: &PrintedCount, normalization_twice_log2: i32, distance: &str,
) -> Result<PrintedVerdict> {
    if normalization_twice_log2.abs() > MAX_EXP {
        return Err(anyhow!("Normalization outside bounded precision transport"));
    }
    let (eps, _) = component(distance)?;
    let zero = BigRational::zero();
    let one = BigRational::from_integer(BigInt::from(1));
    if eps <= zero || eps >= one {
        return Err(anyhow!("Distance tolerance must be in (0,1)"));
    }
    let normal_sq = BigRational::from_integer(BigInt::from(2))
        .pow(normalization_twice_log2);
    let threshold = &normal_sq * (&one - &eps * &eps);
    let re = count.real.abs();
    let im = count.imag.abs();
    let min_re = (&re - &count.real_half_unit).max(BigRational::zero());
    let min_im = (&im - &count.imag_half_unit).max(BigRational::zero());
    let max_re = &re + &count.real_half_unit;
    let max_im = &im + &count.imag_half_unit;
    let low = &min_re * &min_re + &min_im * &min_im;
    let high = &max_re * &max_re + &max_im * &max_im;
    if low > normal_sq { Ok(PrintedVerdict::UnknownOvershoot) }
    else if high < threshold { Ok(PrintedVerdict::NotEquivalent) }
    else if low >= threshold { Ok(PrintedVerdict::Equivalent) }
    else { Ok(PrintedVerdict::UnknownResolution) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_sub_f64_solver_digits_and_normalization() {
        let original = parse_stdout("c s exact quadruple float 1.00000000e+00 + 0.00000000e+00i").unwrap();
        let candidate = parse_stdout(
            "c s exact octuple float 9.9999999999999994746875000000000000000117e-01 + 0e+00i"
        ).unwrap();
        assert_eq!(classify(&original, 0, "1e-8").unwrap(), PrintedVerdict::UnknownResolution);
        assert_eq!(classify(&candidate, 0, "1e-8").unwrap(), PrintedVerdict::NotEquivalent);
        assert_eq!(classify(&candidate, 0, "2e-8").unwrap(), PrintedVerdict::Equivalent);
        let scaled = PrintedCount {
            real: &candidate.real * BigRational::from_integer(BigInt::from(4)),
            imag: &candidate.imag * BigRational::from_integer(BigInt::from(4)),
            real_half_unit: &candidate.real_half_unit * BigRational::from_integer(BigInt::from(4)),
            imag_half_unit: &candidate.imag_half_unit * BigRational::from_integer(BigInt::from(4)),
            format_name: candidate.format_name.clone(),
        };
        assert_eq!(classify(&scaled, 4, "1e-8").unwrap(), PrintedVerdict::NotEquivalent);
    }

    #[test]
    fn overshoot_invalid_count_and_conflicting_lines_fail_closed() {
        let count = parse_stdout(
            "c s exact octuple float 1.0000000000000000525312499999999999999988e+00 + 0e+00i"
        ).unwrap();
        assert_eq!(classify(&count, 0, "1e-8").unwrap(), PrintedVerdict::UnknownOvershoot);
        assert!(parse_stdout(
            "c s exact arb frac 3/2 + 1/4i\nc s exact arb frac 7/2 + 1/4i"
        ).is_err());
        for value in ["nan", "inf", "1e9999", "1/0"] {
            assert!(parse_stdout(&format!("c s exact quadruple float {value}")).is_err());
        }
    }

    #[test]
    fn all_ganak_printed_format_names_recognized() {
        for name in ["half", "single", "double", "quadruple", "octuple"] {
            let input = format!("c s exact {name} float 1.0e+00 + 0e+00i");
            let result = parse_stdout(&input).unwrap();
            assert_eq!(result.real, BigRational::from_integer(BigInt::from(1)));
        }
    }
}
