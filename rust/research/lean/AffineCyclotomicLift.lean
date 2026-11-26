/-
Independent exact cyclotomic basis lifting model.
d is the small negacyclic degree, s a positive integer scale.
The lifted degree is d*s, and exponent p maps to p*s.
No complex embedding, normalization or Rust arithmetic claim.
-/
import Std

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineCyclotomicLift

def coordinate (d k p : Nat) : Int :=
  if p % (2*d) = k then 1
  else if p % (2*d) = k+d then -1 else 0

theorem residue_scale (p d s : Nat) :
    (p*s) % (2*(d*s)) = (p % (2*d))*s := by
  rw [← Nat.mul_assoc]
  exact Nat.mul_mod_mul_right s p (2*d)

theorem coordinate_lift (d k p s : Nat) (hs : 0 < s) :
    coordinate (d*s) (k*s) (p*s) = coordinate d k p := by
  unfold coordinate
  rw [residue_scale, ← Nat.add_mul]
  have he : (p % (2*d))*s = k*s ↔ p % (2*d) = k := by
    constructor
    · intro h
      exact Nat.mul_right_cancel hs h
    · intro h
      rw [h]
  have hf : (p % (2*d))*s = (k+d)*s ↔ p % (2*d) = k+d := by
    constructor
    · intro h
      exact Nat.mul_right_cancel hs h
    · intro h
      rw [h]
  simp only [he, hf]

theorem coordinate_off_grid (d k p s : Nat)
    (hk : k % s ≠ 0) :
    coordinate (d*s) k (p*s) = 0 := by
  unfold coordinate
  rw [residue_scale]
  have h1 : (p % (2*d))*s ≠ k := by
    intro h
    apply hk
    rw [← h, Nat.mul_mod_left]
  have h2 : (p % (2*d))*s ≠ k+d*s := by
    intro h
    have hmod := congrArg (fun z : Nat => z % s) h
    have hleft : ((p % (2*d))*s) % s = 0 := Nat.mul_mod_left _ _
    have hright : (k+d*s) % s = k % s := by
      rw [Nat.add_mod, Nat.mul_mod_left, Nat.add_zero, Nat.mod_mod]
    rw [hleft, hright] at hmod
    exact hk hmod.symm
  simp only [ite_eq_right h1, ite_eq_right h2]

def phaseSum {Y : Type} (d k : Nat) (phase : Y → Nat)
    (guard : Y → Bool) : List Y → Int
  | [] => 0
  | y :: ys => (if guard y then coordinate d k (phase y) else 0) +
      phaseSum d k phase guard ys

theorem phase_sum_lift {Y : Type} (d k s : Nat) (hs : 0 < s)
    (phase : Y → Nat) (guard : Y → Bool) (ys : List Y) :
    phaseSum (d*s) (k*s) (fun y => phase y*s) guard ys =
      phaseSum d k phase guard ys := by
  induction ys with
  | nil => rfl
  | cons y ys ih =>
      simp only [phaseSum, coordinate_lift d k (phase y) s hs, ih]

theorem phase_sum_off_grid {Y : Type} (d k s : Nat)
    (hk : k % s ≠ 0) (phase : Y → Nat) (guard : Y → Bool) (ys : List Y) :
    phaseSum (d*s) k (fun y => phase y*s) guard ys = 0 := by
  induction ys with
  | nil => rfl
  | cons y ys ih =>
      simp only [phaseSum, coordinate_off_grid d k (phase y) s hk, ih]
      cases guard y <;> rfl

/-- Zero detection is invariant under basis lifting, including every
    off-grid coordinate. The degree and scale are not enumerated. -/
theorem lifted_zero_iff {Y : Type} (d s : Nat) (hs : 0 < s)
    (phase : Y → Nat) (guard : Y → Bool) (ys : List Y) :
    (∀ k, k < d*s → phaseSum (d*s) k (fun y => phase y*s) guard ys = 0) ↔
    (∀ j, j < d → phaseSum d j phase guard ys = 0) := by
  constructor
  · intro h j hj
    have hk : j*s < d*s := Nat.mul_lt_mul_of_pos_right hj hs
    rw [← phase_sum_lift d j s hs phase guard ys]
    exact h (j*s) hk
  · intro h k hk
    by_cases hz : k % s = 0
    · have he : k / s * s = k := by
        have hm := Nat.mod_add_div' k s
        rw [hz, Nat.zero_add] at hm
        exact hm
      have hj : k / s < d := (Nat.div_lt_iff_lt_mul hs).mpr hk
      rw [← he, phase_sum_lift d (k/s) s hs phase guard ys]
      exact h (k/s) hj
    · exact phase_sum_off_grid d k s hz phase guard ys

/-- A nonzero common integer factor cannot change a coefficient-zero
    decision. This does not identify the actual Path-sum normalization
    factor, nor equate a coefficient-square sum with a physical norm. -/
theorem common_factor_zero_iff (d : Nat) (a : Nat → Int) (q : Int)
    (hq : q ≠ 0) :
    (∀ k, k < d → q * a k = 0) ↔ (∀ k, k < d → a k = 0) := by
  constructor
  · intro h k hk
    rcases Int.mul_eq_zero.mp (h k hk) with hz | hz
    · exact False.elim (hq hz)
    · exact hz
  · intro h k hk
    rw [h k hk, Int.mul_zero]

#print axioms residue_scale
#print axioms coordinate_lift
#print axioms coordinate_off_grid
#print axioms phase_sum_lift
#print axioms phase_sum_off_grid
#print axioms lifted_zero_iff
#print axioms common_factor_zero_iff

end QuPRS.AffineCyclotomicLift
