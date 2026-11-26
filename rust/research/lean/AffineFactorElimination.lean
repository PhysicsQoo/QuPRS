/-
Exact variable elimination, with coefficient algebra laws explicit.
Scope lists represent sets semantically; deduplicating/packing these
lists and correspondence to Rust checked execution are separate tasks.
-/
import AffineFactorScope
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineFactorElimination
open QuPRS.AffineFactorScope

structure Algebra (A : Type) where
  one : A
  add : A → A → A
  mul : A → A → A
  rightUnit : ∀ a, mul a one = a
  assoc : ∀ p q r, mul (mul p q) r = mul p (mul q r)
  comm : ∀ p q, mul p q = mul q p
  dist : ∀ r p q, add (mul r p) (mul r q) = mul r (add p q)

def allScope {X A : Type} : List (ScopedFactor X A) → List X
  | [] => []
  | f :: fs => f.scope ++ allScope fs

def without {X : Type} [DecidableEq X] (x : X) : List X → List X
  | [] => []
  | y :: ys => if y = x then without x ys else y :: without x ys

theorem mem_without {X : Type} [DecidableEq X] (x y : X) (xs : List X) :
    y ∈ without x xs ↔ y ∈ xs ∧ y ≠ x := by
  induction xs with
  | nil =>
      constructor
      · intro h
        exact False.elim (List.not_mem_nil h)
      · intro h
        exact False.elim (List.not_mem_nil h.1)
  | cons z zs ih =>
      by_cases hz : z = x
      · subst z
        rw [without, ite_eq_left rfl, ih, List.mem_cons]
        constructor
        · intro h
          exact ⟨Or.inr h.1, h.2⟩
        · intro h
          exact ⟨h.1.resolve_left h.2, h.2⟩
      · rw [without, ite_eq_right hz, List.mem_cons, ih, List.mem_cons]
        constructor
        · intro h
          rcases h with he | ht
          · exact ⟨Or.inl he, fun hy => hz (he.symm.trans hy)⟩
          · exact ⟨Or.inr ht.1, ht.2⟩
        · intro h
          rcases h.1 with he | ht
          · exact Or.inl he
          · exact Or.inr ⟨ht, h.2⟩

theorem removed_not_member {X : Type} [DecidableEq X] (x : X) (xs : List X) :
    x ∉ without x xs :=
  fun h => ((mem_without x x xs).mp h).2 rfl

theorem product_support {X A : Type} (alg : Algebra A)
    (fs : List (ScopedFactor X A)) :
    dependsOn (allScope fs) (fun a => factorProduct alg.one alg.mul a fs) := by
  induction fs with
  | nil =>
      intro a b _
      rfl
  | cons f fs ih =>
      intro a b h
      have hf : f.eval a = f.eval b :=
        f.support a b (fun x hx => h x (List.mem_append.mpr (Or.inl hx)))
      have ht : factorProduct alg.one alg.mul a fs =
          factorProduct alg.one alg.mul b fs :=
        ih a b (fun x hx => h x (List.mem_append.mpr (Or.inr hx)))
      change alg.mul (f.eval a) (factorProduct alg.one alg.mul a fs) =
        alg.mul (f.eval b) (factorProduct alg.one alg.mul b fs)
      rw [hf, ht]

theorem eliminate_support {X A : Type} [DecidableEq X]
    (add : A → A → A) (x : X) (scope : List X)
    (f : (X → Bool) → A) (hf : dependsOn scope f) :
    dependsOn (without x scope) (eliminate add x f) := by
  intro a b hab
  have hw (v : Bool) : f (write a x v) = f (write b x v) := by
    apply hf
    intro y hy
    by_cases he : y = x
    · simp only [write, ite_eq_left he]
    · simp only [write, ite_eq_right he]
      exact hab y ((mem_without x y scope).mpr ⟨hy, he⟩)
  unfold eliminate
  rw [hw false, hw true]

def contractedFactor {X A : Type} [DecidableEq X] (alg : Algebra A)
    (x : X) (fs : List (ScopedFactor X A)) : ScopedFactor X A :=
  ⟨without x (allScope (bucketFactors x fs)),
   eliminate alg.add x (fun a => factorProduct alg.one alg.mul a (bucketFactors x fs)),
   eliminate_support alg.add x _ _ (product_support alg (bucketFactors x fs))⟩

