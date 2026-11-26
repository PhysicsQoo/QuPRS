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

-- Raw-byte transport. The checked kernel consumes lists of natural
-- byte values, with no String/Char conversion or Unicode library.
-- IO reads the original file bytes; only the outer runner converts
-- UInt8 to Nat. The wire format is unchanged.
abbrev Token := List Nat

def splitBytes (separator : Nat) (cs : List Nat) : List (List Nat) :=
  let (pieces, current) := cs.foldl
    (fun (acc : List (List Nat) × List Nat) c =>
      if c == separator then (acc.2.reverse :: acc.1, [])
      else (acc.1, c :: acc.2)) ([], [])
  (current.reverse :: pieces).reverse

def rows (s : List Nat) : List (List Token) :=
  List.filter (fun ts => !ts.isEmpty)
    ((splitBytes 10 s).map (fun line =>
      (splitBytes 32 line).filter (fun cs => !cs.isEmpty)))

def natLE (a b : Nat) : Bool := Nat.ble a b

def digits (cs : List Nat) (acc : Nat) : Option Nat :=
  match cs with
  | [] => some acc
  | d :: rest =>
    if natLE 48 d && natLE d 57 then digits rest (10 * acc + (d - 48))
    else none

def parseNatToken (s : Token) : Option Nat :=
  match s with
  | [] => none
  | c :: cs => digits (c :: cs) 0

def parseIntToken (s : Token) : Option Int :=
  match s with
  | [] => none
  | c :: cs =>
    if c == 45 then
      match cs with
      | [] => none
      | d :: ds => (digits (d :: ds) 0).map (fun n => -(Int.ofNat n))
    else (digits (c :: cs) 0).map Int.ofNat

def negative (v : Int) : Bool :=
  match v with
  | .ofNat _ => false
  | .negSucc _ => true

def parseRecord : List Token → Option Record
  | tag :: rest =>
    if tag == [108, 105, 118, 101] then
      match rest with
      | [a, b] => do return .live (← parseNatToken a) (← parseNatToken b)
      | _ => none
    else if tag == [102, 97, 108, 115, 101] then
      match rest with
      | [z] => do return .zero (← parseNatToken z)
      | _ => none
    else if tag == [97, 110, 100] then
      match rest with
      | z :: xs => do return .andGate (← parseNatToken z) (← xs.mapM parseNatToken)
      | _ => none
    else if tag == [120, 111, 114] then
      match rest with
      | [z, a, b] => do return .xorGate (← parseNatToken z) (← parseNatToken a) (← parseNatToken b)
      | _ => none
    else if tag == [101, 113] then
      match rest with
      | [a, b] => do return .eqGate (← parseNatToken a) (← parseNatToken b)
      | _ => none
    else if tag == [112, 104, 97, 115, 101] then
      match rest with
      | z :: xs => do return .phase (← parseNatToken z) (← xs.mapM parseNatToken)
      | _ => none
    else none
  | [] => none

def parseGate (s : List Nat) : Option (Nat × List Record) :=
  match rows s with
  | [tag, n] :: rest =>
    if tag == [99, 114, 114, 45, 103, 97, 116, 101, 45, 118, 49] then do
      return (← parseNatToken n, ← rest.mapM parseRecord)
    else none
  | _ => none

def pos (n : Nat) : Int := Int.ofNat n

def clauseSort (xs : List Int) : List Int :=
  xs.mergeSort (fun a b => decide (a ≤ b))

def parseClause (n : Nat) (xs : List Token) : Option (List Int) := do
  let ints ← xs.mapM parseIntToken
  match ints.reverse with
  | 0 :: rev =>
    if rev.all (fun x => x != 0 && natLE x.natAbs n) then
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
    List (List Token) → Bool → List (List Int) → List Int →
    Option (List (List Int) × List Int)
  | [], _, cs, ws => some (cs, ws)
  | row :: rest, inClauses, cs, ws =>
    match row with
    | [c, p, tag, id, re, im, zero] =>
      if c == [99] && p == [112] && tag == [119, 101, 105, 103, 104, 116] && zero == [48] then do
        let v ← parseIntToken id
        if inClauses || v == 0 || !natLE v.natAbs n || ws.contains v ||
            (negative v && (re != [49, 46, 48] || im != [48, 46, 48])) then none
        else parseCnfRows n rest false cs (v :: ws)
      else do
        let clause ← parseClause n row
        parseCnfRows n rest true (clause :: cs) ws
    | _ => do
      let c ← parseClause n row
      parseCnfRows n rest true (c :: cs) ws

