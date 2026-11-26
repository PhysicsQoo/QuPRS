/-
Complete checked table materialization on canonical Boolean scopes.
A successful state transition uses the materialized table, not an exact
oracle substituted for its contents. Success-only semantic refinement,
not packed index, source, deadline, or machine arithmetic refinement.
-/
import AffineCanonicalScope
import AffineCheckedFactor
set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineCheckedOrder
open QuPRS.AffineFactorScope
open QuPRS.AffineFactorElimination
open QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineCheckedFactor
open QuPRS.AffineCanonicalScope

def materialize {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (scope : List X) : List (List Bool) → Option (List (List Bool × Coeff d))
  | [] => some []
  | key :: keys =>
      match checkedRow lo hi x fs (deposit scope key) with
      | none => none
      | some v =>
          match materialize lo hi x fs scope keys with
          | none => none
          | some tail => some ((key,v) :: tail)

theorem materialize_some {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (scope : List X) (keys : List (List Bool)) (table : List (List Bool × Coeff d))
    (h : materialize lo hi x fs scope keys = some table) :
    table = keys.map (fun k =>
      (k,(contractedFactor (cycloAlgebra d) x fs).eval (deposit scope k))) := by
  induction keys generalizing table with
  | nil => exact (Option.some.inj h).symm
  | cons key keys ih =>
      cases hv : checkedRow lo hi x fs (deposit scope key) with
      | none => simp only [materialize, hv] at h; contradiction
      | some v =>
          simp only [materialize, hv] at h
          cases ht : materialize lo hi x fs scope keys with
          | none => rw [ht] at h; contradiction
          | some tail =>
              rw [ht] at h
              have he : (key,v) :: tail = table := Option.some.inj h
              rw [← he, checked_row_some lo hi x fs _ v hv, ih tail ht]
              rfl

theorem materialize_length {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (scope : List X) (table : List (List Bool × Coeff d))
    (h : materialize lo hi x fs scope (rows scope.length) = some table) :
    table.length = 2^scope.length := by
  rw [materialize_some lo hi x fs scope _ table h, List.length_map, rows_length]

def lookup {A : Type} (fallback : A) (key : List Bool) :
    List (List Bool × A) → A
  | [] => fallback
  | (k,v) :: tail => if key = k then v else lookup fallback key tail

theorem lookup_map {A : Type} (fallback : A) (f : List Bool → A)
    (key : List Bool) (keys : List (List Bool)) (h : key ∈ keys) :
    lookup fallback key (keys.map (fun k => (k,f k))) = f key := by
  induction keys with
  | nil => exact False.elim (List.not_mem_nil h)
  | cons k ks ih =>
      change (if key = k then f k else lookup fallback key
        (ks.map (fun t => (t,f t)))) = f key
      by_cases he : key = k
      · subst k
        exact ite_eq_left rfl
      · rw [ite_eq_right he]
        exact ih ((List.mem_cons.mp h).resolve_left he)

theorem extract_agrees {X : Type} (scope : List X) (a b : X → Bool)
    (h : ∀ x, x ∈ scope → a x = b x) : extract a scope = extract b scope := by
  induction scope with
  | nil => rfl
  | cons x xs ih =>
      change a x :: extract a xs = b x :: extract b xs
      rw [h x (List.mem_cons.mpr (Or.inl rfl)),
          ih (fun y hy => h y (List.mem_cons.mpr (Or.inr hy)))]

def tableFactor {X : Type} {d : Nat} (scope : List X)
    (table : List (List Bool × Coeff d)) : ScopedFactor X (Coeff d) where
  scope := scope
  eval := fun a => lookup (finZero d) (extract a scope) table
  support := by
    intro a b h
    change lookup (finZero d) (extract a scope) table = lookup (finZero d) (extract b scope) table
    rw [extract_agrees scope a b h]

theorem materialized_factor_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (scope : List X) (table : List (List Bool × Coeff d)) (a : X → Bool)
    (hs : dependsOn scope (contractedFactor (cycloAlgebra d) x fs).eval)
    (h : materialize lo hi x fs scope (rows scope.length) = some table) :
    (tableFactor scope table).eval a = (contractedFactor (cycloAlgebra d) x fs).eval a := by
  change lookup (finZero d) (extract a scope) table = _
  rw [materialize_some lo hi x fs scope _ table h]
  rw [lookup_map (finZero d)
    (fun k => (contractedFactor (cycloAlgebra d) x fs).eval (deposit scope k))
    (extract a scope) (rows scope.length) (projection_mem_rows scope a)]
  exact factor_scope_projection scope _ hs a

/-- Domain admission checks the original raw scope, not the filtered scope. -/
def covered {X : Type} [DecidableEq X] (domain raw : List X) : Bool :=
  raw.all (fun v => decide (v ∈ domain))

theorem covered_sound {X : Type} [DecidableEq X] (domain raw : List X)
    (h : covered domain raw = true) : ∀ v, v ∈ raw → v ∈ domain := by
  intro v hv
  exact of_decide_eq_true ((List.all_eq_true.mp h) v hv)

def checkedStep {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain : List X) (x : X) (fs : List (ScopedFactor X (Coeff d))) :
    Option (List (ScopedFactor X (Coeff d))) :=
  let raw := (contractedFactor (cycloAlgebra d) x fs).scope
  let scope := canonical raw domain
  if covered domain raw then
    match materialize lo hi x fs scope (rows scope.length) with
    | none => none
    | some table => some (restFactors x fs ++ [tableFactor scope table])
  else none

theorem checked_step_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain : List X) (x : X)
    (fs gs : List (ScopedFactor X (Coeff d))) (a : X → Bool)
    (h : checkedStep lo hi domain x fs = some gs) :
    factorProduct (finOne d) finMul a gs =
      eliminate finAdd x (fun v => factorProduct (finOne d) finMul v fs) a := by
  let g := contractedFactor (cycloAlgebra d) x fs
  let scope := canonical g.scope domain
  change (if covered domain g.scope then
    match materialize lo hi x fs scope (rows scope.length) with
    | none => none
    | some table => some (restFactors x fs ++ [tableFactor scope table])
    else none) = some gs at h
  by_cases hc : covered domain g.scope = true
  · rw [ite_eq_left hc] at h
    cases ht : materialize lo hi x fs scope (rows scope.length) with
    | none => rw [ht] at h; contradiction
    | some table =>
        rw [ht] at h
        have he : restFactors x fs ++ [tableFactor scope table] = gs := Option.some.inj h
        have hs : dependsOn scope g.eval :=
          canonical_support domain g (covered_sound domain g.scope hc)
        have hv := materialized_factor_sound lo hi x fs scope table a hs ht
        rw [← he]
        change factorProduct (cycloAlgebra d).one (cycloAlgebra d).mul a
          (restFactors x fs ++ [tableFactor scope table]) = _
        rw [product_append (cycloAlgebra d)]
        change finMul (factorProduct (finOne d) finMul a (restFactors x fs))
          (finMul ((tableFactor scope table).eval a) (finOne d)) = _
        rw [hv]
        have hex := contract_step_sound (cycloAlgebra d) x a fs
        rw [contractStep, product_append] at hex
        exact hex
  · rw [ite_eq_right hc] at h
    contradiction

def checkedOrder {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain : List X) :
    List X → List (ScopedFactor X (Coeff d)) → Option (List (ScopedFactor X (Coeff d)))
  | [], fs => some fs
  | x :: xs, fs =>
      match checkedStep lo hi domain x fs with
      | none => none
      | some gs => checkedOrder lo hi domain xs gs

theorem checked_order_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain xs : List X)
    (fs gs : List (ScopedFactor X (Coeff d))) (a : X → Bool)
    (h : checkedOrder lo hi domain xs fs = some gs) :
    factorProduct (finOne d) finMul a gs =
      sumOrder finAdd xs (fun v => factorProduct (finOne d) finMul v fs) a := by
  induction xs generalizing fs with
  | nil =>
      have he : fs = gs := Option.some.inj h
      rw [← he]
      rfl
  | cons x xs ih =>
      cases ht : checkedStep lo hi domain x fs with
      | none => simp only [checkedOrder, ht] at h; contradiction
      | some mid =>
          simp only [checkedOrder, ht] at h
          have he : (fun v => factorProduct (finOne d) finMul v mid) =
              eliminate finAdd x (fun v => factorProduct (finOne d) finMul v fs) :=
            funext (fun v => checked_step_sound lo hi domain x fs mid v ht)
          change factorProduct (finOne d) finMul a gs =
            sumOrder finAdd xs (eliminate finAdd x
              (fun v => factorProduct (finOne d) finMul v fs)) a
          rw [ih mid h, he]

def checkedResult {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) : Option (Coeff d) :=
  match checkedOrder lo hi domain xs fs with
  | none => none
  | some gs => checkedProduct lo hi (finOne d) (gs.map (fun f => f.eval a))

theorem checked_result_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) (v : Coeff d) (h : checkedResult lo hi domain xs fs a = some v) :
    v = sumOrder finAdd xs (fun b => factorProduct (finOne d) finMul b fs) a := by
  cases ht : checkedOrder lo hi domain xs fs with
  | none => simp only [checkedResult, ht] at h; contradiction
  | some gs =>
      simp only [checkedResult, ht] at h
      rw [checked_product_from_one lo hi v _ h, exact_product_eval]
      exact checked_order_sound lo hi domain xs fs gs a ht

theorem checked_order_head_reject {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain xs : List X) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (h : checkedStep lo hi domain x fs = none) :
    checkedOrder lo hi domain (x :: xs) fs = none := by
  simp only [checkedOrder, h]

#print axioms materialize_some
#print axioms materialize_length
#print axioms lookup_map
#print axioms extract_agrees
#print axioms materialized_factor_sound
#print axioms covered_sound
#print axioms checked_step_sound
#print axioms checked_order_sound
#print axioms checked_result_sound
#print axioms checked_order_head_reject
end QuPRS.AffineCheckedOrder
