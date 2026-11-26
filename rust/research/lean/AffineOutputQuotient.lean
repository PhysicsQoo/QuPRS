/-
Research-only affine output quotient semantic certificate.
The row identities and fixed-row support are certificate premises.
No proof of Gaussian elimination, Rust refinement, source admission,
cyclotomic embedding or contraction implementation is claimed.
-/
import Std

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineOutputQuotient

def bx (a b : Bool) : Bool := if a then !b else b

def parity {I : Type} (u : I → Bool) : List I → Bool
  | [] => false
  | j :: js => bx (u j) (parity u js)

theorem parity_congr {I : Type} (u v : I → Bool) (js : List I)
    (h : ∀ j, j ∈ js → u j = v j) : parity u js = parity v js := by
  induction js with
  | nil => rfl
  | cons j js ih =>
    have hj : u j = v j := h j (by simp)
    have ht : parity u js = parity v js := ih (fun k hk => h k (by simp [hk]))
    simp only [parity, hj, ht]

theorem parity_single {I : Type} (u : I → Bool) (j : I) :
    parity u [j] = u j := by
  cases h : u j <;> simp [parity, bx, h]

def reconstruct {I J : Type} (rows : J → List I) (offset : J → Bool)
    (u : I → Bool) (i : J) : Bool := bx (offset i) (parity u (rows i))

def pick {I J : Type} (rep : I → J) (z : J → Bool) (j : I) : Bool := z (rep j)

theorem representative_left_inverse {I J : Type}
    (rows : J → List I) (offset : J → Bool) (rep : I → J)
    (hr : ∀ j, rows (rep j) = [j]) (ho : ∀ j, offset (rep j) = false)
    (u : I → Bool) : pick rep (reconstruct rows offset u) = u := by
  funext j
  simp [pick, reconstruct, hr j, ho j, bx, parity_single]

theorem reconstruction_injective {I J : Type}
    (rows : J → List I) (offset : J → Bool) (rep : I → J)
    (hr : ∀ j, rows (rep j) = [j]) (ho : ∀ j, offset (rep j) = false)
    (u v : I → Bool) (h : reconstruct rows offset u = reconstruct rows offset v) :
    u = v := by
  have hp := congrArg (pick rep) h
  rw [representative_left_inverse rows offset rep hr ho u,
      representative_left_inverse rows offset rep hr ho v] at hp
  exact hp

def agrees {J : Type} (fixed target z : J → Bool) : Prop :=
  ∀ i, fixed i = true → z i = target i

def basisAgrees {I J : Type} (rep : I → J) (fixed target : J → Bool)
    (u : I → Bool) : Prop :=
  ∀ j, fixed (rep j) = true → u j = target (rep j)

/-- Fixed-first certificate: every fixed row uses only fixed representatives.
    Consistency is checked once on the prescribed representative values. -/
theorem fixed_first_equivalence {I J : Type}
    (rows : J → List I) (offset : J → Bool) (rep : I → J)
    (fixed target : J → Bool)
    (hr : ∀ j, rows (rep j) = [j]) (ho : ∀ j, offset (rep j) = false)
    (hs : ∀ i, fixed i = true → ∀ j, j ∈ rows i → fixed (rep j) = true)
    (u : I → Bool) :
    agrees fixed target (reconstruct rows offset u) ↔
    basisAgrees rep fixed target u ∧
    agrees fixed target (reconstruct rows offset (pick rep target)) := by
  constructor
  · intro hf
    have hb : basisAgrees rep fixed target u := by
      intro j hj
      have h := hf (rep j) hj
      have he := congrFun (representative_left_inverse rows offset rep hr ho u) j
      change reconstruct rows offset u (rep j) = u j at he
      exact he.symm.trans h
    refine ⟨hb, ?_⟩
    intro i hi
    have he : parity u (rows i) = parity (pick rep target) (rows i) :=
      parity_congr u (pick rep target) (rows i) (fun j hj => hb j (hs i hi j hj))
    change bx (offset i) (parity (pick rep target) (rows i)) = target i
    rw [← he]
    exact hf i hi
  · rintro ⟨hb, hc⟩
    intro i hi
    have he : parity u (rows i) = parity (pick rep target) (rows i) :=
      parity_congr u (pick rep target) (rows i) (fun j hj => hb j (hs i hi j hj))
    change bx (offset i) (parity u (rows i)) = target i
    rw [he]
    exact hc i hi

