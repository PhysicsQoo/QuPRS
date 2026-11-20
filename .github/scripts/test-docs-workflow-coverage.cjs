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
const website = fs.readFileSync('.github/workflows/website-ci.yml', 'utf8');

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
// The single PR admission routes local strict docs and native site reference
// validation. Native dev-push docs deployment still owns publication; do not
// rerun the fast strict docs workflow on the same protected dev commit.
const prPaths = eventPaths(website, 'pull_request');
const rustPushPaths = eventPaths(rust, 'push');
for (const path of local) {
  assert.ok(prPaths.includes(path), `Website PR lost strict documentation coverage: ${path}`);
}
assert.ok(website.includes('uses: ./.github/workflows/docs-check.yml'),
  'Website CI must route strict documentation checks');
assert.ok(!docs.includes('\n  pull_request:\n') &&
          !docs.includes('\n  push:\n'),
  'Reusable strict docs must not duplicate Website CI or protected dev push');
for (const path of shared) {
  assert.ok(prPaths.includes(path),
    `Website PR lost native reference coverage for ${path}`);
  assert.ok(rustPushPaths.includes(path),
    `Native dev docs publisher lost source coverage for ${path}`);
}
assert.ok(rust.includes('branches: [dev]'),
  'Rust API docs deployment must target protected dev');
assert.ok(docs.includes('on:\n  workflow_call:\n'), 'Strict docs must be reusable');
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
const consumerStep = stepBlock(rust, 'Package complete Rust crate and test external GPMC/Ganak consumers');
assert.ok(consumerStep.includes("steps.reuse-rustdoc.outputs.used != 'true'"),
  'Native external-solver package tests must skip on identical-site reuse');
for (const essential of [
  'quprs = { path = "%s", default-features = false }',
  'VerificationMethod::ReductionRules',
  'rr_only_needs_no_solver_executable',
  'QUPRS_SOLVER_PROVISION=external',
  'QUPRS_GPMC_PATH="$RUNNER_TEMP/nonexistent-gpmc"',
  'QUPRS_GANAK_PATH="$RUNNER_TEMP/nonexistent-ganak"',
  'cargo test --manifest-path "$RUNNER_TEMP/quprs-rr-consumer/Cargo.toml"'
]) {
  assert.ok(consumerStep.includes(essential),
    `Missing isolated RR-only consumer requirement: ${essential}`);
}
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
