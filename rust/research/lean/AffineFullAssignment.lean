/-
Independent explicit Boolean assignment sum and final scope closure.
All coefficients are exact integers. The hidden list is admitted against
its declared domain; assignment keys use the already checked enumeration.
The base assignment is preserved outside the hidden scope.
No machine-word, source extraction, or native executor refinement.
-/
import AffineHiddenOrder
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineFullAssignment
open QuPRS.AffineFactorScope
open QuPRS.AffineFactorElimination
open QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineCheckedFactor
open QuPRS.AffineCanonicalScope
open QuPRS.AffineCheckedOrder
open QuPRS.AffineHiddenOrder

def overlay {X : Type} [DecidableEq X] (a : X → Bool)
    (scope : List X) (key : List Bool) : X → Bool :=
  fun y => if y ∈ scope then deposit scope key y else a y

theorem overlay_nil {X : Type} [DecidableEq X] (a : X → Bool) :
    overlay a [] [] = a := by
  funext y
  simp [overlay]

theorem overlay_cons {X : Type} [DecidableEq X] (a : X → Bool)
    (x : X) (xs : List X) (b : Bool) (bs : List Bool) :
    overlay a (x :: xs) (b :: bs) = write (overlay a xs bs) x b := by
  funext y
  by_cases he : y = x
  · subst y
    simp [overlay, deposit, write]
  · simp [overlay, deposit, write, he]

theorem overlay_outside {X : Type} [DecidableEq X] (a : X → Bool)
    (scope : List X) (key : List Bool) (y : X) (hy : y ∉ scope) :
    overlay a scope key y = a y := by
  exact ite_eq_right hy

theorem overlay_roundtrip {X : Type} [DecidableEq X] (a : X → Bool)
    (scope : List X) (key : List Bool) (hn : scope.Nodup)
    (hk : key ∈ rows scope.length) :
    extract (overlay a scope key) scope = key := by
  calc
    _ = extract (deposit scope key) scope :=
      extract_agrees scope _ _ (fun y hy => ite_eq_left hy)
    _ = key := extract_deposit scope key hn ((mem_rows_iff _ _).mp hk)

theorem overlay_complete {X : Type} [DecidableEq X] (a b : X → Bool)
    (scope : List X) (h : ∀ y, y ∉ scope → a y = b y) :
    overlay a scope (extract b scope) = b := by
  funext y
  by_cases hy : y ∈ scope
  · exact (ite_eq_left hy).trans (deposit_extract_on scope b y hy)
  · exact (ite_eq_right hy).trans (h y hy)

theorem overlay_injective {X : Type} [DecidableEq X] (a : X → Bool)
    (scope : List X) (hn : scope.Nodup) (k l : List Bool)
    (hk : k ∈ rows scope.length) (hl : l ∈ rows scope.length)
    (h : overlay a scope k = overlay a scope l) : k = l := by
  have he := congrArg (fun v => extract v scope) h
  rw [overlay_roundtrip a scope k hn hk, overlay_roundtrip a scope l hn hl] at he
  exact he

def sumKeys {d : Nat} (f : List Bool → Coeff d) : List (List Bool) → Coeff d
  | [] => finZero d
  | key :: keys => finAdd (f key) (sumKeys f keys)

theorem sum_expand {d : Nat} (f : List Bool → Coeff d) (keys : List (List Bool)) :
    sumKeys f (expand keys) =
      sumKeys (fun k => finAdd (f (false :: k)) (f (true :: k))) keys := by
  induction keys with
  | nil => rfl
  | cons key keys ih =>
      change finAdd (f (false :: key)) (finAdd (f (true :: key))
        (sumKeys f (expand keys))) =
        finAdd (finAdd (f (false :: key)) (f (true :: key)))
          (sumKeys (fun k => finAdd (f (false :: k)) (f (true :: k))) keys)
      rw [ih]
      funext i
      exact (Int.add_assoc _ _ _).symm

def explicitSum {X : Type} [DecidableEq X] {d : Nat}
    (hidden : List X) (f : (X → Bool) → Coeff d) (a : X → Bool) : Coeff d :=
  sumKeys (fun k => f (overlay a hidden k)) (rows hidden.length)

theorem sum_order_explicit {X : Type} [DecidableEq X] {d : Nat}
    (hidden : List X) (f : (X → Bool) → Coeff d) (a : X → Bool) :
    sumOrder finAdd hidden f a = explicitSum hidden f a := by
  induction hidden generalizing f with
  | nil =>
      change f a = finAdd (f (overlay a [] [])) (finZero d)
      rw [overlay_nil]
      funext i
      exact (Int.add_zero (f a i)).symm
  | cons x xs ih =>
      change sumOrder finAdd xs (eliminate finAdd x f) a =
        sumKeys (fun k => f (overlay a (x :: xs) k)) (expand (rows xs.length))
      rw [ih, sum_expand]
      have he : (fun k => finAdd (f (overlay a (x :: xs) (false :: k)))
            (f (overlay a (x :: xs) (true :: k)))) =
          (fun k => eliminate finAdd x f (overlay a xs k)) := by
        funext k
        rw [overlay_cons, overlay_cons]
        rfl
      rw [he]
      rfl

theorem admitted_explicit_sound {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs : List X) (fs : List (ScopedFactor X (Coeff d)))
    (a : X → Bool) (v : Coeff d) (h : admittedResult lo hi domain hidden xs fs a = some v) :
    v = explicitSum hidden (fun b => factorProduct (finOne d) finMul b fs) a :=
  (admitted_result_sound lo hi domain hidden xs fs a v h).trans
    (sum_order_explicit hidden _ a)

