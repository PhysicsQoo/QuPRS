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
  | accepted (masks : List Nat) (rest : WireBytes) (total local : Nat)
  | invalidProof
  | unknownResource
  deriving Repr, DecidableEq

/-- The order of the checks matches the bounded frame contract:
    read count, charge both limits, then parse masks. Width >16 is
    outside this symbolic specification (not general P8C1). -/
def decodeTermFrame16 (width total local : Nat) (bs : WireBytes) :
    TermFrame16Result :=
  if width ≤ 16 then
    match readLE 2 bs with
    | none => .invalidProof
    | some (count, tail) =>
        if 32768 < total + count ∨ 256 < local + count then
          .unknownResource
        else
          match readOrderedMasks width count none tail with
          | none => .invalidProof
          | some (ms, rest) => .accepted ms rest (total + count) (local + count)
  else .invalidProof

/-- Acceptance entails exact declared count/byte consumption,
    width, order and both budgets; no truncated list is accepted. -/
theorem decodeTermFrame16_sound
    (width total local : Nat) (bs : WireBytes)
    (ms : List Nat) (rest : WireBytes) (total' local' : Nat)
    (h : decodeTermFrame16 width total local bs =
      .accepted ms rest total' local') :
    width ≤ 16 ∧ total' = total + ms.length ∧
      local' = local + ms.length ∧ total' ≤ 32768 ∧
      local' ≤ 256 ∧ bs.length = 2 + 8 * ms.length + rest.length ∧
      (∀ m ∈ ms, m < 2 ^ width) ∧
      ms.Pairwise (fun a b => a < b) := by
  by_cases hw : width ≤ 16
  · cases hh : readLE 2 bs with
    | none => simp [decodeTermFrame16, hw, hh] at h
    | some p =>
        obtain ⟨count, tail⟩ := p
        by_cases hb : 32768 < total + count ∨ 256 < local + count
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
    (width total local count : Nat) (bs tail : WireBytes)
    (hw : width ≤ 16) (hh : readLE 2 bs = some (count, tail))
    (hb : 32768 < total + count ∨ 256 < local + count) :
    decodeTermFrame16 width total local bs = .unknownResource := by
  simp [decodeTermFrame16, hw, hh, hb]

/-- Trailing bytes belong to the caller's subsequent frame; this
    exact-frame wrapper rejects any trailing bytes. -/
def decodeExactTermFrame16 (width total local : Nat) (bs : WireBytes) :
    TermFrame16Result :=
  match decodeTermFrame16 width total local bs with
  | .accepted ms [] t l => .accepted ms [] t l
  | .accepted _ (_ :: _) _ _ => .invalidProof
  | .invalidProof => .invalidProof
  | .unknownResource => .unknownResource

theorem decodeExactTermFrame16_no_trailing
    (width total local : Nat) (bs : WireBytes)
    (ms : List Nat) (rest : WireBytes) (t l : Nat)
    (h : decodeExactTermFrame16 width total local bs =
      .accepted ms rest t l) : rest = [] := by
  cases hf : decodeTermFrame16 width total local bs with
  | invalidProof => simp [decodeExactTermFrame16, hf] at h
  | unknownResource => simp [decodeExactTermFrame16, hf] at h
  | accepted xs tail t' l' =>
      cases tail with
      | nil =>
          simp [decodeExactTermFrame16, hf] at h
          exact h.2.1.symm
      | cons a as => simp [decodeExactTermFrame16, hf] at h

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

end QuPRS.P0
