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

def intEq (a b : Int) : Bool := @decide (a = b) (Int.decEq a b)

def literalValid (n : Nat) (x : Int) : Bool :=
  !intEq x 0 && natLE x.natAbs n

-- Avoid the overloaded Int numeral pattern (0 :: rest): the
-- equation compiler may introduce a classical equality decision.
-- Match only List constructors and compare the last literal using
-- the same explicit integer equality as the checked multiset.
def finishClause (n : Nat) (reversed : List Int) : Option (List Int) :=
  match reversed with
  | last :: rev =>
    if intEq last 0 && rev.all (literalValid n) then
      some (clauseSort rev)
    else none
  | [] => none

def parseClause (n : Nat) (xs : List Token) : Option (List Int) := do
  let ints ← xs.mapM parseIntToken
  finishClause n ints.reverse

-- Exact decimal transport: (signed numerator, positive denominator).
-- No floating-point conversion; retain the actual serialized values.
-- Fractions need not be reduced. Exponent and token caps match Rust.
abbrev DecimalValue := Int × Nat
abbrev ComplexValue := DecimalValue × DecimalValue
abbrev WeightEntry := Int × ComplexValue

def signedToken (s : Token) : Bool × Token :=
  match s with
  | c :: cs => if c == 45 then (true, cs)
    else if c == 43 then (false, cs) else (false, s)
  | [] => (false, [])

def decimalMantissa (s : Token) : Option (Int × Nat) := do
  let (neg, unsigned) := signedToken s
  let (ds, places) ←
    match splitBytes 46 unsigned with
    | [whole] => some (whole, 0)
    | [whole, frac] => some (whole ++ frac, frac.length)
    | _ => none
  let n ← parseNatToken ds
  return (if neg then -(Int.ofNat n) else Int.ofNat n, places)

def decimalExponent (s : Token) : Option Int := do
  let (neg, ds) := signedToken s
  let n ← parseNatToken ds
  if natLE n 4096 then
    some (if neg then -(Int.ofNat n) else Int.ofNat n)
  else none

-- Give the intermediate token/exponent pair its own explicit type.
-- Avoid nested do/return elaboration against DecimalValue.
def decimalParts (s : Token) : Option (Token × Int) :=
  match splitBytes 101 (s.map (fun b => if b == 69 then 101 else b)) with
  | [m] => some (m, 0)
  | [m,e] => (decimalExponent e).map (fun exp => (m, exp))
  | _ => none

def decimalValue (s : Token) : Option DecimalValue := do
  if !natLE s.length 512 then none else
    let (mant, exp) ← decimalParts s
    let (n, places) ← decimalMantissa mant
    let shift := exp - Int.ofNat places
    let power : Nat := 10 ^ shift.natAbs
    if negative shift then some (n, power)
    else some (n * Int.ofNat power, 1)

structure ParsedCnf where
  vars : Nat
  clauses : List (List Int)
  weights : List Int
  weightValues : List WeightEntry

def parseCnfRows (n : Nat) :
    List (List Token) → Bool → List (List Int) → List WeightEntry →
    Option (List (List Int) × List WeightEntry)
  | [], _, cs, ws => some (cs, ws)
  | row :: rest, inClauses, cs, ws =>
    match row with
    | [c, p, tag, id, re, im, zero] =>
      if c == [99] && p == [112] && tag == [119, 101, 105, 103, 104, 116] && zero == [48] then do
        let v ← parseIntToken id
        if inClauses || !literalValid n v || ws.any (fun e => intEq v e.1) ||
            (negative v && (re != [49, 46, 48] || im != [48, 46, 48])) then none
        else
          let real ← decimalValue re
          let imag ← decimalValue im
          parseCnfRows n rest false cs ((v, (real, imag)) :: ws)
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
      if cs.length == m then some (ParsedCnf.mk n cs (ws.map Prod.fst) ws) else none
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

-- Generate exactly the same rows as the former replay accumulator,
-- in reverse record order. This pure function is shared by runtime
-- replay and the semantic composition theorem.
def recordRows : Record → List (List Int)
  | .zero z => [[-pos z]]
  | .andGate z inputs => andRows z inputs
  | .xorGate z a b => xorRows z a b
  | .eqGate a b => eqRows a b
  | .live _ _ => []
  | .phase _ _ => []

def recordsRows : List Record → List (List Int)
  | [] => []
  | r :: rs => recordsRows rs ++ recordRows r

def natMem (x : Nat) : List Nat → Bool
  | [] => false
  | y :: ys => (@decide (x = y) (Nat.decEq x y)) || natMem x ys

def inputsKnown (seen : List Nat) : List Nat → Bool
  | [] => true
  | x :: xs => natMem x seen && inputsKnown seen xs

def liveIds : List Record → List Nat
  | [] => []
  | .live _ id :: rs => id :: liveIds rs
  | _ :: rs => liveIds rs

def gateOutput : Record → Option Nat
  | .zero z => some z
  | .andGate z _ => some z
  | .xorGate z _ _ => some z
  | _ => none

def gateInputs : Record → List Nat
  | .andGate _ inputs => inputs
  | .xorGate _ a b => [a,b]
  | _ => []

def nextSeen (seen : List Nat) (r : Record) : List Nat :=
  match gateOutput r with
  | some z => z :: seen
  | none => seen

-- Redundant independently checkable topological premise. The
-- original replay still checks stage, ID bounds, freshness, full
-- domain, phase binding and equality dependencies.
def topo (seen : List Nat) : List Record → Bool
  | [] => true
  | r :: rs => inputsKnown seen (gateInputs r) &&
      (match gateOutput r with
       | some z => !natMem z seen
       | none => true) &&
      topo (nextSeen seen r) rs

def finalSeen (seen : List Nat) : List Record → List Nat
  | [] => seen
  | r :: rs => finalSeen (nextSeen seen r) rs

-- Replay all records in order. Live entries first; all later outputs
-- fresh, dependencies already available; equalities and phase
-- declarations can only refer to the completed graph.
def replayWeights (n : Nat) (records : List Record) : Option (List Nat) := Id.run do
  let mut seen : List Nat := []
  let mut live : List (Nat × Nat) := []
  let mut products : List (Nat × List Nat) := []
  let mut weighted : List Nat := []
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
    | .andGate z inputs =>
      if stage > 1 || !validId n z || seen.contains z ||
          !distinctNat inputs || !inputs.all (fun v => seen.contains v) then return none
      stage := 1
      seen := z :: seen
      products := (z,inputs) :: products
    | .xorGate z a b =>
      if stage > 1 || !validId n z || seen.contains z ||
          !seen.contains a || !seen.contains b then return none
      stage := 1
      seen := z :: seen
    | .eqGate a b =>
      if stage > 2 || !seen.contains a || !seen.contains b then return none
      stage := 2
    | .phase z source =>
      stage := 3
      if weighted.contains z || !distinctNat source then return none
      let some ids := source.mapM (fun v => (live.find? (fun p => p.1 == v)).map Prod.snd)
        | return none
      let some p := products.find? (fun p => p.1 == z) | return none
      if p.2 != ids then return none
      weighted := z :: weighted
  if seen.length == n then return some weighted else return none

def dimacsIds (n : Nat) : List Nat := (List.range n).map Nat.succ

-- Every ID used in a Boolean row must belong to the declared domain.
-- Phase source IDs are not DIMACS IDs; the original phase binding
-- check remains responsible for their mapping.
def rowIds : Record → List Nat
  | .zero z => [z]
  | .andGate z xs => z :: xs
  | .xorGate z a b => [z,a,b]
  | .eqGate a b => [a,b]
  | _ => []

def recordsKnown (ids : List Nat) : List Record → Bool
  | [] => true
  | r :: rs => inputsKnown ids (rowIds r) && recordsKnown ids rs

def domainCheck (n : Nat) (rs : List Record) : Bool :=
  let ids := finalSeen (liveIds rs) rs
  (inputsKnown ids (dimacsIds n) && inputsKnown (dimacsIds n) ids) &&
    recordsKnown (dimacsIds n) rs

-- Independently replayable live/phase binding checks. The original
-- stage, freshness, source mapping and weight coverage checks remain.
def uniqueIds : List Nat → Bool
  | [] => true
  | x :: xs => !natMem x xs && uniqueIds xs

def natListEq : List Nat → List Nat → Bool
  | [], [] => true
  | x :: xs, y :: ys => (@decide (x = y) (Nat.decEq x y)) && natListEq xs ys
  | _, _ => false

def sourceDimacs (s : Nat) : List Record → Option Nat
  | [] => none
  | .live v id :: rs => if s == v then some id else sourceDimacs s rs
  | _ :: rs => sourceDimacs s rs

def phaseIds : List Record → List Nat
  | [] => []
  | .phase z _ :: rs => z :: phaseIds rs
  | _ :: rs => phaseIds rs

def andWitness (z : Nat) (ids : List Nat) : List Record → Bool
  | [] => false
  | .andGate out xs :: rs =>
    ((@decide (z = out) (Nat.decEq z out)) && natListEq ids xs) || andWitness z ids rs
  | _ :: rs => andWitness z ids rs

-- Structural source mapper shared by admission and the inductive
-- semantic proof. The original replayWeights mapM remains an
-- independent source mapping check.
def sourceIds (rs : List Record) : List Nat → Option (List Nat)
  | [] => some []
  | s :: ss =>
    match sourceDimacs s rs with
    | none => none
    | some id =>
      match sourceIds rs ss with
      | none => none
      | some ids => some (id :: ids)

def phaseRecordOK (rs : List Record) : Record → Bool
  | .phase z source =>
    match sourceIds rs source with
    | some ids => andWitness z ids rs
    | none => false
  | _ => true

def phaseRecordsOK (all : List Record) : List Record → Bool
  | [] => true
  | r :: rs => phaseRecordOK all r && phaseRecordsOK all rs

def replayExtras (rs : List Record) (ws : List Nat) : Bool :=
  (uniqueIds (liveIds rs) && natListEq ws (phaseIds rs).reverse) && phaseRecordsOK rs rs

def replayRows (n : Nat) (records : List Record) : Option (List (List Int) × List Nat) :=
  if topo (liveIds records) records && domainCheck n records then
    match replayWeights n records with
    | some ws => if replayExtras records ws then some (recordsRows records, ws) else none
    | none => none
  else none

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

def checkParsed : Option (Nat × List Record) → Option ParsedCnf → Bool
  | some (n, rs), some p => acceptResult n p (replayRows n rs)
  | _, _ => false

def check (gate cnf : List Nat) : Bool :=
  (ascii gate && ascii cnf) && checkParsed (parseGate gate) (parseCnf cnf)

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


-- Connect actual byte-checker acceptance to its typed replay result.
-- Parsing correctness relative to the external DIMACS specification
-- remains separate: the theorem concerns exactly the parsed rows.
theorem byte_check_sound (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf)
    (generated : List (List Int)) (weighted : List Nat)
    (hg : parseGate gate = some (n, rs))
    (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (generated, weighted))
    (h : check gate cnf = true) (value : Int → Bool) :
    satisfies generated value ↔ satisfies p.clauses value :=
  let h' : ((ascii gate && ascii cnf) &&
      checkParsed (parseGate gate) (parseCnf cnf)) = true := h
  let hc := (and_true_parts h').2
  let h1 : checkParsed (some (n, rs)) (parseCnf cnf) = true :=
    (congrArg (fun g => checkParsed g (parseCnf cnf)) hg).symm.trans hc
  let he : checkParsed (some (n, rs)) (some p) = true :=
    (congrArg (checkParsed (some (n, rs))) hp).symm.trans h1
  accepted_rows_sound n rs p generated weighted hr he value

-- Semantics of the exact sorted rows used by replayRows, not a
-- separate CNF encoder. A valuation is coherent on the relevant
-- positive/negative literal pairs (nonzero IDs established by replay).
def rowTruth (value : Int → Bool) : List Int → Bool
  | [] => false
  | x :: xs => value x || rowTruth value xs

def cnfTruth (value : Int → Bool) : List (List Int) → Bool
  | [] => true
  | row :: rest => rowTruth value row && cnfTruth value rest

theorem row_truth_iff (value : Int → Bool) (row : List Int) :
    rowTruth value row = true ↔ ∃ x, x ∈ row ∧ value x = true := by
  induction row with
  | nil => simp [rowTruth]
  | cons x xs ih =>
    simp only [rowTruth, Bool.or_eq_true, ih, List.mem_cons]
    constructor
    · intro h
      rcases h with hx | ⟨y, hy, hv⟩
      · exact ⟨x, Or.inl rfl, hx⟩
      · exact ⟨y, Or.inr hy, hv⟩
    · intro h
      rcases h with ⟨y, hy, hv⟩
      rcases hy with he | hm
      · subst y
        exact Or.inl hv
      · exact Or.inr ⟨y, hm, hv⟩

theorem cnf_truth_iff (value : Int → Bool) (cs : List (List Int)) :
    cnfTruth value cs = true ↔ satisfies cs value := by
  induction cs with
  | nil => simp [cnfTruth, satisfies]
  | cons c cs ih =>
    constructor
    · intro h row hm
      have h' : (rowTruth value c && cnfTruth value cs) = true := h
      have hc := and_true_parts h'
      rcases List.mem_cons.mp hm with he | ht
      · subst row
        exact (row_truth_iff value c).mp hc.1
      · exact (ih.mp hc.2) row ht
    · intro h
      have hc := (row_truth_iff value c).mpr (h c (List.mem_cons.mpr (Or.inl rfl)))
      have ht := ih.mpr (fun row hm => h row (List.mem_cons.mpr (Or.inr hm)))
      change (rowTruth value c && cnfTruth value cs) = true
      rw [hc, ht]
      rfl

theorem bool_true_iff_eq {a b : Bool} (h : (a = true ↔ b = true)) :
    a = b := by
  cases a <;> cases b <;> simp_all

theorem row_truth_sort (value : Int → Bool) (row : List Int) :
    rowTruth value (clauseSort row) = rowTruth value row := by
  apply bool_true_iff_eq
  simp only [row_truth_iff]
  constructor
  · rintro ⟨x, hm, hv⟩
    exact ⟨x, List.mem_mergeSort.mp hm, hv⟩
  · rintro ⟨x, hm, hv⟩
    exact ⟨x, List.mem_mergeSort.mpr hm, hv⟩

theorem cnf_truth_append (value : Int → Bool) (a b : List (List Int)) :
    cnfTruth value (a ++ b) = (cnfTruth value a && cnfTruth value b) := by
  induction a with
  | nil => rfl
  | cons x xs ih =>
    simp only [List.cons_append, cnfTruth, ih, Bool.and_assoc]

theorem cnf_truth_sorted (value : Int → Bool) (cs : List (List Int)) :
    cnfTruth value (cs.map clauseSort) = cnfTruth value cs := by
  induction cs with
  | nil => rfl
  | cons x xs ih =>
    simp only [List.map_cons, cnfTruth, row_truth_sort, ih]

theorem and_forward_rows (value : Int → Bool) (z : Nat) (inputs : List Nat)
    (hz : value (-pos z) = !(value (pos z))) :
    cnfTruth value (inputs.map (fun v => clauseSort [-pos z, pos v])) =
      andForward (inputs.map (fun v => value (pos v))) (value (pos z)) := by
  induction inputs with
  | nil => rfl
  | cons x xs ih =>
    simp only [List.map_cons, cnfTruth, row_truth_sort, rowTruth, Bool.or_false,
      hz, andForward, ih]

theorem negative_row (value : Int → Bool) (inputs : List Nat)
    (h : ∀ v, v ∈ inputs → value (-pos v) = !(value (pos v))) :
    rowTruth value (inputs.map (fun v => -pos v)) =
      !(andValue (inputs.map (fun v => value (pos v)))) := by
  induction inputs with
  | nil => rfl
  | cons x xs ih =>
    have hx := h x (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih (fun v hv => h v (List.mem_cons.mpr (Or.inr hv)))
    simp only [List.map_cons, rowTruth, andValue, hx, ht]
    cases value (pos x) <;> cases andValue (xs.map (fun v => value (pos v))) <;> rfl

theorem actual_and_rows_sound (value : Int → Bool) (z : Nat) (inputs : List Nat)
    (hz : value (-pos z) = !(value (pos z)))
    (hi : ∀ v, v ∈ inputs → value (-pos v) = !(value (pos v))) :
    satisfies (andRows z inputs) value ↔
      value (pos z) = andValue (inputs.map (fun v => value (pos v))) := by
  rw [← cnf_truth_iff]
  unfold andRows
  rw [cnf_truth_append, and_forward_rows value z inputs hz]
  simp only [cnfTruth, row_truth_sort, rowTruth, Bool.and_true, negative_row value inputs hi]
  exact and_nary (inputs.map (fun v => value (pos v))) (value (pos z))

theorem actual_xor_rows_sound (value : Int → Bool) (z a b : Nat)
    (hz : value (-pos z) = !(value (pos z)))
    (ha : value (-pos a) = !(value (pos a)))
    (hb : value (-pos b) = !(value (pos b))) :
    satisfies (xorRows z a b) value ↔
      value (pos z) = (value (pos a)).xor (value (pos b)) := by
  rw [← cnf_truth_iff]
  unfold xorRows
  rw [cnf_truth_sorted]
  simp only [cnfTruth, rowTruth, Bool.or_false, Bool.and_true, hz, ha, hb]
  cases value (pos z) <;> cases value (pos a) <;> cases value (pos b) <;> decide

theorem actual_eq_rows_sound (value : Int → Bool) (a b : Nat)
    (ha : value (-pos a) = !(value (pos a)))
    (hb : value (-pos b) = !(value (pos b))) :
    satisfies (eqRows a b) value ↔ value (pos a) = value (pos b) := by
  rw [← cnf_truth_iff]
  unfold eqRows
  rw [cnf_truth_sorted]
  simp only [cnfTruth, rowTruth, Bool.or_false, Bool.and_true, ha, hb]
  cases value (pos a) <;> cases value (pos b) <;> decide

theorem actual_zero_row_sound (value : Int → Bool) (z : Nat)
    (hz : value (-pos z) = !(value (pos z))) :
    satisfies [[-pos z]] value ↔ value (pos z) = false := by
  rw [← cnf_truth_iff]
  simp only [cnfTruth, rowTruth, Bool.or_false, Bool.and_true, hz]
  cases value (pos z) <;> decide


-- Global semantic relation of the actual record sequence.
def recordSem (value : Int → Bool) : Record → Prop
  | .zero z => value (pos z) = false
  | .andGate z xs => value (pos z) = andValue (xs.map (fun v => value (pos v)))
  | .xorGate z a b => value (pos z) = (value (pos a)).xor (value (pos b))
  | .eqGate a b => value (pos a) = value (pos b)
  | .live _ _ => True
  | .phase _ _ => True

def recordCoherent (value : Int → Bool) : Record → Prop
  | .zero z => value (-pos z) = !(value (pos z))
  | .andGate z xs => (value (-pos z) = !(value (pos z))) ∧
      (∀ v, v ∈ xs → value (-pos v) = !(value (pos v)))
  | .xorGate z a b => (value (-pos z) = !(value (pos z))) ∧
      (value (-pos a) = !(value (pos a))) ∧ (value (-pos b) = !(value (pos b)))
  | .eqGate a b => (value (-pos a) = !(value (pos a))) ∧
      (value (-pos b) = !(value (pos b)))
  | .live _ _ => True
  | .phase _ _ => True

def recordsSem (value : Int → Bool) (rs : List Record) : Prop :=
  ∀ r, r ∈ rs → recordSem value r

theorem actual_record_rows_sound (value : Int → Bool) (r : Record)
    (h : recordCoherent value r) :
    satisfies (recordRows r) value ↔ recordSem value r := by
  cases r with
  | live v id => simp [recordRows, recordSem, satisfies]
  | phase z xs => simp [recordRows, recordSem, satisfies]
  | zero z => exact actual_zero_row_sound value z h
  | andGate z xs => exact actual_and_rows_sound value z xs h.1 h.2
  | xorGate z a b => exact actual_xor_rows_sound value z a b h.1 h.2.1 h.2.2
  | eqGate a b => exact actual_eq_rows_sound value a b h.1 h.2

theorem satisfies_append (value : Int → Bool) (a b : List (List Int)) :
    satisfies (a ++ b) value ↔ satisfies a value ∧ satisfies b value := by
  constructor
  · intro h
    exact ⟨fun row hm => h row (List.mem_append.mpr (Or.inl hm)),
      fun row hm => h row (List.mem_append.mpr (Or.inr hm))⟩
  · intro h row hm
    rcases List.mem_append.mp hm with ha | hb
    · exact h.1 row ha
    · exact h.2 row hb

theorem actual_records_rows_sound (value : Int → Bool) (rs : List Record)
    (h : ∀ r, r ∈ rs → recordCoherent value r) :
    satisfies (recordsRows rs) value ↔ recordsSem value rs := by
  induction rs with
  | nil => simp [recordsRows, recordsSem, satisfies]
  | cons r rs ih =>
    have hc := h r (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih (fun q hm => h q (List.mem_cons.mpr (Or.inr hm)))
    have hr := actual_record_rows_sound value r hc
    change satisfies (recordsRows rs ++ recordRows r) value ↔ recordsSem value (r :: rs)
    rw [satisfies_append, ht, hr]
    constructor
    · intro hs q hm
      rcases List.mem_cons.mp hm with he | hm
      · subst q
        exact hs.2
      · exact hs.1 q hm
    · intro hs
      exact ⟨fun q hm => hs q (List.mem_cons.mpr (Or.inr hm)),
        hs r (List.mem_cons.mpr (Or.inl rfl))⟩

theorem replay_rows_binding (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (h : replayRows n rs = some (cs, ws)) :
    cs = recordsRows rs ∧ topo (liveIds rs) rs = true := by
  unfold replayRows at h
  cases ht : (topo (liveIds rs) rs && domainCheck n rs) with
  | false => simp [ht] at h
  | true =>
    cases hw : replayWeights n rs with
    | none => simp [ht, hw] at h
    | some w =>
      cases hx : replayExtras rs w with
      | false => simp [ht, hw, hx] at h
      | true =>
        have he : some (recordsRows rs, w) = some (cs, ws) := by
          simpa [ht, hw, hx] using h
        exact ⟨(congrArg Prod.fst (Option.some.inj he)).symm, (and_true_parts ht).1⟩

theorem accepted_records_sound (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs))
    (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws))
    (h : check gate cnf = true) (value : Int → Bool)
    (hc : ∀ r, r ∈ rs → recordCoherent value r) :
    satisfies p.clauses value ↔ recordsSem value rs := by
  have hb := (replay_rows_binding n rs cs ws hr).1
  have hs := byte_check_sound gate cnf n rs p cs ws hg hp hr h value
  rw [hb] at hs
  exact hs.symm.trans (actual_records_rows_sound value rs hc)

theorem nat_mem_iff (x : Nat) (xs : List Nat) :
    natMem x xs = true ↔ x ∈ xs := by
  induction xs with
  | nil => simp [natMem]
  | cons y ys ih =>
    simp only [natMem, Bool.or_eq_true, decide_eq_true_eq, ih, List.mem_cons]

theorem inputs_known_sound (seen xs : List Nat) (h : inputsKnown seen xs = true) :
    ∀ x, x ∈ xs → x ∈ seen := by
  induction xs with
  | nil => simp
  | cons x xs ih =>
    have h' : (natMem x seen && inputsKnown seen xs) = true := h
    have hh := and_true_parts h'
    intro v hm
    rcases List.mem_cons.mp hm with he | hm
    · subst v
      exact (nat_mem_iff x seen).mp hh.1
    · exact ih hh.2 v hm

def agreeOn (a b : Int → Bool) (ids : List Nat) : Prop :=
  ∀ x, x ∈ ids → a (pos x) = b (pos x)

theorem and_value_agree (a b : Int → Bool) (xs : List Nat)
    (h : agreeOn a b xs) :
    andValue (xs.map (fun v => a (pos v))) =
      andValue (xs.map (fun v => b (pos v))) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
    have hx := h x (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih (fun v hm => h v (List.mem_cons.mpr (Or.inr hm)))
    simp only [List.map_cons, andValue, hx, ht]

theorem agree_cons (a b : Int → Bool) (z : Nat) (seen : List Nat)
    (hz : a (pos z) = b (pos z)) (h : agreeOn a b seen) :
    agreeOn a b (z :: seen) := by
  intro v hm
  rcases List.mem_cons.mp hm with he | hm
  · subst v
    exact hz
  · exact h v hm

theorem gate_agreement_step (a b : Int → Bool) (seen : List Nat) (r : Record)
    (h : agreeOn a b seen) (hk : inputsKnown seen (gateInputs r) = true)
    (ha : recordSem a r) (hb : recordSem b r) :
    agreeOn a b (nextSeen seen r) := by
  cases r with
  | live v id => exact h
  | phase z xs => exact h
  | eqGate x y => exact h
  | zero z =>
    change a (pos z) = false at ha
    change b (pos z) = false at hb
    exact agree_cons a b z seen (ha.trans hb.symm) h
  | andGate z xs =>
    change a (pos z) = andValue (xs.map (fun v => a (pos v))) at ha
    change b (pos z) = andValue (xs.map (fun v => b (pos v))) at hb
    have hs : agreeOn a b xs := fun x hm => h x (inputs_known_sound seen xs hk x hm)
    exact agree_cons a b z seen (ha.trans ((and_value_agree a b xs hs).trans hb.symm)) h
  | xorGate z x y =>
    have hxy := inputs_known_sound seen [x,y] hk
    have hx := h x (hxy x (List.mem_cons.mpr (Or.inl rfl)))
    have hy := h y (hxy y (List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inl rfl)))))
    have hz : a (pos z) = b (pos z) := by
      change a (pos z) = (a (pos x)).xor (a (pos y)) at ha
      change b (pos z) = (b (pos x)).xor (b (pos y)) at hb
      rw [ha, hb, hx, hy]
    exact agree_cons a b z seen hz h

