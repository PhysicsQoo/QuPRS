/-
Exact coefficient algebra, using the accepted Cartesian pair semantics.
Laws hold over unbounded Int. No reassociation of checked Rust operations
is asserted. Associativity and ring instantiation are separate obligations.
-/
import AffineNegacyclic
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineCyclotomicAlgebra
open QuPRS.AffineNegacyclic
open QuPRS.AffineCyclotomicLift

local instance (priority := 2000) : DecidableEq Nat := Nat.decEq

def total {X : Type} (f : X → Int) : List X → Int
  | [] => 0
  | x :: xs => f x + total f xs

theorem total_congr {X : Type} (f g : X → Int) (xs : List X)
    (h : ∀ x, x ∈ xs → f x = g x) : total f xs = total g xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change f x + total f xs = g x + total g xs
      rw [h x (List.mem_cons.mpr (Or.inl rfl)),
        ih (fun y hy => h y (List.mem_cons.mpr (Or.inr hy)))]

theorem total_zero {X : Type} (xs : List X) :
    total (fun _ : X => 0) xs = 0 := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change 0 + total (fun _ : X => 0) xs = 0
      rw [ih]

theorem total_add {X : Type} (f g : X → Int) (xs : List X) :
    total (fun x => f x + g x) xs = total f xs + total g xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change (f x + g x) + total (fun y => f y + g y) xs =
        (f x + total f xs) + (g x + total g xs)
      rw [ih]
      omega

theorem total_append {X : Type} (f : X → Int) (xs ys : List X) :
    total f (xs ++ ys) = total f xs + total f ys := by
  induction xs with
  | nil => exact (Int.zero_add _).symm
  | cons x xs ih =>
      change f x + total f (xs ++ ys) = (f x + total f xs) + total f ys
      rw [ih, Int.add_assoc]

theorem total_map {X Y : Type} (f : Y → Int) (g : X → Y) (xs : List X) :
    total f (xs.map g) = total (fun x => f (g x)) xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change f (g x) + total f (xs.map g) = f (g x) + total (fun y => f (g y)) xs
      rw [ih]

theorem total_flatMap {X Y : Type} (f : Y → Int) (g : X → List Y) (xs : List X) :
    total f (xs.flatMap g) = total (fun x => total f (g x)) xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      change total f (g x ++ xs.flatMap g) =
        total f (g x) + total (fun y => total f (g y)) xs
      rw [total_append, ih]

theorem total_swap {X Y : Type} (f : X → Y → Int) (xs : List X) (ys : List Y) :
    total (fun x => total (f x) ys) xs =
      total (fun y => total (fun x => f x y) xs) ys := by
  induction xs with
  | nil => exact (total_zero ys).symm
  | cons x xs ih =>
      change total (f x) ys + total (fun z => total (f z) ys) xs =
        total (fun y => f x y + total (fun z => f z y) xs) ys
      rw [total_add, ih]

theorem pair_sum_total (d k : Nat) (ts : List PairTerm) :
    pairSum d k ts = total (fun t => exactTerm d k t.i t.j t.a t.b) ts := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      change exactTerm d k t.i t.j t.a t.b + pairSum d k ts =
        exactTerm d k t.i t.j t.a t.b + total (fun u => exactTerm d k u.i u.j u.a u.b) ts
      rw [ih]

def mul (d : Nat) (a b : Nat → Int) (k : Nat) : Int :=
  pairSum d k (pairs d a b)

def add (a b : Nat → Int) : Nat → Int := fun k => a k + b k

def one : Nat → Int := fun k => if k = 0 then 1 else 0

theorem mul_nested (d k : Nat) (a b : Nat → Int) :
    mul d a b k =
      total (fun i => total (fun j => coordinate d k (i+j) * (a i * b j))
        (List.range d)) (List.range d) := by
  unfold mul pairs
  rw [pair_sum_total, total_flatMap]
  apply total_congr
  intro i _
  exact total_map _ _ _

theorem mul_comm (d : Nat) (a b : Nat → Int) : mul d a b = mul d b a := by
  funext k
  rw [mul_nested, mul_nested, total_swap]
  apply total_congr
  intro j _
  apply total_congr
  intro i _
  rw [Nat.add_comm i j, Int.mul_comm (a i) (b j)]

