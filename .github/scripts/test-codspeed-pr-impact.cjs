'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {isPerformanceBearingPath: isMeasured} = require('./codspeed-pr-impact.cjs');
const {VERSION_PATHS, canonicalVersion, isVersionOnlyChange} =
  require('./codspeed-metadata-only.cjs');

for (const path of [
  'src/QuPRS/interface/load_qiskit.py', 'rust/quprs/src/ir.rs',
  'GPMC', '.gitmodules', 'pyproject.toml',
  'benchmarks/codspeed/test_pr_solver_walltime.py',
  'test/test_MQT.py', 'test/test_Feynman.py', 'test/conftest.py',
  'test/_benchmark_RR.py', 'test/test_benchmark_solvers.py',
  'scripts/check_codspeed_shards.py', 'scripts/paper_corpus_audit.py',
  '.github/workflows/codspeed.yml',
  '.github/scripts/codspeed-pr-impact.cjs',
  '.github/scripts/codspeed-metadata-only.cjs',
  '.github/scripts/ci-impact-reuse.cjs'
]) assert.equal(isMeasured(path), true, `must measure: ${path}`);

for (const path of [
  'docs/development/notes.md', 'README.md',
  'rust/quprs/README.md', 'rust/quprs/docs/reduction.md',
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
assert.equal(isRustDocOnlyChange(
  'const S = r'+'#'.repeat(40)+'"a " b\n/// Before\n"'+ '#'.repeat(40)+';\n',
  'const S = r'+'#'.repeat(40)+'"a " b\n/// After\n"'+ '#'.repeat(40)+';\n'),
  false, 'long-delimiter raw string with embedded quotes is data');
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
assert.doesNotMatch(prEvents, /edited/, 'editing PR metadata must not retrigger CodSpeed');
assert.doesNotMatch(prEvents, /ready_for_review/, 'Ready transition must not rerun same source HEAD');
assert.match(workflow, /^  workflow_dispatch:/m, 'manual pilot dispatch must remain');
// The workflow embeds JavaScript in YAML: compile the real source_scope step,
// not just the imported helper, to catch escaping corruption before CI admission.
const admission = workflow.match(/\n      - id: source_scope\n([\s\S]*?)\n      - id: resolve\n/);
assert.ok(admission, 'source_scope workflow step must exist');
const script = admission[1].split('          script: |\n')[1];
assert.ok(script, 'source_scope script body must exist');
const dedented = script.split('\n').map(line =>
  line.startsWith('            ') ? line.slice(12) : line).join('\n');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
assert.doesNotThrow(() => new AsyncFunction('context', 'github', 'core', 'Buffer', dedented),
  'GitHub Actions source_scope must remain syntactically valid');
assert.match(workflow, /assessPushSourceImpact/, 'push must use source-specific admission');
assert.match(workflow, /context\.eventName === 'push'/, 'push event gate must remain');
assert.match(workflow, /context\.eventName !== 'pull_request'/, 'manual dispatch must remain');
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
assert.equal(isVersionOnlyChange('rust/quprs/src/solver_adapter.rs', '', ''), null);
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
  'src/QuPRS/interface/load_qiskit.py', 'rust/quprs/build.rs', 'GPMC',
  '.github/workflows/codspeed.yml', 'benchmarks/codspeed/solver_case.py'
]) assert.equal(isMeasured(path), true, `source changes must measure: ${path}`);
assert.match(workflow, /isVersionOnlyChange/);
assert.match(workflow, /pull\.base\.sha/);
assert.match(workflow, /pull\.head\.sha/);
process.stdout.write('codspeed-pr-impact: strict metadata-only truth table passed\n');


