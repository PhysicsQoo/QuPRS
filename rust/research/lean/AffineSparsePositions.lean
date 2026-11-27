/-
A canonical increasing list of set positions, independently computed
by scanning low digits of the numerical mask. Relate it to the actual
BitVec clear/lowBit operations, not merely to a set with equal cardinality.
-/
import AffineMachineWord
import Init.Data.List.Pairwise
set_option autoImplicit false
set_option warningAsError true
namespace QuPRS.AffineSparsePositions
open QuPRS.AffineMachineWord

def positions : Nat → Nat → List Nat
  | 0, _ => []
  | n+1, m =>
      let rest := (positions n (m/2)).map Nat.succ
      if m % 2 = 1 then 0 :: rest else rest

def scope {w : Nat} (m : BitVec w) : List Nat := positions w m.toNat

theorem positions_zero (w : Nat) : positions w 0 = [] := by
  induction w with
  | zero => rfl
  | succ n ih => simp [positions, ih]

theorem scope_zero (w : Nat) : scope (0#w) = [] :=
  positions_zero w

theorem scope_concat {w : Nat} (x : BitVec w) (b : Bool) :
    scope (x.concat b) =
      if b then 0 :: (scope x).map Nat.succ else (scope x).map Nat.succ := by
  unfold scope
  rw [BitVec.toNat_concat]
  cases b
  · change (if (x.toNat*2+0)%2=1 then
      0 :: (positions w ((x.toNat*2+0)/2)).map Nat.succ
      else (positions w ((x.toNat*2+0)/2)).map Nat.succ) =
      (positions w x.toNat).map Nat.succ
    have hq : (x.toNat*2+0)/2 = x.toNat := by omega
    have hr : ¬ (x.toNat*2+0)%2=1 := by omega
    rw [hq, if_neg hr]
  · change (if (x.toNat*2+1)%2=1 then
      0 :: (positions w ((x.toNat*2+1)/2)).map Nat.succ
      else (positions w ((x.toNat*2+1)/2)).map Nat.succ) =
      0 :: (positions w x.toNat).map Nat.succ
    have hq : (x.toNat*2+1)/2 = x.toNat := by omega
    have hr : (x.toNat*2+1)%2=1 := by omega
    rw [hq, if_pos hr]

theorem scope_count {w : Nat} (m : BitVec w) : (scope m).length = m.cpop.toNat := by
  refine BitVec.concat_induction (motive := fun _ x => (scope x).length = x.cpop.toNat) ?_ ?_ m
  · decide
  · intro n x b ih
    rw [scope_concat, BitVec.toNat_cpop_concat]
    cases b
    · change ((scope x).map Nat.succ).length = 0 + x.cpop.toNat
      rw [List.length_map, ih]
      omega
    · change (0 :: (scope x).map Nat.succ).length = 1 + x.cpop.toNat
      rw [List.length_cons, List.length_map, ih]
      omega

theorem scope_clear {w : Nat} (m : BitVec w) : scope (clear m) = (scope m).tail := by
  refine BitVec.concat_induction (motive := fun _ x => scope (clear x) = (scope x).tail) ?_ ?_ m
  · decide
  · intro n x b ih
    cases b
    · rw [clear_concat_false, scope_concat, scope_concat]
      change (scope (clear x)).map Nat.succ = ((scope x).map Nat.succ).tail
      rw [ih, List.map_tail]
    · rw [clear_concat_true, scope_concat, scope_concat]
      rfl

theorem map_take_one (xs : List Nat) :
    (xs.take 1).map Nat.succ = (xs.map Nat.succ).take 1 := by
  cases xs <;> rfl

theorem scope_low {w : Nat} (m : BitVec w) : scope (lowBit m) = (scope m).take 1 := by
  refine BitVec.concat_induction (motive := fun _ x => scope (lowBit x) = (scope x).take 1) ?_ ?_ m
  · decide
  · intro n x b ih
    cases b
    · rw [low_concat_false, scope_concat, scope_concat]
      change (scope (lowBit x)).map Nat.succ = ((scope x).map Nat.succ).take 1
      rw [ih, map_take_one]
    · rw [low_concat_true, scope_concat, scope_concat]
      change 0 :: (scope (0#n)).map Nat.succ = (0 :: (scope x).map Nat.succ).take 1
      rw [scope_zero]
      rfl

theorem scope_member {w : Nat} (m : BitVec w) :
    ∀ i : Nat, i ∈ scope m ↔ i < w ∧ m.getLsbD i = true := by
  refine BitVec.concat_induction (motive := fun n x =>
    ∀ i : Nat, i ∈ scope x ↔ i < n ∧ x.getLsbD i = true) ?_ ?_ m
  · intro i
    change i ∈ ([] : List Nat) ↔ i < 0 ∧ _
    constructor
    · intro h
      exact False.elim (List.not_mem_nil h)
    · intro h
      omega
  · intro n x b ih i
    rw [scope_concat]
    cases i with
    | zero =>
        rw [BitVec.getLsbD_concat_zero]
        have hn : 0 ∉ (scope x).map Nat.succ := by
          intro h
          rcases List.mem_map.mp h with ⟨j, _, hj⟩
          omega
        cases b
        · change 0 ∈ (scope x).map Nat.succ ↔ 0 < n+1 ∧ false = true
          constructor
          · intro h
            exact False.elim (hn h)
          · intro h
            exact False.elim (Bool.false_ne_true h.2)
        · change 0 ∈ 0 :: (scope x).map Nat.succ ↔ 0 < n+1 ∧ true = true
          exact ⟨fun _ => ⟨by omega, rfl⟩, fun _ => List.mem_cons.mpr (Or.inl rfl)⟩
    | succ j =>
        rw [BitVec.getLsbD_concat_succ]
        have hm : j+1 ∈ (scope x).map Nat.succ ↔ j ∈ scope x := by
          constructor
          · intro h
            rcases List.mem_map.mp h with ⟨k, hk, he⟩
            have he' : k = j := by omega
            exact he' ▸ hk
          · intro h
            exact List.mem_map_of_mem h
        have hbase : j+1 ∈ (scope x).map Nat.succ ↔ j+1 < n+1 ∧ x.getLsbD j = true := by
          rw [hm, ih j]
          exact ⟨fun h => ⟨by omega, h.2⟩, fun h => ⟨by omega, h.2⟩⟩
        cases b
        · exact hbase
        · change j+1 ∈ 0 :: (scope x).map Nat.succ ↔ j+1 < n+1 ∧ x.getLsbD j = true
          constructor
          · intro h
            rcases List.mem_cons.mp h with hz | ht
            · omega
            · exact hbase.mp ht
          · intro h
            exact List.mem_cons.mpr (Or.inr (hbase.mpr h))

theorem scope_increasing {w : Nat} (m : BitVec w) : (scope m).Pairwise (· < ·) := by
  refine BitVec.concat_induction (motive := fun _ x => (scope x).Pairwise (· < ·)) ?_ ?_ m
  · exact List.Pairwise.nil
  · intro n x b ih
    have hm := List.Pairwise.map Nat.succ (fun a b h => Nat.succ_lt_succ h) ih
    rw [scope_concat]
    cases b
    · exact hm
    · change (0 :: (scope x).map Nat.succ).Pairwise (· < ·)
      apply List.Pairwise.cons
      · intro y hy
        rcases List.mem_map.mp hy with ⟨j, _, hj⟩
        omega
      · exact hm

theorem scope_nodup {w : Nat} (m : BitVec w) : (scope m).Nodup :=
  List.nodup_iff_pairwise_ne.mpr ((scope_increasing m).imp (fun h => Nat.ne_of_lt h))

theorem scope_remaining (fuel : Nat) (m : Word) :
    scope (remaining fuel m) = (scope m).drop fuel := by
  induction fuel generalizing m with
  | zero => rfl
  | succ n ih =>
      change scope (remaining n (clear m)) = (scope m).drop (n+1)
      rw [ih, scope_clear]
      cases scope m <;> rfl

#print axioms positions_zero
#print axioms scope_zero
#print axioms scope_concat
#print axioms scope_count
#print axioms scope_clear
#print axioms map_take_one
#print axioms scope_low
#print axioms scope_member
#print axioms scope_increasing
#print axioms scope_nodup
#print axioms scope_remaining
end QuPRS.AffineSparsePositions
