/-
Native ANF incidence bridge. Model a row set by a duplicate-free list,
with the constant coefficient separated. Model incidence construction
by OR of one-hot output words. The one-hot bit specification is explicit;
Rust HashSet/BTreeMap internals and actual shifts are not verified here.
-/
import AffineOutputWordCertificate

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineNativeIncidence
open QuPRS.AffineOutputQuotient
open QuPRS.AffineOutputChecker
open QuPRS.AffineOutputMask
open QuPRS.AffineOutputWordCertificate

def buildColumn {n : Nat} (one : Fin n → BitVec n) (p : Fin n → Bool) :
    List (Fin n) → BitVec n
  | [] => 0
  | j :: js => if p j then one j ||| buildColumn one p js else buildColumn one p js

theorem decode_or_word {n : Nat} (a b : BitVec n) (i : Fin n) :
    decode (a ||| b) i = (decode a i || decode b i) := by
  simp [decode]

theorem column_decode {n : Nat} (one : Fin n → BitVec n)
    (p : Fin n → Bool) (js : List (Fin n)) (i : Fin n)
    (hone : ∀ j k, decode (one j) k = decide (k = j)) :
    decode (buildColumn one p js) i = (decide (i ∈ js) && p i) := by
  induction js with
  | nil =>
      change decode (0 : BitVec n) i = false
      exact decode_zero i
  | cons j js ih =>
      -- Use decidable membership explicitly; simp_all can introduce
      -- classical proposition decisions even though Fin equality is decidable.
      by_cases he : i = j
      · subst j
        have hm : decide (i ∈ i :: js) = true :=
          decide_eq_true (List.mem_cons.mpr (Or.inl rfl))
        cases hp : p i with
        | false =>
            have hf : buildColumn one p (i :: js) = buildColumn one p js := by
              simp [buildColumn, hp]
            rw [hf, ih, hm, hp] <;> simp
        | true =>
            have hf : buildColumn one p (i :: js) = one i ||| buildColumn one p js := by
              simp [buildColumn, hp]
            have hb : decode (one i) i = true := by
              rw [hone]
              exact decide_eq_true rfl
            rw [hf, decode_or_word, hb, hm, hp]
      · have hm : decide (i ∈ j :: js) = decide (i ∈ js) := by
          apply Bool.eq_iff_iff.mpr
          simp only [decide_eq_true_eq]
          constructor
          · intro h
            rcases List.mem_cons.mp h with h | h
            · exact False.elim (he h)
            · exact h
          · intro h
            exact List.mem_cons.mpr (Or.inr h)
        cases hp : p j with
        | false =>
            have hf : buildColumn one p (j :: js) = buildColumn one p js := by
              simp [buildColumn, hp]
            rw [hf, ih, hm]
        | true =>
            have hf : buildColumn one p (j :: js) = one j ||| buildColumn one p js := by
              simp [buildColumn, hp]
            have hb : decode (one j) i = false := by
              rw [hone]
              exact decide_eq_false he
            rw [hf, decode_or_word, hb, ih, hm]

def fullColumn {n : Nat} (one : Fin n → BitVec n) (p : Fin n → Bool) : BitVec n :=
  buildColumn one p (List.finRange n)

theorem full_column_decode {n : Nat} (one : Fin n → BitVec n)
    (p : Fin n → Bool) (i : Fin n)
    (hone : ∀ j k, decode (one j) k = decide (k = j)) :
    decode (fullColumn one p) i = p i := by
  rw [fullColumn, column_decode one p _ i hone]
  simp [List.mem_finRange]

theorem selected_nodup {M : Type} (p : M → Bool) (xs : List M)
    (h : xs.Nodup) : (selected p xs).Nodup := by
  induction xs with
  | nil => simp [selected]
  | cons a rest ih =>
      have hn := List.nodup_cons.mp h
      have ht := ih hn.2
      by_cases hp : p a = true
      · have ha : a ∉ selected p rest := by
          intro hm
          exact hn.1 (selected_mem_sound p rest a hm).1
        have hc : (a :: selected p rest).Nodup := List.nodup_cons.mpr ⟨ha, ht⟩
        simpa [selected, hp] using hc
      · simpa [selected, hp] using ht

