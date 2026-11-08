'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {isPerformanceBearingPath: isMeasured} = require('./codspeed-pr-impact.cjs');
const {VERSION_PATHS, canonicalVersion, isVersionOnlyChange} =
  require('./codspeed-metadata-only.cjs');

for (const path of [
  'src/QuPRS/interface/load_qiskit.py', 'rust/pathsum/src/ir.rs',
  'GPMC', '.gitmodules', 'pyproject.toml',
  'benchmarks/codspeed/test_pr_solver_walltime.py',
  'test/test_MQT.py', 'test/test_Feynman.py', 'test/conftest.py',
  'test/_benchmark_RR.py', 'test/test_benchmark_solvers.py',
  'scripts/check_codspeed_shards.py', 'scripts/paper_corpus_audit.py',
  '.github/workflows/codspeed.yml',
  '.github/scripts/codspeed-pr-impact.cjs',
  '.github/scripts/codspeed-metadata-only.cjs'
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


// Rustdoc-only source changes must not consume new CodSpeed measurements.
// The lexical check is deliberately conservative for uncertain/invalid input.
const {isRustDocOnlyChange} = require('./codspeed-pr-impact.cjs');
const rustOriginal = '/// Before\npub fn run() -> i32 { 2 }\n';
assert.equal(isRustDocOnlyChange(rustOriginal, '/// After\npub fn run() -> i32 { 2 }\n'), true);
assert.equal(isRustDocOnlyChange(rustOriginal, '//! Module\n'+rustOriginal), true);
assert.equal(isRustDocOnlyChange(rustOriginal, '/// After\npub fn run() -> i32 { 3 }\n'), false);
assert.equal(isRustDocOnlyChange(rustOriginal, '//// Ordinary comment\npub fn run() -> i32 { 2 }\n'), false);
assert.equal(isRustDocOnlyChange('pub fn a() {}\n', 'pub fn a() {}\n'), false);
assert.equal(isRustDocOnlyChange('pub fn a() {}\n', 'pub fn a() { }\n'), false);
assert.equal(isRustDocOnlyChange('const S: &str = r#"\n/// Before\n"#;\n',
  'const S: &str = r#"\n/// After\n"#;\n'), false, 'raw strings are data');
assert.equal(isRustDocOnlyChange('const S: &str = "start\n/// Before\nend";\n',
  'const S: &str = "start\n/// After\nend";\n'), false, 'multiline strings are data');
assert.equal(isRustDocOnlyChange('/* outer /* nested */\n/// Before\n*/\npub fn a() {}\n',
  '/* outer /* nested */\n/// After\n*/\npub fn a() {}\n'), false, 'block comments cannot masquerade as docs');
assert.equal(isRustDocOnlyChange("let c = '/';\n/// Before\nfn f() {}\n",
  "let c = '/';\n/// After\nfn f() {}\n"), true, 'char literal context');
assert.equal(isRustDocOnlyChange('/// Before\n#[derive(Debug)]\nstruct A;\n',
  '/// After\n#[derive(Debug)]\nstruct A;\n'), true, 'doctests remain a separate required gate');
assert.equal(isRustDocOnlyChange('pub fn a() {}\n', '/// New doc\npub fn a() {}\n'), true);
assert.equal(isRustDocOnlyChange('/// Old\npub fn a() {}\n', 'pub fn a() {}\n'), true);
assert.equal(isRustDocOnlyChange('/// Old\n/* unterminated', '/// New\n/* unterminated'), false);
assert.equal(isRustDocOnlyChange('/// Old\npub fn a() {}\n', '/// New\npub fn a() {}\n#[cfg(test)] mod extra {}'), false);
assert.equal(isRustDocOnlyChange('/// Old\npub fn a() {}\n', '/// New\npub fn a() {}\n'+'.'.repeat(150001)), false);

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

// The release-only classification must survive future workspace version bumps.
// Read actual checked-in files rather than fixing the current version in the test.
const actual = Object.fromEntries([...VERSION_PATHS].map(path =>
  [path, fs.readFileSync(path, 'utf8')]));
const currentVersion = canonicalVersion('rust/Cargo.toml', actual['rust/Cargo.toml'])?.version;
assert.ok(currentVersion, 'workspace version must parse');
const previousVersion = currentVersion === '0.13.4' ? '0.13.3' : '0.13.4';
const inconsistentVersion = currentVersion === '0.0.0' ? '0.0.1' : '0.0.0';
const previous = Object.fromEntries(Object.entries(actual).map(([path, value]) => {
  const canonical = canonicalVersion(path, value);
  assert.equal(canonical?.version, currentVersion,
    `checked-in metadata version mismatch: ${path}`);
  return [path, canonical.normalized.replaceAll('<release-version>', previousVersion)];
}));
const versions = [];
for (const path of VERSION_PATHS) {
  const verified = isVersionOnlyChange(path, previous[path], actual[path]);
  assert.deepEqual(verified, {before:previousVersion, after:currentVersion},
    `metadata-only version upgrade must be excluded: ${path}`);
  versions.push(verified);
  assert.equal(isVersionOnlyChange(path, actual[path], actual[path]), null);
  assert.equal(isVersionOnlyChange(path, previous[path], ''), null);
  assert.equal(isVersionOnlyChange(path, previous[path],
    actual[path] + '\n# unrelated change'), null);
}
assert.equal(versions.every(v => v.before === versions[0].before &&
                                 v.after === versions[0].after), true);
assert.equal(isVersionOnlyChange('rust/pathsum/src/solver_adapter.rs', '', ''), null);
assert.equal(isVersionOnlyChange('pyproject.toml', '', ''), null);

// Package metadata is safe; compiler/dependencies/features/third-party lock
// source changes are not, even when bundled alongside version updates.
const cargo = actual['rust/Cargo.toml'];
assert.equal(isVersionOnlyChange('rust/Cargo.toml', previous['rust/Cargo.toml'],
  cargo.replace('edition = "2021"', 'edition = "2024"')), null);
assert.equal(isVersionOnlyChange('rust/Cargo.toml', previous['rust/Cargo.toml'],
  cargo.replace('publish = false', 'publish = true')), null);
assert.equal(isVersionOnlyChange('rust/Cargo.toml', previous['rust/Cargo.toml'],
  cargo + '\n[features]\nexperimental = []\n'), null);
const lock = actual['rust/Cargo.lock'];
const foreign = lock.replace(
  /(^name = "adler2"\r?\nversion = ")[^"]+(")/m,
  (_, prefix, suffix) => prefix + '999.1.0' + suffix
);
assert.notEqual(foreign, lock, 'negative fixture must modify third-party dependency');
assert.equal(isVersionOnlyChange('rust/Cargo.lock', previous['rust/Cargo.lock'],
  foreign), null);
assert.equal(isVersionOnlyChange('rust/Cargo.lock', previous['rust/Cargo.lock'],
  lock.replace('name = "quprs"', 'name = "unknown-quprs"')), null);
assert.equal(isVersionOnlyChange('rust/Cargo.lock', previous['rust/Cargo.lock'],
  lock.replace('name = "quprs_python"', 'name = "quprs_python-other"')), null);
const inconsistent = lock.replace(
  /(^name = "QuPRS_cli"\r?\nversion = ")[^"]+(")/m,
  (_, prefix, suffix) => prefix + inconsistentVersion + suffix
);
assert.notEqual(inconsistent, lock);
assert.equal(isVersionOnlyChange('rust/Cargo.lock', previous['rust/Cargo.lock'],
  inconsistent), null);
assert.equal(isVersionOnlyChange('src/QuPRS/_version.py',
  previous['src/QuPRS/_version.py'],
  actual['src/QuPRS/_version.py']+'\nfrom os import environ'), null);
for (const path of [
  'src/QuPRS/interface/load_qiskit.py', 'rust/pathsum/build.rs', 'GPMC',
  '.github/workflows/codspeed.yml', 'benchmarks/codspeed/solver_case.py'
]) assert.equal(isMeasured(path), true, `source changes must measure: ${path}`);
assert.match(workflow, /isVersionOnlyChange/);
assert.match(workflow, /pull\.base\.sha/);
assert.match(workflow, /pull\.head\.sha/);
process.stdout.write('codspeed-pr-impact: strict metadata-only truth table passed\n');
