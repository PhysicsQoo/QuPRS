// src/rational.rs
#![allow(dead_code)]
use std::fmt;
use std::ops::*;
use std::collections::BTreeMap;

// ============================================================================
// 1. Rational (Phase Arithmetic: [0, 1) Interval)
// ============================================================================
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Rational {
    pub numer: i64,
    pub denom: i64,
}

impl Rational {
    pub fn new(numer: i64, denom: i64) -> Self {
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

    pub fn zero() -> Self { Self::new(0, 1) }
    pub fn is_zero(&self) -> bool { self.numer == 0 }
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
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = (n1 * d2 + n2 * d1).rem_euclid(d1 * d2);
        if new_numer == 0 { return Self::zero(); }
        
        let common = gcd_i128(new_numer, d1 * d2);
        Rational { 
            numer: (new_numer / common) as i64, 
            denom: ((d1 * d2) / common) as i64 
        }
    }
}

impl Sub for Rational {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = (n1 * d2 - n2 * d1).rem_euclid(d1 * d2);
        if new_numer == 0 { return Self::zero(); }
        
        let common = gcd_i128(new_numer, d1 * d2);
        Rational { 
            numer: (new_numer / common) as i64, 
            denom: ((d1 * d2) / common) as i64 
        }
    }
}

impl Mul<i64> for Rational {
    type Output = Self;
    fn mul(self, rhs: i64) -> Self {
        Self::new(self.numer * rhs, self.denom)
    }
}

impl Div<i64> for Rational {
    type Output = Self;
    fn div(self, rhs: i64) -> Self {
        Self::new(self.numer, self.denom * rhs)
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
    pub fn new(numer: i64, denom: i64) -> Self {
        if denom == 0 { panic!("Zero denominator in FreeRational"); }
        let mut n = numer;
        let mut d = denom;
        
        if d < 0 { n = -n; d = -d; }
        if n == 0 { return FreeRational { numer: 0, denom: 1 }; }
        
        let common = gcd(n.abs(), d);
        FreeRational { numer: n / common, denom: d / common }
    }
    
    pub fn zero() -> Self { FreeRational { numer: 0, denom: 1 } }
    pub fn is_zero(&self) -> bool { self.numer == 0 }
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
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = n1 * d2 + n2 * d1;
        let new_denom = d1 * d2;
        
        if new_numer == 0 { return Self::zero(); }
        
        let common = gcd_i128(new_numer.abs(), new_denom);
        FreeRational { 
            numer: (new_numer / common) as i64, 
            denom: (new_denom / common) as i64 
        }
    }
}

impl Sub for FreeRational {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = n1 * d2 - n2 * d1;
        let new_denom = d1 * d2;
        
        if new_numer == 0 { return Self::zero(); }
        
        let common = gcd_i128(new_numer.abs(), new_denom);
        FreeRational { 
            numer: (new_numer / common) as i64, 
            denom: (new_denom / common) as i64 
        }
    }
}

impl Mul<i64> for FreeRational {
    type Output = Self;
    fn mul(self, rhs: i64) -> Self {
        Self::new(self.numer * rhs, self.denom)
    }
}

impl Div<i64> for FreeRational {
    type Output = Self;
    fn div(self, rhs: i64) -> Self {
        if rhs == 0 { panic!("Division by zero"); }
        Self::new(self.numer, self.denom * rhs)
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
    pub symbols: BTreeMap<u32, FreeRational>,
}

/// 核心邏輯集中區
impl PhaseCoeff {
    pub fn new_constant(constant: Rational) -> Self {
        Self { constant, symbols: BTreeMap::new() }
    }

    pub fn new_symbolic(symbol_id: u32, weight: FreeRational) -> Self {
        let mut symbols = BTreeMap::new();
        symbols.insert(symbol_id, weight);
        Self { constant: Rational::zero(), symbols }
    }

    pub fn is_zero(&self) -> bool {
        self.constant.is_zero() && self.symbols.is_empty()
    }

    // --- Inspection Helpers (Missing in previous version) ---

    pub fn is_pure_half(&self) -> bool {
        self.constant.numer == 1 && self.constant.denom == 2 && self.symbols.is_empty()
    }

    pub fn is_pure_quarter(&self) -> bool {
        self.constant.numer == 1 && self.constant.denom == 4 && self.symbols.is_empty()
    }

    pub fn is_pure_three_quarters(&self) -> bool {
        self.constant.numer == 3 && self.constant.denom == 4 && self.symbols.is_empty()
    }

    pub fn is_pure_fraction(&self, numer: i64, denom: i64) -> bool {
        let target = Rational::new(numer, denom);
        self.constant == target && self.symbols.is_empty()
    }

    // --- 運算邏輯 (Internal Logic) ---

    pub fn add_logic(&mut self, rhs: &Self) {
        self.constant += rhs.constant;
        for (sym_id, weight) in &rhs.symbols {
            let entry = self.symbols.entry(*sym_id).or_insert(FreeRational::zero());
            *entry += *weight;
            if entry.is_zero() {
                self.symbols.remove(sym_id);
            }
        }
    }

    pub fn sub_logic(&mut self, rhs: &Self) {
        self.constant -= rhs.constant;
        for (sym_id, weight) in &rhs.symbols {
            let entry = self.symbols.entry(*sym_id).or_insert(FreeRational::zero());
            *entry -= *weight;
            if entry.is_zero() {
                self.symbols.remove(sym_id);
            }
        }
    }

    pub fn mul_scalar_logic(&mut self, rhs: i64) {
        if rhs == 0 {
            self.constant = Rational::zero();
            self.symbols.clear();
            return;
        }
        self.constant *= rhs;
        self.symbols.retain(|_, weight| {
            *weight *= rhs;
            !weight.is_zero()
        });
    }

    pub fn div_scalar_logic(&mut self, rhs: i64) {
        if rhs == 0 { panic!("Division by zero in PhaseCoeff"); }
        self.constant /= rhs;
        self.symbols.retain(|_, weight| {
            *weight /= rhs;
            !weight.is_zero()
        });
    }
}

// --- Trait Wiring ---

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


// Helper functions
fn gcd(mut a: i64, mut b: i64) -> i64 {
    while b != 0 { let t = b; b = a % b; a = t; }
    a
}

fn gcd_i128(mut a: i128, mut b: i128) -> i128 {
    while b != 0 { let t = b; b = a % b; a = t; }
    a
}