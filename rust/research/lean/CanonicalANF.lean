/-
QuPRS P0 research: canonical multilinear GF(2) ANF.

The indexed coefficient tree is the square-free polynomial representation:
  a(x_rest) XOR (x_head AND b(x_rest)).
There is one Boolean coefficient per subset/monomial mask, and
evaluation is exactly the multilinear ANF semantics.

This file proves representation/existence and semantic uniqueness for
*arbitrary* numbers of Boolean variables, independently of the Rust
BTreeSet<u16> producer. Concrete bitmask packing/refinement is NOT
yet mechanized. No sorry, no custom axioms, no Mathlib.
-/
import Init

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

def BoolVector : Nat → Type
  | 0 => PUnit
  | n + 1 => Bool × BoolVector n

inductive CanonicalANF : Nat → Type where
  | scalar : Bool → CanonicalANF 0
  | split {n : Nat} : CanonicalANF n → CanonicalANF n →
      CanonicalANF (n + 1)

/-- The coefficient tree is a square-free polynomial:
    A(x, xs) = A0(xs) XOR (x AND A1(xs)). -/
def evalANF : (n : Nat) → CanonicalANF n → BoolVector n → Bool
  | 0, .scalar c, _ => c
  | n + 1, .split a b, (x, xs) =>
      (evalANF n a xs).xor (x && evalANF n b xs)

private theorem bool_xor_cancel_left (a b c : Bool)
    (h : a.xor b = a.xor c) : b = c := by
  cases a <;> cases b <;> cases c <;> simp_all

/-- Semantic injectivity: two distinct coefficient trees never represent
    the same Boolean function. The proof is an induction on variable
    count, using evaluation at the head variable false/true. -/
theorem canonical_anf_unique :
    ∀ (n : Nat) (a b : CanonicalANF n),
      (∀ v : BoolVector n, evalANF n a v = evalANF n b v) →
      a = b := by
  intro n
  induction n with
  | zero =>
      intro a b h
      cases a with
      | scalar ca =>
        cases b with
        | scalar cb =>
          have hv := h PUnit.unit
          cases ca <;> cases cb <;> simp_all [evalANF]
  | succ n ih =>
      intro a b h
      cases a with
      | split a0 a1 =>
        cases b with
        | split b0 b1 =>
          have hlo : a0 = b0 := ih a0 b0 (by
            intro xs
            have hv := h (false, xs)
            simpa [evalANF] using hv)
          have hhi : a1 = b1 := ih a1 b1 (by
            intro xs
            have hv := h (true, xs)
            change (evalANF n a0 xs).xor (evalANF n a1 xs) =
              (evalANF n b0 xs).xor (evalANF n b1 xs) at hv
            rw [hlo] at hv
            exact bool_xor_cancel_left _ _ _ hv)
          cases hlo
          cases hhi
          rfl

/-- Every Boolean function has a multilinear ANF coefficient tree.
    The second coefficient half is the difference between restrictions
    at x_head=false and x_head=true, over GF(2). -/
theorem canonical_anf_exists :
    ∀ (n : Nat) (f : BoolVector n → Bool),
      ∃ a : CanonicalANF n,
        ∀ v : BoolVector n, evalANF n a v = f v := by
  intro n
  induction n with
  | zero =>
      intro f
      refine ⟨CanonicalANF.scalar (f PUnit.unit), ?_⟩
      intro v
      cases v
      rfl
  | succ n ih =>
      intro f
      let f0 : BoolVector n → Bool := fun xs => f (false, xs)
      let fd : BoolVector n → Bool :=
        fun xs => (f (false, xs)).xor (f (true, xs))
      obtain ⟨a, ha⟩ := ih f0
      obtain ⟨b, hb⟩ := ih fd
      refine ⟨CanonicalANF.split a b, ?_⟩
      intro v
      rcases v with ⟨head, tail⟩
      cases head with
      | false =>
          simpa [evalANF, f0] using ha tail
      | true =>
          change (evalANF n a tail).xor (evalANF n b tail) =
            f (true, tail)
          rw [ha tail, hb tail]
          dsimp [f0, fd]
          cases h0 : f (false, tail) <;>
            cases h1 : f (true, tail) <;>
            simp

/-- Coefficient extraction indexed by the Boolean monomial mask.
    A split has the coefficients for masks lacking the first variable
    on the left, and masks containing it on the right. -/
def coefficient : (n : Nat) → CanonicalANF n →
    BoolVector n → Bool
  | 0, .scalar b, _ => b
  | n + 1, .split a b, (mask, rest) =>
      if mask then coefficient n b rest else coefficient n a rest

