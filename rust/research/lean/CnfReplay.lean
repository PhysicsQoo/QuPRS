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
        if inClauses || !literalValid n v || ws.any (intEq v) ||
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

def domainCheck (n : Nat) (rs : List Record) : Bool :=
  let ids := finalSeen (liveIds rs) rs
  inputsKnown ids (dimacsIds n) && inputsKnown (dimacsIds n) ids

def replayRows (n : Nat) (records : List Record) : Option (List (List Int) × List Nat) :=
  if topo (liveIds records) records && domainCheck n records then
    (replayWeights n records).map (fun ws => (recordsRows records, ws))
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
      have he : some (recordsRows rs, w) = some (cs, ws) := by
        simpa [ht, hw] using h
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
  have h' : (inputsKnown (finalSeen (liveIds rs) rs) (dimacsIds n) &&
      inputsKnown (dimacsIds n) (finalSeen (liveIds rs) rs)) = true := h
  have hs := and_true_parts h'
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
      cases ha : v a <;> cases hb : v b <;> simp [ha, hb]

-- The canonical extension satisfies the full record sequence iff its
-- diagonal guard passes. This is not yet a WMC sum theorem.
theorem canonical_guard_iff (v : Nat → Bool) (seen : List Nat) (rs : List Record)
    (ht : topo seen rs = true) :
    recordsSem (liftVal (extendVal v rs)) rs ↔ guardTruth (extendVal v rs) rs = true :=
  let h := records_guard_iff (extendVal v rs) rs
  Iff.intro (fun hs => (h.mp hs).2)
    (fun hg => h.mpr ⟨extend_defs_sound v seen rs ht, hg⟩)

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
