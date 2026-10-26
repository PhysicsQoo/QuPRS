// src/rational.rs
#![allow(dead_code)]
use std::fmt;
use std::ops::*;
use std::collections::BTreeMap;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};

// ============================================================================
// 1. Rational (Phase Arithmetic: [0, 1) Interval)
// ============================================================================
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Rational {
    pub numer: i64,
    pub denom: i64,
}

impl Rational {
    pub const fn new(numer: i64, denom: i64) -> Self {
        if denom == 0 { panic!("Zero denominator in Rational"); }
        
        // 1. Normalize sign
        let (mut n, d) = if denom < 0 { (-numer, -denom) } else { (numer, denom) };
        
        // 2. Modulo 1 restriction -> [0, d)
        n = n.rem_euclid(d);
        
        if n == 0 { return Rational { numer: 0, denom: 1 }; }
        
        // 3. Reduce
        let common = gcd(n, d);
        Rational { numer: n / common, denom: d / common }
    }

    pub const ZERO: Self = Self::new(0, 1);
    pub const HALF: Self = Self::new(1, 2);
    pub const QUARTER: Self = Self::new(1, 4);
    pub const THREE_QUARTERS: Self = Self::new(3, 4);
    pub fn is_zero(&self) -> bool { self.numer == 0 }
    pub fn from_f64(val: f64) -> Self {
        let v = val.rem_euclid(1.0);
        let (n, d) = float_to_rational_continued_fraction(v);
        Self::new(n, d)
    }
}

impl fmt::Display for Rational {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.denom == 1 { write!(f, "{}", self.numer) } 
        else { write!(f, "{}/{}", self.numer, self.denom) }
    }
}

// --- Rational Operators ---

impl Add for Rational {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        let num = (self.numer as i128) * (rhs.denom as i128) + (rhs.numer as i128) * (self.denom as i128);
        let den = (self.denom as i128) * (rhs.denom as i128);
        let (n, d) = reduce_and_cap_i128(num, den);
        Self::new(n, d) 
    }
}

impl Sub for Rational {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        let num = (self.numer as i128) * (rhs.denom as i128) - (rhs.numer as i128) * (self.denom as i128);
        let den = (self.denom as i128) * (rhs.denom as i128);
        let (n, d) = reduce_and_cap_i128(num, den);
        Self::new(n, d)
    }
}

impl Mul<i64> for Rational {
    type Output = Self;
    fn mul(self, rhs: i64) -> Self {
        let (n, d) = reduce_and_cap_i128((self.numer as i128) * (rhs as i128), self.denom as i128);
        Self::new(n, d)
    }
}

impl Div<i64> for Rational {
    type Output = Self;
    fn div(self, rhs: i64) -> Self {
        let (n, d) = reduce_and_cap_i128(self.numer as i128, (self.denom as i128) * (rhs as i128));
        Self::new(n, d)
    }
}

impl AddAssign for Rational { fn add_assign(&mut self, rhs: Self) { *self = *self + rhs; } }
impl SubAssign for Rational { fn sub_assign(&mut self, rhs: Self) { *self = *self - rhs; } }
impl MulAssign<i64> for Rational { fn mul_assign(&mut self, rhs: i64) { *self = *self * rhs; } }
impl DivAssign<i64> for Rational { fn div_assign(&mut self, rhs: i64) { *self = *self / rhs; } }


// ============================================================================
// 2. FreeRational (Unrestricted Standard Arithmetic)
// ============================================================================
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FreeRational {
    pub numer: i64,
    pub denom: i64,
}

impl FreeRational {
    pub const fn new(numer: i64, denom: i64) -> Self {
        if denom == 0 { panic!("Zero denominator in FreeRational"); }
        let mut n = numer;
        let mut d = denom;
        
        if d < 0 { n = -n; d = -d; }
        if n == 0 { return FreeRational { numer: 0, denom: 1 }; }
        
        let common = gcd(n.abs(), d);
        FreeRational { numer: n / common, denom: d / common }
    }
    
    pub const ZERO: Self = Self::new(0, 1);
    pub const HALF: Self = Self::new(1, 2);
    pub const QUARTER: Self = Self::new(1, 4);
    pub const THREE_QUARTERS: Self = Self::new(3, 4);
    pub fn is_zero(&self) -> bool { self.numer == 0 }
    pub fn from_f64(val: f64) -> Self {
        let sign = if val < 0.0 { -1 } else { 1 };
        let v = val.abs();
        let (n, d) = float_to_rational_continued_fraction(v);
        Self::new(n * sign, d)
    }
}

