/-
Reference checked integer arithmetic. All operations compute over Int
and reject a result outside [lo,hi]. i128 is the instantiation below.
This is not a verified translation of Rust's intrinsics.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineCheckedArithmetic

def i128Min : Int := -(2^127)
def i128Max : Int := 2^127-1

def checked (lo hi v : Int) : Option Int :=
  if lo ≤ v ∧ v ≤ hi then some v else none

theorem checked_some_iff (lo hi v r : Int) :
    checked lo hi v = some r ↔ v = r ∧ lo ≤ v ∧ v ≤ hi := by
  unfold checked
  split
  · rename_i h
    simp [h.1, h.2]
  · rename_i h
    constructor
    · intro hbad
      contradiction
    · intro hgood
      exact False.elim (h hgood.2)

theorem checked_none_iff (lo hi v : Int) :
    checked lo hi v = none ↔ ¬ (lo ≤ v ∧ v ≤ hi) := by
  unfold checked
  split
  · rename_i h
    simp [h]
  · rename_i h
    simp [h]

def checkedMul (lo hi a b : Int) : Option Int := checked lo hi (a*b)
def checkedAdd (lo hi a b : Int) : Option Int := checked lo hi (a+b)
def checkedSub (lo hi a b : Int) : Option Int := checked lo hi (a-b)

theorem mul_some_exact (lo hi a b r : Int)
    (h : checkedMul lo hi a b = some r) : r = a*b :=
  ((checked_some_iff lo hi (a*b) r).mp h).1.symm

theorem add_some_exact (lo hi a b r : Int)
    (h : checkedAdd lo hi a b = some r) : r = a+b :=
  ((checked_some_iff lo hi (a+b) r).mp h).1.symm

theorem sub_some_exact (lo hi a b r : Int)
    (h : checkedSub lo hi a b = some r) : r = a-b :=
  ((checked_some_iff lo hi (a-b) r).mp h).1.symm

/-- Native multiplication followed by add OR subtract, never checked
    negation of the product. Operands are assumed representable. -/
def checkedStep (lo hi acc a b : Int) (negative : Bool) : Option Int :=
  match checkedMul lo hi a b with
  | none => none
  | some p => if negative then checkedSub lo hi acc p else checkedAdd lo hi acc p

def exactStep (acc a b : Int) (negative : Bool) : Int :=
  if negative then acc-a*b else acc+a*b

theorem step_some_exact (lo hi acc a b r : Int) (negative : Bool)
    (h : checkedStep lo hi acc a b negative = some r) :
    r = exactStep acc a b negative := by
  unfold checkedStep at h
  cases hm : checkedMul lo hi a b with
  | none => simp [hm] at h
  | some p =>
      have hp := mul_some_exact lo hi a b p hm
      rw [hm] at h
      cases negative with
      | false =>
          exact (add_some_exact lo hi acc p r h).trans
            (congrArg (fun v => acc+v) hp)
      | true =>
          exact (sub_some_exact lo hi acc p r h).trans
            (congrArg (fun v => acc-v) hp)

structure Update where
  a : Int
  b : Int
  negative : Bool

def checkedTrace (lo hi : Int) (acc : Int) : List Update → Option Int
  | [] => some acc
  | u :: us =>
      match checkedStep lo hi acc u.a u.b u.negative with
      | none => none
      | some mid => checkedTrace lo hi mid us

def exactTrace (acc : Int) : List Update → Int
  | [] => acc
  | u :: us => exactTrace (exactStep acc u.a u.b u.negative) us

theorem trace_some_exact (lo hi acc r : Int) (us : List Update)
    (h : checkedTrace lo hi acc us = some r) :
    r = exactTrace acc us := by
  induction us generalizing acc with
  | nil => exact (Option.some.inj h).symm
  | cons u us ih =>
      unfold checkedTrace at h
      cases hs : checkedStep lo hi acc u.a u.b u.negative with
      | none => simp [hs] at h
      | some mid =>
          rw [hs] at h
          have hm := step_some_exact lo hi acc u.a u.b mid u.negative hs
          exact (ih mid h).trans (congrArg (fun v => exactTrace v us) hm)

/-- Failure on an intermediate product is not an exact zero verdict. -/
theorem step_product_overflow (lo hi acc a b : Int) (negative : Bool)
    (h : ¬ (lo ≤ a*b ∧ a*b ≤ hi)) :
    checkedStep lo hi acc a b negative = none := by
  have hm : checkedMul lo hi a b = none :=
    (checked_none_iff lo hi (a*b)).mpr h
  simp only [checkedStep, hm]


/-- One coordinate's successful trace equals the signed integer sum. -/
def signedSum : List Update → Int
  | [] => 0
  | u :: us => (if u.negative then -(u.a*u.b) else u.a*u.b) + signedSum us

theorem exact_trace_sum (acc : Int) (us : List Update) :
    exactTrace acc us = acc + signedSum us := by
  induction us generalizing acc with
  | nil => exact (Int.add_zero acc).symm
  | cons u us ih =>
      change exactTrace (exactStep acc u.a u.b u.negative) us =
        acc + ((if u.negative then -(u.a*u.b) else u.a*u.b) + signedSum us)
      rw [ih]
      cases h : u.negative with
      | false => simp [exactStep, h, Int.add_assoc]
      | true => simp [exactStep, h, Int.sub_eq_add_neg, Int.add_assoc]

theorem checked_trace_sum (lo hi acc r : Int) (us : List Update)
    (h : checkedTrace lo hi acc us = some r) :
    r = acc + signedSum us :=
  (trace_some_exact lo hi acc r us h).trans (exact_trace_sum acc us)

theorem step_accumulator_overflow (lo hi acc a b : Int) (negative : Bool)
    (h : ¬ (lo ≤ exactStep acc a b negative ∧ exactStep acc a b negative ≤ hi)) :
    checkedStep lo hi acc a b negative = none := by
  unfold checkedStep
  cases hm : checkedMul lo hi a b with
  | none => rfl
  | some p =>
      have hp := mul_some_exact lo hi a b p hm
      subst p
      cases negative with
      | false => exact (checked_none_iff lo hi (acc+a*b)).mpr h
      | true => exact (checked_none_iff lo hi (acc-a*b)).mpr h

#print axioms exact_trace_sum
#print axioms checked_trace_sum
#print axioms step_accumulator_overflow
#print axioms checked_some_iff
#print axioms checked_none_iff
#print axioms mul_some_exact
#print axioms add_some_exact
#print axioms sub_some_exact
#print axioms step_some_exact
#print axioms trace_some_exact
#print axioms step_product_overflow
end QuPRS.AffineCheckedArithmetic
