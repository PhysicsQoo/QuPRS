/-
Constructive fixed-width low-bit semantics.
Do not use bv_decide/native_decide: the pinned toolchain's reflection
uses a generated native axiom, which is outside this research trust gate.
Split the least significant bit via concat, use exact Nat arithmetic
and Boolean truth tables, then prove traversal by induction.
-/
import Init.Data.BitVec.Lemmas
set_option autoImplicit false
set_option warningAsError true
set_option maxHeartbeats 4000000
set_option maxRecDepth 4096
namespace QuPRS.AffineMachineWord

abbrev Word := BitVec 64

def lowBit {w : Nat} (m : BitVec w) : BitVec w := m &&& (-m)
def clear {w : Nat} (m : BitVec w) : BitVec w := m ^^^ lowBit m

theorem neg_concat_even {w : Nat} (x : BitVec w) :
    -(x.concat false) = (-x).concat false := by
  by_cases hz : x = 0
  · subst x
    simp
  · have hn : x.toNat ≠ 0 := fun h => hz (BitVec.toNat_eq.mpr h)
    have hp : (0 : BitVec w) < x := by
      change 0 < x.toNat
      omega
    have hq : (0 : BitVec (w+1)) < x.concat false := by
      change 0 < (x.concat false).toNat
      rw [BitVec.toNat_concat]
      omega
    apply BitVec.toNat_eq.mpr
    simp only [BitVec.toNat_neg_of_pos hq, BitVec.toNat_concat,
      BitVec.toNat_neg_of_pos hp, Nat.pow_succ]
    change 2^w * 2 - (x.toNat * 2 + 0) = (2^w - x.toNat) * 2 + 0
    omega

theorem neg_concat_odd {w : Nat} (x : BitVec w) :
    -(x.concat true) = (~~~x).concat true := by
  have hq : (0 : BitVec (w+1)) < x.concat true := by
    change 0 < (x.concat true).toNat
    rw [BitVec.toNat_concat]
    change 0 < x.toNat * 2 + 1
    omega
  have hx := x.isLt
  apply BitVec.toNat_eq.mpr
  simp only [BitVec.toNat_neg_of_pos hq, BitVec.toNat_concat,
    BitVec.toNat_not, Nat.pow_succ]
  change 2^w * 2 - (x.toNat * 2 + 1) = (2^w - 1 - x.toNat) * 2 + 1
  omega

theorem sub_concat_even {w : Nat} (x : BitVec w) :
    x.concat false - 1 = (x-1).concat true := by
  calc
    _ = ~~~(-(x.concat false)) := (BitVec.not_neg _).symm
    _ = (~~~(-x)).concat true := by rw [neg_concat_even, BitVec.not_concat]; rfl
    _ = _ := by rw [BitVec.not_neg]

theorem sub_concat_odd {w : Nat} (x : BitVec w) :
    x.concat true - 1 = x.concat false := by
  calc
    _ = ~~~(-(x.concat true)) := (BitVec.not_neg _).symm
    _ = _ := by rw [neg_concat_odd, BitVec.not_concat]; simp

theorem low_concat_false {w : Nat} (x : BitVec w) :
    lowBit (x.concat false) = (lowBit x).concat false := by
  unfold lowBit
  rw [neg_concat_even, BitVec.concat_and_concat]
  rfl

theorem low_concat_true {w : Nat} (x : BitVec w) :
    lowBit (x.concat true) = (0 : BitVec w).concat true := by
  unfold lowBit
  rw [neg_concat_odd, BitVec.concat_and_concat, BitVec.and_not_self]
  rfl

theorem low_zero : lowBit (0 : Word) = 0 := by
  decide

theorem clear_zero : clear (0 : Word) = 0 := by
  decide

theorem clear_identity {w : Nat} (m : BitVec w) : clear m = m &&& (m - 1) := by
  rw [← BitVec.not_neg]
  apply BitVec.eq_of_getLsbD_eq_iff.mpr
  intro i hi
  simp only [clear, lowBit, BitVec.getLsbD_xor, BitVec.getLsbD_and,
    BitVec.getLsbD_not, decide_eq_true hi, Bool.true_and]
  cases m.getLsbD i <;> cases (-m).getLsbD i <;> rfl

theorem clear_concat_false {w : Nat} (x : BitVec w) :
    clear (x.concat false) = (clear x).concat false := by
  unfold clear
  rw [low_concat_false, BitVec.concat_xor_concat]
  rfl

theorem clear_concat_true {w : Nat} (x : BitVec w) :
    clear (x.concat true) = x.concat false := by
  rw [clear_identity, sub_concat_odd, BitVec.concat_and_concat, BitVec.and_self]
  rfl

