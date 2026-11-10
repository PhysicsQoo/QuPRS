'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const decide = require('./docs-render-admission.cjs');

const HEAD = 'a'.repeat(40);
const BEFORE = 'b'.repeat(40);
const repo = {owner: 'PhysicsQoo', repo: 'QuPRS'};
const pull = {
  number: 101,
  base: {ref: 'dev'},
  head: {sha: HEAD, repo: {full_name: 'PhysicsQoo/QuPRS'}}
};
const prContext = {eventName: 'pull_request', repo,
  payload: {action: 'synchronize', pull_request: pull}};
const pushContext = {eventName: 'push', repo, ref: 'refs/heads/dev', sha: HEAD,
  payload: {before: BEFORE}};
const site = 'docs/site/path-sum.md';
const docsOnly = 'scripts/check_docs_scoped_contract.py';
const rust = 'rust/pathsum/src/qasm.rs';
const entry = filename => ({filename, status: 'modified'});
const github = (files, status = 'ahead') => ({
  paginate: async () => files,
  rest: {
    pulls: {listFiles: () => {}},
    repos: {compareCommits: async () => ({
      data: {status, behind_by: 0, files}
    })}
  }
});
const run = (context, files, options = {}) =>
  decide({github: github(files), context, treeMatches: () => true, ...options});

(async () => {
  for (const event of ['pull_request', 'push']) {
    const paths = decide.workflowPaths(
      fs.readFileSync('.github/workflows/rust-api-docs.yml', 'utf8'), event);
    assert.ok(paths.includes('docs/site/**'), 'Shared site path must be covered');
    assert.ok(paths.includes('mkdocs.yml'), 'Shared config must be covered');
    assert.ok(paths.includes('src/QuPRS/pathsum/core.py'),
      'Shared Python API sources must be covered');
  }

  assert.equal((await run(prContext, [entry(site)])).buildSite, false);
  assert.equal((await run(pushContext, [entry(site)])).buildSite, false);
  assert.equal((await run(prContext, [entry(rust), entry(docsOnly)])).buildSite, false);
  assert.equal((await run(prContext, [entry(docsOnly)])).buildSite, true);
  assert.equal((await run(pushContext, [entry(docsOnly)])).buildSite, true);
  assert.equal((await run(prContext, [entry('.github/workflows/docs-check.yml')])).buildSite, true);
  assert.equal((await run(prContext, [])).buildSite, true);
  assert.equal((await run(prContext, Array(300).fill(entry(site)))).buildSite, true);
  assert.equal((await run(prContext, [{filename: site, status: 'renamed'}])).buildSite, true);
  assert.equal((await run(prContext, [entry(site)], {treeMatches: () => false})).buildSite, true);
  assert.equal((await run(prContext, [entry(site)], {treeMatches: () => {
    throw new Error('not fetched');
  }})).buildSite, true);
  assert.equal((await run(prContext, [entry(site)], {readYaml: () => 'on:\n'})).buildSite, true);
  const docYaml = fs.readFileSync('.github/workflows/rust-api-docs.yml', 'utf8');
  assert.equal((await run(prContext, [entry(site)], {
    readYaml: () => docYaml.replace("      - 'docs/site/**'", "      - '!docs/site/**'")
  })).buildSite, true);
  assert.equal((await decide({
    github: github([entry(site)]),
    context: {...prContext, payload: {...prContext.payload,
      pull_request: {...pull, head: {...pull.head, repo: {full_name: 'someone/other'}}}}},
    treeMatches: () => true
  })).buildSite, true);
  assert.equal((await decide({
    github: {paginate: async () => {throw new Error('API unavailable');},
      rest: {pulls: {listFiles: () => {}}}},
    context: prContext, treeMatches: () => true
  })).buildSite, true);
  assert.equal((await run({...prContext, payload: {...prContext.payload,
    action: 'edited'}}, [entry(site)])).buildSite, true);
  assert.equal((await run({...pushContext, ref: 'refs/heads/main'}, [entry(site)])).buildSite, true);
  assert.equal((await run({...pushContext, payload: {before: '0'.repeat(40)}},
    [entry(site)])).buildSite, true);
  assert.equal((await decide({github: github([entry(site)], 'behind'),
    context: pushContext, treeMatches: () => true})).buildSite, true);
  assert.equal((await run({eventName: 'workflow_dispatch', repo}, [entry(site)])).buildSite, true);

  const workflow = fs.readFileSync('.github/workflows/docs-check.yml', 'utf8');
  for (const step of [
    'Build documentation in strict mode',
    'Validate generated documentation',
    'Check rendered dynamic Gate members'
  ]) {
    const pos = workflow.indexOf(`      - name: ${step}\n`);
    assert.ok(pos !== -1, `Missing site check ${step}`);
    assert.match(workflow.slice(pos, pos + 180),
      /if: steps\.rendered_site\.outputs\.build_site != 'false'/,
      `Not protected by source-matched site admission: ${step}`);
  }
  assert.match(workflow, /python scripts\/check_docs_site\.py --negative-link-test/);
  assert.match(workflow, /node \.github\/scripts\/test-docs-render-admission\.cjs/);
  assert.match(workflow, /fetch-depth: 2/);
  assert.match(workflow, /pull-requests: read/);
  const rustWorkflow = fs.readFileSync('.github/workflows/rust-api-docs.yml', 'utf8');
  assert.match(rustWorkflow, /zensical build --strict --clean/);
  assert.match(rustWorkflow, /python scripts\/check_docs_gate_stubs\.py --site/);
  assert.match(rustWorkflow, /python scripts\/check_docs_site\.py --site/);
  console.log('Document site build ownership: positive and fail-closed cases PASS');
})().catch(e => {console.error(e); process.exitCode = 1;});