impl fmt::Display for FreeRational {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.denom == 1 { write!(f, "{}", self.numer) } 
        else { write!(f, "{}/{}", self.numer, self.denom) }
    }
}

// --- FreeRational Operators ---

impl Add for FreeRational {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        let num = (self.numer as i128) * (rhs.denom as i128) + (rhs.numer as i128) * (self.denom as i128);
        let den = (self.denom as i128) * (rhs.denom as i128);
        let (n, d) = reduce_and_cap_i128(num, den);
        Self::new(n, d)
    }
}

impl Sub for FreeRational {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        let num = (self.numer as i128) * (rhs.denom as i128) - (rhs.numer as i128) * (self.denom as i128);
        let den = (self.denom as i128) * (rhs.denom as i128);
        let (n, d) = reduce_and_cap_i128(num, den);
        Self::new(n, d)
    }
}

impl Mul<i64> for FreeRational {
    type Output = Self;
    fn mul(self, rhs: i64) -> Self {
        let (n, d) = reduce_and_cap_i128((self.numer as i128) * (rhs as i128), self.denom as i128);
        Self::new(n, d)
    }
}

impl Div<i64> for FreeRational {
    type Output = Self;
    fn div(self, rhs: i64) -> Self {
        if rhs == 0 { panic!("Division by zero"); }
        let (n, d) = reduce_and_cap_i128(self.numer as i128, (self.denom as i128) * (rhs as i128));
        Self::new(n, d)
    }
}

impl AddAssign for FreeRational { fn add_assign(&mut self, rhs: Self) { *self = *self + rhs; } }
impl SubAssign for FreeRational { fn sub_assign(&mut self, rhs: Self) { *self = *self - rhs; } }
impl MulAssign<i64> for FreeRational { fn mul_assign(&mut self, rhs: i64) { *self = *self * rhs; } }
impl DivAssign<i64> for FreeRational { fn div_assign(&mut self, rhs: i64) { *self = *self / rhs; } }


// ============================================================================
// 3. PhaseCoeff (Mixed Algebraic Structure)
// ============================================================================
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PhaseCoeff {
    pub constant: Rational,
    /// Exact rational radians divided by pi in the phase exponent.
    /// None represents zero without allocating BigRational for Clifford paths.
    pub radians: Option<BigRational>,
    pub symbols: BTreeMap<u32, FreeRational>,
}

impl PhaseCoeff {
    pub const fn new_constant(constant: Rational) -> Self {
        Self { constant, radians: None, symbols: BTreeMap::new() }
    }

    pub fn new_symbolic(symbol_id: u32, weight: FreeRational) -> Self {
        let mut symbols = BTreeMap::new();
        symbols.insert(symbol_id, weight);
        Self { constant: Rational::ZERO, radians: None, symbols }
    }

    pub const ZERO: Self = Self::new_constant(Rational::ZERO);
    pub const HALF: Self = Self::new_constant(Rational::HALF);
    pub const QUARTER: Self = Self::new_constant(Rational::QUARTER);
    pub const THREE_QUARTERS: Self = Self::new_constant(Rational::THREE_QUARTERS);

    pub fn is_zero(&self) -> bool {
        self.constant.is_zero() && self.radians.is_none() && self.symbols.is_empty()
    }

    pub fn is_pure_half(&self) -> bool {
        self.constant.numer == 1 && self.constant.denom == 2 && self.radians.is_none() && self.symbols.is_empty()
    }

    pub fn is_pure_quarter(&self) -> bool {
        self.constant.numer == 1 && self.constant.denom == 4 && self.radians.is_none() && self.symbols.is_empty()
    }

    pub fn is_pure_three_quarters(&self) -> bool {
        self.constant.numer == 3 && self.constant.denom == 4 && self.radians.is_none() && self.symbols.is_empty()
    }

    pub fn is_pure_fraction(&self, numer: i64, denom: i64) -> bool {
        let target = Rational::new(numer, denom);
        self.constant == target && self.radians.is_none() && self.symbols.is_empty()
    }

    fn add_radians(&mut self, rhs: &Option<BigRational>, negative: bool) {
        if let Some(value) = rhs {
            let old = self.radians.take().unwrap_or_else(BigRational::zero);
            let new = if negative { old - value } else { old + value };
            if !new.is_zero() {
                self.radians = Some(new);
            }
        }
    }

