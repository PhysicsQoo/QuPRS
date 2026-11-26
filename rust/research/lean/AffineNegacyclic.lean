/-
Exact integer negacyclic term semantics matching the native cyclo_mul
loop, conditional on bounded indices. No checked i128 refinement yet.
-/
import AffineCyclotomicLift
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineNegacyclic
open QuPRS.AffineCyclotomicLift

def nativeTerm (d k i j : Nat) (a b : Int) : Int :=
  if (i+j) % d = k then
    if i+j < d then a*b else -(a*b)
  else 0

def exactTerm (d k i j : Nat) (a b : Int) : Int :=
  coordinate d k (i+j) * (a*b)

/-- The one-wrap native loop agrees with the signed phase coordinate
    for every pair of in-range basis exponents and output coordinate. -/
theorem native_term_correct (d k i j : Nat) (a b : Int)
    (hi : i < d) (hj : j < d) (hk : k < d) :
    nativeTerm d k i j a b = exactTerm d k i j a b := by
  have h2 : i+j < 2*d := by omega
  unfold nativeTerm exactTerm coordinate
  rw [Nat.mod_eq_of_lt h2]
  by_cases h : i+j < d
  · have hn : i+j ≠ k+d := by omega
    rw [Nat.mod_eq_of_lt h, ite_eq_left h, ite_eq_right hn]
    by_cases he : i+j = k
    · simp only [ite_eq_left he, Int.one_mul]
    · simp only [ite_eq_right he, Int.zero_mul]
  · have hd : d ≤ i+j := by omega
    have hsub : i+j-d < d := by omega
    have hn : i+j ≠ k := by omega
    have he : i+j-d = k ↔ i+j = k+d := by omega
    rw [Nat.mod_eq_sub_mod hd, Nat.mod_eq_of_lt hsub, ite_eq_right h, ite_eq_right hn]
    simp only [he]
    by_cases heq : i+j = k+d
    · simp only [ite_eq_left heq, Int.neg_mul, Int.one_mul]
    · simp only [ite_eq_right heq, Int.zero_mul]

theorem term_lift (d k i j s : Nat) (a b : Int) (hs : 0 < s) :
    exactTerm (d*s) (k*s) (i*s) (j*s) a b =
      exactTerm d k i j a b := by
  unfold exactTerm
  rw [← Nat.add_mul, coordinate_lift d k (i+j) s hs]

theorem term_off_grid (d k i j s : Nat) (a b : Int) (hk : k % s ≠ 0) :
    exactTerm (d*s) k (i*s) (j*s) a b = 0 := by
  unfold exactTerm
  rw [← Nat.add_mul, coordinate_off_grid d k (i+j) s hk, Int.zero_mul]

/-- A list enumerates coefficient-pair contributions. Full Cartesian
    coverage, accumulator order and overflow are separate obligations. -/
structure PairTerm where
  i : Nat
  j : Nat
  a : Int
  b : Int

def scaled (s : Nat) (t : PairTerm) : PairTerm :=
  ⟨t.i*s, t.j*s, t.a, t.b⟩

def pairSum (d k : Nat) : List PairTerm → Int
  | [] => 0
  | t :: ts => exactTerm d k t.i t.j t.a t.b + pairSum d k ts

theorem pair_sum_lift (d k s : Nat) (hs : 0 < s) (ts : List PairTerm) :
    pairSum (d*s) (k*s) (ts.map (scaled s)) = pairSum d k ts := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      change exactTerm (d*s) (k*s) (t.i*s) (t.j*s) t.a t.b +
        pairSum (d*s) (k*s) (ts.map (scaled s)) =
        exactTerm d k t.i t.j t.a t.b + pairSum d k ts
      rw [term_lift d k t.i t.j s t.a t.b hs, ih]

theorem pair_sum_off_grid (d k s : Nat) (hk : k % s ≠ 0) (ts : List PairTerm) :
    pairSum (d*s) k (ts.map (scaled s)) = 0 := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      change exactTerm (d*s) k (t.i*s) (t.j*s) t.a t.b +
        pairSum (d*s) k (ts.map (scaled s)) = 0
      rw [term_off_grid d k t.i t.j s t.a t.b hk, ih, Int.zero_add]


/-- Row-major Cartesian enumeration of every coefficient pair. -/
def pairs (d : Nat) (a b : Nat → Int) : List PairTerm :=
  (List.range d).flatMap (fun i =>
    (List.range d).map (fun j => ⟨i, j, a i, b j⟩))

theorem pairs_membership (d : Nat) (a b : Nat → Int) (t : PairTerm) :
    t ∈ pairs d a b ↔
      ∃ i j, i < d ∧ j < d ∧ t = ⟨i, j, a i, b j⟩ := by
  unfold pairs
  constructor
  · intro ht
    obtain ⟨i, hi, hm⟩ := List.mem_flatMap.mp ht
    obtain ⟨j, hj, he⟩ := List.mem_map.mp hm
    exact ⟨i, j, List.mem_range.mp hi, List.mem_range.mp hj, he.symm⟩
  · rintro ⟨i, j, hi, hj, he⟩
    apply List.mem_flatMap.mpr
    exact ⟨i, List.mem_range.mpr hi, List.mem_map.mpr ⟨j, List.mem_range.mpr hj, he.symm⟩⟩

def nativeAcc (d k : Nat) (acc : Int) : List PairTerm → Int
  | [] => acc
  | t :: ts =>
      if t.a = 0 ∨ t.b = 0 then nativeAcc d k acc ts
      else nativeAcc d k (acc + nativeTerm d k t.i t.j t.a t.b) ts

