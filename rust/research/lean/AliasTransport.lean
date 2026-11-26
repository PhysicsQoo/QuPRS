/-
Alias monomial/ANF/phase transport, algebraic reference specification.
Lists model supports; equality of normalized lists is used for merging.
Sort/dedup membership and Rust exact coefficient representation refinement
remain separate, as does justification of the chosen forest edges.
-/
import ForestWeightedSum
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AliasTransport
open QuPRS.AliasForest QuPRS.ForestEnumeration QuPRS.ConditionalTrace

abbrev Mono := List Nat
abbrev ANF := List Mono

def monoEval (a : Assignment) (m : Mono) : Bool := m.all a

def mappedMono (f : Forest) (m : Mono) : Mono := m.map (root f)

theorem mono_map (f : Forest) (a : Assignment) (m : Mono) :
    monoEval a (mappedMono f m) = monoEval (extend f a) m := by
  induction m with
  | nil => rfl
  | cons v m ih =>
      change (a (root f v) && monoEval a (mappedMono f m)) =
        (a (root f v) && monoEval (extend f a) m)
      rw [ih]

/-- Any canonical support preserving membership (including sort/dedup)
    preserves Boolean monomial evaluation. No multiplicity assumption. -/
theorem mono_support (a : Assignment) (m k : Mono)
    (h : ∀ v, v ∈ m ↔ v ∈ k) : monoEval a m = monoEval a k := by
  have he : monoEval a m = true ↔ monoEval a k = true := by
    unfold monoEval
    constructor
    · intro hm
      apply List.all_eq_true.mpr
      intro v hv
      exact List.all_eq_true.mp hm v ((h v).mpr hv)
    · intro hk
      apply List.all_eq_true.mpr
      intro v hv
      exact List.all_eq_true.mp hk v ((h v).mp hv)
  cases hm : monoEval a m <;> cases hk : monoEval a k
  · rfl
  · have hf := he.mpr hk
    rw [hm] at hf
    contradiction
  · have hf := he.mp hm
    rw [hk] at hf
    contradiction
  · rfl

def NormSpec (norm : Mono → Mono) : Prop :=
  ∀ m v, v ∈ norm m ↔ v ∈ m

def transportMono (f : Forest) (norm : Mono → Mono) (m : Mono) : Mono :=
  norm (mappedMono f m)

theorem mono_transport (f : Forest) (norm : Mono → Mono)
    (hn : NormSpec norm) (a : Assignment) (m : Mono) :
    monoEval a (transportMono f norm m) = monoEval (extend f a) m := by
  exact (mono_support a _ _ (hn _)).trans (mono_map f a m)

def anfEval (a : Assignment) : ANF → Bool
  | [] => false
  | m :: ms => (monoEval a m).xor (anfEval a ms)

-- Toggle one normalized monomial, mirroring F2 coefficient cancellation.
-- Explicit DecidableEq on Nat lists, not equality of assignment functions.
def toggle (m : Mono) : ANF → ANF
  | [] => [m]
  | k :: ks => if m = k then ks else k :: toggle m ks

theorem xor_cancel (x y : Bool) : x.xor (x.xor y) = y := by
  cases x <;> cases y <;> rfl

theorem xor_exchange (x y z : Bool) : x.xor (y.xor z) = y.xor (x.xor z) := by
  cases x <;> cases y <;> cases z <;> rfl

theorem anf_toggle (a : Assignment) (m : Mono) (q : ANF) :
    anfEval a (toggle m q) = (monoEval a m).xor (anfEval a q) := by
  induction q with
  | nil => rfl
  | cons k ks ih =>
      simp only [toggle]
      split
      · rename_i h
        subst k
        simp only [anfEval, xor_cancel]
      · simp only [anfEval, ih, xor_exchange (monoEval a k) (monoEval a m)]

def transportANF (f : Forest) (norm : Mono → Mono) : ANF → ANF
  | [] => []
  | m :: ms => toggle (transportMono f norm m) (transportANF f norm ms)

theorem anf_transport (f : Forest) (norm : Mono → Mono)
    (hn : NormSpec norm) (a : Assignment) (q : ANF) :
    anfEval a (transportANF f norm q) = anfEval (extend f a) q := by
  induction q with
  | nil => rfl
  | cons m ms ih =>
      simp only [transportANF, anf_toggle, mono_transport f norm hn, ih, anfEval]

def rowsOK (a : Assignment) (qs : List ANF) : Bool :=
  qs.all (fun q => !(anfEval a q))

def transportRows (f : Forest) (norm : Mono → Mono) (qs : List ANF) : List ANF :=
  (qs.map (transportANF f norm)).filter (fun q => !q.isEmpty)

theorem rows_drop_empty (a : Assignment) (qs : List ANF) :
    rowsOK a (qs.filter (fun q => !q.isEmpty)) = rowsOK a qs := by
  induction qs with
  | nil => rfl
  | cons q qs ih =>
      cases q with
      | nil => exact ih
      | cons m ms =>
          change (!(anfEval a (m :: ms)) && rowsOK a (qs.filter (fun q => !q.isEmpty))) =
            (!(anfEval a (m :: ms)) && rowsOK a qs)
          rw [ih]

