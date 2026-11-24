/-
Research-only compositional Hoare proof kernel.

The mass lemmas below use nonnegative NATURAL weights on finite lists.
They prove combinatorial partition and prefix facts, not a formalization
of complex Hilbert spaces, real cyclotomic embeddings or Rust/Python.
The routing theorem is conditional on EACH definite route being sound.
The assumptions must be discharged by independent refinement proofs.
No source parser, solver, or implementation certification is implied.
-/
import Std

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.HoareComposition

def mass {α : Type} (xs : List α) (g : α → Bool) (w : α → Nat) : Nat :=
  match xs with
  | [] => 0
  | x :: rest => (if g x then w x else 0) + mass rest g w

def allGood {α : Type} (bs : List (α → Bool)) (x : α) : Bool :=
  match bs with
  | [] => true
  | b :: rest => b x && allGood rest x

def partitionMass {α : Type} (xs : List α) (g : α → Bool)
    (w : α → Nat) (bs : List (α → Bool)) : Nat :=
  match bs with
  | [] => 0
  | b :: rest =>
      mass xs (fun x => g x && !(b x)) w +
      partitionMass xs (fun x => g x && b x) w rest

theorem mass_false {α : Type} (xs : List α) (w : α → Nat) :
    mass xs (fun _ => false) w = 0 := by
  induction xs with
  | nil => rfl
  | cons a xs ih => simp [mass, ih]

/-- Local disjointness identity. Split only independent Boolean variables,
    never applications of predicates that also occur in the tail. -/
private theorem first_failure_head (g b c : Bool) (w : Nat) :
    (if g && !(b && c) then w else 0) =
      (if g && !b then w else 0) +
      (if (g && b) && !c then w else 0) := by
  cases g <;> cases b <;> cases c <;> simp

theorem first_failure_step {α : Type} (xs : List α)
    (g b : α → Bool) (w : α → Nat) (bs : List (α → Bool)) :
    mass xs (fun x => g x && !(allGood (b :: bs) x)) w =
      mass xs (fun x => g x && !(b x)) w +
      mass xs (fun x => (g x && b x) && !(allGood bs x)) w := by
  induction xs with
  | nil => rfl
  | cons a xs ih =>
      -- Keep the recursive predicates opaque. Prove the head identity
      -- separately and combine it with the exact tail equality.
      have hh :
          (if g a && !(allGood (b :: bs) a) then w a else 0) =
            (if g a && !(b a) then w a else 0) +
            (if (g a && b a) && !(allGood bs a) then w a else 0) :=
        first_failure_head (g a) (b a) (allGood bs a) (w a)
      simp only [mass]
      rw [ih, hh]
      ac_rfl

/-- Earlier conjuncts must pass, so failure branches do not double count. -/
theorem first_failure_mass {α : Type} (xs : List α)
    (g : α → Bool) (w : α → Nat) (bs : List (α → Bool)) :
    partitionMass xs g w bs =
      mass xs (fun x => g x && !(allGood bs x)) w := by
  induction bs generalizing g with
  | nil =>
      simp [partitionMass, allGood, mass_false]
  | cons b bs ih =>
      simp only [partitionMass, ih]
      exact (first_failure_step xs g b w bs).symm

/-- The two restrictions of a Boolean prefix exactly partition its mass. -/
theorem prefix_split {α : Type} (xs : List α) (g b : α → Bool)
    (w : α → Nat) :
    mass xs g w =
      mass xs (fun x => g x && !(b x)) w +
      mass xs (fun x => g x && b x) w := by
  induction xs with
  | nil => rfl
  | cons a xs ih =>
      cases hg : g a <;> cases hb : b a <;>
        simp [mass, hg, hb] <;> omega

theorem positive_child {α : Type} (xs : List α) (g b : α → Bool)
    (w : α → Nat) (h : 0 < mass xs g w) :
    0 < mass xs (fun x => g x && !(b x)) w ∨
      0 < mass xs (fun x => g x && b x) w := by
  have hs := prefix_split xs g b w
  omega

