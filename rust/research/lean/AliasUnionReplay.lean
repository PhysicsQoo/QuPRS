/-
Proof-carrying ordered union replay for a fixed original ANF row list.
Each union links current representatives of a genuine singleton equality.
This is a semantic certificate relation, not yet an executable Rust
checker or a proof that alias_map always produces its witnesses.
-/
import TraceAliasSoundness
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AliasUnionReplay
open QuPRS.AliasForest QuPRS.ForestEnumeration QuPRS.ForestWeightedSum
open QuPRS.ConditionalTrace QuPRS.AliasTransport QuPRS.TraceAliasSoundness

theorem singleton_row_eq (a : Assignment) (x y : Nat)
    (h : !(anfEval a [[x],[y]]) = true) : a x = a y := by
  cases hx : a x <;> cases hy : a y <;> simp_all [anfEval, monoEval]

theorem source_row_eq (qs : List ANF) (a : Assignment) (x y : Nat)
    (hr : [[x],[y]] ∈ qs ∨ [[y],[x]] ∈ qs)
    (h : rowsOK a qs = true) : a x = a y := by
  have hall : ∀ q ∈ qs, !(anfEval a q) = true :=
    List.all_eq_true.mp h
  rcases hr with hxy | hyx
  · exact singleton_row_eq a x y (hall _ hxy)
  · exact (singleton_row_eq a y x (hall _ hyx)).symm

/-- Structural link of two existing roots. The caller supplies live and
    ordering checks. Input representatives cannot become children. -/
def linkForest (f : Forest) (child par : Nat)
    (_hc : f.live child) (hp : f.live par)
    (ho : par < child) (hi : f.n ≤ child) : Forest where
  live := f.live
  n := f.n
  parent := fun v => if v = child then some par else f.parent v
  ordered := by
    intro v p h
    cases Nat.decEq v child with
    | isTrue he =>
        rw [ite_eq_left he] at h
        have hpe := Option.some.inj h
        rw [he, ← hpe]
        exact ho
    | isFalse he =>
        rw [ite_eq_right he] at h
        exact f.ordered v p h
  closed := by
    intro v p hv h
    cases Nat.decEq v child with
    | isTrue he =>
        rw [ite_eq_left he] at h
        rw [← Option.some.inj h]
        exact hp
    | isFalse he =>
        rw [ite_eq_right he] at h
        exact f.closed v p hv h
  input_live := f.input_live
  input_root := by
    intro v hv
    have hn : v ≠ child := by
      intro he
      rw [he] at hv
      exact (Nat.not_lt_of_ge hi) hv
    rw [ite_eq_right hn]
    exact f.input_root v hv

/-- The child argument's live membership is retained explicitly in the
    certificate; the definition of linkForest needs only parent closure. -/
structure UnionStep (qs : List ANF) (before after : Forest) where
  x : Nat
  y : Nat
  child : Nat
  par : Nat
  row : [[x],[y]] ∈ qs ∨ [[y],[x]] ∈ qs
  x_live : before.live x
  y_live : before.live y
  child_root : child = root before x
  par_root : par = root before y
  ordered : par < child
  internal : before.n ≤ child
  live_same : ∀ v, after.live v ↔ before.live v
  n_same : after.n = before.n
  parent_update : ∀ v, after.parent v =
    if v = child then some par else before.parent v

/-- Construct a certificate for an actual link of current roots. -/
def certifyLink (qs : List ANF) (f : Forest) (x y : Nat)
    (hx : f.live x) (hy : f.live y)
    (hr : [[x],[y]] ∈ qs ∨ [[y],[x]] ∈ qs)
    (ho : root f y < root f x) (hi : f.n ≤ root f x) :
    UnionStep qs f
      (linkForest f (root f x) (root f y)
        (root_live f x hx) (root_live f y hy) ho hi) where
  x := x
  y := y
  child := root f x
  par := root f y
  row := hr
  x_live := hx
  y_live := hy
  child_root := rfl
  par_root := rfl
  ordered := ho
  internal := hi
  live_same := fun _ => Iff.rfl
  n_same := rfl
  parent_update := fun _ => rfl

theorem step_child_root (qs : List ANF) (f g : Forest)
    (s : UnionStep qs f g) : IsRoot f s.child := by
  rw [s.child_root]
  exact root_is_root f s.x s.x_live

theorem step_parent_root (qs : List ANF) (f g : Forest)
    (s : UnionStep qs f g) : IsRoot f s.par := by
  rw [s.par_root]
  exact root_is_root f s.y s.y_live

theorem step_root_eq (qs : List ANF) (f g : Forest)
    (s : UnionStep qs f g) (a : Assignment)
    (ha : rowsOK a qs = true) (hf : Satisfies f a) :
    a s.child = a s.par := by
  rw [s.child_root, s.par_root]
  exact (consistent_root f a hf s.x s.x_live).symm.trans
    ((source_row_eq qs a s.x s.y s.row ha).trans
      (consistent_root f a hf s.y s.y_live))

theorem step_preserves_entailment (qs : List ANF) (f g : Forest)
    (s : UnionStep qs f g) (h : EntailsForest f qs) :
    EntailsForest g qs := by
  intro a ha v p hv he
  have hf := h a ha
  have hr := step_root_eq qs f g s a ha hf
  rw [s.parent_update] at he
  cases Nat.decEq v s.child with
  | isTrue hvchild =>
      rw [ite_eq_left hvchild] at he
      have hpe := Option.some.inj he
      rw [hvchild, ← hpe]
      exact hr
  | isFalse hvchild =>
      rw [ite_eq_right hvchild] at he
      exact hf v p ((s.live_same v).mp hv) he

/-- A replay begins with an empty parent map. Each accepted step carries
    proof of one structural link and its original ANF row membership. -/
inductive Replay (qs : List ANF) : Forest → Prop where
  | empty (f : Forest) (h : ∀ v, f.parent v = none) : Replay qs f
  | step {f g : Forest} (prior : Replay qs f)
      (s : UnionStep qs f g) : Replay qs g

theorem empty_entails (qs : List ANF) (f : Forest)
    (h : ∀ v, f.parent v = none) : EntailsForest f qs := by
  intro _ _ v _ _ he
  rw [h v] at he
  contradiction

theorem replay_entails (qs : List ANF) (f : Forest)
    (h : Replay qs f) : EntailsForest f qs := by
  induction h with
  | empty f he => exact empty_entails qs f he
  | step _ s ih => exact step_preserves_entailment qs _ _ s ih

/-- End-to-end abstract trace identity from a replay witness, replacing
    the previous EntailsForest hypothesis with constructive union steps. -/
theorem replay_trace_soundness {C A : Type} [Zero C] [Add C] [Zero A] [Add A]
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
    (hw : Replay qs f) :
    sumPaths (enumerate vs) (traceTerm qs ps amplitude) =
    sumPaths (enumerate rs)
      (traceTerm (transportRows f norm qs) (transportPhase f norm ps) amplitude) :=
  trace_alias_soundness czl cassoc ccomm azl aassoc acomm
    f vs rs hv hr norm hn qs ps amplitude hq hp (replay_entails qs f hw)

#print axioms singleton_row_eq
#print axioms source_row_eq
#print axioms linkForest
#print axioms certifyLink
#print axioms step_child_root
#print axioms step_parent_root
#print axioms step_root_eq
#print axioms step_preserves_entailment
#print axioms empty_entails
#print axioms replay_entails
#print axioms replay_trace_soundness
end QuPRS.AliasUnionReplay
