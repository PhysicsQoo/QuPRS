/-
Finite Boolean enumeration for an admitted alias forest.
List recursion, no fixed width, no classical choice.
Concrete enumeration coverage and uniqueness on the root domain.
Original live-domain enumeration permutation remains separate.
-/
import AliasForest
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.ForestEnumeration
open QuPRS.AliasForest

def setBit (a : Assignment) (v : Nat) (b : Bool) : Assignment :=
  fun i => if i = v then b else a i

def enumerate : List Nat → List Assignment
  | [] => [fun _ => false]
  | v :: vs =>
      (enumerate vs).map (fun a => setBit a v false) ++
      (enumerate vs).map (fun a => setBit a v true)

def AgreeOn (vs : List Nat) (a b : Assignment) : Prop :=
  ∀ v, v ∈ vs → a v = b v

theorem set_self (a : Assignment) (v : Nat) (b : Bool) :
    setBit a v b v = b := by simp [setBit]

theorem set_other (a : Assignment) (v i : Nat) (b : Bool) (h : i ≠ v) :
    setBit a v b i = a i := by simp [setBit, h]

theorem enumeration_length (vs : List Nat) :
    (enumerate vs).length = 2 ^ vs.length := by
  induction vs with
  | nil => rfl
  | cons v vs ih =>
      simp only [enumerate, List.length_append, List.length_map, List.length_cons, ih, Nat.pow_succ]
      omega

theorem enumeration_cover (vs : List Nat) (a : Assignment) :
    ∃ b ∈ enumerate vs, AgreeOn vs b a := by
  induction vs with
  | nil =>
      refine ⟨fun _ => false, by simp [enumerate], ?_⟩
      intro v hv
      simp at hv
  | cons v vs ih =>
      obtain ⟨b, hb, ha⟩ := ih
      refine ⟨setBit b v (a v), ?_, ?_⟩
      · cases (a v)
        · simp only [enumerate, List.mem_append, List.mem_map]
          exact Or.inl ⟨b, hb, rfl⟩
        · simp only [enumerate, List.mem_append, List.mem_map]
          exact Or.inr ⟨b, hb, rfl⟩
      · intro i hi
        cases (inferInstance : Decidable (i = v)) with
        | isTrue h =>
          subst i
          exact set_self b v (a v)
        | isFalse h =>
          rw [set_other b v i (a v) h]
          exact ha i ((List.mem_cons.mp hi).resolve_left h)

theorem enumeration_outside (vs : List Nat) (a : Assignment)
    (ha : a ∈ enumerate vs) (i : Nat) (hi : i ∉ vs) :
    a i = false := by
  induction vs generalizing a with
  | nil =>
      simp [enumerate] at ha
      rw [ha]
  | cons v vs ih =>
      have hv : i ≠ v := fun h => hi (List.mem_cons.mpr (Or.inl h))
      have ht : i ∉ vs := fun h => hi (List.mem_cons.mpr (Or.inr h))
      simp only [enumerate, List.mem_append, List.mem_map] at ha
      rcases ha with ⟨b, hb, rfl⟩ | ⟨b, hb, rfl⟩
      · rw [set_other b v i false hv]
        exact ih b hb ht
      · rw [set_other b v i true hv]
        exact ih b hb ht

theorem enumeration_distinguishes (vs : List Nat) (a b : Assignment)
    (ha : a ∈ enumerate vs) (hb : b ∈ enumerate vs)
    (h : AgreeOn vs a b) : a = b := by
  apply funext
  intro i
  cases (inferInstance : Decidable (i ∈ vs)) with
  | isTrue hi => exact h i hi
  | isFalse hi => rw [enumeration_outside vs a ha i hi, enumeration_outside vs b hb i hi]

theorem map_nodup_of_inj {A B : Type} (xs : List A) (f : A → B)
    (hn : xs.Nodup)
    (hf : ∀ a ∈ xs, ∀ b ∈ xs, f a = f b → a = b) :
    (xs.map f).Nodup := by
  induction xs with
  | nil => simp
  | cons a xs ih =>
      rw [List.nodup_cons] at hn
      rw [List.map_cons, List.nodup_cons]
      refine ⟨?_, ih hn.2 ?_⟩
      · intro hm
        obtain ⟨b, hb, he⟩ := List.mem_map.mp hm
        have hba := hf b (List.mem_cons.mpr (Or.inr hb)) a
          (List.mem_cons.mpr (Or.inl rfl)) he
        exact hn.1 (hba ▸ hb)
      · intro b hb c hc he
        exact hf b (List.mem_cons.mpr (Or.inr hb)) c
          (List.mem_cons.mpr (Or.inr hc)) he

