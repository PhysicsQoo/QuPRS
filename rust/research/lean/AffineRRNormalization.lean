/-
RR receipt convention from the native experiment: Elim and HH add 2;
Omega adds 1. Trace composition is conditional on local scalar
relations; this does not prove native RR or a physical norm identity.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineRRNormalization

inductive Rule where
  | elim | hh | omega
  deriving DecidableEq

def delta : Rule → Nat
  | .elim => 2
  | .hh => 2
  | .omega => 1

def scale2 : List Rule → Nat
  | [] => 0
  | r :: rs => delta r + scale2 rs

def count (r : Rule) : List Rule → Nat
  | [] => 0
  | x :: xs => (if x = r then 1 else 0) + count r xs

theorem scale2_counts (rs : List Rule) :
    scale2 rs = 2 * count .elim rs + 2 * count .hh rs + count .omega rs := by
  induction rs with
  | nil => rfl
  | cons r rs ih =>
      cases r <;> simp [scale2, delta, count] <;> omega

theorem scale2_append (rs ts : List Rule) :
    scale2 (rs ++ ts) = scale2 rs + scale2 ts := by
  induction rs with
  | nil => exact (Nat.zero_add (scale2 ts)).symm
  | cons r rs ih =>
      change delta r + scale2 (rs ++ ts) = (delta r + scale2 rs) + scale2 ts
      rw [ih, Nat.add_assoc]

def factor (s : Nat) : Int := 2 ^ s

theorem factor_add (s t : Nat) :
    factor (s+t) = factor s * factor t := by
  exact Int.pow_add 2 s t

theorem factor_nonzero (s : Nat) : factor s ≠ 0 := by
  induction s with
  | zero => decide
  | succ s ih =>
      change factor (s+1) ≠ 0
      rw [factor_add s 1]
      intro hz
      rcases Int.mul_eq_zero.mp hz with h | h
      · exact ih h
      · exact (show factor 1 ≠ 0 by decide) h

def validTrace : List Rule → Int → Int → Prop
  | [], a, b => a = b
  | r :: rs, a, b =>
      ∃ mid, a = factor (delta r) * mid ∧ validTrace rs mid b

theorem trace_scale (rs : List Rule) (a b : Int)
    (h : validTrace rs a b) :
    a = factor (scale2 rs) * b := by
  induction rs generalizing a with
  | nil =>
      have he : a = b := h
      rw [he]
      exact (Int.one_mul b).symm
  | cons r rs ih =>
      obtain ⟨mid, hm, ht⟩ := h
      have hx := ih mid ht
      change a = factor (delta r + scale2 rs) * b
      rw [hm, hx, factor_add, Int.mul_assoc]

theorem trace_zero_iff (rs : List Rule) (a b : Int)
    (h : validTrace rs a b) : a = 0 ↔ b = 0 := by
  rw [trace_scale rs a b h]
  constructor
  · intro hz
    exact (Int.mul_eq_zero.mp hz).resolve_left (factor_nonzero _)
  · intro hz
    rw [hz, Int.mul_zero]

/-- Local exact squared-coordinate identities for the three rules.
    Elim and HH double the retained coefficient; omega is modeled by
    multiplication by 1+i on a two-coordinate integer pair. -/
theorem double_square (a : Int) :
    (a+a)*(a+a) = factor (delta .elim) * (a*a) := by
  change (a+a)*(a+a) = 4*(a*a)
  simp only [Int.add_mul, Int.mul_add]
  omega

theorem hh_double_square (a : Int) :
    (a+a)*(a+a) = factor (delta .hh) * (a*a) :=
  double_square a

theorem omega_pair_square (a b : Int) :
    (a-b)*(a-b)+(a+b)*(a+b) = factor (delta .omega) * (a*a+b*b) := by
  change (a-b)*(a-b)+(a+b)*(a+b) = 2*(a*a+b*b)
  simp only [Int.sub_mul, Int.mul_sub, Int.add_mul, Int.mul_add]
  rw [Int.mul_comm b a]
  omega

#print axioms double_square
#print axioms hh_double_square
#print axioms omega_pair_square
#print axioms scale2_counts
#print axioms scale2_append
#print axioms factor_add
#print axioms factor_nonzero
#print axioms trace_scale
#print axioms trace_zero_iff
end QuPRS.AffineRRNormalization
