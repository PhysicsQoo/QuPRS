/-
QuPRS P0: polynomial-mask collection semantics over BitVec16 masks.
A list represents GF(2) parity of monomial occurrences; two equal
occurrences cancel. parityNormalize removes duplicates modulo two.
This is the abstract set algebra, not a proof of Rust's memory model,
serialization, sorting or resource accounting.
-/
import BitMask16

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

abbrev Mask16 := BitVec 16
abbrev MaskTerms16 := List Mask16

noncomputable def monomialTruth16 (m : Mask16) (v : Fin 16 → Bool) : Bool := by
  classical
  exact decide (evalMonomial16 m v)

noncomputable def evalMaskTerms16 : MaskTerms16 → (Fin 16 → Bool) → Bool
  | [], _ => false
  | m :: rest, v =>
      (monomialTruth16 m v).xor (evalMaskTerms16 rest v)

/-- Concatenation is GF(2) sum, with duplicate cancellation. -/
theorem evalMaskTerms16_append
    (p q : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (p ++ q) v =
      (evalMaskTerms16 p v).xor (evalMaskTerms16 q v) := by
  induction p with
  | nil => simp [evalMaskTerms16]
  | cons m ms ih =>
      change (monomialTruth16 m v).xor (evalMaskTerms16 (ms ++ q) v) =
        ((monomialTruth16 m v).xor (evalMaskTerms16 ms v)).xor
          (evalMaskTerms16 q v)
      rw [ih]
      cases monomialTruth16 m v <;>
        cases evalMaskTerms16 ms v <;>
        cases evalMaskTerms16 q v <;>
        decide

/-- A squarefree monomial's bitwise OR product has Boolean AND truth. -/
theorem monomialTruth16_or
    (a b : Mask16) (v : Fin 16 → Bool) :
    monomialTruth16 (multiplyMonomials16 a b) v =
      ((monomialTruth16 a v) && (monomialTruth16 b v)) := by
  classical
  simp [monomialTruth16, evalMonomial16_product_iff]

/-- Distributivity of one monomial over GF(2) parity. -/
theorem evalMaskTerms16_monomial_map
    (a : Mask16) (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (p.map (multiplyMonomials16 a)) v =
      ((monomialTruth16 a v) && evalMaskTerms16 p v) := by
  induction p with
  | nil => simp [evalMaskTerms16]
  | cons m ms ih =>
      change
        (monomialTruth16 (multiplyMonomials16 a m) v).xor
          (evalMaskTerms16 (ms.map (multiplyMonomials16 a)) v) =
        ((monomialTruth16 a v) &&
          ((monomialTruth16 m v).xor (evalMaskTerms16 ms v)))
      rw [monomialTruth16_or, ih]
      cases monomialTruth16 a v <;>
        cases monomialTruth16 m v <;>
        cases evalMaskTerms16 ms v <;>
        decide

/-- Pairwise OR-products prior to GF(2) parity reduction. -/
def rawMaskConvolution16 : MaskTerms16 → MaskTerms16 → MaskTerms16
  | [], _ => []
  | m :: rest, q =>
      q.map (multiplyMonomials16 m) ++ rawMaskConvolution16 rest q

/-- Pairwise OR-convolution is Boolean AND, for all finite input lists
    and all Boolean assignments (no circuit path enumeration). -/
theorem evalMaskTerms16_convolution
    (p q : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (rawMaskConvolution16 p q) v =
      ((evalMaskTerms16 p v) && (evalMaskTerms16 q v)) := by
  induction p with
  | nil => rfl
  | cons m ms ih =>
      change evalMaskTerms16
        ((q.map (multiplyMonomials16 m)) ++
          rawMaskConvolution16 ms q) v =
        (((monomialTruth16 m v).xor (evalMaskTerms16 ms v)) &&
          evalMaskTerms16 q v)
      rw [evalMaskTerms16_append,
          evalMaskTerms16_monomial_map, ih]
      cases monomialTruth16 m v <;>
        cases evalMaskTerms16 ms v <;>
        cases evalMaskTerms16 q v <;>
        decide

/-- Toggle one coefficient: remove its first occurrence or insert it. -/
def toggleMask16 (m : Mask16) : MaskTerms16 → MaskTerms16
  | [] => [m]
  | a :: rest =>
      if m = a then rest else a :: toggleMask16 m rest

/-- Toggling changes evaluation by the target monomial. -/
theorem evalMaskTerms16_toggle
    (m : Mask16) (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (toggleMask16 m p) v =
      ((monomialTruth16 m v).xor (evalMaskTerms16 p v)) := by
  induction p with
  | nil => rfl
  | cons a rest ih =>
      by_cases h : m = a
      · subst a
        have heq : toggleMask16 m (m :: rest) = rest := by
          simp [toggleMask16]
        rw [heq]
        change evalMaskTerms16 rest v =
          (monomialTruth16 m v).xor
            ((monomialTruth16 m v).xor (evalMaskTerms16 rest v))
        cases monomialTruth16 m v <;>
          cases evalMaskTerms16 rest v <;>
          decide
      · have heq : toggleMask16 m (a :: rest) =
            a :: toggleMask16 m rest := by
          simp [toggleMask16, h]
        rw [heq]
        change (monomialTruth16 a v).xor
          (evalMaskTerms16 (toggleMask16 m rest) v) =
          (monomialTruth16 m v).xor
            ((monomialTruth16 a v).xor (evalMaskTerms16 rest v))
        rw [ih]
        cases monomialTruth16 m v <;>
          cases monomialTruth16 a v <;>
          cases evalMaskTerms16 rest v <;>
          decide

/-- Normalize duplicate monomials modulo two, not numeric sort order. -/
def parityNormalize16 : MaskTerms16 → MaskTerms16
  | [] => []
  | m :: rest => toggleMask16 m (parityNormalize16 rest)

theorem evalMaskTerms16_normalize
    (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (parityNormalize16 p) v =
      evalMaskTerms16 p v := by
  induction p with
  | nil => rfl
  | cons m rest ih =>
      change evalMaskTerms16
        (toggleMask16 m (parityNormalize16 rest)) v =
        (monomialTruth16 m v).xor (evalMaskTerms16 rest v)
      rw [evalMaskTerms16_toggle, ih]

/-- Toggle can only introduce the chosen mask; all other masks were
    already present in the original list. -/
theorem toggleMask16_membership_limited
    (m x : Mask16) (p : MaskTerms16)
    (h : x ∈ toggleMask16 m p) : x = m ∨ x ∈ p := by
  induction p with
  | nil =>
      simp [toggleMask16] at h
      exact Or.inl h
  | cons a rest ih =>
      by_cases eq : m = a
      · subst a
        have hx : x ∈ rest := by simpa [toggleMask16] using h
        exact Or.inr (by simp [hx])
      · have hx : x = a ∨ x ∈ toggleMask16 m rest := by
          simpa [toggleMask16, eq] using h
        rcases hx with hxa | htail
        · exact Or.inr (by simp [hxa])
        · rcases ih htail with hm | hr
          · exact Or.inl hm
          · exact Or.inr (by simp [hr])

/-- The coefficient toggle preserves a collection of distinct masks. -/
theorem toggleMask16_nodup
    (m : Mask16) (p : MaskTerms16) (h : p.Nodup) :
    (toggleMask16 m p).Nodup := by
  induction p with
  | nil => simp [toggleMask16]
  | cons a rest ih =>
      have hr : rest.Nodup := (List.nodup_cons.mp h).2
      have ha : a ∉ rest := (List.nodup_cons.mp h).1
      by_cases eq : m = a
      · subst a
        simpa [toggleMask16] using hr
      · have hn : a ∉ toggleMask16 m rest := by
          intro hx
          rcases toggleMask16_membership_limited m a rest hx with hm | hrest
          · exact eq hm.symm
          · exact ha hrest
        have hresult : (a :: toggleMask16 m rest).Nodup :=
          List.nodup_cons.mpr ⟨hn, ih hr⟩
        simpa [toggleMask16, eq] using hresult

/-- Parity normalization produces a coefficient set with no duplicates.
    This does not assert any ordering of the terms. -/
theorem parityNormalize16_nodup (p : MaskTerms16) :
    (parityNormalize16 p).Nodup := by
  induction p with
  | nil => simp [parityNormalize16]
  | cons m rest ih =>
      simpa [parityNormalize16] using
        toggleMask16_nodup m (parityNormalize16 rest) ih

/-- The abstract XOR operator for BTreeSet-like coefficient parity. -/
def maskXor16 (p q : MaskTerms16) : MaskTerms16 :=
  parityNormalize16 (p ++ q)

theorem maskXor16_sound
    (p q : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (maskXor16 p q) v =
      ((evalMaskTerms16 p v).xor (evalMaskTerms16 q v)) := by
  rw [maskXor16, evalMaskTerms16_normalize,
      evalMaskTerms16_append]

/-- Parity-normalized OR-convolution of masks. -/
def maskConvolution16 (p q : MaskTerms16) : MaskTerms16 :=
  parityNormalize16 (rawMaskConvolution16 p q)

theorem maskConvolution16_sound
    (p q : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (maskConvolution16 p q) v =
      ((evalMaskTerms16 p v) && (evalMaskTerms16 q v)) := by
  rw [maskConvolution16, evalMaskTerms16_normalize,
      evalMaskTerms16_convolution]

theorem maskXor16_self_zero
    (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (maskXor16 p p) v = false := by
  rw [maskXor16_sound]
  cases evalMaskTerms16 p v <;> decide

theorem maskConvolution16_self_idempotent_eval
    (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (maskConvolution16 p p) v =
      evalMaskTerms16 p v := by
  rw [maskConvolution16_sound]
  cases evalMaskTerms16 p v <;> decide

#print axioms toggleMask16_membership_limited
#print axioms toggleMask16_nodup
#print axioms parityNormalize16_nodup
#print axioms evalMaskTerms16_append
#print axioms monomialTruth16_or
#print axioms evalMaskTerms16_monomial_map
#print axioms evalMaskTerms16_convolution
#print axioms evalMaskTerms16_toggle
#print axioms evalMaskTerms16_normalize
#print axioms maskXor16_sound
#print axioms maskConvolution16_sound
#print axioms maskXor16_self_zero
#print axioms maskConvolution16_self_idempotent_eval

end QuPRS.P0
