/-
Admission of a distinct complete hidden order against the original domain.
Exact permutation invariance, not checked operational reassociation.
Native planner, explicit assignment enumeration and packed indices remain
separate obligations.
-/
import AffineCheckedOrder
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineHiddenOrder
open QuPRS.AffineFactorScope
open QuPRS.AffineFactorElimination
open QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineCheckedOrder

def unique {X : Type} [DecidableEq X] : List X → Bool
  | [] => true
  | x :: xs => if x ∈ xs then false else unique xs

theorem unique_sound {X : Type} [DecidableEq X] (xs : List X)
    (h : unique xs = true) : xs.Nodup := by
  induction xs with
  | nil => exact List.nodup_nil
  | cons x xs ih =>
      by_cases hx : x ∈ xs
      · rw [unique, ite_eq_left hx] at h
        contradiction
      · rw [unique, ite_eq_right hx] at h
        exact List.nodup_cons.mpr ⟨hx, ih h⟩

def removeOne {X : Type} [DecidableEq X] (x : X) : List X → Option (List X)
  | [] => none
  | y :: ys =>
      if x = y then some ys
      else match removeOne x ys with
        | none => none
        | some zs => some (y :: zs)

theorem remove_one_perm {X : Type} [DecidableEq X] (x : X) (xs ys : List X)
    (h : removeOne x xs = some ys) : List.Perm xs (x :: ys) := by
  induction xs generalizing ys with
  | nil => contradiction
  | cons y zs ih =>
      by_cases he : x = y
      · subst y
        rw [removeOne, ite_eq_left rfl] at h
        have hz : zs = ys := Option.some.inj h
        subst ys
        exact List.Perm.refl _
      · rw [removeOne, ite_eq_right he] at h
        cases ht : removeOne x zs with
        | none => rw [ht] at h; contradiction
        | some tail =>
            rw [ht] at h
            have hz : y :: tail = ys := Option.some.inj h
            subst ys
            exact (List.Perm.cons y (ih tail ht)).trans (List.Perm.swap x y tail)

def consume {X : Type} [DecidableEq X] : List X → List X → Bool
  | [], hidden => hidden.isEmpty
  | x :: xs, hidden =>
      match removeOne x hidden with
      | none => false
      | some remaining => consume xs remaining

theorem consume_perm {X : Type} [DecidableEq X] (xs hidden : List X)
    (h : consume xs hidden = true) : List.Perm hidden xs := by
  induction xs generalizing hidden with
  | nil =>
      cases hidden with
      | nil => exact List.Perm.nil
      | cons y ys => contradiction
  | cons x xs ih =>
      cases hr : removeOne x hidden with
      | none => simp only [consume, hr] at h; contradiction
      | some remaining =>
          simp only [consume, hr] at h
          exact (remove_one_perm x hidden remaining hr).trans
            (List.Perm.cons x (ih remaining h))

def admitOrder {X : Type} [DecidableEq X] (hidden xs : List X) : Bool :=
  if unique hidden then consume xs hidden else false

theorem admitted_order {X : Type} [DecidableEq X] (hidden xs : List X)
    (h : admitOrder hidden xs = true) :
    hidden.Nodup ∧ xs.Nodup ∧ List.Perm hidden xs := by
  by_cases hu : unique hidden = true
  · have hd := unique_sound hidden hu
    rw [admitOrder, ite_eq_left hu] at h
    have hp := consume_perm xs hidden h
    exact ⟨hd, hp.nodup hd, hp⟩
  · rw [admitOrder, ite_eq_right hu] at h
    contradiction

theorem admitted_coverage {X : Type} [DecidableEq X] (hidden xs : List X)
    (h : admitOrder hidden xs = true) (x : X) :
    x ∈ xs ↔ x ∈ hidden :=
  (admitted_order hidden xs h).2.2.mem_iff.symm

theorem write_swap {X : Type} [DecidableEq X] (a : X → Bool)
    (x y : X) (b c : Bool) (h : x ≠ y) :
    write (write a x b) y c = write (write a y c) x b := by
  funext z
  by_cases hx : z = x
  · subst z
    simp [write, h]
  · by_cases hy : z = y
    · subst z
      simp [write, hx]
    · simp [write, hx, hy]

theorem eliminate_swap {X : Type} [DecidableEq X] {d : Nat}
    (x y : X) (f : (X → Bool) → Coeff d) :
    eliminate finAdd x (eliminate finAdd y f) =
      eliminate finAdd y (eliminate finAdd x f) := by
  by_cases he : x = y
  · subst y
    rfl
  · funext a k
    change (f (write (write a x false) y false) k +
        f (write (write a x false) y true) k) +
        (f (write (write a x true) y false) k +
        f (write (write a x true) y true) k) =
      (f (write (write a y false) x false) k +
        f (write (write a y false) x true) k) +
        (f (write (write a y true) x false) k +
        f (write (write a y true) x true) k)
    rw [write_swap a x y false false he, write_swap a x y false true he,
        write_swap a x y true false he, write_swap a x y true true he]
    omega

theorem sum_order_fold {X : Type} [DecidableEq X] {d : Nat}
    (xs : List X) (f : (X → Bool) → Coeff d) :
    sumOrder finAdd xs f =
      xs.foldl (fun g x => eliminate finAdd x g) f := by
  induction xs generalizing f with
  | nil => rfl
  | cons x xs ih => exact ih (eliminate finAdd x f)

theorem sum_order_perm {X : Type} [DecidableEq X] {d : Nat}
    (xs ys : List X) (f : (X → Bool) → Coeff d)
    (hp : List.Perm xs ys) :
    sumOrder finAdd xs f = sumOrder finAdd ys f := by
  rw [sum_order_fold, sum_order_fold]
  exact hp.foldl_eq' (fun x _ y _ g => eliminate_swap y x g) f

def admittedResult {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) : Option (Coeff d) :=
  if admitOrder hidden xs then checkedResult lo hi domain xs fs a else none

theorem admitted_result_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) (v : Coeff d) (h : admittedResult lo hi domain hidden xs fs a = some v) :
    v = sumOrder finAdd hidden (fun b => factorProduct (finOne d) finMul b fs) a := by
  by_cases ha : admitOrder hidden xs = true
  · rw [admittedResult, ite_eq_left ha] at h
    have hp := (admitted_order hidden xs ha).2.2.symm
    exact (checked_result_sound lo hi domain xs fs a v h).trans
      (congrFun (sum_order_perm xs hidden _ hp) a)
  · rw [admittedResult, ite_eq_right ha] at h
    contradiction

theorem invalid_order_reject {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) (h : admitOrder hidden xs = false) :
    admittedResult lo hi domain hidden xs fs a = none := by
  simp [admittedResult, h]

#print axioms unique_sound
#print axioms remove_one_perm
#print axioms consume_perm
#print axioms admitted_order
#print axioms admitted_coverage
#print axioms write_swap
#print axioms eliminate_swap
#print axioms sum_order_fold
#print axioms sum_order_perm
#print axioms admitted_result_sound
#print axioms invalid_order_reject
end QuPRS.AffineHiddenOrder