theorem topological_agreement (a b : Int → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) (h : agreeOn a b seen)
    (ha : recordsSem a rs) (hb : recordsSem b rs) :
    agreeOn a b (finalSeen seen rs) := by
  induction rs generalizing seen with
  | nil => exact h
  | cons r rs ih =>
    have ht' : ((inputsKnown seen (gateInputs r) &&
        (match gateOutput r with | some z => !natMem z seen | none => true)) &&
        topo (nextSeen seen r) rs) = true := ht
    have hh := and_true_parts ht'
    have hs := gate_agreement_step a b seen r h (and_true_parts hh.1).1
      (ha r (List.mem_cons.mpr (Or.inl rfl))) (hb r (List.mem_cons.mpr (Or.inl rfl)))
    exact ih (nextSeen seen r) hh.2 hs
      (fun q hm => ha q (List.mem_cons.mpr (Or.inr hm)))
      (fun q hm => hb q (List.mem_cons.mpr (Or.inr hm)))

-- At most one positive-literal assignment on the checked live/gate
-- IDs, for a fixed live assignment and satisfying CNF. Existence,
-- coverage of finalSeen versus all DIMACS IDs, and weighted sums
-- are separate obligations.
theorem accepted_assignment_unique (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs))
    (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws))
    (h : check gate cnf = true) (a b : Int → Bool)
    (hca : ∀ r, r ∈ rs → recordCoherent a r)
    (hcb : ∀ r, r ∈ rs → recordCoherent b r)
    (ha : satisfies p.clauses a) (hb : satisfies p.clauses b)
    (hl : agreeOn a b (liveIds rs)) :
    agreeOn a b (finalSeen (liveIds rs) rs) :=
  topological_agreement a b (liveIds rs) rs
    (replay_rows_binding n rs cs ws hr).2 hl
    ((accepted_records_sound gate cnf n rs p cs ws hg hp hr h a hca).mp ha)
    ((accepted_records_sound gate cnf n rs p cs ws hg hp hr h b hcb).mp hb)


-- Exact domain membership, not just a count of allocated IDs.
theorem replay_domain_checked (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (h : replayRows n rs = some (cs, ws)) : domainCheck n rs = true := by
  unfold replayRows at h
  cases ht : (topo (liveIds rs) rs && domainCheck n rs) with
  | false => simp [ht] at h
  | true => exact (and_true_parts ht).2

theorem domain_membership (n : Nat) (rs : List Record)
    (h : domainCheck n rs = true) (x : Nat) :
    x ∈ finalSeen (liveIds rs) rs ↔ x ∈ dimacsIds n := by
  have h' : ((inputsKnown (finalSeen (liveIds rs) rs) (dimacsIds n) &&
      inputsKnown (dimacsIds n) (finalSeen (liveIds rs) rs)) &&
      recordsKnown (dimacsIds n) rs) = true := h
  have hs := and_true_parts (and_true_parts h').1
  exact ⟨inputs_known_sound (dimacsIds n) (finalSeen (liveIds rs) rs) hs.2 x,
    inputs_known_sound (finalSeen (liveIds rs) rs) (dimacsIds n) hs.1 x⟩

theorem dimacs_ids_iff (n x : Nat) :
    x ∈ dimacsIds n ↔ 0 < x ∧ x ≤ n := by
  unfold dimacsIds
  constructor
  · intro hm
    rcases List.mem_map.mp hm with ⟨k, hk, he⟩
    subst x
    exact ⟨Nat.zero_lt_succ k, Nat.succ_le_of_lt (List.mem_range.mp hk)⟩
  · intro h
    cases x with
    | zero => exact False.elim (Nat.lt_irrefl 0 h.1)
    | succ k => exact List.mem_map.mpr ⟨k, List.mem_range.mpr h.2, rfl⟩

theorem accepted_domain_agreement (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (hr : replayRows n rs = some (cs, ws)) (a b : Int → Bool)
    (h : agreeOn a b (finalSeen (liveIds rs) rs)) :
    ∀ x, 0 < x → x ≤ n → a (pos x) = b (pos x) :=
  fun x hx hn => h x ((domain_membership n rs (replay_domain_checked n rs cs ws hr) x).mpr
    ((dimacs_ids_iff n x).mpr ⟨hx, hn⟩))

-- Constructive extension over positive DIMACS IDs. Equality guards
-- do not modify the assignment; they filter the deterministic fiber.
def liftVal (v : Nat → Bool) : Int → Bool
  | .ofNat n => v n
  | .negSucc n => !(v (n + 1))

def setVal (v : Nat → Bool) (z : Nat) (b : Bool) (x : Nat) : Bool :=
  if x = z then b else v x

def gateValue (v : Nat → Bool) : Record → Bool
  | .zero _ => false
  | .andGate _ xs => andValue (xs.map v)
  | .xorGate _ a b => (v a).xor (v b)
  | _ => false

def stepVal (v : Nat → Bool) (r : Record) : Nat → Bool :=
  match gateOutput r with
  | some z => setVal v z (gateValue v r)
  | none => v

def extendVal (v : Nat → Bool) : List Record → Nat → Bool
  | [] => v
  | r :: rs => extendVal (stepVal v r) rs

def defSem (v : Int → Bool) (r : Record) : Prop :=
  match r with
  | .eqGate _ _ => True
  | _ => recordSem v r

def defsSem (v : Int → Bool) (rs : List Record) : Prop :=
  ∀ r, r ∈ rs → defSem v r

def guardTruth (v : Nat → Bool) : List Record → Bool
  | [] => true
  | .eqGate a b :: rs => (v a == v b) && guardTruth v rs
  | _ :: rs => guardTruth v rs

theorem set_val_eq (v : Nat → Bool) (z : Nat) (b : Bool) :
    setVal v z b z = b := by simp [setVal]

theorem set_val_ne (v : Nat → Bool) (z x : Nat) (b : Bool) (h : x ≠ z) :
    setVal v z b x = v x := by simp [setVal, h]

theorem lift_positive (v : Nat → Bool) (x : Nat) :
    liftVal v (pos x) = v x := rfl

theorem lift_coherent (v : Nat → Bool) (x : Nat) (h : 0 < x) :
    liftVal v (-pos x) = !(liftVal v (pos x)) := by
  cases x with
  | zero => exact False.elim (Nat.lt_irrefl 0 h)
  | succ k => rfl

theorem fresh_not_mem (z : Nat) (seen : List Nat) (h : (!natMem z seen) = true) :
    z ∉ seen := by
  intro hm
  have hz := (nat_mem_iff z seen).mpr hm
  rw [hz] at h
  cases h

theorem update_agree (v : Nat → Bool) (z : Nat) (b : Bool) (seen : List Nat)
    (hf : (!natMem z seen) = true) :
    agreeOn (liftVal v) (liftVal (setVal v z b)) seen := by
  intro x hm
  have hn : x ≠ z := fun he => fresh_not_mem z seen hf (he ▸ hm)
  exact (set_val_ne v z x b hn).symm

theorem step_agree (v : Nat → Bool) (r : Record) (seen : List Nat)
    (hf : (match gateOutput r with | some z => !natMem z seen | none => true) = true) :
    agreeOn (liftVal v) (liftVal (stepVal v r)) seen := by
  cases r with
  | live s id => exact fun _ _ => rfl
  | phase z xs => exact fun _ _ => rfl
  | eqGate a b => exact fun _ _ => rfl
  | zero z => exact update_agree v z false seen hf
  | andGate z xs => exact update_agree v z (andValue (xs.map v)) seen hf
  | xorGate z a b => exact update_agree v z ((v a).xor (v b)) seen hf

theorem seen_subset_next (seen : List Nat) (r : Record) :
    ∀ x, x ∈ seen → x ∈ nextSeen seen r := by
  intro x hm
  cases r with
  | live s id => exact hm
  | phase z xs => exact hm
  | eqGate a b => exact hm
  | zero z => exact List.mem_cons.mpr (Or.inr hm)
  | andGate z xs => exact List.mem_cons.mpr (Or.inr hm)
  | xorGate z a b => exact List.mem_cons.mpr (Or.inr hm)

theorem agree_trans (a b c : Int → Bool) (seen : List Nat)
    (h1 : agreeOn a b seen) (h2 : agreeOn b c seen) : agreeOn a c seen :=
  fun x hm => (h1 x hm).trans (h2 x hm)

theorem extend_preserves (v : Nat → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) :
    agreeOn (liftVal v) (liftVal (extendVal v rs)) seen := by
  induction rs generalizing v seen with
  | nil => exact fun _ _ => rfl
  | cons r rs ih =>
    have ht' : ((inputsKnown seen (gateInputs r) &&
        (match gateOutput r with | some z => !natMem z seen | none => true)) &&
        topo (nextSeen seen r) rs) = true := ht
    have hh := and_true_parts ht'
    have hs := step_agree v r seen (and_true_parts hh.1).2
    have he := ih (stepVal v r) (nextSeen seen r) hh.2
    exact agree_trans _ _ _ seen hs (fun x hm => he x (seen_subset_next seen r x hm))

-- Gate truth after a single deterministic update, using freshness
-- and known inputs to ensure that writing the output cannot change
-- the value of its own arguments.
theorem step_def_sound (v : Nat → Bool) (seen : List Nat) (r : Record)
    (hk : inputsKnown seen (gateInputs r) = true)
    (hf : (match gateOutput r with | some z => !natMem z seen | none => true) = true) :
    defSem (liftVal (stepVal v r)) r := by
  cases r with
  | live s id => exact True.intro
  | phase z xs => exact True.intro
  | eqGate a b => exact True.intro
  | zero z => exact set_val_eq v z false
  | andGate z xs =>
    let u := setVal v z (andValue (xs.map v))
    have h1 : agreeOn (liftVal v) (liftVal u) xs :=
      fun x hm => update_agree v z (andValue (xs.map v)) seen hf x
        (inputs_known_sound seen xs hk x hm)
    have h2 := and_value_agree (liftVal v) (liftVal u) xs h1
    change u z = andValue (xs.map u)
    exact (set_val_eq v z (andValue (xs.map v))).trans h2
  | xorGate z a b =>
    let u := setVal v z ((v a).xor (v b))
    have hs := update_agree v z ((v a).xor (v b)) seen hf
    have hxy := inputs_known_sound seen [a,b] hk
    have ha : v a = u a := hs a (hxy a (List.mem_cons.mpr (Or.inl rfl)))
    have hb : v b = u b := hs b (hxy b (List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inl rfl)))))
    change u z = (u a).xor (u b)
    exact (set_val_eq v z ((v a).xor (v b))).trans ((congrArg (fun x => x.xor (v b)) ha).trans (congrArg (fun y => (u a).xor y) hb))

theorem def_sem_transport (a b : Int → Bool) (seen : List Nat) (r : Record)
    (hk : inputsKnown seen (gateInputs r) = true)
    (h : agreeOn a b (nextSeen seen r)) (ha : defSem a r) : defSem b r := by
  cases r with
  | live s id => exact True.intro
  | phase z xs => exact True.intro
  | eqGate x y => exact True.intro
  | zero z =>
    change a (pos z) = false at ha
    exact (h z (List.mem_cons.mpr (Or.inl rfl))).symm.trans ha
  | andGate z xs =>
    change a (pos z) = andValue (xs.map (fun v => a (pos v))) at ha
    have hz := h z (List.mem_cons.mpr (Or.inl rfl))
    have hi : agreeOn a b xs := fun x hm =>
      h x (List.mem_cons.mpr (Or.inr (inputs_known_sound seen xs hk x hm)))
    exact hz.symm.trans (ha.trans (and_value_agree a b xs hi))
  | xorGate z x y =>
    change a (pos z) = (a (pos x)).xor (a (pos y)) at ha
    have hz := h z (List.mem_cons.mpr (Or.inl rfl))
    have hxy := inputs_known_sound seen [x,y] hk
    have hx := h x (List.mem_cons.mpr (Or.inr (hxy x (List.mem_cons.mpr (Or.inl rfl)))))
    have hy := h y (List.mem_cons.mpr (Or.inr (hxy y (List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inl rfl)))))))
    exact hz.symm.trans (ha.trans ((congrArg (fun t => t.xor (a (pos y))) hx).trans (congrArg (fun t => (b (pos x)).xor t) hy)))

theorem extend_defs_sound (v : Nat → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) : defsSem (liftVal (extendVal v rs)) rs := by
  induction rs generalizing v seen with
  | nil => intro r hm; cases hm
  | cons r rs ih =>
    have ht' : ((inputsKnown seen (gateInputs r) &&
        (match gateOutput r with | some z => !natMem z seen | none => true)) &&
        topo (nextSeen seen r) rs) = true := ht
    have hh := and_true_parts ht'
    have hk := (and_true_parts hh.1).1
    have hf := (and_true_parts hh.1).2
    have hstep := step_def_sound v seen r hk hf
    have hp := extend_preserves (stepVal v r) (nextSeen seen r) rs hh.2
    have hr := def_sem_transport _ _ seen r hk hp hstep
    have htail := ih (stepVal v r) (nextSeen seen r) hh.2
    intro q hm
    rcases List.mem_cons.mp hm with he | hm
    · subst q
      exact hr
    · exact htail q hm

theorem records_guard_iff (v : Nat → Bool) (rs : List Record) :
    recordsSem (liftVal v) rs ↔ defsSem (liftVal v) rs ∧ guardTruth v rs = true := by
  induction rs with
  | nil => simp [recordsSem, defsSem, guardTruth]
  | cons r rs ih =>
    have hrec : recordsSem (liftVal v) (r :: rs) ↔
        recordSem (liftVal v) r ∧ recordsSem (liftVal v) rs := by
      constructor
      · intro h
        exact ⟨h r (List.mem_cons.mpr (Or.inl rfl)), fun q hm => h q (List.mem_cons.mpr (Or.inr hm))⟩
      · intro h q hm
        rcases List.mem_cons.mp hm with he | hm
        · subst q
          exact h.1
        · exact h.2 q hm
    have hdef : defsSem (liftVal v) (r :: rs) ↔
        defSem (liftVal v) r ∧ defsSem (liftVal v) rs := by
      constructor
      · intro h
        exact ⟨h r (List.mem_cons.mpr (Or.inl rfl)), fun q hm => h q (List.mem_cons.mpr (Or.inr hm))⟩
      · intro h q hm
        rcases List.mem_cons.mp hm with he | hm
        · subst q
          exact h.1
        · exact h.2 q hm
    rw [hrec, hdef, ih]
    cases r with
    | live s id => exact and_assoc.symm
    | phase z xs => exact and_assoc.symm
    | zero z => exact and_assoc.symm
    | andGate z xs => exact and_assoc.symm
    | xorGate z a b => exact and_assoc.symm
    | eqGate a b =>
      change (v a = v b ∧ (defsSem (liftVal v) rs ∧ guardTruth v rs = true)) ↔
        ((True ∧ defsSem (liftVal v) rs) ∧ ((v a == v b) && guardTruth v rs) = true)
      cases v a <;> cases v b <;> simp

-- The canonical extension satisfies the full record sequence iff its
-- diagonal guard passes. This is not yet a WMC sum theorem.
theorem canonical_guard_iff (v : Nat → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) :
    recordsSem (liftVal (extendVal v rs)) rs ↔ guardTruth (extendVal v rs) rs = true :=
  let h := records_guard_iff (extendVal v rs) rs
  Iff.intro (fun hs => (h.mp hs).2)
    (fun hg => h.mpr ⟨extend_defs_sound v seen rs ht, hg⟩)


-- All row IDs lie inside the accepted finite DIMACS domain.
theorem records_known_sound (ids : List Nat) (rs : List Record)
    (h : recordsKnown ids rs = true) :
    ∀ r, r ∈ rs → ∀ x, x ∈ rowIds r → x ∈ ids := by
  induction rs with
  | nil => intro r hm; cases hm
  | cons r rs ih =>
    have h' : (inputsKnown ids (rowIds r) && recordsKnown ids rs) = true := h
    have hh := and_true_parts h'
    intro q hm x hx
    rcases List.mem_cons.mp hm with he | hm
    · subst q
      exact inputs_known_sound ids (rowIds r) hh.1 x hx
    · exact ih hh.2 q hm x hx

theorem replay_record_ids (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (hr : replayRows n rs = some (cs, ws)) :
    ∀ r, r ∈ rs → ∀ x, x ∈ rowIds r → x ∈ dimacsIds n :=
  let h : ((inputsKnown (finalSeen (liveIds rs) rs) (dimacsIds n) &&
      inputsKnown (dimacsIds n) (finalSeen (liveIds rs) rs)) &&
      recordsKnown (dimacsIds n) rs) = true :=
    replay_domain_checked n rs cs ws hr
  records_known_sound (dimacsIds n) rs (and_true_parts h).2

theorem record_lift_coherent (v : Nat → Bool) (r : Record)
    (h : ∀ x, x ∈ rowIds r → 0 < x) : recordCoherent (liftVal v) r := by
  cases r with
  | live s id => exact True.intro
  | phase z xs => exact True.intro
  | zero z => exact lift_coherent v z (h z (List.mem_cons.mpr (Or.inl rfl)))
  | andGate z xs =>
    exact ⟨lift_coherent v z (h z (List.mem_cons.mpr (Or.inl rfl))),
      fun x hm => lift_coherent v x (h x (List.mem_cons.mpr (Or.inr hm)))⟩
  | xorGate z a b =>
    exact ⟨lift_coherent v z (h z (by simp [rowIds])),
      lift_coherent v a (h a (by simp [rowIds])),
      lift_coherent v b (h b (by simp [rowIds]))⟩
  | eqGate a b =>
    exact ⟨lift_coherent v a (h a (by simp [rowIds])),
      lift_coherent v b (h b (by simp [rowIds]))⟩

theorem accepted_lift_coherent (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (hr : replayRows n rs = some (cs, ws)) (v : Nat → Bool) :
    ∀ r, r ∈ rs → recordCoherent (liftVal v) r :=
  fun r hm => record_lift_coherent v r
    (fun x hx => ((dimacs_ids_iff n x).mp (replay_record_ids n rs cs ws hr r hm x hx)).1)

-- Uniqueness of definition assignments does not require equality
-- guards to pass. This is crucial for the no-model direction.
theorem definition_agreement_step (a b : Int → Bool) (seen : List Nat) (r : Record)
    (h : agreeOn a b seen) (hk : inputsKnown seen (gateInputs r) = true)
    (ha : defSem a r) (hb : defSem b r) :
    agreeOn a b (nextSeen seen r) := by
  cases r with
  | eqGate x y => exact h
  | live s id => exact h
  | phase z xs => exact h
  | zero z => exact gate_agreement_step a b seen (.zero z) h hk ha hb
  | andGate z xs => exact gate_agreement_step a b seen (.andGate z xs) h hk ha hb
  | xorGate z x y => exact gate_agreement_step a b seen (.xorGate z x y) h hk ha hb

theorem topological_defs_agreement (a b : Int → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) (h : agreeOn a b seen)
    (ha : defsSem a rs) (hb : defsSem b rs) :
    agreeOn a b (finalSeen seen rs) := by
  induction rs generalizing seen with
  | nil => exact h
  | cons r rs ih =>
    have ht' : ((inputsKnown seen (gateInputs r) &&
        (match gateOutput r with | some z => !natMem z seen | none => true)) &&
        topo (nextSeen seen r) rs) = true := ht
    have hh := and_true_parts ht'
    have hs := definition_agreement_step a b seen r h (and_true_parts hh.1).1
      (ha r (List.mem_cons.mpr (Or.inl rfl))) (hb r (List.mem_cons.mpr (Or.inl rfl)))
    exact ih (nextSeen seen r) hh.2 hs
      (fun q hm => ha q (List.mem_cons.mpr (Or.inr hm)))
      (fun q hm => hb q (List.mem_cons.mpr (Or.inr hm)))

theorem guard_agreement (a b : Nat → Bool) (ids : List Nat) (rs : List Record)
    (h : agreeOn (liftVal a) (liftVal b) ids)
    (hk : recordsKnown ids rs = true) : guardTruth a rs = guardTruth b rs := by
  induction rs with
  | nil => rfl
  | cons r rs ih =>
    have hk' : (inputsKnown ids (rowIds r) && recordsKnown ids rs) = true := hk
    have hh := and_true_parts hk'
    have ht := ih hh.2
    cases r with
    | live s id => exact ht
    | phase z xs => exact ht
    | zero z => exact ht
    | andGate z xs => exact ht
    | xorGate z x y => exact ht
    | eqGate x y =>
      have hx : a x = b x := h x (inputs_known_sound ids [x,y] hh.1 x (by simp))
      have hy : a y = b y := h y (inputs_known_sound ids [x,y] hh.1 y (by simp))
      change ((a x == a y) && guardTruth a rs) = ((b x == b y) && guardTruth b rs)
      rw [hx, hy, ht]

-- Actual parsed CNF: the constructive witness satisfies it exactly
-- when the evaluated diagonal guard is true.
theorem accepted_canonical_iff (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) :
    satisfies p.clauses (liftVal (extendVal v rs)) ↔
      guardTruth (extendVal v rs) rs = true :=
  (accepted_records_sound gate cnf n rs p cs ws hg hp hr h
    (liftVal (extendVal v rs)) (accepted_lift_coherent n rs cs ws hr (extendVal v rs))).trans
    (canonical_guard_iff v (liveIds rs) rs (replay_rows_binding n rs cs ws hr).2)

theorem accepted_model_canonical_agreement (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v u : Nat → Bool) (hu : satisfies p.clauses (liftVal u))
    (hl : agreeOn (liftVal u) (liftVal v) (liveIds rs)) :
    agreeOn (liftVal u) (liftVal (extendVal v rs)) (dimacsIds n) := by
  have ht := (replay_rows_binding n rs cs ws hr).2
  have hs := (accepted_records_sound gate cnf n rs p cs ws hg hp hr h
    (liftVal u) (accepted_lift_coherent n rs cs ws hr u)).mp hu
  have hd := ((records_guard_iff u rs).mp hs).1
  have ha := topological_defs_agreement (liftVal u) (liftVal (extendVal v rs))
    (liveIds rs) rs ht (agree_trans _ _ _ _ hl (extend_preserves v (liveIds rs) rs ht))
    hd (extend_defs_sound v (liveIds rs) rs ht)
  exact fun x hx => ha x ((domain_membership n rs (replay_domain_checked n rs cs ws hr) x).mpr hx)

-- Existence of a satisfying extension is equivalent to the canonical
-- guard. Uniqueness is modulo the declared finite domain, not all Nat.
theorem accepted_extension_exists_iff (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) :
    (∃ u : Nat → Bool, agreeOn (liftVal u) (liftVal v) (liveIds rs) ∧
      satisfies p.clauses (liftVal u)) ↔ guardTruth (extendVal v rs) rs = true := by
  have ht := (replay_rows_binding n rs cs ws hr).2
  constructor
  · rintro ⟨u, hl, hu⟩
    have ha := accepted_model_canonical_agreement gate cnf n rs p cs ws hg hp hr h v u hu hl
    have hd : ((inputsKnown (finalSeen (liveIds rs) rs) (dimacsIds n) &&
        inputsKnown (dimacsIds n) (finalSeen (liveIds rs) rs)) &&
        recordsKnown (dimacsIds n) rs) = true := replay_domain_checked n rs cs ws hr
    have he := guard_agreement u (extendVal v rs) (dimacsIds n) rs ha (and_true_parts hd).2
    have hs := (accepted_records_sound gate cnf n rs p cs ws hg hp hr h
      (liftVal u) (accepted_lift_coherent n rs cs ws hr u)).mp hu
    exact he.symm.trans ((records_guard_iff u rs).mp hs).2
  · intro hc
    exact ⟨extendVal v rs, fun x hx => (extend_preserves v (liveIds rs) rs ht x hx).symm,
      (accepted_canonical_iff gate cnf n rs p cs ws hg hp hr h v).mpr hc⟩

