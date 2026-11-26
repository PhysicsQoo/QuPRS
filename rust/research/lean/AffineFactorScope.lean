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
      | cons b bs => simp at hl
  | cons x xs ih =>
      cases bits with
      | nil => simp at hl
      | cons b bs =>
          have hnd := List.nodup_cons.mp hn
          have hlen : bs.length = xs.length := Nat.succ.inj hl
          change write (deposit xs bs) x b x ::
            extract (write (deposit xs bs) x b) xs = b :: bs
          have he : write (deposit xs bs) x b x = b := by simp [write]
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
  unfold eliminate
  rw [factor_outside_invariant scope rest hr x hx a false,
      factor_outside_invariant scope rest hr x hx a true]
  exact dist _ _ _

theorem empty_bucket {X A : Type} [DecidableEq X] (add : A → A → A)
    (one : A) (x : X) (a : X → Bool) :
    eliminate add x (fun _ => one) a = add one one := rfl

#print axioms deposit_outside
#print axioms deposit_extract_on
#print axioms extract_write_outside
#print axioms extract_deposit
#print axioms factor_scope_projection
#print axioms factor_outside_invariant
#print axioms bucket_eliminate
#print axioms empty_bucket
end QuPRS.AffineFactorScope