theorem nodup_same_members_perm {M : Type} (xs ys : List M)
    (hx : xs.Nodup) (hy : ys.Nodup)
    (hm : ∀ a, a ∈ xs ↔ a ∈ ys) : xs.Perm ys := by
  induction xs generalizing ys with
  | nil =>
      cases ys with
      | nil => exact List.Perm.nil
      | cons b bs =>
          have hb := (hm b).mpr (List.mem_cons.mpr (Or.inl rfl))
          exact False.elim (List.not_mem_nil hb)
  | cons a xs ih =>
      have hna := List.nodup_cons.mp hx
      have ha := (hm a).mp (List.mem_cons.mpr (Or.inl rfl))
      obtain ⟨pre, post, hs⟩ := List.append_of_mem ha
      have p : ys.Perm (a :: (pre ++ post)) := by
        rw [hs]
        exact List.perm_middle
      have hn := List.nodup_cons.mp (p.nodup hy)
      have htail : ∀ b, b ∈ xs ↔ b ∈ pre ++ post := by
        intro b
        constructor
        · intro hb
          have hmem := p.mem_iff.mp ((hm b).mp (List.mem_cons.mpr (Or.inr hb)))
          rcases List.mem_cons.mp hmem with he | ht
          · exact False.elim (hna.1 (he ▸ hb))
          · exact ht
        · intro hb
          have hmem := (hm b).mpr (p.mem_iff.mpr (List.mem_cons.mpr (Or.inr hb)))
          rcases List.mem_cons.mp hmem with he | ht
          · exact False.elim (hn.1 (he ▸ hb))
          · exact ht
      have q : xs.Perm (pre ++ post) := by
        apply ih
        · exact hna.2
        · exact hn.2
        · exact htail
      exact (q.cons a).trans p.symm

theorem parity_perm {M : Type} (active : M → Bool) {xs ys : List M}
    (h : xs.Perm ys) : parity active xs = parity active ys := by
  induction h with
  | nil => rfl
  | cons x _ ih => simp only [parity, ih]
  | swap x y rest =>
      simp only [parity]
      cases active x <;> cases active y <;> cases parity active rest <;> rfl
  | trans _ _ ih1 ih2 => exact ih1.trans ih2

def rowColumn {n : Nat} {M : Type} [DecidableEq M]
    (one : Fin n → BitVec n) (terms : Fin n → List M) (m : M) : BitVec n :=
  fullColumn one (fun i => decide (m ∈ terms i))

def nativeEval {n : Nat} {M : Type} (terms : Fin n → List M)
    (constant : Fin n → Bool) (active : M → Bool) (i : Fin n) : Bool :=
  bx (constant i) (parity active (terms i))

/-- A distinct key list covers each original row; no assumed ordering
    correspondence between the source set and map iteration. -/
theorem row_keys_perm {M : Type} [DecidableEq M] (keys row : List M)
    (hk : keys.Nodup) (hr : row.Nodup) (hc : ∀ m, m ∈ row → m ∈ keys) :
    row.Perm (selected (fun m => decide (m ∈ row)) keys) := by
  apply nodup_same_members_perm row _ hr (selected_nodup _ keys hk)
  intro m
  constructor
  · intro hm
    exact selected_mem_complete _ keys m (hc m hm) (decide_eq_true hm)
  · intro hm
    exact of_decide_eq_true (selected_mem_sound _ keys m hm).2