    pub fn add_logic(&mut self, rhs: &Self) {
        self.constant += rhs.constant;
        self.add_radians(&rhs.radians, false);
        for (sym_id, weight) in &rhs.symbols {
            let entry = self.symbols.entry(*sym_id).or_insert(FreeRational::ZERO);
            *entry += *weight;
            if entry.is_zero() {
                self.symbols.remove(sym_id);
            }
        }
    }

    pub fn sub_logic(&mut self, rhs: &Self) {
        self.constant -= rhs.constant;
        self.add_radians(&rhs.radians, true);
        for (sym_id, weight) in &rhs.symbols {
            let entry = self.symbols.entry(*sym_id).or_insert(FreeRational::ZERO);
            *entry -= *weight;
            if entry.is_zero() {
                self.symbols.remove(sym_id);
            }
        }
    }

    pub fn mul_scalar_logic(&mut self, rhs: i64) {
        if rhs == 0 {
            self.constant = Rational::ZERO;
            self.radians = None;
            self.symbols.clear();
            return;
        }
        self.constant *= rhs;
        if let Some(rad) = &mut self.radians {
            *rad *= BigRational::from_integer(BigInt::from(rhs));
        }
        self.symbols.retain(|_, weight| {
            *weight *= rhs;
            !weight.is_zero()
        });
    }

    pub fn div_scalar_logic(&mut self, rhs: i64) {
        if rhs == 0 { panic!("Division by zero in PhaseCoeff"); }
        self.constant /= rhs;
        if let Some(rad) = &mut self.radians {
            *rad /= BigRational::from_integer(BigInt::from(rhs));
        }
        self.symbols.retain(|_, weight| {
            *weight /= rhs;
            !weight.is_zero()
        });
    }
}
impl fmt::Display for PhaseCoeff {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.constant)?;
        if let Some(rad) = &self.radians {
            write!(f, " + ({})/pi", rad)?;
        }
        
        for (var_id, weight) in &self.symbols {
            if weight.numer > 0 {
                write!(f, " + {}*var_{}", weight, var_id)?;
            } else {
                write!(f, " {}*var_{}", weight, var_id)?;
            }
        }
        Ok(())
    }
}

impl AddAssign for PhaseCoeff { fn add_assign(&mut self, rhs: Self) { self.add_logic(&rhs); } }
impl AddAssign<&PhaseCoeff> for PhaseCoeff { fn add_assign(&mut self, rhs: &Self) { self.add_logic(rhs); } }
impl Add for PhaseCoeff { type Output = Self; fn add(mut self, rhs: Self) -> Self { self += rhs; self } }

impl SubAssign for PhaseCoeff { fn sub_assign(&mut self, rhs: Self) { self.sub_logic(&rhs); } }
impl SubAssign<&PhaseCoeff> for PhaseCoeff { fn sub_assign(&mut self, rhs: &Self) { self.sub_logic(rhs); } }
impl Sub for PhaseCoeff { type Output = Self; fn sub(mut self, rhs: Self) -> Self { self -= rhs; self } }

impl MulAssign<i64> for PhaseCoeff { fn mul_assign(&mut self, rhs: i64) { self.mul_scalar_logic(rhs); } }
impl Mul<i64> for PhaseCoeff { type Output = Self; fn mul(mut self, rhs: i64) -> Self { self *= rhs; self } }

impl DivAssign<i64> for PhaseCoeff { fn div_assign(&mut self, rhs: i64) { self.div_scalar_logic(rhs); } }
impl Div<i64> for PhaseCoeff { type Output = Self; fn div(mut self, rhs: i64) -> Self { self /= rhs; self } }



/// Converts a floating-point number into a rational approximation (n/d).
/// Implements the Continued Fraction Algorithm for optimal precision.
fn float_to_rational_continued_fraction(val: f64) -> (i64, i64) {
    let epsilon = 1e-10;
    let max_denom = 1_000_000_000; // Safety limit to prevent overflow

    if val.abs() < epsilon { return (0, 1); }

    let mut x = val;
    let mut n0 = 0; let mut n1 = 1;
    let mut d0 = 1; let mut d1 = 0;

    // Iteratively calculate the convergents h_n/k_n
    loop {
        let a = x.floor() as i64;
        let n2 = a * n1 + n0;
        let d2 = a * d1 + d0;

        // Break if denominator exceeds safety limit
        if d2 > max_denom { break; }

        n0 = n1; n1 = n2;
        d0 = d1; d1 = d2;

        // Break if approximation is sufficiently close
        if (val - (n1 as f64 / d1 as f64)).abs() < epsilon { break; }

        let fractional = x - a as f64;
        if fractional < epsilon { break; }
        x = 1.0 / fractional;
    }

    (n1, d1)
}
// Helper: greatest common divisor
const fn gcd(mut a: i64, mut b: i64) -> i64 {
    while b != 0 { let t = b; b = a % b; a = t; }
    a
}

