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
  | nil => cases ha : atomVal a x <;> simp [crossFour, fourPoly, evalQ]
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
        simp [singleQuad, evalQ, singleDelta, bit] <;> omega

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
      change (evalQ (selectedFour (d a) (f b)) x +
        (evalQ (selectedFour (d b) (f a)) x + 4 * bit (d a) * bit (d b))) % 8 =
        (4 * (bit (d a) * bit (formVal (f b) x) +
          bit (d b) * bit (formVal (f a) x) + bit (d a) * bit (d b))) % 8
      cases hda : d a <;> cases hdb : d b <;>
        simp [hda, hdb, bit] at ha hb ⊢ <;> omega

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

/-! Finite canonical quadratic table interpolation.
    This theorem works for an explicitly bounded table of coefficients,
    independent of the method that produced it. Linking QExpr/traceQuad
    to this canonical table and its admitted wire bounds remains a
    separate proof obligation. No statistical sampling assumption. -/

def sumInt : Nat → (Nat → Int) → Int
  | 0, _ => 0
  | n+1, f => sumInt n f + f n

theorem sumInt_zero (n : Nat) (f : Nat → Int)
    (h : ∀ i, i < n → f i = 0) : sumInt n f = 0 := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have ht := ih (fun i hi => h i (by omega))
      have hn := h n (by omega)
      simp [sumInt, ht, hn]

theorem sumInt_single (n j : Nat) (v : Int) (hj : j < n) :
    sumInt n (fun i => if i = j then v else 0) = v := by
  induction n with
  | zero => omega
  | succ n ih =>
      by_cases he : j = n
      · subst j
        have hz : sumInt n (fun i => if i = n then v else 0) = 0 := by
          apply sumInt_zero
          intro i hi
          have hn : i ≠ n := by omega
          simp [hn]
        simp [sumInt, hz]
      · have ht := ih (by omega : j < n)
        have hn : n ≠ j := by omega
        simp [sumInt, ht, hn]

theorem sumInt_congr (n : Nat) (f g : Nat → Int)
    (h : ∀ i, i < n → f i = g i) : sumInt n f = sumInt n g := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [sumInt]
      rw [ih (fun i hi => h i (by omega)), h n (by omega)]

theorem sumInt_mod_zero (n : Nat) (f : Nat → Int)
    (h : ∀ i, i < n → f i % 8 = 0) : sumInt n f % 8 = 0 := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have ht := ih (fun i hi => h i (by omega))
      have hn := h n (by omega)
      simp only [sumInt]
      omega

def unitState (j : Nat) : State := fun i => decide (i = j)

def pairState (j k : Nat) : State :=
  fun i => decide (i = j ∨ i = k)

def rowEval (n : Nat) (q : Nat → Int) (x : State) : Int :=
  sumInt n (fun j => if x j then q j else 0)

theorem row_eval_zero (n : Nat) (q : Nat → Int) :
    rowEval n q (fun _ => false) = 0 := by
  apply sumInt_zero
  intro i _
  rfl

theorem row_eval_unit (n j : Nat) (q : Nat → Int) :
    rowEval n q (unitState j) = if j < n then q j else 0 := by
  by_cases hj : j < n
  · have h : rowEval n q (unitState j) =
        sumInt n (fun i => if i = j then q j else 0) := by
      apply sumInt_congr
      intro i _
      by_cases he : i = j
      · subst i
        simp [unitState]
      · simp [unitState, he]
    rw [h, sumInt_single n j (q j) hj]
    simp [hj]
  · have h : rowEval n q (unitState j) = 0 := by
      apply sumInt_zero
      intro i hi
      have he : i ≠ j := by omega
      simp [unitState, he]
    simp [h, hj]

def quadTable (c : Int) (l : Nat → Int) (q : Nat → Nat → Int) :
    Nat → State → Int
  | 0, _ => c
  | n+1, x =>
      quadTable c l q n x +
        (if x n then l n + rowEval n (q n) x else 0)

theorem quad_table_congr (c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n : Nat) (x y : State) (h : ∀ i, i < n → x i = y i) :
    quadTable c l q n x = quadTable c l q n y := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have hr : rowEval n (q n) x = rowEval n (q n) y := by
        apply sumInt_congr
        intro i hi
        rw [h i (by omega)]
      simp only [quadTable]
      rw [ih (fun i hi => h i (by omega)), h n (by omega), hr]

theorem quad_table_zero (c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n : Nat) : quadTable c l q n (fun _ => false) = c := by
  induction n with
  | zero => rfl
  | succ n ih => simp [quadTable, ih]

private theorem lt_select_true (a b : Nat) (u v : Int) (h : a < b) :
    (if a < b then u else v) = u := by
  split
  · rfl
  · contradiction

private theorem lt_select_false (a b : Nat) (u v : Int) (h : ¬ a < b) :
    (if a < b then u else v) = v := by
  split
  · contradiction
  · rfl

