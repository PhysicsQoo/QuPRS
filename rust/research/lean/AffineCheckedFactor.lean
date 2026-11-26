/-
Checked factor arithmetic reference model, using the same finite carrier
as the exact factor algebra. Left-to-right product, zero early stop and
two sequential checked additions match the experimental bucket loop's
operation order. Scope indexing and Rust implementation correspondence
remain separate obligations.
-/
import AffineCyclotomicAlgebra
import AffineCheckedCycloSchedule
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineCheckedFactor
open QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineCheckedCycloSchedule
open QuPRS.AffineFactorScope
open QuPRS.AffineFactorElimination

def finZero (d : Nat) : Coeff d := fun _ => 0

def isZero {d : Nat} (a : Coeff d) : Bool :=
  (List.finRange d).all (fun k => decide (a k = 0))

theorem is_zero_sound {d : Nat} (a : Coeff d) (h : isZero a = true) :
    a = finZero d := by
  funext k
  exact (List.all_eq_true.mp h) k (List.mem_finRange k)

theorem fin_mul_zero {d : Nat} (a : Coeff d) :
    finMul a (finZero d) = finZero d := by
  funext k
  change mul d (extend a) (extend (finZero d)) k.val = 0
  calc
    _ = mul d (extend a) (fun _ => 0) k.val :=
      mul_input_congr d k.val _ _ _ _ (fun _ _ => rfl)
        (fun i hi => extend_fin (finZero d) ⟨i,hi⟩)
    _ = 0 := congrFun (mul_zero d (extend a)) k.val

def checkedMul {d : Nat} (lo hi : Int) (a b : Coeff d) : Option (Coeff d) :=
  (checkedCyclo lo hi d (extend a) (extend b)).map (fun v k => v k.val)

theorem checked_mul_some {d : Nat} (lo hi : Int) (a b r : Coeff d)
    (h : checkedMul lo hi a b = some r) :
    r = finMul a b := by
  unfold checkedMul at h
  cases hc : checkedCyclo lo hi d (extend a) (extend b) with
  | none => simp [hc] at h
  | some v =>
      have he : (fun k : Fin d => v k.val) = r := by
        rw [hc] at h
        exact Option.some.inj h
      rw [← he]
      funext k
      exact checked_cyclo_some lo hi d (extend a) (extend b) v hc k.val k.isLt

def fits {d : Nat} (lo hi : Int) (a : Coeff d) : Bool :=
  (List.finRange d).all (fun k => decide (lo ≤ a k ∧ a k ≤ hi))

def checkedAdd {d : Nat} (lo hi : Int) (a b : Coeff d) : Option (Coeff d) :=
  if fits lo hi (finAdd a b) then some (finAdd a b) else none

theorem checked_add_some {d : Nat} (lo hi : Int) (a b r : Coeff d)
    (h : checkedAdd lo hi a b = some r) :
    r = finAdd a b := by
  unfold checkedAdd at h
  split at h
  · exact (Option.some.inj h).symm
  · contradiction

def exactProduct {d : Nat} : List (Coeff d) → Coeff d
  | [] => finOne d
  | v :: vs => finMul v (exactProduct vs)

def checkedProduct {d : Nat} (lo hi : Int) (acc : Coeff d) :
    List (Coeff d) → Option (Coeff d)
  | [] => some acc
  | v :: vs =>
      match checkedMul lo hi acc v with
      | none => none
      | some mid =>
          if isZero mid then some mid else checkedProduct lo hi mid vs

/-- A zero result can skip the remaining factors in exact arithmetic.
    Failure before reaching zero is not suppressed. -/
theorem checked_product_some {d : Nat} (lo hi : Int) (acc r : Coeff d)
    (vs : List (Coeff d)) (h : checkedProduct lo hi acc vs = some r) :
    r = finMul acc (exactProduct vs) := by
  induction vs generalizing acc with
  | nil =>
      exact (Option.some.inj h).symm.trans (fin_mul_unit acc).symm
  | cons v vs ih =>
      unfold checkedProduct at h
      cases hm : checkedMul lo hi acc v with
      | none => simp [hm] at h
      | some mid =>
          have he := checked_mul_some lo hi acc v mid hm
          rw [hm] at h
          split at h
          · rename_i hz
            have hmid : mid = finZero d := is_zero_sound mid hz
            have hr : r = mid := (Option.some.inj h).symm
            change r = finMul acc (finMul v (exactProduct vs))
            rw [← fin_mul_assoc, ← he, hr, hmid, fin_mul_comm (finZero d), fin_mul_zero]
          · have hr := ih mid h
            change r = finMul acc (finMul v (exactProduct vs))
            rw [← fin_mul_assoc, ← he]
            exact hr

theorem checked_product_from_one {d : Nat} (lo hi : Int) (r : Coeff d)
    (vs : List (Coeff d)) (h : checkedProduct lo hi (finOne d) vs = some r) :
    r = exactProduct vs := by
  rw [checked_product_some lo hi (finOne d) r vs h, fin_mul_comm (finOne d),
      fin_mul_unit]

theorem checked_product_head_reject {d : Nat} (lo hi : Int) (acc v : Coeff d)
    (vs : List (Coeff d)) (h : checkedMul lo hi acc v = none) :
    checkedProduct lo hi acc (v :: vs) = none := by
  simp only [checkedProduct, h]

def checkedBucket {d : Nat} (lo hi : Int) (fs ts : List (Coeff d)) :
    Option (Coeff d) := do
  let f ← checkedProduct lo hi (finOne d) fs
  let s ← checkedAdd lo hi (finZero d) f
  let t ← checkedProduct lo hi (finOne d) ts
  checkedAdd lo hi s t

theorem fin_add_zero_left {d : Nat} (a : Coeff d) :
    finAdd (finZero d) a = a := by
  funext k
  exact Int.zero_add (a k)

theorem checked_bucket_some {d : Nat} (lo hi : Int) (fs ts : List (Coeff d))
    (r : Coeff d) (h : checkedBucket lo hi fs ts = some r) :
    r = finAdd (exactProduct fs) (exactProduct ts) := by
  unfold checkedBucket at h
  cases hf : checkedProduct lo hi (finOne d) fs with
  | none => simp [hf] at h
  | some f =>
      cases hs : checkedAdd lo hi (finZero d) f with
      | none => simp [hf, hs] at h
      | some s =>
          cases ht : checkedProduct lo hi (finOne d) ts with
          | none => simp [hf, hs, ht] at h
          | some t =>
              have hh : checkedAdd lo hi s t = some r := by
                simpa [hf, hs, ht] using h
              rw [checked_add_some lo hi s t r hh,
                  checked_add_some lo hi (finZero d) f s hs,
                  fin_add_zero_left,
                  checked_product_from_one lo hi f fs hf,
                  checked_product_from_one lo hi t ts ht]

#print axioms is_zero_sound
#print axioms fin_mul_zero
#print axioms checked_mul_some
#print axioms checked_add_some
#print axioms checked_product_some
#print axioms checked_product_from_one
#print axioms checked_product_head_reject
#print axioms fin_add_zero_left
#print axioms checked_bucket_some
end QuPRS.AffineCheckedFactor