theorem native_incidence_eval {n : Nat} {M : Type} [DecidableEq M]
    (keys : List M) (one : Fin n → BitVec n) (terms : Fin n → List M)
    (constant : Fin n → Bool) (active : M → Bool)
    (hone : ∀ j k, decode (one j) k = decide (k = j))
    (hk : keys.Nodup) (hr : ∀ i, (terms i).Nodup)
    (hc : ∀ i m, m ∈ terms i → m ∈ keys) :
    nativeEval terms constant active =
      evalRow keys (fun m => decode (rowColumn one terms m))
        (decode (fullColumn one constant)) active := by
  funext i
  unfold nativeEval evalRow
  rw [full_column_decode one constant i hone]
  have hp := parity_perm active (row_keys_perm keys (terms i) hk (hr i) (hc i))
  rw [hp, selected_parity]
  apply congrArg (bx (constant i))
  apply parity_congr
  intro m _
  have hcol : decode (rowColumn one terms m) i = decide (m ∈ terms i) := by
    exact full_column_decode one (fun j => decide (m ∈ terms j)) i hone
  change (if decide (m ∈ terms i) then active m else false) =
    (if active m then decode (rowColumn one terms m) i else false)
  rw [hcol]
  cases active m <;> cases decide (m ∈ terms i) <;> rfl