theorem zero_mass_member {α : Type} (xs : List α) (g : α → Bool)
    (w : α → Nat) (h : mass xs g w = 0)
    (x : α) (hx : x ∈ xs) (hg : g x = true) : w x = 0 := by
  induction xs with
  | nil => simp at hx
  | cons a xs ih =>
      have ht : mass xs g w = 0 := by
        simp only [mass] at h
        omega
      have hh : (if g a then w a else 0) = 0 := by
        simp only [mass] at h
        omega
      rcases List.mem_cons.mp hx with he | he
      · subst x
        simpa [hg] using hh
      · exact ih ht he

inductive Verdict where
  | proved | refuted | unknown
deriving DecidableEq

def Sound (bad : Prop) : Verdict → Prop
  | .proved => ¬ bad
  | .refuted => bad
  | .unknown => True

def firstDefinite : List Verdict → Verdict
  | [] => .unknown
  | .unknown :: rest => firstDefinite rest
  | .proved :: _ => .proved
  | .refuted :: _ => .refuted

/-- Conditional composition theorem: unknown has no evidentiary force.
    This does not discharge any individual algorithm's soundness. -/
theorem dispatch_sound (bad : Prop) (vs : List Verdict)
    (h : ∀ v : Verdict, v ∈ vs → Sound bad v) :
    Sound bad (firstDefinite vs) := by
  induction vs with
  | nil => exact True.intro
  | cons v vs ih =>
      cases v with
      | unknown =>
          apply ih
          intro u hu
          exact h u (List.mem_cons_of_mem _ hu)
      | proved =>
          exact h .proved (by simp)
      | refuted =>
          exact h .refuted (by simp)

#print axioms mass_false
#print axioms first_failure_step
#print axioms first_failure_mass
#print axioms prefix_split
#print axioms positive_child
#print axioms zero_mass_member
#print axioms dispatch_sound


/-! Exact coefficient kernel for integer numerators in the negacyclic
    representation X^D = -1. It computes coefficients of A A* by
    distributing the signed, reduced differences j-k. This is NOT yet
    a theorem about the complex embedding, source parser or WMC encoder. -/

def sumBelow : Nat → (Nat → Int) → Int
  | 0, _ => 0
  | n+1, f => sumBelow n f + f n

theorem sumBelow_congr (n : Nat) (f g : Nat → Int)
    (h : ∀ i, i < n → f i = g i) :
    sumBelow n f = sumBelow n g := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [sumBelow]
      rw [ih (fun i hi => h i (by omega)), h n (by omega)]

theorem sumBelow_all_zero (n : Nat) (f : Nat → Int)
    (h : ∀ i, i < n → f i = 0) : sumBelow n f = 0 := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have ht := ih (fun i hi => h i (by omega))
      have hn := h n (by omega)
      simp [sumBelow, ht, hn]

theorem sumBelow_delta (n j : Nat) (v : Int) (hj : j < n) :
    sumBelow n (fun k => if j = k then v else 0) = v := by
  induction n with
  | zero => omega
  | succ n ih =>
      by_cases e : j = n
      · subst j
        have hz : sumBelow n (fun k => if n = k then v else 0) = 0 := by
          apply sumBelow_all_zero
          intro k hk
          have hne : n ≠ k := by omega
          simp [hne]
        simp [sumBelow, hz]
      · have ht := ih (by omega : j < n)
        simp [sumBelow, ht, e]

theorem sumBelow_nonneg (n : Nat) (f : Nat → Int)
    (h : ∀ i, i < n → 0 ≤ f i) : 0 ≤ sumBelow n f := by
  induction n with
  | zero =>
      change (0 : Int) ≤ 0
      exact Int.le_refl 0
  | succ n ih =>
      exact Int.add_nonneg (ih (fun i hi => h i (by omega))) (h n (by omega))

theorem sumBelow_zero_iff (n : Nat) (f : Nat → Int)
    (h : ∀ i, i < n → 0 ≤ f i) :
    sumBelow n f = 0 ↔ ∀ i, i < n → f i = 0 := by
  constructor
  · induction n with
    | zero =>
        intro _ i hi
        omega
    | succ n ih =>
        intro hz i hi
        have hs : ∀ k, k < n → 0 ≤ f k := fun k hk => h k (by omega)
        have hp := sumBelow_nonneg n f hs
        have hn := h n (by omega)
        have ht : sumBelow n f = 0 := by
          simp only [sumBelow] at hz
          omega
        have hl : f n = 0 := by
          simp only [sumBelow] at hz
          omega
        by_cases e : i = n
        · simpa only [e] using hl
        · exact ih hs ht i (by omega)
  · exact sumBelow_all_zero n f

