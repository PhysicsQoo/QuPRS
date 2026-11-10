'use strict';

const assert = require('node:assert/strict');
const { admit } = require('./docker-release-admission.cjs');

const decide = (eventName, ref, runBuildPush = '') =>
  admit({ eventName, ref, runBuildPush });

for (const version of ['v0.15.0', 'v0.15.1', 'v1.0.0', 'v12.34.56']) {
  assert.equal(decide('push', `refs/tags/${version}`), true, version);
}

for (const version of [
  'v0.15.0-beta.1', 'v0.15.0-rc.1', 'v0.15.0b1',
  'v0.15.0rc1', 'v0.15.0+build', 'v0.15', 'v0.15.0.1',
  'v00.15.0', 'v0.015.0', 'v0.15.00', 'v0.15.0-dirty',
]) {
  assert.equal(decide('push', `refs/tags/${version}`), false, version);
}

assert.equal(decide('push', 'refs/heads/main'), false);
assert.equal(decide('push', 'refs/heads/dev'), false);
assert.equal(decide('pull_request', 'refs/pull/210/merge'), false);
assert.equal(decide('workflow_dispatch', 'refs/heads/main'), false);
assert.equal(decide('workflow_dispatch', 'refs/heads/main', 'false'), false);
assert.equal(decide('workflow_dispatch', 'refs/heads/dev', 'true'), false);
assert.equal(decide('workflow_dispatch', 'refs/heads/main', 'true'), true);
assert.equal(decide('workflow_dispatch', 'refs/tags/v0.15.0-beta.1', 'true'), false);
assert.equal(decide('workflow_dispatch', 'refs/tags/v0.15.0', 'true'), false);
console.log('Docker stable/prerelease publication policy: PASS');
