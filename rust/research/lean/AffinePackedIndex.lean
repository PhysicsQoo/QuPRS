/-
Natural-number little-endian index refinement for the explicit Boolean
row enumeration and checked materialized tables. Bounds are explicit:
the raw packed primitive would truncate high index bits.
The u64 low-bit loop and usize machine refinement are separate.
-/
import AffineCheckedOrder
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffinePackedIndex
open QuPRS.AffineCanonicalScope
open QuPRS.AffineFactorScope
open QuPRS.AffineFactorElimination
open QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineCheckedOrder

def bitValue : Bool → Nat
  | false => 0
  | true => 1

def encode : List Bool → Nat
  | [] => 0
  | b :: bs => bitValue b + 2 * encode bs

def decode : Nat → Nat → List Bool
  | 0, _ => []
  | n+1, i => decide (i % 2 = 1) :: decode n (i / 2)

theorem encode_bound (key : List Bool) : encode key < 2^key.length := by
  induction key with
  | nil => decide
  | cons b bs ih =>
      change bitValue b + 2 * encode bs < 2^(bs.length+1)
      rw [Nat.pow_succ]
      cases b <;> simp only [bitValue] <;> omega

theorem decode_length (n i : Nat) : (decode n i).length = n := by
  induction n generalizing i with
  | zero => rfl
  | succ n ih => simp [decode, ih]

theorem decode_encode (key : List Bool) : decode key.length (encode key) = key := by
  induction key with
  | nil => rfl
  | cons b bs ih =>
      have hq : (bitValue b + 2 * encode bs) / 2 = encode bs := by
        cases b <;> simp only [bitValue] <;> omega
      have hr : decide ((bitValue b + 2 * encode bs) % 2 = 1) = b := by
        cases b <;> simp [bitValue] <;> omega
      change decide ((bitValue b + 2 * encode bs) % 2 = 1) ::
        decode bs.length ((bitValue b + 2 * encode bs) / 2) = b :: bs
      rw [hq, hr, ih]

theorem encode_decode (n i : Nat) (h : i < 2^n) : encode (decode n i) = i := by
  induction n generalizing i with
  | zero =>
      change i < 1 at h
      change 0 = i
      omega
  | succ n ih =>
      have hq : i / 2 < 2^n := by
        rw [Nat.pow_succ] at h
        omega
      change bitValue (decide (i % 2 = 1)) + 2 * encode (decode n (i / 2)) = i
      rw [ih _ hq]
      by_cases hb : i % 2 = 1
      · simp [hb, bitValue] <;> omega
      · simp [hb, bitValue] <;> omega

theorem decode_mem_rows (n i : Nat) : decode n i ∈ rows n :=
  (mem_rows_iff n _).mpr (decode_length n i)

theorem expand_at_even (keys : List (List Bool)) (i : Nat) :
    (expand keys)[2*i]? = (keys[i]?).map (fun k => false :: k) := by
  induction keys generalizing i with
  | nil => simp [expand]
  | cons k ks ih =>
      cases i with
      | zero => rfl
      | succ i =>
          have he : 2*(i+1) = 2*i+1+1 := by omega
          rw [he]
          change ((false :: k) :: (true :: k) :: expand ks)[2*i+1+1]? =
            ((k :: ks)[i+1]?).map (fun t => false :: t)
          simp only [List.getElem?_cons_succ]
          exact ih i

theorem expand_at_odd (keys : List (List Bool)) (i : Nat) :
    (expand keys)[2*i+1]? = (keys[i]?).map (fun k => true :: k) := by
  induction keys generalizing i with
  | nil => simp [expand]
  | cons k ks ih =>
      cases i with
      | zero => rfl
      | succ i =>
          have he : 2*(i+1)+1 = (2*i+1)+1+1 := by omega
          rw [he]
          change ((false :: k) :: (true :: k) :: expand ks)[(2*i+1)+1+1]? =
            ((k :: ks)[i+1]?).map (fun t => true :: t)
          simp only [List.getElem?_cons_succ]
          exact ih i

theorem rows_at (n i : Nat) (h : i < 2^n) :
    (rows n)[i]? = some (decode n i) := by
  induction n generalizing i with
  | zero =>
      change i < 1 at h
      have hi : i = 0 := by omega
      subst i
      rfl
  | succ n ih =>
      have hq : i / 2 < 2^n := by
        rw [Nat.pow_succ] at h
        omega
      have ht := ih (i/2) hq
      by_cases hb : i % 2 = 1
      · have hi : i = 2*(i/2)+1 := by omega
        calc
          (rows (n+1))[i]? = (expand (rows n))[2*(i/2)+1]? :=
            congrArg (fun j => (expand (rows n))[j]?) hi
          _ = ((rows n)[i/2]?).map (fun k => true :: k) := expand_at_odd _ _
          _ = some (decode (n+1) i) := by simp [ht, decode, hb]
      · have hi : i = 2*(i/2) := by omega
        calc
          (rows (n+1))[i]? = (expand (rows n))[2*(i/2)]? :=
            congrArg (fun j => (expand (rows n))[j]?) hi
          _ = ((rows n)[i/2]?).map (fun k => false :: k) := expand_at_even _ _
          _ = some (decode (n+1) i) := by simp [ht, decode, hb]

theorem rows_at_encode (key : List Bool) :
    (rows key.length)[encode key]? = some key := by
  rw [rows_at _ _ (encode_bound key), decode_encode]

/-- The actual row stored at the natural numeric index, not association
    lookup or an exact oracle replacing the checked table. -/
theorem materialized_numeric_lookup {X : Type} [DecidableEq X] {d : Nat}
    (lo hi : Int) (x : X) (fs : List (ScopedFactor X (Coeff d)))
    (scope : List X) (table : List (List Bool × Coeff d)) (a : X → Bool)
    (hs : dependsOn scope (contractedFactor (cycloAlgebra d) x fs).eval)
    (h : materialize lo hi x fs scope (rows scope.length) = some table) :
    table[encode (extract a scope)]? =
      some (extract a scope, (contractedFactor (cycloAlgebra d) x fs).eval a) := by
  let key := extract a scope
  have hl : key.length = scope.length := by simp [key, extract]
  have hr : (rows scope.length)[encode key]? = some key := by
    rw [← hl]
    exact rows_at_encode key
  change table[encode key]? = some (key, (contractedFactor (cycloAlgebra d) x fs).eval a)
  rw [materialize_some lo hi x fs scope _ table h, List.getElem?_map, hr]
  change some (key, (contractedFactor (cycloAlgebra d) x fs).eval (deposit scope key)) = _
  rw [factor_scope_projection scope _ hs a]

#print axioms encode_bound
#print axioms decode_length
#print axioms decode_encode
#print axioms encode_decode
#print axioms decode_mem_rows
#print axioms expand_at_even
#print axioms expand_at_odd
#print axioms rows_at
#print axioms rows_at_encode
#print axioms materialized_numeric_lookup
end QuPRS.AffinePackedIndex
