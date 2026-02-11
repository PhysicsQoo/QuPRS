// src/rational.rs
use std::fmt;
use std::ops::*;
use num_integer::Integer;
use num_traits::Zero;


#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash)]
pub struct Rational {
    pub numer: i64,
    pub denom: i64,
}

impl Rational {
    pub fn new(numer: i64, denom: i64) -> Self {
        if denom == 0 { panic!("Zero denominator"); }
        let mut n = numer; let mut d = denom;
        if d < 0 { n = -n; d = -d; }
        let common = n.abs().gcd(&d);
        Rational { numer: n / common, denom: d / common }
    }
}

impl fmt::Display for Rational {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.denom == 1 { write!(f, "{}", self.numer) } 
        else { write!(f, "{}/{}", self.numer, self.denom) }
    }
}

impl Add for Rational {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        let n1 = self.numer as i128; let d1 = self.denom as i128;
        let n2 = rhs.numer as i128; let d2 = rhs.denom as i128;
        let new_numer = n1 * d2 + n2 * d1;
        let new_denom = d1 * d2;
        let common = new_numer.abs().gcd(&new_denom);
        Rational { numer: (new_numer / common) as i64, denom: (new_denom / common) as i64 }
    }
}

impl AddAssign for Rational {
    fn add_assign(&mut self, rhs: Self) { *self = *self + rhs; }
}

impl Zero for Rational {
    fn zero() -> Self { Rational { numer: 0, denom: 1 } }
    fn is_zero(&self) -> bool { self.numer == 0 }
}

pub fn from_f64_phase(val: f64, epsilon: f64) -> Option<Rational> {
    let pi = std::f64::consts::PI;
    let target = val / pi;
    let max_iterations = 50;
    
    let mut h_prev = 0i64;
    let mut k_prev = 1i64;
    let mut h_curr = 1i64;
    let mut k_curr = 0i64;
    let mut x = target;

    for _ in 0..max_iterations {
        if x.is_infinite() || x.is_nan() { break; }
        let a = x.floor() as i64;
        
        let h_next = a.saturating_mul(h_curr).saturating_add(h_prev);
        let k_next = a.saturating_mul(k_curr).saturating_add(k_prev);

        let approx = h_next as f64 / k_next as f64;
        if (approx - target).abs() < epsilon {
            return Some(Rational::new(h_next, k_next));
        }

        h_prev = h_curr;
        k_prev = k_curr;
        h_curr = h_next;
        k_curr = k_next;

        let rem = x - a as f64;
        if rem.abs() < 1e-15 {
             return Some(Rational::new(h_curr, k_curr));
        }
        x = 1.0 / rem;
        
        if k_curr > 1_000_000 { break; }
    }
    None
}

// --- 測試模組 (proptest) ---

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // 定義一個"小數值"的有理數生成器，專門用於測試結合律等會讓數值膨脹的性質
    prop_compose! {
        fn any_rational_small()(n in any::<i16>(), d in 1..i16::MAX) -> Rational {
            Rational::new(n as i64, d as i64)
        }
    }

    // 一般測試可以使用較大範圍 (i32)，只要不涉及多次連乘
    prop_compose! {
        fn any_rational()(n in any::<i32>(), d in 1..i32::MAX) -> Rational {
            Rational::new(n as i64, d as i64)
        }
    }

    proptest! {
        #[test]
        fn test_rational_addition_commutativity(a in any_rational(), b in any_rational()) {
            // 交換律只涉及兩數運算，i32 是安全的
            // (a + b) 分母約為 d1*d2 < 10^18 (i64 max)
            prop_assert_eq!(a + b, b + a);
        }
        
        #[test]
        fn test_reconstruct_pi_fractions(n in -100..100i64, d in 1..100i64) {
             let target_rational = Rational::new(n, d);
             let pi = std::f64::consts::PI;
             let val = (target_rational.numer as f64 / target_rational.denom as f64) * pi;
             
             if let Some(recovered) = from_f64_phase(val, 1e-9) {
                 prop_assert_eq!(recovered, target_rational);
             }
        }
    }
}