theorem mul_add (d : Nat) (a b c : Nat → Int) :
    mul d a (add b c) = add (mul d a b) (mul d a c) := by
  funext k
  change mul d a (add b c) k = mul d a b k + mul d a c k
  rw [mul_nested, mul_nested, mul_nested, ← total_add]
  apply total_congr
  intro i _
  rw [← total_add]
  apply total_congr
  intro j _
  change coordinate d k (i+j) * (a i * (b j+c j)) =
    coordinate d k (i+j) * (a i*b j) + coordinate d k (i+j) * (a i*c j)
  rw [Int.mul_add, Int.mul_add]

theorem mul_zero (d : Nat) (a : Nat → Int) :
    mul d a (fun _ => 0) = fun _ => 0 := by
  funext k
  rw [mul_nested]
  calc
    _ = total (fun _ : Nat => 0) (List.range d) := by
      apply total_congr
      intro i _
      calc
        _ = total (fun _ : Nat => 0) (List.range d) := by
          apply total_congr
          intro j _
          rw [Int.mul_zero, Int.mul_zero]
        _ = 0 := total_zero _
    _ = 0 := total_zero _

/-- Delta-weighted sums count a unique selected index once. -/
theorem total_delta {X : Type} [DecidableEq X] (f : X → Int)
    (xs : List X) (k : X) (hn : xs.Nodup) :
    total (fun i => if i = k then f i else 0) xs =
      if k ∈ xs then f k else 0 := by
  induction xs with
  | nil => rfl
  | cons i xs ih =>
      have hnd := List.nodup_cons.mp hn
      change (if i = k then f i else 0) +
        total (fun j => if j = k then f j else 0) xs =
          if k ∈ i :: xs then f k else 0
      rw [ih hnd.2]
      by_cases he : i = k
      · subst k
        have hm : i ∈ i :: xs := List.mem_cons.mpr (Or.inl rfl)
        rw [ite_eq_left rfl, ite_eq_right hnd.1, ite_eq_left hm, Int.add_zero]
      · have hm : k ∈ i :: xs ↔ k ∈ xs := by
          constructor
          · intro h
            exact (List.mem_cons.mp h).resolve_left (fun h' => he h'.symm)
          · intro h
            exact List.mem_cons.mpr (Or.inr h)
        rw [ite_eq_right he, Int.zero_add]
        simp only [hm]

theorem mul_one_coordinate (d k : Nat) (hk : k < d) (a : Nat → Int) :
    mul d a one k = a k := by
  have hd : 0 < d := Nat.lt_of_le_of_lt (Nat.zero_le k) hk
  have hn := range_nodup_constructive d
  have hzero : (0 : Nat) ∈ List.range d := List.mem_range.mpr hd
  have hkMem : k ∈ List.range d := List.mem_range.mpr hk
  rw [mul_nested]
  calc
    _ = total (fun i => coordinate d k i * a i) (List.range d) := by
      apply total_congr
      intro i _
      calc
        _ = total (fun j => if j = 0 then coordinate d k i * a i else 0)
              (List.range d) := by
          apply total_congr
          intro j _
          by_cases hj : j = 0
          · subst j
            simp [one]
          · simp [one, hj]
        _ = coordinate d k i * a i := by
          rw [total_delta (fun _ : Nat => coordinate d k i * a i) _ 0 hn,
              ite_eq_left hzero]
    _ = total (fun i => if i = k then a i else 0) (List.range d) := by
      apply total_congr
      intro i hi
      have hib : i < d := List.mem_range.mp hi
      have h2 : i < 2*d := by omega
      have hnwrap : i ≠ k+d := by omega
      unfold coordinate
      rw [Nat.mod_eq_of_lt h2, ite_eq_right hnwrap]
      by_cases he : i = k
      · rw [ite_eq_left he, Int.one_mul]
      · rw [ite_eq_right he, Int.zero_mul]
    _ = a k := by
      rw [total_delta a _ k hn, ite_eq_left hkMem]

#print axioms total_congr
#print axioms total_zero
#print axioms total_add
#print axioms total_append
#print axioms total_map
#print axioms total_flatMap
#print axioms total_swap
#print axioms pair_sum_total
#print axioms mul_nested
#print axioms mul_comm
#print axioms mul_add
#print axioms mul_zero
#print axioms total_delta
#print axioms mul_one_coordinate
end QuPRS.AffineCyclotomicAlgebra