def parseCnf (s : List Nat) : Option ParsedCnf :=
  match rows s with
  | [p, cnf, n, m] :: [c, t, wmc] :: rest =>
    if p == [112] && cnf == [99, 110, 102] && c == [99] &&
        t == [116] && wmc == [119, 109, 99] then do
      let n ← parseNatToken n
      let m ← parseNatToken m
      let (cs, ws) ← parseCnfRows n rest false [] []
      if cs.length == m then some { vars := n, clauses := cs, weights := ws } else none
    else none
  | _ => none

-- Explicit comparator, no inferred equality instances. Remove one
-- matching occurrence, preserving multiplicity.
def removeOne {A : Type} (eq : A → A → Bool) (x : A) :
    List A → Option (List A)
  | [] => none
  | y :: ys =>
    if eq x y then some ys
    else (removeOne eq x ys).map (fun rest => y :: rest)

def bagEqBy {A : Type} (eq : A → A → Bool) :
    List A → List A → Bool
  | [], ys => ys.isEmpty
  | x :: xs, ys =>
    match removeOne eq x ys with
    | some rest => bagEqBy eq xs rest
    | none => false

def intEq (a b : Int) : Bool := @decide (a = b) (Int.decEq a b)

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

-- Explicit constructive equality/membership. Avoid inferred
-- Decidable (x ∈ ys), which picked up a classical instance.
def clauseEq : List Int → List Int → Bool
  | [], [] => true
  | a :: xs, b :: ys => (@decide (a = b) (Int.decEq a b)) && clauseEq xs ys
  | _, _ => false

theorem clause_eq_iff (xs ys : List Int) :
    clauseEq xs ys = true ↔ xs = ys := by
  induction xs generalizing ys with
  | nil => cases ys <;> simp [clauseEq]
  | cons a xs ih =>
    cases ys with
    | nil => simp [clauseEq]
    | cons b bs =>
      simp only [clauseEq, Bool.and_eq_true, decide_eq_true_eq, ih, List.cons.injEq]

def clauseMem (x : List Int) : List (List Int) → Bool
  | [] => false
  | y :: ys => clauseEq x y || clauseMem x ys

theorem clause_mem_iff (x : List Int) (ys : List (List Int)) :
    clauseMem x ys = true ↔ x ∈ ys := by
  induction ys with
  | nil => simp [clauseMem]
  | cons y ys ih =>
    simp only [clauseMem, Bool.or_eq_true, clause_eq_iff, ih, List.mem_cons]

-- Redundant semantic coverage is retained alongside the stronger
-- multiplicity check, with a constructive decision path.
def covers (xs ys : List (List Int)) : Bool :=
  match xs with
  | [] => true
  | x :: rest => clauseMem x ys && covers rest ys

theorem covers_iff (xs ys : List (List Int)) :
    covers xs ys = true ↔ ∀ x, x ∈ xs → x ∈ ys := by
  induction xs with
  | nil => simp [covers]
  | cons x xs ih =>
    simp only [covers, Bool.and_eq_true, clause_mem_iff, ih, List.mem_cons]
    constructor
    · intro h y hy
      rcases hy with he | he
      · subst y
        exact h.1
      · exact h.2 y he
    · intro h
      exact ⟨h x (Or.inl rfl), fun y hy => h y (Or.inr hy)⟩

-- Explicit truth-table lemma, independent of library theorem naming.
theorem and_true_parts {a b : Bool} (h : (a && b) = true) :
    a = true ∧ b = true := by
  cases a <;> cases b <;> simp_all

def satisfies (clauses : List (List Int)) (value : Int → Bool) : Prop :=
  ∀ c, c ∈ clauses → ∃ lit, lit ∈ c ∧ value lit = true

def checkRows (generated actual : List (List Int)) : Bool :=
  (bagEqBy clauseEq generated actual && covers generated actual) && covers actual generated

theorem check_rows_sound (generated actual : List (List Int))
    (h : checkRows generated actual = true) (value : Int → Bool) :
    satisfies generated value ↔ satisfies actual value :=
  let h' : ((bagEqBy clauseEq generated actual && covers generated actual) &&
      covers actual generated) = true := h
  let hc := and_true_parts h'
  let hg := (covers_iff generated actual).mp (and_true_parts hc.1).2
  let ha := (covers_iff actual generated).mp hc.2
  Iff.intro (fun hs c hm => hs c (ha c hm))
    (fun hs c hm => hs c (hg c hm))

def weightIds (weighted : List Nat) : List Int :=
  weighted.flatMap (fun z => [pos z, -pos z])