theorem accepted_guard_rejects (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) (hf : guardTruth (extendVal v rs) rs = false) :
    ¬ (∃ u : Nat → Bool, agreeOn (liftVal u) (liftVal v) (liveIds rs) ∧
      satisfies p.clauses (liftVal u)) := by
  intro he
  have ht := (accepted_extension_exists_iff gate cnf n rs p cs ws hg hp hr h v).mp he
  rw [hf] at ht
  cases ht


-- Exact finite assignment representation: bit position k represents
-- DIMACS variable k+1. Values outside the declared domain are ignored.
def bitsAt : List Bool → Nat → Bool
  | [], _ => false
  | b :: _, 0 => b
  | _ :: bs, k+1 => bitsAt bs k

def packBits (v : Nat → Bool) : Nat → List Bool
  | 0 => []
  | n+1 => v 0 :: packBits (fun k => v (k+1)) n

def decodeBits (bits : List Bool) (x : Nat) : Bool :=
  bitsAt bits (x-1)

theorem pack_length (v : Nat → Bool) (n : Nat) :
    (packBits v n).length = n := by
  induction n generalizing v with
  | zero => rfl
  | succ n ih => simp only [packBits, List.length_cons, ih]

theorem pack_at (v : Nat → Bool) (n k : Nat) (hk : k < n) :
    bitsAt (packBits v n) k = v k := by
  induction n generalizing v k with
  | zero => exact False.elim (Nat.not_lt_zero k hk)
  | succ n ih =>
    cases k with
    | zero => rfl
    | succ k => exact ih (fun j => v (j+1)) k (Nat.lt_of_succ_lt_succ hk)

theorem bits_ext (xs ys : List Bool) (hl : xs.length = ys.length)
    (h : ∀ k, k < xs.length → bitsAt xs k = bitsAt ys k) : xs = ys := by
  induction xs generalizing ys with
  | nil =>
    cases ys with
    | nil => rfl
    | cons y ys =>
      change 0 = Nat.succ ys.length at hl
      cases hl
  | cons x xs ih =>
    cases ys with
    | nil =>
      change Nat.succ xs.length = 0 at hl
      cases hl
    | cons y ys =>
      have he : x = y := h 0 (Nat.zero_lt_succ xs.length)
      have ht : xs = ys := ih ys (Nat.succ.inj hl)
        (fun k hk => h (k+1) (Nat.succ_lt_succ hk))
      exact (congrArg (fun b => b :: xs) he).trans
        (congrArg (fun tail => y :: tail) ht)

theorem decode_pack_agree (v : Nat → Bool) (n : Nat) :
    agreeOn (liftVal (decodeBits (packBits (fun k => v (k+1)) n))) (liftVal v) (dimacsIds n) := by
  intro x hx
  have h := (dimacs_ids_iff n x).mp hx
  cases x with
  | zero => exact False.elim (Nat.lt_irrefl 0 h.1)
  | succ k =>
    exact pack_at (fun j => v (j+1)) n k h.2

theorem bits_eq_of_domain (bits : List Bool) (v : Nat → Bool) (n : Nat)
    (hl : bits.length = n)
    (h : agreeOn (liftVal (decodeBits bits)) (liftVal v) (dimacsIds n)) :
    bits = packBits (fun k => v (k+1)) n := by
  apply bits_ext bits (packBits (fun k => v (k+1)) n)
  · exact hl.trans (pack_length _ _).symm
  · intro k hk
    have hn : k < n := hl ▸ hk
    have hv := h (k+1) ((dimacs_ids_iff n (k+1)).mpr ⟨Nat.zero_lt_succ k, hn⟩)
    exact hv.trans (pack_at (fun j => v (j+1)) n k hn).symm

def liveMatch (a b : Nat → Bool) : List Nat → Bool
  | [] => true
  | x :: xs => (a x == b x) && liveMatch a b xs

theorem bool_match (a b : Bool) : (a == b) = true ↔ a = b := by
  cases a <;> cases b <;> decide

theorem live_match_iff (a b : Nat → Bool) (ids : List Nat) :
    liveMatch a b ids = true ↔ agreeOn (liftVal a) (liftVal b) ids := by
  induction ids with
  | nil => simp [liveMatch, agreeOn]
  | cons x xs ih =>
    constructor
    · intro h
      have hh := and_true_parts (show ((a x == b x) && liveMatch a b xs) = true from h)
      exact agree_cons _ _ x xs ((bool_match (a x) (b x)).mp hh.1) (ih.mp hh.2)
    · intro h
      have hx := (bool_match (a x) (b x)).mpr (h x (List.mem_cons.mpr (Or.inl rfl)))
      have ht := ih.mpr (fun y hm => h y (List.mem_cons.mpr (Or.inr hm)))
      change ((a x == b x) && liveMatch a b xs) = true
      rw [hx, ht]
      rfl

theorem record_sem_agree (a b : Int → Bool) (r : Record)
    (h : agreeOn a b (rowIds r)) : recordSem a r ↔ recordSem b r := by
  cases r with
  | live s id => exact Iff.rfl
  | phase z xs => exact Iff.rfl
  | zero z =>
    change a (pos z) = false ↔ b (pos z) = false
    rw [h z (by simp [rowIds])]
  | andGate z xs =>
    have hz := h z (List.mem_cons.mpr (Or.inl rfl))
    have hi : agreeOn a b xs := fun x hm => h x (List.mem_cons.mpr (Or.inr hm))
    change a (pos z) = andValue (xs.map (fun v => a (pos v))) ↔
      b (pos z) = andValue (xs.map (fun v => b (pos v)))
    rw [hz, and_value_agree a b xs hi]
  | xorGate z x y =>
    change a (pos z) = (a (pos x)).xor (a (pos y)) ↔
      b (pos z) = (b (pos x)).xor (b (pos y))
    rw [h z (by simp [rowIds]), h x (by simp [rowIds]), h y (by simp [rowIds])]
  | eqGate x y =>
    change a (pos x) = a (pos y) ↔ b (pos x) = b (pos y)
    rw [h x (by simp [rowIds]), h y (by simp [rowIds])]

theorem accepted_sat_agree (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (a b : Nat → Bool) (ha : agreeOn (liftVal a) (liftVal b) (dimacsIds n)) :
    satisfies p.clauses (liftVal a) ↔ satisfies p.clauses (liftVal b) := by
  have h1 := accepted_records_sound gate cnf n rs p cs ws hg hp hr h
    (liftVal a) (accepted_lift_coherent n rs cs ws hr a)
  have h2 := accepted_records_sound gate cnf n rs p cs ws hg hp hr h
    (liftVal b) (accepted_lift_coherent n rs cs ws hr b)
  have hs : recordsSem (liftVal a) rs ↔ recordsSem (liftVal b) rs := by
    constructor
    · intro hs r hm
      exact (record_sem_agree (liftVal a) (liftVal b) r
        (fun x hx => ha x (replay_record_ids n rs cs ws hr r hm x hx))).mp (hs r hm)
    · intro hs r hm
      exact (record_sem_agree (liftVal a) (liftVal b) r
        (fun x hx => ha x (replay_record_ids n rs cs ws hr r hm x hx))).mpr (hs r hm)
  exact h1.trans (hs.trans h2.symm)

theorem accepted_live_in_domain (n : Nat) (rs : List Record) (cs : List (List Int)) (ws : List Nat)
    (hr : replayRows n rs = some (cs, ws)) :
    ∀ x, x ∈ liveIds rs → x ∈ dimacsIds n := by
  have hs : ∀ (seen : List Nat) (rs : List Record) (x : Nat),
      x ∈ seen → x ∈ finalSeen seen rs := by
    intro seen records
    induction records generalizing seen with
    | nil => exact fun x hm => hm
    | cons r rest ih =>
      exact fun x hm => ih (nextSeen seen r) x (seen_subset_next seen r x hm)
  exact fun x hx => (domain_membership n rs (replay_domain_checked n rs cs ws hr) x).mp (hs (liveIds rs) rs x hx)

-- Enumerate all 2^n bit vectors exactly once by their leading bit.
-- No exponential enumeration is executed for real benchmark files.
def sumBits {A : Type} [Add A] : Nat → (List Bool → A) → A
  | 0, f => f []
  | n+1, f => sumBits n (fun xs => f (false :: xs)) +
      sumBits n (fun xs => f (true :: xs))

theorem sum_bits_zero {A : Type} [Zero A] [Add A] (zl : ∀ a : A, 0 + a = a)
    (n : Nat) (f : List Bool → A) (h : ∀ xs, xs.length = n → f xs = 0) :
    sumBits n f = 0 := by
  induction n generalizing f with
  | zero => exact h [] rfl
  | succ n ih =>
    change sumBits n (fun xs => f (false :: xs)) +
      sumBits n (fun xs => f (true :: xs)) = 0
    rw [ih (fun xs => f (false :: xs)) (fun xs hx => h (false :: xs) (congrArg Nat.succ hx)),
      ih (fun xs => f (true :: xs)) (fun xs hx => h (true :: xs) (congrArg Nat.succ hx))]
    exact zl 0

theorem sum_bits_single {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (target : List Bool) (f : List Bool → A) (w : A)
    (hw : f target = w)
    (hz : ∀ xs, xs.length = target.length → xs ≠ target → f xs = 0) :
    sumBits target.length f = w := by
  induction target generalizing f with
  | nil => exact hw
  | cons b bs ih =>
    cases b with
    | false =>
      have h1 := ih (fun xs => f (false :: xs)) hw
        (fun xs hl hn => hz (false :: xs) (congrArg Nat.succ hl)
          (fun he => hn (List.cons.inj he).2))
      have h2 := sum_bits_zero zl bs.length (fun xs => f (true :: xs))
        (fun xs hl => hz (true :: xs) (congrArg Nat.succ hl) (fun he => by cases he))
      change sumBits bs.length (fun xs => f (false :: xs)) +
        sumBits bs.length (fun xs => f (true :: xs)) = w
      rw [h1, h2]
      exact zr w
    | true =>
      have h1 := sum_bits_zero zl bs.length (fun xs => f (false :: xs))
        (fun xs hl => hz (false :: xs) (congrArg Nat.succ hl) (fun he => by cases he))
      have h2 := ih (fun xs => f (true :: xs)) hw
        (fun xs hl hn => hz (true :: xs) (congrArg Nat.succ hl)
          (fun he => hn (List.cons.inj he).2))
      change sumBits bs.length (fun xs => f (false :: xs)) +
        sumBits bs.length (fun xs => f (true :: xs)) = w
      rw [h1, h2]
      exact zl w

def fiberTerm {A : Type} [Zero A] (p : ParsedCnf) (rs : List Record)
    (v : Nat → Bool) (weight : List Bool → A) (bits : List Bool) : A :=
  if liveMatch (decodeBits bits) v (liveIds rs) &&
      cnfTruth (liftVal (decodeBits bits)) p.clauses then weight bits else 0

def actualFiber {A : Type} [Zero A] [Add A] (n : Nat) (p : ParsedCnf)
    (rs : List Record) (v : Nat → Bool) (weight : List Bool → A) : A :=
  sumBits n (fiberTerm p rs v weight)

-- Actual parsed CNF finite weighted fiber, for any exact weight
-- function on its declared bit vectors. The live mask fixes x.
-- The only possible contributing vector is the canonical extension.
theorem accepted_weighted_fiber {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) (weight : List Bool → A) :
    actualFiber n p rs v weight =
      if guardTruth (extendVal v rs) rs then
        weight (packBits (fun k => extendVal v rs (k+1)) n) else 0 := by
  let u := extendVal v rs
  let target := packBits (fun k => u (k+1)) n
  have hlen : target.length = n := pack_length _ _
  have ht := (replay_rows_binding n rs cs ws hr).2
  have hda := decode_pack_agree u n
  have hl : agreeOn (liftVal (decodeBits target)) (liftVal v) (liveIds rs) :=
    fun x hx => (hda x (accepted_live_in_domain n rs cs ws hr x hx)).trans
      ((extend_preserves v (liveIds rs) rs ht x hx).symm)
  have hm := (live_match_iff (decodeBits target) v (liveIds rs)).mpr hl
  have he : cnfTruth (liftVal (decodeBits target)) p.clauses =
      guardTruth u rs := by
    apply bool_true_iff_eq
    exact (cnf_truth_iff (liftVal (decodeBits target)) p.clauses).trans
      ((accepted_sat_agree gate cnf n rs p cs ws hg hp hr h (decodeBits target) u hda).trans
        (accepted_canonical_iff gate cnf n rs p cs ws hg hp hr h v))
  have htarget : fiberTerm p rs v weight target =
      (if guardTruth u rs then weight target else 0) := by
    unfold fiberTerm
    rw [hm, he]
    rfl
  have hzero : ∀ bits, bits.length = target.length → bits ≠ target →
      fiberTerm p rs v weight bits = 0 := by
    intro bits hb hn
    unfold fiberTerm
    cases hm' : (liveMatch (decodeBits bits) v (liveIds rs) &&
        cnfTruth (liftVal (decodeBits bits)) p.clauses) with
    | false => rfl
    | true =>
      have hh := and_true_parts hm'
      have hmodel := (cnf_truth_iff (liftVal (decodeBits bits)) p.clauses).mp hh.2
      have hlive := (live_match_iff (decodeBits bits) v (liveIds rs)).mp hh.1
      have ha := accepted_model_canonical_agreement gate cnf n rs p cs ws hg hp hr h
        v (decodeBits bits) hmodel hlive
      exact False.elim (hn (bits_eq_of_domain bits u n (hb.trans hlen) ha))
  have hf := sum_bits_single zl zr target (fiberTerm p rs v weight)
    (if guardTruth u rs then weight target else 0) htarget hzero
  rw [hlen] at hf
  exact hf

theorem accepted_fiber_count (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) :
    actualFiber n p rs v (fun _ => (1 : Nat)) =
      if guardTruth (extendVal v rs) rs then 1 else 0 :=
  accepted_weighted_fiber Nat.zero_add Nat.add_zero gate cnf n rs p cs ws hg hp hr h v (fun _ => 1)


-- Literal weight products in declared DIMACS order. Unlisted literal
-- weights must be supplied as the multiplicative unit by the caller.
-- This is an exact algebraic interface, not a decimal parser proof.
def chosenLiteral (v : Nat → Bool) (z : Nat) : Int :=
  if v z then pos z else -pos z

def literalProduct {A : Type} [One A] [Mul A]
    (weight : Int → A) (v : Nat → Bool) : List Nat → A
  | [] => 1
  | z :: zs => weight (chosenLiteral v z) * literalProduct weight v zs

theorem literal_product_agree {A : Type} [One A] [Mul A]
    (weight : Int → A) (a b : Nat → Bool) (ids : List Nat)
    (h : agreeOn (liftVal a) (liftVal b) ids) :
    literalProduct weight a ids = literalProduct weight b ids := by
  induction ids with
  | nil => rfl
  | cons z zs ih =>
    have hz : a z = b z := h z (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih (fun x hm => h x (List.mem_cons.mpr (Or.inr hm)))
    change weight (if a z then pos z else -pos z) * literalProduct weight a zs =
      weight (if b z then pos z else -pos z) * literalProduct weight b zs
    rw [hz, ht]

theorem accepted_literal_fiber {A : Type} [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) (weight : Int → A) :
    actualFiber n p rs v (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n)) =
      if guardTruth (extendVal v rs) rs then
        literalProduct weight (extendVal v rs) (dimacsIds n) else 0 := by
  have hf := accepted_weighted_fiber zl zr gate cnf n rs p cs ws hg hp hr h v
    (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n))
  have ha := literal_product_agree weight
    (decodeBits (packBits (fun k => extendVal v rs (k+1)) n))
    (extendVal v rs) (dimacsIds n) (decode_pack_agree (extendVal v rs) n)
  exact hf.trans (congrArg (fun x => if guardTruth (extendVal v rs) rs then x else 0) ha)

-- Keep only the positive phase literals selected by the canonical
-- assignment, in the same declared-ID order as literalProduct.
def selectedPhaseProduct {A : Type} [One A] [Mul A]
    (weight : Int → A) (v : Nat → Bool) (weighted : List Nat) : List Nat → A
  | [] => 1
  | z :: zs =>
    if natMem z weighted && v z then
      weight (pos z) * selectedPhaseProduct weight v weighted zs
    else selectedPhaseProduct weight v weighted zs

theorem chosen_literal_false (v : Nat → Bool) (z : Nat) (h : v z = false) :
    chosenLiteral v z = -pos z := by
  unfold chosenLiteral
  rw [h]
  rfl

theorem chosen_literal_true (v : Nat → Bool) (z : Nat) (h : v z = true) :
    chosenLiteral v z = pos z := by
  unfold chosenLiteral
  rw [h]
  rfl

theorem literal_product_phase {A : Type} [One A] [Mul A]
    (ol : ∀ a : A, 1 * a = a)
    (weight : Int → A) (v : Nat → Bool) (weighted ids : List Nat)
    (hn : ∀ z, z ∈ ids → weight (-pos z) = 1)
    (hu : ∀ z, z ∈ ids → natMem z weighted = false → weight (pos z) = 1) :
    literalProduct weight v ids = selectedPhaseProduct weight v weighted ids := by
  induction ids with
  | nil => rfl
  | cons z zs ih =>
    have ht := ih
      (fun x hm => hn x (List.mem_cons.mpr (Or.inr hm)))
      (fun x hm hf => hu x (List.mem_cons.mpr (Or.inr hm)) hf)
    have hneg := hn z (List.mem_cons.mpr (Or.inl rfl))
    have hunit := hu z (List.mem_cons.mpr (Or.inl rfl))
    change weight (chosenLiteral v z) * literalProduct weight v zs =
      (if natMem z weighted && v z then
        weight (pos z) * selectedPhaseProduct weight v weighted zs
       else selectedPhaseProduct weight v weighted zs)
    rw [ht]
    cases hv : v z with
    | false =>
      rw [chosen_literal_false v z hv, hneg]
      cases natMem z weighted <;> exact ol _
    | true =>
      rw [chosen_literal_true v z hv]
      cases hw : natMem z weighted with
      | false =>
        rw [hunit hw]
        exact ol _
      | true => rfl

-- Specialization of the actual weighted fiber to a phase-weight
-- product. The unit assumptions are explicit; no assertion that
-- parsed decimal strings already equal ideal complex phases.
theorem accepted_phase_product_fiber {A : Type} [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0 + a = a) (zr : ∀ a : A, a + 0 = a)
    (ol : ∀ a : A, 1 * a = a)
    (gate cnf : List Nat) (n : Nat)
    (rs : List Record) (p : ParsedCnf) (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (v : Nat → Bool) (weight : Int → A)
    (hn : ∀ z, z ∈ dimacsIds n → weight (-pos z) = 1)
    (hu : ∀ z, z ∈ dimacsIds n → natMem z ws = false → weight (pos z) = 1) :
    actualFiber n p rs v (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n)) =
      if guardTruth (extendVal v rs) rs then
        selectedPhaseProduct weight (extendVal v rs) ws (dimacsIds n) else 0 :=
  (accepted_literal_fiber zl zr gate cnf n rs p cs ws hg hp hr h v weight).trans
    (congrArg (fun x => if guardTruth (extendVal v rs) rs then x else 0)
      (literal_product_phase ol weight (extendVal v rs) ws (dimacsIds n) hn hu))


-- The runtime has checked the distinct live projection and phase
-- declarations. Derive the exact extra admission premise.
theorem replay_extras_checked (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat)
    (h : replayRows n rs = some (cs, ws)) : replayExtras rs ws = true := by
  unfold replayRows at h
  cases ht : (topo (liveIds rs) rs && domainCheck n rs) with
  | false => simp [ht] at h
  | true =>
    cases hw : replayWeights n rs with
    | none => simp [ht, hw] at h
    | some w =>
      cases hx : replayExtras rs w with
      | false => simp [ht, hw, hx] at h
      | true =>
        have he : some (recordsRows rs, w) = some (cs, ws) := by
          simpa [ht, hw, hx] using h
        have hws : w = ws := congrArg Prod.snd (Option.some.inj he)
        exact (congrArg (replayExtras rs) hws).symm.trans hx

theorem nat_list_eq_iff (xs ys : List Nat) :
    natListEq xs ys = true ↔ xs = ys := by
  induction xs generalizing ys with
  | nil => cases ys <;> simp [natListEq]
  | cons x xs ih =>
    cases ys with
    | nil => simp [natListEq]
    | cons y ys =>
      simp only [natListEq, Bool.and_eq_true, decide_eq_true_eq, ih, List.cons.injEq]

theorem replay_live_unique (n : Nat) (rs : List Record) (cs : List (List Int))
    (ws : List Nat) (hr : replayRows n rs = some (cs, ws)) :
    uniqueIds (liveIds rs) = true :=
  (and_true_parts (and_true_parts (show
    ((uniqueIds (liveIds rs) && natListEq ws (phaseIds rs).reverse) &&
      phaseRecordsOK rs rs) = true from replay_extras_checked n rs cs ws hr)).1).1

theorem replay_phase_ids (n : Nat) (rs : List Record) (cs : List (List Int))
    (ws : List Nat) (hr : replayRows n rs = some (cs, ws)) :
    ws = (phaseIds rs).reverse :=
  (nat_list_eq_iff ws (phaseIds rs).reverse).mp
    (and_true_parts (and_true_parts (show
      ((uniqueIds (liveIds rs) && natListEq ws (phaseIds rs).reverse) &&
        phaseRecordsOK rs rs) = true from replay_extras_checked n rs cs ws hr)).1).2

-- Compact live bit vector uses record order, independently of
-- DIMACS allocation order. Decoding outside its live IDs is arbitrary.
def decodeLive : List Nat → List Bool → Nat → Bool
  | z :: zs, b :: bs => fun x => if x = z then b else decodeLive zs bs x
  | _, _ => fun _ => false