theorem quad_table_unit (c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n j : Nat) :
    quadTable c l q n (unitState j) = c + (if j < n then l j else 0) := by
  induction n with
  | zero =>
      rw [lt_select_false j 0 (l j) 0 (by omega)]
      simp [quadTable]
  | succ n ih =>
      by_cases he : j = n
      · subst j
        have hu : unitState n n = true := by simp [unitState]
        simp only [quadTable, ih, row_eval_unit, hu]
        rw [lt_select_false n n (l n) 0 (by omega),
            lt_select_false n n (q n n) 0 (by omega),
            lt_select_true n (n+1) (l n) 0 (by omega)] <;> simp
      · have hn : n ≠ j := by omega
        have hu : unitState j n = false := by simp [unitState, hn]
        simp only [quadTable, ih, hu]
        by_cases hj : j < n
        · rw [lt_select_true j n (l j) 0 hj,
              lt_select_true j (n+1) (l j) 0 (by omega)] <;> simp
        · rw [lt_select_false j n (l j) 0 hj,
              lt_select_false j (n+1) (l j) 0 (by omega)] <;> simp

theorem quad_table_pair (c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n j k : Nat) (hj : j < k) (hk : k < n) :
    quadTable c l q n (pairState j k) = c + l j + l k + q k j := by
  induction n with
  | zero => omega
  | succ n ih =>
      by_cases he : k = n
      · subst k
        have ht : quadTable c l q n (pairState j n) =
            quadTable c l q n (unitState j) := by
          apply quad_table_congr
          intro i hi
          have hn : i ≠ n := by omega
          simp [pairState, unitState, hn]
        have hr : rowEval n (q n) (pairState j n) =
            rowEval n (q n) (unitState j) := by
          apply sumInt_congr
          intro i hi
          have hn : i ≠ n := by omega
          simp [pairState, unitState, hn]
        have hp : pairState j n n = true := by simp [pairState]
        simp only [quadTable, hp]
        rw [ht, hr, quad_table_unit, row_eval_unit]
        rw [lt_select_true j n (l j) 0 hj,
            lt_select_true j n (q n j) 0 hj] <;> simp <;> omega
      · have hkn : k < n := by omega
        have hnj : n ≠ j := by omega
        have hnk : n ≠ k := by omega
        have hp : pairState j k n = false := by simp [pairState, hnj, hnk]
        simp only [quadTable, ih hkn, hp] <;> simp

theorem quad_table_mod_constant (c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n : Nat) (x : State)
    (hl : ∀ i, i < n → l i % 8 = 0)
    (hq : ∀ i j, i < n → j < i → q i j % 8 = 0) :
    quadTable c l q n x % 8 = c % 8 := by
  induction n with
  | zero => rfl
  | succ n ih =>
      have ht := ih (fun i hi => hl i (by omega))
        (fun i j hi hj => hq i j (by omega) hj)
      have hn := hl n (by omega)
      have hr : rowEval n (q n) x % 8 = 0 := by
        apply sumInt_mod_zero
        intro j hj
        have hh := hq n j (by omega) hj
        cases x j <;> simp [hh]
      simp only [quadTable]
      cases x n <;> simp <;> omega

/-- Exact interpolation: the zero, one-hot and two-hot sample values
    imply a universal constant modulo 8 for every bounded table.
    This conclusion is about all Boolean inputs, not just samples. -/
theorem quadratic_interpolation_sound (c : Int) (l : Nat → Int)
    (q : Nat → Nat → Int) (n : Nat) (v : Int)
    (h0 : quadTable c l q n (fun _ => false) % 8 = v % 8)
    (h1 : ∀ i, i < n → quadTable c l q n (unitState i) % 8 = v % 8)
    (h2 : ∀ i j, j < i → i < n →
      quadTable c l q n (pairState j i) % 8 = v % 8) :
    ∀ x : State, quadTable c l q n x % 8 = v % 8 := by
  rw [quad_table_zero] at h0
  have hl : ∀ i, i < n → l i % 8 = 0 := by
    intro i hi
    have h := h1 i hi
    rw [quad_table_unit] at h
    rw [lt_select_true i n (l i) 0 hi] at h
    omega
  have hq : ∀ i j, i < n → j < i → q i j % 8 = 0 := by
    intro i j hi hj
    have h := h2 i j hj hi
    rw [quad_table_pair c l q n j i hj hi] at h
    have ha := hl i hi
    have hb := hl j (by omega)
    omega
  intro x
  rw [quad_table_mod_constant c l q n x hl hq, h0]

#print axioms sumInt_zero
#print axioms sumInt_single
#print axioms sumInt_congr
#print axioms sumInt_mod_zero
#print axioms row_eval_zero
#print axioms row_eval_unit
#print axioms quad_table_congr
#print axioms quad_table_zero
#print axioms quad_table_unit
#print axioms quad_table_pair
#print axioms quad_table_mod_constant
#print axioms quadratic_interpolation_sound

/-! Bounded expression to canonical triangular coefficient table.
    All equalities here are exact Int equalities, not just mod 8.
    Wire admission is explicit; the next layer must establish it for
    traceQuad from the original gate list and finite frame.
    A zero scalar does not bypass syntactic wire admission. -/

