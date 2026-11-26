/-
Factor scope reference semantics: ordered Boolean coordinates, not a
proof of packed u64/usize operations. Generic algebraic laws are explicit
premises so that the bucket argument can later be instantiated in the
negacyclic coefficient ring.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineFactorScope

def write {X : Type} [DecidableEq X] (a : X → Bool) (x : X) (b : Bool) : X → Bool :=
  fun y => if y = x then b else a y

def extract {X : Type} (a : X → Bool) (scope : List X) : List Bool :=
  scope.map a

def deposit {X : Type} [DecidableEq X] : List X → List Bool → X → Bool
  | x :: xs, b :: bs => write (deposit xs bs) x b
  | _, _ => fun _ => false

theorem deposit_outside {X : Type} [DecidableEq X] (scope : List X)
    (bits : List Bool) (y : X) (h : y ∉ scope) :
    deposit scope bits y = false := by
  induction scope generalizing bits with
  | nil => rfl
  | cons x xs ih =>
      cases bits with
      | nil => rfl
      | cons b bs =>
          have hn : y ≠ x := fun he => h (List.mem_cons.mpr (Or.inl he))
          have ht : y ∉ xs := fun hm => h (List.mem_cons.mpr (Or.inr hm))
          change write (deposit xs bs) x b y = false
          rw [write, ite_eq_right hn]
          exact ih bs ht

theorem deposit_extract_on {X : Type} [DecidableEq X] (scope : List X)
    (a : X → Bool) (y : X) (h : y ∈ scope) :
    deposit scope (extract a scope) y = a y := by
  induction scope with
  | nil => exact False.elim (List.not_mem_nil h)
  | cons x xs ih =>
      change write (deposit xs (extract a xs)) x (a x) y = a y
      by_cases he : y = x
      · subst y
        simp [write]
      · have ht : y ∈ xs := (List.mem_cons.mp h).resolve_left he
        rw [write, ite_eq_right he]
        exact ih ht

theorem extract_write_outside {X : Type} [DecidableEq X]
    (scope : List X) (a : X → Bool) (x : X) (b : Bool)
    (h : x ∉ scope) :
    extract (write a x b) scope = extract a scope := by
  induction scope with
  | nil => rfl
  | cons y ys ih =>
      have hn : y ≠ x := fun he => h (List.mem_cons.mpr (Or.inl he.symm))
      have ht : x ∉ ys := fun hm => h (List.mem_cons.mpr (Or.inr hm))
      change write a x b y :: extract (write a x b) ys = a y :: extract a ys
      rw [write, ite_eq_right hn, ih ht]

theorem extract_deposit {X : Type} [DecidableEq X] (scope : List X)
    (bits : List Bool) (hn : scope.Nodup) (hl : bits.length = scope.length) :
    extract (deposit scope bits) scope = bits := by
  induction scope generalizing bits with
  | nil =>
      cases bits with
      | nil => rfl
      | cons b bs =>
          exact False.elim (Nat.succ_ne_zero bs.length hl)
  | cons x xs ih =>
      cases bits with
      | nil =>
          exact False.elim (Nat.succ_ne_zero xs.length hl.symm)
      | cons b bs =>
          have hnd := List.nodup_cons.mp hn
          have hlen : bs.length = xs.length := Nat.succ.inj hl
          change write (deposit xs bs) x b x ::
            extract (write (deposit xs bs) x b) xs = b :: bs
          have he : write (deposit xs bs) x b x = b := ite_eq_left rfl
          rw [he, extract_write_outside xs (deposit xs bs) x b hnd.1, ih bs hnd.2 hlen]

def dependsOn {X A : Type} (scope : List X) (f : (X → Bool) → A) : Prop :=
  ∀ a b, (∀ x, x ∈ scope → a x = b x) → f a = f b

theorem factor_scope_projection {X A : Type} [DecidableEq X]
    (scope : List X) (f : (X → Bool) → A) (hf : dependsOn scope f)
    (a : X → Bool) :
    f (deposit scope (extract a scope)) = f a :=
  hf _ _ (fun x hx => deposit_extract_on scope a x hx)

theorem factor_outside_invariant {X A : Type} [DecidableEq X]
    (scope : List X) (f : (X → Bool) → A) (hf : dependsOn scope f)
    (x : X) (hx : x ∉ scope) (a : X → Bool) (b : Bool) :
    f (write a x b) = f a := by
  apply hf
  intro y hy
  have hn : y ≠ x := fun he => hx (he ▸ hy)
  exact ite_eq_right hn

def eliminate {X A : Type} [DecidableEq X] (add : A → A → A)
    (x : X) (bucket : (X → Bool) → A) (a : X → Bool) : A :=
  add (bucket (write a x false)) (bucket (write a x true))

/-- The retained product may be factored outside the Boolean sum iff it
    is independent of the eliminated variable; algebraic law explicit. -/
theorem bucket_eliminate {X A : Type} [DecidableEq X]
    (add mul : A → A → A)
    (dist : ∀ r p q, add (mul r p) (mul r q) = mul r (add p q))
    (scope : List X) (rest bucket : (X → Bool) → A)
    (hr : dependsOn scope rest) (x : X) (hx : x ∉ scope) (a : X → Bool) :
    eliminate add x (fun v => mul (rest v) (bucket v)) a =
      mul (rest a) (eliminate add x bucket a) := by
  change add (mul (rest (write a x false)) (bucket (write a x false)))
    (mul (rest (write a x true)) (bucket (write a x true))) =
      mul (rest a) (add (bucket (write a x false)) (bucket (write a x true)))
  rw [factor_outside_invariant scope rest hr x hx a false,
      factor_outside_invariant scope rest hr x hx a true]
  exact dist _ _ _

