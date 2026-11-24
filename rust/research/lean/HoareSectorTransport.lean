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
    (!(bx a b)) = bx (!a) b := by
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
        simpa [advance, advanceDelta, shifted] using bx_flip (x a) (d a)
      · simp [advance, advanceDelta, shifted, h]
  | cnot a b =>
      funext i
      by_cases h : i = b
      · subst i
        simpa [advance, advanceDelta, cnotState, shifted] using
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

/-! Independent affine row-combination certificate.
    Masks are Boolean functions restricted to the first n wires.
    The selected original rows are determined by a Boolean list.
    The checker verifies the combination and a separate legal witness;
    no assumption about Gaussian elimination or completeness is needed.
    This is a Lean reference checker, not a refinement of Python/Rust
    packed masks or of the original circuit parser. -/

def maskXor (a b : State) : State := fun i => bx (a i) (b i)

def dot : Nat → State → State → Bool
  | 0, _, _ => false
  | n+1, m, x => bx (dot n m x) (m n && x n)

theorem bx_and (a b c : Bool) :
    (bx a b && c) = bx (a && c) (b && c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem bx_zero_right (a : Bool) : bx a false = a := by
  cases a <;> decide

theorem dot_zero (n : Nat) (x : State) :
    dot n (fun _ => false) x = false := by
  induction n with
  | zero => rfl
  | succ n ih => simp [dot, ih, bx]

theorem dot_xor (n : Nat) (m s x : State) :
    dot n (maskXor m s) x = bx (dot n m x) (dot n s x) := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [dot, maskXor]
      rw [ih, bx_and]
      exact bx_four (dot n m x) (dot n s x) (m n && x n) (s n && x n)

def sameMask : Nat → State → State → Bool
  | 0, _, _ => true
  | n+1, m, s => sameMask n m s && decide (m n = s n)

theorem sameMask_dot (n : Nat) (m s x : State)
    (h : sameMask n m s = true) :
    dot n m x = dot n s x := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have hh : sameMask n m s = true ∧ m n = s n := by
        simpa [sameMask] using h
      simp only [dot]
      rw [ih hh.1, hh.2]

structure AffineRow where
  mask : State
  rhs : Bool

def zeroRow : AffineRow := ⟨fun _ => false, false⟩

def rowXor (a b : AffineRow) : AffineRow :=
  ⟨maskXor a.mask b.mask, bx a.rhs b.rhs⟩

def rowOK (n : Nat) (r : AffineRow) (x : State) : Prop :=
  dot n r.mask x = r.rhs

theorem row_zero_ok (n : Nat) (x : State) : rowOK n zeroRow x := by
  exact dot_zero n x

theorem row_xor_ok (n : Nat) (a b : AffineRow) (x : State)
    (ha : rowOK n a x) (hb : rowOK n b x) : rowOK n (rowXor a b) x := by
  unfold rowOK at ha hb ⊢
  change dot n (maskXor a.mask b.mask) x = bx a.rhs b.rhs
  rw [dot_xor, ha, hb]

def combined : List AffineRow → List Bool → AffineRow
  | [], _ => zeroRow
  | _, [] => zeroRow
  | r :: rs, b :: bs =>
      if b then rowXor r (combined rs bs) else combined rs bs

def affinePre (n : Nat) (rs : List AffineRow) (x : State) : Prop :=
  ∀ r : AffineRow, r ∈ rs → rowOK n r x

theorem combined_ok (n : Nat) (rs : List AffineRow) (bs : List Bool)
    (x : State) (hp : affinePre n rs x) : rowOK n (combined rs bs) x := by
  induction rs generalizing bs with
  | nil => exact row_zero_ok n x
  | cons r rs ih =>
      have hr : rowOK n r x := hp r (by simp)
      have ht : affinePre n rs x := by
        intro a ha
        exact hp a (List.mem_cons_of_mem _ ha)
      cases bs with
      | nil => exact row_zero_ok n x
      | cons b bs =>
          cases b with
          | false =>
              simpa [combined] using ih bs ht
          | true =>
              simpa [combined] using row_xor_ok n r (combined rs bs) x hr (ih bs ht)

def checkCombination (n : Nat) (rs : List AffineRow) (bs : List Bool)
    (s : State) (e : Bool) : Bool :=
  let r := combined rs bs
  decide (rs.length = bs.length) && (sameMask n r.mask s && decide (r.rhs = e))

theorem combination_sound (n : Nat) (rs : List AffineRow) (bs : List Bool)
    (s : State) (e : Bool)
    (hc : checkCombination n rs bs s e = true) :
    ∀ x, affinePre n rs x → dot n s x = e := by
  have h : rs.length = bs.length ∧
      (sameMask n (combined rs bs).mask s = true ∧ (combined rs bs).rhs = e) := by
    simpa [checkCombination] using hc
  intro x hp
  have he := combined_ok n rs bs x hp
  unfold rowOK at he
  rw [← sameMask_dot n (combined rs bs).mask s x h.2.1, he, h.2.2]

def checkWitness (n : Nat) (x : State) : List AffineRow → Bool
  | [] => true
  | r :: rs => decide (dot n r.mask x = r.rhs) && checkWitness n x rs

theorem witness_sound (n : Nat) (rs : List AffineRow) (x : State)
    (hc : checkWitness n x rs = true) : affinePre n rs x := by
  induction rs with
  | nil =>
      intro r hr
      simp at hr
  | cons r rs ih =>
      have h : dot n r.mask x = r.rhs ∧ checkWitness n x rs = true := by
        simpa [checkWitness] using hc
      intro a ha
      rcases List.mem_cons.mp ha with he | ht
      · subst a
        exact h.1
      · exact ih h.2 a ht

/-- Connect the independent combination and witness checkers to the
    existing terminal theorem. Transport and nonzero output remain
    explicit semantic premises. -/
theorem checked_affine_terminal_sound {Z : Type} (n : Nat)
    (rs : List AffineRow) (bs : List Bool) (s w : State)
    (amp : State → Z → Nat → Int) (output : Z → Bool)
    (e b q : Bool)
    (hc : checkCombination n rs bs s e = true)
    (hw : checkWitness n w rs = true)
    (transport : ∀ x z j, sgn (output z) * amp x z j =
      sgn (bx (dot n s x) b) * amp x z j)
    (nonzero : ∃ z j, amp w z j ≠ 0) :
    Sound (Bad (affinePre n rs) output q amp) (terminal true e b q) := by
  apply terminal_sound (affinePre n rs) amp (dot n s) output true e b q
  intro _
  exact ⟨transport, combination_sound n rs bs s e hc, w, witness_sound n rs w hw, nonzero⟩

#print axioms bx_and
#print axioms bx_zero_right
#print axioms dot_zero
#print axioms dot_xor
#print axioms sameMask_dot
#print axioms row_zero_ok
#print axioms row_xor_ok
#print axioms combined_ok
#print axioms combination_sound
#print axioms witness_sound
#print axioms checked_affine_terminal_sound

/-! Quadratic degree bound for the exact derivative of a monomial
    Clifford+T circuit. The symbolic affine frame is deliberately a
    list of XOR atoms, not the producer's packed masks. QExpr can only
    express constants, linear and quadratic monomials and their linear
    combinations. Repeated wire indices are harmless on Boolean inputs.
    This is a reference semantics theorem, not a complexity claim for
    this list representation or a packed-mask implementation refinement. -/

inductive Atom where
  | wire (i : Nat)
  | one

def atomVal (a : Atom) (x : State) : Bool :=
  match a with
  | .wire i => x i
  | .one => true

abbrev Form := List Atom

def formVal (f : Form) (x : State) : Bool :=
  match f with
  | [] => false
  | a :: rest => bx (atomVal a x) (formVal rest x)

inductive QExpr where
  | constant (k : Int)
  | linear (k : Int) (a : Atom)
  | pair (k : Int) (a b : Atom)
  | add (a b : QExpr)
  | scale (k : Int) (a : QExpr)

def evalQ (q : QExpr) (x : State) : Int :=
  match q with
  | .constant k => k
  | .linear k a => k * bit (atomVal a x)
  | .pair k a b => k * bit (atomVal a x) * bit (atomVal b x)
  | .add a b => evalQ a x + evalQ b x
  | .scale k a => k * evalQ a x

theorem bx_assoc (a b c : Bool) :
    bx (bx a b) c = bx a (bx b c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem form_append (a b : Form) (x : State) :
    formVal (a ++ b) x = bx (formVal a x) (formVal b x) := by
  induction a with
  | nil => rfl
  | cons c a ih =>
      simp only [List.cons_append, formVal, ih]
      exact (bx_assoc (atomVal c x) (formVal a x) (formVal b x)).symm

def fourPoly : Form → QExpr
  | [] => .constant 0
  | a :: f => .add (.linear 4 a) (fourPoly f)

def crossFour (a : Atom) : Form → QExpr
  | [] => .constant 0
  | b :: f => .add (.pair 4 a b) (crossFour a f)

def twoPoly : Form → QExpr
  | [] => .constant 0
  | a :: f => .add (.linear 2 a) (.add (twoPoly f) (.scale (-1) (crossFour a f)))

theorem four_poly_sound (f : Form) (x : State) :
    evalQ (fourPoly f) x % 8 = (4 * bit (formVal f x)) % 8 := by
  induction f with
  | nil => rfl
  | cons a f ih =>
      cases ha : atomVal a x <;> cases hf : formVal f x <;>
        simp [hf, bit] at ih <;>
        simp [fourPoly, evalQ, formVal, ha, hf, bx, bit] <;> omega

theorem cross_four_eval (a : Atom) (f : Form) (x : State) :
    evalQ (crossFour a f) x =
      if atomVal a x then evalQ (fourPoly f) x else 0 := by
  induction f with
  | nil => cases ha : atomVal a x <;> simp [crossFour, fourPoly, evalQ, ha]
  | cons b f ih =>
      cases ha : atomVal a x <;>
        simp [ha] at ih <;>
        simp [crossFour, fourPoly, evalQ, ha, bit, ih]

theorem two_poly_sound (f : Form) (x : State) :
    evalQ (twoPoly f) x % 8 = (2 * bit (formVal f x)) % 8 := by
  induction f with
  | nil => rfl
  | cons a f ih =>
      have h4 := four_poly_sound f x
      have hc := cross_four_eval a f x
      cases ha : atomVal a x <;> cases hf : formVal f x <;>
        simp [hf, bit] at ih h4 <;>
        simp [ha] at hc <;>
        simp [twoPoly, evalQ, formVal, ha, hf, bx, bit, hc] <;> omega

abbrev Frame := Nat → Form

def evalFrame (f : Frame) (x : State) : State :=
  fun i => formVal (f i) x

def identityFrame : Frame := fun i => [.wire i]

def advanceFrame (g : Gate) (f : Frame) : Frame :=
  match g with
  | .flip a => fun i => if i = a then .one :: f i else f i
  | .cnot a b => fun i => if i = b then f i ++ f a else f i
  | _ => f

theorem identity_frame_eval (x : State) : evalFrame identityFrame x = x := by
  funext i
  simp [evalFrame, identityFrame, formVal, atomVal, bx_zero_right]

theorem advance_frame_eval (g : Gate) (f : Frame) (x : State) :
    evalFrame (advanceFrame g f) x = advance g (evalFrame f x) := by
  cases g with
  | flip a =>
      funext i
      by_cases h : i = a <;>
        simp [advanceFrame, evalFrame, advance, formVal, atomVal, bx, h]
  | cnot a b =>
      funext i
      by_cases h : i = b <;>
        simp [advanceFrame, evalFrame, advance, cnotState, form_append, h]
  | z a => rfl
  | s a => rfl
  | t a => rfl
  | cz a b => rfl

def singleQuad (k : Int) (f : Form) (d : Bool) : QExpr :=
  if d then .add (.constant k) (.scale (-k) (twoPoly f)) else .constant 0

theorem single_quad_sound (k : Int) (f : Form) (d : Bool) (x : State)
    (hk : k = 1 ∨ k = 2 ∨ k = 4) :
    evalQ (singleQuad k f d) x % 8 =
      singleDelta k (formVal f x) d % 8 := by
  cases d with
  | false => rfl
  | true =>
      have h := two_poly_sound f x
      rcases hk with he | he | he <;> subst k <;>
        cases hv : formVal f x <;>
        simp [hv, bit] at h <;>
        simp [singleQuad, evalQ, singleDelta, hv, bit] <;> omega

def selectedFour (d : Bool) (f : Form) : QExpr :=
  if d then fourPoly f else .constant 0

theorem selected_four_sound (d : Bool) (f : Form) (x : State) :
    evalQ (selectedFour d f) x % 8 =
      (4 * bit d * bit (formVal f x)) % 8 := by
  cases d with
  | false => simp [selectedFour, evalQ, bit]
  | true => simpa [selectedFour, bit] using four_poly_sound f x

def localQuad (g : Gate) (f : Frame) (d : State) : QExpr :=
  match g with
  | .z a => singleQuad 4 (f a) (d a)
  | .s a => singleQuad 2 (f a) (d a)
  | .t a => singleQuad 1 (f a) (d a)
  | .cz a b =>
      .add (selectedFour (d a) (f b))
        (.add (selectedFour (d b) (f a)) (.constant (4 * bit (d a) * bit (d b))))
  | _ => .constant 0

theorem local_quad_sound (g : Gate) (f : Frame) (d x : State) :
    evalQ (localQuad g f d) x % 8 =
      localDelta g (evalFrame f x) d % 8 := by
  cases g with
  | flip a => rfl
  | cnot a b => rfl
  | z a =>
      exact single_quad_sound 4 (f a) (d a) x (Or.inr (Or.inr rfl))
  | s a =>
      exact single_quad_sound 2 (f a) (d a) x (Or.inr (Or.inl rfl))
  | t a =>
      exact single_quad_sound 1 (f a) (d a) x (Or.inl rfl)
  | cz a b =>
      have ha := selected_four_sound (d a) (f b) x
      have hb := selected_four_sound (d b) (f a) x
      cases hda : d a <;> cases hdb : d b <;>
        simp [hda, hdb, bit] at ha hb <;>
        simp [localQuad, localDelta, evalQ, evalFrame, hda, hdb, bit] <;> omega

def traceQuad : List Gate → Frame → State → QExpr
  | [], _, _ => .constant 0
  | g :: gs, f, d =>
      .add (localQuad g f d) (traceQuad gs (advanceFrame g f) (advanceDelta g d))

theorem trace_quad_sound (gs : List Gate) (f : Frame) (d x : State) :
    evalQ (traceQuad gs f d) x % 8 = tracePhase gs (evalFrame f x) d % 8 := by
  induction gs generalizing f d with
  | nil => rfl
  | cons g gs ih =>
      have hl := local_quad_sound g f d x
      have ht := ih (advanceFrame g f) (advanceDelta g d)
      rw [advance_frame_eval] at ht
      simp only [traceQuad, evalQ, tracePhase]
      omega

/-- Existence of a degree <= 2 Boolean polynomial modulo 8 for the
    concrete derivative of every finite gate sequence in this grammar.
    This proves the degree premise, not yet interpolation soundness. -/
theorem phase_derivative_degree_bound (gs : List Gate) (d : State) :
    ∃ q : QExpr, ∀ x : State,
      (evalPhase gs (shifted x d) - evalPhase gs x) % 8 = evalQ q x % 8 := by
  refine ⟨traceQuad gs identityFrame d, ?_⟩
  intro x
  rw [replay_phase_shift]
  have h := trace_quad_sound gs identityFrame d x
  rw [identity_frame_eval] at h
  exact h.symm

#print axioms bx_assoc
#print axioms form_append
#print axioms four_poly_sound
#print axioms cross_four_eval
#print axioms two_poly_sound
#print axioms identity_frame_eval
#print axioms advance_frame_eval
#print axioms single_quad_sound
#print axioms selected_four_sound
#print axioms local_quad_sound
#print axioms trace_quad_sound
#print axioms phase_derivative_degree_bound

end QuPRS.SectorTransport
