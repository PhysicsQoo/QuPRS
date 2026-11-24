/-
QuPRS P0: polynomial-mask collection semantics over BitVec16 masks.
A list represents GF(2) parity of monomial occurrences; two equal
occurrences cancel. parityNormalize removes duplicates modulo two.
This is the abstract set algebra, not a proof of Rust's memory model,
serialization or resource accounting. Sorted coefficient order and
executable Boolean evaluation are modeled and checked below.
-/
import BitMask16
import Init.Data.List.FinRange

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

abbrev Mask16 := BitVec 16
abbrev MaskTerms16 := List Mask16

/-- Executable finite evaluation; only sixteen Boolean implications,
    with no classical choice and no enumeration of circuit paths. -/
def monomialTruth16 (m : Mask16) (v : Fin 16 → Bool) : Bool :=
  (List.finRange 16).all
    (fun i => decide (decodeMask16 m i = true → v i = true))

theorem monomialTruth16_iff (m : Mask16) (v : Fin 16 → Bool) :
    monomialTruth16 m v = true ↔ evalMonomial16 m v := by
  unfold monomialTruth16 evalMonomial16
  rw [List.all_eq_true]
  constructor
  · intro h i hm
    exact (of_decide_eq_true (h i (List.mem_finRange i))) hm
  · intro h i _
    exact decide_eq_true (h i)

def evalMaskTerms16 : MaskTerms16 → (Fin 16 → Bool) → Bool
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
  apply Bool.eq_iff_iff.mpr
  change monomialTruth16 (multiplyMonomials16 a b) v = true ↔
    (monomialTruth16 a v && monomialTruth16 b v) = true
  rw [Bool.and_eq_true_iff, monomialTruth16_iff,
    monomialTruth16_iff, monomialTruth16_iff,
    evalMonomial16_product_iff]

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


/-- Unsigned numeric order of coefficient masks, exactly the iteration
    order of Rust BTreeSet<u16>. -/
def StrictMasks16 : MaskTerms16 → Prop
  | [] => True
  | a :: rest =>
      (∀ x : Mask16, x ∈ rest → a.toNat < x.toNat) ∧ StrictMasks16 rest

/-- Ordered coefficient toggle: delete an equal word, insert before
    the first greater word, or recurse. No comparison by popcount. -/
def sortedToggle16 (m : Mask16) : MaskTerms16 → MaskTerms16
  | [] => [m]
  | a :: rest =>
      if m = a then rest
      else if m.toNat < a.toNat then m :: a :: rest
      else a :: sortedToggle16 m rest

theorem sortedToggle16_membership_limited
    (m x : Mask16) (p : MaskTerms16)
    (h : x ∈ sortedToggle16 m p) : x = m ∨ x ∈ p := by
  induction p with
  | nil =>
      simp [sortedToggle16] at h
      exact Or.inl h
  | cons a rest ih =>
      by_cases heq : m = a
      · subst a
        have hx : x ∈ rest := by simpa [sortedToggle16] using h
        exact Or.inr (by simp [hx])
      · by_cases hlt : m.toNat < a.toNat
        · have hx : x ∈ m :: a :: rest := by
            simpa [sortedToggle16, heq, hlt] using h
          exact List.mem_cons.mp hx
        · have hx : x ∈ a :: sortedToggle16 m rest := by
            simpa [sortedToggle16, heq, hlt] using h
          rcases List.mem_cons.mp hx with ha | hr
          · exact Or.inr (by simp [ha])
          · rcases ih hr with hm | hs
            · exact Or.inl hm
            · exact Or.inr (by simp [hs])

/-- Both insertion and removal preserve strictly ascending masks. -/
theorem sortedToggle16_strict
    (m : Mask16) (p : MaskTerms16) (h : StrictMasks16 p) :
    StrictMasks16 (sortedToggle16 m p) := by
  induction p with
  | nil => simp [sortedToggle16, StrictMasks16]
  | cons a rest ih =>
      change (∀ x : Mask16, x ∈ rest → a.toNat < x.toNat) ∧
        StrictMasks16 rest at h
      rcases h with ⟨hhead, hrest⟩
      by_cases heq : m = a
      · subst a
        simpa [sortedToggle16] using hrest
      · by_cases hlt : m.toNat < a.toNat
        · have ht : sortedToggle16 m (a :: rest) = m :: a :: rest := by
            simp [sortedToggle16, heq, hlt]
          rw [ht]
          change (∀ x : Mask16, x ∈ a :: rest → m.toNat < x.toNat) ∧
            StrictMasks16 (a :: rest)
          constructor
          · intro x hx
            rcases List.mem_cons.mp hx with hxa | hxr
            · subst x
              exact hlt
            · exact Nat.lt_trans hlt (hhead x hxr)
          · exact ⟨hhead, hrest⟩
        · have hne : m.toNat ≠ a.toNat := by
            intro hn
            exact heq (BitVec.eq_of_toNat_eq hn)
          have ham : a.toNat < m.toNat := by omega
          have ht : sortedToggle16 m (a :: rest) =
              a :: sortedToggle16 m rest := by
            simp [sortedToggle16, heq, hlt]
          rw [ht]
          change
            (∀ x : Mask16, x ∈ sortedToggle16 m rest →
              a.toNat < x.toNat) ∧ StrictMasks16 (sortedToggle16 m rest)
          constructor
          · intro x hx
            rcases sortedToggle16_membership_limited m x rest hx with hm | hr
            · subst x
              exact ham
            · exact hhead x hr
          · exact ih hrest

