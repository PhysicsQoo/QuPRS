/-
Portable Boolean certificate replay for actual Rust DIMACS exports.
This is an executable checker, not yet a proved parser/refinement.
No numerical weight, source ANF, or external solver certification.
-/
import Std
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.CnfReplay

def andValue : List Bool → Bool
  | [] => true
  | x :: xs => x && andValue xs

def andForward : List Bool → Bool → Bool
  | [], _ => true
  | x :: xs, z => (!z || x) && andForward xs z

def andNClauses (xs : List Bool) (z : Bool) : Bool :=
  andForward xs z && (z || !andValue xs)

theorem and_forward (xs : List Bool) (z : Bool) :
    andForward xs z = (!z || andValue xs) := by
  induction xs with
  | nil => cases z <;> rfl
  | cons x xs ih =>
    cases z <;> cases x <;> simp [andForward, andValue, ih]

theorem and_nary (xs : List Bool) (z : Bool) :
    andNClauses xs z = true ↔ z = andValue xs := by
  unfold andNClauses
  rw [and_forward]
  cases z <;> cases h : andValue xs <;> simp [h]

inductive Record where
  | live (source id : Nat)
  | zero (out : Nat)
  | andGate (out : Nat) (inputs : List Nat)
  | xorGate (out a b : Nat)
  | eqGate (a b : Nat)
  | phase (out : Nat) (source : List Nat)
deriving Repr

def tokens (s : String) : List String :=
  (s.splitOn " ").filter (fun t => !t.isEmpty)

def rows (s : String) : List (List String) :=
  ((s.splitOn "\n").map tokens).filter (fun t => !t.isEmpty)

def parseRecord : List String → Option Record
  | ["live", a, b] => do return .live (← a.toNat?) (← b.toNat?)
  | ["false", z] => do return .zero (← z.toNat?)
  | "and" :: z :: xs => do return .andGate (← z.toNat?) (← xs.mapM String.toNat?)
  | ["xor", z, a, b] => do return .xorGate (← z.toNat?) (← a.toNat?) (← b.toNat?)
  | ["eq", a, b] => do return .eqGate (← a.toNat?) (← b.toNat?)
  | "phase" :: z :: xs => do return .phase (← z.toNat?) (← xs.mapM String.toNat?)
  | _ => none

def parseGate (s : String) : Option (Nat × List Record) :=
  match rows s with
  | ["crr-gate-v1", n] :: rest => do
    return (← n.toNat?, ← rest.mapM parseRecord)
  | _ => none

def pos (n : Nat) : Int := Int.ofNat n

def clauseSort (xs : List Int) : List Int :=
  xs.mergeSort (fun a b => decide (a ≤ b))

def parseClause (n : Nat) (xs : List String) : Option (List Int) := do
  let ints ← xs.mapM String.toInt?
  match ints.reverse with
  | 0 :: rev =>
    if rev.all (fun x => x != 0 && x.natAbs ≤ n) then
      some (clauseSort rev)
    else none
  | _ => none

-- Exact emitted GPMC grammar. Weight records are recognized but not
-- interpreted by this Boolean checker. They remain in the archived CNF.
def parseCnf (s : String) : Option (Nat × List (List Int)) := do
  match rows s with
  | ["p", "cnf", n, m] :: ["c", "t", "wmc"] :: rest =>
    let n ← n.toNat?
    let m ← m.toNat?
    let mut clauses := []
    let mut inClauses := false
    for row in rest do
      match row with
      | ["c", "p", "weight", _, _, _, "0"] =>
        if inClauses then return none
      | _ =>
        inClauses := true
        let c ← parseClause n row
        clauses := c :: clauses
    if clauses.length = m then return (n, clauses) else none
  | _ => none

def bagEq {A : Type} [BEq A] : List A → List A → Bool
  | [], ys => ys.isEmpty
  | x :: xs, ys => ys.contains x && bagEq xs (ys.erase x)

