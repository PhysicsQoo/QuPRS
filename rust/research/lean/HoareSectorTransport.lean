/-
Research-only exact sector transport proof kernel.
Integer coefficient-vector amplitudes, arbitrary basis types and dimensions.
The matrix-entry transport equation is a premise, NOT a proved refinement
of H^n M H^n, a complex embedding, or the implementation. Nonzero output
for each legal input is also a premise, representing unitary normalization.
Proves conditional terminal soundness plus local Z8 arithmetic identities.
-/
import Std

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.SectorTransport

def bx (a b : Bool) : Bool := if a then !b else b

def sgn (b : Bool) : Int := if b then -1 else 1

theorem sign_mul (a b : Bool) :
    sgn (bx a b) = sgn a * sgn b := by
  cases a <;> cases b <;> decide

theorem opposite_sign_zero (a b e : Bool) (v : Int)
    (h : sgn a * v = sgn (bx e b) * v)
    (hne : a ≠ bx e b) : v = 0 := by
  cases a <;> cases b <;> cases e <;> simp [sgn, bx] at h hne <;> omega

/-- If the entrywise transport equation holds, all nonzero integer
    coefficients vanish outside the transported sector. -/
theorem support_sector {X Z : Type} (amp : X → Z → Nat → Int)
    (input : X → Bool) (output : Z → Bool) (b : Bool)
    (transport : ∀ x z j, sgn (output z) * amp x z j =
      sgn (bx (input x) b) * amp x z j)
    (x : X) (z : Z) (j : Nat) (hne : output z ≠ bx (input x) b) :
    amp x z j = 0 :=
  opposite_sign_zero (output z) b (input x) (amp x z j) (transport x z j) hne

def Bad {X Z : Type} (pre : X → Prop) (output : Z → Bool)
    (q : Bool) (amp : X → Z → Nat → Int) : Prop :=
  ∃ x z j, pre x ∧ output z ≠ q ∧ amp x z j ≠ 0

theorem sector_proved {X Z : Type} (pre : X → Prop)
    (amp : X → Z → Nat → Int) (input : X → Bool) (output : Z → Bool)
    (e b q : Bool)
    (transport : ∀ x z j, sgn (output z) * amp x z j =
      sgn (bx (input x) b) * amp x z j)
    (fixed : ∀ x, pre x → input x = e)
    (hmatches : bx e b = q) :
    ¬ Bad pre output q amp := by
  rintro ⟨x, z, j, hp, hn, ha⟩
  apply ha
  apply support_sector amp input output b transport x z j
  rw [fixed x hp, hmatches]
  exact hn

/-- Opposite-sector refutation requires a genuine admitted input and
    nonzero output, not merely a failed proof attempt. -/
theorem sector_refuted {X Z : Type} (pre : X → Prop)
    (amp : X → Z → Nat → Int) (input : X → Bool) (output : Z → Bool)
    (e b q : Bool)
    (transport : ∀ x z j, sgn (output z) * amp x z j =
      sgn (bx (input x) b) * amp x z j)
    (fixed : ∀ x, pre x → input x = e)
    (opposite : bx e b ≠ q)
    (x : X) (hp : pre x) (nonzero : ∃ z j, amp x z j ≠ 0) :
    Bad pre output q amp := by
  rcases nonzero with ⟨z, j, ha⟩
  have hz : output z = bx (input x) b := by
    by_cases he : output z = bx (input x) b
    · exact he
    · exact False.elim (ha (support_sector amp input output b transport x z j he))
  refine ⟨x, z, j, hp, ?_, ha⟩
  rw [hz, fixed x hp]
  exact opposite

inductive Verdict where
  | proved | refuted | unknown
deriving DecidableEq

def Sound (bad : Prop) : Verdict → Prop
  | .proved => ¬ bad
  | .refuted => bad
  | .unknown => True

def terminal (admit : Bool) (e b q : Bool) : Verdict :=
  if admit then
    if bx e b = q then .proved else .refuted
  else .unknown

theorem terminal_unknown (e b q : Bool) :
    terminal false e b q = .unknown := rfl

