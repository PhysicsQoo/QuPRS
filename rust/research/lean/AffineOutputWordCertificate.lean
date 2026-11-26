/-
Compose the accepted finite coefficient checker and output word lemmas.
The reduced coordinates are supported on keep: unselected bits are
canonical false, not extra free variables. Integer fibre sums preserve
multiplicity. The native incidence producer, Rust one-hot decoding,
intrinsic and admission/resource behavior are not proved here.
-/
import AffineOutputChecker
import AffineOutputMask

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineOutputWordCertificate
open QuPRS.AffineOutputQuotient
open QuPRS.AffineOutputChecker
open QuPRS.AffineOutputMask

def dot {n : Nat} (a r : BitVec n) : Bool :=
  odd (countBits (a &&& r))

def rowsOf {n : Nat} (relation : Fin n → BitVec n) (i : Fin n) : List (Fin n) :=
  indices (relation i)

def BasisValue {n : Nat} (keep : BitVec n) :=
  {u : Fin n → Bool // ∀ i, decode keep i = false → u i = false}

def project {n : Nat} (keep : BitVec n) (z : Fin n → Bool) : BasisValue keep :=
  ⟨fun i => if decode keep i then z i else false, by
    intro i hi
    simp [hi]⟩

def restore {n : Nat} {keep : BitVec n} (relation : Fin n → BitVec n)
    (offset : Fin n → Bool) (u : BasisValue keep) : Fin n → Bool :=
  reconstruct (rowsOf relation) offset u.val

def checkWordRow {n : Nat} {M : Type} (ms : List M)
    (coeff : M → BitVec n) (constant keep mask : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (i : Fin n) : Bool :=
  decide (relation i &&& keep = relation i) &&
    ((!decode keep i || (decide (rowsOf relation i = [i]) && !offset i)) &&
      ((!decode mask i || decide (relation i &&& (keep &&& mask) = relation i)) &&
        (decide (decode constant i = bx (offset i) (dot constant (relation i))) &&
          checkAll (fun m => decide (decode (coeff m) i = dot (coeff m) (relation i))) ms)))

def checkWordTarget {n : Nat} (mask target value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) : Bool :=
  checkAll (fun i => !decode mask i ||
    decide (bx (offset i) (dot value (relation i)) = decode target i)) (List.finRange n)

def checkWordCertificate {n : Nat} {M : Type} (ms : List M)
    (coeff : M → BitVec n) (constant keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (impossible : Bool) : Bool :=
  decide (fixed = keep &&& mask) &&
    (decide (value = target &&& fixed) &&
      (checkAll (checkWordRow ms coeff constant keep mask relation offset) (List.finRange n) &&
        decide (impossible = !(checkWordTarget mask target value relation offset))))

theorem word_row_premises {n : Nat} {M : Type} (ms : List M)
    (coeff : M → BitVec n) (constant keep mask : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (i : Fin n)
    (h : checkWordRow ms coeff constant keep mask relation offset i = true) :
    (∀ j, j ∈ rowsOf relation i → decode keep j = true) ∧
    (decode keep i = true → rowsOf relation i = [i] ∧ offset i = false) ∧
    (decode mask i = true → ∀ j, j ∈ rowsOf relation i → decode mask j = true) ∧
    (decode constant i = bx (offset i) (parity (decode constant) (rowsOf relation i))) ∧
    (∀ m, m ∈ ms → decode (coeff m) i = parity (decode (coeff m)) (rowsOf relation i)) := by
  have hh : relation i &&& keep = relation i ∧
      (!decode keep i || (decide (rowsOf relation i = [i]) && !offset i)) = true ∧
      (!decode mask i || decide (relation i &&& (keep &&& mask) = relation i)) = true ∧
      decode constant i = bx (offset i) (dot constant (relation i)) ∧
      checkAll (fun m => decide (decode (coeff m) i = dot (coeff m) (relation i))) ms = true := by
    simpa only [checkWordRow, Bool.and_eq_true, decide_eq_true_eq] using h
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · intro j hj
    exact word_subset_sound (relation i) keep hh.1 j ((indices_membership _ _).mp hj)
  · intro hk
    simpa [hk] using hh.2.1
  · intro hf j hj
    have hs : relation i &&& (keep &&& mask) = relation i := by
      simpa [hf] using hh.2.2.1
    have hb := word_subset_sound (relation i) (keep &&& mask) hs j
      ((indices_membership _ _).mp hj)
    rw [decode_and] at hb
    exact (Bool.and_eq_true_iff.mp hb).2
  · simpa only [dot, rowsOf, word_dot] using hh.2.2.2.1
  · intro m hm
    have hc := of_decide_eq_true (check_all_sound _ ms hh.2.2.2.2 m hm)
    simpa only [dot, rowsOf, word_dot] using hc

theorem project_parity {n : Nat} (keep : BitVec n) (z : Fin n → Bool)
    (xs : List (Fin n)) (h : ∀ j, j ∈ xs → decode keep j = true) :
    parity (project keep z).val xs = parity z xs := by
  apply parity_congr
  intro j hj
  simp [project, h j hj]

theorem restore_project {n : Nat} (keep : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool)
    (hs : ∀ i j, j ∈ rowsOf relation i → decode keep j = true)
    (z : Fin n → Bool) :
    restore relation offset (project keep z) = reconstruct (rowsOf relation) offset z := by
  funext i
  change bx (offset i) (parity (project keep z).val (rowsOf relation i)) =
    bx (offset i) (parity z (rowsOf relation i))
  rw [project_parity keep z _ (hs i)]

theorem restore_left_inverse {n : Nat} (keep : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool)
    (hr : ∀ i, decode keep i = true → rowsOf relation i = [i] ∧ offset i = false)
    (u : BasisValue keep) : project keep (restore relation offset u) = u := by
  apply Subtype.ext
  funext i
  change (if decode keep i then restore relation offset u i else false) = u.val i
  cases hk : decode keep i with
  | false =>
      exact (u.property i hk).symm
  | true =>
      have h := hr i hk
      change bx (offset i) (parity u.val (rowsOf relation i)) = u.val i
      rw [h.1, h.2, parity_single]
      rfl

theorem restore_injective {n : Nat} (keep : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool)
    (hr : ∀ i, decode keep i = true → rowsOf relation i = [i] ∧ offset i = false)
    (u v : BasisValue keep) (h : restore relation offset u = restore relation offset v) : u = v := by
  have hp := congrArg (project keep) h
  rw [restore_left_inverse keep relation offset hr u,
    restore_left_inverse keep relation offset hr v] at hp
  exact hp

theorem target_word_iff {n : Nat} (keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool)
    (hf : fixed = keep &&& mask) (hv : value = target &&& fixed)
    (hs : ∀ i, decode mask i = true → ∀ j, j ∈ rowsOf relation i →
      decode keep j = true ∧ decode mask j = true) :
    checkWordTarget mask target value relation offset = true ↔
      agrees (decode mask) (decode target) (reconstruct (rowsOf relation) offset (decode target)) := by
  have he (i : Fin n) (hi : decode mask i = true) :
      dot value (relation i) = parity (decode target) (rowsOf relation i) := by
    rw [dot, word_dot]
    apply parity_congr
    intro j hj
    have hb := hs i hi j hj
    rw [hv, hf, decode_and, decode_and, hb.1, hb.2]
    cases decode target j <;> rfl
  constructor
  · intro h i hi
    have hh := check_all_sound _ (List.finRange n) h i (List.mem_finRange i)
    have hc : bx (offset i) (dot value (relation i)) = decode target i := by
      simpa [hi] using hh
    rw [he i hi] at hc
    exact hc
  · intro h
    unfold checkWordTarget
    apply check_all_complete
    intro i _
    cases hi : decode mask i with
    | false => simp
    | true =>
        have hc := h i hi
        change bx (offset i) (parity (decode target) (rowsOf relation i)) = decode target i at hc
        rw [← he i hi] at hc
        simp [hc]

/-- The model accepts only certificates giving correct reconstruction,
    injectivity on the canonical reduced domain, and exact consistency
    of fixed-coordinate targets. No Gaussian rank claim is required. -/
theorem word_certificate_sound {n : Nat} {M : Type} (ms : List M)
    (coeff : M → BitVec n) (constant keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (impossible : Bool)
    (h : checkWordCertificate ms coeff constant keep mask target fixed value relation offset impossible = true) :
    (∀ active, evalRow ms (fun m => decode (coeff m)) (decode constant) active =
      restore relation offset (project keep (evalRow ms (fun m => decode (coeff m)) (decode constant) active))) ∧
    (∀ u v : BasisValue keep, restore relation offset u = restore relation offset v → u = v) ∧
    (impossible = false ↔ agrees (decode mask) (decode target)
      (reconstruct (rowsOf relation) offset (decode target))) := by
  have hh : fixed = keep &&& mask ∧ value = target &&& fixed ∧
      checkAll (checkWordRow ms coeff constant keep mask relation offset) (List.finRange n) = true ∧
      impossible = !(checkWordTarget mask target value relation offset) := by
    simpa only [checkWordCertificate, Bool.and_eq_true, decide_eq_true_eq] using h
  have row (i : Fin n) := word_row_premises ms coeff constant keep mask relation offset i
    (check_all_sound _ (List.finRange n) hh.2.2.1 i (List.mem_finRange i))
  refine ⟨?_, ?_, ?_⟩
  · intro active
    rw [restore_project keep relation offset (fun i => (row i).1)]
    funext i
    exact column_reconstruction ms (fun m => decode (coeff m)) (decode constant)
      (rowsOf relation) offset id i active (row i).2.2.2.1 (row i).2.2.2.2
  · exact restore_injective keep relation offset (fun i => (row i).2.1)
  · rw [hh.2.2.2, ← target_word_iff keep mask target fixed value relation offset hh.1 hh.2.1
      (fun i hi j hj => ⟨(row i).1 j hj, (row i).2.2.1 hi j hj⟩)]
    cases checkWordTarget mask target value relation offset <;> simp

/-- Compose the accepted word certificate with the finite signed fibre
    theorem. Decidable equality instances are explicit at this boundary;
    the exact coefficient weights can be arbitrary integers. -/
theorem word_fibre_preserved {n : Nat} {M Y : Type}
    (ms : List M) (coeff : M → BitVec n) (constant keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (impossible : Bool)
    (h : checkWordCertificate ms coeff constant keep mask target fixed value relation offset impossible = true)
    (active : Y → M → Bool) (w : Y → Int) (u : BasisValue keep) (ys : List Y)
    [DecidableEq (Fin n → Bool)] [DecidableEq (BasisValue keep)] :
    fibreSum (fun y => evalRow ms (fun m => decode (coeff m)) (decode constant) (active y))
      w (restore relation offset u) ys =
    fibreSum (fun y => project keep (evalRow ms (fun m => decode (coeff m)) (decode constant) (active y)))
      w u ys := by
  have hs := word_certificate_sound ms coeff constant keep mask target fixed value relation offset impossible h
  exact fibre_preserved _ _ (restore relation offset) w (fun y => hs.1 (active y)) hs.2.1 u ys

#print axioms word_row_premises
#print axioms project_parity
#print axioms restore_project
#print axioms restore_left_inverse
#print axioms restore_injective
#print axioms target_word_iff
#print axioms word_certificate_sound
#print axioms word_fibre_preserved

end QuPRS.AffineOutputWordCertificate