theorem projection_agree (a b : Nat → Bool) (ids : List Nat)
    (h : agreeOn (liftVal a) (liftVal b) ids) : ids.map a = ids.map b := by
  induction ids with
  | nil => rfl
  | cons z zs ih =>
    have hz : a z = b z := h z (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih (fun x hm => h x (List.mem_cons.mpr (Or.inr hm)))
    exact (congrArg (fun x => x :: zs.map a) hz).trans
      (congrArg (fun tail => b z :: tail) ht)

theorem projection_decode (ids : List Nat) (bits : List Bool)
    (hu : uniqueIds ids = true) (hl : bits.length = ids.length) :
    ids.map (decodeLive ids bits) = bits := by
  induction ids generalizing bits with
  | nil =>
    cases bits with
    | nil => rfl
    | cons b bs => cases hl
  | cons z zs ih =>
    cases bits with
    | nil => cases hl
    | cons b bs =>
      have hh := and_true_parts (show (!natMem z zs && uniqueIds zs) = true from hu)
      have hs : agreeOn (liftVal (decodeLive (z :: zs) (b :: bs)))
          (liftVal (decodeLive zs bs)) zs := by
        intro x hx
        have hn : x ≠ z := fun he => fresh_not_mem z zs hh.1 (he ▸ hx)
        change (if x = z then b else decodeLive zs bs x) = decodeLive zs bs x
        simp [hn]
      have ht := (projection_agree _ _ zs hs).trans (ih bs hh.2 (Nat.succ.inj hl))
      change (if z = z then b else decodeLive zs bs z) ::
        zs.map (decodeLive (z :: zs) (b :: bs)) = b :: bs
      have hz : (if z = z then b else decodeLive zs bs z) = b := by simp
      rw [hz, ht]

theorem decode_projection (ids : List Nat) (v : Nat → Bool) :
    agreeOn (liftVal (decodeLive ids (ids.map v))) (liftVal v) ids := by
  induction ids with
  | nil => intro x hx; cases hx
  | cons z zs ih =>
    intro x hx
    change (if x = z then v z else decodeLive zs (zs.map v) x) = v x
    by_cases he : x = z
    · subst x
      simp
    · have hn : (if x = z then v z else decodeLive zs (zs.map v) x) =
          decodeLive zs (zs.map v) x := by simp [he]
      rw [hn]
      rcases List.mem_cons.mp hx with he' | hm
      · exact False.elim (he he')
      · exact ih x hm

theorem live_projection_unique (ids : List Nat) (bits : List Bool) (v : Nat → Bool)
    (hu : uniqueIds ids = true) (hl : bits.length = ids.length)
    (hm : liveMatch v (decodeLive ids bits) ids = true) :
    bits = ids.map v :=
  (projection_decode ids bits hu hl).symm.trans
    (projection_agree _ _ ids (fun x hx => ((live_match_iff v (decodeLive ids bits) ids).mp hm x hx).symm))

-- Sum congruence and finite Fubini for any additive type satisfying
-- the four-term interchange law (in particular complex addition).
theorem sum_bits_congr {A : Type} [Add A] (n : Nat) (f g : List Bool → A)
    (h : ∀ xs, xs.length = n → f xs = g xs) : sumBits n f = sumBits n g := by
  induction n generalizing f g with
  | zero => exact h [] rfl
  | succ n ih =>
    change sumBits n (fun xs => f (false :: xs)) + sumBits n (fun xs => f (true :: xs)) =
      sumBits n (fun xs => g (false :: xs)) + sumBits n (fun xs => g (true :: xs))
    rw [ih _ _ (fun xs hx => h (false :: xs) (congrArg Nat.succ hx)),
      ih _ _ (fun xs hx => h (true :: xs) (congrArg Nat.succ hx))]

theorem sum_bits_add {A : Type} [Add A]
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (n : Nat) (f g : List Bool → A) :
    sumBits n (fun xs => f xs + g xs) = sumBits n f + sumBits n g := by
  induction n generalizing f g with
  | zero => rfl
  | succ n ih =>
    change sumBits n (fun xs => f (false :: xs) + g (false :: xs)) +
      sumBits n (fun xs => f (true :: xs) + g (true :: xs)) =
      (sumBits n (fun xs => f (false :: xs)) + sumBits n (fun xs => f (true :: xs))) +
      (sumBits n (fun xs => g (false :: xs)) + sumBits n (fun xs => g (true :: xs)))
    rw [ih, ih]
    exact shuffle _ _ _ _

theorem sum_bits_swap {A : Type} [Add A]
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (m n : Nat) (f : List Bool → List Bool → A) :
    sumBits m (fun xs => sumBits n (f xs)) =
      sumBits n (fun ys => sumBits m (fun xs => f xs ys)) := by
  induction m generalizing f with
  | zero => rfl
  | succ m ih =>
    change sumBits m (fun xs => sumBits n (f (false :: xs))) +
      sumBits m (fun xs => sumBits n (f (true :: xs))) =
      sumBits n (fun ys =>
        sumBits m (fun xs => f (false :: xs) ys) +
        sumBits m (fun xs => f (true :: xs) ys))
    rw [ih (fun xs ys => f (false :: xs) ys), ih (fun xs ys => f (true :: xs) ys)]
    exact (sum_bits_add shuffle n _ _).symm

def totalWmc {A : Type} [Zero A] [Add A] (n : Nat) (p : ParsedCnf)
    (weight : List Bool → A) : A :=
  sumBits n (fun bits => if cnfTruth (liftVal (decodeBits bits)) p.clauses then weight bits else 0)

-- For each DIMACS bit vector there is exactly one matching compact
-- live vector. This proves the partition without enumerating live
-- variables redundantly or assuming the solver counts correctly.
theorem live_partition_term {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (p : ParsedCnf) (rs : List Record) (weight : List Bool → A)
    (bits : List Bool) (hu : uniqueIds (liveIds rs) = true) :
    sumBits (liveIds rs).length
      (fun xs => fiberTerm p rs (decodeLive (liveIds rs) xs) weight bits) =
      (if cnfTruth (liftVal (decodeBits bits)) p.clauses then weight bits else 0) := by
  let ids := liveIds rs
  let target := ids.map (decodeBits bits)
  have hlen : target.length = ids.length := List.length_map (decodeBits bits)
  have ha := decode_projection ids (decodeBits bits)
  have hm : liveMatch (decodeBits bits) (decodeLive ids target) ids = true :=
    (live_match_iff _ _ ids).mpr (fun x hx => (ha x hx).symm)
  have htarget : fiberTerm p rs (decodeLive ids target) weight bits =
      (if cnfTruth (liftVal (decodeBits bits)) p.clauses then weight bits else 0) := by
    unfold fiberTerm
    rw [hm]
    rfl
  have hz : ∀ xs, xs.length = target.length → xs ≠ target →
      fiberTerm p rs (decodeLive ids xs) weight bits = 0 := by
    intro xs hx hn
    unfold fiberTerm
    cases hmatch : liveMatch (decodeBits bits) (decodeLive ids xs) ids with
    | false => rfl
    | true =>
      exact False.elim (hn (live_projection_unique ids xs (decodeBits bits) hu (hx.trans hlen) hmatch))
  have hsum := sum_bits_single zl zr target
    (fun xs => fiberTerm p rs (decodeLive ids xs) weight bits) _ htarget hz
  rw [hlen] at hsum
  exact hsum

theorem total_wmc_partition {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (n : Nat) (p : ParsedCnf) (rs : List Record) (weight : List Bool → A)
    (hu : uniqueIds (liveIds rs) = true) :
    totalWmc n p weight = sumBits (liveIds rs).length
      (fun xs => actualFiber n p rs (decodeLive (liveIds rs) xs) weight) := by
  have hsum := sum_bits_swap shuffle (liveIds rs).length n
    (fun xs bits => fiberTerm p rs (decodeLive (liveIds rs) xs) weight bits)
  apply Eq.symm
  exact hsum.trans (sum_bits_congr n _ _ (fun bits _ =>
    live_partition_term zl zr p rs weight bits hu))

theorem accepted_total_wmc {A : Type} [Zero A] [Add A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (gate cnf : List Nat) (n : Nat) (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (weight : List Bool → A) :
    totalWmc n p weight =
      sumBits (liveIds rs).length (fun xs =>
        let u := extendVal (decodeLive (liveIds rs) xs) rs
        if guardTruth u rs then weight (packBits (fun k => u (k+1)) n) else 0) :=
  (total_wmc_partition zl zr shuffle n p rs weight (replay_live_unique n rs cs ws hr)).trans
    (sum_bits_congr (liveIds rs).length _ _ (fun xs _ =>
      accepted_weighted_fiber zl zr gate cnf n rs p cs ws hg hp hr h
        (decodeLive (liveIds rs) xs) weight))

theorem accepted_total_phase_product {A : Type} [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (ol : ∀ a : A, 1*a=a)
    (gate cnf : List Nat) (n : Nat) (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (weight : Int → A)
    (hn : ∀ z, z ∈ dimacsIds n → weight (-pos z) = 1)
    (hu : ∀ z, z ∈ dimacsIds n → natMem z ws = false → weight (pos z) = 1) :
    totalWmc n p (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n)) =
      sumBits (liveIds rs).length (fun xs =>
        let u := extendVal (decodeLive (liveIds rs) xs) rs
        if guardTruth u rs then selectedPhaseProduct weight u ws (dimacsIds n) else 0) :=
  (total_wmc_partition zl zr shuffle n p rs
    (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n))
    (replay_live_unique n rs cs ws hr)).trans
    (sum_bits_congr (liveIds rs).length _ _ (fun xs _ =>
      accepted_phase_product_fiber zl zr ol gate cnf n rs p cs ws hg hp hr h
        (decodeLive (liveIds rs) xs) weight hn hu))

-- Phase output is linked to an actual AND record, with each source
-- variable independently mapped to a live DIMACS ID.
theorem and_witness_sound (z : Nat) (ids : List Nat) (rs : List Record)
    (h : andWitness z ids rs = true) : Record.andGate z ids ∈ rs := by
  induction rs with
  | nil => cases h
  | cons r rs ih =>
    cases r with
    | live s id => exact List.mem_cons.mpr (Or.inr (ih h))
    | zero q => exact List.mem_cons.mpr (Or.inr (ih h))
    | xorGate q a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | eqGate a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | phase q src => exact List.mem_cons.mpr (Or.inr (ih h))
    | andGate q xs =>
      have hh : (((@decide (z = q) (Nat.decEq z q)) && natListEq ids xs) ||
          andWitness z ids rs) = true := h
      have hor : ((@decide (z = q) (Nat.decEq z q)) && natListEq ids xs) = true ∨
          andWitness z ids rs = true := by
        simpa only [Bool.or_eq_true] using hh
      rcases hor with hm | ht
      · have hp := and_true_parts hm
        have hq : z = q := of_decide_eq_true hp.1
        have hxs := (nat_list_eq_iff ids xs).mp hp.2
        subst q
        subst xs
        exact List.mem_cons.mpr (Or.inl rfl)
      · exact List.mem_cons.mpr (Or.inr (ih ht))

theorem phase_records_sound (all rs : List Record) (h : phaseRecordsOK all rs = true) :
    ∀ r, r ∈ rs → phaseRecordOK all r = true := by
  induction rs with
  | nil => intro r hm; cases hm
  | cons r rs ih =>
    have hh := and_true_parts (show (phaseRecordOK all r && phaseRecordsOK all rs) = true from h)
    intro q hm
    rcases List.mem_cons.mp hm with he | ht
    · subst q
      exact hh.1
    · exact ih hh.2 q ht

theorem replay_phase_binding (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat) (hr : replayRows n rs = some (cs, ws))
    (z : Nat) (source : List Nat) (hm : Record.phase z source ∈ rs) :
    ∃ ids : List Nat, sourceIds rs source = some ids ∧
      Record.andGate z ids ∈ rs := by
  have he : ((uniqueIds (liveIds rs) && natListEq ws (phaseIds rs).reverse) &&
      phaseRecordsOK rs rs) = true := replay_extras_checked n rs cs ws hr
  have hs := phase_records_sound rs rs (and_true_parts he).2 (.phase z source) hm
  change (match sourceIds rs source with
    | some ids => andWitness z ids rs
    | none => false) = true at hs
  cases hmap : sourceIds rs source with
  | none => rw [hmap] at hs; cases hs
  | some ids =>
    rw [hmap] at hs
    exact ⟨ids, rfl, and_witness_sound z ids rs hs⟩

theorem source_dimacs_live (s id : Nat) (rs : List Record)
    (h : sourceDimacs s rs = some id) : id ∈ liveIds rs := by
  induction rs with
  | nil => cases h
  | cons r rs ih =>
    cases r with
    | live v q =>
      change (if s == v then some q else sourceDimacs s rs) = some id at h
      cases he : (s == v) with
      | false =>
        have ht : sourceDimacs s rs = some id := by simpa [he] using h
        exact List.mem_cons.mpr (Or.inr (ih ht))
      | true =>
        have hq : q = id := Option.some.inj (by simpa [he] using h)
        subst id
        exact List.mem_cons.mpr (Or.inl rfl)
    | zero z => exact ih h
    | andGate z xs => exact ih h
    | xorGate z a b => exact ih h
    | eqGate a b => exact ih h
    | phase z xs => exact ih h

def sourceVal (v : Nat → Bool) (rs : List Record) (s : Nat) : Bool :=
  match sourceDimacs s rs with
  | some id => v id
  | none => false

theorem mapped_source_values (rs : List Record) (source ids : List Nat)
    (v u : Nat → Bool) (ha : agreeOn (liftVal v) (liftVal u) (liveIds rs))
    (h : sourceIds rs source = some ids) :
    ids.map u = source.map (sourceVal v rs) := by
  induction source generalizing ids with
  | nil =>
    have he : [] = ids := Option.some.inj h
    subst ids
    rfl
  | cons s source ih =>
    change (match sourceDimacs s rs with
      | none => none
      | some id =>
        match sourceIds rs source with
        | none => none
        | some rest => some (id :: rest)) = some ids at h
    cases hd : sourceDimacs s rs with
    | none =>
      rw [hd] at h
      cases h
    | some id =>
      rw [hd] at h
      change (match sourceIds rs source with
        | none => none
        | some rest => some (id :: rest)) = some ids at h
      cases ht : sourceIds rs source with
      | none =>
        rw [ht] at h
        cases h
      | some rest =>
        rw [ht] at h
        have he : id :: rest = ids := Option.some.inj h
        subst ids
        have hv : v id = u id := ha id (source_dimacs_live s id rs hd)
        have htail := ih rest ht
        have hhead : sourceVal v rs s = v id := by
          unfold sourceVal
          rw [hd]
        change u id :: rest.map u = sourceVal v rs s :: source.map (sourceVal v rs)
        exact (congrArg (fun b => b :: rest.map u) (hv.symm.trans hhead.symm)).trans
          (congrArg (fun tail => sourceVal v rs s :: tail) htail)

theorem accepted_phase_monomial (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat) (hr : replayRows n rs = some (cs, ws))
    (z : Nat) (source : List Nat) (hm : Record.phase z source ∈ rs)
    (v : Nat → Bool) :
    extendVal v rs z = andValue (source.map (sourceVal v rs)) := by
  obtain ⟨ids, hmap, hgate⟩ := replay_phase_binding n rs cs ws hr z source hm
  have ht := (replay_rows_binding n rs cs ws hr).2
  have hdef := extend_defs_sound v (liveIds rs) rs ht (.andGate z ids) hgate
  have hvalues := mapped_source_values rs source ids v (extendVal v rs)
    (extend_preserves v (liveIds rs) rs ht) hmap
  change extendVal v rs z = andValue (ids.map (extendVal v rs)) at hdef
  exact hdef.trans (congrArg andValue hvalues)


-- The exact rational pair from the admitted decimal tokens, with
-- multiplicative unit for an unlisted literal. Interpretation is
-- explicit, rather than equating printed weights with ideal phases.
def lookupWeight (id : Int) : List WeightEntry → ComplexValue
  | [] => ((1,1),(0,1))
  | e :: es => if intEq id e.1 then e.2 else lookupWeight id es

def serializedProduct {A : Type} [One A] [Mul A]
    (interpret : ComplexValue → A) (p : ParsedCnf) (n : Nat) (bits : List Bool) : A :=
  literalProduct (fun id => interpret (lookupWeight id p.weightValues))
    (decodeBits bits) (dimacsIds n)

theorem accepted_serialized_weight_total {A : Type} [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (gate cnf : List Nat) (n : Nat) (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (interpret : ComplexValue → A) :
    totalWmc n p (serializedProduct interpret p n) =
      sumBits (liveIds rs).length (fun xs =>
        let u := extendVal (decodeLive (liveIds rs) xs) rs
        if guardTruth u rs then
          literalProduct (fun id => interpret (lookupWeight id p.weightValues))
            u (dimacsIds n) else 0) :=
  (total_wmc_partition zl zr shuffle n p rs (serializedProduct interpret p n)
    (replay_live_unique n rs cs ws hr)).trans
    (sum_bits_congr (liveIds rs).length _ _ (fun xs _ =>
      accepted_literal_fiber zl zr gate cnf n rs p cs ws hg hp hr h
        (decodeLive (liveIds rs) xs)
        (fun id => interpret (lookupWeight id p.weightValues))))

-- Abstract exact phase algebra: exponentiation is a supplied
-- homomorphism from additive coefficients to multiplicative weights.
-- This separates the exact algebraic identity from analytic and
-- numerical approximation obligations.
def selectedPhaseSum {P : Type} [Zero P] [Add P]
    (coeff : Nat → P) (v : Nat → Bool) (weighted : List Nat) : List Nat → P
  | [] => 0
  | z :: zs =>
    if natMem z weighted && v z then
      coeff z + selectedPhaseSum coeff v weighted zs
    else selectedPhaseSum coeff v weighted zs

theorem selected_phase_exp {P A : Type} [Zero P] [Add P] [One A] [Mul A]
    (ex : P → A) (ez : ex 0 = 1)
    (ea : ∀ p q : P, ex (p+q) = ex p * ex q)
    (coeff : Nat → P) (weight : Int → A) (v : Nat → Bool)
    (weighted ids : List Nat)
    (hw : ∀ z, z ∈ ids → natMem z weighted = true → weight (pos z) = ex (coeff z)) :
    selectedPhaseProduct weight v weighted ids = ex (selectedPhaseSum coeff v weighted ids) := by
  induction ids with
  | nil => exact ez.symm
  | cons z zs ih =>
    have ht := ih (fun x hm hmem => hw x (List.mem_cons.mpr (Or.inr hm)) hmem)
    have hz := hw z (List.mem_cons.mpr (Or.inl rfl))
    change (if natMem z weighted && v z then
      weight (pos z) * selectedPhaseProduct weight v weighted zs
      else selectedPhaseProduct weight v weighted zs) =
      ex (if natMem z weighted && v z then
        coeff z + selectedPhaseSum coeff v weighted zs
        else selectedPhaseSum coeff v weighted zs)
    cases he : (natMem z weighted && v z) with
    | false => exact ht
    | true =>
      have hm := (and_true_parts he).1
      change weight (pos z) * selectedPhaseProduct weight v weighted zs =
        ex (coeff z + selectedPhaseSum coeff v weighted zs)
      rw [hz hm, ht, ea]

theorem accepted_total_phase_sum {P A : Type} [Zero P] [Add P]
    [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (ol : ∀ a : A, 1*a=a)
    (gate cnf : List Nat) (n : Nat) (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (ex : P → A) (ez : ex 0 = 1) (ea : ∀ p q : P, ex (p+q) = ex p * ex q)
    (coeff : Nat → P) (weight : Int → A)
    (hn : ∀ z, z ∈ dimacsIds n → weight (-pos z) = 1)
    (hu : ∀ z, z ∈ dimacsIds n → natMem z ws = false → weight (pos z) = 1)
    (hw : ∀ z, z ∈ dimacsIds n → natMem z ws = true → weight (pos z) = ex (coeff z)) :
    totalWmc n p (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n)) =
      sumBits (liveIds rs).length (fun xs =>
        let u := extendVal (decodeLive (liveIds rs) xs) rs
        if guardTruth u rs then ex (selectedPhaseSum coeff u ws (dimacsIds n)) else 0) := by
  have ht := accepted_total_phase_product zl zr shuffle ol gate cnf n rs p cs ws hg hp hr h weight hn hu
  exact ht.trans (sum_bits_congr (liveIds rs).length _ _ (fun xs _ =>
    congrArg (fun x => if guardTruth (extendVal (decodeLive (liveIds rs) xs) rs) rs then x else 0)
      (selected_phase_exp ex ez ea coeff weight (extendVal (decodeLive (liveIds rs) xs) rs)
        ws (dimacsIds n) hw)))


-- A separate versioned source coefficient stream. It retains the
-- exact rational turns and radian components from the Rust residual
-- certificate without modifying gate-v1 or equating them to MPFR.
structure PhaseEntry where
  out : Nat
  source : List Nat
  turns : DecimalValue
  radians : DecimalValue
deriving Repr

def parsePhaseEntry : List Token → Option PhaseEntry
  | tag :: z :: tn :: td :: rn :: rd :: src =>
    if tag == [99,111,101,102] then do
      let id ← parseNatToken z
      let t ← parseIntToken tn
      let d ← parseNatToken td
      let a ← parseIntToken rn
      let b ← parseNatToken rd
      let support ← src.mapM parseNatToken
      if d == 0 || b == 0 || negative t || !natLE (t.natAbs + 1) d ||
          (intEq t 0 && intEq a 0) then none
      else some (PhaseEntry.mk id support (t,d) (a,b))
    else none
  | _ => none

def parsePhase (bytes : List Nat) : Option (List PhaseEntry) :=
  if ascii bytes then
    match rows bytes with
    | [tag] :: rest =>
      if tag == [99,114,114,45,112,104,97,115,101,45,118,49] then
        rest.mapM parsePhaseEntry
      else none
    | _ => none
  else none

def phaseSource (z : Nat) : List Record → Option (List Nat)
  | [] => none
  | .phase id src :: rs =>
    if (@decide (z = id) (Nat.decEq z id)) then some src else phaseSource z rs
  | _ :: rs => phaseSource z rs

def phaseEntryOK (rs : List Record) (e : PhaseEntry) : Bool :=
  match phaseSource e.out rs with
  | some src => natListEq e.source src
  | none => false

def phaseEntriesKnown (rs : List Record) : List PhaseEntry → Bool
  | [] => true
  | e :: es => phaseEntryOK rs e && phaseEntriesKnown rs es

def phaseSidecarOK (rs : List Record) (es : List PhaseEntry) : Bool :=
  natListEq (es.map PhaseEntry.out) (phaseIds rs) && phaseEntriesKnown rs es

def checkPhaseSidecar (gate side : List Nat) : Bool :=
  match parseGate gate, parsePhase side with
  | some (_,rs), some es => phaseSidecarOK rs es
  | _, _ => false

def phaseLookup (z : Nat) : List PhaseEntry → Option PhaseEntry
  | [] => none
  | e :: es =>
    if (@decide (z = e.out) (Nat.decEq z e.out)) then some e else phaseLookup z es

theorem phase_source_sound (z : Nat) (rs : List Record) (src : List Nat)
    (h : phaseSource z rs = some src) : Record.phase z src ∈ rs := by
  induction rs with
  | nil => cases h
  | cons r rs ih =>
    cases r with
    | live s id => exact List.mem_cons.mpr (Or.inr (ih h))
    | zero id => exact List.mem_cons.mpr (Or.inr (ih h))
    | andGate id xs => exact List.mem_cons.mpr (Or.inr (ih h))
    | xorGate id a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | eqGate a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | phase id xs =>
      change (if (@decide (z = id) (Nat.decEq z id)) then some xs else phaseSource z rs) =
        some src at h
      cases he : (@decide (z = id) (Nat.decEq z id)) with
      | false =>
        have ht : phaseSource z rs = some src := by simpa [he] using h
        exact List.mem_cons.mpr (Or.inr (ih ht))
      | true =>
        have hz : z = id := of_decide_eq_true he
        have hx : xs = src := Option.some.inj (by simpa [he] using h)
        subst id
        subst xs
        exact List.mem_cons.mpr (Or.inl rfl)

theorem phase_entry_sound (rs : List Record) (e : PhaseEntry)
    (h : phaseEntryOK rs e = true) : Record.phase e.out e.source ∈ rs := by
  unfold phaseEntryOK at h
  cases hs : phaseSource e.out rs with
  | none => rw [hs] at h; cases h
  | some src =>
    rw [hs] at h
    have he := (nat_list_eq_iff e.source src).mp h
    have hm := phase_source_sound e.out rs src hs
    rw [he]
    exact hm

theorem phase_entries_sound (rs : List Record) (es : List PhaseEntry)
    (h : phaseEntriesKnown rs es = true) :
    ∀ e, e ∈ es → Record.phase e.out e.source ∈ rs := by
  induction es with
  | nil => intro e hm; cases hm
  | cons e es ih =>
    have hh := and_true_parts (show (phaseEntryOK rs e && phaseEntriesKnown rs es) = true from h)
    intro q hm
    rcases List.mem_cons.mp hm with he | ht
    · subst q
      exact phase_entry_sound rs e hh.1
    · exact ih hh.2 q ht

theorem phase_lookup_sound (z : Nat) (es : List PhaseEntry) (e : PhaseEntry)
    (h : phaseLookup z es = some e) : e ∈ es ∧ z = e.out := by
  induction es with
  | nil => cases h
  | cons q es ih =>
    change (if (@decide (z = q.out) (Nat.decEq z q.out)) then some q else phaseLookup z es) =
      some e at h
    cases he : (@decide (z = q.out) (Nat.decEq z q.out)) with
    | false =>
      have ht : phaseLookup z es = some e := by simpa [he] using h
      have hh := ih ht
      exact ⟨List.mem_cons.mpr (Or.inr hh.1), hh.2⟩
    | true =>
      have hz : z = q.out := of_decide_eq_true he
      have hq : q = e := Option.some.inj (by simpa [he] using h)
      subst q
      exact ⟨List.mem_cons.mpr (Or.inl rfl), hz⟩

theorem phase_lookup_exists (z : Nat) (es : List PhaseEntry)
    (h : z ∈ es.map PhaseEntry.out) : ∃ e, phaseLookup z es = some e := by
  induction es with
  | nil => cases h
  | cons e es ih =>
    cases he : (@decide (z = e.out) (Nat.decEq z e.out)) with
    | true =>
      exact ⟨e, by simp [phaseLookup, he]⟩
    | false =>
      have hn : z ≠ e.out := fun hz => by
        have ht : (@decide (z = e.out) (Nat.decEq z e.out)) = true := decide_eq_true hz
        rw [he] at ht
        cases ht
      have hm : z ∈ es.map PhaseEntry.out := by
        rcases List.mem_cons.mp h with hz | ht
        · exact False.elim (hn hz)
        · exact ht
      obtain ⟨q, hq⟩ := ih hm
      exact ⟨q, by simp [phaseLookup, he, hq]⟩

theorem sidecar_weighted_lookup (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat) (hr : replayRows n rs = some (cs, ws))
    (es : List PhaseEntry) (hs : phaseSidecarOK rs es = true)
    (z : Nat) (hz : natMem z ws = true) :
    ∃ e, phaseLookup z es = some e ∧ Record.phase z e.source ∈ rs := by
  have hh := and_true_parts (show
    (natListEq (es.map PhaseEntry.out) (phaseIds rs) && phaseEntriesKnown rs es) = true from hs)
  have hi := (nat_list_eq_iff (es.map PhaseEntry.out) (phaseIds rs)).mp hh.1
  have hm := (nat_mem_iff z ws).mp hz
  rw [replay_phase_ids n rs cs ws hr] at hm
  have hm' : z ∈ es.map PhaseEntry.out := by
    rw [hi]
    exact List.mem_reverse.mp hm
  obtain ⟨e, he⟩ := phase_lookup_exists z es hm'
  have hp := phase_lookup_sound z es e he
  have hrec := phase_entries_sound rs es hh.2 e hp.1
  have hbind : Record.phase z e.source ∈ rs := by
    rw [hp.2]
    exact hrec
  exact ⟨e, he, hbind⟩

-- The interpretation of a rational coefficient pair is supplied
-- separately (turns and radians have different physical units).
def sidecarCoeff {P : Type} [Zero P]
    (interpret : DecimalValue → DecimalValue → P) (es : List PhaseEntry) (z : Nat) : P :=
  match phaseLookup z es with
  | some e => interpret e.turns e.radians
  | none => 0

def sourcePhaseBit (rs : List Record) (es : List PhaseEntry)
    (v : Nat → Bool) (z : Nat) : Bool :=
  match phaseLookup z es with
  | some e => andValue (e.source.map (sourceVal v rs))
  | none => false

theorem accepted_source_phase_bit (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat) (hr : replayRows n rs = some (cs, ws))
    (es : List PhaseEntry) (hs : phaseSidecarOK rs es = true)
    (v : Nat → Bool) (z : Nat) (hz : natMem z ws = true) :
    extendVal v rs z = sourcePhaseBit rs es v z := by
  obtain ⟨e, he, hm⟩ := sidecar_weighted_lookup n rs cs ws hr es hs z hz
  unfold sourcePhaseBit
  rw [he]
  exact accepted_phase_monomial n rs cs ws hr z e.source hm v

theorem selected_phase_sum_agree {P : Type} [Zero P] [Add P]
    (coeff : Nat → P) (a b : Nat → Bool) (weighted ids : List Nat)
    (h : ∀ z, z ∈ ids → natMem z weighted = true → a z = b z) :
    selectedPhaseSum coeff a weighted ids = selectedPhaseSum coeff b weighted ids := by
  induction ids with
  | nil => rfl
  | cons z zs ih =>
    have ht := ih (fun x hm hx => h x (List.mem_cons.mpr (Or.inr hm)) hx)
    change (if natMem z weighted && a z then coeff z + selectedPhaseSum coeff a weighted zs
      else selectedPhaseSum coeff a weighted zs) =
      (if natMem z weighted && b z then coeff z + selectedPhaseSum coeff b weighted zs
      else selectedPhaseSum coeff b weighted zs)
    rw [ht]
    cases he : natMem z weighted with
    | false => rfl
    | true => rw [h z (List.mem_cons.mpr (Or.inl rfl)) he]

theorem accepted_source_phase_sum {P : Type} [Zero P] [Add P]
    (n : Nat) (rs : List Record) (cs : List (List Int)) (ws : List Nat)
    (hr : replayRows n rs = some (cs, ws))
    (es : List PhaseEntry) (hs : phaseSidecarOK rs es = true)
    (interpret : DecimalValue → DecimalValue → P) (v : Nat → Bool) :
    selectedPhaseSum (sidecarCoeff interpret es) (extendVal v rs) ws (dimacsIds n) =
      selectedPhaseSum (sidecarCoeff interpret es) (sourcePhaseBit rs es v) ws (dimacsIds n) :=
  selected_phase_sum_agree (sidecarCoeff interpret es) _ _ ws (dimacsIds n)
    (fun z _ hz => accepted_source_phase_bit n rs cs ws hr es hs v z hz)


-- Source diagonal rows: x_i = XOR of monomials in the encoded
-- residual output ANF. Terms are stored in reverse encoder order;
-- the empty polynomial is zero and the empty monomial is one.
abbrev GuardRow := Nat × List (List Nat)

def parseGuardMono (s : Token) : Option (List Nat) :=
  if s == [45] then some []
  else (splitBytes 44 s).mapM parseNatToken

def parseGuardRow : List Token → Option GuardRow
  | tag :: i :: terms =>
    if tag == [114,111,119] then do
      let id ← parseNatToken i
      let ms ← terms.mapM parseGuardMono
      some (id,ms)
    else none
  | _ => none

def parseGuard (bytes : List Nat) : Option (List GuardRow) :=
  if ascii bytes then
    match rows bytes with
    | [tag] :: rest =>
      if tag == [99,114,114,45,103,117,97,114,100,45,118,49] then
        rest.mapM parseGuardRow
      else none
    | _ => none
  else none

def zeroWitness (z : Nat) : List Record → Bool
  | [] => false
  | .zero q :: rs => (@decide (z = q) (Nat.decEq z q)) || zeroWitness z rs
  | _ :: rs => zeroWitness z rs

def xorInputs (z : Nat) : List Record → Option (Nat × Nat)
  | [] => none
  | .xorGate q a b :: rs =>
    if (@decide (z = q) (Nat.decEq z q)) then some (a,b) else xorInputs z rs
  | _ :: rs => xorInputs z rs

def monoIdOK (rs : List Record) (z : Nat) : List Nat → Bool
  | [x] => @decide (z = x) (Nat.decEq z x)
  | xs => andWitness z xs rs

def guardMonoOK (rs : List Record) (z : Nat) (m : List Nat) : Bool :=
  match sourceIds rs m with
  | some ids => monoIdOK rs z ids
  | none => false

-- Each recursive step consumes one source ANF term, so this check
-- never expands a potentially shared XOR circuit exponentially.
def guardPolyOK (rs : List Record) : List (List Nat) → Nat → Bool
  | [], z => zeroWitness z rs
  | [m], z => guardMonoOK rs z m
  | m :: q :: qs, z =>
    match xorInputs z rs with
    | some (a,b) => guardMonoOK rs b m && guardPolyOK rs (q :: qs) a
    | none => false

def guardRowOK (rs : List Record) (a b : Nat) (row : GuardRow) : Bool :=
  match sourceDimacs row.1 rs with
  | some id => (@decide (a = id) (Nat.decEq a id)) && guardPolyOK rs row.2 b
  | none => false

def guardRowsOK (all : List Record) : List Record → List GuardRow → Bool
  | [], [] => true
  | [], _ :: _ => false
  | .eqGate a b :: rs, row :: rest => guardRowOK all a b row && guardRowsOK all rs rest
  | .eqGate _ _ :: _, [] => false
  | _ :: rs, rest => guardRowsOK all rs rest

def checkGuardSidecar (gate side : List Nat) : Bool :=
  match parseGate gate, parseGuard side with
  | some (_,rs), some gs => guardRowsOK rs rs gs
  | _, _ => false

def anfValue (v : Nat → Bool) : List (List Nat) → Bool
  | [] => false
  | m :: ms => (anfValue v ms).xor (andValue (m.map v))

def residualGuard (v : Nat → Bool) : List GuardRow → Bool
  | [] => true
  | (i,ms) :: gs => (v i == anfValue v ms) && residualGuard v gs

theorem zero_witness_sound (z : Nat) (rs : List Record)
    (h : zeroWitness z rs = true) : Record.zero z ∈ rs := by
  induction rs with
  | nil => cases h
  | cons r rs ih =>
    cases r with
    | live s id => exact List.mem_cons.mpr (Or.inr (ih h))
    | andGate q xs => exact List.mem_cons.mpr (Or.inr (ih h))
    | xorGate q a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | eqGate a b => exact List.mem_cons.mpr (Or.inr (ih h))
    | phase q xs => exact List.mem_cons.mpr (Or.inr (ih h))
    | zero q =>
      have hh : ((@decide (z = q) (Nat.decEq z q)) || zeroWitness z rs) = true := h
      have hor : (@decide (z = q) (Nat.decEq z q)) = true ∨ zeroWitness z rs = true := by
        simpa only [Bool.or_eq_true] using hh
      rcases hor with he | ht
      · have hz : z = q := of_decide_eq_true he
        subst q
        exact List.mem_cons.mpr (Or.inl rfl)
      · exact List.mem_cons.mpr (Or.inr (ih ht))

theorem xor_inputs_sound (z a b : Nat) (rs : List Record)
    (h : xorInputs z rs = some (a,b)) : Record.xorGate z a b ∈ rs := by
  induction rs with
  | nil => cases h
  | cons r rs ih =>
    cases r with
    | live s id => exact List.mem_cons.mpr (Or.inr (ih h))
    | zero q => exact List.mem_cons.mpr (Or.inr (ih h))
    | andGate q xs => exact List.mem_cons.mpr (Or.inr (ih h))
    | eqGate x y => exact List.mem_cons.mpr (Or.inr (ih h))
    | phase q xs => exact List.mem_cons.mpr (Or.inr (ih h))
    | xorGate q x y =>
      change (if (@decide (z = q) (Nat.decEq z q)) then some (x,y) else xorInputs z rs) =
        some (a,b) at h
      cases he : (@decide (z = q) (Nat.decEq z q)) with
      | false =>
        have ht : xorInputs z rs = some (a,b) := by simpa [he] using h
        exact List.mem_cons.mpr (Or.inr (ih ht))
      | true =>
        have hz : z = q := of_decide_eq_true he
        have hp : (x,y) = (a,b) := Option.some.inj (by simpa [he] using h)
        have hx : x = a := congrArg Prod.fst hp
        have hy : y = b := congrArg Prod.snd hp
        subst q
        subst x
        subst y
        exact List.mem_cons.mpr (Or.inl rfl)

theorem mono_id_sound (rs : List Record) (u : Nat → Bool) (z : Nat)
    (ids : List Nat) (hd : defsSem (liftVal u) rs)
    (h : monoIdOK rs z ids = true) : u z = andValue (ids.map u) := by
  cases ids with
  | nil =>
    exact hd (.andGate z []) (and_witness_sound z [] rs h)
  | cons x xs =>
    cases xs with
    | nil =>
      have he : z = x := of_decide_eq_true h
      subst z
      change u x = (u x && true)
      cases u x <;> rfl
    | cons y ys =>
      exact hd (.andGate z (x :: y :: ys)) (and_witness_sound z (x :: y :: ys) rs h)

theorem guard_mono_sound (rs : List Record) (v u : Nat → Bool)
    (ha : agreeOn (liftVal v) (liftVal u) (liveIds rs))
    (hd : defsSem (liftVal u) rs) (z : Nat) (m : List Nat)
    (h : guardMonoOK rs z m = true) : u z = andValue (m.map (sourceVal v rs)) := by
  unfold guardMonoOK at h
  cases hm : sourceIds rs m with
  | none => rw [hm] at h; cases h
  | some ids =>
    rw [hm] at h
    exact (mono_id_sound rs u z ids hd h).trans
      (congrArg andValue (mapped_source_values rs m ids v u ha hm))

theorem guard_poly_sound (rs : List Record) (v u : Nat → Bool)
    (ha : agreeOn (liftVal v) (liftVal u) (liveIds rs))
    (hd : defsSem (liftVal u) rs) (ms : List (List Nat)) (z : Nat)
    (h : guardPolyOK rs ms z = true) : u z = anfValue (sourceVal v rs) ms := by
  induction ms generalizing z with
  | nil => exact hd (.zero z) (zero_witness_sound z rs h)
  | cons m ms ih =>
    cases ms with
    | nil =>
      have hm := guard_mono_sound rs v u ha hd z m h
      change u z = (false : Bool).xor (andValue (m.map (sourceVal v rs)))
      rw [hm]
      cases andValue (m.map (sourceVal v rs)) <;> rfl
    | cons q qs =>
      change (match xorInputs z rs with
        | some (a,b) => guardMonoOK rs b m && guardPolyOK rs (q :: qs) a
        | none => false) = true at h
      cases hx : xorInputs z rs with
      | none => rw [hx] at h; cases h
      | some pair =>
        rcases pair with ⟨a,b⟩
        rw [hx] at h
        have hh := and_true_parts h
        have hm := guard_mono_sound rs v u ha hd b m hh.1
        have ht := ih a hh.2
        have hz := hd (.xorGate z a b) (xor_inputs_sound z a b rs hx)
        change u z = (u a).xor (u b) at hz
        change u z = (anfValue (sourceVal v rs) (q :: qs)).xor
          (andValue (m.map (sourceVal v rs)))
        rw [hz, hm, ht]

theorem guard_row_sound (rs : List Record) (v u : Nat → Bool)
    (ha : agreeOn (liftVal v) (liftVal u) (liveIds rs))
    (hd : defsSem (liftVal u) rs) (a b : Nat) (row : GuardRow)
    (h : guardRowOK rs a b row = true) :
    (u a == u b) = (sourceVal v rs row.1 == anfValue (sourceVal v rs) row.2) := by
  unfold guardRowOK at h
  cases hm : sourceDimacs row.1 rs with
  | none => rw [hm] at h; cases h
  | some id =>
    rw [hm] at h
    have hh := and_true_parts h
    have he : a = id := of_decide_eq_true hh.1
    have hv : v id = u id := ha id (source_dimacs_live row.1 id rs hm)
    have hb := guard_poly_sound rs v u ha hd row.2 b hh.2
    have hleft : sourceVal v rs row.1 = v id := by
      unfold sourceVal
      rw [hm]
    rw [he, hleft, hv, hb]

theorem guard_rows_sound (all rs : List Record) (v u : Nat → Bool)
    (ha : agreeOn (liftVal v) (liftVal u) (liveIds all))
    (hd : defsSem (liftVal u) all) (gs : List GuardRow)
    (h : guardRowsOK all rs gs = true) :
    guardTruth u rs = residualGuard (sourceVal v all) gs := by
  induction rs generalizing gs with
  | nil =>
    cases gs with
    | nil => rfl
    | cons g gs => cases h
  | cons r rs ih =>
    cases r with
    | live s id => exact ih gs h
    | zero z => exact ih gs h
    | andGate z xs => exact ih gs h
    | xorGate z a b => exact ih gs h
    | phase z xs => exact ih gs h
    | eqGate a b =>
      cases gs with
      | nil => cases h
      | cons g gs =>
        have hh := and_true_parts (show
          (guardRowOK all a b g && guardRowsOK all rs gs) = true from h)
        have hr := guard_row_sound all v u ha hd a b g hh.1
        have ht := ih gs hh.2
        change ((u a == u b) && guardTruth u rs) =
          ((sourceVal v all g.1 == anfValue (sourceVal v all) g.2) &&
            residualGuard (sourceVal v all) gs)
        rw [hr, ht]

theorem accepted_residual_guard (n : Nat) (rs : List Record)
    (cs : List (List Int)) (ws : List Nat) (hr : replayRows n rs = some (cs, ws))
    (gs : List GuardRow) (hg : guardRowsOK rs rs gs = true) (v : Nat → Bool) :
    guardTruth (extendVal v rs) rs = residualGuard (sourceVal v rs) gs :=
  let ht := (replay_rows_binding n rs cs ws hr).2
  guard_rows_sound rs rs v (extendVal v rs)
    (extend_preserves v (liveIds rs) rs ht)
    (extend_defs_sound v (liveIds rs) rs ht) gs hg

-- Compose the two checked source sidecars with ideal phase weights.
-- The actual serialized-weight approximation remains a separate
-- numerical obligation, and source provenance is not inferred here.
theorem accepted_constrained_phase_sum {P A : Type} [Zero P] [Add P]
    [Zero A] [Add A] [One A] [Mul A]
    (zl : ∀ a : A, 0+a=a) (zr : ∀ a : A, a+0=a)
    (shuffle : ∀ a b c d : A, (a+b)+(c+d) = (a+c)+(b+d))
    (ol : ∀ a : A, 1*a=a)
    (gate cnf : List Nat) (n : Nat) (rs : List Record) (p : ParsedCnf)
    (cs : List (List Int)) (ws : List Nat)
    (hg : parseGate gate = some (n, rs)) (hp : parseCnf cnf = some p)
    (hr : replayRows n rs = some (cs, ws)) (h : check gate cnf = true)
    (es : List PhaseEntry) (hs : phaseSidecarOK rs es = true)
    (gs : List GuardRow) (hgs : guardRowsOK rs rs gs = true)
    (interpret : DecimalValue → DecimalValue → P)
    (ex : P → A) (ez : ex 0 = 1) (ea : ∀ p q : P, ex (p+q) = ex p * ex q)
    (weight : Int → A)
    (hn : ∀ z, z ∈ dimacsIds n → weight (-pos z) = 1)
    (hu : ∀ z, z ∈ dimacsIds n → natMem z ws = false → weight (pos z) = 1)
    (hw : ∀ z, z ∈ dimacsIds n → natMem z ws = true →
      weight (pos z) = ex (sidecarCoeff interpret es z)) :
    totalWmc n p (fun bits => literalProduct weight (decodeBits bits) (dimacsIds n)) =
      sumBits (liveIds rs).length (fun xs =>
        let v := decodeLive (liveIds rs) xs
        if residualGuard (sourceVal v rs) gs then
          ex (selectedPhaseSum (sidecarCoeff interpret es)
            (sourcePhaseBit rs es v) ws (dimacsIds n)) else 0) := by
  have ht := accepted_total_phase_sum zl zr shuffle ol gate cnf n rs p cs ws
    hg hp hr h ex ez ea (sidecarCoeff interpret es) weight hn hu hw
  apply ht.trans
  apply sum_bits_congr
  intro xs _
  let v := decodeLive (liveIds rs) xs
  change (if guardTruth (extendVal v rs) rs then
    ex (selectedPhaseSum (sidecarCoeff interpret es) (extendVal v rs) ws (dimacsIds n)) else 0) =
    (if residualGuard (sourceVal v rs) gs then
      ex (selectedPhaseSum (sidecarCoeff interpret es) (sourcePhaseBit rs es v) ws (dimacsIds n)) else 0)
  rw [accepted_residual_guard n rs cs ws hr gs hgs v,
    accepted_source_phase_sum n rs cs ws hr es hs interpret v]


-- Portable reduction ledger v2. Structural replay is independent of
-- the Rust ledger observer. Local alias/substitution/HH/omega
-- semantic certificates are deliberately NOT inferred by this gate.
structure LedgerSnap where
  raw : Token
  n : Nat
  live : List Nat
  phaseText : Token
  rowText : Token
  phaseSupport : List (List Nat)
  constraints : List (List (List Nat))

def parseLedgerPhase (s : Token) : Option (List Nat) :=
  match splitBytes 58 s with
  | [m,tn,td,rn,rd] => do
    let ids ← parseGuardMono m
    let e ← parsePhaseEntry ([99,111,101,102] :: [48] :: tn :: td :: rn :: rd ::
      (if m == [45] then [] else splitBytes 44 m))
    if natListEq ids e.source then some ids else none
  | _ => none

def parseLedgerPoly (s : Token) : Option (List (List Nat)) :=
  if s == [126] then some [] else (splitBytes 58 s).mapM parseGuardMono

def parseLedgerSnap (s : Token) : Option LedgerSnap :=
  match splitBytes 59 s with
  | [n,live,phase,cs] => do
    let n ← parseNatToken n
    let ids ← parseGuardMono live
    let ps ← if phase == [126] then some [] else (splitBytes 124 phase).mapM parseLedgerPhase
    let rows ← if cs == [33] then some [] else (splitBytes 124 cs).mapM parseLedgerPoly
    if natLE n 4096 && uniqueIds ids && inputsKnown ids (List.range n) &&
        ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
        rows.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
      some (LedgerSnap.mk s n ids phase cs ps rows)
    else none
  | _ => none

def snapCost (s : LedgerSnap) : Nat × Nat :=
  let p := s.phaseSupport.foldl (fun a m => a+1+m.length) 0
  let c := s.constraints.foldl (fun a row => row.foldl (fun b m => b+1+m.length) a) 0
  (p,p+c+s.live.length)

def removedIds (a b : LedgerSnap) : List Nat :=
  a.live.filter (fun x => !natMem x b.live)

def freeSnapOK (a b : LedgerSnap) : Bool :=
  natListEq a.phaseText b.phaseText && natListEq a.rowText b.rowText &&
    (removedIds a b).all (fun x =>
      !(a.phaseSupport.any (natMem x)) &&
      !(a.constraints.any (fun row => row.any (natMem x))))

structure LedgerStep where
  kind : Nat
  commit : Bool
  witness : Token
  before : LedgerSnap
  trial : LedgerSnap

structure LedgerTally where
  sub : Nat := 0
  free : Nat := 0
  hh : Nat := 0
  omega : Nat := 0
  rejected : Nat := 0
  alias : Nat := 0
  batchFree : Nat := 0
  stage : Nat := 0

def ledgerTallyList (t : LedgerTally) : List Nat :=
  [t.sub,t.free,t.hh,t.omega,t.rejected,t.alias,t.batchFree]

def ledgerFuel (t : LedgerTally) : Nat := t.sub+t.free+t.hh+t.omega

def ledgerMultiplier (t : LedgerTally) : Nat := 2*(t.free+t.hh)+t.omega

def parseLedgerStep : List Token → Option LedgerStep
  | [tag,k,c,wi,b,a] =>
    if tag == [115,116,101,112] then do
      let kind ← parseNatToken k
      let commit ← parseNatToken c
      let before ← parseLedgerSnap b
      let trial ← parseLedgerSnap a
      if natLE kind 5 && natLE commit 1 then
        some (LedgerStep.mk kind (commit == 1) wi before trial)
      else none
    else none
  | _ => none

def ledgerWitnessOK (s : LedgerStep) : Bool :=
  let removed := removedIds s.before s.trial
  if s.kind == 0 then
    match splitBytes 58 s.witness with
    | [links,parent] =>
      let ls := (splitBytes 124 links).mapM (fun t => (splitBytes 44 t).mapM parseNatToken)
      let ps := (splitBytes 124 parent).mapM (fun t => (splitBytes 44 t).mapM parseNatToken)
      match ls,ps with
      | some ll,some pp => !ll.isEmpty && ll.length == pp.length &&
          pp.length == removed.length &&
          ll.all (fun p => p.length == 4) &&
          pp.all (fun p => match p with
            | [child,par] => natMem child removed && natMem par s.before.live
            | _ => false)
      | _,_ => false
    | _ => false
  else if s.kind == 1 then s.witness == [45]
  else if s.kind == 2 then
    match (splitBytes 44 s.witness).mapM parseNatToken with
    | some [y,row] => natMem y removed && natLE (row+1) s.before.constraints.length
    | _ => false
  else
    match parseNatToken s.witness with
    | some y => natMem y removed
    | none => false

-- Rejected trials are recorded but do not change the committed
-- state. Their local rule witness is not certified by this check.
def ledgerAdvance (t : LedgerTally) (s : LedgerStep) : Option LedgerTally :=
  let a := snapCost s.before
  let b := snapCost s.trial
  let improves := natLE b.1 a.1 && natLE (b.2+1) a.2
  let d := (removedIds s.before s.trial).length
  if !natLE (ledgerFuel t+1) 64 then none
  else if !s.commit then
    if natLE 2 s.kind && !improves then
      some { t with rejected := t.rejected+1, stage := 2 }
    else none
  else if !improves || s.before.n != s.trial.n ||
      !inputsKnown s.before.live s.trial.live || !ledgerWitnessOK s then none
  else if s.kind == 0 then
    if t.stage == 0 && d != 0 then
      some { t with sub := t.sub+d, alias := d, stage := 1 }
    else none
  else if s.kind == 1 then
    if natLE t.stage 1 && d != 0 && freeSnapOK s.before s.trial then
      some { t with free := t.free+d, batchFree := d, stage := 2 }
    else none
  else if s.kind == 2 then
    if d == 1 then some { t with sub := t.sub+1, stage := 2 } else none
  else if s.kind == 3 then
    if d == 1 && freeSnapOK s.before s.trial then
      some { t with free := t.free+1, stage := 2 }
    else none
  else if s.kind == 4 then
    if d == 2 then some { t with hh := t.hh+1, stage := 2 } else none
  else if s.kind == 5 then
    if d == 1 then some { t with omega := t.omega+1, stage := 2 } else none
  else none

def ledgerNext (current : LedgerSnap) (s : LedgerStep) : LedgerSnap :=
  if s.commit then s.trial else current

def replayLedger (current : LedgerSnap) (t : LedgerTally) :
    List LedgerStep → Option (LedgerSnap × LedgerTally)
  | [] => some (current,t)
  | s :: ss =>
    if natListEq current.raw s.before.raw then
      match ledgerAdvance t s with
      | some next =>
        if natLE (ledgerFuel next) 64 then replayLedger (ledgerNext current s) next ss
        else none
      | none => none
    else none

def checkLedger (bytes : List Nat) : Bool :=
  if !ascii bytes then false else
  match rows bytes with
  | (tag :: norm :: k :: counts) :: [st,start] :: rest =>
    if tag == [99,114,114,45,108,101,100,103,101,114,45,118,50] &&
        st == [115,116,97,114,116] && counts.length == 7 then
      match parseNatToken norm, parseNatToken k, counts.mapM parseNatToken,
          parseLedgerSnap start, rest.reverse with
      | some n, some mult, some expected, some initial, [et,last] :: rev =>
        if et == [101,110,100] && n == initial.n+initial.live.length then
          match rev.reverse.mapM parseLedgerStep, parseLedgerSnap last with
          | some steps, some final =>
            match replayLedger initial {} steps with
            | some (actual,t) => natListEq actual.raw final.raw &&
                natListEq (ledgerTallyList t) expected && ledgerMultiplier t == mult
            | none => false
          | _,_ => false
        else false
      | _,_,_,_,_ => false
    else false
  | _ => false

theorem free_snapshot_payload (a b : LedgerSnap) (h : freeSnapOK a b = true) :
    a.phaseText = b.phaseText ∧ a.rowText = b.rowText := by
  have hh : ((natListEq a.phaseText b.phaseText && natListEq a.rowText b.rowText) &&
    (removedIds a b).all (fun x => !(a.phaseSupport.any (natMem x)) &&
      !(a.constraints.any (fun row => row.any (natMem x))))) = true := h
  have hp := and_true_parts (and_true_parts hh).1
  exact ⟨(nat_list_eq_iff _ _).mp hp.1,(nat_list_eq_iff _ _).mp hp.2⟩

theorem rejected_ledger_next (current : LedgerSnap) (s : LedgerStep)
    (h : s.commit = false) : ledgerNext current s = current := by
  unfold ledgerNext
  rw [h]
  rfl

theorem committed_ledger_next (current : LedgerSnap) (s : LedgerStep)
    (h : s.commit = true) : ledgerNext current s = s.trial := by
  unfold ledgerNext
  rw [h]
  rfl

-- Independent composition theorem over a list of local semantic
-- obligations. This does not discharge the Rust step obligations.
theorem ledger_scale_compose {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (current final : LedgerSnap)
    (steps : List (LedgerStep × Nat))
    (chain : ∀ a b : LedgerSnap, a.raw = b.raw → value a = value b)
    (stepSound : ∀ e, e ∈ steps → value e.1.before = scale e.2 (value e.1.trial))
    (ordered : List (LedgerStep × Nat) → LedgerSnap → LedgerSnap → Prop)
    (hnil : ∀ a b, ordered [] a b → a.raw = b.raw)
    (hcons : ∀ e es a b, ordered (e :: es) a b →
      a.raw = e.1.before.raw ∧ ordered es e.1.trial b)
    (h : ordered steps current final) :
    value current = scale (steps.map Prod.snd).sum (value final) := by
  induction steps generalizing current with
  | nil => exact (chain current final (hnil current final h)).trans (h0 (value final)).symm
  | cons e es ih =>
    have hh := hcons e es current final h
    have he := stepSound e (List.mem_cons.mpr (Or.inl rfl))
    have ht := ih e.1.trial (fun q hm => stepSound q (List.mem_cons.mpr (Or.inr hm))) hh.2
    exact (chain current e.1.before hh.1).trans (he.trans
      ((congrArg (scale e.2) ht).trans (ha e.2 (es.map Prod.snd).sum (value final))))


-- Exponent in units of sqrt(2); rejected proposals contribute zero.
def ledgerStepExponent (s : LedgerStep) : Nat :=
  if !s.commit then 0
  else if s.kind == 1 then 2 * (removedIds s.before s.trial).length
  else if s.kind == 3 || s.kind == 4 then 2
  else if s.kind == 5 then 1
  else 0

-- Independently audit each constructive ingredient rather than hiding
-- the axiom dependencies inside a single tactic proof.
theorem ledger_bool_false {A : Type} (b : Bool) (x y : A)
    (hb : b = false) : (if b then x else y) = y := by
  cases b with
  | false => rfl
  | true => cases hb

theorem ledger_bool_true {A : Type} (b : Bool) (x y : A)
    (hb : b = true) : (if b then x else y) = x := by
  cases b with
  | false => cases hb
  | true => rfl

theorem ledger_batch_arithmetic (f q o d : Nat) :
    2 * (f+d+q)+o = 2*(f+q)+o+2*d := by
  simp only [Nat.mul_add, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]

theorem ledger_free_arithmetic (f q o : Nat) :
    2 * (f+1+q)+o = 2*(f+q)+o+2 :=
  ledger_batch_arithmetic f q o 1

theorem ledger_hh_arithmetic (f q o : Nat) :
    2 * (f+(q+1))+o = 2*(f+q)+o+2 := by
  rw [Nat.add_comm q 1, ← Nat.add_assoc f 1 q]
  exact ledger_free_arithmetic f q o

-- Use the Nat-specific constructive recursion from Init.Prelude,
-- not generic LawfulBEq instance resolution.
theorem ledger_kind_eq (k j : Nat) (h : (k == j) = true) : k = j :=
  Nat.eq_of_beq_eq_true h

theorem ledger_exponent_5 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 5) = true) : ledgerStepExponent s = 1 := by
  have hkind : s.kind = 5 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_4 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 4) = true) : ledgerStepExponent s = 2 := by
  have hkind : s.kind = 4 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_3 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 3) = true) : ledgerStepExponent s = 2 := by
  have hkind : s.kind = 3 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_2 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 2) = true) : ledgerStepExponent s = 0 := by
  have hkind : s.kind = 2 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_1 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 1) = true) : ledgerStepExponent s = 2 * (removedIds s.before s.trial).length := by
  have hkind : s.kind = 1 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_0 (s : LedgerStep) (hc : (!s.commit) = false)
    (hk : (s.kind == 0) = true) : ledgerStepExponent s = 0 := by
  have hkind : s.kind = 0 := ledger_kind_eq _ _ hk
  unfold ledgerStepExponent
  rw [ledger_bool_false _ _ _ hc, hkind] <;> rfl