theorem all_scope_append {X A : Type} (fs gs : List (ScopedFactor X A)) :
    allScope (fs ++ gs) = allScope fs ++ allScope gs := by
  induction fs with
  | nil => rfl
  | cons f fs ih =>
      change f.scope ++ allScope (fs ++ gs) = (f.scope ++ allScope fs) ++ allScope gs
      rw [ih, List.append_assoc]

theorem rest_scope {X A : Type} [DecidableEq X] (x y : X)
    (fs : List (ScopedFactor X A)) (h : y ∈ allScope (restFactors x fs)) :
    y ∈ allScope fs ∧ y ≠ x := by
  induction fs with
  | nil => exact False.elim (List.not_mem_nil h)
  | cons f fs ih =>
      by_cases hx : x ∈ f.scope
      · rw [restFactors, ite_eq_left hx] at h
        have ht := ih h
        exact ⟨List.mem_append.mpr (Or.inr ht.1), ht.2⟩
      · rw [restFactors, ite_eq_right hx] at h
        change y ∈ f.scope ++ allScope (restFactors x fs) at h
        rcases List.mem_append.mp h with hf | ht
        · exact ⟨List.mem_append.mpr (Or.inl hf), fun he => hx (he ▸ hf)⟩
        · have ht' := ih ht
          exact ⟨List.mem_append.mpr (Or.inr ht'.1), ht'.2⟩

theorem bucket_scope {X A : Type} [DecidableEq X] (x y : X)
    (fs : List (ScopedFactor X A)) (h : y ∈ allScope (bucketFactors x fs)) :
    y ∈ allScope fs := by
  induction fs with
  | nil => exact False.elim (List.not_mem_nil h)
  | cons f fs ih =>
      by_cases hx : x ∈ f.scope
      · rw [bucketFactors, ite_eq_left hx] at h
        change y ∈ f.scope ++ allScope (bucketFactors x fs) at h
        rcases List.mem_append.mp h with hf | ht
        · exact List.mem_append.mpr (Or.inl hf)
        · exact List.mem_append.mpr (Or.inr (ih ht))
      · rw [bucketFactors, ite_eq_right hx] at h
        exact List.mem_append.mpr (Or.inr (ih h))

theorem checked_step_scope {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain : List X) (x : X) (fs gs : List (ScopedFactor X (Coeff d)))
    (h : checkedStep lo hi domain x fs = some gs) (y : X) (hm : y ∈ allScope gs) :
    y ∈ allScope fs ∧ y ≠ x := by
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
        rw [← he, all_scope_append] at hm
        rcases List.mem_append.mp hm with hr | hn
        · exact rest_scope x y fs hr
        · change y ∈ scope ++ [] at hn
          rw [List.append_nil] at hn
          have hraw := ((canonical_mem g.scope domain y).mp hn).2
          change y ∈ without x (allScope (bucketFactors x fs)) at hraw
          have hb := (mem_without x y _).mp hraw
          exact ⟨bucket_scope x y fs hb.1, hb.2⟩
  · rw [ite_eq_right hc] at h
    contradiction

theorem checked_order_scope {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain xs : List X) (fs gs : List (ScopedFactor X (Coeff d)))
    (h : checkedOrder lo hi domain xs fs = some gs) (y : X) (hm : y ∈ allScope gs) :
    y ∈ allScope fs ∧ y ∉ xs := by
  induction xs generalizing fs with
  | nil =>
      have he : fs = gs := Option.some.inj h
      exact ⟨he.symm ▸ hm, List.not_mem_nil⟩
  | cons x xs ih =>
      cases ht : checkedStep lo hi domain x fs with
      | none => simp only [checkedOrder, ht] at h; contradiction
      | some mid =>
          simp only [checkedOrder, ht] at h
          have hr := ih mid h
          have hs := checked_step_scope lo hi domain x fs mid ht y hr.1
          exact ⟨hs.1, fun hn => (List.mem_cons.mp hn).elim hs.2 hr.2⟩

theorem final_scope_boundary {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs boundary : List X)
    (fs gs : List (ScopedFactor X (Coeff d)))
    (ha : admitOrder hidden xs = true)
    (h : checkedOrder lo hi domain xs fs = some gs)
    (hinit : ∀ y, y ∈ allScope fs → y ∈ hidden ∨ y ∈ boundary)
    (y : X) (hm : y ∈ allScope gs) : y ∈ boundary := by
  have hs := checked_order_scope lo hi domain xs fs gs h y hm
  exact (hinit y hs.1).resolve_left (fun hh => hs.2 ((admitted_coverage hidden xs ha y).mpr hh))

theorem final_product_boundary {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (domain hidden xs boundary : List X)
    (fs gs : List (ScopedFactor X (Coeff d)))
    (ha : admitOrder hidden xs = true)
    (h : checkedOrder lo hi domain xs fs = some gs)
    (hinit : ∀ y, y ∈ allScope fs → y ∈ hidden ∨ y ∈ boundary) :
    dependsOn boundary (fun a => factorProduct (finOne d) finMul a gs) := by
  intro a b hab
  exact product_support (cycloAlgebra d) gs a b
    (fun y hy => hab y (final_scope_boundary lo hi domain hidden xs boundary fs gs ha h hinit y hy))

#print axioms overlay_nil
#print axioms overlay_cons
#print axioms overlay_outside
#print axioms overlay_roundtrip
#print axioms overlay_complete
#print axioms overlay_injective
#print axioms sum_expand
#print axioms sum_order_explicit
#print axioms admitted_explicit_sound
#print axioms all_scope_append
#print axioms rest_scope
#print axioms bucket_scope
#print axioms checked_step_scope
#print axioms checked_order_scope
#print axioms final_scope_boundary
#print axioms final_product_boundary
end QuPRS.AffineFullAssignment