// Exact-SHA push tests exercise the same helper called by the real workflow.
// Do not use abbreviated SHA or GitHub diff hunks as evidence.
const {assessPushSourceImpact} = require('./codspeed-pr-impact.cjs');
const shaBefore = 'a'.repeat(40), shaAfter = 'b'.repeat(40);
const docPath = 'rust/quprs/src/lib.rs';
const oldDoc = '/// Before\npub fn verify() -> bool { true }\n';
const newDoc = '/// After\npub fn verify() -> bool { true }\n';
function makePush(options = {}) {
  const {
    files = [{filename: docPath, status:'modified'}],
    source = {[docPath]:[oldDoc, newDoc]},
    before = shaBefore, after = shaAfter, contextSha = shaAfter,
    ref = 'refs/heads/dev', forced = false, created = false, deleted = false,
    status = 'ahead', behind = 0, total = 1, commits = [shaAfter],
    baseCommit = shaBefore, throwCompare = false, throwSource = false,
    repoName = 'PhysicsQoo/QuPRS',
    eventName = 'push'
  } = options;
  const context = {
    eventName, ref, sha:contextSha,
    repo: {owner:'PhysicsQoo', repo:'QuPRS'},
    payload: {ref, before, after, forced, created, deleted,
      repository:{full_name:repoName}}
  };
  const github = {rest: {repos:{
    async compareCommits(args) {
      assert.equal(args.base, before);
      assert.equal(args.head, after);
      assert.equal(args.per_page, 100);
      if (throwCompare) throw new Error('GitHub unavailable');
      return {data: {status,behind_by:behind,ahead_by:total,
        base_commit:{sha:baseCommit},total_commits:total,
        commits: commits.map(sha => ({sha})),files}};
    },
    async getContent({path,ref}) {
      if (throwSource) throw new Error('Source unavailable');
      assert.ok(source[path], 'unexpected file fetch: ' + path);
      const value = source[path][ref === before ? 0 : 1];
      return {data:{type:'file',encoding:'base64',size:Buffer.byteLength(value),
        content:Buffer.from(value).toString('base64')}};
    }
  }}};
  return assessPushSourceImpact({github,context});
}
async function pushContracts() {
  const skip = async (o, label) =>
    assert.equal((await makePush(o)).run, false, label);
  const run = async (o, label) =>
    assert.equal((await makePush(o)).run, true, label);
  await skip({}, 'single-file Rustdoc-only push');
  await skip({ref:'refs/heads/main'}, 'main push is protected');
  await skip({files:[{filename:'rust/quprs/README.md',status:'modified'}]},
    'Rust markdown is documentation');
  await skip({files:[{filename:'README.md',status:'modified'},
    {filename:docPath,status:'modified'}]}, 'mixed non-executable docs');
  await skip({files:[{filename:docPath,status:'modified'}],source:{
    [docPath]: ['pub fn verify() -> bool { true }\n',
                '/// API docs\npub fn verify() -> bool { true }\n']
  }}, 'new docs preceding unchanged function');
  await run({source:{[docPath]:[oldDoc,
    '/// After\npub fn verify() -> bool { false }\n']}}, 'real Rust implementation');
  await run({source:{[docPath]:[
    'const S: &str = r#"\n/// Before\n"#;\n',
    'const S: &str = r#"\n/// After\n"#;\n'
  ]}}, 'raw string contents not documentation');
  await run({files:[{filename:docPath,status:'modified'},
    {filename:'rust/quprs/Cargo.toml',status:'modified'}]},
    'mixed Rustdoc and Cargo feature changes must measure');
  await run({files:[{filename:'rust/quprs/src/lib.rs',status:'renamed',
    previous_filename:'rust/quprs/src/circuit.rs'}]}, 'renamed source');
  await run({files:[{filename:'GPMC',status:'modified'}]}, 'solver revision');
  await run({files:[{filename:'benchmarks/codspeed/foo.py',status:'added'}]}, 'benchmark added');
  await run({files:[{filename:'.github/workflows/codspeed.yml',status:'modified'}]}, 'workflow change');
  await run({files:[{filename:'.github/scripts/ci-impact-reuse.cjs',status:'modified'}]}, 'reuse configuration change');
  await run({files:[{filename:docPath,status:'modified'}],throwSource:true}, 'missing source is not a skip');
  await run({throwCompare:true}, 'compare API error');
  await run({before:'0'.repeat(40)}, 'initial push');
  await run({after:'0'.repeat(40)}, 'deleted push');
  await run({contextSha:'c'.repeat(40)}, 'head mismatch');
  await run({forced:true}, 'force push');
  await run({created:true}, 'new branch');
  await run({deleted:true}, 'branch deleted');
  await run({repoName:'other/repo'}, 'repository mismatch');
  await run({ref:'refs/heads/feature'}, 'non-maintained branch');
  await run({status:'diverged'}, 'non-fast-forward comparison');
  await run({behind:1}, 'behind base');
  await run({baseCommit:'c'.repeat(40)}, 'base mismatch');
  await run({total:101,commits:[shaAfter]}, 'comparison truncated commits');
  await run({total:2,commits:[shaAfter]}, 'missing commit in response');
  await run({commits:['c'.repeat(40)]}, 'wrong last commit');
  await run({files:Array.from({length:300},(_,i)=>
    ({filename:'docs/'+i+'.md',status:'modified'}))}, '300-file truncation');
  await run({files:[{filename:docPath,status:'mystery'}]}, 'unknown status');
  await run({files:[{filename:docPath,status:'modified'},
    {filename:docPath,status:'modified'}]}, 'duplicate file metadata');
  await run({files:[]}, 'empty diff');
  await run({eventName:'workflow_dispatch'}, 'manual dispatch is not push');
  process.stdout.write('codspeed-push-impact: strict positive/negative contracts passed\n');
}
pushContracts().catch(err => {console.error(err);process.exitCode = 1;});
