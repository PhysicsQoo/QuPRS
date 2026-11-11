'use strict';

// An audit-only predicate. It is NOT called by a skip-gate. Artifacts must
// first be authenticated with GitHub run/job metadata before any future
// automation is allowed to use a positive comparison.
const platforms = ['ubuntu-latest', 'ubuntu-24.04-arm', 'macos-15-intel', 'macos-15'];
const py = ['3.11', '3.12', '3.13'];
const expectedSlots = py.flatMap(version => platforms.map(os => version + '|' + os));
const refuse = reason => ({certified:false, reason});
function decideNativeMatrixReuse(pr, merged) {
  if (!Array.isArray(pr) || !Array.isArray(merged)) return refuse('MISSING_MATRIX');
  if (pr.length !== 12 || merged.length !== 12) return refuse('INCOMPLETE_MATRIX');
  const a = new Map(), b = new Map();
  for (const [samples, index] of [[pr, a], [merged, b]]) {
    for (const r of samples) {
      if (!r || r.schema !== 1 || !r.complete || !expectedSlots.includes(r.slot))
        return refuse('INVALID_OR_UNATTESTED_SLOT');
      if (index.has(r.slot)) return refuse('DUPLICATE_SLOT');
      if (r.job_step_status !== 'success') return refuse('NON_SUCCESSFUL_STEP');
      const s=r.source || {}, e=r.environment || {};
      if (!/^[0-9a-f]{40}$/.test(s.tree || '') ||
          !/^[0-9a-f]{64}$/.test(s.contract_sha256 || '') ||
          !/^[0-9a-f]{64}$/.test(s.submodule_sha256 || '') ||
          s.command_contract !== 'native-12-python-4-rust-source-v2' ||
          !e.image_version || !e.image_os ||
          !e.runner_os || !e.runner_arch || !e.python ||
          !/^[0-9a-f]{64}$/.test(e.rustc_sha256 || '') ||
          !/^[0-9a-f]{64}$/.test(e.pip_sha256 || '') ||
          !e.native_libs?.gmp || !e.native_libs?.mpfr)
        return refuse('INCOMPLETE_FINGERPRINT');
      index.set(r.slot, r);
    }
  }
  for (const slot of expectedSlots) {
    if (!a.has(slot) || !b.has(slot)) return refuse('MISSING_SLOT');
    const x=a.get(slot), y=b.get(slot);
    if (JSON.stringify(x.source) !== JSON.stringify(y.source))
      return refuse('SOURCE_OR_SUBMODULE_DIFFERENCE:' + slot);
    if (JSON.stringify(x.environment) !== JSON.stringify(y.environment))
      return refuse('RUNNER_OR_DEPENDENCY_DRIFT:' + slot);
  }
  return {certified:true, reason:'SOURCE_AND_ENV_FINGERPRINT_MATCH_ONLY; TRUSTED_JOB_PROVENANCE_REQUIRED'};
}
module.exports={decideNativeMatrixReuse, expectedSlots};