-- The acceptance function is shared by the executable path and
-- proof, so the theorem does not rely on tactic unfolding or simp.
def acceptResult (n : Nat) (p : ParsedCnf) :
    Option (List (List Int) × List Nat) → Bool
  | some (cs, ws) =>
    ((@decide (n = p.vars) (Nat.decEq n p.vars)) &&
      bagEqBy intEq (weightIds ws) p.weights) && checkRows cs p.clauses
  | none => false

def ascii (bytes : List Nat) : Bool :=
  bytes.all (fun b => natLE b 127)

def check (gate cnf : List Nat) : Bool :=
  if ascii gate && ascii cnf then
    match parseGate gate, parseCnf cnf with
    | some (n, rs), some p => acceptResult n p (replayRows n rs)
    | _, _ => false
  else false

-- Typed replay boundary: acceptance implies clause satisfaction
-- equivalence for every literal valuation. Use only explicit
-- congruence/definitional equality, without rewrite automation.
theorem accepted_rows_sound (n : Nat) (rs : List Record)
    (p : ParsedCnf) (generated : List (List Int)) (weighted : List Nat)
    (hr : replayRows n rs = some (generated, weighted))
    (h : acceptResult n p (replayRows n rs) = true)
    (value : Int → Bool) :
    satisfies generated value ↔ satisfies p.clauses value :=
  let h' : acceptResult n p (some (generated, weighted)) = true :=
    (congrArg (acceptResult n p) hr).symm.trans h
  let hc : (((@decide (n = p.vars) (Nat.decEq n p.vars)) &&
    bagEqBy intEq (weightIds weighted) p.weights) &&
    checkRows generated p.clauses) = true := h'
  check_rows_sound generated p.clauses (and_true_parts hc).2 value

-- Localize any unexpected dependency to a definition vs theorem.
#print axioms splitBytes
#print axioms digits
#print axioms ascii
#print axioms rows
#print axioms parseNatToken
#print axioms parseIntToken
#print axioms parseRecord
#print axioms parseGate
#print axioms parseClause
#print axioms parseCnfRows
#print axioms parseCnf
#print axioms bagEqBy
#print axioms covers
#print axioms satisfies
#print axioms checkRows
#print axioms replayRows
#print axioms acceptResult
#print axioms check
#print axioms and_forward
#print axioms and_nary
#print axioms clause_eq_iff
#print axioms clause_mem_iff
#print axioms and_true_parts
#print axioms covers_iff
#print axioms check_rows_sound
#print axioms accepted_rows_sound
end QuPRS.CnfReplay

def main (args : List String) : IO Unit := do
  -- Exercise the same byte parser used for real files.
  if QuPRS.CnfReplay.parseNatToken [49, 50, 51] != some 123 ||
      QuPRS.CnfReplay.parseNatToken [] != none ||
      QuPRS.CnfReplay.parseNatToken [49, 50, 120] != none ||
      QuPRS.CnfReplay.parseIntToken [45, 51, 55] != some (-37) ||
      QuPRS.CnfReplay.parseIntToken [45] != none ||
      QuPRS.CnfReplay.parseIntToken [49, 45, 50] != none ||
      QuPRS.CnfReplay.rows [112, 32, 32, 99, 110, 102, 32, 51, 32, 49, 10, 10, 45, 49, 32, 50, 32, 48, 10] !=
        [[[112], [99, 110, 102], [51], [49]], [[45, 49], [50], [48]]] ||
      QuPRS.CnfReplay.ascii [128] then
    throw (IO.userError "portable parser grammar regression")
  IO.println "CRR_LEAN_PARSER_GRAMMAR_PASS controls=8"
  let mode :: paths := args | throw (IO.userError "usage: CnfReplay accept|reject files")
  if (mode != "accept" && mode != "reject") || paths.isEmpty then
    throw (IO.userError "bad replay mode or empty cohort")
  let want := mode == "accept"
  for path in paths do
    let gate ← IO.FS.readBinFile path
    let cnf ← IO.FS.readBinFile (path ++ ".cnf")
    let got := QuPRS.CnfReplay.check
      (gate.data.toList.map UInt8.toNat) (cnf.data.toList.map UInt8.toNat)
    if got != want then throw (IO.userError s!"unexpected replay result {path}: {got}")
    IO.println s!"CRR_LEAN_PORTABLE_GATE mode={mode} path={path} matched=true"
  IO.println s!"CRR_LEAN_PORTABLE_SUMMARY mode={mode} count={paths.length}"