theorem count_zero_iff {w : Nat} (m : BitVec w) :
    m.cpop.toNat = 0 ↔ m = 0 := by
  refine BitVec.concat_induction (motive := fun n x => x.cpop.toNat = 0 ↔ x = (0 : BitVec n)) ?_ ?_ m
  · decide
  · intro n x b ih
    constructor
    · intro h
      rw [BitVec.toNat_cpop_concat] at h
      cases b
      · have hx : x.cpop.toNat = 0 := by
          change 0 + x.cpop.toNat = 0 at h
          omega
        rw [ih.mp hx, BitVec.zero_concat_false]
      · change 1 + x.cpop.toNat = 0 at h
        omega
    · intro h
      rw [h, BitVec.cpop_zero]
      rfl

theorem count_clear {w : Nat} (m : BitVec w) :
    (clear m).cpop.toNat = m.cpop.toNat - 1 := by
  refine BitVec.concat_induction (motive := fun _ x =>
    (clear x).cpop.toNat = x.cpop.toNat - 1) ?_ ?_ m
  · decide
  · intro n x b ih
    cases b
    · rw [clear_concat_false, BitVec.toNat_cpop_concat, BitVec.toNat_cpop_concat, ih]
      rfl
    · rw [clear_concat_true, BitVec.toNat_cpop_concat, BitVec.toNat_cpop_concat]
      change 0 + x.cpop.toNat = (1 + x.cpop.toNat) - 1
      omega

theorem low_nonzero {w : Nat} (m : BitVec w) (h : m ≠ 0) : lowBit m ≠ 0 := by
  intro hl
  have he : clear m = m := by simp [clear, hl]
  have hc := count_clear m
  rw [he] at hc
  exact h ((count_zero_iff m).mp (by omega))

theorem low_onehot {w : Nat} (m : BitVec w) : lowBit m &&& (lowBit m - 1) = 0 := by
  refine BitVec.concat_induction (motive := fun n x =>
    lowBit x &&& (lowBit x - 1) = (0 : BitVec n)) ?_ ?_ m
  · decide
  · intro n x b ih
    cases b
    · rw [low_concat_false, sub_concat_even, BitVec.concat_and_concat, ih]
      exact BitVec.zero_concat_false
    · rw [low_concat_true, sub_concat_odd, BitVec.concat_and_concat, BitVec.and_self]
      exact BitVec.zero_concat_false

theorem low_subset {w : Nat} (m : BitVec w) : lowBit m &&& m = lowBit m := by
  apply BitVec.eq_of_getLsbD_eq_iff.mpr
  intro i _
  simp only [lowBit, BitVec.getLsbD_and]
  cases m.getLsbD i <;> cases (-m).getLsbD i <;> rfl

theorem low_minimal_aux {w : Nat} (m : BitVec w) : m &&& (lowBit m - 1) = 0 := by
  refine BitVec.concat_induction (motive := fun n x =>
    x &&& (lowBit x - 1) = (0 : BitVec n)) ?_ ?_ m
  · decide
  · intro n x b ih
    cases b
    · rw [low_concat_false, sub_concat_even, BitVec.concat_and_concat, ih]
      exact BitVec.zero_concat_false
    · rw [low_concat_true, sub_concat_odd, BitVec.concat_and_concat, BitVec.and_zero]
      exact BitVec.zero_concat_false

theorem low_minimal {w : Nat} (m : BitVec w) :
    m &&& (lowBit m - 1) = 0 ∨ m = 0 :=
  Or.inl (low_minimal_aux m)

theorem clear_lt {w : Nat} (m : BitVec w) (h : m ≠ 0) : clear m < m := by
  have hn : clear m ≠ m := by
    intro he
    have hc := count_clear m
    rw [he] at hc
    exact h ((count_zero_iff m).mp (by omega))
  change (clear m).toNat < m.toNat
  have hle : (clear m).toNat ≤ m.toNat := by
    rw [clear_identity, BitVec.toNat_and]
    exact Nat.and_le_left
  exact Nat.lt_of_le_of_ne hle (fun e => hn (BitVec.toNat_eq.mpr e))

theorem split_mask {w : Nat} (m : BitVec w) :
    lowBit m ||| clear m = m ∧ lowBit m &&& clear m = 0 := by
  constructor
  · apply BitVec.eq_of_getLsbD_eq_iff.mpr
    intro i _
    simp only [lowBit, clear, BitVec.getLsbD_or, BitVec.getLsbD_and, BitVec.getLsbD_xor]
    cases m.getLsbD i <;> cases (-m).getLsbD i <;> rfl
  · apply BitVec.eq_of_getLsbD_eq_iff.mpr
    intro i _
    simp only [lowBit, clear, BitVec.getLsbD_and, BitVec.getLsbD_xor, BitVec.getLsbD_zero]
    cases m.getLsbD i <;> cases (-m).getLsbD i <;> rfl

