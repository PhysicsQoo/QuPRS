/-
Finite executable certificate model for the affine output quotient.
Rows are lists of basis indices; coefficient columns are the original
finite ANF monomial incidences. Soundness is for arbitrary Boolean
monomial values, hence also for Boolean path assignments.
This is not yet refinement of Rust u64 masks or its resource/admission
checks, nor a proof of rank minimality.
-/
import AffineOutputQuotient

set_option autoImplicit false
set_option warningAsError true

namespace QuPRS.AffineOutputChecker
open QuPRS.AffineOutputQuotient

def checkAll {X : Type} (f : X → Bool) : List X → Bool
  | [] => true
  | x :: xs => f x && checkAll f xs

theorem check_all_sound {X : Type} (f : X → Bool) (xs : List X)
    (h : checkAll f xs = true) : ∀ x, x ∈ xs → f x = true := by
  induction xs with
  | nil => simp
  | cons a as ih =>
      have hh : f a = true ∧ checkAll f as = true := by
        simpa [checkAll] using h
      intro x hx
      rcases List.mem_cons.mp hx with he | ht
      · subst x
        exact hh.1
      · exact ih hh.2 x ht

theorem check_all_complete {X : Type} (f : X → Bool) (xs : List X)
    (h : ∀ x, x ∈ xs → f x = true) : checkAll f xs = true := by
  induction xs with
  | nil => rfl
  | cons a as ih =>
      have ha := h a (by simp)
      have ht := ih (fun x hx => h x (by simp [hx]))
      simp [checkAll, ha, ht]