theorem terminal_sound {X Z : Type} (pre : X → Prop)
    (amp : X → Z → Nat → Int) (input : X → Bool) (output : Z → Bool)
    (admit e b q : Bool)
    (certificate : admit = true →
      (∀ x z j, sgn (output z) * amp x z j =
        sgn (bx (input x) b) * amp x z j) ∧
      (∀ x, pre x → input x = e) ∧
      (∃ x, pre x ∧ ∃ z j, amp x z j ≠ 0)) :
    Sound (Bad pre output q amp) (terminal admit e b q) := by
  cases admit with
  | false => exact True.intro
  | true =>
      obtain ⟨ht, hf, x, hp, hn⟩ := certificate rfl
      by_cases hm : bx e b = q
      · simpa [terminal, Sound, hm] using
          sector_proved pre amp input output e b q ht hf hm
      · simpa [terminal, Sound, hm] using
          sector_refuted pre amp input output e b q ht hf hm x hp hn

/- Local arithmetic identities used in gate-level phase derivative.
   These do not yet establish the all-gates replay invariant or
   multilinear polynomial normalization. -/
def bit (b : Bool) : Int := if b then 1 else 0

theorem bit_xor (a b : Bool) :
    bit (bx a b) = bit a + bit b - 2 * bit a * bit b := by
  cases a <;> cases b <;> decide

theorem single_phase_shift (a d : Bool) (k : Int) :
    k * (bit (bx a d) - bit a) =
      (if d then k * (1 - 2 * bit a) else 0) := by
  cases a <;> cases d <;> simp [bx, bit] <;> omega

theorem cz_phase_shift (a b d e : Bool) :
    (4 * (bit (bx a d) * bit (bx b e) - bit a * bit b)) % 8 =
      (4 * (bit d * bit b + bit e * bit a + bit d * bit e)) % 8 := by
  cases a <;> cases b <;> cases d <;> cases e <;> decide

theorem even_xor_mod8 (a b : Bool) (k : Int) :
    (2 * k * bit (bx a b)) % 8 =
      (2 * k * bit a + 2 * k * bit b - 4 * k * bit a * bit b) % 8 := by
  cases a <;> cases b <;> simp [bx, bit] <;> omega

#print axioms sign_mul
#print axioms opposite_sign_zero
#print axioms support_sector
#print axioms sector_proved
#print axioms sector_refuted
#print axioms terminal_unknown
#print axioms terminal_sound
#print axioms bit_xor
#print axioms single_phase_shift
#print axioms cz_phase_shift
#print axioms even_xor_mod8

/-! Gate sequence replay: concrete Boolean basis state and Z8 phase
    semantics. Arbitrary finite list, no bound on wires or length.
    The following does not prove the Python affine-mask / polynomial
    representation, nor Fourier/complex embedding or source admission. -/

abbrev State := Nat → Bool

inductive Gate where
  | flip (a : Nat)
  | cnot (a b : Nat)
  | z (a : Nat)
  | s (a : Nat)
  | t (a : Nat)
  | cz (a b : Nat)

def shifted (x d : State) : State := fun i => bx (x i) (d i)

def cnotState (a b : Nat) (x : State) : State :=
  fun i => if i = b then bx (x i) (x a) else x i

def advance (g : Gate) (x : State) : State :=
  match g with
  | .flip a => fun i => if i = a then !(x i) else x i
  | .cnot a b => cnotState a b x
  | _ => x

def advanceDelta (g : Gate) (d : State) : State :=
  match g with
  | .cnot a b => cnotState a b d
  | _ => d

def localPhase (g : Gate) (x : State) : Int :=
  match g with
  | .z a => 4 * bit (x a)
  | .s a => 2 * bit (x a)
  | .t a => bit (x a)
  | .cz a b => 4 * bit (x a) * bit (x b)
  | _ => 0

def singleDelta (k : Int) (x d : Bool) : Int :=
  if d then k * (1 - 2 * bit x) else 0

def localDelta (g : Gate) (x d : State) : Int :=
  match g with
  | .z a => singleDelta 4 (x a) (d a)
  | .s a => singleDelta 2 (x a) (d a)
  | .t a => singleDelta 1 (x a) (d a)
  | .cz a b =>
      4 * (bit (d a) * bit (x b) + bit (d b) * bit (x a) + bit (d a) * bit (d b))
  | _ => 0

theorem bx_flip (a b : Bool) :
    !(bx a b) = bx (!a) b := by
  cases a <;> cases b <;> decide

