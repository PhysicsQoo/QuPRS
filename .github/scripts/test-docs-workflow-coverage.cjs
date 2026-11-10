'use strict';

// Docs-only checks own sources that do not require a native Rustdoc build.
// When inputs affect the generated Python/Rust reference, the Rust API lane
// owns the site render and all original documentation source checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');

function eventPaths(source, event) {
  const segment = source.split(`\n  ${event}:\n`)[1];
  assert.ok(segment, `Missing ${event} event`);
  const events = segment.split(/\n  [a-z][a-z_-]*:\n/)[0];
  const lines = events.split('\n');
  let started = false;
  const paths = [];
  for (const line of lines) {
    if (!started) {
      if (line === '    paths:') started = true;
      continue;
    }
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const match = /^      - '([^']+)'$/.exec(line);
    if (match) {
      assert.ok(!match[1].startsWith('!'), 'Unsupported exclusion path');
      paths.push(match[1]);
    } else {
      assert.ok(!line.startsWith('    '), `Unsupported paths syntax: ${line}`);
      break;
    }
  }
  assert.ok(started && paths.length, `Missing ${event} path filters`);
  return paths;
}

const docs = fs.readFileSync('.github/workflows/docs-check.yml', 'utf8');
const rust = fs.readFileSync('.github/workflows/rust-api-docs.yml', 'utf8');

const shared = [
  'mkdocs.yml', 'docs/requirements-site.txt', 'docs/site/**',
  'scripts/check_docs_site.py', 'scripts/check_docs_gate_stubs.py',
  'scripts/generate_stubs.py', 'src/QuPRS/py.typed',
  'src/QuPRS/pathsum/core.py', 'src/QuPRS/pathsum/core.pyi',
  'src/QuPRS/pathsum/statistics.py', 'src/QuPRS/pathsum/__init__.py',
  'src/QuPRS/pathsum/gates/**'
];
const local = [
  'scripts/check_generated_stub.py', 'test/test_generated_stub_parity.py',
  'scripts/check_docs_examples.py', 'scripts/check_docs_scoped_contract.py',
  'src/QuPRS/utils/solver_adapter.py', 'src/QuPRS/utils/wmc_problem.py',
  '.github/workflows/docs-check.yml',
  '.github/scripts/test-docs-workflow-coverage.cjs'
];
for (const event of ['pull_request', 'push']) {
  const fastPaths = eventPaths(docs, event);
  const nativePaths = eventPaths(rust, event);
  assert.deepEqual([...fastPaths].sort(), [...local].sort(),
    `Unexpected fast documentation trigger for ${event}`);
  for (const path of shared) {
    assert.ok(nativePaths.includes(path),
      `Rust API workflow lost ${event} coverage for ${path}`);
    assert.ok(!fastPaths.includes(path),
      `Duplicate docs workflow triggers on ${event}: ${path}`);
  }
  assert.ok(docs.includes('branches: [dev]'), 'Fast docs must target dev');
  assert.ok(rust.includes('branches: [dev]'), 'Rust API docs must target dev');
}
for (const statement of [
  'python scripts/check_docs_site.py --sources',
  'python scripts/generate_stubs.py --check',
  "python -m unittest discover -s test -p 'test_generated_stub_parity.py'",
  'python -m py_compile scripts/generate_stubs.py scripts/check_generated_stub.py scripts/release_artifact_smoke.py',
  'python scripts/check_docs_examples.py --check',
  'python scripts/check_docs_scoped_contract.py',
  'python scripts/check_docs_site.py --negative-link-test',
  'python scripts/check_docs_gate_stubs.py --check',
  'zensical build --strict --clean',
  'python scripts/check_docs_site.py --site',
  'python scripts/check_docs_gate_stubs.py --site',
  'python scripts/check_docs_science.py',
  'python scripts/check_docs_links.py --site site',
  'python scripts/check_docs_visual.py --site site'
]) {
  assert.ok(rust.includes(statement), `Rust API docs lost gate: ${statement}`);
}
for(const statement of [
  'python scripts/check_docs_site.py --sources',
  'python scripts/generate_stubs.py --check',
  'python scripts/check_docs_examples.py --check',
  'python scripts/check_docs_scoped_contract.py',
  'zensical build --strict --clean',
  'python scripts/check_docs_site.py --site',
  'python scripts/check_docs_gate_stubs.py --site',
  'python scripts/check_docs_site.py --negative-link-test'
]){
  assert.ok(docs.includes(statement), `Fast docs lost fallback gate: ${statement}`);
}
// A site-only PR can reuse the exact base Rustdoc without provisioning
// native dependencies. Every native build/test step must respect that gate.
function stepBlock(workflow, name) {
  const marker = `      - name: ${name}\n`;
  const begin = workflow.indexOf(marker);
  assert.notEqual(begin, -1, `Missing native step: ${name}`);
  const end = workflow.indexOf('\n      - name: ', begin + marker.length);
  return workflow.slice(begin, end === -1 ? undefined : end);
}
for (const nativeStep of [
  'Set up Rust', 'Cache Rust build outputs', 'Install native build dependencies',
  'Restore pinned Ganak archive when available', 'Build Rust library reference',
  'Run Rust documentation tests', 'Check solver-free Rust library build'
]) {
  assert.ok(stepBlock(rust, nativeStep).includes(
    "if: steps.reuse-rustdoc.outputs.used != 'true'"),
    `Native step must skip when verified Rustdoc is reused: ${nativeStep}`);
}
assert.ok(stepBlock(rust, 'Package complete Rust crate and test external GPMC/Ganak consumers')
  .includes("steps.reuse-rustdoc.outputs.used != 'true'"),
  'Native external-solver package tests must skip on identical-site reuse');
for (const requiredSiteGate of [
  'Build Python reference and documentation site',
  'Verify rendered dynamic Gate API members',
  'Verify public mathematical identities',
  'Verify Python reference',
  'Compose and validate both API references',
  'Audit all internal links against deployment URL prefix'
]) {
  assert.ok(!stepBlock(rust, requiredSiteGate).includes(
    "if: steps.reuse-rustdoc.outputs.used != 'true'"),
    `Site verification must run even when native Rustdoc is reused: ${requiredSiteGate}`);
}

assert.ok(!docs.includes('rendered_site.outputs'),
  'The fast docs job must not infer success from a separate workflow');
assert.ok(!docs.includes('actions/github-script'),
  'No cross-workflow API calls needed for fast docs');
console.log('Documentation workflow partition and scientific source gates PASS');
