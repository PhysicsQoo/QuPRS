/-
Research decoder for the P8C1 ANF termset wire format, restricted to
the 16-variable symbolic checker profile. Count is LE u16, masks
are LE u64, and the admitted natural-number masks must fit width <=16.
This is a standalone executable specification; it is not a proof of
Rust Cursor, integer arithmetic, or the full source-bound certificate.
-/
import BitMask16

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.P0

abbrev WireBytes := List UInt8

def leValue : WireBytes → Nat
  | [] => 0
  | b :: bs => b.toNat + 256 * leValue bs

def readLE : Nat → WireBytes → Option (Nat × WireBytes)
  | 0, bs => some (0, bs)
  | _ + 1, [] => none
  | n + 1, b :: bs =>
    match readLE n bs with
    | none => none
    | some (v, rest) => some (b.toNat + 256 * v, rest)

/-- Successful reads consume exactly n bytes and preserve their
    little-endian natural-number meaning. -/
theorem readLE_sound (n : Nat) (bs : WireBytes)
    (v : Nat) (rest : WireBytes)
    (h : readLE n bs = some (v, rest)) :
    ∃ payload : WireBytes,
      payload.length = n ∧ bs = payload ++ rest ∧
      v = leValue payload := by
  induction n generalizing bs v rest with
  | zero =>
      simp [readLE] at h
      obtain ⟨rfl, rfl⟩ := h
      exact ⟨[], rfl, rfl, rfl⟩
  | succ n ih =>
      cases bs with
      | nil => simp [readLE] at h
      | cons b bs =>
          cases ht : readLE n bs with
          | none => simp [readLE, ht] at h
          | some p =>
              obtain ⟨w, tail⟩ := p
              simp [readLE, ht] at h
              obtain ⟨rfl, rfl⟩ := h
              obtain ⟨payload, hl, hb, hv⟩ := ih bs w tail ht
              refine ⟨b :: payload, ?_, ?_, ?_⟩
              · simp [hl]
              · simp [hb]
              · simp [leValue, hv]

theorem readLE_consumes (n : Nat) (bs : WireBytes)
    (v : Nat) (rest : WireBytes)
    (h : readLE n bs = some (v, rest)) :
    bs.length = n + rest.length := by
  obtain ⟨payload, hl, hb, _⟩ := readLE_sound n bs v rest h
  simp [hb, hl]

theorem readLE_truncated (n : Nat) (bs : WireBytes)
    (h : bs.length < n) : readLE n bs = none := by
  cases hr : readLE n bs with
  | none => rfl
  | some p =>
      obtain ⟨v, rest⟩ := p
      have hc := readLE_consumes n bs v rest hr
      omega

def afterPrevious (previous : Option Nat) (m : Nat) : Prop :=
  match previous with
  | none => True
  | some p => p < m

instance (previous : Option Nat) (m : Nat) :
    Decidable (afterPrevious previous m) := by
  cases previous <;> unfold afterPrevious <;> infer_instance

def OrderedMaskWords (width : Nat) (previous : Option Nat) :
    List Nat → Prop
  | [] => True
  | m :: rest =>
      m < 2 ^ width ∧ afterPrevious previous m ∧
        OrderedMaskWords width (some m) rest

def readOrderedMasks (width : Nat) :
    Nat → Option Nat → WireBytes → Option (List Nat × WireBytes)
  | 0, _, bs => some ([], bs)
  | n + 1, previous, bs =>
      match readLE 8 bs with
      | none => none
      | some (m, tail) =>
          if m < 2 ^ width ∧ afterPrevious previous m then
            match readOrderedMasks width n (some m) tail with
            | none => none
            | some (ms, rest) => some (m :: ms, rest)
          else none

/-- All accepted masks are within the declared width and strictly
    increase from the preceding word. The parser consumes eight bytes
    per accepted monomial, with no implicit deduplication. -/
theorem readOrderedMasks_sound (width count : Nat)
    (previous : Option Nat) (bs : WireBytes)
    (ms : List Nat) (rest : WireBytes)
    (h : readOrderedMasks width count previous bs = some (ms, rest)) :
    ms.length = count ∧ OrderedMaskWords width previous ms ∧
      bs.length = 8 * count + rest.length := by
  induction count generalizing previous bs ms rest with
  | zero =>
      simp [readOrderedMasks] at h
      obtain ⟨rfl, rfl⟩ := h
      simp [OrderedMaskWords]
  | succ n ih =>
      cases hw : readLE 8 bs with
      | none => simp [readOrderedMasks, hw] at h
      | some p =>
          obtain ⟨m, tail⟩ := p
          by_cases hg : m < 2 ^ width ∧ afterPrevious previous m
          · cases ht : readOrderedMasks width n (some m) tail with
            | none => simp [readOrderedMasks, hw, hg, ht] at h
            | some q =>
                obtain ⟨xs, endBytes⟩ := q
                simp [readOrderedMasks, hw, hg, ht] at h
                obtain ⟨rfl, rfl⟩ := h
                obtain ⟨hl, ho, hc⟩ := ih (some m) tail xs endBytes ht
                have hb := readLE_consumes 8 bs m tail hw
                refine ⟨by simp [hl], ⟨hg.1, hg.2, ho⟩, ?_⟩
                omega
          · simp [readOrderedMasks, hw, hg] at h