/-- Reduced coefficient of X^(j-k) at basis exponent r. Valid for
    j,k < D: negative exponents wrap once with sign -1. -/
def negacyclicDiffTerm (D j k r : Nat) (u v : Int) : Int :=
  if k ≤ j then
    if j-k = r then u*v else 0
  else
    if D+j-k = r then -(u*v) else 0

theorem negacyclicDiffTerm_zero (D j k : Nat) (u v : Int)
    (_hj : j < D) (hk : k < D) :
    negacyclicDiffTerm D j k 0 u v =
      (if j = k then u*v else 0) := by
  by_cases h : k ≤ j
  · by_cases e : j = k
    · subst k
      simp [negacyclicDiffTerm]
    · have hn : j-k ≠ 0 := by omega
      simp [negacyclicDiffTerm, h, hn, e]
  · have hn : D+j-k ≠ 0 := by omega
    have e : j ≠ k := by omega
    simp [negacyclicDiffTerm, h, hn, e]

def normCoeff (D : Nat) (a : Nat → Int) (r : Nat) : Int :=
  sumBelow D (fun j =>
    sumBelow D (fun k => negacyclicDiffTerm D j k r (a j) (a k)))

theorem norm_constant (D : Nat) (a : Nat → Int) :
    normCoeff D a 0 = sumBelow D (fun j => a j * a j) := by
  unfold normCoeff
  apply sumBelow_congr
  intro j hj
  calc
    sumBelow D (fun k => negacyclicDiffTerm D j k 0 (a j) (a k)) =
        sumBelow D (fun k => if j = k then a j * a j else 0) := by
          apply sumBelow_congr
          intro k hk
          rw [negacyclicDiffTerm_zero D j k (a j) (a k) hj hk]
          by_cases e : j = k
          · subst k
            rfl
          · simp [e]
    _ = a j * a j := sumBelow_delta D j (a j * a j) hj

private theorem square_nonneg (v : Int) : 0 ≤ v * v := by
  by_cases h : 0 ≤ v
  · exact Int.mul_nonneg h h
  · have hn : v ≤ 0 := by omega
    exact Int.mul_nonneg_of_nonpos_of_nonpos hn hn

theorem norm_constant_nonneg (D : Nat) (a : Nat → Int) :
    0 ≤ normCoeff D a 0 := by
  rw [norm_constant]
  exact sumBelow_nonneg D _ (fun i _ => square_nonneg (a i))

theorem norm_constant_zero_iff (D : Nat) (a : Nat → Int) :
    normCoeff D a 0 = 0 ↔ ∀ j, j < D → a j = 0 := by
  rw [norm_constant, sumBelow_zero_iff D _ (fun i _ => square_nonneg (a i))]
  constructor
  · intro h j hj
    rcases Int.mul_eq_zero.mp (h j hj) with hz | hz
    · exact hz
    · exact hz
  · intro h j hj
    simp [h j hj]

def familyNormCoeff (n D : Nat) (a : Nat → Nat → Int) (r : Nat) : Int :=
  sumBelow n (fun i => normCoeff D (a i) r)

theorem family_norm_constant_zero_iff (n D : Nat) (a : Nat → Nat → Int) :
    familyNormCoeff n D a 0 = 0 ↔
      ∀ i, i < n → ∀ j, j < D → a i j = 0 := by
  unfold familyNormCoeff
  rw [sumBelow_zero_iff n _ (fun i _ => norm_constant_nonneg D (a i))]
  constructor
  · intro h i hi
    exact (norm_constant_zero_iff D (a i)).mp (h i hi)
  · intro h i hi
    exact (norm_constant_zero_iff D (a i)).mpr (h i hi)

#print axioms sumBelow_congr
#print axioms sumBelow_all_zero
#print axioms sumBelow_delta
#print axioms sumBelow_nonneg
#print axioms sumBelow_zero_iff
#print axioms negacyclicDiffTerm_zero
#print axioms norm_constant
#print axioms norm_constant_nonneg
#print axioms norm_constant_zero_iff
#print axioms family_norm_constant_zero_iff

end QuPRS.HoareComposition