def atomBound (n : Nat) : Atom → Prop
  | .one => True
  | .wire i => i < n

def qBound (n : Nat) : QExpr → Prop
  | .constant _ => True
  | .linear _ a => atomBound n a
  | .pair _ a b => atomBound n a ∧ atomBound n b
  | .add a b => qBound n a ∧ qBound n b
  | .scale _ a => qBound n a

theorem sumInt_add (n : Nat) (f g : Nat → Int) :
    sumInt n (fun i => f i + g i) = sumInt n f + sumInt n g := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [sumInt, ih]
      omega

theorem sumInt_scale (n : Nat) (k : Int) (f : Nat → Int) :
    sumInt n (fun i => k * f i) = k * sumInt n f := by
  induction n with
  | zero => simp [sumInt]
  | succ n ih => simp only [sumInt, ih, Int.mul_add]

theorem row_eval_add (n : Nat) (a b : Nat → Int) (x : State) :
    rowEval n (fun i => a i + b i) x = rowEval n a x + rowEval n b x := by
  unfold rowEval
  rw [← sumInt_add]
  apply sumInt_congr
  intro i _
  cases x i <;> simp

theorem row_eval_scale (n : Nat) (k : Int) (a : Nat → Int) (x : State) :
    rowEval n (fun i => k * a i) x = k * rowEval n a x := by
  unfold rowEval
  rw [← sumInt_scale]
  apply sumInt_congr
  intro i _
  cases x i <;> simp

theorem row_eval_const_zero (n : Nat) (x : State) :
    rowEval n (fun _ => 0) x = 0 := by
  apply sumInt_zero
  intro i _
  cases x i <;> rfl

theorem row_eval_select (n j : Nat) (k : Int) (x : State) (hj : j < n) :
    rowEval n (fun i => if i = j then k else 0) x =
      (if x j then k else 0) := by
  unfold rowEval
  calc
    sumInt n (fun i => if x i then (if i = j then k else 0) else 0) =
        sumInt n (fun i => if i = j then (if x j then k else 0) else 0) := by
          apply sumInt_congr
          intro i _
          by_cases he : i = j
          · subst i
            simp
          · simp [he]
    _ = _ := sumInt_single n j (if x j then k else 0) hj

theorem quad_table_add (c d : Int) (l m : Nat → Int) (q r : Nat → Nat → Int)
    (n : Nat) (x : State) :
    quadTable (c+d) (fun i => l i + m i) (fun i j => q i j + r i j) n x =
      quadTable c l q n x + quadTable d m r n x := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [quadTable, ih, row_eval_add]
      cases x n <;> simp <;> omega

theorem quad_table_scale (k c : Int) (l : Nat → Int) (q : Nat → Nat → Int)
    (n : Nat) (x : State) :
    quadTable (k*c) (fun i => k * l i) (fun i j => k * q i j) n x =
      k * quadTable c l q n x := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [quadTable, ih, row_eval_scale]
      cases x n <;> simp [Int.mul_add]

theorem quad_table_const (c : Int) (n : Nat) (x : State) :
    quadTable c (fun _ => 0) (fun _ _ => 0) n x = c := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [quadTable, ih, row_eval_const_zero]
      cases x n <;> simp

/-- One nonzero triangular row, with every other row zero. -/
theorem quad_table_single_row (n j : Nat) (k : Int) (r : Nat → Int) (x : State) :
    quadTable 0 (fun i => if i = j then k else 0)
      (fun i t => if i = j then r t else 0) n x =
    (if j < n then (if x j then k + rowEval j r x else 0) else 0) := by
  induction n with
  | zero =>
      rw [lt_select_false j 0 _ 0 (by omega)] <;> rfl
  | succ n ih =>
      by_cases he : n = j
      · subst j
        simp only [quadTable, ih]
        rw [lt_select_false n n _ 0 (by omega),
            lt_select_true n (n+1) _ 0 (by omega)] <;> simp
      · have hr : rowEval n (fun t => if n = j then r t else 0) x = 0 := by
          apply sumInt_zero
          intro i _
          simp [he]
        simp only [quadTable, ih, hr]
        have hz : (if n = j then k else 0) = 0 := by simp [he]
        rw [hz]
        by_cases hj : j < n
        · rw [lt_select_true j n _ 0 hj,
              lt_select_true j (n+1) _ 0 (by omega)]
          cases x n <;> simp
        · rw [lt_select_false j n _ 0 hj,
              lt_select_false j (n+1) _ 0 (by omega)]
          cases x n <;> simp

theorem quad_table_linear_basis (n j : Nat) (k : Int) (x : State) (hj : j < n) :
    quadTable 0 (fun i => if i = j then k else 0) (fun _ _ => 0) n x =
      k * bit (x j) := by
  have ht : quadTable 0 (fun i => if i = j then k else 0) (fun _ _ => 0) n x =
      quadTable 0 (fun i => if i = j then k else 0)
        (fun i t => if i = j then (0 : Int) else 0) n x := by
    have h : (fun (_ : Nat) (_ : Nat) => (0 : Int)) =
        (fun i (_ : Nat) => if i = j then (0 : Int) else 0) := by
      funext i t
      simp
    rw [← h]
  rw [ht, quad_table_single_row, lt_select_true j n _ 0 hj, row_eval_const_zero]
  cases x j <;> simp [bit]