theorem empty_bucket {X A : Type} [DecidableEq X] (add : A → A → A)
    (one : A) (x : X) (a : X → Bool) :
    eliminate add x (fun _ => one) a = add one one := rfl


/-- A table's denotation includes its support invariant. The list order
    models the native factor list; partition preserves each sublist order. -/
structure ScopedFactor (X A : Type) where
  scope : List X
  eval : (X → Bool) → A
  support : dependsOn scope eval

def factorProduct {X A : Type} (one : A) (mul : A → A → A)
    (a : X → Bool) : List (ScopedFactor X A) → A
  | [] => one
  | f :: fs => mul (f.eval a) (factorProduct one mul a fs)

def bucketFactors {X A : Type} [DecidableEq X] (x : X) :
    List (ScopedFactor X A) → List (ScopedFactor X A)
  | [] => []
  | f :: fs => if x ∈ f.scope then f :: bucketFactors x fs else bucketFactors x fs

def restFactors {X A : Type} [DecidableEq X] (x : X) :
    List (ScopedFactor X A) → List (ScopedFactor X A)
  | [] => []
  | f :: fs => if x ∈ f.scope then restFactors x fs else f :: restFactors x fs

theorem product_partition {X A : Type} [DecidableEq X]
    (one : A) (mul : A → A → A)
    (unit : mul one one = one)
    (assoc : ∀ p q r, mul (mul p q) r = mul p (mul q r))
    (comm : ∀ p q, mul p q = mul q p)
    (x : X) (a : X → Bool) (fs : List (ScopedFactor X A)) :
    factorProduct one mul a fs =
      mul (factorProduct one mul a (restFactors x fs))
        (factorProduct one mul a (bucketFactors x fs)) := by
  induction fs with
  | nil => exact unit.symm
  | cons f fs ih =>
      by_cases hx : x ∈ f.scope
      · simp only [factorProduct, restFactors, bucketFactors, ite_eq_left hx]
        rw [ih, ← assoc, comm (f.eval a) (factorProduct one mul a (restFactors x fs)), assoc]
      · simp only [factorProduct, restFactors, bucketFactors, ite_eq_right hx]
        rw [ih, assoc]

theorem rest_product_independent {X A : Type} [DecidableEq X]
    (one : A) (mul : A → A → A) (x : X) (a : X → Bool) (b : Bool)
    (fs : List (ScopedFactor X A)) :
    factorProduct one mul (write a x b) (restFactors x fs) =
      factorProduct one mul a (restFactors x fs) := by
  induction fs with
  | nil => rfl
  | cons f fs ih =>
      by_cases hx : x ∈ f.scope
      · simpa only [restFactors, ite_eq_left hx] using ih
      · simp only [restFactors, ite_eq_right hx, factorProduct,
          factor_outside_invariant f.scope f.eval f.support x hx a b, ih]

/-- One exact bucket step on the actual partitioned factor list.
    Commutativity, associativity and distributivity are explicit
    obligations for the coefficient algebra, not assumed Rust properties. -/
theorem partitioned_bucket_eliminate {X A : Type} [DecidableEq X]
    (one : A) (add mul : A → A → A)
    (unit : mul one one = one)
    (assoc : ∀ p q r, mul (mul p q) r = mul p (mul q r))
    (comm : ∀ p q, mul p q = mul q p)
    (dist : ∀ r p q, add (mul r p) (mul r q) = mul r (add p q))
    (x : X) (a : X → Bool) (fs : List (ScopedFactor X A)) :
    eliminate add x (fun v => factorProduct one mul v fs) a =
      mul (factorProduct one mul a (restFactors x fs))
        (eliminate add x (fun v => factorProduct one mul v (bucketFactors x fs)) a) := by
  change add (factorProduct one mul (write a x false) fs)
    (factorProduct one mul (write a x true) fs) =
      mul (factorProduct one mul a (restFactors x fs))
        (add (factorProduct one mul (write a x false) (bucketFactors x fs))
          (factorProduct one mul (write a x true) (bucketFactors x fs)))
  rw [product_partition one mul unit assoc comm x (write a x false) fs,
      product_partition one mul unit assoc comm x (write a x true) fs,
      rest_product_independent one mul x a false fs,
      rest_product_independent one mul x a true fs]
  exact dist _ _ _

theorem write_overwrite {X : Type} [DecidableEq X] (a : X → Bool)
    (x : X) (b c : Bool) :
    write (write a x b) x c = write a x c := by
  funext y
  by_cases h : y = x
  · simp [write, h]
  · simp [write, h]

theorem eliminated_variable_independent {X A : Type} [DecidableEq X]
    (add : A → A → A) (x : X) (bucket : (X → Bool) → A)
    (a : X → Bool) (b : Bool) :
    eliminate add x bucket (write a x b) = eliminate add x bucket a := by
  unfold eliminate
  rw [write_overwrite a x b false, write_overwrite a x b true]

#print axioms product_partition
#print axioms rest_product_independent
#print axioms partitioned_bucket_eliminate
#print axioms write_overwrite
#print axioms eliminated_variable_independent
#print axioms deposit_outside
#print axioms deposit_extract_on
#print axioms extract_write_outside
#print axioms extract_deposit
#print axioms factor_scope_projection
#print axioms factor_outside_invariant
#print axioms bucket_eliminate
#print axioms empty_bucket
end QuPRS.AffineFactorScope