/-- Evaluate an arbitrary set of Boolean monomial coefficients by
    the same Shannon/Möbius decomposition. -/
def evalCoefficients : (n : Nat) →
    (BoolVector n → Bool) → BoolVector n → Bool
  | 0, c, _ => c PUnit.unit
  | n + 1, c, (x, xs) =>
      (evalCoefficients n (fun mask => c (false, mask)) xs).xor
        (x && evalCoefficients n (fun mask => c (true, mask)) xs)

/-- The canonical ANF tree and coefficient-by-mask interpretation
    denote the same Boolean function at every assignment. -/
theorem coefficient_eval_correct :
    ∀ (n : Nat) (a : CanonicalANF n) (v : BoolVector n),
      evalCoefficients n (coefficient n a) v = evalANF n a v := by
  intro n
  induction n with
  | zero =>
      intro a v
      cases a
      cases v
      rfl
  | succ n ih =>
      intro a v
      cases a with
      | split a0 a1 =>
        rcases v with ⟨x, xs⟩
        change (evalCoefficients n (coefficient n a0) xs).xor
          (x && evalCoefficients n (coefficient n a1) xs) =
          (evalANF n a0 xs).xor (x && evalANF n a1 xs)
        rw [ih a0 xs, ih a1 xs]

/-- A mask-indexed coefficient function determines the polynomial
    uniquely: no two different canonical coefficient trees can have
    identical denotations. -/
theorem canonical_anf_coefficient_semantics_unique
    (n : Nat) (a b : CanonicalANF n)
    (h : ∀ v : BoolVector n,
      evalCoefficients n (coefficient n a) v =
      evalCoefficients n (coefficient n b) v) :
    a = b := by
  apply canonical_anf_unique n a b
  intro v
  rw [← coefficient_eval_correct n a v,
      ← coefficient_eval_correct n b v]
  exact h v

/-- Construct the canonical square-free ANF coefficient tree from an
    arbitrary monomial-mask indexed Boolean coefficient function. -/
def fromCoefficients : (n : Nat) →
    (BoolVector n → Bool) → CanonicalANF n
  | 0, c => .scalar (c PUnit.unit)
  | n + 1, c =>
      .split
        (fromCoefficients n (fun mask => c (false, mask)))
        (fromCoefficients n (fun mask => c (true, mask)))

/-- The mask-indexed encoding is lossless for all variable counts:
    selecting any coefficient after construction yields the original. -/
theorem coefficient_roundtrip :
    ∀ (n : Nat) (c : BoolVector n → Bool) (mask : BoolVector n),
      coefficient n (fromCoefficients n c) mask = c mask := by
  intro n
  induction n with
  | zero =>
      intro c mask
      cases mask
      rfl
  | succ n ih =>
      intro c mask
      rcases mask with ⟨head, tail⟩
      cases head with
      | false =>
          exact ih (fun rest => c (false, rest)) tail
      | true =>
          exact ih (fun rest => c (true, rest)) tail

/-- Strong form of canonical ANF uniqueness: two arbitrary coefficient
    functions over the complete set of n-variable Boolean monomial masks
    are extensionally equal if their GF(2) multilinear evaluations
    agree for all valuations. This is not limited to pre-built trees. -/
theorem masked_coefficients_unique
    (n : Nat) (c d : BoolVector n → Bool)
    (h : ∀ v : BoolVector n,
      evalCoefficients n c v = evalCoefficients n d v) :
    ∀ mask : BoolVector n, c mask = d mask := by
  let ac := fromCoefficients n c
  let ad := fromCoefficients n d
  have hc : coefficient n ac = c := by
    funext mask
    exact coefficient_roundtrip n c mask
  have hd : coefficient n ad = d := by
    funext mask
    exact coefficient_roundtrip n d mask
  have semantic : ∀ v : BoolVector n,
      evalANF n ac v = evalANF n ad v := by
    intro v
    rw [← coefficient_eval_correct n ac v,
        ← coefficient_eval_correct n ad v, hc, hd]
    exact h v
  have equalTrees := canonical_anf_unique n ac ad semantic
  intro mask
  have heq := congrArg (fun t => coefficient n t mask) equalTrees
  simpa [hc, hd] using heq

#print axioms coefficient_roundtrip
#print axioms masked_coefficients_unique

#print axioms canonical_anf_unique
#print axioms canonical_anf_exists
#print axioms coefficient_eval_correct
#print axioms canonical_anf_coefficient_semantics_unique

end QuPRS.P0
