/-
Canonical scope and complete Boolean row enumeration.
The domain is ordered and duplicate-free (native positions are increasing).
The abstract keys are little endian: the first coordinate changes fastest.
No packed-machine-word refinement is claimed.
-/
import AffineFactorScope
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineCanonicalScope
open QuPRS.AffineFactorScope

def canonical {X : Type} [DecidableEq X] (raw : List X) : List X → List X
  | [] => []
  | x :: xs =>
      if x ∈ raw then x :: canonical raw xs else canonical raw xs

theorem canonical_mem {X : Type} [DecidableEq X] (raw domain : List X) (x : X) :
    x ∈ canonical raw domain ↔ x ∈ domain ∧ x ∈ raw := by
  induction domain with
  | nil => simp [canonical]
  | cons y ys ih =>
      by_cases hy : y ∈ raw
      · rw [canonical, ite_eq_left hy, List.mem_cons, ih, List.mem_cons]
        constructor
        · intro h
          rcases h with he | ht
          · subst x
            exact ⟨Or.inl rfl, hy⟩
          · exact ⟨Or.inr ht.1, ht.2⟩
        · intro h
          rcases h.1 with he | ht
          · exact Or.inl he
          · exact Or.inr ⟨ht, h.2⟩
      · rw [canonical, ite_eq_right hy, ih, List.mem_cons]
        constructor
        · intro h
          exact ⟨Or.inr h.1, h.2⟩
        · intro h
          rcases h.1 with he | ht
          · subst x
            exact False.elim (hy h.2)
          · exact ⟨ht, h.2⟩

theorem canonical_nodup {X : Type} [DecidableEq X] (raw domain : List X)
    (h : domain.Nodup) : (canonical raw domain).Nodup := by
  induction domain with
  | nil => simp [canonical]
  | cons y ys ih =>
      have hn := List.nodup_cons.mp h
      by_cases hy : y ∈ raw
      · rw [canonical, ite_eq_left hy]
        exact List.nodup_cons.mpr
          ⟨fun hm => hn.1 ((canonical_mem raw ys y).mp hm).1, ih hn.2⟩
      · rw [canonical, ite_eq_right hy]
        exact ih hn.2

theorem canonical_covers {X : Type} [DecidableEq X] (raw domain : List X)
    (h : ∀ x, x ∈ raw → x ∈ domain) (x : X) :
    x ∈ canonical raw domain ↔ x ∈ raw := by
  rw [canonical_mem]
  exact ⟨fun hx => hx.2, fun hx => ⟨h x hx,hx⟩⟩

theorem canonical_support {X A : Type} [DecidableEq X]
    (domain : List X) (f : ScopedFactor X A)
    (h : ∀ x, x ∈ f.scope → x ∈ domain) :
    dependsOn (canonical f.scope domain) f.eval := by
  intro a b hab
  exact f.support a b
    (fun x hx => hab x ((canonical_covers f.scope domain h x).mpr hx))

def expand : List (List Bool) → List (List Bool)
  | [] => []
  | k :: ks => (false :: k) :: (true :: k) :: expand ks

def rows : Nat → List (List Bool)
  | 0 => [[]]
  | n+1 => expand (rows n)

theorem mem_expand_cons (b : Bool) (key : List Bool) (ks : List (List Bool)) :
    b :: key ∈ expand ks ↔ key ∈ ks := by
  induction ks with
  | nil => simp [expand]
  | cons k ks ih =>
      cases b <;> simp [expand, ih]

theorem nil_not_mem_expand (ks : List (List Bool)) : [] ∉ expand ks := by
  induction ks with
  | nil => simp [expand]
  | cons k ks ih => simp [expand, ih]

theorem expand_length (ks : List (List Bool)) :
    (expand ks).length = 2 * ks.length := by
  induction ks with
  | nil => rfl
  | cons k ks ih =>
      change (expand ks).length + 2 = 2 * (ks.length + 1)
      rw [ih]
      omega

theorem expand_nodup (ks : List (List Bool)) (h : ks.Nodup) :
    (expand ks).Nodup := by
  induction ks with
  | nil => simp [expand]
  | cons k ks ih =>
      have hn := List.nodup_cons.mp h
      change ((false :: k) :: (true :: k) :: expand ks).Nodup
      apply List.nodup_cons.mpr
      constructor
      · simp [mem_expand_cons, hn.1]
      · apply List.nodup_cons.mpr
        exact ⟨fun hm => hn.1 ((mem_expand_cons true k ks).mp hm), ih hn.2⟩

theorem rows_length (n : Nat) : (rows n).length = 2^n := by
  induction n with
  | zero => rfl
  | succ n ih =>
      rw [rows, expand_length, ih, Nat.pow_succ, Nat.mul_comm]

theorem rows_nodup (n : Nat) : (rows n).Nodup := by
  induction n with
  | zero => simp [rows]
  | succ n ih => exact expand_nodup (rows n) ih

theorem mem_rows_iff (n : Nat) (key : List Bool) :
    key ∈ rows n ↔ key.length = n := by
  induction n generalizing key with
  | zero =>
      cases key <;> simp [rows]
  | succ n ih =>
      cases key with
      | nil =>
          exact iff_of_false (nil_not_mem_expand (rows n)) (Nat.zero_ne_succ n)
      | cons b key =>
          rw [rows, mem_expand_cons, ih]
          simp

theorem projection_mem_rows {X : Type} (scope : List X) (a : X → Bool) :
    extract a scope ∈ rows scope.length :=
  (mem_rows_iff scope.length _).mpr (by simp [extract])

theorem rows_deposit_injective {X : Type} [DecidableEq X]
    (scope : List X) (hn : scope.Nodup) (k l : List Bool)
    (hk : k ∈ rows scope.length) (hl : l ∈ rows scope.length)
    (he : deposit scope k = deposit scope l) : k = l := by
  have h := congrArg (fun a => extract a scope) he
  rw [extract_deposit scope k hn ((mem_rows_iff _ _).mp hk),
      extract_deposit scope l hn ((mem_rows_iff _ _).mp hl)] at h
  exact h

#print axioms canonical_mem
#print axioms canonical_nodup
#print axioms canonical_covers
#print axioms canonical_support
#print axioms mem_expand_cons
#print axioms nil_not_mem_expand
#print axioms expand_length
#print axioms expand_nodup
#print axioms rows_length
#print axioms rows_nodup
#print axioms mem_rows_iff
#print axioms projection_mem_rows
#print axioms rows_deposit_injective
end QuPRS.AffineCanonicalScope
