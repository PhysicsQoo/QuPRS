//! Source-exact, shared-input fixtures for independent native Rust comparisons.
//! This isolated crate can be copied unchanged into a pinned pre-optimization
//! source checkout; only the underlying pathsum source differs.
use pathsum::pathsum::{Monomial, PhasePolynomial};
use pathsum::pathsum::mul_boolean_polys;
use pathsum::rational::{Angle, FreeRational};
use pathsum::{PhaseCoeff, Rational};
use rustc_hash::FxHashSet;

pub const TARGET: u32 = 0;

#[derive(Clone, Copy, Debug)]
pub enum Case {
    Clifford3,
    Decimal5,
    Mixed5,
    Symbolic5,
}

impl Case {
    pub const ALL: [Case; 4] = [
        Case::Clifford3, Case::Decimal5, Case::Mixed5, Case::Symbolic5
    ];
}

pub fn fixture(case: Case) -> (PhasePolynomial, FxHashSet<Monomial>) {
    // Twelve distinct phase terms contain TARGET. Their rest monomials
    // deliberately overlap XOR replacement variables to exercise canonical
    // Boolean-idempotence and source-key collisions in both implementations.
    let sources: [Monomial; 12] = [
        vec![0], vec![0, 3], vec![0, 4], vec![0, 5],
        vec![0, 6], vec![0, 2, 6], vec![0, 7], vec![0, 1, 8],
        vec![0, 1, 9], vec![0, 2, 10], vec![0, 6, 10], vec![0, 11],
    ];
    let decimal = Angle::from_qasm_str("0.12345678901234567890123456789")
        .expect("exact QASM decimal").to_phase_coeff();
    let symbolic = PhaseCoeff::new_symbolic(17, FreeRational::new(2, 3));
    let mut polynomial = PhasePolynomial::new();
    for (index, source) in sources.into_iter().enumerate() {
        let coeff = match case {
            Case::Clifford3 => PhaseCoeff::HALF,
            Case::Decimal5 => decimal.clone(),
            Case::Symbolic5 => symbolic.clone(),
            Case::Mixed5 => match index % 5 {
                0 => PhaseCoeff::HALF,
                1 => PhaseCoeff::QUARTER,
                2 => PhaseCoeff::new_constant(Rational::new(1, 8)),
                3 => decimal.clone(),
                _ => symbolic.clone(),
            },
        };
        polynomial.add_term(source, coeff);
    }
    // Include an unaffected phase term; ensure the transformation does not
    // rewrite terms that do not mention TARGET.
    polynomial.add_term(vec![14, 15], PhaseCoeff::QUARTER);
    let xor_terms: Vec<Monomial> = match case {
        Case::Clifford3 => vec![vec![1], vec![2], vec![1, 3]],
        _ => vec![vec![1], vec![2], vec![3], vec![4], vec![1, 3]],
    };
    let replacement: FxHashSet<Monomial> = xor_terms.into_iter().collect();
    assert_eq!(polynomial.terms.keys()
        .filter(|mono| mono.contains(&TARGET)).count(), 12);
    assert!((3..=5).contains(&replacement.len()));
    (polynomial, replacement)
}

/// Independent copy of the pre-optimization semantic path. Never use the
/// optimized helper here, otherwise correctness becomes circular.
pub fn legacy_substitute(
    polynomial: &mut PhasePolynomial,
    target: u32,
    replacement: &FxHashSet<Monomial>,
) {
    let mut removed: Vec<Monomial> = Vec::new();
    let mut additions: Vec<(FxHashSet<Monomial>, PhaseCoeff)> = Vec::new();
    for (monomial, coeff) in &polynomial.terms {
        if !monomial.contains(&target) { continue; }
        removed.push(monomial.clone());
        let rest: Monomial = monomial.iter()
            .copied().filter(|&id| id != target).collect();
        let rest_poly: FxHashSet<Monomial> = [rest].into_iter().collect();
        additions.push((mul_boolean_polys(&rest_poly, replacement), coeff.clone()));
    }
    for monomial in removed {
        polynomial.terms.remove(&monomial);
    }
    for (product, coeff) in additions {
        *polynomial += (&product, coeff);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_native_fixture_is_source_exact_and_matches_legacy() {
        for case in Case::ALL {
            let (mut candidate, replacement) = fixture(case);
            let mut expected = candidate.clone();
            legacy_substitute(&mut expected, TARGET, &replacement);
            candidate.substitute_var_with_poly(TARGET, &replacement);
            assert_eq!(candidate.terms, expected.terms, "{case:?}");
            assert!(candidate.terms.keys().all(|m| !m.contains(&TARGET)));
        }
    }
}