const fn gcd_i128(mut a: i128, mut b: i128) -> i128 {
    while b != 0 { let t = b; b = a % b; a = t; }
    a
}

fn reduce_and_cap_i128(n: i128, d: i128) -> (i64, i64) {
    if n == 0 { return (0, 1); }
    let mut num = n;
    let mut den = d;
    if den < 0 { num = -num; den = -den; }
    
    let common = gcd_i128(num.abs(), den);
    num /= common;
    den /= common;
    
    let max_safe = 100_000_000_000_000i128; 
    
    if num.abs() > max_safe || den > max_safe {
        let val = (num as f64) / (den as f64);
        let sign = if val < 0.0 { -1 } else { 1 };
        let (n_approx, d_approx) = float_to_rational_continued_fraction(val.abs());
        (n_approx * sign, d_approx)
    } else {
        (num as i64, den as i64)
    }
}
// ============================================================================
// 4. Angle (Continuous Algebraic Structure for Input Rotations)
// ============================================================================
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Angle {
    pub constant: FreeRational,
    /// Exact decimal-radian part of the source angle. Symbolic pi remains in constant.
    pub radians: Option<BigRational>,
    pub symbols: BTreeMap<u32, FreeRational>,
}

impl Angle {
    pub const fn new_constant(constant: FreeRational) -> Self {
        Self { constant, radians: None, symbols: BTreeMap::new() }
    }

    pub fn new_symbolic(symbol_id: u32, weight: FreeRational) -> Self {
        let mut symbols = BTreeMap::new();
        symbols.insert(symbol_id, weight);
        Self { constant: FreeRational::ZERO, radians: None, symbols }
    }

    pub const ZERO: Self = Self::new_constant(FreeRational::ZERO);
    pub const HALF: Self = Self::new_constant(FreeRational::HALF);
    pub const QUARTER: Self = Self::new_constant(FreeRational::QUARTER);
    pub const THREE_QUARTERS: Self = Self::new_constant(FreeRational::THREE_QUARTERS);

    pub fn to_phase_coeff(&self) -> PhaseCoeff {
        let mod1_constant = Rational::new(self.constant.numer, self.constant.denom);
        PhaseCoeff {
            constant: mod1_constant,
            radians: self.radians.clone(),
            symbols: self.symbols.clone(), 
        }
    }

    /// Parse supported OpenQASM 2 angle expressions without binary64 coercion.
    ///
    /// Decimal constants are exact rational radians; pi factors are symbolic.
    /// Unsupported/non-linear expressions and pi fractions exceeding the
    /// legacy fixed-width pi domain are errors rather than lossy approximations.
    pub fn from_qasm_str(input: &str) -> Result<Self, String> {
        let source = input.trim().to_lowercase().replace(' ', "");
        if source.is_empty() { return Err("Empty QASM angle".to_string()); }
        let expr = source.trim_start_matches('+');
        let (neg, expr) = if let Some(rest) = expr.strip_prefix('-') {
            (true, rest)
        } else { (false, expr) };
        if expr.is_empty() { return Err("Missing QASM angle".to_string()); }
        let parts: Vec<&str> = expr.split('/').collect();
        if parts.len() > 2 || parts.iter().any(|p| p.is_empty()) {
            return Err(format!("Unsupported QASM angle expression: {}", input));
        }
        let (num, num_pi) = Self::parse_product(parts[0])?;
        let (den, den_pi) = if parts.len() == 2 {
            Self::parse_product(parts[1])?
        } else { (BigRational::from_integer(BigInt::from(1)), false) };
        if den.is_zero() || den_pi {
            return Err(format!("Unsupported or zero QASM angle denominator: {}", input));
        }
        let mut factor = num / den;
        if neg { factor = -factor; }
        if num_pi {
            let n = factor.numer().to_i64()
                .ok_or_else(|| format!("QASM pi numerator outside exact i64 domain: {}", input))?;
            let d = factor.denom().to_i64()
                .ok_or_else(|| format!("QASM pi denominator outside exact i64 domain: {}", input))?;
            Ok(Self::new_constant(FreeRational::new(n, d)))
        } else if factor.is_zero() {
            Ok(Self::ZERO)
        } else {
            Ok(Self {
                constant: FreeRational::ZERO,
                radians: Some(factor),
                symbols: BTreeMap::new(),
            })
        }
    }

