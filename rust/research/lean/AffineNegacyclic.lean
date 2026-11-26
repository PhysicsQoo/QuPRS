/-
Exact integer negacyclic term semantics matching the native cyclo_mul
loop, conditional on bounded indices. No checked i128 refinement yet.
-/
import AffineCyclotomicLift
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineNegacyclic
open QuPRS.AffineCyclotomicLift

def nativeTerm (d k i j : Nat) (a b : Int) : Int :=
  if (i+j) % d = k then
    if i+j < d then a*b else -(a*b)
  else 0

def exactTerm (d k i j : Nat) (a b : Int) : Int :=
  coordinate d k (i+j) * (a*b)

/-- The one-wrap native loop agrees with the signed phase coordinate
    for every pair of in-range basis exponents and output coordinate. -/
theorem native_term_correct (d k i j : Nat) (a b : Int)
    (hi : i < d) (hj : j < d) (hk : k < d) :
    nativeTerm d k i j a b = exactTerm d k i j a b := by
  have h2 : i+j < 2*d := by omega
  unfold nativeTerm exactTerm coordinate
  rw [Nat.mod_eq_of_lt h2]
  by_cases h : i+j < d
  · have hn : i+j ≠ k+d := by omega
    rw [Nat.mod_eq_of_lt h]
    simp [h, hn]
  · have hd : d ≤ i+j := by omega
    have hsub : i+j-d < d := by omega
    have hn : i+j ≠ k := by omega
    have he : i+j-d = k ↔ i+j = k+d := by omega
    rw [Nat.mod_eq_sub_mod hd, Nat.mod_eq_of_lt hsub]
    simp [h, hn, he]

theorem term_lift (d k i j s : Nat) (a b : Int) (hs : 0 < s) :
    exactTerm (d*s) (k*s) (i*s) (j*s) a b =
      exactTerm d k i j a b := by
  unfold exactTerm
  rw [← Nat.add_mul, coordinate_lift d k (i+j) s hs]

theorem term_off_grid (d k i j s : Nat) (a b : Int) (hk : k % s ≠ 0) :
    exactTerm (d*s) k (i*s) (j*s) a b = 0 := by
  unfold exactTerm
  rw [← Nat.add_mul, coordinate_off_grid d k (i+j) s hk, Int.zero_mul]

/-- A list enumerates coefficient-pair contributions. Full Cartesian
    coverage, accumulator order and overflow are separate obligations. -/
structure PairTerm where
  i : Nat
  j : Nat
  a : Int
  b : Int

def scaled (s : Nat) (t : PairTerm) : PairTerm :=
  ⟨t.i*s, t.j*s, t.a, t.b⟩

def pairSum (d k : Nat) : List PairTerm → Int
  | [] => 0
  | t :: ts => exactTerm d k t.i t.j t.a t.b + pairSum d k ts

theorem pair_sum_lift (d k s : Nat) (hs : 0 < s) (ts : List PairTerm) :
    pairSum (d*s) (k*s) (ts.map (scaled s)) = pairSum d k ts := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      change exactTerm (d*s) (k*s) (t.i*s) (t.j*s) t.a t.b +
        pairSum (d*s) (k*s) (ts.map (scaled s)) =
        exactTerm d k t.i t.j t.a t.b + pairSum d k ts
      rw [term_lift d k t.i t.j s t.a t.b hs, ih]

theorem pair_sum_off_grid (d k s : Nat) (hk : k % s ≠ 0) (ts : List PairTerm) :
    pairSum (d*s) k (ts.map (scaled s)) = 0 := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      change exactTerm (d*s) k (t.i*s) (t.j*s) t.a t.b +
        pairSum (d*s) k (ts.map (scaled s)) = 0
      rw [term_off_grid d k t.i t.j s t.a t.b hk, ih]

#print axioms native_term_correct
#print axioms term_lift
#print axioms term_off_grid
#print axioms pair_sum_lift
#print axioms pair_sum_off_grid
end QuPRS.AffineNegacyclic