theorem quad_table_pair_basis (n i j : Nat) (k : Int) (x : State)
    (hj : j < i) (hi : i < n) :
    quadTable 0 (fun _ => 0)
      (fun a b => if a = i then (if b = j then k else 0) else 0) n x =
      k * bit (x i) * bit (x j) := by
  have h : (fun (_ : Nat) => (0 : Int)) =
      (fun a => if a = i then (0 : Int) else 0) := by
    funext a
    simp
  rw [h, quad_table_single_row, lt_select_true i n _ 0 hi, row_eval_select i j k x hj]
  cases x i <;> cases x j <;> simp [bit]

/-- A bounded QExpr has a canonical triangular table with exact integer
    semantics on all states. No enumeration or choice of a table by an
    untrusted producer is assumed. -/
theorem qexpr_canonical_table (n : Nat) (p : QExpr) (h : qBound n p) :
    ∃ c : Int, ∃ l : Nat → Int, ∃ q : Nat → Nat → Int,
      ∀ x : State, evalQ p x = quadTable c l q n x := by
  induction p with
  | constant k =>
      exact ⟨k, fun _ => 0, fun _ _ => 0, fun x => (quad_table_const k n x).symm⟩
  | linear k a =>
      cases a with
      | one =>
          refine ⟨k, fun _ => 0, fun _ _ => 0, ?_⟩
          intro x
          rw [quad_table_const]
          simp [evalQ, atomVal, bit]
      | wire i =>
          refine ⟨0, fun j => if j = i then k else 0, fun _ _ => 0, ?_⟩
          intro x
          exact (quad_table_linear_basis n i k x h).symm
  | pair k a b =>
      have ha : atomBound n a := h.1
      have hb : atomBound n b := h.2
      cases a with
      | one =>
          cases b with
          | one =>
              refine ⟨k, fun _ => 0, fun _ _ => 0, ?_⟩
              intro x
              rw [quad_table_const]
              simp [evalQ, atomVal, bit]
          | wire j =>
              refine ⟨0, fun i => if i = j then k else 0, fun _ _ => 0, ?_⟩
              intro x
              rw [quad_table_linear_basis n j k x hb]
              change k * 1 * bit (x j) = k * bit (x j)
              rw [Int.mul_one]
      | wire i =>
          cases b with
          | one =>
              refine ⟨0, fun j => if j = i then k else 0, fun _ _ => 0, ?_⟩
              intro x
              rw [quad_table_linear_basis n i k x ha]
              change k * bit (x i) * 1 = k * bit (x i)
              rw [Int.mul_one]
          | wire j =>
              by_cases he : i = j
              · subst j
                refine ⟨0, fun j => if j = i then k else 0, fun _ _ => 0, ?_⟩
                intro x
                rw [quad_table_linear_basis n i k x ha]
                simp only [evalQ, atomVal]
                cases x i <;> simp [bit]
              · by_cases hj : j < i
                · refine ⟨0, fun _ => 0,
                    fun a b => if a = i then (if b = j then k else 0) else 0, ?_⟩
                  intro x
                  exact (quad_table_pair_basis n i j k x hj ha).symm
                · have hi : i < j := by omega
                  refine ⟨0, fun _ => 0,
                    fun a b => if a = j then (if b = i then k else 0) else 0, ?_⟩
                  intro x
                  rw [quad_table_pair_basis n j i k x hi hb]
                  simp only [evalQ, atomVal]
                  cases x i <;> cases x j <;> simp [bit]
  | add a b ihA ihB =>
      obtain ⟨c, l, q, hp⟩ := ihA h.1
      obtain ⟨d, m, r, hr⟩ := ihB h.2
      refine ⟨c+d, fun i => l i + m i, fun i j => q i j + r i j, ?_⟩
      intro x
      simp only [evalQ, hp x, hr x, quad_table_add]
  | scale k a ih =>
      obtain ⟨c, l, q, hp⟩ := ih h
      refine ⟨k*c, fun i => k * l i, fun i j => k * q i j, ?_⟩
      intro x
      simp only [evalQ, hp x, quad_table_scale]

theorem bounded_qexpr_interpolation (n : Nat) (p : QExpr) (h : qBound n p)
    (v : Int)
    (h0 : evalQ p (fun _ => false) % 8 = v % 8)
    (h1 : ∀ i, i < n → evalQ p (unitState i) % 8 = v % 8)
    (h2 : ∀ i j, j < i → i < n → evalQ p (pairState j i) % 8 = v % 8) :
    ∀ x : State, evalQ p x % 8 = v % 8 := by
  obtain ⟨c, l, q, he⟩ := qexpr_canonical_table n p h
  have h0' : quadTable c l q n (fun _ => false) % 8 = v % 8 := by
    rw [← he]
    exact h0
  have h1' : ∀ i, i < n → quadTable c l q n (unitState i) % 8 = v % 8 := by
    intro i hi
    rw [← he]
    exact h1 i hi
  have h2' : ∀ i j, j < i → i < n → quadTable c l q n (pairState j i) % 8 = v % 8 := by
    intro i j hj hi
    rw [← he]
    exact h2 i j hj hi
  intro x
  rw [he]
  exact quadratic_interpolation_sound c l q n v h0' h1' h2' x

