/-
Conditional trace reduction: unbounded finite-list fiber lemmas and
exact eighth-root cyclotomic arithmetic. No Mathlib, no sorry,
no axiom declarations, no native_decide.
Semantic layer only: Rust ANF/phase substitution, alias forest
construction, source admission, and complex embedding are not refined.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.ConditionalTrace

def mask {A : Type} [Zero A] (b : Bool) (a : A) : A :=
  if b then a else 0

def sumPaths {X A : Type} [Zero A] [Add A] (xs : List X)
    (f : X → A) : A :=
  match xs with
  | [] => 0
  | x :: rest => f x + sumPaths rest f

theorem sum_congr {X A : Type} [Zero A] [Add A]
    (xs : List X) (f g : X → A) (h : ∀ x, f x = g x) :
    sumPaths xs f = sumPaths xs g := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp only [sumPaths, h x, ih]

/-- Unique extension: y xor rhs = 0 selects precisely one y.
    The other constraints and amplitude can depend arbitrarily on y. -/
theorem unique_fiber {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (rhs : Bool) (g : Bool → Bool) (a : Bool → A) :
    mask (!(false.xor rhs) && g false) (a false) +
      mask (!(true.xor rhs) && g true) (a true) =
      mask (g rhs) (a rhs) := by
  cases rhs <;> simp [mask, zl, zr]

theorem substitution_sum {X A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (xs : List X) (rhs : X → Bool) (g : X → Bool → Bool)
    (a : X → Bool → A) :
    sumPaths xs (fun x =>
      mask (!(false.xor rhs x) && g x false) (a x false) +
      mask (!(true.xor rhs x) && g x true) (a x true)) =
    sumPaths xs (fun x => mask (g x (rhs x)) (a x (rhs x))) := by
  apply sum_congr
  intro x
  exact unique_fiber zl zr (rhs x) (g x) (a x)

/-- A simple alias step is the same theorem with rhs a live bit.
    Induction over a valid forest uses the general composition below. -/
theorem alias_fiber {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (z : Bool) (g : Bool → Bool) (a : Bool → A) :
    mask (!(false.xor z) && g false) (a false) +
      mask (!(true.xor z) && g true) (a true) = mask (g z) (a z) :=
  unique_fiber zl zr z g a

/-- Sum-level factor lifting assumes only the specified additive law. -/
theorem scale_sum {X A : Type} [Zero A] [Add A]
    (scale : A → A) (h0 : scale 0 = 0)
    (ha : ∀ a b : A, scale (a+b) = scale a + scale b)
    (xs : List X) (f : X → A) :
    sumPaths xs (fun x => scale (f x)) = scale (sumPaths xs f) := by
  induction xs with
  | nil => exact h0.symm
  | cons x xs ih => simp only [sumPaths, ih, ha]

theorem free_fiber {A : Type} [Zero A] [Add A]
    (g : Bool) (a : A) :
    mask g a + mask g a = (fun x : A => x+x) (mask g a) := rfl

theorem free_sum {X A : Type} [Zero A] [Add A]
    (h0 : (0 : A) + 0 = 0)
    (hadd : ∀ a b : A, (a+b)+(a+b) = (a+a)+(b+b))
    (xs : List X) (g : X → Bool) (a : X → A) :
    sumPaths xs (fun x => mask (g x) (a x) + mask (g x) (a x)) =
      sumPaths xs (fun x => mask (g x) (a x)) +
      sumPaths xs (fun x => mask (g x) (a x)) :=
  scale_sum (fun x : A => x+x) h0 hadd xs (fun x => mask (g x) (a x))

/-- HH: summed y is independent of every remaining constraint,
    but the constraint may depend on the eliminated pivot z. -/
def hhAt {A : Type} [Zero A] [Add A] [Neg A]
    (q z : Bool) (g : Bool → Bool) (a : Bool → A) : A :=
  mask (g z) (a z) + mask (g z) (if z = q then a z else -(a z))

theorem hh_point {A : Type} [Zero A] [Add A] [Neg A]
    (h0 : (0 : A)+0 = 0) (hn : ∀ a : A, a + -a = 0)
    (q z : Bool) (g : Bool → Bool) (a : Bool → A) :
    hhAt q z g a =
      if z = q then mask (g z) (a z) + mask (g z) (a z) else 0 := by
  by_cases h : z = q
  · simp [hhAt, h]
  · simp only [hhAt, h, if_false]
    cases hg : g z <;> simp [mask, hg, h0, hn]

theorem hh_fiber {A : Type} [Zero A] [Add A] [Neg A]
    (h0 : (0 : A)+0 = 0) (hn : ∀ a : A, a + -a = 0)
    (zl : ∀ a : A, 0+a = a) (zr : ∀ a : A, a+0 = a)
    (q : Bool) (g : Bool → Bool) (a : Bool → A) :
    hhAt q false g a + hhAt q true g a =
      mask (g q) (a q) + mask (g q) (a q) := by
  rw [hh_point h0 hn, hh_point h0 hn]
  cases q <;> simp [zl, zr]

/-- Exact Z[zeta_8] representation modulo zeta_8^4 = -1.
    The tuples are coefficients in basis 1,zeta,zeta^2,zeta^3.
    This proves all Z8 phase fibers without an analytic premise. -/
abbrev C8 := Int × Int × Int × Int
def plus (a b : C8) : C8 :=
  (a.1+b.1, a.2.1+b.2.1, a.2.2.1+b.2.2.1, a.2.2.2+b.2.2.2)

def root8 (k : Fin 8) : C8 :=
  match k.val with
  | 0 => (1,0,0,0)
  | 1 => (0,1,0,0)
  | 2 => (0,0,1,0)
  | 3 => (0,0,0,1)
  | 4 => (-1,0,0,0)
  | 5 => (0,-1,0,0)
  | 6 => (0,0,-1,0)
  | _ => (0,0,0,-1)

-- Multiplication by zeta - zeta^3 (the algebraic sqrt(2)).
def scaleRoot2 (a : C8) : C8 :=
  (a.2.1-a.2.2.2, a.1+a.2.2.1, a.2.1+a.2.2.2, a.2.2.1-a.1)

def omegaQuarter (b : Bool) : Fin 8 := if b then 7 else 1
def omegaThreeQuarter (b : Bool) : Fin 8 := if b then 1 else 7
def halfSign (b : Bool) : Fin 8 := if b then 4 else 0

theorem omega_quarter_exact :
    ∀ q : Fin 8, ∀ b : Bool,
      plus (root8 q) (root8 (q+2+halfSign b)) =
        scaleRoot2 (root8 (q+omegaQuarter b)) := by decide

theorem omega_threequarter_exact :
    ∀ q : Fin 8, ∀ b : Bool,
      plus (root8 q) (root8 (q+6+halfSign b)) =
        scaleRoot2 (root8 (q+omegaThreeQuarter b)) := by decide

theorem root2_twice_exact :
    ∀ q : Fin 8, scaleRoot2 (scaleRoot2 (root8 q)) =
      plus (root8 q) (root8 q) := by decide

/-- Composition records exponent of sqrt(2), not count of steps.
    Substitution contributes 0, Elim/HH 2, omega 1.
    Abstract action laws isolate the complex embedding obligation. -/
inductive Chain {A : Type} (scale : Nat → A → A) :
    A → List Nat → A → Prop where
  | nil (a : A) : Chain scale a [] a
  | cons {a b c : A} {k : Nat} {ks : List Nat}
      (h : a = scale k b) (tail : Chain scale b ks c) :
      Chain scale a (k :: ks) c

theorem chain_scale {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (hadd : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    {a b : A} {ks : List Nat} (h : Chain scale a ks b) :
    a = scale ks.sum b := by
  induction h with
  | nil a => exact (h0 a).symm
  | cons h tail ih =>
      rw [h, ih, hadd]
      rfl

/-- Explicit guard partition uses a coherent sum, not an OR of
    branch verdicts. No branch independence assumption. -/
theorem guard_partition {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0+a = a) (zr : ∀ a : A, a+0 = a)
    (g : Bool) (a : A) : mask g a + mask (!g) a = a := by
  cases g <;> simp [mask, zl, zr]

#print axioms sum_congr
#print axioms unique_fiber
#print axioms substitution_sum
#print axioms alias_fiber
#print axioms scale_sum
#print axioms free_fiber
#print axioms free_sum
#print axioms hh_point
#print axioms hh_fiber
#print axioms omega_quarter_exact
#print axioms omega_threequarter_exact
#print axioms root2_twice_exact
#print axioms chain_scale
#print axioms guard_partition
end QuPRS.ConditionalTrace