theorem rows_map (f : Forest) (norm : Mono → Mono)
    (hn : NormSpec norm) (a : Assignment) (qs : List ANF) :
    rowsOK a (qs.map (transportANF f norm)) = rowsOK (extend f a) qs := by
  induction qs with
  | nil => rfl
  | cons q qs ih =>
      change (!(anfEval a (transportANF f norm q)) && rowsOK a (qs.map (transportANF f norm))) =
        (!(anfEval (extend f a) q) && rowsOK (extend f a) qs)
      rw [anf_transport f norm hn, ih]

theorem rows_transport (f : Forest) (norm : Mono → Mono)
    (hn : NormSpec norm) (a : Assignment) (qs : List ANF) :
    rowsOK a (transportRows f norm qs) = rowsOK (extend f a) qs :=
  (rows_drop_empty a _).trans (rows_map f norm hn a qs)

abbrev Phase (C : Type) := List (Mono × C)

def phaseEval {C : Type} [Zero C] [Add C] (a : Assignment) : Phase C → C
  | [] => 0
  | (m,c) :: ps => mask (monoEval a m) c + phaseEval a ps

-- Coefficient addition in an abstract exact additive domain.
-- Keeping zero coefficients is semantically harmless; native zero pruning
-- and modulo/overflow properties are separate representation obligations.
def phaseInsert {C : Type} [Add C] (m : Mono) (c : C) : Phase C → Phase C
  | [] => [(m,c)]
  | (k,d) :: ps => if m = k then (k,c+d) :: ps else (k,d) :: phaseInsert m c ps

theorem phase_insert {C : Type} [Zero C] [Add C]
    (zl : ∀ c : C, 0+c=c)
    (assoc : ∀ a b c : C, (a+b)+c=a+(b+c))
    (comm : ∀ a b : C, a+b=b+a)
    (a : Assignment) (m : Mono) (c : C) (ps : Phase C) :
    phaseEval a (phaseInsert m c ps) = mask (monoEval a m) c + phaseEval a ps := by
  induction ps with
  | nil => rfl
  | cons t ps ih =>
      obtain ⟨k,d⟩ := t
      simp only [phaseInsert]
      split
      · rename_i h
        subst k
        simp only [phaseEval]
        cases hm : monoEval a m <;> simp [mask, hm, zl, assoc]
      · simp only [phaseEval, ih]
        rw [← assoc, comm (mask (monoEval a k) d) (mask (monoEval a m) c), assoc]

def transportPhase {C : Type} [Add C] (f : Forest) (norm : Mono → Mono) : Phase C → Phase C
  | [] => []
  | (m,c) :: ps => phaseInsert (transportMono f norm m) c (transportPhase f norm ps)

theorem phase_transport {C : Type} [Zero C] [Add C]
    (zl : ∀ c : C, 0+c=c)
    (assoc : ∀ a b c : C, (a+b)+c=a+(b+c))
    (comm : ∀ a b : C, a+b=b+a)
    (f : Forest) (norm : Mono → Mono) (hn : NormSpec norm)
    (a : Assignment) (ps : Phase C) :
    phaseEval a (transportPhase f norm ps) = phaseEval (extend f a) ps := by
  induction ps with
  | nil => rfl
  | cons t ps ih =>
      obtain ⟨m,c⟩ := t
      simp only [transportPhase, phase_insert zl assoc comm,
        mono_transport f norm hn, ih, phaseEval]

/-- Any phase-to-amplitude function respects equal exact phase values.
    In particular the theorem does not assume eighth-root-only phases. -/
theorem transported_term {C A : Type} [Zero C] [Add C] [Zero A]
    (zl : ∀ c : C, 0+c=c)
    (assoc : ∀ a b c : C, (a+b)+c=a+(b+c))
    (comm : ∀ a b : C, a+b=b+a)
    (f : Forest) (norm : Mono → Mono) (hn : NormSpec norm)
    (a : Assignment) (qs : List ANF) (ps : Phase C) (amplitude : C → A) :
    mask (rowsOK a (transportRows f norm qs))
      (amplitude (phaseEval a (transportPhase f norm ps))) =
    mask (rowsOK (extend f a) qs)
      (amplitude (phaseEval (extend f a) ps)) := by
  rw [rows_transport f norm hn, phase_transport zl assoc comm f norm hn]

#print axioms mono_map
#print axioms mono_support
#print axioms mono_transport
#print axioms xor_cancel
#print axioms xor_exchange
#print axioms anf_toggle
#print axioms anf_transport
#print axioms rows_drop_empty
#print axioms rows_map
#print axioms rows_transport
#print axioms phase_insert
#print axioms phase_transport
#print axioms transported_term
end QuPRS.AliasTransport