theorem contracted_scope_closed {X A : Type} [DecidableEq X]
    (alg : Algebra A) (x : X) (fs : List (ScopedFactor X A)) :
    x ∉ (contractedFactor alg x fs).scope :=
  removed_not_member x (allScope (bucketFactors x fs))

def contractStep {X A : Type} [DecidableEq X] (alg : Algebra A)
    (x : X) (fs : List (ScopedFactor X A)) : List (ScopedFactor X A) :=
  restFactors x fs ++ [contractedFactor alg x fs]

theorem product_append {X A : Type} (alg : Algebra A) (a : X → Bool)
    (fs gs : List (ScopedFactor X A)) :
    factorProduct alg.one alg.mul a (fs ++ gs) =
      alg.mul (factorProduct alg.one alg.mul a fs)
        (factorProduct alg.one alg.mul a gs) := by
  induction fs with
  | nil =>
      change factorProduct alg.one alg.mul a gs =
        alg.mul alg.one (factorProduct alg.one alg.mul a gs)
      rw [alg.comm alg.one _, alg.rightUnit]
  | cons f fs ih =>
      change alg.mul (f.eval a) (factorProduct alg.one alg.mul a (fs ++ gs)) =
        alg.mul (alg.mul (f.eval a) (factorProduct alg.one alg.mul a fs))
          (factorProduct alg.one alg.mul a gs)
      rw [ih, alg.assoc]

theorem contract_step_sound {X A : Type} [DecidableEq X] (alg : Algebra A)
    (x : X) (a : X → Bool) (fs : List (ScopedFactor X A)) :
    factorProduct alg.one alg.mul a (contractStep alg x fs) =
      eliminate alg.add x (fun v => factorProduct alg.one alg.mul v fs) a := by
  rw [contractStep, product_append]
  change alg.mul (factorProduct alg.one alg.mul a (restFactors x fs))
    (alg.mul (eliminate alg.add x
      (fun v => factorProduct alg.one alg.mul v (bucketFactors x fs)) a) alg.one) = _
  rw [alg.rightUnit]
  exact (partitioned_bucket_eliminate alg.one alg.add alg.mul
    (alg.rightUnit alg.one) alg.assoc alg.comm alg.dist x a fs).symm

def contractOrder {X A : Type} [DecidableEq X] (alg : Algebra A) :
    List X → List (ScopedFactor X A) → List (ScopedFactor X A)
  | [], fs => fs
  | x :: xs, fs => contractOrder alg xs (contractStep alg x fs)

def sumOrder {X A : Type} [DecidableEq X] (add : A → A → A) :
    List X → ((X → Bool) → A) → (X → Bool) → A
  | [], f => f
  | x :: xs, f => sumOrder add xs (eliminate add x f)

theorem contract_order_sound {X A : Type} [DecidableEq X] (alg : Algebra A)
    (xs : List X) (fs : List (ScopedFactor X A)) (a : X → Bool) :
    factorProduct alg.one alg.mul a (contractOrder alg xs fs) =
      sumOrder alg.add xs (fun v => factorProduct alg.one alg.mul v fs) a := by
  induction xs generalizing fs with
  | nil => rfl
  | cons x xs ih =>
      change factorProduct alg.one alg.mul a (contractOrder alg xs (contractStep alg x fs)) =
        sumOrder alg.add xs (eliminate alg.add x
          (fun v => factorProduct alg.one alg.mul v fs)) a
      rw [ih]
      have he : (fun v => factorProduct alg.one alg.mul v (contractStep alg x fs)) =
          eliminate alg.add x (fun v => factorProduct alg.one alg.mul v fs) :=
        funext (fun v => contract_step_sound alg x v fs)
      rw [he]

#print axioms mem_without
#print axioms removed_not_member
#print axioms product_support
#print axioms eliminate_support
#print axioms contracted_scope_closed
#print axioms product_append
#print axioms contract_step_sound
#print axioms contract_order_sound
end QuPRS.AffineFactorElimination
