/-
Native Path-sum semantic obligations for diagonal Boolean pre/post.
This is a pointwise semantic view of P, f and path variables, NOT a
coefficient-vector IR. A is the amplitude carrier; analytic phase laws
and normalization remain explicit obligations. No source refinement,
matrix semantics, or approximate matching certification is asserted.
-/
import Std

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.NativeGuardedPathSum

def mask {A : Type} [Zero A] (g : Bool) (a : A) : A :=
  if g then a else 0

def guard {X Z Y : Type} (pre : X → Bool) (post : Z → Bool)
    (out : X → Y → Z) (x : X) (y : Y) : Bool :=
  pre x && !(post (out x y))

def entry {A Z : Type} [Zero A] [DecidableEq Z]
    (g : Bool) (out z : Z) (a : A) : A :=
  mask (g && decide (out = z)) a

theorem guard_output_congr {X Z Y : Type} (pre : X → Bool)
    (post : Z → Bool) (out : X → Y → Z) (x : X) (y y' : Y)
    (h : out x y = out x y') :
    guard pre post out x y = guard pre post out x y' := by
  unfold guard
  rw [h]

theorem projection_entry {A X Z Y : Type} [Zero A] [DecidableEq Z]
    (pre : X → Bool) (post : Z → Bool) (out : X → Y → Z)
    (x : X) (y : Y) (z : Z) (a : A) :
    entry (guard pre post out x y) (out x y) z a =
      mask (pre x && !(post z)) (entry true (out x y) z a) := by
  by_cases h : out x y = z
  · simp [entry, guard, mask, h]
  · simp [entry, mask, h]

theorem mask_add {A : Type} [Zero A] [Add A]
    (h00 : (0 : A) + 0 = 0) (g : Bool) (a b : A) :
    mask g a + mask g b = mask g (a + b) := by
  cases g with
  | false => exact h00
  | true => rfl

/-- Elim: a pair with identical phase, output and guard. The amplitude
    sum a+a is deliberately not silently absorbed into normalization. -/
theorem elim_entry {A Z : Type} [Zero A] [Add A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (g : Bool) (out z : Z) (a : A) :
    entry g out z a + entry g out z a = entry g out z (a+a) :=
  mask_add h00 (g && decide (out = z)) a a

theorem cancel_entry {A Z : Type} [Zero A] [Add A] [Neg A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (hneg : ∀ a : A, a + -a = 0)
    (g : Bool) (out z : Z) (a : A) :
    entry g out z a + entry g out z (-a) = 0 := by
  unfold entry
  rw [mask_add h00, hneg]
  cases (g && decide (out = z)) <;> rfl

/-- HH: the first summed bit has phase sign (-1)^(t xor q).
    The second bit t remains visible to BOTH output and guard.
    No independence of the guard from t is required. -/
def hhBranch {A Z : Type} [Zero A] [Add A] [Neg A] [DecidableEq Z]
    (g : Bool → Bool) (out : Bool → Z) (a : Bool → A)
    (q t : Bool) (z : Z) : A :=
  entry (g t) (out t) z (a t) +
    entry (g t) (out t) z (if t = q then a t else -(a t))

theorem hh_branch {A Z : Type} [Zero A] [Add A] [Neg A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (hneg : ∀ a : A, a + -a = 0)
    (g : Bool → Bool) (out : Bool → Z) (a : Bool → A)
    (q t : Bool) (z : Z) :
    hhBranch g out a q t z =
      if t = q then entry (g t) (out t) z (a t+a t) else 0 := by
  by_cases h : t = q
  · simp only [hhBranch, ite_eq_left h]
    exact elim_entry h00 (g t) (out t) z (a t)
  · simp only [hhBranch, ite_eq_right h]
    exact cancel_entry h00 hneg (g t) (out t) z (a t)

theorem hh_substitute {A Z : Type} [Zero A] [Add A] [Neg A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (hneg : ∀ a : A, a + -a = 0)
    (hzl : ∀ a : A, 0+a = a) (hzr : ∀ a : A, a+0 = a)
    (g : Bool → Bool) (out : Bool → Z) (a : Bool → A)
    (q : Bool) (z : Z) :
    hhBranch g out a q false z + hhBranch g out a q true z =
      entry (g q) (out q) z (a q+a q) := by
  rw [hh_branch h00 hneg, hh_branch h00 hneg]
  cases q with
  | false => exact hzr _
  | true => exact hzl _

/-- Omega's analytic identity is a premise, not a theorem of this file:
    a+b=c includes the sqrt(2) scaling. Guard/output are preserved. -/
theorem omega_lift {A Z : Type} [Zero A] [Add A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (g : Bool) (out z : Z) (a b c : A)
    (hphase : a+b = c) :
    entry g out z a + entry g out z b = entry g out z c := by
  unfold entry
  rw [mask_add h00, hphase]

def sumPaths {Y A : Type} [Zero A] [Add A]
    (ys : List Y) (term : Y → A) : A :=
  match ys with
  | [] => 0
  | y :: rest => term y + sumPaths rest term

theorem sum_paths_congr {Y A : Type} [Zero A] [Add A]
    (ys : List Y) (a b : Y → A) (h : ∀ y, a y = b y) :
    sumPaths ys a = sumPaths ys b := by
  induction ys with
  | nil => rfl
  | cons y ys ih => simp only [sumPaths, h y, ih]

theorem sum_paths_mask {Y A : Type} [Zero A] [Add A]
    (h00 : (0 : A) + 0 = 0) (ys : List Y) (g : Bool) (a : Y → A) :
    sumPaths ys (fun y => mask g (a y)) = mask g (sumPaths ys a) := by
  induction ys with
  | nil => cases g <;> rfl
  | cons y ys ih =>
      simp only [sumPaths, ih]
      exact mask_add h00 g (a y) (sumPaths ys a)

/-- Moving the diagonal property projection through the native path sum.
    The finite list is the existing path assignment domain. Completeness,
    uniqueness and the physical normalization are separate obligations. -/
theorem projection_sum {A X Z Y : Type} [Zero A] [Add A] [DecidableEq Z]
    (h00 : (0 : A) + 0 = 0) (ys : List Y)
    (pre : X → Bool) (post : Z → Bool) (out : X → Y → Z)
    (amp : X → Y → A) (x : X) (z : Z) :
    sumPaths ys (fun y => entry (guard pre post out x y) (out x y) z (amp x y)) =
      mask (pre x && !(post z)) (sumPaths ys (fun y => entry true (out x y) z (amp x y))) := by
  calc
    _ = sumPaths ys (fun y => mask (pre x && !(post z))
          (entry true (out x y) z (amp x y))) := by
            apply sum_paths_congr
            intro y
            exact projection_entry pre post out x y z (amp x y)
    _ = _ := sum_paths_mask h00 ys _ _

theorem paired_paths_cancel {Y A : Type} [Zero A] [Add A]
    (h00 : (0 : A) + 0 = 0) (ys : List Y) (a b : Y → A)
    (h : ∀ y, a y + b y = 0) :
    sumPaths ys (fun y => a y + b y) = 0 := by
  induction ys with
  | nil => rfl
  | cons y ys ih =>
      simp only [sumPaths, h y, ih]
      exact h00


/-- Local guarded RR scale factors compose, assuming the action of
    sqrt(2)^k on the amplitude carrier obeys the stated laws.
    This does not establish analytic phase laws or native refinement. -/
inductive ScaleChain {A : Type} (scale : Nat → A → A) :
    A → List Nat → A → Prop where
  | nil (a : A) : ScaleChain scale a [] a
  | cons {a b c : A} {k : Nat} {ks : List Nat}
      (step : a = scale k b) (tail : ScaleChain scale b ks c) :
      ScaleChain scale a (k :: ks) c

theorem scale_chain_sound {A : Type} (scale : Nat → A → A)
    (hzero : ∀ a, scale 0 a = a)
    (hadd : ∀ k l a, scale k (scale l a) = scale (k+l) a)
    {a b : A} {ks : List Nat} (h : ScaleChain scale a ks b) :
    a = scale ks.sum b := by
  induction h with
  | nil a => exact (hzero a).symm
  | cons step tail ih =>
    calc
      _ = scale _ _ := step
      _ = scale _ (scale _ _) := congrArg (scale _) ih
      _ = _ := hadd _ _ _


/-- A phase rewrite certified only on active paths is sufficient for the
    projected entries, provided output and guard do not change. The
    analytic implication from phase congruence to amplitude equality
    and the SAT encoding/refinement are separate obligations. -/
theorem active_phase_entry {A Z : Type} [Zero A] [DecidableEq Z]
    (g : Bool) (out z : Z) (a b : A)
    (h : g = true → a = b) :
    entry g out z a = entry g out z b := by
  by_cases hg : g = true
  · rw [h hg]
  · cases g with
    | false => rfl
    | true => exact False.elim (hg rfl)

theorem active_phase_sum {A Y Z : Type} [Zero A] [Add A] [DecidableEq Z]
    (ys : List Y) (g : Y → Bool) (out : Y → Z) (z : Z)
    (a b : Y → A) (h : ∀ y, g y = true → a y = b y) :
    sumPaths ys (fun y => entry (g y) (out y) z (a y)) =
      sumPaths ys (fun y => entry (g y) (out y) z (b y)) := by
  apply sum_paths_congr
  intro y
  exact active_phase_entry (g y) (out y) z (a y) (b y) (h y)

#print axioms active_phase_entry
#print axioms active_phase_sum
#print axioms scale_chain_sound
#print axioms guard_output_congr
#print axioms projection_entry
#print axioms mask_add
#print axioms elim_entry
#print axioms cancel_entry
#print axioms hh_branch
#print axioms hh_substitute
#print axioms omega_lift
#print axioms sum_paths_congr
#print axioms sum_paths_mask
#print axioms projection_sum
#print axioms paired_paths_cancel

end QuPRS.NativeGuardedPathSum