#print axioms sumInt_add
#print axioms sumInt_scale
#print axioms row_eval_add
#print axioms row_eval_scale
#print axioms row_eval_const_zero
#print axioms row_eval_select
#print axioms quad_table_add
#print axioms quad_table_scale
#print axioms quad_table_const
#print axioms quad_table_single_row
#print axioms quad_table_linear_basis
#print axioms quad_table_pair_basis
#print axioms qexpr_canonical_table
#print axioms bounded_qexpr_interpolation

/-! Finite wire support and circuit-level phase interpolation.
    Only wire bounds are discharged here. Distinct-wire invertibility,
    the Hadamard sandwich amplitude bridge, and native checker refinement
    remain separate obligations. -/

def gateBound (n : Nat) : Gate → Prop
  | .flip a => a < n
  | .cnot a b => a < n ∧ b < n
  | .z a => a < n
  | .s a => a < n
  | .t a => a < n
  | .cz a b => a < n ∧ b < n

def formBound (n : Nat) : Form → Prop
  | [] => True
  | a :: rest => atomBound n a ∧ formBound n rest

def frameBound (n : Nat) (f : Frame) : Prop :=
  ∀ i, i < n → formBound n (f i)

def gatesBound (n : Nat) : List Gate → Prop
  | [] => True
  | g :: gs => gateBound n g ∧ gatesBound n gs

theorem form_bound_append (n : Nat) (a b : Form)
    (ha : formBound n a) (hb : formBound n b) :
    formBound n (a ++ b) := by
  induction a with
  | nil => exact hb
  | cons c a ih =>
      exact ⟨ha.1, ih ha.2⟩

theorem four_poly_bound (n : Nat) (f : Form) (h : formBound n f) :
    qBound n (fourPoly f) := by
  induction f with
  | nil => exact True.intro
  | cons a f ih => exact ⟨h.1, ih h.2⟩

theorem cross_four_bound (n : Nat) (a : Atom) (f : Form)
    (ha : atomBound n a) (hf : formBound n f) :
    qBound n (crossFour a f) := by
  induction f with
  | nil => exact True.intro
  | cons b f ih => exact ⟨⟨ha, hf.1⟩, ih hf.2⟩

theorem two_poly_bound (n : Nat) (f : Form) (h : formBound n f) :
    qBound n (twoPoly f) := by
  induction f with
  | nil => exact True.intro
  | cons a f ih =>
      exact ⟨h.1, ih h.2, cross_four_bound n a f h.1 h.2⟩

theorem identity_frame_bound (n : Nat) : frameBound n identityFrame := by
  intro i hi
  exact ⟨hi, True.intro⟩

theorem advance_frame_bound (n : Nat) (g : Gate) (f : Frame)
    (hg : gateBound n g) (hf : frameBound n f) :
    frameBound n (advanceFrame g f) := by
  intro i hi
  cases g with
  | flip a =>
      by_cases he : i = a
      · subst i
        have hh : formBound n (Atom.one :: f a) := ⟨True.intro, hf a hi⟩
        simpa [advanceFrame] using hh
      · simpa [advanceFrame, he] using hf i hi
  | cnot a b =>
      by_cases he : i = b
      · subst i
        have ha : a < n := hg.1
        simpa [advanceFrame] using form_bound_append n (f b) (f a) (hf b hi) (hf a ha)
      · simpa [advanceFrame, he] using hf i hi
  | z a => exact hf i hi
  | s a => exact hf i hi
  | t a => exact hf i hi
  | cz a b => exact hf i hi

theorem single_quad_bound (n : Nat) (k : Int) (f : Form) (d : Bool)
    (h : formBound n f) : qBound n (singleQuad k f d) := by
  cases d with
  | false => exact True.intro
  | true => exact ⟨True.intro, two_poly_bound n f h⟩

theorem selected_four_bound (n : Nat) (d : Bool) (f : Form)
    (h : formBound n f) : qBound n (selectedFour d f) := by
  cases d with
  | false => exact True.intro
  | true => exact four_poly_bound n f h

theorem local_quad_bound (n : Nat) (g : Gate) (f : Frame) (d : State)
    (hg : gateBound n g) (hf : frameBound n f) :
    qBound n (localQuad g f d) := by
  cases g with
  | flip a => exact True.intro
  | cnot a b => exact True.intro
  | z a => exact single_quad_bound n 4 (f a) (d a) (hf a hg)
  | s a => exact single_quad_bound n 2 (f a) (d a) (hf a hg)
  | t a => exact single_quad_bound n 1 (f a) (d a) (hf a hg)
  | cz a b =>
      exact ⟨selected_four_bound n (d a) (f b) (hf b hg.2),
        selected_four_bound n (d b) (f a) (hf a hg.1), True.intro⟩