theorem bx_assoc (a b c : Bool) : bx (bx a b) c = bx a (bx b c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem bx_exchange (a b c d : Bool) :
    bx (bx a b) (bx c d) = bx (bx a c) (bx b d) := by
  cases a <;> cases b <;> cases c <;> cases d <;> rfl

theorem parity_false {X : Type} (xs : List X) :
    parity (fun _ : X => false) xs = false := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simpa [parity, bx] using ih

theorem parity_xor {X : Type} (u v : X → Bool) (xs : List X) :
    parity (fun x => bx (u x) (v x)) xs = bx (parity u xs) (parity v xs) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change bx (bx (u x) (v x)) (parity (fun t => bx (u t) (v t)) xs) =
        bx (bx (u x) (parity u xs)) (bx (v x) (parity v xs))
      rw [ih, bx_exchange]

theorem parity_transpose {I M : Type} (a : I → M → Bool)
    (is : List I) (ms : List M) :
    parity (fun j => parity (a j) ms) is =
      parity (fun m => parity (fun j => a j m) is) ms := by
  induction is with
  | nil =>
      change false = parity (fun _ : M => false) ms
      exact (parity_false ms).symm
  | cons j js ih =>
      change bx (parity (a j) ms) (parity (fun k => parity (a k) ms) js) =
        parity (fun m => bx (a j m) (parity (fun k => a k m) js)) ms
      rw [parity_xor, ih]

def evalRow {J M : Type} (ms : List M) (coeff : M → J → Bool)
    (constant : J → Bool) (active : M → Bool) (i : J) : Bool :=
  bx (constant i) (parity (fun m => if active m then coeff m i else false) ms)

/-- Checking every coefficient column suffices for every valuation of
    the monomials, without enumerating the Boolean path assignments. -/
theorem column_reconstruction {I J M : Type} (ms : List M)
    (coeff : M → J → Bool) (constant : J → Bool)
    (rows : J → List I) (offset : J → Bool) (rep : I → J)
    (i : J) (active : M → Bool)
    (hc : constant i = bx (offset i) (parity (fun j => constant (rep j)) (rows i)))
    (hm : ∀ m, m ∈ ms → coeff m i = parity (fun j => coeff m (rep j)) (rows i)) :
    evalRow ms coeff constant active i =
      reconstruct rows offset (pick rep (evalRow ms coeff constant active)) i := by
  have hw : parity (fun m => if active m then coeff m i else false) ms =
      parity (fun m => parity (fun j => if active m then coeff m (rep j) else false) (rows i)) ms := by
    apply parity_congr
    intro m hmem
    cases ha : active m with
    | false => simp [ha, parity_false]
    | true => simpa [ha] using hm m hmem
  change bx (constant i) (parity (fun m => if active m then coeff m i else false) ms) =
    bx (offset i) (parity (fun j => bx (constant (rep j))
      (parity (fun m => if active m then coeff m (rep j) else false) ms)) (rows i))
  rw [hc, hw, parity_xor,
    parity_transpose (fun j m => if active m then coeff m (rep j) else false) (rows i) ms,
    bx_assoc]

def checkRepresentative {I J : Type} [DecidableEq I]
    (rows : J → List I) (offset : J → Bool) (rep : I → J) (j : I) : Bool :=
  decide (rows (rep j) = [j]) && decide (offset (rep j) = false)

def checkRow {I J M : Type} (ms : List M) (coeff : M → J → Bool)
    (constant : J → Bool) (rows : J → List I) (offset : J → Bool)
    (rep : I → J) (fixed : J → Bool) (i : J) : Bool :=
  (!fixed i || checkAll (fun j => fixed (rep j)) (rows i)) &&
    (decide (constant i = bx (offset i) (parity (fun j => constant (rep j)) (rows i))) &&
      checkAll (fun m => decide (coeff m i = parity (fun j => coeff m (rep j)) (rows i))) ms)

def checkTarget {I J : Type} (js : List J) (rows : J → List I)
    (offset : J → Bool) (rep : I → J) (fixed target : J → Bool) : Bool :=
  checkAll (fun i => !fixed i ||
    decide (reconstruct rows offset (pick rep target) i = target i)) js

theorem check_target_iff {I J : Type} (js : List J) (rows : J → List I)
    (offset : J → Bool) (rep : I → J) (fixed target : J → Bool)
    (hj : ∀ i, i ∈ js) :
    checkTarget js rows offset rep fixed target = true ↔
      agrees fixed target (reconstruct rows offset (pick rep target)) := by
  constructor
  · intro h i hi
    have hr := check_all_sound _ js h i (hj i)
    simpa [hi] using hr
  · intro h
    unfold checkTarget
    apply check_all_complete
    intro i _
    cases hi : fixed i with
    | false => simp [hi]
    | true => simp [hi, h i hi]

def checkCertificate {I J M : Type} [DecidableEq I]
    (is : List I) (js : List J) (ms : List M)
    (coeff : M → J → Bool) (constant : J → Bool) (rows : J → List I)
    (offset : J → Bool) (rep : I → J) (fixed target : J → Bool)
    (impossible : Bool) : Bool :=
  checkAll (checkRepresentative rows offset rep) is &&
    (checkAll (checkRow ms coeff constant rows offset rep fixed) js &&
      decide (impossible = !(checkTarget js rows offset rep fixed target)))

/-- The finite lists cover the abstract index domains. Shape and mask
    decoding are separate implementation refinement obligations. -/
theorem check_certificate_sound {I J M : Type} [DecidableEq I]
    (is : List I) (js : List J) (ms : List M)
    (coeff : M → J → Bool) (constant : J → Bool) (rows : J → List I)
    (offset : J → Bool) (rep : I → J) (fixed target : J → Bool)
    (impossible : Bool) (hi : ∀ j, j ∈ is) (hj : ∀ i, i ∈ js)
    (h : checkCertificate is js ms coeff constant rows offset rep fixed target impossible = true) :
    (∀ j, rows (rep j) = [j]) ∧
    (∀ j, offset (rep j) = false) ∧
    (∀ i, fixed i = true → ∀ j, j ∈ rows i → fixed (rep j) = true) ∧
    (∀ active, evalRow ms coeff constant active =
      reconstruct rows offset (pick rep (evalRow ms coeff constant active))) ∧
    (impossible = false ↔ agrees fixed target (reconstruct rows offset (pick rep target))) := by
  have hh : checkAll (checkRepresentative rows offset rep) is = true ∧
      checkAll (checkRow ms coeff constant rows offset rep fixed) js = true ∧
      impossible = !(checkTarget js rows offset rep fixed target) := by
    simpa [checkCertificate] using h
  have reps (j : I) : rows (rep j) = [j] ∧ offset (rep j) = false := by
    have hr := check_all_sound _ is hh.1 j (hi j)
    simpa [checkRepresentative] using hr
  have rowOK (i : J) :
      (!fixed i || checkAll (fun j => fixed (rep j)) (rows i)) = true ∧
      constant i = bx (offset i) (parity (fun j => constant (rep j)) (rows i)) ∧
      checkAll (fun m => decide (coeff m i = parity (fun j => coeff m (rep j)) (rows i))) ms = true := by
    have hr := check_all_sound _ js hh.2.1 i (hj i)
    simpa [checkRow] using hr
  refine ⟨fun j => (reps j).1, fun j => (reps j).2, ?_, ?_, ?_⟩
  · intro i hf j hm
    have hs : checkAll (fun j => fixed (rep j)) (rows i) = true := by
      simpa [hf] using (rowOK i).1
    exact check_all_sound _ (rows i) hs j hm
  · intro active
    funext i
    exact column_reconstruction ms coeff constant rows offset rep i active (rowOK i).2.1
      (fun m hm => of_decide_eq_true (check_all_sound _ ms (rowOK i).2.2 m hm))
  · rw [hh.2.2, ← check_target_iff js rows offset rep fixed target hj]
    cases checkTarget js rows offset rep fixed target <;> simp

#print axioms check_all_sound
#print axioms check_all_complete
#print axioms bx_assoc
#print axioms bx_exchange
#print axioms parity_false
#print axioms parity_xor
#print axioms parity_transpose
#print axioms column_reconstruction
#print axioms check_target_iff
#print axioms check_certificate_sound

end QuPRS.AffineOutputChecker