theorem set_injective_on_enum (vs : List Nat) (v : Nat) (b : Bool)
    (hv : v ∉ vs) (a c : Assignment)
    (ha : a ∈ enumerate vs) (hc : c ∈ enumerate vs)
    (h : setBit a v b = setBit c v b) : a = c := by
  apply enumeration_distinguishes vs a c ha hc
  intro i hi
  have hn : i ≠ v := fun he => hv (he ▸ hi)
  have hh := congrFun h i
  rw [set_other a v i b hn, set_other c v i b hn] at hh
  exact hh

theorem enumeration_nodup (vs : List Nat) (h : vs.Nodup) :
    (enumerate vs).Nodup := by
  induction vs with
  | nil => simp [enumerate]
  | cons v vs ih =>
      rw [List.nodup_cons] at h
      have hn := ih h.2
      have hf := map_nodup_of_inj (enumerate vs) (fun a => setBit a v false) hn
        (fun a ha b hb he => set_injective_on_enum vs v false h.1 a b ha hb he)
      have ht := map_nodup_of_inj (enumerate vs) (fun a => setBit a v true) hn
        (fun a ha b hb he => set_injective_on_enum vs v true h.1 a b ha hb he)
      simp only [enumerate]
      rw [List.nodup_append]
      refine ⟨hf, ht, ?_⟩
      intro a ha b hb he
      obtain ⟨x, _, hx⟩ := List.mem_map.mp ha
      obtain ⟨y, _, hy⟩ := List.mem_map.mp hb
      have hbit := congrFun (hx.trans (he.trans hy.symm)) v
      simp [setBit] at hbit

def RootList (f : Forest) (vs : List Nat) : Prop :=
  vs.Nodup ∧ ∀ v, v ∈ vs ↔ IsRoot f v

theorem root_seed_cover (f : Forest) (vs : List Nat) (h : RootList f vs)
    (a : Assignment) : ∃ b ∈ enumerate vs, AgreeRoots f b a := by
  obtain ⟨b, hb, he⟩ := enumeration_cover vs a
  exact ⟨b, hb, fun v hv => he v ((h.2 v).mpr hv)⟩

theorem root_seed_unique (f : Forest) (vs : List Nat) (h : RootList f vs)
    (a b : Assignment) (ha : a ∈ enumerate vs) (hb : b ∈ enumerate vs)
    (he : AgreeRoots f a b) : a = b :=
  enumeration_distinguishes vs a b ha hb (fun v hv => he v ((h.2 v).mp hv))

theorem extended_cover (f : Forest) (vs : List Nat) (h : RootList f vs)
    (a : Assignment) (ha : Satisfies f a) :
    ∃ b ∈ enumerate vs, AgreeLive f (extend f b) a := by
  obtain ⟨b, hb, hr⟩ := root_seed_cover f vs h a
  refine ⟨b, hb, ?_⟩
  intro v hv
  exact (extend_congr f b a hr v hv).trans (extend_restrict f a ha v hv)

theorem extended_unique (f : Forest) (vs : List Nat) (h : RootList f vs)
    (a b : Assignment) (ha : a ∈ enumerate vs) (hb : b ∈ enumerate vs)
    (he : AgreeLive f (extend f a) (extend f b)) : a = b :=
  root_seed_unique f vs h a b ha hb (extension_injective f a b he)

theorem extended_nodup (f : Forest) (vs : List Nat) (h : RootList f vs) :
    ((enumerate vs).map (extend f)).Nodup := by
  apply map_nodup_of_inj _ _ (enumeration_nodup vs h.1)
  intro a ha b hb he
  apply extended_unique f vs h a b ha hb
  intro v _
  exact congrFun he v

theorem extended_satisfies (f : Forest) (vs : List Nat)
    (a : Assignment) (ha : a ∈ (enumerate vs).map (extend f)) :
    Satisfies f a := by
  obtain ⟨b, _, rfl⟩ := List.mem_map.mp ha
  exact extend_satisfies f b

theorem enumerated_sum {A : Type} [Zero A] [Add A] (f : Forest)
    (vs : List Nat) (g : Assignment → Bool) (amp : Assignment → A) :
    QuPRS.ConditionalTrace.sumPaths ((enumerate vs).map (extend f))
      (fun a => QuPRS.ConditionalTrace.mask (g a) (amp a)) =
    QuPRS.ConditionalTrace.sumPaths (enumerate vs) (transported f g amp) :=
  forest_sum f (enumerate vs) g amp

#print axioms set_self
#print axioms set_other
#print axioms enumeration_length
#print axioms enumeration_cover
#print axioms enumeration_outside
#print axioms enumeration_distinguishes
#print axioms map_nodup_of_inj
#print axioms set_injective_on_enum
#print axioms enumeration_nodup
#print axioms root_seed_cover
#print axioms root_seed_unique
#print axioms extended_cover
#print axioms extended_unique
#print axioms extended_nodup
#print axioms extended_satisfies
#print axioms enumerated_sum
end QuPRS.ForestEnumeration
