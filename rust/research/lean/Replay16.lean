/-
P8C1 bounded streaming replay composition.
The source parser, SHA-256 and quantum gate transition are explicit
external obligations. The theorem is parametric in a deterministic
transition on an already parsed, trusted gate sequence. It proves
that the codec and equality checks cannot skip a gate or ignore bytes.
It does NOT establish the correctness of the supplied transition.
-/
import TermFrame16

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

structure ReplayState16 where
  paths : Nat
  outputs : OutputWords16
  phase : PhaseWords16
  deriving Repr, DecidableEq

inductive StepOutcome16 where
  | advanced (state : ReplayState16)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

inductive ReplayResult16 where
  | accepted (state : ReplayState16) (total : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

/-- Decode exactly one frame per gate; compare the entire decoded
    state (path count, all ANFs and phase) with the transition result.
    An empty gate suffix accepts only an empty byte suffix. -/
def replayFrames16 {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16) :
    List G → ReplayState16 → Nat → WireBytes → ReplayResult16
  | [], state, total, bs =>
      if bs = [] then .accepted state total else .invalidProof
  | g :: gs, state, total, bs =>
      match decodeStateFrame16 n total bs with
      | .invalidProof => .invalidProof
      | .unknownResource => .unknownResource
      | .accepted paths xs ps tail t =>
          match step g state with
          | .invalidProof => .invalidProof
          | .unknownResource => .unknownResource
          | .advanced next =>
              if next = ⟨paths,xs,ps⟩ then
                replayFrames16 n step gs next t tail
              else .invalidProof

/-- Independent relational contract. Every constructor corresponds
    to one source gate AND one successful byte decoding. The base
    constructor requires the exact end of input. -/
inductive ReplayTrace16 {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16) :
    List G → ReplayState16 → Nat → WireBytes →
      ReplayState16 → Nat → Prop where
  | done (state : ReplayState16) (total : Nat) :
      ReplayTrace16 n step [] state total [] state total
  | next (g : G) (gs : List G) (state : ReplayState16)
      (total : Nat) (bs : WireBytes)
      (paths : Nat) (xs : OutputWords16) (ps : PhaseWords16)
      (tail : WireBytes) (t : Nat)
      (finalState : ReplayState16) (endTotal : Nat)
      (hd : decodeStateFrame16 n total bs = .accepted paths xs ps tail t)
      (hs : step g state = .advanced ⟨paths,xs,ps⟩)
      (hr : ReplayTrace16 n step gs ⟨paths,xs,ps⟩ t tail
        finalState endTotal) :
      ReplayTrace16 n step (g :: gs) state total bs finalState endTotal

theorem replayFrames16_sound {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (bs : WireBytes) (finalState : ReplayState16) (endTotal : Nat)
    (h : replayFrames16 n step gs state total bs =
      .accepted finalState endTotal) :
    ReplayTrace16 n step gs state total bs finalState endTotal := by
  induction gs generalizing state total bs finalState endTotal with
  | nil =>
      by_cases he : bs = []
      · subst bs
        simp [replayFrames16] at h
        obtain ⟨rfl,rfl⟩ := h
        exact .done _ _
      · simp [replayFrames16,he] at h
  | cons g gs ih =>
      cases hd : decodeStateFrame16 n total bs with
      | invalidProof => simp [replayFrames16,hd] at h
      | unknownResource => simp [replayFrames16,hd] at h
      | accepted paths xs ps tail t =>
          cases hs : step g state with
          | invalidProof => simp [replayFrames16,hd,hs] at h
          | unknownResource => simp [replayFrames16,hd,hs] at h
          | advanced next =>
              by_cases he : next = ⟨paths,xs,ps⟩
              · subst next
                simp [replayFrames16,hd,hs] at h
                exact .next g gs state total bs paths xs ps tail t
                  finalState endTotal hd hs
                  (ih _ t tail finalState endTotal h)
              · simp [replayFrames16,hd,hs,he] at h

/-- The relational contract is also sufficient for acceptance. -/
theorem replayFrames16_complete {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (bs : WireBytes) (finalState : ReplayState16) (endTotal : Nat)
    (h : ReplayTrace16 n step gs state total bs finalState endTotal) :
    replayFrames16 n step gs state total bs =
      .accepted finalState endTotal := by
  induction h with
  | done state total => simp [replayFrames16]
  | next g gs state total bs paths xs ps tail t finalState endTotal hd hs hr ih =>
      simp [replayFrames16,hd,hs,ih]

/-- Source transition semantics independent of proof bytes. -/
def runTransitions16 {G : Type}
    (step : G → ReplayState16 → StepOutcome16) :
    List G → ReplayState16 → Option ReplayState16
  | [], state => some state
  | g :: gs, state =>
      match step g state with
      | .advanced next => runTransitions16 step gs next
      | .invalidProof => none
      | .unknownResource => none

/-- A successful trace must reach the same state as direct execution
    of the supplied deterministic transitions, with no proof input. -/
theorem replayTrace16_endpoint {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (bs : WireBytes) (finalState : ReplayState16) (endTotal : Nat)
    (h : ReplayTrace16 n step gs state total bs finalState endTotal) :
    runTransitions16 step gs state = some finalState := by
  induction h with
  | done state total => rfl
  | next g gs state total bs paths xs ps tail t finalState endTotal hd hs hr ih =>
      simp [runTransitions16,hs,ih]

/-- The accepted terminal state is uniquely determined by the source
    transition sequence and starting state, independent of proof bytes. -/
theorem replayFrames16_endpoint_unique {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (a b : WireBytes) (sa sb : ReplayState16) (ta tb : Nat)
    (ha : replayFrames16 n step gs state total a = .accepted sa ta)
    (hb : replayFrames16 n step gs state total b = .accepted sb tb) :
    sa = sb := by
  have h1 := replayTrace16_endpoint n step gs state total a sa ta
    (replayFrames16_sound n step gs state total a sa ta ha)
  have h2 := replayTrace16_endpoint n step gs state total b sb tb
    (replayFrames16_sound n step gs state total b sb tb hb)
  rw [h1] at h2
  exact Option.some.inj h2

/-- All accepted frames contribute to one monotonically increasing
    aggregate counter. The bound is global, not reset per gate. -/
theorem replayTrace16_budget {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (bs : WireBytes) (finalState : ReplayState16) (endTotal : Nat)
    (h : ReplayTrace16 n step gs state total bs finalState endTotal)
    (hb : total ≤ 32768) : total ≤ endTotal ∧ endTotal ≤ 32768 := by
  induction h with
  | done state total => exact ⟨Nat.le_refl _,hb⟩
  | next g gs state total bs paths xs ps tail t finalState endTotal hd hs hr ih =>
      obtain ⟨_,_,_,_,_,ht,htmax,_,_⟩ :=
        decodeStateFrame16_sound n total bs paths xs ps tail t hd
      have htail := ih htmax
      exact ⟨by omega,htail.2⟩

/-- Each frame consumes at least its fixed header/output-count
    overhead. Therefore accepted traces contain one frame per gate
    and cannot consume zero bytes on a nonempty gate suffix. -/
theorem replayTrace16_minimum_bytes {G : Type} (n : Nat)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (state : ReplayState16) (total : Nat)
    (bs : WireBytes) (finalState : ReplayState16) (endTotal : Nat)
    (h : ReplayTrace16 n step gs state total bs finalState endTotal) :
    (3 + 2 * n) * gs.length ≤ bs.length := by
  induction h with
  | done state total => simp
  | next g gs state total bs paths xs ps tail t finalState endTotal hd hs hr ih =>
      obtain ⟨_,_,_,_,_,_,_,_,hlen⟩ :=
        decodeStateFrame16_sound n total bs paths xs ps tail t hd
      simp only [List.length_cons,Nat.mul_succ]
      omega

def initialReplay16 (n : Nat) : ReplayState16 :=
  ⟨0,(List.range n).map (fun i => [2 ^ i]),[]⟩

/-- The supplied 32 bytes are the expected source digest. The model
    checks exact bytes but does not verify SHA-256 or source parsing. -/
def replayHeader16 (n count : Nat) (digest : WireBytes) : WireBytes :=
  [80,56,67,49] ++ encodeLE 1 n ++ encodeLE 2 count ++ digest

def checkReplay16 {G : Type} (n : Nat) (digest : WireBytes)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (proof : WireBytes) : ReplayResult16 :=
  if proof.length > 1048576 then .unknownResource
  else if 0 < n ∧ n ≤ 16 ∧ gs.length ≤ 1024 ∧ digest.length = 32 then
    let headerBytes := replayHeader16 n gs.length digest
    if proof.take headerBytes.length = headerBytes then
      replayFrames16 n step gs (initialReplay16 n) 0
        (proof.drop headerBytes.length)
    else .invalidProof
  else .invalidProof

/-- Complete wire-envelope acceptance binds the caller-supplied
    digest, n, gate count and exact replay payload, conditional on the
    source adapter and the supplied transition semantics. -/
theorem checkReplay16_sound {G : Type} (n : Nat) (digest : WireBytes)
    (step : G → ReplayState16 → StepOutcome16)
    (gs : List G) (proof : WireBytes)
    (finalState : ReplayState16) (endTotal : Nat)
    (h : checkReplay16 n digest step gs proof =
      .accepted finalState endTotal) :
    proof.length ≤ 1048576 ∧
      (0 < n ∧ n ≤ 16 ∧ gs.length ≤ 1024 ∧ digest.length = 32) ∧
      (∃ payload : WireBytes,
        proof = replayHeader16 n gs.length digest ++ payload ∧
        ReplayTrace16 n step gs (initialReplay16 n) 0 payload
          finalState endTotal) ∧
      runTransitions16 step gs (initialReplay16 n) = some finalState ∧
      endTotal ≤ 32768 := by
  by_cases hsize : proof.length > 1048576
  · simp [checkReplay16,hsize] at h
  · by_cases hg : 0 < n ∧ n ≤ 16 ∧ gs.length ≤ 1024 ∧ digest.length = 32
    · let headerBytes := replayHeader16 n gs.length digest
      by_cases hh : proof.take headerBytes.length = headerBytes
      · have hr : replayFrames16 n step gs (initialReplay16 n) 0
            (proof.drop headerBytes.length) = .accepted finalState endTotal := by
          simpa [checkReplay16,hsize,hg,headerBytes,hh] using h
        have trace := replayFrames16_sound n step gs (initialReplay16 n) 0
          (proof.drop headerBytes.length) finalState endTotal hr
        have hsplit := List.take_append_drop headerBytes.length proof
        rw [hh] at hsplit
        refine ⟨by omega,hg,⟨proof.drop headerBytes.length,hsplit.symm,trace⟩,
          replayTrace16_endpoint n step gs (initialReplay16 n) 0 _
            finalState endTotal trace,?_⟩
        exact (replayTrace16_budget n step gs (initialReplay16 n) 0 _
          finalState endTotal trace (by decide)).2
      · simp [checkReplay16,hsize,hg,headerBytes,hh] at h
    · simp [checkReplay16,hsize,hg] at h

#print axioms replayFrames16_sound
#print axioms replayFrames16_complete
#print axioms replayTrace16_endpoint
#print axioms replayFrames16_endpoint_unique
#print axioms replayTrace16_budget
#print axioms replayTrace16_minimum_bytes
#print axioms checkReplay16_sound

/- Known-answer interface probes, using a deliberately tiny abstract
   transition function. These are not proofs of quantum gate semantics. -/
def replayProbeStep (flip : Bool) (_ : ReplayState16) : StepOutcome16 :=
  if flip then .advanced ⟨0,[[0,1]],[]⟩
  else .advanced ⟨0,[[1]],[]⟩

def replayProbeDigest : WireBytes := List.replicate 32 42

def replayProbeProof : WireBytes :=
  replayHeader16 1 1 replayProbeDigest ++ encodeStateFrame16 0 [[0,1]] []

#eval checkReplay16 1 replayProbeDigest replayProbeStep [true] replayProbeProof
#eval checkReplay16 1 replayProbeDigest replayProbeStep [false] replayProbeProof
#eval checkReplay16 1 replayProbeDigest replayProbeStep [true] (replayProbeProof ++ [0])
#eval checkReplay16 1 (List.replicate 32 43) replayProbeStep [true] replayProbeProof
#eval checkReplay16 1 replayProbeDigest replayProbeStep [true]
  (replayHeader16 1 1 replayProbeDigest)

end QuPRS.P0