theorem ledger_exponent_rejected (s : LedgerStep) (hc : (!s.commit) = true) :
    ledgerStepExponent s = 0 :=
  ledger_bool_true _ _ _ hc

theorem ledger_advance_multiplier (t : LedgerTally) (s : LedgerStep)
    (next : LedgerTally) (h : ledgerAdvance t s = some next) :
    ledgerMultiplier next = ledgerMultiplier t + ledgerStepExponent s := by
  unfold ledgerAdvance at h
  dsimp only at h
  cases hf : (!natLE (ledgerFuel t+1) 64) with
  | false =>
    rw [ledger_bool_false _ _ _ hf] at h
    cases hc : (!s.commit) with
    | false =>
      rw [ledger_bool_false _ _ _ hc] at h
      cases hb : (!(natLE (snapCost s.trial).1 (snapCost s.before).1 && natLE ((snapCost s.trial).2+1) (snapCost s.before).2) || s.before.n != s.trial.n || !inputsKnown s.before.live s.trial.live || !ledgerWitnessOK s) with
      | false =>
        rw [ledger_bool_false _ _ _ hb] at h
        cases hk0 : (s.kind == 0) with
        | false =>
          rw [ledger_bool_false _ _ _ hk0] at h
          cases hk1 : (s.kind == 1) with
          | false =>
            rw [ledger_bool_false _ _ _ hk1] at h
            cases hk2 : (s.kind == 2) with
            | false =>
              rw [ledger_bool_false _ _ _ hk2] at h
              cases hk3 : (s.kind == 3) with
              | false =>
                rw [ledger_bool_false _ _ _ hk3] at h
                cases hk4 : (s.kind == 4) with
                | false =>
                  rw [ledger_bool_false _ _ _ hk4] at h
                  cases hk5 : (s.kind == 5) with
                  | false =>
                    rw [ledger_bool_false _ _ _ hk5] at h
                    cases h
                  | true =>
                    rw [ledger_bool_true _ _ _ hk5] at h
                    cases hr : ((removedIds s.before s.trial).length == 1) with
                    | false =>
                      rw [ledger_bool_false _ _ _ hr] at h
                      cases h
                    | true =>
                      rw [ledger_bool_true _ _ _ hr] at h
                      have he := Option.some.inj h
                      rw [← he]
                      rw [ledger_exponent_5 s hc hk5]
                      unfold ledgerMultiplier
                      rfl
                | true =>
                  rw [ledger_bool_true _ _ _ hk4] at h
                  cases hr : ((removedIds s.before s.trial).length == 2) with
                  | false =>
                    rw [ledger_bool_false _ _ _ hr] at h
                    cases h
                  | true =>
                    rw [ledger_bool_true _ _ _ hr] at h
                    have he := Option.some.inj h
                    rw [← he]
                    rw [ledger_exponent_4 s hc hk4]
                    unfold ledgerMultiplier
                    exact ledger_hh_arithmetic _ _ _
              | true =>
                rw [ledger_bool_true _ _ _ hk3] at h
                cases hr : ((removedIds s.before s.trial).length == 1 && freeSnapOK s.before s.trial) with
                | false =>
                  rw [ledger_bool_false _ _ _ hr] at h
                  cases h
                | true =>
                  rw [ledger_bool_true _ _ _ hr] at h
                  have he := Option.some.inj h
                  rw [← he]
                  rw [ledger_exponent_3 s hc hk3]
                  unfold ledgerMultiplier
                  exact ledger_free_arithmetic _ _ _
            | true =>
              rw [ledger_bool_true _ _ _ hk2] at h
              cases hr : ((removedIds s.before s.trial).length == 1) with
              | false =>
                rw [ledger_bool_false _ _ _ hr] at h
                cases h
              | true =>
                rw [ledger_bool_true _ _ _ hr] at h
                have he := Option.some.inj h
                rw [← he]
                rw [ledger_exponent_2 s hc hk2]
                unfold ledgerMultiplier
                rfl
          | true =>
            rw [ledger_bool_true _ _ _ hk1] at h
            cases hr : (natLE t.stage 1 && (removedIds s.before s.trial).length != 0 && freeSnapOK s.before s.trial) with
            | false =>
              rw [ledger_bool_false _ _ _ hr] at h
              cases h
            | true =>
              rw [ledger_bool_true _ _ _ hr] at h
              have he := Option.some.inj h
              rw [← he]
              rw [ledger_exponent_1 s hc hk1]
              unfold ledgerMultiplier
              exact ledger_batch_arithmetic _ _ _ _
        | true =>
          rw [ledger_bool_true _ _ _ hk0] at h
          cases hr : (t.stage == 0 && (removedIds s.before s.trial).length != 0) with
          | false =>
            rw [ledger_bool_false _ _ _ hr] at h
            cases h
          | true =>
            rw [ledger_bool_true _ _ _ hr] at h
            have he := Option.some.inj h
            rw [← he]
            rw [ledger_exponent_0 s hc hk0]
            unfold ledgerMultiplier
            rfl
      | true =>
        rw [ledger_bool_true _ _ _ hb] at h
        cases h
    | true =>
      rw [ledger_bool_true _ _ _ hc] at h
      cases hr : (natLE 2 s.kind && !(natLE (snapCost s.trial).1 (snapCost s.before).1 && natLE ((snapCost s.trial).2+1) (snapCost s.before).2)) with
      | false =>
        rw [ledger_bool_false _ _ _ hr] at h
        cases h
      | true =>
        rw [ledger_bool_true _ _ _ hr] at h
        have he := Option.some.inj h
        rw [← he]
        rw [ledger_exponent_rejected s hc]
        rfl
  | true =>
    rw [ledger_bool_true _ _ _ hf] at h
    cases h

