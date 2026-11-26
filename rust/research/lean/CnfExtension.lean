/-
Tseitin semantic kernel. Local Boolean truth relations and arbitrary
finite ordered definitions. No claim about DIMACS parsing, source
allocation, Rust extraction, or real/complex numerical rounding.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.CnfExtension

def andClauses (a b z : Bool) : Bool :=
  (!z || a) && (!z || b) && (z || !a || !b)

def xorClauses (a b z : Bool) : Bool :=
  (!a || !b || !z) && (a || b || !z) &&
  (a || !b || z) && (!a || b || z)

def eqClauses (a b : Bool) : Bool :=
  (!a || b) && (a || !b)

theorem and_gate : ∀ a b z : Bool, andClauses a b z = true ↔ z = (a && b) := by decide
theorem xor_gate : ∀ a b z : Bool, xorClauses a b z = true ↔ z = (a.xor b) := by decide
theorem equality_gate : ∀ a b : Bool, eqClauses a b = true ↔ a = b := by decide
theorem false_gate : ∀ z : Bool, (!z) = true ↔ z = false := by decide
theorem true_gate : ∀ z : Bool, z = true ↔ z = true := by decide

-- Each definition may read the original live assignment and all
-- earlier outputs, but cannot read later outputs. The runtime graph
-- checker is responsible for establishing this premise.
abbrev Def := List Bool → Bool

def extendDefs : List Def → List Bool → List Bool
  | [], _ => []
  | f :: fs, env => f env :: extendDefs fs (f env :: env)

def checkDefs : List Def → List Bool → List Bool → Bool
  | [], _, [] => true
  | [], _, _ :: _ => false
  | _ :: _, _, [] => false
  | f :: fs, env, y :: ys =>
    if y = f env then checkDefs fs (y :: env) ys else false

theorem defs_iff (fs : List Def) (env ys : List Bool) :
    checkDefs fs env ys = true ↔ ys = extendDefs fs env := by
  induction fs generalizing env ys with
  | nil => cases ys <;> simp [checkDefs, extendDefs]
  | cons f fs ih =>
    cases ys with
    | nil => simp [checkDefs, extendDefs]
    | cons y ys =>
      by_cases h : y = f env
      · subst y
        simp [checkDefs, extendDefs, ih]
      · simp [checkDefs, extendDefs, h]

theorem defs_exists (fs : List Def) (env : List Bool) :
    checkDefs fs env (extendDefs fs env) = true :=
  (defs_iff fs env _).2 rfl

theorem defs_unique (fs : List Def) (env a b : List Bool)
    (ha : checkDefs fs env a = true) (hb : checkDefs fs env b = true) :
    a = b :=
  ((defs_iff fs env a).1 ha).trans ((defs_iff fs env b).1 hb).symm

def mask {A : Type} [Zero A] (b : Bool) (a : A) : A :=
  if b then a else 0

-- Sum over the Boolean tree of all auxiliary assignments; mask
-- invalid branches at each local definition, then apply diagonal guard.
def weightedFiber {A : Type} [Zero A] [Add A]
    (guard : List Bool → Bool) (weight : List Bool → A) :
    List Def → List Bool → A
  | [], env => mask (guard env) (weight env)
  | f :: fs, env =>
    mask (!(false.xor (f env))) (weightedFiber guard weight fs (false :: env)) +
    mask (!(true.xor (f env))) (weightedFiber guard weight fs (true :: env))

def finalEnv : List Def → List Bool → List Bool
  | [], env => env
  | f :: fs, env => finalEnv fs (f env :: env)

theorem weighted_fiber {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (guard : List Bool → Bool) (weight : List Bool → A)
    (fs : List Def) (env : List Bool) :
    weightedFiber guard weight fs env =
      mask (guard (finalEnv fs env)) (weight (finalEnv fs env)) := by
  induction fs generalizing env with
  | nil => rfl
  | cons f fs ih =>
    cases h : f env <;> simp [weightedFiber, finalEnv, h, mask, zl, zr, ih]

theorem unweighted_fiber (guard : List Bool → Bool)
    (fs : List Def) (env : List Bool) :
    weightedFiber (A := Nat) guard (fun _ => 1) fs env =
      if guard (finalEnv fs env) then 1 else 0 := by
  exact weighted_fiber Nat.zero_add Nat.add_zero guard (fun _ => 1) fs env

#print axioms and_gate
#print axioms xor_gate
#print axioms equality_gate
#print axioms false_gate
#print axioms true_gate
#print axioms defs_iff
#print axioms defs_exists
#print axioms defs_unique
#print axioms weighted_fiber
#print axioms unweighted_fiber
end QuPRS.CnfExtension
