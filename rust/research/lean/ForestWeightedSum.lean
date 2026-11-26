/-
Batch alias weighted-sum preservation on a finite live domain.
Canonicalize outside-live bits to false before comparing enumerations.
The original list is explicitly filtered by the forest edge predicate;
the reduced list is enumerated roots extended to live assignments.
No classical choice, Mathlib, or bound on the number of live IDs.
This is a semantic theorem, not Rust implementation refinement.
-/
import ForestEnumeration
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.ForestWeightedSum
open QuPRS.AliasForest QuPRS.ForestEnumeration QuPRS.ConditionalTrace

def LiveList (f : Forest) (vs : List Nat) : Prop :=
  vs.Nodup ∧ ∀ v, v ∈ vs ↔ f.live v

def canon (vs : List Nat) (a : Assignment) : Assignment :=
  fun i => match memDecision i vs with
    | isTrue _ => a i
    | isFalse _ => false

theorem canon_inside (vs : List Nat) (a : Assignment) (v : Nat)
    (hv : v ∈ vs) : canon vs a v = a v := by
  unfold canon
  split
  · rfl
  · contradiction

theorem canon_outside (vs : List Nat) (a : Assignment) (v : Nat)
    (hv : v ∉ vs) : canon vs a v = false := by
  unfold canon
  split
  · contradiction
  · rfl

theorem canon_agree (vs : List Nat) (a : Assignment) :
    AgreeOn vs (canon vs a) a :=
  fun v hv => canon_inside vs a v hv

theorem canon_eq_of_agree (vs : List Nat) (a b : Assignment)
    (h : AgreeOn vs a b) : canon vs a = canon vs b :=
  @funext Nat (fun _ => Bool) _ _ (fun v =>
    match memDecision v vs with
    | isTrue hv =>
        (canon_inside vs a v hv).trans ((h v hv).trans (canon_inside vs b v hv).symm)
    | isFalse hv =>
        (canon_outside vs a v hv).trans (canon_outside vs b v hv).symm)

theorem enum_canonical (vs : List Nat) (a : Assignment)
    (ha : a ∈ enumerate vs) : canon vs a = a :=
  @funext Nat (fun _ => Bool) _ _ (fun v =>
    match memDecision v vs with
    | isTrue hv => canon_inside vs a v hv
    | isFalse hv =>
        (canon_outside vs a v hv).trans (enumeration_outside vs a ha v hv).symm)

theorem canon_mem_enum (vs : List Nat) (a : Assignment) :
    canon vs a ∈ enumerate vs := by
  obtain ⟨b, hb, h⟩ := enumeration_cover vs a
  have he := canon_eq_of_agree vs b a h
  rw [enum_canonical vs b hb] at he
  rw [← he]
  exact hb

theorem canon_agree_live (f : Forest) (vs : List Nat)
    (hv : LiveList f vs) (a : Assignment) :
    AgreeLive f (canon vs a) a :=
  fun v h => canon_inside vs a v ((hv.2 v).mpr h)

def edgeOK (f : Forest) (a : Assignment) (v : Nat) : Bool :=
  match f.parent v with
  | none => true
  | some p => a v == a p

def forestOK (f : Forest) (vs : List Nat) (a : Assignment) : Bool :=
  vs.all (edgeOK f a)

theorem edge_ok_iff (f : Forest) (a : Assignment) (v : Nat) :
    edgeOK f a v = true ↔ ∀ p, f.parent v = some p → a v = a p := by
  cases h : f.parent v with
  | none => simp [edgeOK, h]
  | some p => simp [edgeOK, h]

theorem forest_ok_iff (f : Forest) (vs : List Nat)
    (hv : LiveList f vs) (a : Assignment) :
    forestOK f vs a = true ↔ Satisfies f a := by
  constructor
  · intro h v p hl he
    have hh := (List.all_eq_true.mp h) v ((hv.2 v).mpr hl)
    exact (edge_ok_iff f a v).mp hh p he
  · intro h
    apply List.all_eq_true.mpr
    intro v hm
    exact (edge_ok_iff f a v).mpr (fun p he => h v p ((hv.2 v).mp hm) he)

theorem satisfies_transport (f : Forest) (a b : Assignment)
    (h : AgreeLive f a b) (hb : Satisfies f b) : Satisfies f a := by
  intro v p hv he
  exact (h v hv).trans ((hb v p hv he).trans (h p (f.closed v p hv he)).symm)

def original (f : Forest) (vs : List Nat) : List Assignment :=
  (enumerate vs).filter (forestOK f vs)

def reduced (f : Forest) (vs rs : List Nat) : List Assignment :=
  (enumerate rs).map (fun a => canon vs (extend f a))