-- Extract actual successful recursive calls (including fuel) from the
-- executable replay, rather than assuming an abstract ordered relation.
theorem replay_ledger_cons (current : LedgerSnap) (t : LedgerTally)
    (s : LedgerStep) (ss : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (h : replayLedger current t (s :: ss) = some (final,out)) :
    ∃ next, current.raw = s.before.raw ∧ ledgerAdvance t s = some next ∧
      natLE (ledgerFuel next) 64 = true ∧
      replayLedger (ledgerNext current s) next ss = some (final,out) := by
  cases hc : natListEq current.raw s.before.raw with
  | false => simp [replayLedger, hc] at h
  | true =>
    cases ha : ledgerAdvance t s with
    | none => simp [replayLedger, hc, ha] at h
    | some next =>
      cases hf : natLE (ledgerFuel next) 64 with
      | false => simp [replayLedger, hc, ha, hf] at h
      | true =>
        refine ⟨next, (nat_list_eq_iff _ _).mp hc, ?_, ?_, ?_⟩
        · first | exact ha | rfl
        · first | exact hf | rfl
        · simpa [replayLedger, hc, ha, hf] using h

theorem replay_ledger_multiplier (current : LedgerSnap) (t : LedgerTally)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (h : replayLedger current t steps = some (final,out)) :
    ledgerMultiplier out = ledgerMultiplier t + (steps.map ledgerStepExponent).sum := by
  induction steps generalizing current t with
  | nil =>
    change some (current,t) = some (final,out) at h
    cases h
    simp
  | cons s ss ih =>
    obtain ⟨next, _, hadv, _, htail⟩ := replay_ledger_cons current t s ss final out h
    have hm := ledger_advance_multiplier t s next hadv
    have ht := ih (ledgerNext current s) next htail
    rw [ht, hm]
    simp only [List.map_cons, List.sum_cons]
    omega

-- Semantic composition over the actual executable recursive calls.
-- Snapshot consistency and the semantics of each committed local rule
-- remain explicit premises; rejected proposals need no semantic law.
theorem replay_ledger_scale {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (current : LedgerSnap) (t : LedgerTally)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (chain : ∀ a b : LedgerSnap, a.raw = b.raw → value a = value b)
    (stepSound : ∀ s, s ∈ steps → s.commit = true →
      value s.before = scale (ledgerStepExponent s) (value s.trial))
    (h : replayLedger current t steps = some (final,out)) :
    value current = scale (steps.map ledgerStepExponent).sum (value final) := by
  induction steps generalizing current t with
  | nil =>
    change some (current,t) = some (final,out) at h
    cases h
    exact (h0 (value final)).symm
  | cons s ss ih =>
    obtain ⟨next, hchain, _, _, htail⟩ := replay_ledger_cons current t s ss final out h
    have hlocal : value current = scale (ledgerStepExponent s) (value (ledgerNext current s)) := by
      cases hc : s.commit with
      | false => simp [ledgerStepExponent, ledgerNext, hc, h0]
      | true =>
        rw [committed_ledger_next current s hc]
        exact (chain current s.before hchain).trans
          (stepSound s (List.mem_cons.mpr (Or.inl rfl)) hc)
    have ht := ih (ledgerNext current s) next
      (fun q hm => stepSound q (List.mem_cons.mpr (Or.inr hm))) htail
    exact hlocal.trans ((congrArg (scale (ledgerStepExponent s)) ht).trans
      (ha (ledgerStepExponent s) (ss.map ledgerStepExponent).sum (value final)))

theorem replay_ledger_scale_from_zero {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (current : LedgerSnap)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (chain : ∀ a b : LedgerSnap, a.raw = b.raw → value a = value b)
    (stepSound : ∀ s, s ∈ steps → s.commit = true →
      value s.before = scale (ledgerStepExponent s) (value s.trial))
    (h : replayLedger current {} steps = some (final,out)) :
    value current = scale (ledgerMultiplier out) (value final) := by
  have hm := replay_ledger_multiplier current {} steps final out h
  change ledgerMultiplier out = 0 + (steps.map ledgerStepExponent).sum at hm
  rw [Nat.zero_add] at hm
  rw [hm]
  exact replay_ledger_scale scale h0 ha value current {} steps final out chain stepSound h


-- Canonicality is a property of a successfully parsed record, not
-- an assumption about arbitrary records sharing a raw token.
def canonicalLedgerSnap (s : LedgerSnap) : Prop :=
  parseLedgerSnap s.raw = some s

theorem ledger_bind_some {A B : Type} (x : Option A) (f : A → Option B) (out : B)
    (h : x.bind f = some out) : ∃ a, x = some a ∧ f a = some out := by
  cases x with
  | none => cases h
  | some a => exact ⟨a, rfl, h⟩

theorem ledger_if_some_branch {A : Type} (b : Bool) (x : Option A) (out : A)
    (h : (if b then x else none) = some out) : x = some out := by
  cases b with
  | false => cases h
  | true => exact h

theorem parse_ledger_snap_raw (raw : Token) (s : LedgerSnap)
    (h : parseLedgerSnap raw = some s) : s.raw = raw := by
  unfold parseLedgerSnap at h
  generalize splitBytes 59 raw = fields at h
  cases fields with
  | nil => cases h
  | cons n tail =>
    cases tail with
    | nil => cases h
    | cons live tail =>
      cases tail with
      | nil => cases h
      | cons phase tail =>
        cases tail with
        | nil => cases h
        | cons cs tail =>
          cases tail with
          | cons extra rest => cases h
          | nil =>
            obtain ⟨nv, _, h1⟩ := ledger_bind_some _ _ _ h
            obtain ⟨ids, _, h2⟩ := ledger_bind_some _ _ _ h1
            -- Lean 4.36 elaborates conditional do-binds to join points.
            -- Eliminate the two sentinel guards before extracting binds.
            cases hp : (phase == [126]) with
            | false =>
              rw [ledger_bool_false _ _ _ hp] at h2
              obtain ⟨ps, _, h3⟩ := ledger_bind_some _ _ _ h2
              -- Normalize the applied phase join point explicitly. Keep
              -- the sentinel test at the head of the hypothesis.
              change (if cs == [33] then
                (some ([] : List (List (List Nat)))).bind (fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none)
                else (splitBytes 124 cs).mapM parseLedgerPoly >>= fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h3
              cases hc : (cs == [33]) with
              | false =>
                rw [ledger_bool_false _ _ _ hc] at h3
                obtain ⟨rs, _, h4⟩ := ledger_bind_some _ _ _ h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h4
                have he : some (LedgerSnap.mk raw nv ids phase cs ps rs) = some s :=
                  ledger_if_some_branch _ _ _ h4
                exact (congrArg LedgerSnap.raw (Option.some.inj he)).symm
              | true =>
                rw [ledger_bool_true _ _ _ hc] at h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      ([] : List (List (List Nat))).all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps [])
                  else none) = some s at h3
                have he : some (LedgerSnap.mk raw nv ids phase cs ps []) = some s :=
                  ledger_if_some_branch _ _ _ h3
                exact (congrArg LedgerSnap.raw (Option.some.inj he)).symm
            | true =>
              rw [ledger_bool_true _ _ _ hp] at h2
              obtain ⟨ps, _, h3⟩ := ledger_bind_some _ _ _ h2
              -- Normalize the applied phase join point explicitly. Keep
              -- the sentinel test at the head of the hypothesis.
              change (if cs == [33] then
                (some ([] : List (List (List Nat)))).bind (fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none)
                else (splitBytes 124 cs).mapM parseLedgerPoly >>= fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h3
              cases hc : (cs == [33]) with
              | false =>
                rw [ledger_bool_false _ _ _ hc] at h3
                obtain ⟨rs, _, h4⟩ := ledger_bind_some _ _ _ h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h4
                have he : some (LedgerSnap.mk raw nv ids phase cs ps rs) = some s :=
                  ledger_if_some_branch _ _ _ h4
                exact (congrArg LedgerSnap.raw (Option.some.inj he)).symm
              | true =>
                rw [ledger_bool_true _ _ _ hc] at h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      ([] : List (List (List Nat))).all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps [])
                  else none) = some s at h3
                have he : some (LedgerSnap.mk raw nv ids phase cs ps []) = some s :=
                  ledger_if_some_branch _ _ _ h3
                exact (congrArg LedgerSnap.raw (Option.some.inj he)).symm

theorem parsed_ledger_snap_canonical (raw : Token) (s : LedgerSnap)
    (h : parseLedgerSnap raw = some s) : canonicalLedgerSnap s := by
  unfold canonicalLedgerSnap
  rw [parse_ledger_snap_raw raw s h]
  exact h

theorem canonical_ledger_snap_eq (a b : LedgerSnap)
    (ha : canonicalLedgerSnap a) (hb : canonicalLedgerSnap b)
    (hr : a.raw = b.raw) : a = b := by
  unfold canonicalLedgerSnap at ha hb
  rw [hr, hb] at ha
  exact (Option.some.inj ha).symm

theorem parse_ledger_step_canonical (tokens : List Token) (s : LedgerStep)
    (h : parseLedgerStep tokens = some s) :
    canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial := by
  cases tokens with
  | nil => cases h
  | cons tag tail =>
    cases tail with
    | nil => cases h
    | cons k tail =>
      cases tail with
      | nil => cases h
      | cons c tail =>
        cases tail with
        | nil => cases h
        | cons wi tail =>
          cases tail with
          | nil => cases h
          | cons b tail =>
            cases tail with
            | nil => cases h
            | cons a tail =>
              cases tail with
              | cons extra rest => cases h
              | nil =>
                unfold parseLedgerStep at h
                have h0 := ledger_if_some_branch _ _ _ h
                obtain ⟨kind, _, h1⟩ := ledger_bind_some _ _ _ h0
                obtain ⟨commit, _, h2⟩ := ledger_bind_some _ _ _ h1
                obtain ⟨before, hb, h3⟩ := ledger_bind_some _ _ _ h2
                obtain ⟨trial, ht, h4⟩ := ledger_bind_some _ _ _ h3
                have he : some (LedgerStep.mk kind (commit == 1) wi before trial) = some s :=
                  ledger_if_some_branch _ _ _ h4
                have hs := Option.some.inj he
                rw [← hs]
                exact ⟨parsed_ledger_snap_canonical b before hb,
                  parsed_ledger_snap_canonical a trial ht⟩

theorem ledger_next_canonical (current : LedgerSnap) (s : LedgerStep)
    (hc : canonicalLedgerSnap current) (ht : canonicalLedgerSnap s.trial) :
    canonicalLedgerSnap (ledgerNext current s) := by
  cases h : s.commit with
  | false => rw [rejected_ledger_next current s h]; exact hc
  | true => rw [committed_ledger_next current s h]; exact ht

theorem replay_ledger_canonical (current : LedgerSnap) (t : LedgerTally)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (hc : canonicalLedgerSnap current)
    (hs : ∀ s, s ∈ steps → canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial)
    (h : replayLedger current t steps = some (final,out)) :
    canonicalLedgerSnap final := by
  induction steps generalizing current t with
  | nil =>
    change some (current,t) = some (final,out) at h
    cases h
    exact hc
  | cons s ss ih =>
    obtain ⟨next, _, _, _, htail⟩ := replay_ledger_cons current t s ss final out h
    have hnext := ledger_next_canonical current s hc (hs s (List.mem_cons.mpr (Or.inl rfl))).2
    exact ih (ledgerNext current s) next hnext
      (fun q hm => hs q (List.mem_cons.mpr (Or.inr hm))) htail

-- No arbitrary raw-equality semantic premise: both chain records
-- are canonical, so equality is obtained from parser determinism.
theorem replay_ledger_canonical_scale {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (current : LedgerSnap) (t : LedgerTally)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (hc : canonicalLedgerSnap current)
    (hs : ∀ s, s ∈ steps → canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial)
    (stepSound : ∀ s, s ∈ steps → s.commit = true →
      value s.before = scale (ledgerStepExponent s) (value s.trial))
    (h : replayLedger current t steps = some (final,out)) :
    value current = scale (steps.map ledgerStepExponent).sum (value final) := by
  induction steps generalizing current t with
  | nil =>
    change some (current,t) = some (final,out) at h
    cases h
    exact (h0 (value final)).symm
  | cons s ss ih =>
    obtain ⟨next, hchain, _, _, htail⟩ := replay_ledger_cons current t s ss final out h
    have hstep := hs s (List.mem_cons.mpr (Or.inl rfl))
    have he := canonical_ledger_snap_eq current s.before hc hstep.1 hchain
    have hlocal : value current = scale (ledgerStepExponent s) (value (ledgerNext current s)) := by
      cases hcommit : s.commit with
      | false => simp [ledgerStepExponent, ledgerNext, hcommit, h0]
      | true =>
        rw [committed_ledger_next current s hcommit]
        exact (congrArg value he).trans (stepSound s (List.mem_cons.mpr (Or.inl rfl)) hcommit)
    have ht := ih (ledgerNext current s) next
      (ledger_next_canonical current s hc hstep.2)
      (fun q hm => hs q (List.mem_cons.mpr (Or.inr hm)))
      (fun q hm => stepSound q (List.mem_cons.mpr (Or.inr hm))) htail
    exact hlocal.trans ((congrArg (scale (ledgerStepExponent s)) ht).trans
      (ha (ledgerStepExponent s) (ss.map ledgerStepExponent).sum (value final)))

theorem replay_ledger_canonical_scale_from_zero {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (current : LedgerSnap)
    (steps : List LedgerStep) (final : LedgerSnap) (out : LedgerTally)
    (hc : canonicalLedgerSnap current)
    (hs : ∀ s, s ∈ steps → canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial)
    (stepSound : ∀ s, s ∈ steps → s.commit = true →
      value s.before = scale (ledgerStepExponent s) (value s.trial))
    (h : replayLedger current {} steps = some (final,out)) :
    value current = scale (ledgerMultiplier out) (value final) := by
  have hm := replay_ledger_multiplier current {} steps final out h
  change ledgerMultiplier out = 0 + (steps.map ledgerStepExponent).sum at hm
  rw [Nat.zero_add] at hm
  rw [hm]
  exact replay_ledger_canonical_scale scale h0 ha value current {} steps final out hc hs stepSound h


-- Canonicality for the actual list parser, using the pinned core
-- mapM_cons equation rather than a new certificate parser.
theorem parse_ledger_steps_canonical (tokens : List (List Token))
    (steps : List LedgerStep) (h : tokens.mapM parseLedgerStep = some steps) :
    ∀ s, s ∈ steps → canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial := by
  induction tokens generalizing steps with
  | nil =>
    change some [] = some steps at h
    cases h
    intro s hm
    cases hm
  | cons row rest ih =>
    rw [List.mapM_cons] at h
    obtain ⟨first, hf, ht⟩ := ledger_bind_some _ _ _ h
    obtain ⟨tail, hr, he⟩ := ledger_bind_some _ _ _ ht
    have he' : some (first :: tail) = some steps := he
    have hs := Option.some.inj he'
    intro s hm
    rw [← hs] at hm
    rcases List.mem_cons.mp hm with hh | hh
    · subst s
      exact parse_ledger_step_canonical row first hf
    · exact ih tail hr s hh

-- Preserve the exact token origin of each witness, including the
-- header and both endpoints. No external parser correctness assumed.
def LedgerByteWitness (bytes : List Nat) : Prop :=
  ∃ (tag norm k : Token) (counts : List Token) (st start : Token)
    (rest : List (List Token)) (et last : Token) (rev : List (List Token))
    (n mult : Nat) (expected : List Nat) (initial : LedgerSnap)
    (steps : List LedgerStep) (final : LedgerSnap) (t : LedgerTally),
    ascii bytes = true ∧
    rows bytes = (tag :: norm :: k :: counts) :: [st,start] :: rest ∧
    (tag == [99,114,114,45,108,101,100,103,101,114,45,118,50] &&
      st == [115,116,97,114,116] && counts.length == 7) = true ∧
    parseNatToken norm = some n ∧ parseNatToken k = some mult ∧
    counts.mapM parseNatToken = some expected ∧
    parseLedgerSnap start = some initial ∧ rest.reverse = [et,last] :: rev ∧
    (et == [101,110,100]) = true ∧ n = initial.n + initial.live.length ∧
    rev.reverse.mapM parseLedgerStep = some steps ∧
    parseLedgerSnap last = some final ∧
    replayLedger initial {} steps = some (final,t) ∧
    ledgerTallyList t = expected ∧ ledgerMultiplier t = mult

-- Once the executable checker accepts its final Boolean tests,
-- raw equality is upgraded to typed equality using canonicality.
theorem ledger_accepted_endpoint (initial actual final : LedgerSnap)
    (steps : List LedgerStep) (t : LedgerTally) (expected : List Nat) (mult : Nat)
    (hc : canonicalLedgerSnap initial) (hf : canonicalLedgerSnap final)
    (hs : ∀ s, s ∈ steps → canonicalLedgerSnap s.before ∧ canonicalLedgerSnap s.trial)
    (hr : replayLedger initial {} steps = some (actual,t))
    (h : (natListEq actual.raw final.raw &&
      natListEq (ledgerTallyList t) expected && ledgerMultiplier t == mult) = true) :
    replayLedger initial {} steps = some (final,t) ∧
      ledgerTallyList t = expected ∧ ledgerMultiplier t = mult := by
  have hp := and_true_parts h
  have hq := and_true_parts hp.1
  have ha := replay_ledger_canonical initial {} steps actual t hc hs hr
  have he := canonical_ledger_snap_eq actual final ha hf
    ((nat_list_eq_iff _ _).mp hq.1)
  rw [he] at hr
  exact ⟨hr, (nat_list_eq_iff _ _).mp hq.2, ledger_kind_eq _ _ hp.2⟩

-- Extract witnesses from checkLedger itself, not from an independently
-- asserted successful parse. Generalization isolates actual match
-- scrutinees before constructive case analysis.
theorem check_ledger_byte_witness (bytes : List Nat)
    (h : checkLedger bytes = true) : LedgerByteWitness bytes := by
  unfold checkLedger at h
  generalize ha : ascii bytes = aok at h
  cases aok with
  | false => cases h
  | true =>
    try dsimp only at h
    generalize hrows : rows bytes = records at h
    cases records with
    | nil => cases h
    | cons header restRows =>
      cases header with
      | nil => cases h
      | cons tag tail =>
        cases tail with
        | nil => cases h
        | cons norm tail =>
          cases tail with
          | nil => cases h
          | cons k counts =>
            cases restRows with
            | nil => cases h
            | cons startRow rest =>
              cases startRow with
              | nil => cases h
              | cons st tail =>
                cases tail with
                | nil => cases h
                | cons start tail =>
                  cases tail with
                  | cons extra more => cases h
                  | nil =>
                    try dsimp only at h
                    generalize hg : (tag == [99,114,114,45,108,101,100,103,101,114,45,118,50] &&
                      st == [115,116,97,114,116] && counts.length == 7) = gok at h
                    cases gok with
                    | false => cases h
                    | true =>
                      try dsimp only at h
                      generalize hn : parseNatToken norm = pn at h
                      cases pn with
                      | none => cases h
                      | some n =>
                        generalize hm : parseNatToken k = pm at h
                        cases pm with
                        | none => cases h
                        | some mult =>
                          generalize hcounts : counts.mapM parseNatToken = pc at h
                          cases pc with
                          | none => cases h
                          | some expected =>
                            generalize hi : parseLedgerSnap start = pi at h
                            cases pi with
                            | none => cases h
                            | some initial =>
                              generalize hrev : rest.reverse = reversed at h
                              cases reversed with
                              | nil => cases h
                              | cons endRow rev =>
                                cases endRow with
                                | nil => cases h
                                | cons et tail =>
                                  cases tail with
                                  | nil => cases h
                                  | cons last tail =>
                                    cases tail with
                                    | cons extra more => cases h
                                    | nil =>
                                      try dsimp only at h
                                      generalize he : (et == [101,110,100] &&
                                        n == initial.n+initial.live.length) = eok at h
                                      cases eok with
                                      | false => cases h
                                      | true =>
                                        try dsimp only at h
                                        generalize hs : rev.reverse.mapM parseLedgerStep = ps at h
                                        cases ps with
                                        | none => cases h
                                        | some steps =>
                                          generalize hf : parseLedgerSnap last = pf at h
                                          cases pf with
                                          | none => cases h
                                          | some final =>
                                            -- Expose the actual replay scrutinee before
                                            -- eliminating its Option result; outer true
                                            -- guards and the paired parser match reduce
                                            -- definitionally, not by dependent elimination.
                                            change (match replayLedger initial {} steps with
                                              | some (actual,t) => natListEq actual.raw final.raw &&
                                                  natListEq (ledgerTallyList t) expected &&
                                                  ledgerMultiplier t == mult
                                              | none => false) = true at h
                                            cases hr : replayLedger initial {} steps with
                                            | none =>
                                              have hfalse : false = true := by
                                                first | exact h | simpa only [hr] using h
                                              cases hfalse
                                            | some result =>
                                              cases result with
                                              | mk actual t =>
                                                have haccepted : (natListEq actual.raw final.raw &&
                                                  natListEq (ledgerTallyList t) expected &&
                                                  ledgerMultiplier t == mult) = true := by
                                                  first | exact h | simpa only [hr] using h
                                                have hhead := and_true_parts he
                                                have hc := parsed_ledger_snap_canonical start initial hi
                                                have hfinal := parsed_ledger_snap_canonical last final hf
                                                have hsteps := parse_ledger_steps_canonical _ steps hs
                                                have hend := ledger_accepted_endpoint initial actual final steps t
                                                  expected mult hc hfinal hsteps hr haccepted
                                                exact ⟨tag,norm,k,counts,st,start,rest,et,last,rev,n,mult,
                                                  expected,initial,steps,final,t,ha,hrows,hg,hn,hm,hcounts,hi,hrev,
                                                  hhead.1,ledger_kind_eq _ _ hhead.2,hs,hf,hend.1,hend.2.1,hend.2.2⟩

-- A certificate-level semantic corollary with local committed-rule
-- semantics still explicit. The accepted byte witness supplies
-- canonicality, typed endpoint equality and multiplier binding.
theorem check_ledger_witness_scale {A : Type} (scale : Nat → A → A)
    (h0 : ∀ a, scale 0 a = a)
    (ha : ∀ i j a, scale i (scale j a) = scale (i+j) a)
    (value : LedgerSnap → A) (bytes : List Nat)
    (h : checkLedger bytes = true)
    (localSound : ∀ s : LedgerStep, canonicalLedgerSnap s.before →
      canonicalLedgerSnap s.trial → s.commit = true →
      value s.before = scale (ledgerStepExponent s) (value s.trial)) :
    ∃ (initial final : LedgerSnap) (steps : List LedgerStep) (t : LedgerTally)
      (n mult : Nat) (start last : Token),
      parseLedgerSnap start = some initial ∧ parseLedgerSnap last = some final ∧
      n = initial.n + initial.live.length ∧
      replayLedger initial {} steps = some (final,t) ∧
      ledgerMultiplier t = mult ∧ value initial = scale mult (value final) := by
  obtain ⟨_tag,_norm,_k,_counts,_st,start,_rest,_et,last,rev,n,mult,_expected,
    initial,steps,final,t,_ascii,_rows,_head,_hn,_hm,_hcounts,hi,_rev,_end,hnorm,hs,hf,hr,_ht,hmult⟩ :=
    check_ledger_byte_witness bytes h
  have hc := parsed_ledger_snap_canonical start initial hi
  have hsteps := parse_ledger_steps_canonical rev.reverse steps hs
  have hv := replay_ledger_canonical_scale_from_zero scale h0 ha value initial steps final t
    hc hsteps (fun s hm hcommit => localSound s (hsteps s hm).1 (hsteps s hm).2 hcommit) hr
  rw [hmult] at hv
  exact ⟨initial,final,steps,t,n,mult,start,last,hi,hf,hnorm,hr,hmult,hv⟩


-- Derive support exclusion from the actual Boolean predicate,
-- independently of the interpretation of phase coefficients.
theorem ledger_removed_ids_iff (a b : LedgerSnap) (x : Nat) :
    x ∈ removedIds a b ↔ x ∈ a.live ∧ x ∉ b.live := by
  unfold removedIds
  constructor
  · intro h
    have hp := List.mem_filter.mp h
    exact ⟨hp.1, fresh_not_mem x b.live hp.2⟩
  · intro h
    apply List.mem_filter.mpr
    refine ⟨h.1, ?_⟩
    cases he : natMem x b.live with
    | false => rfl
    | true => exact False.elim (h.2 ((nat_mem_iff x b.live).mp he))

theorem ledger_no_any_member {A : Type} (xs : List A) (p : A → Bool)
    (h : (!xs.any p) = true) (x : A) (hm : x ∈ xs) (hp : p x = true) :
    False := by
  have he : xs.any p = true := List.any_eq_true.mpr ⟨x, hm, hp⟩
  rw [he] at h
  cases h

theorem free_snapshot_support_exclusion (a b : LedgerSnap) (h : freeSnapOK a b = true) :
    ∀ x, x ∈ removedIds a b →
      (∀ m, m ∈ a.phaseSupport → x ∉ m) ∧
      (∀ row, row ∈ a.constraints → ∀ m, m ∈ row → x ∉ m) := by
  have hh : ((natListEq a.phaseText b.phaseText && natListEq a.rowText b.rowText) &&
    (removedIds a b).all (fun x => !(a.phaseSupport.any (natMem x)) &&
      !(a.constraints.any (fun row => row.any (natMem x))))) = true := h
  intro x hx
  have hp := and_true_parts
    (List.all_eq_true.mp (and_true_parts hh).2 x hx)
  constructor
  · intro m hm hmem
    exact ledger_no_any_member a.phaseSupport (natMem x) hp.1 m hm
      ((nat_mem_iff x m).mpr hmem)
  · intro row hr m hm hmem
    have hrow : row.any (natMem x) = true :=
      List.any_eq_true.mpr ⟨m, hm, (nat_mem_iff x m).mpr hmem⟩
    exact ledger_no_any_member a.constraints (fun r => r.any (natMem x))
      hp.2 row hr hrow

theorem ledger_advance_free_obligations (t next : LedgerTally) (s : LedgerStep)
    (hc : s.commit = true) (hk : s.kind = 1 ∨ s.kind = 3)
    (h : ledgerAdvance t s = some next) :
    inputsKnown s.before.live s.trial.live = true ∧
      freeSnapOK s.before s.trial = true ∧
      ledgerStepExponent s = 2 * (removedIds s.before s.trial).length := by
  have hcommit : (!s.commit) = false := by rw [hc] <;> rfl
  unfold ledgerAdvance at h
  dsimp only at h
  cases hf : (!natLE (ledgerFuel t+1) 64) with
  | true =>
    rw [ledger_bool_true _ _ _ hf] at h
    cases h
  | false =>
    rw [ledger_bool_false _ _ _ hf, ledger_bool_false _ _ _ hcommit] at h
    cases hb : (!(natLE (snapCost s.trial).1 (snapCost s.before).1 &&
      natLE ((snapCost s.trial).2+1) (snapCost s.before).2) ||
      s.before.n != s.trial.n || !inputsKnown s.before.live s.trial.live ||
      !ledgerWitnessOK s) with
    | true =>
      rw [ledger_bool_true _ _ _ hb] at h
      cases h
    | false =>
      rw [ledger_bool_false _ _ _ hb] at h
      have hsubset : inputsKnown s.before.live s.trial.live = true := by
        cases he : inputsKnown s.before.live s.trial.live with
        | true => rfl
        | false => simp [he] at hb
      rcases hk with hk | hk
      · rw [hk] at h
        change (if natLE t.stage 1 && (removedIds s.before s.trial).length != 0 &&
          freeSnapOK s.before s.trial then
            some { t with free := t.free+(removedIds s.before s.trial).length, batchFree := (removedIds s.before s.trial).length, stage := 2 }
          else none) = some next at h
        cases hr : (natLE t.stage 1 && (removedIds s.before s.trial).length != 0 &&
          freeSnapOK s.before s.trial) with
        | false =>
          rw [ledger_bool_false _ _ _ hr] at h
          cases h
        | true =>
          have hkind : (s.kind == 1) = true := by rw [hk] <;> rfl
          exact ⟨hsubset, (and_true_parts hr).2, ledger_exponent_1 s hcommit hkind⟩
      · rw [hk] at h
        change (if (removedIds s.before s.trial).length == 1 &&
          freeSnapOK s.before s.trial then
            some { t with free := t.free+1, stage := 2 }
          else none) = some next at h
        cases hr : ((removedIds s.before s.trial).length == 1 &&
          freeSnapOK s.before s.trial) with
        | false =>
          rw [ledger_bool_false _ _ _ hr] at h
          cases h
        | true =>
          have hp := and_true_parts hr
          have hd := ledger_kind_eq _ _ hp.1
          have hkind : (s.kind == 3) = true := by rw [hk] <;> rfl
          have hx := ledger_exponent_3 s hcommit hkind
          rw [hd]
          exact ⟨hsubset, hp.2, hx⟩

theorem ledger_advance_free_support (t next : LedgerTally) (s : LedgerStep)
    (hc : s.commit = true) (hk : s.kind = 1 ∨ s.kind = 3)
    (h : ledgerAdvance t s = some next) :
    (∀ x, x ∈ s.trial.live → x ∈ s.before.live) ∧
    s.before.phaseText = s.trial.phaseText ∧ s.before.rowText = s.trial.rowText ∧
    (∀ x, x ∈ removedIds s.before s.trial →
      (∀ m, m ∈ s.before.phaseSupport → x ∉ m) ∧
      (∀ row, row ∈ s.before.constraints → ∀ m, m ∈ row → x ∉ m)) ∧
    ledgerStepExponent s = 2 * (removedIds s.before s.trial).length := by
  have hp := ledger_advance_free_obligations t next s hc hk h
  have htext := free_snapshot_payload s.before s.trial hp.2.1
  exact ⟨inputs_known_sound _ _ hp.1, htext.1, htext.2,
    free_snapshot_support_exclusion _ _ hp.2.1, hp.2.2⟩

-- Exact repeated doubling, assuming only addition. Binding this
-- prefix split to the live-ID ordering and phase/guard evaluation
-- remains a separate refinement obligation.
def freeDouble {A : Type} [Add A] : Nat → A → A
  | 0, a => a
  | n+1, a => freeDouble n a + freeDouble n a

theorem sum_bits_free_prefix {A : Type} [Add A] (d n : Nat)
    (f : List Bool → A) (g : List Bool → A)
    (h : ∀ xs ys : List Bool, xs.length = d → ys.length = n → f (xs ++ ys) = g ys) :
    sumBits (d+n) f = freeDouble d (sumBits n g) := by
  induction d generalizing f with
  | zero =>
    rw [Nat.zero_add]
    exact sum_bits_congr n f g (fun ys hy => h [] ys rfl hy)
  | succ d ih =>
    rw [Nat.succ_add]
    change sumBits (d+n) (fun xs => f (false :: xs)) +
      sumBits (d+n) (fun xs => f (true :: xs)) =
      freeDouble d (sumBits n g) + freeDouble d (sumBits n g)
    have hfalse : ∀ xs ys : List Bool, xs.length = d → ys.length = n →
        f (false :: (xs ++ ys)) = g ys := by
      intro xs ys hx hy
      exact h (false :: xs) ys (congrArg Nat.succ hx) hy
    have htrue : ∀ xs ys : List Bool, xs.length = d → ys.length = n →
        f (true :: (xs ++ ys)) = g ys := by
      intro xs ys hx hy
      exact h (true :: xs) ys (congrArg Nat.succ hx) hy
    rw [ih _ hfalse, ih _ htrue]


-- Bind every relevant typed field to the successful actual parser.
-- In particular, equal payload text is not assumed to imply equal
-- typed fields for arbitrary noncanonical records.
def LedgerSnapFields (s : LedgerSnap) : Prop :=
  (natLE s.n 4096 && uniqueIds s.live && inputsKnown s.live (List.range s.n) &&
    s.phaseSupport.all (fun m => uniqueIds m && inputsKnown s.live m) &&
    s.constraints.all (fun p => p.all (fun m => uniqueIds m && inputsKnown s.live m))) = true ∧
  (if s.phaseText == [126] then some [] else
    (splitBytes 124 s.phaseText).mapM parseLedgerPhase) = some s.phaseSupport ∧
  (if s.rowText == [33] then some [] else
    (splitBytes 124 s.rowText).mapM parseLedgerPoly) = some s.constraints

theorem ledger_snap_fields_of_admission (raw phase cs : Token) (nv : Nat)
    (ids : List Nat) (ps : List (List Nat)) (rs : List (List (List Nat))) (s : LedgerSnap)
    (hp : (if phase == [126] then some [] else
      (splitBytes 124 phase).mapM parseLedgerPhase) = some ps)
    (hr : (if cs == [33] then some [] else
      (splitBytes 124 cs).mapM parseLedgerPoly) = some rs)
    (h : (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
        some (LedgerSnap.mk raw nv ids phase cs ps rs) else none) = some s) :
    LedgerSnapFields s := by
  cases hb : (natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m))) with
  | false =>
    rw [ledger_bool_false _ _ _ hb] at h
    cases h
  | true =>
    rw [ledger_bool_true _ _ _ hb] at h
    have he := Option.some.inj h
    rw [← he]
    exact ⟨hb, hp, hr⟩

theorem parse_ledger_snap_fields (raw : Token) (s : LedgerSnap)
    (h : parseLedgerSnap raw = some s) : LedgerSnapFields s := by
  unfold parseLedgerSnap at h
  generalize splitBytes 59 raw = fields at h
  cases fields with
  | nil => cases h
  | cons n tail =>
    cases tail with
    | nil => cases h
    | cons live tail =>
      cases tail with
      | nil => cases h
      | cons phase tail =>
        cases tail with
        | nil => cases h
        | cons cs tail =>
          cases tail with
          | cons extra rest => cases h
          | nil =>
            obtain ⟨nv, _, h1⟩ := ledger_bind_some _ _ _ h
            obtain ⟨ids, _, h2⟩ := ledger_bind_some _ _ _ h1
            -- Lean 4.36 elaborates conditional do-binds to join points.
            -- Eliminate the two sentinel guards before extracting binds.
            cases hp : (phase == [126]) with
            | false =>
              rw [ledger_bool_false _ _ _ hp] at h2
              obtain ⟨ps, hps, h3⟩ := ledger_bind_some _ _ _ h2
              have hphase : (if phase == [126] then some [] else
                  (splitBytes 124 phase).mapM parseLedgerPhase) = some ps :=
                (ledger_bool_false _ _ _ hp).trans hps
              -- Normalize the applied phase join point explicitly. Keep
              -- the sentinel test at the head of the hypothesis.
              change (if cs == [33] then
                (some ([] : List (List (List Nat)))).bind (fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none)
                else (splitBytes 124 cs).mapM parseLedgerPoly >>= fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h3
              cases hc : (cs == [33]) with
              | false =>
                rw [ledger_bool_false _ _ _ hc] at h3
                obtain ⟨rs, hrs, h4⟩ := ledger_bind_some _ _ _ h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h4
                have hrows : (if cs == [33] then some [] else
                    (splitBytes 124 cs).mapM parseLedgerPoly) = some rs :=
                  (ledger_bool_false _ _ _ hc).trans hrs
                exact ledger_snap_fields_of_admission raw phase cs nv ids ps rs s hphase hrows h4
              | true =>
                rw [ledger_bool_true _ _ _ hc] at h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      ([] : List (List (List Nat))).all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps [])
                  else none) = some s at h3
                have hrows : (if cs == [33] then some [] else
                    (splitBytes 124 cs).mapM parseLedgerPoly) = some [] :=
                  ledger_bool_true _ _ _ hc
                exact ledger_snap_fields_of_admission raw phase cs nv ids ps [] s hphase hrows h3
            | true =>
              rw [ledger_bool_true _ _ _ hp] at h2
              obtain ⟨ps, hps, h3⟩ := ledger_bind_some _ _ _ h2
              have hphase : (if phase == [126] then some [] else
                  (splitBytes 124 phase).mapM parseLedgerPhase) = some ps :=
                (ledger_bool_true _ _ _ hp).trans hps
              -- Normalize the applied phase join point explicitly. Keep
              -- the sentinel test at the head of the hypothesis.
              change (if cs == [33] then
                (some ([] : List (List (List Nat)))).bind (fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none)
                else (splitBytes 124 cs).mapM parseLedgerPoly >>= fun rs =>
                  if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                    some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h3
              cases hc : (cs == [33]) with
              | false =>
                rw [ledger_bool_false _ _ _ hc] at h3
                obtain ⟨rs, hrs, h4⟩ := ledger_bind_some _ _ _ h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      rs.all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps rs)
                  else none) = some s at h4
                have hrows : (if cs == [33] then some [] else
                    (splitBytes 124 cs).mapM parseLedgerPoly) = some rs :=
                  (ledger_bool_false _ _ _ hc).trans hrs
                exact ledger_snap_fields_of_admission raw phase cs nv ids ps rs s hphase hrows h4
              | true =>
                rw [ledger_bool_true _ _ _ hc] at h3
                change (if natLE nv 4096 && uniqueIds ids && inputsKnown ids (List.range nv) &&
                      ps.all (fun m => uniqueIds m && inputsKnown ids m) &&
                      ([] : List (List (List Nat))).all (fun p => p.all (fun m => uniqueIds m && inputsKnown ids m)) then
                  some (LedgerSnap.mk raw nv ids phase cs ps [])
                  else none) = some s at h3
                have hrows : (if cs == [33] then some [] else
                    (splitBytes 124 cs).mapM parseLedgerPoly) = some [] :=
                  ledger_bool_true _ _ _ hc
                exact ledger_snap_fields_of_admission raw phase cs nv ids ps [] s hphase hrows h3

