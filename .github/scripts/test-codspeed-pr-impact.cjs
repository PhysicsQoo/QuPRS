'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {isPerformanceBearingPath: isMeasured} = require('./codspeed-pr-impact.cjs');

for (const path of [
  'src/QuPRS/interface/load_qiskit.py', 'rust/pathsum/src/ir.rs',
  'GPMC', '.gitmodules', 'pyproject.toml',
  'benchmarks/codspeed/test_pr_solver_walltime.py',
  'test/test_MQT.py', 'test/test_Feynman.py', 'test/conftest.py',
  'test/_benchmark_RR.py', 'test/test_benchmark_solvers.py',
  'scripts/check_codspeed_shards.py', 'scripts/paper_corpus_audit.py',
  '.github/workflows/codspeed.yml'
]) assert.equal(isMeasured(path), true, `must measure: ${path}`);

for (const path of [
  'docs/development/notes.md', 'README.md',
  '.github/workflows/qiskit-dual-major-api.yml',
  '.github/workflows/python-publish.yml',
  '.github/workflows/native-qasm3-contract.yml',
  '.github/scripts/test-ci-impact-reuse.cjs',
  '.github/scripts/test-codspeed-pr-impact.cjs',
  'scripts/test_release_ready_policy.js',
  'test/test_qiskit_library_constructor_compat.py'
]) assert.equal(isMeasured(path), false, `CI/docs-only must not measure: ${path}`);
assert.equal(isMeasured(undefined), false);

const workflow = fs.readFileSync('.github/workflows/codspeed.yml', 'utf8');
const prEvents = workflow.match(/^  pull_request:\n    types: \[([^\]]+)\]/m)?.[1] || '';
assert.match(prEvents, /opened/);
assert.match(prEvents, /synchronize/);
assert.match(prEvents, /edited/, 'existing explicit PR-body pilot trigger must remain');
assert.doesNotMatch(prEvents, /ready_for_review/, 'Ready transition must not rerun same source HEAD');
assert.match(workflow, /^  workflow_dispatch:/m, 'manual pilot dispatch must remain');
assert.match(workflow, /id: source_scope/);
assert.match(workflow, /if: \$\{\{ steps\.source_scope\.outputs\.run_source == 'true' \}\}/);
process.stdout.write('codspeed-pr-impact: source relevance / ready / manual pilot contracts passed\n');
