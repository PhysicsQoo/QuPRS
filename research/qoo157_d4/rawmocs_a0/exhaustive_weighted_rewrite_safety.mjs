#!/usr/bin/env node
// RaWMoCS A0f: independent tiny-universe exhaustive exact complex-WMC rewrite audit.
// 2 variables, 8 different non-tautological clauses, all 2^8 CNF clause subsets,
// and all 4^4 combinations of literal weights from {0, 1, -1, i}.
// Uses exact Gaussian INTEGER arithmetic, not floating point, external solvers,
// any previous RaWMoCS oracle, or timing/performance comparisons.

"use strict";

const VALUES = [[0, 0], [1, 0], [-1, 0], [0, 1]];
const CLAUSES = [[1], [-1], [2], [-2], [1, 2], [1, -2], [-1, 2], [-1, -2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
const mul = (a, b) => [a[0] * b[0] - a[1] * b[1],
                       a[0] * b[1] + a[1] * b[0]];
const equal = (a, b) => a[0] === b[0] && a[1] === b[1];
const satisfyClause = (clause, bits) =>
  clause.some(literal => (
    ((bits >> (Math.abs(literal) - 1)) & 1) === (literal > 0 ? 1 : 0)
  ));
const satisfyFormula = (formula, bits) =>
  formula.every(clause => satisfyClause(clause, bits));
function assertExact(actual, expected, what, mask, weights) {
  if (!equal(actual, expected)) {
    throw new Error(JSON.stringify({what, mask, weights, actual, expected}));
  }
}
const stats = {
  status: "RAWMOCS_A0F_EXHAUSTIVE_REWRITE_SAFETY_PASS",
  declared_variables: 2,
  candidate_non_tautological_clauses: CLAUSES.length,
  distinct_cnfs: 0,
  literal_weight_alphabet: ["0", "1", "-1", "i"],
  weight_assignments_per_cnf: 256,
  total_formula_weight_states: 0,
  duplicate_clause_equivalence_checks: 0,
  tautological_clause_equivalence_checks: 0,
  subsumption_equivalence_checks: 0,
  forced_unit_weight_factor_checks: 0,
  literal_equivalence_compensated_checks: 0,
  satisfiable_zero_count_states: 0,
  pure_literal_unsafe_witness: null,
  naive_equivalence_unsafe_witness: null
};

for (let mask = 0; mask < (1 << CLAUSES.length); ++mask) {
  const formula = CLAUSES.filter((_, i) => (mask >> i) & 1);
  ++stats.distinct_cnfs;
  const truth = Array.from({length: 4}, (_, bits) => satisfyFormula(formula, bits));

  for (let weightMask = 0; weightMask < 256; ++weightMask) {
    // w(+x), w(-x), w(+y), w(-y)
    const weights = Array.from({length: 4}, (_, j) =>
      VALUES[(weightMask >> (2 * j)) & 3]
    );
    function weightOfAssignment(bits) {
      return mul(weights[(bits & 1) ? 0 : 1], weights[(bits & 2) ? 2 : 3]);
    }
    function countWithPredicate(predicate) {
      let result = [0, 0];
      for (let bits = 0; bits < 4; ++bits) {
        if (predicate(bits)) result = add(result, weightOfAssignment(bits));
      }
      return result;
    }
    const before = countWithPredicate(bits => truth[bits]);

    // Adding clauses logically implied by F must not affect WMC over the SAME
    // declared variable universe, regardless of signed/complex/zero weights.
    const duplicate = formula.length > 0 ? formula[0] : null;
    const withDuplicate = countWithPredicate(bits =>
      truth[bits] && (duplicate === null || satisfyClause(duplicate, bits)));
    assertExact(withDuplicate, before, "duplicate", mask, weightMask);
    ++stats.duplicate_clause_equivalence_checks;

    const withTautology = countWithPredicate(bits =>
      truth[bits] && satisfyClause([1, -1], bits));
    assertExact(withTautology, before, "tautology", mask, weightMask);
    ++stats.tautological_clause_equivalence_checks;

    if (formula.length > 0) {
      const first = formula[0];
      const extra = first.includes(1) || first.includes(-1) ? 2 : 1;
      const subsumed = [...first, extra];
      const after = countWithPredicate(bits =>
        truth[bits] && satisfyClause(subsumed, bits));
      assertExact(after, before, "subsumed clause", mask, weightMask);
      ++stats.subsumption_equivalence_checks;
    }

    // A unit clause forces a literal. Once x is removed from the residual
    // variable universe, multiply its original literal weight EXACTLY once.
    let forced = null;
    if (formula.some(c => c.length === 1 && c[0] === 1)) forced = 1;
    else if (formula.some(c => c.length === 1 && c[0] === -1)) forced = -1;
    if (forced !== null) {
      let residualOnY = [0, 0];
      for (let y = 0; y < 2; ++y) {
        const assignment = (forced === 1 ? 1 : 0) | (y << 1);
        if (truth[assignment]) {
          residualOnY = add(residualOnY, weights[y ? 2 : 3]);
        }
      }
      const factored = mul(weights[forced === 1 ? 0 : 1], residualOnY);
      assertExact(factored, before, "unit factor", mask, weightMask);
      ++stats.forced_unit_weight_factor_checks;
    }

    if (truth.some(Boolean) && equal(before, [0, 0])) {
      ++stats.satisfiable_zero_count_states;
    }

    // SAT-preserving pure-literal assignment is not general WMC preserving.
    const purePositiveX = formula.some(cl => cl.includes(1)) &&
                          !formula.some(cl => cl.includes(-1));
    if (purePositiveX && truth.some(Boolean) &&
        stats.pure_literal_unsafe_witness === null) {
      const forcedX = countWithPredicate(bits => truth[bits] && !!(bits & 1));
      if (!equal(forcedX, before)) {
        stats.pure_literal_unsafe_witness = {
          formula, weights, correct_count: before, count_if_x_forced_true: forcedX
        };
      }
    }

    // For the stand-alone equivalence constraint x <-> y, eliminating y
    // requires multiplying both matching polarity weights into x.
    // We do NOT claim this simple rule applies to arbitrary other constraints.
    const onlyEquivalence = mask === ((1 << 5) | (1 << 6));
    if (onlyEquivalence) {
      const compensated = add(mul(weights[0], weights[2]),
                              mul(weights[1], weights[3]));
      assertExact(compensated, before, "compensated equivalence", mask, weightMask);
      ++stats.literal_equivalence_compensated_checks;
      const naive = add(weights[0], weights[1]);
      if (stats.naive_equivalence_unsafe_witness === null &&
          !equal(naive, before)) {
        stats.naive_equivalence_unsafe_witness = {
          formula, weights, correct_count: before, count_if_y_dropped: naive
        };
      }
    }

    ++stats.total_formula_weight_states;
  }
}
if (stats.distinct_cnfs !== 256 ||
    stats.total_formula_weight_states !== 65536 ||
    stats.duplicate_clause_equivalence_checks !== 65536 ||
    stats.tautological_clause_equivalence_checks !== 65536 ||
    stats.subsumption_equivalence_checks !== 65280 ||
    stats.forced_unit_weight_factor_checks !== 49152 ||
    stats.literal_equivalence_compensated_checks !== 256 ||
    stats.satisfiable_zero_count_states !== 10049 ||
    !stats.pure_literal_unsafe_witness ||
    !stats.naive_equivalence_unsafe_witness) {
  throw new Error("Unexpected exhaustive enumeration coverage: " +
                  JSON.stringify(stats));
}
console.log(JSON.stringify(stats, null, 2));
