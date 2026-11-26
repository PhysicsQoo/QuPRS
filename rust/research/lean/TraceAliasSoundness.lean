/-
Connect the accepted finite weighted-sum and polynomial transport lemmas.
The original sum uses ALL live assignments, not a prefiltered forest.
Forest entailment by the original ANF rows is an explicit premise.
NormSpec, exact coefficient algebra and source admission remain premises;
this file is not a certificate of native Rust execution.
-/
import AliasTransport
set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.TraceAliasSoundness
open QuPRS.AliasForest QuPRS.ForestEnumeration QuPRS.ForestWeightedSum
open QuPRS.ConditionalTrace QuPRS.AliasTransport

def LiveMono (f : Forest) (m : Mono) : Prop :=
  ∀ v, v ∈ m → f.live v

def LiveANF (f : Forest) (q : ANF) : Prop :=
  ∀ m, m ∈ q → LiveMono f m

def LiveRows (f : Forest) (qs : List ANF) : Prop :=
  ∀ q, q ∈ qs → LiveANF f q

def LivePhase {C : Type} (f : Forest) (ps : Phase C) : Prop :=
  ∀ t, t ∈ ps → LiveMono f t.1

theorem mono_live_congr (f : Forest) (a b : Assignment)
    (h : AgreeLive f a b) (m : Mono) (hm : LiveMono f m) :
    monoEval a m = monoEval b m := by
  induction m with
  | nil => rfl
  | cons v m ih =>
      have hv := h v (hm v (List.mem_cons.mpr (Or.inl rfl)))
      have ht : LiveMono f m :=
        fun i hi => hm i (List.mem_cons.mpr (Or.inr hi))
      change (a v && monoEval a m) = (b v && monoEval b m)
      rw [hv, ih ht]

theorem anf_live_congr (f : Forest) (a b : Assignment)
    (h : AgreeLive f a b) (q : ANF) (hq : LiveANF f q) :
    anfEval a q = anfEval b q := by
  induction q with
  | nil => rfl
  | cons m ms ih =>
      have hm := mono_live_congr f a b h m (hq m (List.mem_cons.mpr (Or.inl rfl)))
      have ht : LiveANF f ms :=
        fun k hk => hq k (List.mem_cons.mpr (Or.inr hk))
      change (monoEval a m).xor (anfEval a ms) = (monoEval b m).xor (anfEval b ms)
      rw [hm, ih ht]

theorem rows_live_congr (f : Forest) (a b : Assignment)
    (h : AgreeLive f a b) (qs : List ANF) (hq : LiveRows f qs) :
    rowsOK a qs = rowsOK b qs := by
  induction qs with
  | nil => rfl
  | cons q qs ih =>
      have he := anf_live_congr f a b h q (hq q (List.mem_cons.mpr (Or.inl rfl)))
      have ht : LiveRows f qs :=
        fun r hr => hq r (List.mem_cons.mpr (Or.inr hr))
      change (!(anfEval a q) && rowsOK a qs) = (!(anfEval b q) && rowsOK b qs)
      rw [he, ih ht]

theorem phase_live_congr {C : Type} [Zero C] [Add C]
    (f : Forest) (a b : Assignment) (h : AgreeLive f a b)
    (ps : Phase C) (hp : LivePhase f ps) :
    phaseEval a ps = phaseEval b ps := by
  induction ps with
  | nil => rfl
  | cons t ps ih =>
      obtain ⟨m,c⟩ := t
      have he := mono_live_congr f a b h m (hp (m,c) (List.mem_cons.mpr (Or.inl rfl)))
      have ht : LivePhase f ps :=
        fun r hr => hp r (List.mem_cons.mpr (Or.inr hr))
      change mask (monoEval a m) c + phaseEval a ps =
        mask (monoEval b m) c + phaseEval b ps
      rw [he, ih ht]

/-- Filtering away terms known to be zero does not alter the sum. -/
theorem filter_zero_sum {X A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0+a=a) (p : X → Bool) (term : X → A)
    (hz : ∀ x, p x = false → term x = 0) (xs : List X) :
    sumPaths xs term = sumPaths (xs.filter p) term := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      cases h : p x with
      | false =>
          have hf : (x :: xs).filter p = xs.filter p := by simp [h]
          rw [hf]
          change term x + sumPaths xs term = sumPaths (xs.filter p) term
          rw [hz x h, zl, ih]
      | true =>
          have hf : (x :: xs).filter p = x :: xs.filter p := by simp [h]
          rw [hf]
          change term x + sumPaths xs term = term x + sumPaths (xs.filter p) term
          rw [ih]

