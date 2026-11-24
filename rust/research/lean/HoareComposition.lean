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

theorem first_failure_step {α : Type} (xs : List α)
    (g b : α → Bool) (w : α → Nat) (bs : List (α → Bool)) :
    mass xs (fun x => g x && !(allGood (b :: bs) x)) w =
      mass xs (fun x => g x && !(b x)) w +
      mass xs (fun x => (g x && b x) && !(allGood bs x)) w := by
  induction xs with
  | nil => rfl
  | cons a xs ih =>
      simp only [allGood] at ih
      cases hg : g a <;> cases hb : b a <;>
        cases hc : allGood bs a <;>
        simp [mass, allGood, hg, hb, hc] <;> omega

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

end QuPRS.HoareComposition