theorem trace_quad_bound (n : Nat) (gs : List Gate) (f : Frame) (d : State)
    (hg : gatesBound n gs) (hf : frameBound n f) :
    qBound n (traceQuad gs f d) := by
  induction gs generalizing f d with
  | nil => exact True.intro
  | cons g gs ih =>
      exact ⟨local_quad_bound n g f d hg.1 hf,
        ih (advanceFrame g f) (advanceDelta g d) hg.2
          (advance_frame_bound n g f hg.1 hf)⟩

def phaseDiff (gs : List Gate) (d x : State) : Int :=
  (evalPhase gs (shifted x d) - evalPhase gs x) % 8

theorem phase_diff_quad (gs : List Gate) (d x : State) :
    phaseDiff gs d x = evalQ (traceQuad gs identityFrame d) x % 8 := by
  unfold phaseDiff
  rw [replay_phase_shift]
  have h := trace_quad_sound gs identityFrame d x
  rw [identity_frame_eval] at h
  exact h.symm

/-- Circuit-level interpolation: admitted finite wire indices ensure that
    the exact phase derivative has bounded quadratic support. The
    zero/one/two-hot sample premises are therefore sufficient for all
    inputs, independently of any producer's polynomial normalization. -/
theorem circuit_phase_interpolation (n : Nat) (gs : List Gate) (d : State)
    (v : Int) (hg : gatesBound n gs)
    (h0 : phaseDiff gs d (fun _ => false) = v % 8)
    (h1 : ∀ i, i < n → phaseDiff gs d (unitState i) = v % 8)
    (h2 : ∀ i j, j < i → i < n → phaseDiff gs d (pairState j i) = v % 8) :
    ∀ x : State, phaseDiff gs d x = v % 8 := by
  have hb := trace_quad_bound n gs identityFrame d hg (identity_frame_bound n)
  have h0' : evalQ (traceQuad gs identityFrame d) (fun _ => false) % 8 = v % 8 := by
    rw [← phase_diff_quad]
    exact h0
  have h1' : ∀ i, i < n →
      evalQ (traceQuad gs identityFrame d) (unitState i) % 8 = v % 8 := by
    intro i hi
    rw [← phase_diff_quad]
    exact h1 i hi
  have h2' : ∀ i j, j < i → i < n →
      evalQ (traceQuad gs identityFrame d) (pairState j i) % 8 = v % 8 := by
    intro i j hj hi
    rw [← phase_diff_quad]
    exact h2 i j hj hi
  intro x
  rw [phase_diff_quad]
  exact bounded_qexpr_interpolation n _ hb v h0' h1' h2' x

/-- Compose the actual sample condition with the admitted basis-action
    translation theorem. This is still a monomial basis-state result,
    not an amplitude, normalization, or complete Hoare theorem. -/
theorem sampled_constant_translation (n : Nat) (gs : List Gate)
    (s t : State) (b : Bool) (hg : gatesBound n gs)
    (ht : traceDelta gs s = t)
    (h0 : phaseDiff gs s (fun _ => false) = 4 * bit b)
    (h1 : ∀ i, i < n → phaseDiff gs s (unitState i) = 4 * bit b)
    (h2 : ∀ i j, j < i → i < n → phaseDiff gs s (pairState j i) = 4 * bit b) :
    ∀ x : State,
      evalState gs (shifted x s) = shifted (evalState gs x) t ∧
      phaseDiff gs s x = 4 * bit b := by
  have hv : (4 * bit b) % 8 = 4 * bit b := by
    cases b <;> decide
  have h0' : phaseDiff gs s (fun _ => false) = (4 * bit b) % 8 := by
    rw [hv]
    exact h0
  have h1' : ∀ i, i < n → phaseDiff gs s (unitState i) = (4 * bit b) % 8 := by
    intro i hi
    rw [hv]
    exact h1 i hi
  have h2' : ∀ i j, j < i → i < n →
      phaseDiff gs s (pairState j i) = (4 * bit b) % 8 := by
    intro i j hj hi
    rw [hv]
    exact h2 i j hj hi
  have h := circuit_phase_interpolation n gs s (4 * bit b) hg h0' h1' h2'
  intro x
  constructor
  · rw [replay_state_shift, ht]
  · rw [h x, hv]

#print axioms form_bound_append
#print axioms four_poly_bound
#print axioms cross_four_bound
#print axioms two_poly_bound
#print axioms identity_frame_bound
#print axioms advance_frame_bound
#print axioms single_quad_bound
#print axioms selected_four_bound
#print axioms local_quad_bound
#print axioms trace_quad_bound
#print axioms phase_diff_quad
#print axioms circuit_phase_interpolation
#print axioms sampled_constant_translation

/-! Finite Boolean-cube Fourier coefficient transport.
    Sum over the first n Boolean wires, with fixed tail. Coefficients
    are in the integer basis of Z[X]/(X^4+1). This is the unnormalized
    Hadamard-monomial-Hadamard coefficient formula, not yet a refinement
    of complex matrices, parser, or native implementation. -/