theorem zero_pair_term (d k i j : Nat) (a b : Int)
    (h : a = 0 ∨ b = 0) : exactTerm d k i j a b = 0 := by
  rcases h with h | h
  · simp [exactTerm, h]
  · simp [exactTerm, h]

theorem native_acc_correct (d k : Nat) (hk : k < d)
    (ts : List PairTerm) (acc : Int)
    (h : ∀ t, t ∈ ts → t.i < d ∧ t.j < d) :
    nativeAcc d k acc ts = acc + pairSum d k ts := by
  induction ts generalizing acc with
  | nil => exact (Int.add_zero acc).symm
  | cons t ts ih =>
      have hb := h t (List.mem_cons.mpr (Or.inl rfl))
      have ht : ∀ u, u ∈ ts → u.i < d ∧ u.j < d :=
        fun u hu => h u (List.mem_cons.mpr (Or.inr hu))
      by_cases hz : t.a = 0 ∨ t.b = 0
      · simp only [nativeAcc, ite_eq_left hz, pairSum, zero_pair_term d k t.i t.j t.a t.b hz, Int.zero_add]
        exact ih acc ht
      · simp only [nativeAcc, ite_eq_right hz, pairSum]
        rw [ih _ ht, native_term_correct d k t.i t.j t.a t.b hb.1 hb.2 hk, Int.add_assoc]

theorem cartesian_acc_correct (d k : Nat) (hk : k < d)
    (a b : Nat → Int) :
    nativeAcc d k 0 (pairs d a b) = pairSum d k (pairs d a b) := by
  have h : ∀ t, t ∈ pairs d a b → t.i < d ∧ t.j < d := by
    intro t ht
    obtain ⟨i, j, hi, hj, he⟩ := (pairs_membership d a b t).mp ht
    rw [he]
    exact ⟨hi, hj⟩
  rw [native_acc_correct d k hk _ 0 h, Int.zero_add]


/-- An individual row has no repeated coefficient pairs. -/
theorem pair_row_nodup (i : Nat) (a b : Nat → Int) (js : List Nat)
    (h : js.Nodup) :
    (js.map (fun j => (⟨i, j, a i, b j⟩ : PairTerm))).Nodup := by
  induction js with
  | nil => simp
  | cons j js ih =>
      have hn := List.nodup_cons.mp h
      apply List.nodup_cons.mpr
      constructor
      · intro hm
        obtain ⟨k, hk, he⟩ := List.mem_map.mp hm
        have hj : k = j := congrArg PairTerm.j he
        exact hn.1 (hj ▸ hk)
      · exact ih hn.2

/-- Different outer indices have disjoint rows, even if coefficient
    values coincide. Indices, not values, determine multiplicity. -/
theorem pair_rows_nodup (a b : Nat → Int) (is js : List Nat)
    (hi : is.Nodup) (hj : js.Nodup) :
    (is.flatMap (fun i => js.map (fun j => (⟨i,j,a i,b j⟩ : PairTerm)))).Nodup := by
  induction is with
  | nil => simp
  | cons i is ih =>
      have hn := List.nodup_cons.mp hi
      change ((js.map (fun j => (⟨i,j,a i,b j⟩ : PairTerm))) ++
        is.flatMap (fun k => js.map (fun j => (⟨k,j,a k,b j⟩ : PairTerm)))).Nodup
      apply List.nodup_append.mpr
      refine ⟨pair_row_nodup i a b js hj, ih hn.2, ?_⟩
      intro x hx y hy he
      obtain ⟨j, _, hleft⟩ := List.mem_map.mp hx
      obtain ⟨k, hk, hm⟩ := List.mem_flatMap.mp hy
      obtain ⟨l, _, hright⟩ := List.mem_map.mp hm
      have heq : (⟨i,j,a i,b j⟩ : PairTerm) = ⟨k,l,a k,b l⟩ :=
        hleft.trans (he.trans hright.symm)
      have hik : i = k := congrArg PairTerm.i heq
      exact hn.1 (hik.symm ▸ hk)

theorem pairs_nodup (d : Nat) (a b : Nat → Int) :
    (pairs d a b).Nodup :=
  pair_rows_nodup a b (List.range d) (List.range d) List.nodup_range List.nodup_range

theorem pair_rows_length (a b : Nat → Int) (is js : List Nat) :
    (is.flatMap (fun i => js.map (fun j => (⟨i,j,a i,b j⟩ : PairTerm)))).length =
      is.length * js.length := by
  induction is with
  | nil => simp
  | cons i is ih =>
      change ((js.map (fun j => (⟨i,j,a i,b j⟩ : PairTerm))) ++
        is.flatMap (fun k => js.map (fun j => (⟨k,j,a k,b j⟩ : PairTerm)))).length =
          (is.length+1)*js.length
      rw [List.length_append, List.length_map, ih, Nat.add_mul, Nat.one_mul]
      exact Nat.add_comm _ _

theorem pairs_length (d : Nat) (a b : Nat → Int) :
    (pairs d a b).length = d*d := by
  unfold pairs
  rw [pair_rows_length, List.length_range]

#print axioms pair_row_nodup
#print axioms pair_rows_nodup
#print axioms pairs_nodup
#print axioms pair_rows_length
#print axioms pairs_length
#print axioms pairs_membership
#print axioms zero_pair_term
#print axioms native_acc_correct
#print axioms cartesian_acc_correct
#print axioms native_term_correct
#print axioms term_lift
#print axioms term_off_grid
#print axioms pair_sum_lift
#print axioms pair_sum_off_grid
end QuPRS.AffineNegacyclic
