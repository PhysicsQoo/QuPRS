/-
Semantic certificate for an ordered alias forest. Live identifiers can
be sparse; no bound on size or depth. Parent pointers are certified,
not computed by this file. Rust alias_map and all-assignment enumeration
refinement remain separate obligations.
-/
import ConditionalTrace

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AliasForest

abbrev Assignment := Nat → Bool

structure Forest where
  live : Nat → Prop
  parent : Nat → Option Nat
  n : Nat
  ordered : ∀ v p, parent v = some p → p < v
  closed : ∀ v p, live v → parent v = some p → live p
  input_live : ∀ v, v < n → live v
  input_root : ∀ v, v < n → parent v = none

def root (f : Forest) (v : Nat) : Nat :=
  match _h : f.parent v with
  | none => v
  | some p => root f p
termination_by v
decreasing_by exact f.ordered v p _h

theorem root_none (f : Forest) (v : Nat) (h : f.parent v = none) :
    root f v = v := by
  rw [root] <;> (first | rfl | (split <;> simp_all) | simp_all)

theorem root_edge (f : Forest) (v p : Nat) (h : f.parent v = some p) :
    root f v = root f p := by
  rw [root] <;> (first | rfl | (split <;> simp_all) | simp_all)

theorem root_terminal (f : Forest) (v : Nat) :
    f.parent (root f v) = none := by
  cases h : f.parent v with
  | none =>
      rw [root_none f v h]
      exact h
  | some p =>
      rw [root_edge f v p h]
      exact root_terminal f p
termination_by v
decreasing_by exact f.ordered v p h

theorem root_live (f : Forest) (v : Nat) (hv : f.live v) :
    f.live (root f v) := by
  cases h : f.parent v with
  | none =>
      rw [root_none f v h]
      exact hv
  | some p =>
      rw [root_edge f v p h]
      exact root_live f p (f.closed v p hv h)
termination_by v
decreasing_by exact f.ordered v p h

theorem root_le (f : Forest) (v : Nat) : root f v ≤ v := by
  cases h : f.parent v with
  | none =>
      rw [root_none f v h]
      exact Nat.le_refl v
  | some p =>
      rw [root_edge f v p h]
      exact Nat.le_trans (root_le f p) (Nat.le_of_lt (f.ordered v p h))
termination_by v
decreasing_by exact f.ordered v p h

def IsRoot (f : Forest) (v : Nat) : Prop :=
  f.live v ∧ f.parent v = none

theorem root_is_root (f : Forest) (v : Nat) (hv : f.live v) :
    IsRoot f (root f v) :=
  ⟨root_live f v hv, root_terminal f v⟩

theorem input_retained (f : Forest) (v : Nat) (h : v < f.n) :
    IsRoot f v ∧ root f v = v :=
  ⟨⟨f.input_live v h, f.input_root v h⟩, root_none f v (f.input_root v h)⟩

def Satisfies (f : Forest) (a : Assignment) : Prop :=
  ∀ v p, f.live v → f.parent v = some p → a v = a p

def AgreeLive (f : Forest) (a b : Assignment) : Prop :=
  ∀ v, f.live v → a v = b v

def AgreeRoots (f : Forest) (a b : Assignment) : Prop :=
  ∀ v, IsRoot f v → a v = b v

/-- A seed is observed only on roots; arbitrary values elsewhere
    carry no additional information. -/
def extend (f : Forest) (seed : Assignment) : Assignment :=
  fun v => seed (root f v)

theorem extend_satisfies (f : Forest) (seed : Assignment) :
    Satisfies f (extend f seed) := by
  intro v p _ h
  unfold extend
  rw [root_edge f v p h]

theorem extend_roots (f : Forest) (seed : Assignment) :
    AgreeRoots f (extend f seed) seed := by
  intro v hv
  unfold extend
  rw [root_none f v hv.2]

theorem consistent_root (f : Forest) (a : Assignment)
    (ha : Satisfies f a) (v : Nat) (hv : f.live v) :
    a v = a (root f v) := by
  cases h : f.parent v with
  | none => rw [root_none f v h]
  | some p =>
      rw [root_edge f v p h]
      exact (ha v p hv h).trans
        (consistent_root f a ha p (f.closed v p hv h))