theorem original_mem (f : Forest) (vs : List Nat)
    (hv : LiveList f vs) (a : Assignment) :
    a ∈ original f vs ↔ a ∈ enumerate vs ∧ Satisfies f a := by
  rw [original, List.mem_filter]
  exact and_congr_right (fun _ => forest_ok_iff f vs hv a)

theorem reduced_mem_original (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (a : Assignment) (ha : a ∈ reduced f vs rs) :
    a ∈ original f vs := by
  obtain ⟨b, _, rfl⟩ := List.mem_map.mp ha
  exact (original_mem f vs hv _).mpr
    ⟨canon_mem_enum vs _, satisfies_transport f _ _
      (canon_agree_live f vs hv _) (extend_satisfies f b)⟩

theorem original_mem_reduced (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (hr : RootList f rs) (a : Assignment)
    (ha : a ∈ original f vs) : a ∈ reduced f vs rs := by
  obtain ⟨he, hs⟩ := (original_mem f vs hv a).mp ha
  obtain ⟨b, hb, hag⟩ := extended_cover f rs hr a hs
  have hc := canon_eq_of_agree vs (extend f b) a
    (fun v h => hag v ((hv.2 v).mp h))
  rw [enum_canonical vs a he] at hc
  exact List.mem_map.mpr ⟨b, hb, hc⟩

theorem reduced_nodup (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (hr : RootList f rs) :
    (reduced f vs rs).Nodup := by
  apply map_nodup_of_inj _ _ (enumeration_nodup rs hr.1)
  intro a ha b hb he
  apply extended_unique f rs hr a b ha hb
  intro v hl
  exact (canon_inside vs (extend f a) v ((hv.2 v).mpr hl)).symm.trans
    ((congrFun he v).trans (canon_inside vs (extend f b) v ((hv.2 v).mpr hl)))

theorem original_nodup (f : Forest) (vs : List Nat) (hv : LiveList f vs) :
    (original f vs).Nodup :=
  (enumeration_nodup vs hv.1).filter _

/-- Constructive replacement for Std's classical perm_ext_iff_of_nodup.
    Membership provides a split witness; move its head to the front.
    No DecidableEq on functions, no counting via classical equality. -/
theorem nodup_perm_constructive {X : Type} (xs ys : List X)
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

theorem original_reduced_perm (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (hr : RootList f rs) :
    (original f vs).Perm (reduced f vs rs) := by
  apply nodup_perm_constructive
  · exact original_nodup f vs hv
  · exact reduced_nodup f vs rs hv hr
  · intro a
    exact ⟨original_mem_reduced f vs rs hv hr a, reduced_mem_original f vs rs hv a⟩

theorem sum_perm {X A : Type} [Zero A] [Add A]
    (assoc : ∀ a b c : A, (a+b)+c = a+(b+c))
    (comm : ∀ a b : A, a+b = b+a)
    {xs ys : List X} (h : xs.Perm ys) (term : X → A) :
    sumPaths xs term = sumPaths ys term := by
  induction h with
  | nil => rfl
  | cons x _ ih => simp only [sumPaths, ih]
  | swap x y rest =>
      simp only [sumPaths]
      rw [← assoc, comm (term y) (term x), assoc]
  | trans _ _ ih1 ih2 => exact ih1.trans ih2

theorem weighted_sum_preservation {A : Type} [Zero A] [Add A]
    (assoc : ∀ a b c : A, (a+b)+c = a+(b+c))
    (comm : ∀ a b : A, a+b = b+a)
    (f : Forest) (vs rs : List Nat)
    (hv : LiveList f vs) (hr : RootList f rs)
    (g : Assignment → Bool) (amp : Assignment → A)
    (hg : ∀ a b, AgreeLive f a b → g a = g b)
    (hp : ∀ a b, AgreeLive f a b → amp a = amp b) :
    sumPaths (original f vs) (fun a => mask (g a) (amp a)) =
      sumPaths (enumerate rs) (transported f g amp) := by
  rw [sum_perm assoc comm (original_reduced_perm f vs rs hv hr)]
  unfold reduced
  rw [mapped_sum]
  apply sum_congr
  intro a
  unfold transported
  rw [hg _ _ (canon_agree_live f vs hv _), hp _ _ (canon_agree_live f vs hv _)]

#print axioms canon_inside
#print axioms canon_outside
#print axioms canon_agree
#print axioms canon_eq_of_agree
#print axioms enum_canonical
#print axioms canon_mem_enum
#print axioms canon_agree_live
#print axioms edge_ok_iff
#print axioms forest_ok_iff
#print axioms satisfies_transport
#print axioms original_mem
#print axioms reduced_mem_original
#print axioms original_mem_reduced
#print axioms reduced_nodup
#print axioms original_nodup
#print axioms nodup_perm_constructive
#print axioms original_reduced_perm
#print axioms sum_perm
#print axioms weighted_sum_preservation
end QuPRS.ForestWeightedSum