theorem eval_sortedToggle16
    (m : Mask16) (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (sortedToggle16 m p) v =
      ((monomialTruth16 m v).xor (evalMaskTerms16 p v)) := by
  induction p with
  | nil => rfl
  | cons a rest ih =>
      by_cases heq : m = a
      · subst a
        have ht : sortedToggle16 m (m :: rest) = rest := by
          simp [sortedToggle16]
        rw [ht]
        change evalMaskTerms16 rest v =
          (monomialTruth16 m v).xor
            ((monomialTruth16 m v).xor (evalMaskTerms16 rest v))
        cases monomialTruth16 m v <;>
          cases evalMaskTerms16 rest v <;> decide
      · by_cases hlt : m.toNat < a.toNat
        · have ht : sortedToggle16 m (a :: rest) = m :: a :: rest := by
            simp [sortedToggle16, heq, hlt]
          rw [ht]
          rfl
        · have ht : sortedToggle16 m (a :: rest) =
              a :: sortedToggle16 m rest := by
            simp [sortedToggle16, heq, hlt]
          rw [ht]
          change (monomialTruth16 a v).xor
            (evalMaskTerms16 (sortedToggle16 m rest) v) =
            (monomialTruth16 m v).xor
              ((monomialTruth16 a v).xor (evalMaskTerms16 rest v))
          rw [ih]
          cases monomialTruth16 m v <;>
            cases monomialTruth16 a v <;>
            cases evalMaskTerms16 rest v <;> decide

def sortedNormalize16 : MaskTerms16 → MaskTerms16
  | [] => []
  | m :: rest => sortedToggle16 m (sortedNormalize16 rest)

theorem sortedNormalize16_strict (p : MaskTerms16) :
    StrictMasks16 (sortedNormalize16 p) := by
  induction p with
  | nil => simp [sortedNormalize16, StrictMasks16]
  | cons m rest ih =>
      exact sortedToggle16_strict m (sortedNormalize16 rest) ih

theorem eval_sortedNormalize16 (p : MaskTerms16) (v : Fin 16 → Bool) :
    evalMaskTerms16 (sortedNormalize16 p) v = evalMaskTerms16 p v := by
  induction p with
  | nil => rfl
  | cons m rest ih =>
      change evalMaskTerms16 (sortedToggle16 m (sortedNormalize16 rest)) v =
        (monomialTruth16 m v).xor (evalMaskTerms16 rest v)
      rw [eval_sortedToggle16, ih]

theorem strictMasks16_nodup (p : MaskTerms16) (h : StrictMasks16 p) :
    p.Nodup := by
  induction p with
  | nil => simp
  | cons a rest ih =>
      change (∀ x : Mask16, x ∈ rest → a.toNat < x.toNat) ∧
        StrictMasks16 rest at h
      apply List.nodup_cons.mpr
      constructor
      · intro ha
        exact (Nat.lt_irrefl a.toNat) (h.1 a ha)
      · exact ih h.2

def sortedMaskXor16 (p q : MaskTerms16) : MaskTerms16 :=
  sortedNormalize16 (p ++ q)

def sortedMaskConvolution16 (p q : MaskTerms16) : MaskTerms16 :=
  sortedNormalize16 (rawMaskConvolution16 p q)

theorem sortedMaskXor16_correct (p q : MaskTerms16) (v : Fin 16 → Bool) :
    StrictMasks16 (sortedMaskXor16 p q) ∧
    evalMaskTerms16 (sortedMaskXor16 p q) v =
      ((evalMaskTerms16 p v).xor (evalMaskTerms16 q v)) := by
  constructor
  · exact sortedNormalize16_strict (p ++ q)
  · rw [sortedMaskXor16, eval_sortedNormalize16, evalMaskTerms16_append]

theorem sortedMaskConvolution16_correct
    (p q : MaskTerms16) (v : Fin 16 → Bool) :
    StrictMasks16 (sortedMaskConvolution16 p q) ∧
    evalMaskTerms16 (sortedMaskConvolution16 p q) v =
      ((evalMaskTerms16 p v) && (evalMaskTerms16 q v)) := by
  constructor
  · exact sortedNormalize16_strict (rawMaskConvolution16 p q)
  · rw [sortedMaskConvolution16, eval_sortedNormalize16,
      evalMaskTerms16_convolution]

/-- Direct bridge to Rust's (mask & assignment) == mask evaluator. -/
theorem monomialTruth16_word (m word : Mask16) :
    monomialTruth16 m (decodeMask16 word) = ((m &&& word) == m) := by
  apply Bool.eq_iff_iff.mpr
  change monomialTruth16 m (decodeMask16 word) = true ↔
    ((m &&& word) == m) = true
  rw [monomialTruth16_iff]
  constructor
  · intro h
    have he : m &&& word = m := by
      apply decodeMask16_injective
      funext i
      rw [decodeMask16_and]
      cases hm : decodeMask16 m i
      · rfl
      · have hv := h i hm
        simp [hv]
    simp [he]
  · intro h i hm
    have he : m &&& word = m := of_beq_eq_true h
    have hb := congrArg (fun x => decodeMask16 x i) he
    rw [decodeMask16_and, hm] at hb
    simpa using hb

#print axioms monomialTruth16_iff
#print axioms sortedToggle16_membership_limited
#print axioms sortedToggle16_strict
#print axioms eval_sortedToggle16
#print axioms sortedNormalize16_strict
#print axioms eval_sortedNormalize16
#print axioms strictMasks16_nodup
#print axioms sortedMaskXor16_correct
#print axioms sortedMaskConvolution16_correct
#print axioms monomialTruth16_word

/- Executable, small known-answer check of the exact Lean model.
   No native_decide is used to establish any theorem. -/
#eval (sortedNormalize16 [32768#16, 1#16, 32768#16, 0#16]).map BitVec.toNat
#eval monomialTruth16 (32768#16) (decodeMask16 (32768#16))

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