theorem orderedMaskWords_bounded (width : Nat)
    (previous : Option Nat) (ms : List Nat)
    (h : OrderedMaskWords width previous ms) :
    ∀ m ∈ ms, m < 2 ^ width := by
  induction ms generalizing previous with
  | nil => simp
  | cons a xs ih =>
      intro m hm
      rcases List.mem_cons.mp hm with he | ht
      · subst m
        exact h.1
      · exact ih (some a) h.2.2 m ht

theorem orderedMaskWords_after (width lower : Nat) (ms : List Nat)
    (h : OrderedMaskWords width (some lower) ms) :
    ∀ m ∈ ms, lower < m := by
  induction ms generalizing lower with
  | nil => simp
  | cons a xs ih =>
      intro m hm
      rcases List.mem_cons.mp hm with he | ht
      · subst m
        exact h.2.1
      · exact Nat.lt_trans h.2.1 (ih a h.2.2 m ht)

theorem orderedMaskWords_strict (width : Nat)
    (previous : Option Nat) (ms : List Nat)
    (h : OrderedMaskWords width previous ms) :
    ms.Pairwise (fun a b => a < b) := by
  induction ms generalizing previous with
  | nil => simp
  | cons a xs ih =>
      apply List.pairwise_cons.mpr
      exact ⟨orderedMaskWords_after width a xs h.2.2,
        ih (some a) h.2.2⟩

