/-
Fixed-width semantics of the u64 mask operations in deposit8/extract8.
Local bitvector facts are proof-producing bv_decide obligations.
Fuel recursion models the mask walk, padding with zero steps if done.
It is not yet a Rust loop refinement or a usize index correspondence.
-/
import Std.Tactic.BVDecide
set_option autoImplicit false
set_option warningAsError true
set_option maxHeartbeats 4000000
set_option maxRecDepth 4096
namespace QuPRS.AffineMachineWord

abbrev Word := BitVec 64

def lowBit (m : Word) : Word := m &&& (-m)
def clear (m : Word) : Word := m ^^^ lowBit m

theorem low_zero : lowBit 0 = 0 := by
  decide

theorem clear_zero : clear 0 = 0 := by
  decide

theorem low_nonzero (m : Word) (h : m ≠ 0) : lowBit m ≠ 0 := by
  unfold lowBit
  bv_decide

theorem low_onehot (m : Word) : lowBit m &&& (lowBit m - 1) = 0 := by
  unfold lowBit
  bv_decide

theorem low_subset (m : Word) : lowBit m &&& m = lowBit m := by
  unfold lowBit
  bv_decide

theorem low_minimal (m : Word) : m &&& (lowBit m - 1) = 0 ∨ m = 0 := by
  unfold lowBit
  bv_decide

theorem clear_identity (m : Word) : clear m = m &&& (m - 1) := by
  unfold clear lowBit
  bv_decide

theorem clear_lt (m : Word) (h : m ≠ 0) : clear m < m := by
  unfold clear lowBit
  bv_decide

theorem split_mask (m : Word) :
    lowBit m ||| clear m = m ∧ lowBit m &&& clear m = 0 := by
  unfold clear lowBit
  bv_decide

theorem merge_partition (b p r m : Word)
    (hu : b ||| (p ||| r) = m) (hb : b &&& (p ||| r) = 0)
    (hp : p &&& r = 0) :
    (b ||| p) ||| r = m ∧ (b ||| p) &&& r = 0 := by
  bv_decide

theorem select_distributes (a b p : Word) :
    (a &&& b) ||| (a &&& p) = a &&& (b ||| p) := by
  bv_decide

theorem selected_digit (a b : Word) (h : b &&& (b - 1) = 0) :
    (if a &&& b = 0 then 0 else b) = a &&& b := by
  bv_decide

def remaining : Nat → Word → Word
  | 0, m => m
  | n+1, m => remaining n (clear m)

def processed : Nat → Word → Word
  | 0, _ => 0
  | n+1, m => lowBit m ||| processed n (clear m)

theorem walk_partition (fuel : Nat) (m : Word) :
    processed fuel m ||| remaining fuel m = m ∧
    processed fuel m &&& remaining fuel m = 0 := by
  induction fuel generalizing m with
  | zero =>
      change (0 : Word) ||| m = m ∧ (0 : Word) &&& m = 0
      bv_decide
  | succ n ih =>
      have hp := ih (clear m)
      have hs := split_mask m
      change (lowBit m ||| processed n (clear m)) ||| remaining n (clear m) = m ∧
        (lowBit m ||| processed n (clear m)) &&& remaining n (clear m) = 0
      apply merge_partition
      · rw [hp.1, hs.1]
      · rw [hp.1, hs.2]
      · exact hp.2

theorem remaining_zero (fuel : Nat) : remaining fuel 0 = 0 := by
  induction fuel with
  | zero => rfl
  | succ n ih =>
      change remaining n (clear 0) = 0
      rw [clear_zero, ih]

/-- A loose numerical termination bound. The sharper popcount bound
    used for admitted native widths is a separate obligation. -/
theorem remaining_of_numeric_bound (fuel : Nat) (m : Word)
    (h : m.toNat ≤ fuel) : remaining fuel m = 0 := by
  induction fuel generalizing m with
  | zero =>
      change m = 0
      apply BitVec.toNat_eq.mpr
      change m.toNat = 0
      omega
  | succ n ih =>
      by_cases hz : m = 0
      · subst m
        exact remaining_zero (n+1)
      · have hl : (clear m).toNat < m.toNat := clear_lt m hz
        change remaining n (clear m) = 0
        exact ih (clear m) (by omega)

theorem processed_complete (fuel : Nat) (m : Word) (h : remaining fuel m = 0) :
    processed fuel m = m := by
  have hp := (walk_partition fuel m).1
  rw [h] at hp
  simpa using hp

/-- Synchronized reverse reconstruction: at each selected position,
    read the bit from a and deposit that same bit. This models the
    combined bit selection, not the independent usize accumulator. -/
def reconstruct : Nat → Word → Word → Word
  | 0, _, _ => 0
  | n+1, m, a =>
      (if a &&& lowBit m = 0 then 0 else lowBit m) |||
        reconstruct n (clear m) a

theorem reconstruct_prefix (fuel : Nat) (m a : Word) :
    reconstruct fuel m a = a &&& processed fuel m := by
  induction fuel generalizing m with
  | zero =>
      change (0 : Word) = a &&& 0
      bv_decide
  | succ n ih =>
      change (if a &&& lowBit m = 0 then 0 else lowBit m) |||
        reconstruct n (clear m) a = a &&& (lowBit m ||| processed n (clear m))
      rw [selected_digit a (lowBit m) (low_onehot m), ih]
      exact select_distributes a (lowBit m) (processed n (clear m))

theorem reconstruct_complete (fuel : Nat) (m a : Word)
    (h : remaining fuel m = 0) :
    reconstruct fuel m a = a &&& m := by
  rw [reconstruct_prefix, processed_complete fuel m h]

#print axioms low_zero
#print axioms clear_zero
#print axioms low_nonzero
#print axioms low_onehot
#print axioms low_subset
#print axioms low_minimal
#print axioms clear_identity
#print axioms clear_lt
#print axioms split_mask
#print axioms merge_partition
#print axioms select_distributes
#print axioms selected_digit
#print axioms walk_partition
#print axioms remaining_zero
#print axioms remaining_of_numeric_bound
#print axioms processed_complete
#print axioms reconstruct_prefix
#print axioms reconstruct_complete
end QuPRS.AffineMachineWord