theorem canonical_ledger_snap_fields (s : LedgerSnap) (h : canonicalLedgerSnap s) :
    LedgerSnapFields s :=
  parse_ledger_snap_fields s.raw s h

theorem canonical_ledger_live_admission (s : LedgerSnap) (h : canonicalLedgerSnap s) :
    uniqueIds s.live = true ∧ inputsKnown s.live (List.range s.n) = true ∧
    s.phaseSupport.all (fun m => uniqueIds m && inputsKnown s.live m) = true ∧
    s.constraints.all (fun p => p.all (fun m => uniqueIds m && inputsKnown s.live m)) = true := by
  have hf := canonical_ledger_snap_fields s h
  have hvalid : (natLE s.n 4096 && uniqueIds s.live && inputsKnown s.live (List.range s.n) &&
    s.phaseSupport.all (fun m => uniqueIds m && inputsKnown s.live m) &&
    s.constraints.all (fun p => p.all (fun m => uniqueIds m && inputsKnown s.live m))) = true := hf.1
  have h1 := and_true_parts hvalid
  have h2 := and_true_parts h1.1
  have h3 := and_true_parts h2.1
  have h4 := and_true_parts h3.1
  exact ⟨h4.2, h3.2, h2.2, h1.2⟩

theorem free_snapshot_typed_payload (a b : LedgerSnap)
    (ha : canonicalLedgerSnap a) (hb : canonicalLedgerSnap b) (h : freeSnapOK a b = true) :
    a.phaseSupport = b.phaseSupport ∧ a.constraints = b.constraints := by
  have htext := free_snapshot_payload a b h
  have hfa := canonical_ledger_snap_fields a ha
  have hfb := canonical_ledger_snap_fields b hb
  have hp := hfa.2.1
  have hr := hfa.2.2
  rw [htext.1] at hp
  rw [htext.2] at hr
  exact ⟨Option.some.inj (hp.symm.trans hfb.2.1),
    Option.some.inj (hr.symm.trans hfb.2.2)⟩