inductive TermFrame16Result where
  | accepted (masks : List Nat) (rest : WireBytes) (total frameUsed : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

/-- The order of the checks matches the bounded frame contract:
    read count, charge both limits, then parse masks. Width >16 is
    outside this symbolic specification (not general P8C1). -/
def decodeTermFrame16 (width total frameUsed : Nat) (bs : WireBytes) :
    TermFrame16Result :=
  if width ≤ 16 then
    match readLE 2 bs with
    | none => .invalidProof
    | some (count, tail) =>
        if 32768 < total + count ∨ 256 < frameUsed + count then
          .unknownResource
        else
          match readOrderedMasks width count none tail with
          | none => .invalidProof
          | some (ms, rest) => .accepted ms rest (total + count) (frameUsed + count)
  else .invalidProof

/-- Acceptance entails exact declared count/byte consumption,
    width, order and both budgets; no truncated list is accepted. -/
theorem decodeTermFrame16_sound
    (width total frameUsed : Nat) (bs : WireBytes)
    (ms : List Nat) (rest : WireBytes) (total' frameUsed' : Nat)
    (h : decodeTermFrame16 width total frameUsed bs =
      .accepted ms rest total' frameUsed') :
    width ≤ 16 ∧ total' = total + ms.length ∧
      frameUsed' = frameUsed + ms.length ∧ total' ≤ 32768 ∧
      frameUsed' ≤ 256 ∧ bs.length = 2 + 8 * ms.length + rest.length ∧
      (∀ m ∈ ms, m < 2 ^ width) ∧
      ms.Pairwise (fun a b => a < b) := by
  by_cases hw : width ≤ 16
  · cases hh : readLE 2 bs with
    | none => simp [decodeTermFrame16, hw, hh] at h
    | some p =>
        obtain ⟨count, tail⟩ := p
        by_cases hb : 32768 < total + count ∨ 256 < frameUsed + count
        · simp [decodeTermFrame16, hw, hh, hb] at h
        · cases ht : readOrderedMasks width count none tail with
          | none => simp [decodeTermFrame16, hw, hh, hb, ht] at h
          | some q =>
              obtain ⟨xs, endBytes⟩ := q
              simp [decodeTermFrame16, hw, hh, hb, ht] at h
              obtain ⟨rfl, rfl, rfl, rfl⟩ := h
              obtain ⟨hl, ho, hc⟩ :=
                readOrderedMasks_sound width count none tail xs endBytes ht
              have hhead := readLE_consumes 2 bs count tail hh
              refine ⟨hw, by rw [hl], by rw [hl], by omega, by omega,
                by omega, orderedMaskWords_bounded width none xs ho,
                orderedMaskWords_strict width none xs ho⟩
  · simp [decodeTermFrame16, hw] at h

/-- A budget failure is reported before inspecting the mask payload. -/
theorem decodeTermFrame16_resource
    (width total frameUsed count : Nat) (bs tail : WireBytes)
    (hw : width ≤ 16) (hh : readLE 2 bs = some (count, tail))
    (hb : 32768 < total + count ∨ 256 < frameUsed + count) :
    decodeTermFrame16 width total frameUsed bs = .unknownResource := by
  simp [decodeTermFrame16, hw, hh, hb]

/-- Trailing bytes belong to the caller's subsequent frame; this
    exact-frame wrapper rejects any trailing bytes. -/
def decodeExactTermFrame16 (width total frameUsed : Nat) (bs : WireBytes) :
    TermFrame16Result :=
  match decodeTermFrame16 width total frameUsed bs with
  | .accepted ms [] t l => .accepted ms [] t l
  | .accepted _ (_ :: _) _ _ => .invalidProof
  | .invalidProof => .invalidProof
  | .unknownResource => .unknownResource

theorem decodeExactTermFrame16_no_trailing
    (width total frameUsed : Nat) (bs : WireBytes)
    (ms : List Nat) (rest : WireBytes) (t l : Nat)
    (h : decodeExactTermFrame16 width total frameUsed bs =
      .accepted ms rest t l) : rest = [] := by
  cases hf : decodeTermFrame16 width total frameUsed bs with
  | invalidProof => simp [decodeExactTermFrame16, hf] at h
  | unknownResource => simp [decodeExactTermFrame16, hf] at h
  | accepted xs tail t' l' =>
      cases tail with
      | nil =>
          simp [decodeExactTermFrame16, hf] at h
          exact h.2.1
      | cons a as => simp [decodeExactTermFrame16, hf] at h

/-- Fixed-size little-endian encoder. The roundtrip theorem below
    explicitly requires the number to fit, avoiding silent truncation. -/
def encodeLE : Nat → Nat → WireBytes
  | 0, _ => []
  | n + 1, v => UInt8.ofNat v :: encodeLE n (v / 256)

theorem readLE_encodeLE (n v : Nat) (tail : WireBytes)
    (h : v < 256 ^ n) :
    readLE n (encodeLE n v ++ tail) = some (v, tail) := by
  induction n generalizing v with
  | zero =>
      have hz : v = 0 := by
        simp at h
        omega
      subst v
      rfl
  | succ n ih =>
      have hd : v / 256 < 256 ^ n := by
        rw [Nat.pow_succ] at h
        omega
      have hr := ih (v / 256) hd
      have hb : (UInt8.ofNat v).toNat = v % 256 := by simp
      simp only [encodeLE, List.cons_append, readLE, hr]
      rw [hb, Nat.mod_add_div]

def encodeMaskWords : List Nat → WireBytes
  | [] => []
  | m :: ms => encodeLE 8 m ++ encodeMaskWords ms

theorem readOrderedMasks_encode
    (width : Nat) (previous : Option Nat) (ms : List Nat)
    (tail : WireBytes) (h : OrderedMaskWords width previous ms)
    (hw : width ≤ 16) :
    readOrderedMasks width ms.length previous
      (encodeMaskWords ms ++ tail) = some (ms, tail) := by
  induction ms generalizing previous with
  | nil => rfl
  | cons m rest ih =>
      have hm : m < 256 ^ 8 := by
        have hp : 2 ^ width ≤ 2 ^ 16 :=
          Nat.pow_le_pow_right (by decide : 0 < 2) hw
        have hb := h.1
        have hconst : 2 ^ 16 ≤ 256 ^ 8 := by decide
        omega
      have hr := readLE_encodeLE 8 m (encodeMaskWords rest ++ tail) hm
      have ht := ih (some m) h.2.2
      have hg : m < 2 ^ width ∧ afterPrevious previous m := ⟨h.1,h.2.1⟩
      simp [encodeMaskWords, List.append_assoc, readOrderedMasks,
        hr, hg, ht]

def encodeTermFrame16 (ms : List Nat) : WireBytes :=
  encodeLE 2 ms.length ++ encodeMaskWords ms

/-- Every valid canonical termset roundtrips, retaining the suffix
    and both resource counters exactly. -/
theorem decodeTermFrame16_roundtrip
    (width total frameUsed : Nat) (ms : List Nat) (tail : WireBytes)
    (hw : width ≤ 16) (ho : OrderedMaskWords width none ms)
    (ht : total + ms.length ≤ 32768)
    (hl : frameUsed + ms.length ≤ 256) :
    decodeTermFrame16 width total frameUsed (encodeTermFrame16 ms ++ tail) =
      .accepted ms tail (total + ms.length) (frameUsed + ms.length) := by
  have hc : ms.length < 256 ^ 2 := by omega
  have hh := readLE_encodeLE 2 ms.length (encodeMaskWords ms ++ tail) hc
  have hm := readOrderedMasks_encode width none ms tail ho hw
  have hb : ¬ (32768 < total + ms.length ∨ 256 < frameUsed + ms.length) := by
    omega
  simp [decodeTermFrame16, encodeTermFrame16, List.append_assoc,
    hw, hh, hb, hm]

/-- A phase entry uses an eight-byte mask and a one-byte nonzero Z8
    coefficient. Numeric mask order, not coefficient order, matters. -/
abbrev PhaseWords16 := List (Nat × Nat)

def OrderedPhaseWords (width : Nat) (previous : Option Nat) :
    PhaseWords16 → Prop
  | [] => True
  | (m,c) :: rest =>
      (m < 2 ^ width ∧ afterPrevious previous m) ∧
      (0 < c ∧ c < 8) ∧ OrderedPhaseWords width (some m) rest

def readOrderedPhase (width : Nat) :
    Nat → Option Nat → WireBytes → Option (PhaseWords16 × WireBytes)
  | 0, _, bs => some ([], bs)
  | n + 1, previous, bs =>
      match readLE 8 bs with
      | none => none
      | some (m, tail) =>
          match readLE 1 tail with
          | none => none
          | some (c, payload) =>
              if (m < 2 ^ width ∧ afterPrevious previous m) ∧
                  (0 < c ∧ c < 8) then
                match readOrderedPhase width n (some m) payload with
                | none => none
                | some (ps, rest) => some ((m,c) :: ps, rest)
              else none

theorem readOrderedPhase_sound (width count : Nat)
    (previous : Option Nat) (bs : WireBytes)
    (ps : PhaseWords16) (rest : WireBytes)
    (h : readOrderedPhase width count previous bs = some (ps,rest)) :
    ps.length = count ∧ OrderedPhaseWords width previous ps ∧
      bs.length = 9 * count + rest.length := by
  induction count generalizing previous bs ps rest with
  | zero =>
      simp [readOrderedPhase] at h
      obtain ⟨rfl,rfl⟩ := h
      simp [OrderedPhaseWords]
  | succ n ih =>
      cases hm : readLE 8 bs with
      | none => simp [readOrderedPhase,hm] at h
      | some mp =>
          obtain ⟨m,tail⟩ := mp
          cases hc : readLE 1 tail with
          | none => simp [readOrderedPhase,hm,hc] at h
          | some cp =>
              obtain ⟨c,payload⟩ := cp
              by_cases hg : (m < 2 ^ width ∧ afterPrevious previous m) ∧
                  (0 < c ∧ c < 8)
              · cases hp : readOrderedPhase width n (some m) payload with
                | none => simp [readOrderedPhase,hm,hc,hg,hp] at h
                | some out =>
                    obtain ⟨xs,endBytes⟩ := out
                    simp [readOrderedPhase,hm,hc,hg,hp] at h
                    obtain ⟨rfl,rfl⟩ := h
                    obtain ⟨hl,ho,hr⟩ := ih (some m) payload xs endBytes hp
                    have h8 := readLE_consumes 8 bs m tail hm
                    have h1 := readLE_consumes 1 tail c payload hc
                    exact ⟨by simp [hl],⟨hg.1,hg.2,ho⟩,by omega⟩
              · simp [readOrderedPhase,hm,hc,hg] at h

theorem orderedPhaseWords_masks (width : Nat) (previous : Option Nat)
    (ps : PhaseWords16) (h : OrderedPhaseWords width previous ps) :
    OrderedMaskWords width previous (ps.map Prod.fst) := by
  induction ps generalizing previous with
  | nil => trivial
  | cons a rest ih =>
      obtain ⟨m,c⟩ := a
      exact ⟨h.1.1,h.1.2,ih (some m) h.2.2⟩

theorem orderedPhaseWords_coefficients (width : Nat) (previous : Option Nat)
    (ps : PhaseWords16) (h : OrderedPhaseWords width previous ps) :
    ∀ p ∈ ps, 0 < p.2 ∧ p.2 < 8 := by
  induction ps generalizing previous with
  | nil => simp
  | cons a rest ih =>
      obtain ⟨m,c⟩ := a
      intro p hp
      rcases List.mem_cons.mp hp with he | ht
      · subst p
        exact h.2.1
      · exact ih (some m) h.2.2 p ht

inductive PhaseFrame16Result where
  | accepted (phase : PhaseWords16) (rest : WireBytes) (total frameUsed : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

def decodePhaseFrame16 (width total frameUsed : Nat) (bs : WireBytes) :
    PhaseFrame16Result :=
  if width ≤ 16 then
    match readLE 2 bs with
    | none => .invalidProof
    | some (count, tail) =>
        if 32768 < total + count ∨ 256 < frameUsed + count then
          .unknownResource
        else
          match readOrderedPhase width count none tail with
          | none => .invalidProof
          | some (ps,rest) =>
              .accepted ps rest (total + count) (frameUsed + count)
  else .invalidProof

theorem decodePhaseFrame16_sound
    (width total frameUsed : Nat) (bs : WireBytes)
    (ps : PhaseWords16) (rest : WireBytes) (total' frameUsed' : Nat)
    (h : decodePhaseFrame16 width total frameUsed bs =
      .accepted ps rest total' frameUsed') :
    width ≤ 16 ∧ total' = total + ps.length ∧
      frameUsed' = frameUsed + ps.length ∧ total' ≤ 32768 ∧
      frameUsed' ≤ 256 ∧ bs.length = 2 + 9 * ps.length + rest.length ∧
      OrderedPhaseWords width none ps ∧
      (ps.map Prod.fst).Pairwise (fun a b => a < b) ∧
      (∀ p ∈ ps, 0 < p.2 ∧ p.2 < 8) := by
  by_cases hw : width ≤ 16
  · cases hh : readLE 2 bs with
    | none => simp [decodePhaseFrame16,hw,hh] at h
    | some p =>
        obtain ⟨count,tail⟩ := p
        by_cases hb : 32768 < total + count ∨ 256 < frameUsed + count
        · simp [decodePhaseFrame16,hw,hh,hb] at h
        · cases hp : readOrderedPhase width count none tail with
          | none => simp [decodePhaseFrame16,hw,hh,hb,hp] at h
          | some q =>
              obtain ⟨xs,endBytes⟩ := q
              simp [decodePhaseFrame16,hw,hh,hb,hp] at h
              obtain ⟨rfl,rfl,rfl,rfl⟩ := h
              obtain ⟨hl,ho,hc⟩ :=
                readOrderedPhase_sound width count none tail xs endBytes hp
              have hhead := readLE_consumes 2 bs count tail hh
              exact ⟨hw,by rw [hl],by rw [hl],by omega,by omega,
                by omega,ho,
                orderedMaskWords_strict width none _
                  (orderedPhaseWords_masks width none xs ho),
                orderedPhaseWords_coefficients width none xs ho⟩
  · simp [decodePhaseFrame16,hw] at h

theorem decodePhaseFrame16_resource
    (width total frameUsed count : Nat) (bs tail : WireBytes)
    (hw : width ≤ 16) (hh : readLE 2 bs = some (count,tail))
    (hb : 32768 < total + count ∨ 256 < frameUsed + count) :
    decodePhaseFrame16 width total frameUsed bs = .unknownResource := by
  simp [decodePhaseFrame16,hw,hh,hb]

def encodePhaseWords : PhaseWords16 → WireBytes
  | [] => []
  | (m,c) :: ps => encodeLE 8 m ++ encodeLE 1 c ++ encodePhaseWords ps

theorem readOrderedPhase_encode
    (width : Nat) (previous : Option Nat) (ps : PhaseWords16)
    (tail : WireBytes) (h : OrderedPhaseWords width previous ps)
    (hw : width ≤ 16) :
    readOrderedPhase width ps.length previous (encodePhaseWords ps ++ tail) =
      some (ps,tail) := by
  induction ps generalizing previous with
  | nil => rfl
  | cons a rest ih =>
      obtain ⟨m,c⟩ := a
      have hm : m < 256 ^ 8 := by
        have hp : 2 ^ width ≤ 2 ^ 16 :=
          Nat.pow_le_pow_right (by decide : 0 < 2) hw
        have hb := h.1.1
        have hconst : 2 ^ 16 ≤ 256 ^ 8 := by decide
        omega
      have hc : c < 256 ^ 1 := by
        have hb := h.2.1.2
        omega
      have hr := readLE_encodeLE 8 m
        (encodeLE 1 c ++ (encodePhaseWords rest ++ tail)) hm
      have hcoef := readLE_encodeLE 1 c (encodePhaseWords rest ++ tail) hc
      have hrest := ih (some m) h.2.2
      have hg : (m < 2 ^ width ∧ afterPrevious previous m) ∧
          (0 < c ∧ c < 8) := ⟨h.1,h.2.1⟩
      simp [encodePhaseWords,List.append_assoc,readOrderedPhase,
        hr,hcoef,hg,hrest]

def encodePhaseFrame16 (ps : PhaseWords16) : WireBytes :=
  encodeLE 2 ps.length ++ encodePhaseWords ps

theorem decodePhaseFrame16_roundtrip
    (width total frameUsed : Nat) (ps : PhaseWords16) (tail : WireBytes)
    (hw : width ≤ 16) (ho : OrderedPhaseWords width none ps)
    (ht : total + ps.length ≤ 32768)
    (hl : frameUsed + ps.length ≤ 256) :
    decodePhaseFrame16 width total frameUsed (encodePhaseFrame16 ps ++ tail) =
      .accepted ps tail (total + ps.length) (frameUsed + ps.length) := by
  have hc : ps.length < 256 ^ 2 := by omega
  have hh := readLE_encodeLE 2 ps.length (encodePhaseWords ps ++ tail) hc
  have hp := readOrderedPhase_encode width none ps tail ho hw
  have hb : ¬ (32768 < total + ps.length ∨ 256 < frameUsed + ps.length) := by
    omega
  simp [decodePhaseFrame16,encodePhaseFrame16,List.append_assoc,
    hw,hh,hb,hp]

#print axioms readLE_encodeLE
#print axioms readOrderedMasks_encode
#print axioms decodeTermFrame16_roundtrip
#print axioms readOrderedPhase_sound
#print axioms orderedPhaseWords_masks
#print axioms orderedPhaseWords_coefficients
#print axioms decodePhaseFrame16_sound
#print axioms decodePhaseFrame16_resource
#print axioms readOrderedPhase_encode
#print axioms decodePhaseFrame16_roundtrip

#eval decodeTermFrame16 16 0 0 (encodeTermFrame16 [0,1,32768] ++ [42])
#eval decodePhaseFrame16 16 3 3 (encodePhaseFrame16 [(0,1),(32768,7)] ++ [42])
#eval decodePhaseFrame16 16 0 0 (encodePhaseFrame16 [(0,0)])
#eval decodePhaseFrame16 16 0 0 (encodePhaseFrame16 [(0,8)])

#print axioms readLE_sound
#print axioms readLE_consumes
#print axioms readLE_truncated
#print axioms readOrderedMasks_sound
#print axioms orderedMaskWords_bounded
#print axioms orderedMaskWords_after
#print axioms orderedMaskWords_strict
#print axioms decodeTermFrame16_sound
#print axioms decodeTermFrame16_resource
#print axioms decodeExactTermFrame16_no_trailing

-- Executable probes: one monomial 0x8000, width 16 vs 15, and
-- excessive count without a payload.
#eval decodeExactTermFrame16 16 0 0 [1,0,0,128,0,0,0,0,0,0]
#eval decodeExactTermFrame16 15 0 0 [1,0,0,128,0,0,0,0,0,0]
#eval decodeExactTermFrame16 16 0 0 [1,1]


/- Compositional P8C1 per-gate state wire frame: one path count byte,
   exactly n output ANFs, then one Z8 phase frame. The source replay
   transition and digest binding are deliberately outside this lemma. -/
abbrev OutputWords16 := List (List Nat)

def outputTermCount16 : OutputWords16 → Nat
  | [] => 0
  | ms :: rest => ms.length + outputTermCount16 rest

def OrderedOutputs16 (width : Nat) : OutputWords16 → Prop
  | [] => True
  | ms :: rest =>
      OrderedMaskWords width none ms ∧ OrderedOutputs16 width rest

theorem orderedMaskWords_from_pairwise
    (width : Nat) (previous : Option Nat) (ms : List Nat)
    (hb : ∀ m ∈ ms, m < 2 ^ width)
    (hs : ms.Pairwise (fun a b : Nat => a < b))
    (hp : ∀ m ∈ ms, afterPrevious previous m) :
    OrderedMaskWords width previous ms := by
  induction ms generalizing previous with
  | nil => trivial
  | cons m rest ih =>
      have hd := List.pairwise_cons.mp hs
      refine ⟨hb m (by simp), hp m (by simp), ?_⟩
      apply ih (some m)
      · intro x hx
        exact hb x (List.mem_cons.mpr (Or.inr hx))
      · exact hd.2
      · intro x hx
        exact hd.1 x hx

inductive Outputs16Result where
  | accepted (outputs : OutputWords16) (rest : WireBytes) (total frameUsed : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

def decodeOutputs16 (width : Nat) :
    Nat → Nat → Nat → WireBytes → Outputs16Result
  | 0, total, frameUsed, bs => .accepted [] bs total frameUsed
  | n + 1, total, frameUsed, bs =>
      match decodeTermFrame16 width total frameUsed bs with
      | .invalidProof => .invalidProof
      | .unknownResource => .unknownResource
      | .accepted ms tail t f =>
          match decodeOutputs16 width n t f tail with
          | .invalidProof => .invalidProof
          | .unknownResource => .unknownResource
          | .accepted xs rest t' f' => .accepted (ms :: xs) rest t' f'

/-- The n output fields share counters, consume exactly their declared
    bytes, and contain only canonical ordered ANFs. -/
theorem decodeOutputs16_sound
    (width n total frameUsed : Nat) (bs : WireBytes)
    (xs : OutputWords16) (rest : WireBytes) (t f : Nat)
    (h : decodeOutputs16 width n total frameUsed bs =
      .accepted xs rest t f) :
    xs.length = n ∧ OrderedOutputs16 width xs ∧
      t = total + outputTermCount16 xs ∧
      f = frameUsed + outputTermCount16 xs ∧
      bs.length = 2 * n + 8 * outputTermCount16 xs + rest.length := by
  induction n generalizing total frameUsed bs xs rest t f with
  | zero =>
      simp [decodeOutputs16] at h
      obtain ⟨rfl,rfl,rfl,rfl⟩ := h
      simp [OrderedOutputs16,outputTermCount16]
  | succ n ih =>
      cases hh : decodeTermFrame16 width total frameUsed bs with
      | invalidProof => simp [decodeOutputs16,hh] at h
      | unknownResource => simp [decodeOutputs16,hh] at h
      | accepted ms tail t0 f0 =>
          cases ht : decodeOutputs16 width n t0 f0 tail with
          | invalidProof => simp [decodeOutputs16,hh,ht] at h
          | unknownResource => simp [decodeOutputs16,hh,ht] at h
          | accepted ys endBytes t1 f1 =>
              simp [decodeOutputs16,hh,ht] at h
              obtain ⟨rfl,rfl,rfl,rfl⟩ := h
              obtain ⟨_,h1,h2,_,_,hlen,hb,hs⟩ :=
                decodeTermFrame16_sound width total frameUsed bs ms tail t0 f0 hh
              obtain ⟨hl,ho,h3,h4,hrest⟩ := ih t0 f0 tail ys endBytes t1 f1 ht
              have hmask : OrderedMaskWords width none ms :=
                orderedMaskWords_from_pairwise width none ms hb hs
                  (by intro m _; exact True.intro)
              refine ⟨by simp [hl], ⟨hmask,ho⟩, ?_, ?_, ?_⟩
              · simp only [outputTermCount16]; omega
              · simp only [outputTermCount16]; omega
              · simp only [outputTermCount16]; omega

def encodeOutputs16 : OutputWords16 → WireBytes
  | [] => []
  | ms :: rest => encodeTermFrame16 ms ++ encodeOutputs16 rest

theorem decodeOutputs16_roundtrip
    (width total frameUsed : Nat) (xs : OutputWords16)
    (tail : WireBytes) (hw : width ≤ 16)
    (ho : OrderedOutputs16 width xs)
    (ht : total + outputTermCount16 xs ≤ 32768)
    (hf : frameUsed + outputTermCount16 xs ≤ 256) :
    decodeOutputs16 width xs.length total frameUsed
      (encodeOutputs16 xs ++ tail) =
      .accepted xs tail (total + outputTermCount16 xs)
        (frameUsed + outputTermCount16 xs) := by
  induction xs generalizing total frameUsed with
  | nil => simp [decodeOutputs16,encodeOutputs16,outputTermCount16]
  | cons ms rest ih =>
      have hc : outputTermCount16 (ms :: rest) =
          ms.length + outputTermCount16 rest := rfl
      have ht0 : total + ms.length ≤ 32768 := by omega
      have hf0 : frameUsed + ms.length ≤ 256 := by omega
      have ht1 : total + ms.length + outputTermCount16 rest ≤ 32768 := by omega
      have hf1 : frameUsed + ms.length + outputTermCount16 rest ≤ 256 := by omega
      have hfirst := decodeTermFrame16_roundtrip width total frameUsed
        ms (encodeOutputs16 rest ++ tail) hw ho.1 ht0 hf0
      have hrest := ih (total + ms.length) (frameUsed + ms.length)
        ho.2 ht1 hf1
      simp [decodeOutputs16,encodeOutputs16,List.append_assoc,
        hfirst,hrest,outputTermCount16,Nat.add_assoc]

inductive StateFrame16Result where
  | accepted (paths : Nat) (outputs : OutputWords16)
      (phase : PhaseWords16) (rest : WireBytes) (total : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

/-- Model only the admitted <=16-symbol profile. In contrast, Rust
    P8C1 admits larger widths; this lemma is not a general parser proof.
    The local frame counter starts at zero and is shared by all fields. -/
def decodeStateFrame16 (n total : Nat) (bs : WireBytes) :
    StateFrame16Result :=
  match readLE 1 bs with
  | none => .invalidProof
  | some (paths,tail) =>
      if 0 < n ∧ n + paths ≤ 16 then
        match decodeOutputs16 (n + paths) n total 0 tail with
        | .invalidProof => .invalidProof
        | .unknownResource => .unknownResource
        | .accepted xs payload t f =>
            match decodePhaseFrame16 (n + paths) t f payload with
            | .invalidProof => .invalidProof
            | .unknownResource => .unknownResource
            | .accepted ps rest t' _ =>
                .accepted paths xs ps rest t'
      else .invalidProof

/-- Joint validity of the entire per-gate state; in particular the
    phase terms cannot bypass the budget already consumed by ANFs. -/
theorem decodeStateFrame16_sound
    (n total : Nat) (bs : WireBytes) (paths : Nat)
    (xs : OutputWords16) (ps : PhaseWords16)
    (rest : WireBytes) (t : Nat)
    (h : decodeStateFrame16 n total bs =
      .accepted paths xs ps rest t) :
    0 < n ∧ n + paths ≤ 16 ∧ xs.length = n ∧
      OrderedOutputs16 (n + paths) xs ∧
      OrderedPhaseWords (n + paths) none ps ∧
      t = total + outputTermCount16 xs + ps.length ∧
      t ≤ 32768 ∧ outputTermCount16 xs + ps.length ≤ 256 ∧
      bs.length = 3 + 2 * n + 8 * outputTermCount16 xs +
        9 * ps.length + rest.length := by
  cases hh : readLE 1 bs with
  | none => simp [decodeStateFrame16,hh] at h
  | some head =>
      obtain ⟨p,tail⟩ := head
      by_cases hg : 0 < n ∧ n + p ≤ 16
      · cases ho : decodeOutputs16 (n+p) n total 0 tail with
        | invalidProof => simp [decodeStateFrame16,hh,hg,ho] at h
        | unknownResource => simp [decodeStateFrame16,hh,hg,ho] at h
        | accepted ys payload t0 f0 =>
            cases hp : decodePhaseFrame16 (n+p) t0 f0 payload with
            | invalidProof => simp [decodeStateFrame16,hh,hg,ho,hp] at h
            | unknownResource => simp [decodeStateFrame16,hh,hg,ho,hp] at h
            | accepted qs endBytes t1 f1 =>
                simp [decodeStateFrame16,hh,hg,ho,hp] at h
                obtain ⟨rfl,rfl,rfl,rfl,rfl⟩ := h
                obtain ⟨hn,hy,ht,hf,hsize⟩ :=
                  decodeOutputs16_sound (n+p) n total 0 tail ys payload t0 f0 ho
                obtain ⟨_,ht',hf',hmax,hframe,hphase,hq,_,_⟩ :=
                  decodePhaseFrame16_sound (n+p) t0 f0 payload qs endBytes t1 f1 hp
                have hheader := readLE_consumes 1 bs p tail hh
                exact ⟨hg.1,hg.2,hn,hy,hq,by omega,hmax,by omega,by omega⟩
      · simp [decodeStateFrame16,hh,hg] at h

def encodeStateFrame16 (paths : Nat) (xs : OutputWords16)
    (ps : PhaseWords16) : WireBytes :=
  encodeLE 1 paths ++ encodeOutputs16 xs ++ encodePhaseFrame16 ps

/-- Every valid per-gate state roundtrips, with exact counters and
    suffix. This composes both previously proved termset codecs. -/
theorem decodeStateFrame16_roundtrip
    (n total paths : Nat) (xs : OutputWords16) (ps : PhaseWords16)
    (tail : WireBytes) (hn : 0 < n) (hw : n + paths ≤ 16)
    (hl : xs.length = n)
    (ho : OrderedOutputs16 (n + paths) xs)
    (hp : OrderedPhaseWords (n + paths) none ps)
    (ht : total + outputTermCount16 xs + ps.length ≤ 32768)
    (hf : outputTermCount16 xs + ps.length ≤ 256) :
    decodeStateFrame16 n total (encodeStateFrame16 paths xs ps ++ tail) =
      .accepted paths xs ps tail (total + outputTermCount16 xs + ps.length) := by
  have hpaths : paths < 256 ^ 1 := by omega
  have hhead := readLE_encodeLE 1 paths
    (encodeOutputs16 xs ++ (encodePhaseFrame16 ps ++ tail)) hpaths
  have ht0 : total + outputTermCount16 xs ≤ 32768 := by omega
  have hf0 : 0 + outputTermCount16 xs ≤ 256 := by omega
  have hout := decodeOutputs16_roundtrip (n+paths) total 0 xs
    (encodePhaseFrame16 ps ++ tail) hw ho ht0 hf0
  rw [hl] at hout
  have hphase := decodePhaseFrame16_roundtrip (n+paths)
    (total + outputTermCount16 xs) (0 + outputTermCount16 xs)
    ps tail hw hp ht (by omega)
  have hg : 0 < n ∧ n + paths ≤ 16 := ⟨hn,hw⟩
  simp [decodeStateFrame16,encodeStateFrame16,List.append_assoc,
    hhead,hg,hout,hphase]

#print axioms orderedMaskWords_from_pairwise
#print axioms decodeOutputs16_sound
#print axioms decodeOutputs16_roundtrip
#print axioms decodeStateFrame16_sound
#print axioms decodeStateFrame16_roundtrip

#eval decodeStateFrame16 2 0
  (encodeStateFrame16 1 [[1],[2,4]] [(0,1),(7,4)] ++ [42])
#eval decodeStateFrame16 1 0
  (encodeStateFrame16 16 [[1]] [])

end QuPRS.P0