    fn parse_product(source: &str) -> Result<(BigRational, bool), String> {
        let mut coefficient = BigRational::from_integer(BigInt::from(1));
        let mut pi = false;
        for part in source.split('*') {
            if part == "pi" {
                if pi { return Err("Nonlinear pi*pi angle is unsupported".to_string()); }
                pi = true;
            } else {
                coefficient *= Self::parse_decimal(part)?;
            }
        }
        Ok((coefficient, pi))
    }

    fn parse_decimal(input: &str) -> Result<BigRational, String> {
        // Bounds are resource limits, not approximate rounding thresholds.
        if input.is_empty() || input.len() > 1024 {
            return Err(format!("Invalid/oversized decimal angle: {}", input));
        }
        let lowercase = input.to_ascii_lowercase();
        let mut parts = lowercase.split('e');
        let mantissa = parts.next().unwrap();
        let power: i32 = match parts.next() {
            Some(exponent) => exponent.parse()
                .map_err(|_| format!("Invalid decimal exponent: {}", input))?,
            None => 0,
        };
        if parts.next().is_some() {
            return Err(format!("Unsupported decimal exponent: {}", input));
        }
        let mut dot = mantissa.split('.');
        let whole = dot.next().unwrap();
        let fractional = dot.next().unwrap_or("");
        if dot.next().is_some() || (whole.is_empty() && fractional.is_empty())
            || !whole.chars().all(|c| c.is_ascii_digit())
            || !fractional.chars().all(|c| c.is_ascii_digit()) {
            return Err(format!("Invalid decimal angle: {}", input));
        }
        let joined = format!("{}{}", whole, fractional);
        let numerator = BigInt::parse_bytes(joined.as_bytes(), 10)
            .ok_or_else(|| format!("Invalid decimal digits: {}", input))?;
        // Preserve exact zero without allocating unbounded powers of ten.
        if numerator.is_zero() {
            return Ok(BigRational::zero());
        }
        // Bounded nonzero decimal input: avoid i32::abs overflow.
        if power < -512 || power > 512 {
            return Err(format!("Unsupported decimal exponent: {}", input));
        }
        let scale = fractional.len() as i32 - power;
        if scale > 1024 || scale < -1024 {
            return Err(format!("Decimal angle exceeds resource bound: {}", input));
        }
        let ten = BigInt::from(10);
        Ok(if scale > 0 {
            BigRational::new(numerator, ten.pow(scale as u32))
        } else {
            BigRational::from_integer(numerator * ten.pow((-scale) as u32))
        })
    }
}

impl Mul<i64> for Angle {
    type Output = Self;
    fn mul(mut self, rhs: i64) -> Self {
        if rhs == 0 { return Self::ZERO; }
        self.constant *= rhs;
        if let Some(rad) = &mut self.radians {
            *rad *= BigRational::from_integer(BigInt::from(rhs));
        }
        for weight in self.symbols.values_mut() {
            *weight *= rhs;
        }
        self
    }
}

impl std::ops::Sub for Angle {
    type Output = Self;
    fn sub(mut self, rhs: Self) -> Self {
        self.constant = self.constant - rhs.constant;
        if let Some(rad) = rhs.radians {
            let new = self.radians.take().unwrap_or_else(BigRational::zero) - rad;
            if !new.is_zero() { self.radians = Some(new); }
        }
        for (sym_id, weight) in rhs.symbols {
            let entry = self.symbols.entry(sym_id).or_insert(FreeRational::ZERO);
            *entry = *entry - weight;
            if entry.is_zero() {
                self.symbols.remove(&sym_id);
            }
        }
        self
    }
}

impl Div<i64> for Angle {
    type Output = Self;
    fn div(mut self, rhs: i64) -> Self {
        if rhs == 0 { panic!("Division by zero in Angle"); }
        self.constant /= rhs;
        if let Some(rad) = &mut self.radians {
            *rad /= BigRational::from_integer(BigInt::from(rhs));
        }
        for weight in self.symbols.values_mut() {
            *weight /= rhs;
        }
        self
    }
}