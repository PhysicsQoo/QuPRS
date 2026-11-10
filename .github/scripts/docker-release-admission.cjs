'use strict';

// Docker image publication is intentionally stricter than test admission.
const STABLE_TAG = /^refs\/tags\/v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/;

function admit({ eventName, ref, runBuildPush }) {
  if (eventName === 'push' && STABLE_TAG.test(ref)) {
    return true;
  }
  // Manual publication requires both an explicit opt-in and the main branch.
  return eventName === 'workflow_dispatch' &&
    ref === 'refs/heads/main' && runBuildPush === 'true';
}

module.exports = { admit, STABLE_TAG };

if (require.main === module) {
  const allowed = admit({
    eventName: process.env.GITHUB_EVENT_NAME || '',
    ref: process.env.GITHUB_REF || '',
    runBuildPush: process.env.RUN_BUILD_PUSH || '',
  });
  process.stdout.write(`allowed=${allowed}\n`);
}