def distinctNat : List Nat → Bool
  | [] => true
  | x :: xs => !xs.contains x && distinctNat xs

def validId (n v : Nat) : Bool := v != 0 && v ≤ n

def andRows (z : Nat) (inputs : List Nat) : List (List Int) :=
  (inputs.map (fun v => clauseSort [-pos z, pos v])) ++
  [clauseSort (pos z :: inputs.map (fun v => -pos v))]

def xorRows (z a b : Nat) : List (List Int) :=
  [[-pos a, -pos b, -pos z], [pos a, pos b, -pos z],
   [pos a, -pos b, pos z], [-pos a, pos b, pos z]].map clauseSort

def eqRows (a b : Nat) : List (List Int) :=
  [[-pos a, pos b], [pos a, -pos b]].map clauseSort

-- Replay all records in order. Live entries first; all later outputs
-- fresh, dependencies already available; equalities and phase
-- declarations can only refer to the completed graph.
def replay (n : Nat) (records : List Record) (actual : List (List Int)) : Bool := Id.run do
  let mut seen : List Nat := []
  let mut live : List (Nat × Nat) := []
  let mut products : List (Nat × List Nat) := []
  let mut weighted : List Nat := []
  let mut clauses : List (List Int) := []
  let mut stage : Nat := 0
  for r in records do
    match r with
    | .live v id =>
      if stage != 0 || !validId n id || seen.contains id || live.any (fun p => p.1 == v) then return false
      seen := id :: seen
      live := (v,id) :: live
    | .zero z =>
      if stage > 1 || !validId n z || seen.contains z then return false
      stage := 1
      seen := z :: seen
      clauses := [-pos z] :: clauses
    | .andGate z inputs =>
      if stage > 1 || !validId n z || seen.contains z ||
          !distinctNat inputs || !inputs.all (fun v => seen.contains v) then return false
      stage := 1
      seen := z :: seen
      products := (z,inputs) :: products
      clauses := andRows z inputs ++ clauses
    | .xorGate z a b =>
      if stage > 1 || !validId n z || seen.contains z ||
          !seen.contains a || !seen.contains b then return false
      stage := 1
      seen := z :: seen
      clauses := xorRows z a b ++ clauses
    | .eqGate a b =>
      if stage > 2 || !seen.contains a || !seen.contains b then return false
      stage := 2
      clauses := eqRows a b ++ clauses
    | .phase z source =>
      stage := 3
      if weighted.contains z || !distinctNat source then return false
      let some ids := source.mapM (fun v => (live.find? (fun p => p.1 == v)).map Prod.snd)
        | return false
      let some p := products.find? (fun p => p.1 == z) | return false
      if p.2 != ids then return false
      weighted := z :: weighted
  return seen.length == n && bagEq clauses actual

def check (gate cnf : String) : Bool :=
  match parseGate gate, parseCnf cnf with
  | some (n, rs), some (m, clauses) => n == m && replay n rs clauses
  | _, _ => false

#print axioms and_forward
#print axioms and_nary
end QuPRS.CnfReplay

def main (args : List String) : IO Unit := do
  let mode :: paths := args | throw (IO.userError "usage: CnfReplay accept|reject files")
  if (mode != "accept" && mode != "reject") || paths.isEmpty then
    throw (IO.userError "bad replay mode or empty cohort")
  let want := mode == "accept"
  for path in paths do
    let gate ← IO.FS.readFile path
    let cnf ← IO.FS.readFile (path ++ ".cnf")
    let got := QuPRS.CnfReplay.check gate cnf
    if got != want then throw (IO.userError s!"unexpected replay result {path}: {got}")
    IO.println s!"CRR_LEAN_PORTABLE_GATE mode={mode} path={path} matched=true"
  IO.println s!"CRR_LEAN_PORTABLE_SUMMARY mode={mode} count={paths.length}"