theorem bx_four (a b c d : Bool) :
    bx (bx a b) (bx c d) = bx (bx a c) (bx b d) := by
  cases a <;> cases b <;> cases c <;> cases d <;> decide

theorem advance_shift (g : Gate) (x d : State) :
    advance g (shifted x d) = shifted (advance g x) (advanceDelta g d) := by
  cases g with
  | flip a =>
      funext i
      by_cases h : i = a
      · subst i
        simpa only [advance, advanceDelta, shifted, if_pos rfl] using bx_flip (x a) (d a)
      · simp [advance, advanceDelta, shifted, h]
  | cnot a b =>
      funext i
      by_cases h : i = b
      · subst i
        simpa only [advance, advanceDelta, cnotState, shifted, if_pos rfl] using
          bx_four (x b) (d b) (x a) (d a)
      · simp [advance, advanceDelta, cnotState, shifted, h]
  | z a => rfl
  | s a => rfl
  | t a => rfl
  | cz a b => rfl

theorem local_phase_delta (g : Gate) (x d : State) :
    (localPhase g (shifted x d) - localPhase g x) % 8 =
      localDelta g x d % 8 := by
  cases g with
  | flip a => rfl
  | cnot a b => rfl
  | z a =>
      cases hx : x a <;> cases hd : d a <;>
        simp [localPhase, localDelta, shifted, singleDelta, hx, hd, bx, bit]
  | s a =>
      cases hx : x a <;> cases hd : d a <;>
        simp [localPhase, localDelta, shifted, singleDelta, hx, hd, bx, bit]
  | t a =>
      cases hx : x a <;> cases hd : d a <;>
        simp [localPhase, localDelta, shifted, singleDelta, hx, hd, bx, bit]
  | cz a b =>
      cases ha : x a <;> cases hb : x b <;>
        cases hd : d a <;> cases he : d b <;>
        simp [localPhase, localDelta, shifted, ha, hb, hd, he, bx, bit] <;> decide

def evalState : List Gate → State → State
  | [], x => x
  | g :: rest, x => evalState rest (advance g x)

def evalPhase : List Gate → State → Int
  | [], _ => 0
  | g :: rest, x => localPhase g x + evalPhase rest (advance g x)

def traceDelta : List Gate → State → State
  | [], d => d
  | g :: rest, d => traceDelta rest (advanceDelta g d)

def tracePhase : List Gate → State → State → Int
  | [], _, _ => 0
  | g :: rest, x, d =>
      localDelta g x d + tracePhase rest (advance g x) (advanceDelta g d)

theorem replay_state_shift (gs : List Gate) (x d : State) :
    evalState gs (shifted x d) =
      shifted (evalState gs x) (traceDelta gs d) := by
  induction gs generalizing x d with
  | nil => rfl
  | cons g gs ih =>
      simp only [evalState, traceDelta]
      rw [advance_shift]
      exact ih (advance g x) (advanceDelta g d)

theorem replay_phase_shift (gs : List Gate) (x d : State) :
    (evalPhase gs (shifted x d) - evalPhase gs x) % 8 =
      tracePhase gs x d % 8 := by
  induction gs generalizing x d with
  | nil => rfl
  | cons g gs ih =>
      simp only [evalPhase, tracePhase]
      rw [advance_shift]
      have hlocal := local_phase_delta g x d
      have htail := ih (advance g x) (advanceDelta g d)
      omega

/-- A certificate that replays the requested output translation and
    a constant phase modulo 8 suffices for the basis-action relation.
    The certificate checker must still prove these premises. -/
theorem replay_constant_translation (gs : List Gate) (s t : State) (b : Bool)
    (ht : traceDelta gs s = t)
    (hp : ∀ x : State, tracePhase gs x s % 8 = 4 * bit b) :
    ∀ x : State,
      evalState gs (shifted x s) = shifted (evalState gs x) t ∧
      (evalPhase gs (shifted x s) - evalPhase gs x) % 8 = 4 * bit b := by
  intro x
  constructor
  · rw [replay_state_shift, ht]
  · rw [replay_phase_shift, hp x]

#print axioms bx_flip
#print axioms bx_four
#print axioms advance_shift
#print axioms local_phase_delta
#print axioms replay_state_shift
#print axioms replay_phase_shift
#print axioms replay_constant_translation

end QuPRS.SectorTransport
