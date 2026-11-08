'use strict';
const assert = require('node:assert/strict');
const resolve = require('./ci-impact-reuse.cjs');

const sha = 'a'.repeat(40);
const previous = 'b'.repeat(40);
const base = 'c'.repeat(40);
const before = (overrides = {}) => ({
  id: 99, conclusion: 'success', status: 'completed', head_sha: previous,
  pull_requests: [{
    number: 131,
    head: {repo: {id: 11}},
    base: {sha: base, ref: 'dev'}
  }],
  ...overrides
});

async function execute({files = [{filename: 'docs/development/notes.md'}], prior = before(),
  jobs = [{name: 'Named Bench', status: 'completed', conclusion: 'success'}],
  action = 'synchronize', eventName = 'pull_request', compareStatus = 'ahead',
  compareBehind = 0, throwAPI = false, failSource = false,
  sources = {before: '/// Before\npub fn run() {}\n',
             after: '/// After\npub fn run() {}\n'},
  workflowFile = 'codspeed.yml',
  requiredJobs = [{name: 'Named Bench', count: 1}]} = {}) {
  const outputs = {};
  const context = {
    repo: {owner: 'PhysicsQoo', repo: 'QuPRS'}, runId: 1000,
    eventName, payload: {action,
      pull_request: {number: 131, head: {sha, ref: 'feat/per-call-tolerance-api',
        repo: {full_name: 'PhysicsQoo/QuPRS', id: 11}},
      base: {sha: base, ref: 'dev'}}
    }
  };
  const core = {
    setOutput: (k,v) => {outputs[k] = v;}, info: () => {}, warning: () => {},
    summary: {addRaw() {return this;}, async write() {}}
  };
  const github = {
    rest: {
      actions: {
        async listWorkflowRuns() {
          if (throwAPI) throw new Error('unavailable');
          return {data: {workflow_runs: [prior]}};
        },
        listJobsForWorkflowRun: () => {}
      },
      repos: {
        async compareCommits() {
          return {data: {status: compareStatus, behind_by: compareBehind,
            files: files.map(f => ({status: 'modified', ...f}))}};
        },
        async getContent({ref}) {
          if (failSource) throw new Error('source unavailable');
          const content = ref === previous ? sources.before : sources.after;
          return {data: {type: 'file', encoding: 'base64',
            size: content.length, content: Buffer.from(content).toString('base64')}};
        }
      }
    },
    async paginate() {return jobs;}
  };
  const result = await resolve({
    github,context,core, workflowFile, requiredJobs
  });
  assert.equal(outputs.run_heavy, String(result.runHeavy));
  return result.runHeavy;
}

(async () => {
  assert.equal(await execute(), false, 'docs-only can reuse prior success');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs', status: 'modified'}]}), false, 'only Rustdoc may reuse successful previous measurement');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs', status: 'modified'}],
    sources: {before: '/// Before\npub fn run() {}\n',
              after: '/// After\npub fn run() { println!("change"); }\n'}}), true, 'Rust code changes force measurement');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs', status: 'modified'}],
    sources: {before: 'const S:&str=r#"\n/// Before\n"#;\n',
              after: 'const S:&str=r#"\n/// After\n"#;\n'}}), true, 'raw string changes force measurement');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs', status: 'modified'}], failSource:true}), true, 'missing full source fails closed');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs', status: 'renamed', previous_filename:'rust/pathsum/src/circuit.rs'}]}), true, 'rename fails closed');
  assert.equal(await execute({files: [{filename: '.github/workflows/codspeed.yml',status:'modified'}]}), true, 'own workflow changes force measurement');
  assert.equal(await execute({files: [{filename: '.github/scripts/codspeed-pr-impact.cjs',status:'modified'}]}), true, 'routing changes invalidate evidence');
  assert.equal(await execute({files: [{filename: 'rust/pathsum/src/lib.rs',status:'modified'}],
    prior:before({conclusion:'failure'})}), true, 'failed prior Rustdoc evidence is not reusable');
  assert.equal(await execute({files: [{filename: 'src/QuPRS/core.py'}]}), true, 'code must run');
  assert.equal(await execute({files: [{filename: 'benchmarks/codspeed/suite_catalog.json'}]}), true, 'registry must run');
  assert.equal(await execute({prior: before({conclusion: 'failure'})}), true, 'failed run cannot reuse');
  assert.equal(await execute({prior: before({pull_requests: [{number: 131, head: {repo: {id: 11}}, base: {sha: 'd'.repeat(40), ref:'dev'}}]})}), true, 'base mismatch');
  assert.equal(await execute({jobs: [{name:'Named Bench', conclusion:'skipped', status:'completed'}]}), true, 'skipped job is not successful evidence');
  assert.equal(await execute({files: Array.from({length: 300}, (_,i) => ({filename:`docs/${i}.md`}))}), true, 'truncated diff fails closed');
  assert.equal(await execute({compareStatus:'diverged', compareBehind:1}), true, 'force/rebase cannot reuse');
  assert.equal(await execute({throwAPI:true}), true, 'API outage fails closed');
  assert.equal(await execute({eventName:'push'}), true, 'push unchanged policy');
  assert.equal(await execute({action:'opened'}), true, 'first PR opens require fresh evidence');
  assert.equal(await execute({files: [], prior: before({head_sha:sha}), action:'edited'}), false, 'non-code edited event can reuse exact successful SHA');
  assert.equal(await execute({files: [{filename: '.github/workflows/wmc-conservative-policy.yml'}]}), false, 'unrelated WMC workflow does not force CodSpeed');
  assert.equal(await execute({workflowFile: 'wmc-conservative-policy.yml', files: [{filename: '.github/workflows/wmc-conservative-policy.yml'}]}), true, 'own workflow change forces validation');
  assert.equal(await execute({workflowFile: 'native-cross-platform-pr.yml', files: [{filename: '.github/workflows/pytest.yml'}]}), true, 'called pytest workflow invalidates native evidence');
  assert.equal(await execute({jobs: [{name:'Native parser and QASM source semantics',status:'completed',conclusion:'success'}],
      workflowFile:'rust-qasm-source-guard.yml', requiredJobs:[{name:'Native parser and QASM source semantics',count:1}]}), false, 'single current Rust QASM job is reusable');
  assert.equal(await execute({jobs: [{name:'Native parser and QASM source semantics',status:'completed',conclusion:'skipped'}],
      workflowFile:'rust-qasm-source-guard.yml', requiredJobs:[{name:'Native parser and QASM source semantics',count:1}]}), true, 'skipped Rust QASM job cannot be reused');
  assert.equal(await execute({jobs: [{name:'Native parser and QASM source semantics (old)',status:'completed',conclusion:'success'}],
      workflowFile:'rust-qasm-source-guard.yml', requiredJobs:[{name:'Native parser and QASM source semantics',count:1}]}), true, 'mismatched Rust QASM job identity cannot be reused');
  process.stdout.write('ci-impact-reuse: 18 contract cases passed\\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
