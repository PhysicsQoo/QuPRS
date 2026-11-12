'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const active=fs.readFileSync('.github/workflows/native-qasm3-contract.yml','utf8');
const optin=fs.readFileSync('.github/workflows/rust-qasm-source-guard.yml','utf8');
const manifest=active.split('  workflow_dispatch:')[0];
for(const path of [
  'rust/quprs/src/qasm.rs','rust/quprs/src/ir.rs',
  'rust/quprs/src/rational.rs','rust/quprs/src/gates.rs',
  'src/QuPRS/interface/load_qiskit.py',
  'test/test_qasm3_python_global_phase.py','test/test_rust_qasm3_subset.py',
  'test/test_rust_qasm_fail_closed.py','test/test_rust_p_phase_semantics.py',
  'test/test_graphstate16_qiskit_provenance.py'
])assert.ok(manifest.includes("- '"+path+"'"),'missing PR trigger: '+path);
for(const test of [
  'qasm::tests','gates::tests::test_apply_p',
  'gates::tests::test_p_u1_relative_phase_unit_contract',
  'test/test_rust_qasm3_subset.py','test/test_qasm3_python_global_phase.py',
  'test/test_rust_qasm_fail_closed.py','test/test_rust_p_phase_semantics.py',
  'test/test_graphstate16_qiskit_provenance.py'
])assert.ok(active.includes(test),'lost scientific test: '+test);
assert.equal((active.match(/maturin build --release/g)||[]).length,1,'build only one pinned source wheel');
assert.equal((active.match(/actions\/download-artifact@v4/g)||[]).length,1,'reuse the built wheel');
const guardEvents=optin.split(/^permissions:/m)[0];
assert.doesNotMatch(guardEvents,/^  pull_request:/m,'no duplicate recurring PR source guard');
assert.match(guardEvents,/^  workflow_dispatch:/m,'preserve independent manual guard');
assert.match(guardEvents,/^  push:/m,'preserve isolated research branch guard');
process.stdout.write('native-qasm-consolidation: one wheel, all science contracts, manual independence OK\n');
