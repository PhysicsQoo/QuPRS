/- Diagnostic only: inspect pinned library axioms, including deliberately
   untrusted alternatives. Do not use these reports as theorem acceptance. -/
import Init.Data.BitVec.Lemmas
set_option warningAsError true
#print axioms BitVec.not_concat
#print axioms BitVec.getElem_not
#print axioms BitVec.toNat_not
#print axioms BitVec.getLsbD_not
#print axioms BitVec.not_def
#print axioms BitVec.getLsbD_allOnes
#print axioms BitVec.getLsbD_xor
#print axioms BitVec.getLsbD_concat_zero
#print axioms BitVec.getLsbD_concat_succ
#print axioms BitVec.not_not
#print axioms BitVec.not_neg
#print axioms BitVec.toNat_sub_of_le
#print axioms BitVec.toNat_neg_of_pos
#print axioms BitVec.toNat_one
#print axioms BitVec.neg_zero
#print axioms BitVec.concat_extractLsb'_getLsb
#print axioms BitVec.xor_eq_zero_iff
#print axioms BitVec.concat_induction
#print axioms BitVec.toNat_cpop_concat
#print axioms BitVec.toNat_concat