termination_by v
decreasing_by exact f.ordered v p h

theorem extend_restrict (f : Forest) (a : Assignment)
    (ha : Satisfies f a) : AgreeLive f (extend f a) a := by
  intro v hv
  exact (consistent_root f a ha v hv).symm

theorem extend_congr (f : Forest) (a b : Assignment)
    (h : AgreeRoots f a b) : AgreeLive f (extend f a) (extend f b) := by
  intro v hv
  exact h (root f v) (root_is_root f v hv)

/-- Restriction and extension are inverse modulo agreement on the
    live domain and root domain, respectively. No equality of values
    outside these domains is required. -/
theorem unique_extension (f : Forest) (seed : Assignment) :
    ∃ a : Assignment, Satisfies f a ∧ AgreeRoots f a seed ∧
      ∀ b : Assignment, Satisfies f b → AgreeRoots f b seed → AgreeLive f b a := by
  refine ⟨extend f seed, extend_satisfies f seed, extend_roots f seed, ?_⟩
  intro b hb hr v hv
  exact (consistent_root f b hb v hv).trans
    (hr (root f v) (root_is_root f v hv))

theorem extension_injective (f : Forest) (a b : Assignment)
    (h : AgreeLive f (extend f a) (extend f b)) : AgreeRoots f a b := by
  intro v hv
  exact (extend_roots f a v hv).symm.trans
    ((h v hv.1).trans (extend_roots f b v hv))

theorem extension_bijection (f : Forest) (a b : Assignment) :
    AgreeLive f (extend f a) (extend f b) ↔ AgreeRoots f a b :=
  ⟨extension_injective f a b, extend_congr f a b⟩

/-- Semantic transport evaluates ALL residual constraints and phase
    under the root extension, not just the selected forest edges. -/
def transported {A : Type} [Zero A] (f : Forest)
    (g : Assignment → Bool) (amp : Assignment → A) (seed : Assignment) : A :=
  QuPRS.ConditionalTrace.mask (g (extend f seed)) (amp (extend f seed))

theorem transport_restrict {A : Type} [Zero A] (f : Forest)
    (g : Assignment → Bool) (amp : Assignment → A)
    (hg : ∀ a b, AgreeLive f a b → g a = g b)
    (hp : ∀ a b, AgreeLive f a b → amp a = amp b)
    (a : Assignment) (ha : Satisfies f a) :
    transported f g amp a = QuPRS.ConditionalTrace.mask (g a) (amp a) := by
  unfold transported
  rw [hg _ _ (extend_restrict f a ha), hp _ _ (extend_restrict f a ha)]

/-- The mapped list has exactly the same multiplicities as the seed
    list. Exhaustiveness and uniqueness of the seed enumeration must
    be established by the caller, rather than asserted by this lemma. -/
theorem mapped_sum {X Y A : Type} [Zero A] [Add A]
    (xs : List X) (e : X → Y) (term : Y → A) :
    QuPRS.ConditionalTrace.sumPaths (xs.map e) term =
    QuPRS.ConditionalTrace.sumPaths xs (fun x => term (e x)) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.map_cons, QuPRS.ConditionalTrace.sumPaths, ih]

theorem forest_sum {A : Type} [Zero A] [Add A] (f : Forest)
    (seeds : List Assignment) (g : Assignment → Bool) (amp : Assignment → A) :
    QuPRS.ConditionalTrace.sumPaths (seeds.map (extend f))
      (fun a => QuPRS.ConditionalTrace.mask (g a) (amp a)) =
    QuPRS.ConditionalTrace.sumPaths seeds (transported f g amp) :=
  mapped_sum seeds (extend f) (fun a => QuPRS.ConditionalTrace.mask (g a) (amp a))

#print axioms root_none
#print axioms root_edge
#print axioms root_terminal
#print axioms root_live
#print axioms root_le
#print axioms root_is_root
#print axioms input_retained
#print axioms extend_satisfies
#print axioms extend_roots
#print axioms consistent_root
#print axioms extend_restrict
#print axioms extend_congr
#print axioms unique_extension
#print axioms extension_injective
#print axioms extension_bijection
#print axioms transport_restrict
#print axioms mapped_sum
#print axioms forest_sum
end QuPRS.AliasForest
