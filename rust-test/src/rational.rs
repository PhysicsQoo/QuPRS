// src/rational.rs
#![allow(dead_code)]
use rustc_hash::FxHashMap;
use std::fmt;
use std::ops::*;
use num_integer::Integer;
use num_traits::Zero;

// ==========================================
// 1. Rational (restricted to [0, 1) interval)
// ==========================================
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash)]
pub struct Rational {
    pub numer: i64,
    pub denom: i64,
}

impl Rational {
    pub fn new(numer: i64, denom: i64) -> Self {
        if denom == 0 { panic!("Zero denominator"); }
        let mut n = numer;
        let mut d = denom;

        // 1. Ensure denominator is positive
        if d < 0 {
            n = -n;
            d = -d;
        }

        // 2. Restrict value range to [0, 1) (Modulo 1)
        // Example: -1.rem_euclid(4) = 3
        n = n.rem_euclid(d);

        // 3. Handle case where numerator is zero
        if n == 0 { return Rational { numer: 0, denom: 1 }; }

        // 4. Reduce by GCD
        let common = n.gcd(&d);
        Rational { numer: n / common, denom: d / common }
    }
}

impl fmt::Display for Rational {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.denom == 1 { write!(f, "{}", self.numer) } 
        else { write!(f, "{}/{}", self.numer, self.denom) }
    }
}

impl Zero for Rational {
    fn zero() -> Self { Rational { numer: 0, denom: 1 } }
    fn is_zero(&self) -> bool { self.numer == 0 }
}

impl Add for Rational {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = n1 * d2 + n2 * d1;
        let new_denom = d1 * d2;
        
        // Perform modulo 1 restriction in i128 space to prevent overflow
        let mod_numer = new_numer.rem_euclid(new_denom);
        if mod_numer == 0 { return Rational { numer: 0, denom: 1 }; }
        
        let common = mod_numer.gcd(&new_denom);
        Rational { numer: (mod_numer / common) as i64, denom: (new_denom / common) as i64 }
    }
}

impl Sub for Rational {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        
        let new_numer = n1 * d2 - n2 * d1;
        let new_denom = d1 * d2;
        
        let mod_numer = new_numer.rem_euclid(new_denom);
        if mod_numer == 0 { return Rational { numer: 0, denom: 1 }; }
        
        let common = mod_numer.gcd(&new_denom);
        Rational { numer: (mod_numer / common) as i64, denom: (new_denom / common) as i64 }
    }
}

impl Mul<i64> for Rational {
    type Output = Self;
    fn mul(self, rhs: i64) -> Self {
        if rhs == 0 { return Rational { numer: 0, denom: 1 }; }
        let new_numer = (self.numer as i128) * (rhs as i128);
        let new_denom = self.denom as i128;

        let mod_numer = new_numer.rem_euclid(new_denom);
        if mod_numer == 0 { return Rational { numer: 0, denom: 1 }; }

        let common = mod_numer.gcd(&new_denom);
        Rational { numer: (mod_numer / common) as i64, denom: (new_denom / common) as i64 }
    }
}

impl AddAssign for Rational { fn add_assign(&mut self, rhs: Self) { *self = *self + rhs; } }
impl MulAssign<i64> for Rational { fn mul_assign(&mut self, rhs: i64) { *self = *self * rhs; } }

// ==========================================
// 2. PhaseCoeff
// ==========================================
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PhaseCoeff {
    pub constant: Rational,
    pub symbols: FxHashMap<u32, Rational>,
}

impl PhaseCoeff {
    pub fn new_constant(constant: Rational) -> Self {
        Self { constant, symbols: FxHashMap::default() }
    }

    pub fn new_symbolic(symbol_id: u32, weight: Rational) -> Self {
        let mut symbols = FxHashMap::default();
        symbols.insert(symbol_id, weight);
        Self { constant: Rational::zero(), symbols }
    }

    pub fn is_zero(&self) -> bool {
        self.constant.is_zero() && self.symbols.values().all(|v| v.is_zero())
    }

    pub fn is_pure_half(&self) -> bool {
        self.constant.numer == 1 && 
        self.constant.denom == 2 && 
        self.symbols.values().all(|v| v.is_zero())
    }

    /// Checks if the coefficient is exactly 1/4 (e.g., T gate phase)
    pub fn is_pure_quarter(&self) -> bool {
        self.constant.numer == 1 && 
        self.constant.denom == 4 && 
        self.symbols.values().all(|v| v.is_zero())
    }

    /// Checks if the coefficient is exactly 3/4
    pub fn is_pure_three_quarters(&self) -> bool {
        self.constant.numer == 3 && 
        self.constant.denom == 4 && 
        self.symbols.values().all(|v| v.is_zero())
    }

    /// Checks if the coefficient is exactly -1/4 (e.g., Tdg gate phase).
    /// Since Rational limits value to [0, 1), -1/4 is equivalent to 3/4.
    pub fn is_pure_minus_quarter(&self) -> bool {
        self.is_pure_three_quarters()
    }

    /// General function to check if it matches a specific pure fraction
    pub fn is_pure_fraction(&self, target_numer: i64, target_denom: i64) -> bool {
        let expected = Rational::new(target_numer, target_denom);
        self.constant == expected && self.symbols.values().all(|v| v.is_zero())
    }
}

// ==========================================
// Algebraic Operators for PhaseCoeff
// ==========================================

impl AddAssign for PhaseCoeff {
    fn add_assign(&mut self, rhs: Self) {
        self.constant += rhs.constant;
        for (sym_id, weight) in rhs.symbols {
            let entry = self.symbols.entry(sym_id).or_insert_with(Rational::zero);
            *entry += weight;
            
            // Remove the symbol if the weight becomes zero to maintain sparsity
            if entry.is_zero() {
                self.symbols.remove(&sym_id);
            }
        }
    }
}

impl Add for PhaseCoeff {
    type Output = Self;
    fn add(mut self, rhs: Self) -> Self {
        self += rhs;
        self
    }
}

impl SubAssign for PhaseCoeff {
    fn sub_assign(&mut self, rhs: Self) {
        self.constant = self.constant - rhs.constant;
        for (sym_id, weight) in rhs.symbols {
            let entry = self.symbols.entry(sym_id).or_insert_with(Rational::zero);
            *entry = *entry - weight;
            
            if entry.is_zero() {
                self.symbols.remove(&sym_id);
            }
        }
    }
}

impl Sub for PhaseCoeff {
    type Output = Self;
    fn sub(mut self, rhs: Self) -> Self {
        self -= rhs;
        self
    }
}

impl MulAssign<i64> for PhaseCoeff {
    fn mul_assign(&mut self, rhs: i64) {
        // If multiplied by 0, the entire phase becomes zero
        if rhs == 0 {
            self.constant = Rational::zero();
            self.symbols.clear();
            return;
        }

        self.constant *= rhs;
        
        // Multiply all symbolic weights by the scalar
        // retain() will keep elements where the closure returns true
        self.symbols.retain(|_, weight| {
            *weight *= rhs;
            !weight.is_zero()
        });
    }
}

impl Mul<i64> for PhaseCoeff {
    type Output = Self;
    fn mul(mut self, rhs: i64) -> Self {
        self *= rhs;
        self
    }
}

// Support commutative scalar multiplication (e.g., 2 * phase)
impl Mul<PhaseCoeff> for i64 {
    type Output = PhaseCoeff;
    fn mul(self, rhs: PhaseCoeff) -> PhaseCoeff {
        rhs * self
    }
}