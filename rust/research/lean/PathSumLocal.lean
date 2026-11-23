/-
QuPRS P0 research: kernel-checked local algebraic obligations.

No Mathlib, no sorry, no axiom declarations, no native_decide.
Lean 4 toolchain pinned in this directory.

Important trust boundary:
  * These are universally quantified/local semantic theorems about Bool
    and Fin 8, including a CNF correctness lemma for each gate.
  * Fin 8 proofs are kernel-checked finite case analyses. They do not
    mechanically prove the Rust implementation or arbitrary OpenQASM.
  * Source parser, ANF normalization algorithm, source-to-S8C1 compiler,
    verified-count recursion, and end-to-end F8G1 still need refinement.
-/
import Init

set_option autoImplicit false

namespace QuPRS.P0

def asNat (b : Bool) : Nat := if b then 1 else 0

def bit (v : Fin 8) (place : Nat) : Bool :=
  decide ((v.val / 2 ^ place) % 2 = 1)

def pack3 (b0 b1 b2 : Bool) : Fin 8 :=
  ⟨(asNat b0 + 2 * asNat b1 + 4 * asNat b2) % 8,
    Nat.mod_lt _ (by decide)⟩

def carryBit (a b incoming : Bool) : Bool :=
  (a && b) || ((a.xor b) && incoming)

/-- Matches the three-bit GF(2) ripple carry used by the symbolic checker. -/
def ripple8 (a b : Fin 8) : Fin 8 := Id.run do
  let a0 := bit a 0
  let a1 := bit a 1
  let a2 := bit a 2
  let b0 := bit b 0
  let b1 := bit b 1
  let b2 := bit b 2
  let s0 := a0.xor b0
  let c1 := a0 && b0
  let s1 := (a1.xor b1).xor c1
  let c2 := carryBit a1 b1 c1
  let s2 := (a2.xor b2).xor c2
  return pack3 s0 s1 s2

/-- Complement all three bits, then add one with the independently
    verified ripple adder, as in the Rust symbolic verifier. -/
def negate8 (a : Fin 8) : Fin 8 :=
  ripple8 (pack3 (!(bit a 0)) (!(bit a 1)) (!(bit a 2))) 1

/-- Every one of 64 input pairs satisfies the modular-addition law.
    The proof is checked by kernel reduction, not an external solver. -/
theorem ripple8_correct : ∀ a b : Fin 8, ripple8 a b = a + b := by
  decide

theorem negate8_correct : ∀ a : Fin 8, negate8 a = -a := by
  decide

theorem phase_difference_correct :
    ∀ a b : Fin 8, ripple8 b (negate8 a) = b - a := by
  decide

/-- Hadamard introduces a fresh Boolean branch y and phase
    ζ₈^(4 * old * y); no assumption is made about the old state. -/
def hPhase (old fresh : Bool) : Fin 8 :=
  pack3 false false (old && fresh)

theorem hPhase_correct (old fresh : Bool) :
    hPhase old fresh =
      (if old && fresh then (4 : Fin 8) else (0 : Fin 8)) := by
  cases old <;> cases fresh <;> decide

/-- Source-to-symbolic Hadamard phase update is correct pointwise for
    arbitrary assignments and arbitrary prior phase, not just fixtures. -/
theorem hStep_correct {α : Type} (old fresh : α → Bool)
    (prior : α → Fin 8) (x : α) :
    (fresh x, ripple8 (prior x) (hPhase (old x) (fresh x))) =
    (fresh x, prior x +
      (if old x && fresh x then (4 : Fin 8) else (0 : Fin 8))) := by
  rw [ripple8_correct, hPhase_correct]

/-- Boolean XOR interpreted as a Z8-valued phase polynomial:
    x ⊕ y = x + y - 2*x*y (mod 8). 6 is -2 mod 8. -/
theorem xor_phase_lift (x y : Bool) :
    (asNat (x.xor y)) % 8 =
    (asNat x + asNat y + 6 * asNat (x && y)) % 8 := by
  cases x <;> cases y <;> decide

theorem boolean_ring_and_idempotent (x : Bool) : (x && x) = x := by
  cases x <;> decide

theorem boolean_ring_xor_cancel (x : Bool) : x.xor x = false := by
  cases x <;> decide

theorem boolean_ring_or (x y : Bool) :
    (x || y) = (x.xor y).xor (x && y) := by
  cases x <;> cases y <;> decide

/-- Six exact S8C1 local Boolean operations.
    These are the only gate tags admitted by the restricted DAG. -/
inductive BoolOp where
  | zero | one | notG | andG | orG | xorG
deriving DecidableEq, Repr

def gateValue : BoolOp → Bool → Bool → Bool
  | .zero, _, _ => false
  | .one,  _, _ => true
  | .notG, a, _ => !a
  | .andG, a, b => a && b
  | .orG,  a, b => a || b
  | .xorG, a, b => a.xor b

/-- These clauses mirror the exact S8C1 gate_clauses encoding.
    Note especially all four XOR clauses; one-way implication is
    insufficient for uniquely extending the primary assignment. -/
def gateCNF : BoolOp → Bool → Bool → Bool → Bool
  | .zero, _, _, z => !z
  | .one,  _, _, z => z
  | .notG, a, _, z => ((!z || !a) && (z || a))
  | .andG, a, b, z =>
      ((!z || a) && (!z || b) && (z || !a || !b))
  | .orG, a, b, z =>
      ((z || !a) && (z || !b) && (!z || a || b))
  | .xorG, a, b, z =>
      ((!a || !b || !z) &&
       (a || b || !z) &&
       (a || !b || z) &&
       (!a || b || z))

/-- Exact CNF ⇔ definitional gate equality for *all* gate and bit
    assignments. No auxiliary-extension overcount is possible locally. -/
theorem gate_cnf_iff (op : BoolOp) (a b z : Bool) :
    gateCNF op a b z = true ↔ z = gateValue op a b := by
  cases op <;> cases a <;> cases b <;> cases z <;> decide

/-- Every admitted S8C1 gate has exactly one satisfying auxiliary output.
    Induction over an ordered, earlier-inputs-only DAG is the next lemma. -/
theorem gate_unique_extension (op : BoolOp) (a b : Bool) :
    ∃ z : Bool, gateCNF op a b z = true ∧
      ∀ w : Bool, gateCNF op a b w = true → w = z := by
  refine ⟨gateValue op a b, ?_, ?_⟩
  · exact (gate_cnf_iff op a b (gateValue op a b)).2 rfl
  · intro z hz
    exact (gate_cnf_iff op a b z).1 hz

end QuPRS.P0