theorem native_word_reconstruction {n : Nat} {M : Type} [DecidableEq M]
    (keys : List M) (one : Fin n → BitVec n) (terms : Fin n → List M)
    (constant : Fin n → Bool) (keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (impossible : Bool)
    (hone : ∀ j k, decode (one j) k = decide (k = j))
    (hk : keys.Nodup) (hr : ∀ i, (terms i).Nodup)
    (hc : ∀ i m, m ∈ terms i → m ∈ keys)
    (h : checkWordCertificate keys (rowColumn one terms) (fullColumn one constant)
      keep mask target fixed value relation offset impossible = true)
    (active : M → Bool) :
    nativeEval terms constant active =
      restore relation offset (project keep (nativeEval terms constant active)) := by
  rw [native_incidence_eval keys one terms constant active hone hk hr hc]
  exact (word_certificate_sound keys (rowColumn one terms) (fullColumn one constant)
    keep mask target fixed value relation offset impossible h).1 active


/-- One-hot output coordinate using the same unsigned shift as Rust. -/
def oneHot {n : Nat} (j : Fin n) : BitVec n :=
  (1 : BitVec n) <<< j.val

theorem one_hot_decode {n : Nat} (j k : Fin n) :
    decode (oneHot j) k = decide (k = j) := by
  have hn : 0 < n := by have h := k.isLt; omega
  simp only [oneHot, decode, BitVec.getLsbD_shiftLeft, BitVec.getLsbD_one]
  rw [decide_eq_true k.isLt, decide_eq_true hn]
  by_cases h : k = j
  · subst k
    rw [decide_eq_false (Nat.lt_irrefl j.val), Nat.sub_self,
      decide_eq_true (show j = j from rfl)] <;> rfl
  · have hne : k.val ≠ j.val := fun he => h (Fin.ext he)
    rw [decide_eq_false h]
    by_cases hl : k.val < j.val
    · rw [decide_eq_true hl] <;> rfl
    · have hd : k.val - j.val ≠ 0 := by omega
      rw [decide_eq_false hl, decide_eq_false hd] <;> rfl

/-- Construct a duplicate-free key list; order is irrelevant to GF(2).
    This is a reference model of the native map's key set. -/
def uniqueKeys {M : Type} [DecidableEq M] : List M → List M
  | [] => []
  | a :: xs => if a ∈ uniqueKeys xs then uniqueKeys xs else a :: uniqueKeys xs

theorem unique_keys_mem {M : Type} [DecidableEq M] (xs : List M) :
    ∀ m, m ∈ uniqueKeys xs ↔ m ∈ xs := by
  induction xs with
  | nil =>
      intro m
      rfl
  | cons a xs ih =>
      intro m
      by_cases ha : a ∈ uniqueKeys xs
      · have ht := (ih a).mp ha
        have he : uniqueKeys (a :: xs) = uniqueKeys xs := by simp [uniqueKeys, ha]
        rw [he, ih m]
        constructor
        · intro hm
          exact List.mem_cons.mpr (Or.inr hm)
        · intro hm
          rcases List.mem_cons.mp hm with hm | hm
          · subst m
            exact ht
          · exact hm
      · have he : uniqueKeys (a :: xs) = a :: uniqueKeys xs := by simp [uniqueKeys, ha]
        rw [he]
        simp only [List.mem_cons, ih]

theorem unique_keys_nodup {M : Type} [DecidableEq M] (xs : List M) :
    (uniqueKeys xs).Nodup := by
  induction xs with
  | nil => simp [uniqueKeys]
  | cons a xs ih =>
      by_cases ha : a ∈ uniqueKeys xs
      · have he : uniqueKeys (a :: xs) = uniqueKeys xs := by simp [uniqueKeys, ha]
        rw [he]
        exact ih
      · have he : uniqueKeys (a :: xs) = a :: uniqueKeys xs := by simp [uniqueKeys, ha]
        rw [he]
        exact List.nodup_cons.mpr ⟨ha, ih⟩

def gatherKeys {n : Nat} {M : Type} [DecidableEq M]
    (terms : Fin n → List M) : List M :=
  uniqueKeys ((List.finRange n).flatMap terms)

theorem gather_keys_nodup {n : Nat} {M : Type} [DecidableEq M]
    (terms : Fin n → List M) : (gatherKeys terms).Nodup :=
  unique_keys_nodup _

theorem gather_keys_coverage {n : Nat} {M : Type} [DecidableEq M]
    (terms : Fin n → List M) (i : Fin n) (m : M) (hm : m ∈ terms i) :
    m ∈ gatherKeys terms := by
  unfold gatherKeys
  apply (unique_keys_mem _ m).mpr
  exact List.mem_flatMap.mpr ⟨i, List.mem_finRange i, hm⟩

theorem gather_keys_exact {n : Nat} {M : Type} [DecidableEq M]
    (terms : Fin n → List M) (m : M) :
    m ∈ gatherKeys terms ↔ ∃ i, m ∈ terms i := by
  unfold gatherKeys
  rw [unique_keys_mem, List.mem_flatMap]
  constructor
  · rintro ⟨i, _, hm⟩
    exact ⟨i, hm⟩
  · rintro ⟨i, hm⟩
    exact ⟨i, List.mem_finRange i, hm⟩

/-- Eliminate the one-hot and key coverage premises at the reference
    model boundary. The original ANF row set remains duplicate-free. -/
theorem gathered_word_reconstruction {n : Nat} {M : Type} [DecidableEq M]
    (terms : Fin n → List M) (constant : Fin n → Bool)
    (keep mask target fixed value : BitVec n)
    (relation : Fin n → BitVec n) (offset : Fin n → Bool) (impossible : Bool)
    (hr : ∀ i, (terms i).Nodup)
    (h : checkWordCertificate (gatherKeys terms) (rowColumn oneHot terms)
      (fullColumn oneHot constant) keep mask target fixed value relation offset impossible = true)
    (active : M → Bool) :
    nativeEval terms constant active =
      restore relation offset (project keep (nativeEval terms constant active)) :=
  native_word_reconstruction (gatherKeys terms) oneHot terms constant
    keep mask target fixed value relation offset impossible one_hot_decode
    (gather_keys_nodup terms) hr (gather_keys_coverage terms) h active

#print axioms decode_or_word
#print axioms column_decode
#print axioms full_column_decode
#print axioms selected_nodup
#print axioms nodup_same_members_perm
#print axioms parity_perm
#print axioms row_keys_perm
#print axioms native_incidence_eval
#print axioms native_word_reconstruction
#print axioms one_hot_decode
#print axioms unique_keys_mem
#print axioms unique_keys_nodup
#print axioms gather_keys_nodup
#print axioms gather_keys_coverage
#print axioms gather_keys_exact
#print axioms gathered_word_reconstruction

end QuPRS.AffineNativeIncidence