theorem fixed_first_contradiction {I J : Type}
    (rows : J → List I) (offset : J → Bool) (rep : I → J)
    (fixed target : J → Bool)
    (hr : ∀ j, rows (rep j) = [j]) (ho : ∀ j, offset (rep j) = false)
    (hs : ∀ i, fixed i = true → ∀ j, j ∈ rows i → fixed (rep j) = true)
    (hc : ¬ agrees fixed target (reconstruct rows offset (pick rep target)))
    (u : I → Bool) : ¬ agrees fixed target (reconstruct rows offset u) := by
  intro h
  exact hc ((fixed_first_equivalence rows offset rep fixed target hr ho hs u).mp h).2

-- Each coefficient is an exact integer; finite path lists may have
-- repeated paths and weights can be negative. Preserve multiplicity.
def fibreSum {Y Z : Type} [DecidableEq Z]
    (f : Y → Z) (w : Y → Int) (z : Z) : List Y → Int
  | [] => 0
  | y :: ys => (if f y = z then w y else 0) + fibreSum f w z ys

theorem fibre_preserved {Y U Z : Type} [DecidableEq U] [DecidableEq Z]
    (f : Y → Z) (g : Y → U) (r : U → Z) (w : Y → Int)
    (hf : ∀ y, f y = r (g y))
    (hi : ∀ u v, r u = r v → u = v)
    (u : U) (ys : List Y) :
    fibreSum f w (r u) ys = fibreSum g w u ys := by
  induction ys with
  | nil => rfl
  | cons y ys ih =>
    by_cases h : g y = u
    · have hz : f y = r u := (hf y).trans (congrArg r h)
      simp [fibreSum, hz, h, ih]
    · have hz : f y ≠ r u := by
        intro e
        exact h (hi (g y) u ((hf y).symm.trans e))
      simp [fibreSum, hz, h, ih]

theorem outside_image_zero {Y U Z : Type} [DecidableEq Z]
    (f : Y → Z) (g : Y → U) (r : U → Z) (w : Y → Int)
    (hf : ∀ y, f y = r (g y)) (z : Z) (hz : ∀ u, r u ≠ z)
    (ys : List Y) : fibreSum f w z ys = 0 := by
  induction ys with
  | nil => rfl
  | cons y ys ih =>
    have hn : f y ≠ z := fun e => hz (g y) ((hf y).symm.trans e)
    simp [fibreSum, hn, ih]

theorem forbidden_fibre_zero_iff {Y U Z : Type} [DecidableEq U] [DecidableEq Z]
    (f : Y → Z) (g : Y → U) (r : U → Z) (w : Y → Int)
    (hf : ∀ y, f y = r (g y))
    (hi : ∀ u v, r u = r v → u = v)
    (bad : Z → Prop) (ys : List Y)
    (imageDec : ∀ z, (∃ u, r u = z) ∨ (∀ u, r u ≠ z)) :
    (∀ z, bad z → fibreSum f w z ys = 0) ↔
    (∀ u, bad (r u) → fibreSum g w u ys = 0) := by
  constructor
  · intro h u hu
    rw [← fibre_preserved f g r w hf hi u ys]
    exact h (r u) hu
  · intro h z hz
    -- Decide membership in the image logically, without selecting a global inverse.
    rcases imageDec z with ⟨u, e⟩ | he
    ·
      rw [← e, fibre_preserved f g r w hf hi u ys]
      exact h u (by rw [e]; exact hz)
    · exact outside_image_zero f g r w hf z he ys

#print axioms parity_congr
#print axioms parity_single
#print axioms representative_left_inverse
#print axioms reconstruction_injective
#print axioms fixed_first_equivalence
#print axioms fixed_first_contradiction
#print axioms fibre_preserved
#print axioms outside_image_zero
#print axioms forbidden_fibre_zero_iff

end QuPRS.AffineOutputQuotient
