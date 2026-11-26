/-
Bridge the row-major coefficient-pair model to the ordered checked vector
model. The Rust loop is represented by zero-skipping and signed updates.
Successful execution refines the exact negacyclic coefficient sum.
No claim of verified Rust translation, machine arithmetic or embedding.
-/
import AffineNegacyclic
import AffineCheckedArithmetic

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineCheckedCycloSchedule
open QuPRS.AffineNegacyclic
open QuPRS.AffineCheckedArithmetic

local instance (priority := 2000) : DecidableEq Nat := Nat.decEq
local instance (priority := 2000) (a b : Nat) : Decidable (a < b) := Nat.decLt a b

def toUpdate (d : Nat) (t : PairTerm) : VectorUpdate Nat :=
  ⟨(t.i+t.j) % d, ⟨t.a, t.b, !(decide (t.i+t.j < d))⟩⟩

def schedule (d : Nat) : List PairTerm → List (VectorUpdate Nat)
  | [] => []
  | t :: ts =>
      if t.a = 0 ∨ t.b = 0 then schedule d ts
      else toUpdate d t :: schedule d ts

theorem one_update_sum (d k : Nat) (t : PairTerm) (us : List (VectorUpdate Nat)) :
    signedSum (coordinateTrace k (toUpdate d t :: us)) =
      nativeTerm d k t.i t.j t.a t.b + signedSum (coordinateTrace k us) := by
  change signedSum (if k = (t.i+t.j) % d then
      (toUpdate d t).update :: coordinateTrace k us else coordinateTrace k us) =
      nativeTerm d k t.i t.j t.a t.b + signedSum (coordinateTrace k us)
  by_cases hk : k = (t.i+t.j) % d
  · rw [ite_eq_left hk]
    unfold nativeTerm
    rw [ite_eq_left hk.symm]
    change (if !(decide (t.i+t.j < d)) then -(t.a*t.b) else t.a*t.b) +
      signedSum (coordinateTrace k us) =
        (if t.i+t.j < d then t.a*t.b else -(t.a*t.b)) +
          signedSum (coordinateTrace k us)
    by_cases hp : t.i+t.j < d <;> simp [hp]
  · have hn : (t.i+t.j) % d ≠ k := fun he => hk he.symm
    rw [ite_eq_right hk]
    unfold nativeTerm
    rw [ite_eq_right hn, Int.zero_add]

theorem schedule_sum (d k : Nat) (hk : k < d) (ts : List PairTerm)
    (h : ∀ t, t ∈ ts → t.i < d ∧ t.j < d) :
    signedSum (coordinateTrace k (schedule d ts)) = pairSum d k ts := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      have hb := h t (List.mem_cons.mpr (Or.inl rfl))
      have ht : ∀ u, u ∈ ts → u.i < d ∧ u.j < d :=
        fun u hu => h u (List.mem_cons.mpr (Or.inr hu))
      by_cases hz : t.a = 0 ∨ t.b = 0
      · rw [schedule, ite_eq_left hz, pairSum,
            zero_pair_term d k t.i t.j t.a t.b hz, Int.zero_add]
        exact ih ht
      · rw [schedule, ite_eq_right hz, one_update_sum, pairSum,
            native_term_correct d k t.i t.j t.a t.b hb.1 hb.2 hk, ih ht]

theorem schedule_index_bound (d : Nat) (hd : 0 < d) (ts : List PairTerm) :
    ∀ u, u ∈ schedule d ts → u.index < d := by
  induction ts with
  | nil =>
      intro u hu
      exact False.elim (List.not_mem_nil hu)
  | cons t ts ih =>
      intro u hu
      by_cases hz : t.a = 0 ∨ t.b = 0
      · rw [schedule, ite_eq_left hz] at hu
        exact ih u hu
      · rw [schedule, ite_eq_right hz] at hu
        rcases List.mem_cons.mp hu with he | he
        · rw [he]
          exact Nat.mod_lt _ hd
        · exact ih u he

def checkedCyclo (lo hi : Int) (d : Nat) (a b : Nat → Int) :
    Option (Nat → Int) :=
  checkedVector lo hi (fun _ : Nat => 0) (schedule d (pairs d a b))

/-- Successful whole-vector computation refines every legal coordinate
    of the exact product. This does not assert completeness on overflow. -/
theorem checked_cyclo_some (lo hi : Int) (d : Nat) (a b result : Nat → Int)
    (h : checkedCyclo lo hi d a b = some result) :
    ∀ k, k < d → result k = pairSum d k (pairs d a b) := by
  intro k hk
  have hb : ∀ t, t ∈ pairs d a b → t.i < d ∧ t.j < d := by
    intro t ht
    obtain ⟨i, j, hi, hj, he⟩ := (pairs_membership d a b t).mp ht
    rw [he]
    exact ⟨hi, hj⟩
  have he := checked_vector_coordinate_sum lo hi (fun _ : Nat => 0)
    result (schedule d (pairs d a b)) k h
  calc
    result k = 0 + signedSum (coordinateTrace k (schedule d (pairs d a b))) := he
    _ = pairSum d k (pairs d a b) := by
      rw [Int.zero_add, schedule_sum d k hk _ hb]

theorem checked_vector_append {I : Type} [DecidableEq I] (lo hi : Int)
    (acc : I → Int) (xs ys : List (VectorUpdate I)) :
    checkedVector lo hi acc (xs ++ ys) =
      match checkedVector lo hi acc xs with
      | none => none
      | some mid => checkedVector lo hi mid ys := by
  induction xs generalizing acc with
  | nil => rfl
  | cons u xs ih =>
      change (match checkedStep lo hi (acc u.index) u.update.a u.update.b u.update.negative with
        | none => none
        | some mid => checkedVector lo hi (put acc u.index mid) (xs ++ ys)) =
        (match checkedVector lo hi acc (u :: xs) with
        | none => none
        | some mid => checkedVector lo hi mid ys)
      cases hs : checkedStep lo hi (acc u.index) u.update.a u.update.b u.update.negative with
      | none => simp only [checkedVector, hs]
      | some mid =>
          simp only [checkedVector, hs]
          exact ih (put acc u.index mid)

theorem checked_vector_prefix_reject {I : Type} [DecidableEq I] (lo hi : Int)
    (acc : I → Int) (xs ys : List (VectorUpdate I))
    (h : checkedVector lo hi acc xs = none) :
    checkedVector lo hi acc (xs ++ ys) = none := by
  rw [checked_vector_append, h]

#print axioms one_update_sum
#print axioms schedule_sum
#print axioms schedule_index_bound
#print axioms checked_cyclo_some
#print axioms checked_vector_append
#print axioms checked_vector_prefix_reject
end QuPRS.AffineCheckedCycloSchedule
