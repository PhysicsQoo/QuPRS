#!/usr/bin/env node
// RaWMoCS A0 research-only mathematical property checks; no solver or benchmarks.
// Deterministic 32-bit LCG seed 173. BigInt rational complex (Q[i]) exactly.
// This checks identities by separate exhaustive enumerations, not DPLL implementation.

"use strict";

let state = 173;
function rng() { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state; }
function pick(n) { if (n <= 0) throw Error("empty range"); return rng() % n; }
function gcd(a, b) {
  a = a < 0n ? -a : a;
  b = b < 0n ? -b : b;
  while (b !== 0n) { const t = a % b; a = b; b = t; }
  return a || 1n;
}
function rational(n, d = 1n) {
  if (d === 0n) throw Error("zero denominator");
  if (d < 0n) { n = -n; d = -d; }
  const g = gcd(n, d);
  return [n / g, d / g];
}
function add(a, b) { return rational(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }
function mul(a, b) { return rational(a[0] * b[0], a[1] * b[1]); }
function cadd(a, b) { return [add(a[0], b[0]), add(a[1], b[1])]; }
function cmul(a, b) {
  const imagProduct = mul(a[1], b[1]);
  return [
    add(mul(a[0], b[0]), rational(-imagProduct[0], imagProduct[1])),
    add(mul(a[0], b[1]), mul(a[1], b[0]))
  ];
}
const ZERO = [rational(0n), rational(0n)];
const ONE = [rational(1n), rational(0n)];
function equal(a, b) {
  return a[0][0] === b[0][0] && a[0][1] === b[0][1]
      && a[1][0] === b[1][0] && a[1][1] === b[1][1];
}
function randomComplex() {
  return [
    rational(BigInt(pick(5) - 2), BigInt(1 + pick(4))),
    rational(BigInt(pick(5) - 2), BigInt(1 + pick(4)))
  ];
}
function makeFormula(n, m, projected = false) {
  const clauses = [];
  for (let j = 0; j < m; ++j) {
    const clause = [];
    for (let k = 0, count = 1 + pick(Math.min(n, 3)); k < count; ++k) {
      const variable = 1 + pick(n);
      clause.push(pick(2) ? variable : -variable);
    }
    clauses.push(clause);
  }
  const weights = Array.from({length: n}, () => [randomComplex(), randomComplex()]);
  const projection = projected
    ? Array.from({length: n}, (_, i) => i + 1).filter(() => pick(2))
    : null;
  return {n, clauses, weights, projection};
}
function countFormula(formula) {
  const {n, clauses, weights, projection} = formula;
  const P = projection ? new Set(projection) : null;
  const projections = new Set();
  let answer = ZERO;
  let satisfyingModels = 0;
  for (let assignment = 0; assignment < (1 << n); ++assignment) {
    const satisfies = clauses.every(clause => clause.some(literal => (
      Boolean(assignment & (1 << (Math.abs(literal) - 1))) === (literal > 0)
    )));
    if (!satisfies) continue;
    ++satisfyingModels;
    const projectionKey = P
      ? Array.from(P).sort((a, b) => a - b)
         .map(v => Number(Boolean(assignment & (1 << (v - 1))))).join("")
      : null;
    if (P && projections.has(projectionKey)) continue;
    projections.add(projectionKey);
    let term = ONE;
    for (let v = 1; v <= n; ++v) {
      if (P && !P.has(v)) continue;
      const value = (assignment >> (v - 1)) & 1;
      term = cmul(term, weights[v - 1][value]);
    }
    answer = cadd(answer, term);
  }
  return {answer, satisfyingModels, projectedModels: P ? projections.size : null};
}
function projectionFirst(formula) {
  const P = formula.projection;
  const E = Array.from({length: formula.n}, (_, i) => i + 1).filter(v => !P.includes(v));
  let answer = ZERO;
  let distinct = 0;
  for (let a = 0; a < (1 << P.length); ++a) {
    const vals = new Map(P.map((v, i) => [v, (a >> i) & 1]));
    let exists = false;
    for (let b = 0; b < (1 << E.length); ++b) {
      const assignment = new Map(vals);
      E.forEach((v, i) => assignment.set(v, (b >> i) & 1));
      const satisfied = formula.clauses.every(clause => clause.some(l => (
        assignment.get(Math.abs(l)) === (l > 0 ? 1 : 0)
      )));
      if (satisfied) { exists = true; break; }
    }
    if (!exists) continue;
    ++distinct;
    let term = ONE;
    for (const v of P) term = cmul(term, formula.weights[v - 1][vals.get(v)]);
    answer = cadd(answer, term);
  }
  return {answer, distinct};
}
function assertExact(value, expected, context) {
  if (!equal(value, expected)) throw Error("exact rational-complex mismatch in " + context);
}
const counters = {seed: 173, branch: 0, free_variable: 0, projected: 0, disjoint_components: 0};

// Weighted Shannon branch and isolated counted-variable factors.
for (let i = 0; i < 200; ++i) {
  const n = 1 + pick(7);
  const F = makeFormula(n, pick(7));
  const before = countFormula(F).answer;
  const v = 1 + pick(n);
  const left = countFormula({...F, clauses: [...F.clauses, [v]]}).answer;
  const right = countFormula({...F, clauses: [...F.clauses, [-v]]}).answer;
  assertExact(before, cadd(left, right), "weighted branch " + i);
  ++counters.branch;
  const extraWeights = [randomComplex(), randomComplex()];
  const withFreeVariable = {
    ...F, n: n + 1, weights: [...F.weights, extraWeights]
  };
  assertExact(countFormula(withFreeVariable).answer,
              cmul(before, cadd(extraWeights[0], extraWeights[1])),
              "free-variable factor " + i);
  ++counters.free_variable;
}
// Existential distinct projection semantics vs projection-first independent check.
for (let i = 0; i < 120; ++i) {
  const n = 1 + pick(7);
  const F = makeFormula(n, pick(6), true);
  const total = countFormula(F);
  const projected = projectionFirst(F);
  assertExact(total.answer, projected.answer, "projection " + i);
  if (total.projectedModels !== projected.distinct) {
    throw Error("projected cardinality mismatch " + i);
  }
  ++counters.projected;
}
// Disjoint counted supports permit exact component multiplication.
for (let i = 0; i < 100; ++i) {
  const n1 = 1 + pick(3);
  const n2 = 1 + pick(3);
  const A = makeFormula(n1, pick(4));
  const B = makeFormula(n2, pick(4));
  const joined = {
    n: n1 + n2,
    clauses: [
      ...A.clauses,
      ...B.clauses.map(clause => clause.map(l => Math.sign(l) * (Math.abs(l) + n1)))
    ],
    weights: [...A.weights, ...B.weights],
    projection: null
  };
  assertExact(countFormula(joined).answer,
              cmul(countFormula(A).answer, countFormula(B).answer),
              "disjoint-component product " + i);
  ++counters.disjoint_components;
}
const total = Object.values(counters).reduce((a, b) => a + b, -counters.seed);
if (total !== 620) throw Error("unexpected number of assertions");
console.log(JSON.stringify({status:"RAWMOCS_A0_RANDOMIZED_EXACT_PROPERTIES_PASS",
                            total, ...counters}));