/-- All original rows must entail the selected forest. This premise is
    essential: an unrelated forest cannot be imposed to shrink a trace. -/
def EntailsForest (f : Forest) (qs : List ANF) : Prop :=
  ∀ a, rowsOK a qs = true → Satisfies f a

def traceTerm {C A : Type} [Zero C] [Add C] [Zero A]
    (qs : List ANF) (ps : Phase C) (amplitude : C → A) (a : Assignment) : A :=
  mask (rowsOK a qs) (amplitude (phaseEval a ps))

theorem outside_forest_zero {C A : Type} [Zero C] [Add C] [Zero A]
    (f : Forest) (vs : List Nat) (hv : LiveList f vs)
    (qs : List ANF) (ps : Phase C) (amplitude : C → A)
    (he : EntailsForest f qs) (a : Assignment)
    (hf : forestOK f vs a = false) :
    traceTerm qs ps amplitude a = 0 := by
  have hg : rowsOK a qs = false := by
    cases hr : rowsOK a qs with
    | false => rfl
    | true =>
        have ht := (forest_ok_iff f vs hv a).mpr (he a hr)
        rw [hf] at ht
        contradiction
  unfold traceTerm
  rw [hg]
  rfl

theorem full_to_filtered {C A : Type} [Zero C] [Add C] [Zero A] [Add A]
    (zl : ∀ a : A, 0+a=a)
    (f : Forest) (vs : List Nat) (hv : LiveList f vs)
    (qs : List ANF) (ps : Phase C) (amplitude : C → A)
    (he : EntailsForest f qs) :
    sumPaths (enumerate vs) (traceTerm qs ps amplitude) =
    sumPaths (original f vs) (traceTerm qs ps amplitude) :=
  filter_zero_sum zl (forestOK f vs) (traceTerm qs ps amplitude)
    (outside_forest_zero f vs hv qs ps amplitude he) (enumerate vs)

/-- Global syntactic trace identity. No forest prefilter appears on the
    left, no multiplicity factor on the right. All original rows are
    transported; empty zero rows may disappear. The amplitude map is
    arbitrary and the coefficient domain is exact by hypothesis. -/
theorem trace_alias_soundness {C A : Type} [Zero C] [Add C] [Zero A] [Add A]
    (czl : ∀ c : C, 0+c=c)
    (cassoc : ∀ a b c : C, (a+b)+c=a+(b+c))
    (ccomm : ∀ a b : C, a+b=b+a)
    (azl : ∀ a : A, 0+a=a)
    (aassoc : ∀ a b c : A, (a+b)+c=a+(b+c))
    (acomm : ∀ a b : A, a+b=b+a)
    (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (hr : RootList f rs)
    (norm : Mono → Mono) (hn : NormSpec norm)
    (qs : List ANF) (ps : Phase C) (amplitude : C → A)
    (hq : LiveRows f qs) (hp : LivePhase f ps)
    (he : EntailsForest f qs) :
    sumPaths (enumerate vs) (traceTerm qs ps amplitude) =
    sumPaths (enumerate rs)
      (traceTerm (transportRows f norm qs) (transportPhase f norm ps) amplitude) := by
  calc
    _ = sumPaths (original f vs) (traceTerm qs ps amplitude) :=
      full_to_filtered azl f vs hv qs ps amplitude he
    _ = sumPaths (enumerate rs)
          (transported f (fun a => rowsOK a qs) (fun a => amplitude (phaseEval a ps))) :=
      weighted_sum_preservation aassoc acomm f vs rs hv hr
        (fun a => rowsOK a qs) (fun a => amplitude (phaseEval a ps))
        (fun a b h => rows_live_congr f a b h qs hq)
        (fun a b h => congrArg amplitude (phase_live_congr f a b h ps hp))
    _ = _ := by
      apply sum_congr
      intro a
      exact (transported_term czl cassoc ccomm f norm hn a qs ps amplitude).symm

#print axioms mono_live_congr
#print axioms anf_live_congr
#print axioms rows_live_congr
#print axioms phase_live_congr
#print axioms filter_zero_sum
#print axioms outside_forest_zero
#print axioms full_to_filtered
#print axioms trace_alias_soundness
end QuPRS.TraceAliasSoundness