def setWire (x : State) (j : Nat) (b : Bool) : State :=
  fun i => if i = j then b else x i

theorem shift_set_wire (x s : State) (j : Nat) (b : Bool) :
    shifted (setWire x j b) s = setWire (shifted x s) j (bx b (s j)) := by
  funext i
  by_cases he : i = j
  · subst i
    simp [shifted, setWire]
  · simp [shifted, setWire, he]

def cubeSum : Nat → State → (State → Int) → Int
  | 0, x, f => f x
  | n+1, x, f =>
      cubeSum n (setWire x n false) f + cubeSum n (setWire x n true) f

theorem cube_sum_congr (n : Nat) (x : State) (f g : State → Int)
    (h : ∀ y, f y = g y) : cubeSum n x f = cubeSum n x g := by
  induction n generalizing x with
  | zero => exact h x
  | succ n ih =>
      simp only [cubeSum]
      rw [ih (setWire x n false), ih (setWire x n true)]

theorem cube_sum_scale (n : Nat) (x : State) (k : Int) (f : State → Int) :
    cubeSum n x (fun y => k * f y) = k * cubeSum n x f := by
  induction n generalizing x with
  | zero => rfl
  | succ n ih => simp only [cubeSum, ih, Int.mul_add]

theorem cube_sum_shift (n : Nat) (x s : State) (f : State → Int) :
    cubeSum n x (fun y => f (shifted y s)) =
      cubeSum n (shifted x s) f := by
  induction n generalizing x with
  | zero => rfl
  | succ n ih =>
      simp only [cubeSum, ih, shift_set_wire]
      cases s n <;> simp [bx, Int.add_comm]

theorem cube_sum_tail (n : Nat) (x y : State) (f : State → Int)
    (h : ∀ i, n ≤ i → x i = y i) : cubeSum n x f = cubeSum n y f := by
  induction n generalizing x y with
  | zero =>
      have he : x = y := funext (fun i => h i (Nat.zero_le i))
      rw [he]
  | succ n ih =>
      have ht (b : Bool) : ∀ i, n ≤ i →
          setWire x n b i = setWire y n b i := by
        intro i hi
        by_cases he : i = n
        · simp [setWire, he]
        · have hn : n+1 ≤ i := by omega
          simp [setWire, he, h i hn]
      simp only [cubeSum]
      rw [ih _ _ (ht false), ih _ _ (ht true)]

def zeroState : State := fun _ => false

def supported (n : Nat) (s : State) : Prop :=
  ∀ i, n ≤ i → s i = false

theorem cube_sum_xor_reindex (n : Nat) (s : State) (f : State → Int)
    (hs : supported n s) :
    cubeSum n zeroState (fun y => f (shifted y s)) = cubeSum n zeroState f := by
  rw [cube_sum_shift]
  apply cube_sum_tail
  intro i hi
  simp [shifted, zeroState, bx, hs i hi]

theorem dot_symmetric (n : Nat) (x y : State) :
    dot n x y = dot n y x := by
  induction n with
  | zero => rfl
  | succ n ih => simp only [dot, ih, Bool.and_comm]

theorem dot_shift_right (n : Nat) (x y s : State) :
    dot n x (shifted y s) = bx (dot n x y) (dot n x s) := by
  rw [dot_symmetric n x (shifted y s)]
  change dot n (maskXor y s) x = _
  rw [dot_xor, dot_symmetric n y x, dot_symmetric n s x]

/-- Coefficient j in the basis 1,X,X²,X³, X^4=-1. -/
def phaseCoeff (p : Int) (j : Nat) : Int :=
  if j < 4 then
    if p % 8 = (j : Int) then 1
    else if p % 8 = (j : Int) + 4 then -1 else 0
  else 0

/-- Constructive finite residue classification. Separate helpers make
    the axiom dependency of the arithmetic partition auditable. -/
private theorem residue_cases (p : Int) :
    p % 8 = 0 ∨ p % 8 = 1 ∨ p % 8 = 2 ∨ p % 8 = 3 ∨
    p % 8 = 4 ∨ p % 8 = 5 ∨ p % 8 = 6 ∨ p % 8 = 7 := by
  omega

private theorem coefficient_index_cases (j : Nat) (h : j < 4) :
    j = 0 ∨ j = 1 ∨ j = 2 ∨ j = 3 := by
  omega

theorem phase_coeff_shift (p q : Int) (j : Nat) (b : Bool)
    (h : (q-p) % 8 = 4 * bit b) :
    phaseCoeff q j = sgn b * phaseCoeff p j := by
  by_cases hj : j < 4
  · cases b with
    | false =>
        change (q-p) % 8 = 0 at h
        have hq : q % 8 = p % 8 := by omega
        unfold phaseCoeff
        rw [hq]
        change _ = 1 * _
        exact (Int.one_mul _).symm
    | true =>
        change (q-p) % 8 = 4 at h
        have hq : q % 8 = (p % 8 + 4) % 8 := by omega
        rcases coefficient_index_cases j hj with e | e | e | e <;> subst j <;>
          rcases residue_cases p with hp | hp | hp | hp | hp | hp | hp | hp <;>
          simp only [phaseCoeff, hq, hp] <;> decide
  · unfold phaseCoeff
    simp only [lt_select_false j 4 _ 0 hj, Int.mul_zero]

