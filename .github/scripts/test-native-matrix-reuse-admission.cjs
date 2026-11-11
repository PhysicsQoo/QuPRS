'use strict';
const assert=require('node:assert/strict');
const {decideNativeMatrixReuse: decide,expectedSlots}=require('./native-matrix-reuse-admission.cjs');
const hex=(digit, n)=>digit.repeat(n);
function fixture() {
  return expectedSlots.map(slot=>({
    schema:1, slot, complete:true, job_step_status:'success',
    source:{tree:hex('a',40),submodule_sha256:hex('b',64),
      contract_sha256:hex('c',64),command_contract:'native-12-python-4-rust-source-v2'},
    environment:{image_os:'Ubuntu',image_version:'20261025.179',
      runner_os:'Linux',runner_arch:'X64',python:slot.slice(0,4)+'.0',
      rustc_sha256:hex('d',64),pip_sha256:hex('e',64),
      native_libs:{gmp:'6.3.0',mpfr:'4.2.1'}}
  }));
}
const p=fixture(),m=fixture();
assert.equal(decide(p,m).certified,true,'only complete exact environment may qualify for a future proof');
const mutate=(which,change)=>{const copy=structuredClone(which);change(copy);return copy;};
assert.equal(decide(p,mutate(m,q=>q[0].environment.image_version='20261101.186')).certified,false,'image drift blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].environment.pip_sha256=hex('f',64))).certified,false,'resolver drift blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].source.tree=hex('f',40))).certified,false,'different tree blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].source.submodule_sha256=hex('f',64))).certified,false,'submodule drift blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].source.contract_sha256=hex('f',64))).certified,false,'workflow definition drift blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].source.command_contract='native-12-pytest-rust-source-v1')).certified,false,'old all-Rust-slots contract cannot attest new run');
assert.equal(decide(p,mutate(m,q=>q[0].job_step_status='failure')).certified,false,'scientific test failure blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].complete=false)).certified,false,'unattested fingerprint blocks reuse');
assert.equal(decide(p,mutate(m,q=>q[0].environment.image_version='')).certified,false,'unknown runner image blocks reuse');
assert.equal(decide(p,m.slice(1)).certified,false,'partial matrix cannot qualify');
assert.equal(decide(p,mutate(m,q=>q[0].slot=q[1].slot)).certified,false,'duplicate slot blocks reuse');
assert.equal(decide(p,[]).certified,false);
process.stdout.write('native-matrix-reuse: 12-slot positive and 11 fail-closed contracts passed\n');