theorem canonical_ledger_support_known (s : LedgerSnap) (h : canonicalLedgerSnap s) :
    (∀ m, m ∈ s.phaseSupport → ∀ x, x ∈ m → x ∈ s.live) ∧
    (∀ row, row ∈ s.constraints → ∀ m, m ∈ row → ∀ x, x ∈ m → x ∈ s.live) := by
  have hp := canonical_ledger_live_admission s h
  constructor
  · intro m hm
    have hk := and_true_parts (List.all_eq_true.mp hp.2.2.1 m hm)
    exact inputs_known_sound _ _ hk.2
  · intro row hr m hm
    have hrow := List.all_eq_true.mp hp.2.2.2 row hr
    have hk := and_true_parts (List.all_eq_true.mp hrow m hm)
    exact inputs_known_sound _ _ hk.2

-- Equal parsed supports and canonical trial admission imply that all
-- original support is retained. This does not yet interpret phase
-- coefficients or prove the live enumeration permutation.
theorem free_snapshot_retained_support (a b : LedgerSnap)
    (ha : canonicalLedgerSnap a) (hb : canonicalLedgerSnap b) (h : freeSnapOK a b = true) :
    (∀ m, m ∈ a.phaseSupport → ∀ x, x ∈ m → x ∈ b.live) ∧
    (∀ row, row ∈ a.constraints → ∀ m, m ∈ row → ∀ x, x ∈ m → x ∈ b.live) := by
  have he := free_snapshot_typed_payload a b ha hb h
  rw [he.1, he.2]
  exact canonical_ledger_support_known b hb

-- Localize any unexpected dependency to a definition vs theorem.
#print axioms splitBytes
#print axioms digits
#print axioms ascii
#print axioms rows
#print axioms parseNatToken
#print axioms parseIntToken
#print axioms parseRecord
#print axioms parseGate
#print axioms intEq
#print axioms literalValid
#print axioms clauseSort
#print axioms finishClause
#print axioms parseClause
#print axioms parseCnfRows
#print axioms parseCnf
#print axioms bagEqBy
#print axioms covers
#print axioms satisfies
#print axioms checkRows
#print axioms replayRows
#print axioms acceptResult
#print axioms checkParsed
#print axioms check
#print axioms and_forward
#print axioms and_nary
#print axioms clause_eq_iff
#print axioms clause_mem_iff
#print axioms and_true_parts
#print axioms covers_iff
#print axioms check_rows_sound
#print axioms accepted_rows_sound
#print axioms byte_check_sound
#print axioms row_truth_iff
#print axioms cnf_truth_iff
#print axioms bool_true_iff_eq
#print axioms row_truth_sort
#print axioms cnf_truth_append
#print axioms cnf_truth_sorted
#print axioms and_forward_rows
#print axioms negative_row
#print axioms actual_and_rows_sound
#print axioms actual_xor_rows_sound
#print axioms actual_eq_rows_sound
#print axioms actual_zero_row_sound
#print axioms recordRows
#print axioms recordsRows
#print axioms natMem
#print axioms inputsKnown
#print axioms liveIds
#print axioms gateOutput
#print axioms gateInputs
#print axioms nextSeen
#print axioms topo
#print axioms finalSeen
#print axioms replayWeights
#print axioms recordSem
#print axioms recordCoherent
#print axioms recordsSem
#print axioms agreeOn
#print axioms actual_record_rows_sound
#print axioms satisfies_append
#print axioms actual_records_rows_sound
#print axioms replay_rows_binding
#print axioms accepted_records_sound
#print axioms nat_mem_iff
#print axioms inputs_known_sound
#print axioms and_value_agree
#print axioms agree_cons
#print axioms gate_agreement_step
#print axioms topological_agreement
#print axioms accepted_assignment_unique
#print axioms dimacsIds
#print axioms domainCheck
#print axioms liftVal
#print axioms setVal
#print axioms gateValue
#print axioms stepVal
#print axioms extendVal
#print axioms defSem
#print axioms defsSem
#print axioms guardTruth
#print axioms replay_domain_checked
#print axioms domain_membership
#print axioms dimacs_ids_iff
#print axioms accepted_domain_agreement
#print axioms set_val_eq
#print axioms set_val_ne
#print axioms lift_positive
#print axioms lift_coherent
#print axioms fresh_not_mem
#print axioms update_agree
#print axioms step_agree
#print axioms seen_subset_next
#print axioms agree_trans
#print axioms extend_preserves
#print axioms step_def_sound
#print axioms def_sem_transport
#print axioms extend_defs_sound
#print axioms records_guard_iff
#print axioms canonical_guard_iff
#print axioms rowIds
#print axioms recordsKnown
#print axioms records_known_sound
#print axioms replay_record_ids
#print axioms record_lift_coherent
#print axioms accepted_lift_coherent
#print axioms definition_agreement_step
#print axioms topological_defs_agreement
#print axioms guard_agreement
#print axioms accepted_canonical_iff
#print axioms accepted_model_canonical_agreement
#print axioms accepted_extension_exists_iff
#print axioms accepted_guard_rejects
#print axioms bitsAt
#print axioms packBits
#print axioms decodeBits
#print axioms liveMatch
#print axioms sumBits
#print axioms fiberTerm
#print axioms actualFiber
#print axioms pack_length
#print axioms pack_at
#print axioms bits_ext
#print axioms decode_pack_agree
#print axioms bits_eq_of_domain
#print axioms bool_match
#print axioms live_match_iff
#print axioms record_sem_agree
#print axioms accepted_sat_agree
#print axioms accepted_live_in_domain
#print axioms sum_bits_zero
#print axioms sum_bits_single
#print axioms accepted_weighted_fiber
#print axioms accepted_fiber_count
#print axioms chosenLiteral
#print axioms literalProduct
#print axioms selectedPhaseProduct
#print axioms literal_product_agree
#print axioms accepted_literal_fiber
#print axioms chosen_literal_false
#print axioms chosen_literal_true
#print axioms literal_product_phase
#print axioms accepted_phase_product_fiber
#print axioms uniqueIds
#print axioms natListEq
#print axioms sourceDimacs
#print axioms sourceIds
#print axioms phaseIds
#print axioms andWitness
#print axioms phaseRecordOK
#print axioms phaseRecordsOK
#print axioms replayExtras
#print axioms decodeLive
#print axioms totalWmc
#print axioms sourceVal
#print axioms replay_extras_checked
#print axioms nat_list_eq_iff
#print axioms replay_live_unique
#print axioms replay_phase_ids
#print axioms projection_agree
#print axioms projection_decode
#print axioms decode_projection
#print axioms live_projection_unique
#print axioms sum_bits_congr
#print axioms sum_bits_add
#print axioms sum_bits_swap
#print axioms live_partition_term
#print axioms total_wmc_partition
#print axioms accepted_total_wmc
#print axioms accepted_total_phase_product
#print axioms and_witness_sound
#print axioms phase_records_sound
#print axioms replay_phase_binding
#print axioms source_dimacs_live
#print axioms mapped_source_values
#print axioms accepted_phase_monomial
#print axioms signedToken
#print axioms decimalMantissa
#print axioms decimalExponent
#print axioms decimalParts
#print axioms decimalValue
#print axioms lookupWeight
#print axioms serializedProduct
#print axioms selectedPhaseSum
#print axioms accepted_serialized_weight_total
#print axioms selected_phase_exp
#print axioms accepted_total_phase_sum
#print axioms parsePhaseEntry
#print axioms parsePhase
#print axioms phaseSource
#print axioms phaseEntryOK
#print axioms phaseEntriesKnown
#print axioms phaseSidecarOK
#print axioms checkPhaseSidecar
#print axioms phaseLookup
#print axioms sidecarCoeff
#print axioms sourcePhaseBit
#print axioms phase_source_sound
#print axioms phase_entry_sound
#print axioms phase_entries_sound
#print axioms phase_lookup_sound
#print axioms phase_lookup_exists
#print axioms sidecar_weighted_lookup
#print axioms accepted_source_phase_bit
#print axioms selected_phase_sum_agree
#print axioms accepted_source_phase_sum
#print axioms parseGuardMono
#print axioms parseGuardRow
#print axioms parseGuard
#print axioms zeroWitness
#print axioms xorInputs
#print axioms monoIdOK
#print axioms guardMonoOK
#print axioms guardPolyOK
#print axioms guardRowOK
#print axioms guardRowsOK
#print axioms checkGuardSidecar
#print axioms anfValue
#print axioms residualGuard
#print axioms zero_witness_sound
#print axioms xor_inputs_sound
#print axioms mono_id_sound
#print axioms guard_mono_sound
#print axioms guard_poly_sound
#print axioms guard_row_sound
#print axioms guard_rows_sound
#print axioms accepted_residual_guard
#print axioms accepted_constrained_phase_sum
#print axioms parseLedgerPhase
#print axioms parseLedgerPoly
#print axioms parseLedgerSnap
#print axioms snapCost
#print axioms removedIds
#print axioms freeSnapOK
#print axioms ledgerTallyList
#print axioms ledgerFuel
#print axioms ledgerMultiplier
#print axioms parseLedgerStep
#print axioms ledgerWitnessOK
#print axioms ledgerAdvance
#print axioms ledgerNext
#print axioms replayLedger
#print axioms checkLedger
#print axioms free_snapshot_payload
#print axioms rejected_ledger_next
#print axioms committed_ledger_next
#print axioms ledger_scale_compose
#print axioms ledgerStepExponent
#print axioms ledger_bool_false
#print axioms ledger_bool_true
#print axioms ledger_batch_arithmetic
#print axioms ledger_free_arithmetic
#print axioms ledger_hh_arithmetic
#print axioms ledger_kind_eq
#print axioms ledger_exponent_5
#print axioms ledger_exponent_4
#print axioms ledger_exponent_3
#print axioms ledger_exponent_2
#print axioms ledger_exponent_1
#print axioms ledger_exponent_0
#print axioms ledger_exponent_rejected
#print axioms ledger_advance_multiplier
#print axioms replay_ledger_cons
#print axioms replay_ledger_multiplier
#print axioms replay_ledger_scale
#print axioms replay_ledger_scale_from_zero
#print axioms canonicalLedgerSnap
#print axioms ledger_bind_some
#print axioms ledger_if_some_branch
#print axioms parse_ledger_snap_raw
#print axioms parsed_ledger_snap_canonical
#print axioms canonical_ledger_snap_eq
#print axioms parse_ledger_step_canonical
#print axioms ledger_next_canonical
#print axioms replay_ledger_canonical
#print axioms replay_ledger_canonical_scale
#print axioms replay_ledger_canonical_scale_from_zero
#print axioms parse_ledger_steps_canonical
#print axioms LedgerByteWitness
#print axioms ledger_accepted_endpoint
#print axioms check_ledger_byte_witness
#print axioms check_ledger_witness_scale
#print axioms ledger_removed_ids_iff
#print axioms ledger_no_any_member
#print axioms free_snapshot_support_exclusion
#print axioms ledger_advance_free_obligations
#print axioms ledger_advance_free_support
#print axioms freeDouble
#print axioms sum_bits_free_prefix
#print axioms LedgerSnapFields
#print axioms ledger_snap_fields_of_admission
#print axioms parse_ledger_snap_fields
#print axioms canonical_ledger_snap_fields
#print axioms canonical_ledger_live_admission
#print axioms free_snapshot_typed_payload
#print axioms canonical_ledger_support_known
#print axioms free_snapshot_retained_support
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
  -- Exercise exactly the DIMACS termination/admission path, including
  -- a legal empty clause (unsatisfiable), not an empty input row.
  if QuPRS.CnfReplay.parseClause 2 [[50], [45,49], [48]] != some [-1,2] ||
      QuPRS.CnfReplay.parseClause 2 [[48]] != some [] ||
      QuPRS.CnfReplay.parseClause 2 [] != none ||
      QuPRS.CnfReplay.parseClause 2 [[49]] != none ||
      QuPRS.CnfReplay.parseClause 2 [[48], [49], [48]] != none ||
      QuPRS.CnfReplay.parseClause 2 [[51], [48]] != none ||
      QuPRS.CnfReplay.parseClause 2 [[45,51], [48]] != none ||
      QuPRS.CnfReplay.parseClause 2 [[120], [48]] != none then
    throw (IO.userError "DIMACS clause grammar regression")
  IO.println "CRR_LEAN_CLAUSE_GRAMMAR_PASS controls=8"
  -- Small direct controls for the repaired source mapper and compact
  -- live projection. No large-model enumeration.
  let rs : List QuPRS.CnfReplay.Record :=
    [.live 10 2, .live 20 1, .andGate 3 [2,1], .andGate 4 [],
      .phase 3 [10,20], .phase 4 []]
  if QuPRS.CnfReplay.sourceIds rs [10,20] != some [2,1] ||
      QuPRS.CnfReplay.sourceIds rs [] != some [] ||
      QuPRS.CnfReplay.sourceIds rs [10,99] != none ||
      !(QuPRS.CnfReplay.phaseRecordOK rs (.phase 3 [10,20])) ||
      QuPRS.CnfReplay.phaseRecordOK rs (.phase 3 [20,10]) ||
      !(QuPRS.CnfReplay.phaseRecordOK rs (.phase 4 [])) ||
      ([2,1] : List Nat).map (QuPRS.CnfReplay.decodeLive [2,1] [true,false]) != [true,false] ||
      QuPRS.CnfReplay.uniqueIds [2,1,2] then
    throw (IO.userError "live projection or phase binding regression")
  IO.println "CRR_LEAN_PHASE_PROJECTION_PASS controls=8"
  -- Exact numerator/denominator controls, including malformed
  -- positive weights formerly admitted as opaque tokens.
  if QuPRS.CnfReplay.decimalValue [45,49,46,50,53,101,45,50] != some (-125,10000) ||
      QuPRS.CnfReplay.decimalValue [43,50,69,43,51] != some (2000,1) ||
      QuPRS.CnfReplay.decimalValue [46,53] != some (5,10) ||
      QuPRS.CnfReplay.decimalValue [49,46] != some (1,1) ||
      QuPRS.CnfReplay.decimalValue [46] != none ||
      QuPRS.CnfReplay.decimalValue [49,101,52,48,57,55] != none ||
      QuPRS.CnfReplay.decimalValue [49,46,50,46,51] != none ||
      QuPRS.CnfReplay.decimalValue [110,97,110] != none then
    throw (IO.userError "exact decimal grammar regression")
  IO.println "CRR_LEAN_EXACT_DECIMAL_PASS controls=8"
  -- End-to-end byte admission, actual exact values and implicit units.
  -- A valid changed positive weight must remain distinguishable, not
  -- be silently interpreted as the original ideal phase.
  let sampleGate : List Nat := [99,114,114,45,103,97,116,101,45,118,49,32,50,10,108,105,118,101,32,48,32,49,10,97,110,100,32,50,32,49,10,112,104,97,115,101,32,50,32,48,10]
  let sampleCnf : List Nat := [112,32,99,110,102,32,50,32,50,10,99,32,116,32,119,109,99,10,99,32,112,32,119,101,105,103,104,116,32,50,32,49,46,50,53,101,45,50,32,45,48,46,53,32,48,10,99,32,112,32,119,101,105,103,104,116,32,45,50,32,49,46,48,32,48,46,48,32,48,10,45,50,32,49,32,48,10,50,32,45,49,32,48,10]
  let malformedCnf : List Nat := [112,32,99,110,102,32,50,32,50,10,99,32,116,32,119,109,99,10,99,32,112,32,119,101,105,103,104,116,32,50,32,110,97,110,32,45,48,46,53,32,48,10,99,32,112,32,119,101,105,103,104,116,32,45,50,32,49,46,48,32,48,46,48,32,48,10,45,50,32,49,32,48,10,50,32,45,49,32,48,10]
  let changedCnf : List Nat := [112,32,99,110,102,32,50,32,50,10,99,32,116,32,119,109,99,10,99,32,112,32,119,101,105,103,104,116,32,50,32,50,46,53,101,45,50,32,45,48,46,53,32,48,10,99,32,112,32,119,101,105,103,104,116,32,45,50,32,49,46,48,32,48,46,48,32,48,10,45,50,32,49,32,48,10,50,32,45,49,32,48,10]
  let some parsed := QuPRS.CnfReplay.parseCnf sampleCnf
    | throw (IO.userError "exact weight fixture parse failed")
  let some changed := QuPRS.CnfReplay.parseCnf changedCnf
    | throw (IO.userError "changed weight fixture parse failed")
  if !(QuPRS.CnfReplay.check sampleGate sampleCnf) ||
      QuPRS.CnfReplay.check sampleGate malformedCnf ||
      QuPRS.CnfReplay.lookupWeight 2 parsed.weightValues != ((125,10000),(-5,10)) ||
      QuPRS.CnfReplay.lookupWeight (-2) parsed.weightValues != ((10,10),(0,10)) ||
      QuPRS.CnfReplay.lookupWeight 1 parsed.weightValues != ((1,1),(0,1)) ||
      !(QuPRS.CnfReplay.check sampleGate changedCnf) ||
      QuPRS.CnfReplay.lookupWeight 2 changed.weightValues != ((25,1000),(-5,10)) then
    throw (IO.userError "serialized weight admission regression")
  IO.println "CRR_LEAN_SERIALIZED_WEIGHT_PASS controls=7"
  let phaseSample : List Nat := [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,50,32,49,32,50,32,48,32,49,32,48,10]
  if !(QuPRS.CnfReplay.checkPhaseSidecar sampleGate phaseSample) ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10] ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,50,32,49,32,50,32,48,32,49,32,49,10] ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,50,32,49,32,48,32,48,32,49,32,48,10] ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,50,32,50,32,50,32,48,32,49,32,48,10] ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,49,32,49,32,50,32,48,32,49,32,48,10] ||
      QuPRS.CnfReplay.checkPhaseSidecar sampleGate [99,114,114,45,112,104,97,115,101,45,118,49,10,99,111,101,102,32,50,32,49,32,50,32,48,32,49,32,48,10,99,111,101,102,32,50,32,49,32,50,32,48,32,49,32,48,10] then
    throw (IO.userError "phase sidecar regression")
  IO.println "CRR_LEAN_PHASE_SIDECAR_PASS controls=7"
  let guardGate : List Nat := [99,114,114,45,103,97,116,101,45,118,49,32,52,10,108,105,118,101,32,48,32,49,10,108,105,118,101,32,49,32,50,10,97,110,100,32,51,32,49,32,50,10,120,111,114,32,52,32,51,32,50,10,101,113,32,49,32,52,10]
  let guardSample : List Nat := [99,114,114,45,103,117,97,114,100,45,118,49,10,114,111,119,32,48,32,49,32,48,44,49,10]
  if !(QuPRS.CnfReplay.checkGuardSidecar guardGate guardSample) ||
      QuPRS.CnfReplay.checkGuardSidecar guardGate [99,114,114,45,103,117,97,114,100,45,118,49,10] ||
      QuPRS.CnfReplay.checkGuardSidecar guardGate [99,114,114,45,103,117,97,114,100,45,118,49,10,114,111,119,32,49,32,49,32,48,44,49,10] ||
      QuPRS.CnfReplay.checkGuardSidecar guardGate [99,114,114,45,103,117,97,114,100,45,118,49,10,114,111,119,32,48,32,49,32,48,44,57,10] ||
      QuPRS.CnfReplay.checkGuardSidecar guardGate [99,114,114,45,103,117,97,114,100,45,118,49,10,114,111,119,32,48,32,48,44,49,32,49,10] ||
      QuPRS.CnfReplay.checkGuardSidecar guardGate [99,114,114,45,103,117,97,114,100,45,118,49,10,114,111,119,32,48,32,49,32,48,44,49,10,114,111,119,32,48,32,49,32,48,44,49,10] ||
      QuPRS.CnfReplay.parseGuardMono [45] != some [] ||
      QuPRS.CnfReplay.parseGuardMono [49,44,50] != some [1,2] then
    throw (IO.userError "residual guard sidecar regression")
  IO.println "CRR_LEAN_GUARD_SIDECAR_PASS controls=8"
  -- Explicit expected outcomes and names make a failed mutation localizable.
  -- The former wrong-tally fixture duplicated the accepted bytes verbatim.
  let ledgerControls : List (String × Bool × List Nat) := [
    ("valid_batch_free", true, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10]),
    ("wrong_multiplier", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,49,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10]),
    ("wrong_start_chain", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,50,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10]),
    ("wrong_final_snapshot", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,44,49,59,126,59,126,10]),
    ("rejected_improving_batch", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,48,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10]),
    ("wrong_tally", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,51,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,48,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10]),
    ("wrong_normalization", false, [99,114,114,45,108,101,100,103,101,114,45,118,50,32,50,32,50,32,48,32,49,32,48,32,48,32,48,32,48,32,49,10,115,116,97,114,116,32,49,59,48,44,49,59,126,59,126,10,115,116,101,112,32,49,32,49,32,45,32,49,59,48,44,49,59,126,59,126,32,49,59,48,59,126,59,126,10,101,110,100,32,49,59,48,59,126,59,126,10])]
  for (label, want, bytes) in ledgerControls do
    let got := QuPRS.CnfReplay.checkLedger bytes
    if got != want then
      throw (IO.userError s!"portable reduction ledger regression {label}: expected={want} actual={got}")
    IO.println s!"CRR_LEAN_LEDGER_CONTROL name={label} matched=true"
  IO.println "CRR_LEAN_LEDGER_CONTROLS_PASS controls=7"
  let mode :: paths := args | throw (IO.userError "usage: CnfReplay accept|reject files")
  if mode == "ledger" then
    if paths.isEmpty then throw (IO.userError "empty ledger cohort")
    for path in paths do
      let raw ← IO.FS.readBinFile path
      if !(QuPRS.CnfReplay.checkLedger (raw.data.toList.map UInt8.toNat)) then
        throw (IO.userError s!"portable ledger rejected {path}")
      IO.println s!"CRR_LEAN_PORTABLE_LEDGER path={path} structural=true"
    IO.println s!"CRR_LEAN_LEDGER_SUMMARY count={paths.length} structural=true semantic_steps=false"
    return
  if (mode != "accept" && mode != "reject") || paths.isEmpty then
    throw (IO.userError "bad replay mode or empty cohort")
  let want := mode == "accept"
  for path in paths do
    let gate ← IO.FS.readBinFile path
    let cnf ← IO.FS.readBinFile (path ++ ".cnf")
    let got := QuPRS.CnfReplay.check
      (gate.data.toList.map UInt8.toNat) (cnf.data.toList.map UInt8.toNat)
    if got != want then throw (IO.userError s!"unexpected replay result {path}: {got}")
    if want then
      let side ← IO.FS.readBinFile (path ++ ".phase")
      if !(QuPRS.CnfReplay.checkPhaseSidecar (gate.data.toList.map UInt8.toNat)
          (side.data.toList.map UInt8.toNat)) then
        throw (IO.userError s!"phase sidecar rejected {path}")
      IO.println s!"CRR_LEAN_PORTABLE_PHASE path={path} matched=true"
      let guard ← IO.FS.readBinFile (path ++ ".guard")
      if !(QuPRS.CnfReplay.checkGuardSidecar (gate.data.toList.map UInt8.toNat)
          (guard.data.toList.map UInt8.toNat)) then
        throw (IO.userError s!"guard sidecar rejected {path}")
      IO.println s!"CRR_LEAN_PORTABLE_GUARD path={path} matched=true"
    IO.println s!"CRR_LEAN_PORTABLE_GATE mode={mode} path={path} matched=true"
  IO.println s!"CRR_LEAN_PORTABLE_SUMMARY mode={mode} count={paths.length}"