theorem merge_partition (b p r m : Word)
    (hu : b ||| (p ||| r) = m) (hb : b &&& (p ||| r) = 0)
    (hp : p &&& r = 0) :
    (b ||| p) ||| r = m ∧ (b ||| p) &&& r = 0 := by
  constructor
  · rw [BitVec.or_assoc, hu]
  · apply BitVec.eq_of_getLsbD_eq_iff.mpr
    intro i _
    have h1 := congrArg (fun z : Word => z.getLsbD i) hb
    have h2 := congrArg (fun z : Word => z.getLsbD i) hp
    simp only [BitVec.getLsbD_and, BitVec.getLsbD_or, BitVec.getLsbD_zero] at h1 h2 ⊢
    cases b.getLsbD i <;> cases p.getLsbD i <;> cases r.getLsbD i <;> simp_all

theorem select_distributes (a b p : Word) :
    (a &&& b) ||| (a &&& p) = a &&& (b ||| p) :=
  (BitVec.and_or_distrib_left a b p).symm

theorem low_projection {w : Nat} (m : BitVec w) :
    ∀ a : BitVec w, a &&& lowBit m = 0 ∨ a &&& lowBit m = lowBit m := by
  refine BitVec.concat_induction (motive := fun n x =>
    ∀ a : BitVec n, a &&& lowBit x = 0 ∨ a &&& lowBit x = lowBit x) ?_ ?_ m
  · intro a
    exact Or.inl BitVec.of_length_zero
  · intro n x b ih a
    let t := a.extractLsb' 1 n
    let c := a.getLsb 0
    have ha : t.concat c = a := BitVec.concat_extractLsb'_getLsb
    rw [← ha]
    cases b
    · rw [low_concat_false, BitVec.concat_and_concat]
      rcases ih t with hz | he
      · rw [hz, Bool.and_false, BitVec.zero_concat_false]
        exact Or.inl rfl
      · rw [he, Bool.and_false]
        exact Or.inr rfl
    · rw [low_concat_true, BitVec.concat_and_concat, BitVec.and_zero]
      cases c
      · exact Or.inl BitVec.zero_concat_false
      · exact Or.inr rfl

theorem selected_digit (a b : Word) (h : b &&& (b - 1) = 0) :
    (if a &&& b = 0 then 0 else b) = a &&& b := by
  have hc : clear b = 0 := (clear_identity b).trans h
  have he : b = lowBit b := BitVec.xor_eq_zero_iff.mp hc
  have hp := low_projection b a
  rw [← he] at hp
  rcases hp with hz | hs
  · rw [ite_eq_left hz, hz]
  · by_cases hz : a &&& b = 0
    · rw [ite_eq_left hz, hz]
    · rw [ite_eq_right hz, hs]

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
      simp
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
      simp
  | succ n ih =>
      change (if a &&& lowBit m = 0 then 0 else lowBit m) |||
        reconstruct n (clear m) a = a &&& (lowBit m ||| processed n (clear m))
      rw [selected_digit a (lowBit m) (low_onehot m), ih]
      exact select_distributes a (lowBit m) (processed n (clear m))

theorem reconstruct_complete (fuel : Nat) (m a : Word)
    (h : remaining fuel m = 0) :
    reconstruct fuel m a = a &&& m := by
  rw [reconstruct_prefix, processed_complete fuel m h]


/-- Precise padded traversal count. Zero padding never changes the mask. -/
theorem remaining_count (fuel : Nat) (m : Word) :
    (remaining fuel m).cpop.toNat = m.cpop.toNat - fuel := by
  induction fuel generalizing m with
  | zero => simp [remaining]
  | succ n ih =>
      change (remaining n (clear m)).cpop.toNat = m.cpop.toNat - (n+1)
      rw [ih, count_clear]
      omega

theorem remaining_iff_count (fuel : Nat) (m : Word) :
    remaining fuel m = 0 ↔ m.cpop.toNat ≤ fuel := by
  rw [← count_zero_iff (remaining fuel m), remaining_count]
  omega

theorem exact_count_finish (m : Word) :
    remaining m.cpop.toNat m = 0 :=
  (remaining_iff_count _ _).mpr (Nat.le_refl _)

theorem admitted_width_finish (m : Word) (h : m.cpop.toNat ≤ 12) :
    remaining 12 m = 0 :=
  (remaining_iff_count _ _).mpr h

theorem reconstruct_at_count (m a : Word) :
    reconstruct m.cpop.toNat m a = a &&& m :=
  reconstruct_complete _ m a (exact_count_finish m)

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
#print axioms neg_concat_even
#print axioms neg_concat_odd
#print axioms sub_concat_even
#print axioms sub_concat_odd
#print axioms low_concat_false
#print axioms low_concat_true
#print axioms clear_concat_false
#print axioms clear_concat_true
#print axioms count_zero_iff
#print axioms count_clear
#print axioms low_minimal_aux
#print axioms low_projection
#print axioms remaining_count
#print axioms remaining_iff_count
#print axioms exact_count_finish
#print axioms admitted_width_finish
#print axioms reconstruct_at_count
end QuPRS.AffineMachineWord
