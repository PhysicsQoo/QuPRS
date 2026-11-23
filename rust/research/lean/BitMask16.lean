/-
QuPRS research: word-level 16-bit monomial masks.

This is a *specific* refinement boundary for the word interpretation
used by the scoped Rust ANF symbolic checker (BTreeSet<u16>).
No Mathlib, no custom axiom, no sorry, no Rust codegen proof.

The names intentionally specify least-significant-bit first.
The constant monomial has mask 0; multiplication of square-free
monomials uses word-level OR, not numeric addition.
-/
import Init.Data.BitVec.Lemmas

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

/-- LSB-first 16-bit monomial membership, matching Rust (1u16 << i). -/
def decodeMask16 (m : BitVec 16) : Fin 16 → Bool :=
  fun i => m.getLsbD i.val

/-- The complete 16-bit membership function is an injective
    representation of the underlying word (there are no hidden bits). -/
theorem decodeMask16_injective (a b : BitVec 16)
    (h : decodeMask16 a = decodeMask16 b) : a = b := by
  apply BitVec.eq_of_getLsbD_eq_iff.mpr
  intro i hi
  have hbit := congrArg
    (fun f : Fin 16 → Bool => f ⟨i,hi⟩) h
  exact hbit

/-- The constant monomial is the empty variable set, word zero. -/
theorem decodeMask16_constant_zero (i : Fin 16) :
    decodeMask16 (0#16) i = false := by
  simp [decodeMask16]

/-- The exact bit-level interpretation of Rust's monomial mask OR.
    The 16-bit OR is the union of variables, not parity addition. -/
theorem decodeMask16_or (a b : BitVec 16) (i : Fin 16) :
    decodeMask16 (a ||| b) i =
      (decodeMask16 a i || decodeMask16 b i) := by
  simp [decodeMask16]

theorem decodeMask16_and (a b : BitVec 16) (i : Fin 16) :
    decodeMask16 (a &&& b) i =
      (decodeMask16 a i && decodeMask16 b i) := by
  simp [decodeMask16]

theorem decodeMask16_xor (a b : BitVec 16) (i : Fin 16) :
    decodeMask16 (a ^^^ b) i =
      (decodeMask16 a i ^^ decodeMask16 b i) := by
  simp [decodeMask16]

/-- Word-precise squared-free monomial product. -/
def multiplyMonomials16 (a b : BitVec 16) : BitVec 16 :=
  a ||| b

theorem multiplyMonomials16_union (a b : BitVec 16) (i : Fin 16) :
    decodeMask16 (multiplyMonomials16 a b) i =
      (decodeMask16 a i || decodeMask16 b i) := by
  exact decodeMask16_or a b i

/-- x_i*x_i = x_i at the *word* level, for any 16-bit mask. -/
theorem multiplyMonomials16_squarefree (a : BitVec 16) :
    multiplyMonomials16 a a = a := by
  simp [multiplyMonomials16, BitVec.or_self]

/-- Every monomial's variables must be assigned true for its
    Boolean-ring product to be nonzero. -/
def evalMonomial16 (m : BitVec 16) (valuation : Fin 16 → Bool) : Prop :=
  ∀ i : Fin 16, decodeMask16 m i = true → valuation i = true

/-- Monomial-mask union has Boolean conjunction semantics.
    Unlike a finite fixture, this ranges over *all* 16-bit masks and
    all 2^16 Boolean valuations, without enumerating combinations. -/
theorem evalMonomial16_product_iff
    (a b : BitVec 16) (valuation : Fin 16 → Bool) :
    evalMonomial16 (multiplyMonomials16 a b) valuation ↔
      evalMonomial16 a valuation ∧
      evalMonomial16 b valuation := by
  constructor
  · intro h
    constructor
    · intro i ha
      apply h i
      rw [multiplyMonomials16_union]
      simp [ha]
    · intro i hb
      apply h i
      rw [multiplyMonomials16_union]
      simp [hb]
  · rintro ⟨ha,hb⟩ i h
    rw [multiplyMonomials16_union] at h
    cases h1 : decodeMask16 a i <;>
      cases h2 : decodeMask16 b i <;>
      simp_all
    all_goals first | exact ha i h1 | exact hb i h2

/-- Checked conversion from a Nat payload (as produced by a binary
    byte decoder) into an exactly representable 16-bit word.
    A value >= 65536 must be rejected, not silently reduced mod 2^16. -/
def checkedMask16 (n : Nat) : Option (BitVec 16) :=
  if n < 65536 then some (BitVec.ofNat 16 n) else none

theorem checkedMask16_reject_overflow
    (n : Nat) (h : 65536 ≤ n) : checkedMask16 n = none := by
  simp [checkedMask16, Nat.not_lt.mpr h]

theorem checkedMask16_accept_bounded
    (n : Nat) (h : n < 65536) :
    checkedMask16 n = some (BitVec.ofNat 16 n) := by
  simp [checkedMask16, h]

theorem checkedMask16_no_truncation
    (n : Nat) (h : n < 65536) :
    (checkedMask16 n).map BitVec.toNat = some n := by
  simp [checkedMask16, h, BitVec.toNat_ofNat, Nat.mod_eq_of_lt h]

/-- Explicit endianness controls: bit 0 and bit 15 correspond to
    the least and most significant Rust u16 mask positions. -/
theorem decodeMask16_highest_bit :
    decodeMask16 (32768#16) ⟨15,by decide⟩ = true := by
  decide

theorem decodeMask16_highest_bit_not_lowest :
    decodeMask16 (32768#16) ⟨0,by decide⟩ = false := by
  decide

theorem decodeMask16_lowest_bit :
    decodeMask16 (1#16) ⟨0,by decide⟩ = true := by
  decide

#print axioms decodeMask16_injective
#print axioms decodeMask16_constant_zero
#print axioms decodeMask16_or
#print axioms decodeMask16_and
#print axioms decodeMask16_xor
#print axioms multiplyMonomials16_union
#print axioms multiplyMonomials16_squarefree
#print axioms evalMonomial16_product_iff
#print axioms checkedMask16_reject_overflow
#print axioms checkedMask16_accept_bounded
#print axioms checkedMask16_no_truncation
#print axioms decodeMask16_highest_bit
#print axioms decodeMask16_highest_bit_not_lowest
#print axioms decodeMask16_lowest_bit

end QuPRS.P0