def fourierTerm (n : Nat) (gs : List Gate) (x z y : State) (j : Nat) : Int :=
  sgn (dot n x y) *
    (sgn (dot n z (evalState gs y)) * phaseCoeff (evalPhase gs y) j)

def fourierAmp (n : Nat) (gs : List Gate) (x z : State) (j : Nat) : Int :=
  cubeSum n zeroState (fun y => fourierTerm n gs x z y j)

theorem fourier_term_shift (n : Nat) (gs : List Gate)
    (x z s t : State) (b : Bool) (j : Nat)
    (ht : ∀ y, evalState gs (shifted y s) = shifted (evalState gs y) t)
    (hp : ∀ y, phaseDiff gs s y = 4 * bit b)
    (y : State) :
    fourierTerm n gs x z (shifted y s) j =
      (sgn (dot n x s) * sgn (dot n z t) * sgn b) *
        fourierTerm n gs x z y j := by
  have hc := phase_coeff_shift (evalPhase gs y)
    (evalPhase gs (shifted y s)) j b (hp y)
  simp only [fourierTerm, ht y, dot_shift_right, sign_mul, hc]
  ac_rfl

theorem fourier_amp_invariant (n : Nat) (gs : List Gate)
    (x z s t : State) (b : Bool) (j : Nat) (hs : supported n s)
    (ht : ∀ y, evalState gs (shifted y s) = shifted (evalState gs y) t)
    (hp : ∀ y, phaseDiff gs s y = 4 * bit b) :
    fourierAmp n gs x z j =
      (sgn (dot n x s) * sgn (dot n z t) * sgn b) * fourierAmp n gs x z j := by
  unfold fourierAmp
  have he : cubeSum n zeroState (fun y => fourierTerm n gs x z (shifted y s) j) =
      cubeSum n zeroState (fun y =>
        (sgn (dot n x s) * sgn (dot n z t) * sgn b) * fourierTerm n gs x z y j) := by
    apply cube_sum_congr
    exact fourier_term_shift n gs x z s t b j ht hp
  calc
    cubeSum n zeroState (fun y => fourierTerm n gs x z y j) =
        cubeSum n zeroState (fun y => fourierTerm n gs x z (shifted y s) j) :=
      (cube_sum_xor_reindex n s (fun y => fourierTerm n gs x z y j) hs).symm
    _ = _ := he
    _ = _ := cube_sum_scale n zeroState _ _

theorem invariant_entry_sign (a e b : Bool) (v : Int)
    (h : v = (sgn e * sgn a * sgn b) * v) :
    sgn a * v = sgn (bx e b) * v := by
  cases a <;> cases e <;> cases b <;> simp [sgn, bx] at h ⊢ <;> omega

/-- The entrywise premise of the terminal theorem follows from
    finite coefficient summation and a checked constant translation. -/
theorem fourier_entry_transport (n : Nat) (gs : List Gate)
    (s t : State) (b : Bool) (hs : supported n s)
    (ht : ∀ y, evalState gs (shifted y s) = shifted (evalState gs y) t)
    (hp : ∀ y, phaseDiff gs s y = 4 * bit b) :
    ∀ x z j, sgn (dot n z t) * fourierAmp n gs x z j =
      sgn (bx (dot n x s) b) * fourierAmp n gs x z j := by
  intro x z j
  exact invariant_entry_sign (dot n z t) (dot n x s) b
    (fourierAmp n gs x z j) (fourier_amp_invariant n gs x z s t b j hs ht hp)

theorem sampled_fourier_entry_transport (n : Nat) (gs : List Gate)
    (s t : State) (b : Bool) (hg : gatesBound n gs) (hs : supported n s)
    (ht : traceDelta gs s = t)
    (h0 : phaseDiff gs s zeroState = 4 * bit b)
    (h1 : ∀ i, i < n → phaseDiff gs s (unitState i) = 4 * bit b)
    (h2 : ∀ i j, j < i → i < n → phaseDiff gs s (pairState j i) = 4 * bit b) :
    ∀ x z j, sgn (dot n z t) * fourierAmp n gs x z j =
      sgn (bx (dot n x s) b) * fourierAmp n gs x z j := by
  have h := sampled_constant_translation n gs s t b hg ht h0 h1 h2
  exact fourier_entry_transport n gs s t b hs (fun y => (h y).1) (fun y => (h y).2)

#print axioms shift_set_wire
#print axioms cube_sum_congr
#print axioms cube_sum_scale
#print axioms cube_sum_shift
#print axioms cube_sum_tail
#print axioms cube_sum_xor_reindex
#print axioms dot_symmetric
#print axioms dot_shift_right
#print axioms phase_coeff_shift
#print axioms fourier_term_shift
#print axioms fourier_amp_invariant
#print axioms invariant_entry_sign
#print axioms fourier_entry_transport
#print axioms sampled_fourier_entry_transport

end QuPRS.SectorTransport
