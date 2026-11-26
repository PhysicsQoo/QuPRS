/-
Word-level bridge for affine OUTPUT-coordinate masks, distinct from
monomial-variable masks. The Rust admitted width is at most 16 but
the storage word is u64. The lemmas are parametric in word width.
The population count is modeled as the sum of LSB-first decoded bits;
Rust intrinsic/codegen correctness and native incidence construction
are separate obligations. No path enumeration or Mathlib.
-/
import AffineOutputQuotient
import Init.Data.BitVec.Lemmas
import Init.Data.List.FinRange

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineOutputMask
open QuPRS.AffineOutputQuotient

def decode {n : Nat} (a : BitVec n) (i : Fin n) : Bool :=
  a.getLsbD i.val

theorem decode_and {n : Nat} (a r : BitVec n) (i : Fin n) :
    decode (a &&& r) i = (decode a i && decode r i) := by
  simp [decode]

theorem decode_zero {n : Nat} (i : Fin n) :
    decode (0 : BitVec n) i = false := by
  simp [decode]

theorem decode_injective {n : Nat} (a r : BitVec n)
    (h : decode a = decode r) : a = r := by
  apply BitVec.eq_of_getLsbD_eq_iff.mpr
  intro i hi
  exact congrArg (fun f : Fin n → Bool => f ⟨i,hi⟩) h

def selected {X : Type} (p : X → Bool) : List X → List X
  | [] => []
  | x :: xs => if p x then x :: selected p xs else selected p xs

theorem selected_parity {X : Type} (p f : X → Bool) (xs : List X) :
    parity f (selected p xs) =
      parity (fun x => if p x then f x else false) xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change parity f (if p x then x :: selected p xs else selected p xs) =
        bx (if p x then f x else false)
          (parity (fun t => if p t then f t else false) xs)
      rw [← ih]
      cases p x <;> rfl

def countTrue {X : Type} (f : X → Bool) : List X → Nat
  | [] => 0
  | x :: xs => if f x then countTrue f xs + 1 else countTrue f xs

def odd (n : Nat) : Bool := decide (n % 2 = 1)

theorem odd_succ (n : Nat) : odd (n + 1) = !(odd n) := by
  by_cases h : n % 2 = 1
  · have hn : (n+1) % 2 = 0 := by omega
    simp [odd, h, hn]
  · have hn : (n+1) % 2 = 1 := by omega
    simp [odd, h, hn]

theorem parity_count {X : Type} (f : X → Bool) (xs : List X) :
    parity f xs = odd (countTrue f xs) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change bx (f x) (parity f xs) =
        odd (if f x then countTrue f xs + 1 else countTrue f xs)
      rw [ih]
      cases f x
      · rfl
      · exact (odd_succ (countTrue f xs)).symm

def indices {n : Nat} (r : BitVec n) : List (Fin n) :=
  selected (decode r) (List.finRange n)

def countBits {n : Nat} (a : BitVec n) : Nat :=
  countTrue (decode a) (List.finRange n)

/-- Exact GF(2) dot product for the modeled word popcount. -/
theorem word_dot {n : Nat} (a r : BitVec n) :
    odd (countBits (a &&& r)) = parity (decode a) (indices r) := by
  rw [countBits, ← parity_count, indices, selected_parity]
  apply parity_congr
  intro i _
  rw [decode_and]
  cases decode r i <;> cases decode a i <;> rfl

theorem word_subset_sound {n : Nat} (r keep : BitVec n)
    (h : r &&& keep = r) (i : Fin n) (hi : decode r i = true) :
    decode keep i = true := by
  have hb := congrArg (fun a : BitVec n => decode a i) h
  rw [decode_and, hi] at hb
  exact hb

theorem word_subset_complete {n : Nat} (r keep : BitVec n)
    (h : ∀ i, decode r i = true → decode keep i = true) :
    r &&& keep = r := by
  apply decode_injective
  funext i
  rw [decode_and]
  cases hi : decode r i
  · rfl
  · exact h i hi

theorem selected_mem_sound {X : Type} (p : X → Bool) (xs : List X)
    (x : X) (h : x ∈ selected p xs) : x ∈ xs ∧ p x = true := by
  induction xs with
  | nil => simp [selected] at h
  | cons a rest ih =>
      by_cases ha : p a = true
      · have hm : x ∈ a :: selected p rest := by
          simpa [selected, ha] using h
        rcases List.mem_cons.mp hm with he | ht
        · subst x
          exact ⟨by simp, ha⟩
        · have hs := ih ht
          exact ⟨List.mem_cons_of_mem a hs.1, hs.2⟩
      · have ht : x ∈ selected p rest := by
          simpa [selected, ha] using h
        have hs := ih ht
        exact ⟨List.mem_cons_of_mem a hs.1, hs.2⟩

theorem selected_mem_complete {X : Type} (p : X → Bool) (xs : List X)
    (x : X) (hx : x ∈ xs) (hp : p x = true) : x ∈ selected p xs := by
  induction xs with
  | nil => simp at hx
  | cons a rest ih =>
      rcases List.mem_cons.mp hx with he | ht
      · subst a
        simp [selected, hp]
      · have hs := ih ht
        by_cases ha : p a = true
        · have hm : x ∈ a :: selected p rest := List.mem_cons_of_mem a hs
          simpa [selected, ha] using hm
        · simpa [selected, ha] using hs

theorem indices_membership {n : Nat} (r : BitVec n) (i : Fin n) :
    i ∈ indices r ↔ decode r i = true := by
  constructor
  · intro h
    exact (selected_mem_sound (decode r) (List.finRange n) i h).2
  · intro h
    exact selected_mem_complete (decode r) (List.finRange n) i (List.mem_finRange i) h

theorem indices_subset {n : Nat} (r keep : BitVec n)
    (h : r &&& keep = r) (i : Fin n) (hi : i ∈ indices r) :
    i ∈ indices keep := by
  apply (indices_membership keep i).mpr
  exact word_subset_sound r keep h i ((indices_membership r i).mp hi)

theorem word_dot_offset {n : Nat} (a r : BitVec n) (offset : Bool) :
    bx offset (odd (countBits (a &&& r))) =
      bx offset (parity (decode a) (indices r)) := by
  rw [word_dot]

#print axioms decode_and
#print axioms decode_zero
#print axioms decode_injective
#print axioms selected_parity
#print axioms odd_succ
#print axioms parity_count
#print axioms word_dot
#print axioms word_subset_sound
#print axioms word_subset_complete
#print axioms selected_mem_sound
#print axioms selected_mem_complete
#print axioms indices_membership
#print axioms indices_subset
#print axioms word_dot_offset

end QuPRS.AffineOutputMask
