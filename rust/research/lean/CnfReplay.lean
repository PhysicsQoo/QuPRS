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
  cases z <;> cases andValue xs <;> decide

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

-- Recognize the precise GPMC weight grammar structurally. Decimal
-- magnitude and ideal-phase accuracy remain a separate Rust check.
structure ParsedCnf where
  vars : Nat
  clauses : List (List Int)
  weights : List Int

def parseCnfRows (n : Nat) :
    List (List String) → Bool → List (List Int) → List Int →
    Option (List (List Int) × List Int)
  | [], _, cs, ws => some (cs, ws)
  | row :: rest, inClauses, cs, ws =>
    match row with
    | ["c", "p", "weight", id, re, im, "0"] => do
      let v ← id.toInt?
      if inClauses || v == 0 || v.natAbs > n || ws.contains v ||
          (v < 0 && (re != "1.0" || im != "0.0")) then none
      else parseCnfRows n rest false cs (v :: ws)
    | _ => do
      let c ← parseClause n row
      parseCnfRows n rest true (c :: cs) ws

def parseCnf (s : String) : Option ParsedCnf := do
  match rows s with
  | ["p", "cnf", n, m] :: ["c", "t", "wmc"] :: rest =>
    let n ← n.toNat?
    let m ← m.toNat?
    let (cs, ws) ← parseCnfRows n rest false [] []
    if cs.length = m then some { vars := n, clauses := cs, weights := ws } else none
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
def replayRows (n : Nat) (records : List Record) : Option (List (List Int) × List Nat) := Id.run do
  let mut seen : List Nat := []
  let mut live : List (Nat × Nat) := []
  let mut products : List (Nat × List Nat) := []
  let mut weighted : List Nat := []
  let mut clauses : List (List Int) := []
  let mut stage : Nat := 0
  for r in records do
    match r with
    | .live v id =>
      if stage != 0 || !validId n id || seen.contains id || live.any (fun p => p.1 == v) then return none
      seen := id :: seen
      live := (v,id) :: live
    | .zero z =>
      if stage > 1 || !validId n z || seen.contains z then return none
      stage := 1
      seen := z :: seen
      clauses := [-pos z] :: clauses
    | .andGate z inputs =>
      if stage > 1 || !validId n z || seen.contains z ||
          !distinctNat inputs || !inputs.all (fun v => seen.contains v) then return none
      stage := 1
      seen := z :: seen
      products := (z,inputs) :: products
      clauses := andRows z inputs ++ clauses
    | .xorGate z a b =>
      if stage > 1 || !validId n z || seen.contains z ||
          !seen.contains a || !seen.contains b then return none
      stage := 1
      seen := z :: seen
      clauses := xorRows z a b ++ clauses
    | .eqGate a b =>
      if stage > 2 || !seen.contains a || !seen.contains b then return none
      stage := 2
      clauses := eqRows a b ++ clauses
    | .phase z source =>
      stage := 3
      if weighted.contains z || !distinctNat source then return none
      let some ids := source.mapM (fun v => (live.find? (fun p => p.1 == v)).map Prod.snd)
        | return none
      let some p := products.find? (fun p => p.1 == z) | return none
      if p.2 != ids then return none
      weighted := z :: weighted
  if seen.length == n then return some (clauses, weighted) else return none

-- Redundant semantic coverage is deliberately retained alongside
-- the stronger multiplicity check. This executable predicate is the
-- one used by the following kernel theorem, not an unrelated model.
def covers (xs ys : List (List Int)) : Bool :=
  match xs with
  | [] => true
  | x :: rest => decide (x ∈ ys) && covers rest ys

theorem covers_iff (xs ys : List (List Int)) :
    covers xs ys = true ↔ ∀ x, x ∈ xs → x ∈ ys := by
  induction xs with
  | nil => simp [covers]
  | cons x xs ih =>
    simp only [covers, Bool.and_eq_true, decide_eq_true_eq, ih, List.mem_cons]
    constructor
    · intro h y hy
      rcases hy with he | he
      · subst y
        exact h.1
      · exact h.2 y he
    · intro h
      exact ⟨h x (Or.inl rfl), fun y hy => h y (Or.inr hy)⟩

def satisfies (clauses : List (List Int)) (value : Int → Bool) : Prop :=
  ∀ c, c ∈ clauses → ∃ lit, lit ∈ c ∧ value lit = true

def checkRows (generated actual : List (List Int)) : Bool :=
  (bagEq generated actual && covers generated actual) && covers actual generated

theorem check_rows_sound (generated actual : List (List Int))
    (h : checkRows generated actual = true) (value : Int → Bool) :
    satisfies generated value ↔ satisfies actual value := by
  have hc := Bool.and_eq_true.mp h
  have hg := (covers_iff generated actual).mp (Bool.and_eq_true.mp hc.1).2
  have ha := (covers_iff actual generated).mp hc.2
  constructor
  · intro hs c hm
    exact hs c (ha c hm)
  · intro hs c hm
    exact hs c (hg c hm)

def weightIds (weighted : List Nat) : List Int :=
  weighted.flatMap (fun z => [pos z, -pos z])

def check (gate cnf : String) : Bool :=
  match parseGate gate, parseCnf cnf with
  | some (n, rs), some p =>
    match replayRows n rs with
    | some (generated, weighted) =>
      (n == p.vars && bagEq (weightIds weighted) p.weights) &&
        checkRows generated p.clauses
    | none => false
  | _, _ => false

-- Typed replay boundary: acceptance implies clause satisfaction
-- equivalence for every literal valuation. Parser-to-gate semantics
-- and the topological unique-extension refinement are still separate.
theorem accepted_rows_sound (n : Nat) (rs : List Record)
    (p : ParsedCnf) (generated : List (List Int)) (weighted : List Nat)
    (hr : replayRows n rs = some (generated, weighted))
    (h : (match replayRows n rs with
      | some (cs, ws) => (n == p.vars && bagEq (weightIds ws) p.weights) &&
          checkRows cs p.clauses
      | none => false) = true)
    (value : Int → Bool) :
    satisfies generated value ↔ satisfies p.clauses value := by
  rw [hr] at h
  exact check_rows_sound generated p.clauses (Bool.and_eq_true.mp h).2 value

#print axioms and_forward
#print axioms and_nary
#print axioms covers_iff
#print axioms check_rows_sound
#print axioms accepted_rows_sound
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
