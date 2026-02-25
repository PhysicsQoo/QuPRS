// src/rational.rs
#![allow(dead_code)]
use rustc_hash::FxHashMap;
use std::fmt;
use std::ops::*;
use num_integer::Integer;
use num_traits::Zero;

// ==========================================
// 1. Rational (受限於 [0, 1) 區間)
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

        // 1. 確保分母為正
        if d < 0 {
            n = -n;
            d = -d;
        }

        // 2. 限制值域在 [0, 1) 之間 (Modulo 1)
        // 例如 -1.rem_euclid(4) = 3
        n = n.rem_euclid(d);

        // 3. 處理分子為 0 的情況
        if n == 0 { return Rational { numer: 0, denom: 1 }; }

        // 4. GCD 約分
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
        
        // 在 i128 空間執行 [0, 1) 的同餘限制
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

// 相位 * 整數 (純量乘法，用於邏輯展開)
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
// 2. PhaseCoeff (常數與符號混合係數)
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

    /// 檢查是否是純數值的 1/4 (對應 T 閘的正向相位)
    pub fn is_pure_quarter(&self) -> bool {
        self.constant.numer == 1 && 
        self.constant.denom == 4 && 
        self.symbols.values().all(|v| v.is_zero())
    }

    /// 檢查是否是純數值的 3/4
    pub fn is_pure_three_quarters(&self) -> bool {
        self.constant.numer == 3 && 
        self.constant.denom == 4 && 
        self.symbols.values().all(|v| v.is_zero())
    }

    /// 檢查是否是純數值的 -1/4 (對應 T^dag 閘的相位)
    /// 由於 Rational 實作了 modulo [0, 1)，-1/4 會自動等於 3/4
    pub fn is_pure_minus_quarter(&self) -> bool {
        self.is_pure_three_quarters() 
    }

    /// 通用型判斷函數：檢查是否為指定的純常數分數
    pub fn is_pure_fraction(&self, target_numer: i64, target_denom: i64) -> bool {
        let expected = Rational::new(target_numer, target_denom);
        self.constant == expected && self.symbols.values().all(|v| v.is_zero())
    }
}

impl AddAssign for PhaseCoeff {
    fn add_assign(&mut self, rhs: Self) {
        self.constant += rhs.constant;
        for (sym_id, weight) in rhs.symbols {
            let entry = self.symbols.entry(sym_id).or_insert_with(Rational::zero);
            *entry += weight;
            if entry.is_zero() {
                self.symbols.remove(&sym_id);
            }
        }
    }
}