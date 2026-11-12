'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const decide = require('./ci-pytest-push-impact.cjs');
const oldSHA='a'.repeat(40), newSHA='b'.repeat(40);
const rust='rust/quprs/src/lib.rs';
const oldText='/// Before\npub fn f() -> i32 { 1 }\n';
const newText='/// After\npub fn f() -> i32 { 1 }\n';
function fixture(o={}) {
  const {
    files=[{filename:rust,status:'modified'}],
    sources={[rust]:[oldText,newText]},
    eventName='push',forced=false,created=false,deleted=false,
    ref='refs/heads/dev',payloadRef=ref,repoName='PhysicsQoo/QuPRS',
    before=oldSHA,after=newSHA,contextSHA=after,
    compareStatus='ahead',behind=0,baseCommit=before,total=1,
    commits=[after],failCompare=false,failGet=false,badContent=null,
    forceFullMatrix=false
  }=o;
  const context={
    eventName, ref, sha:contextSHA, repo:{owner:'PhysicsQoo',repo:'QuPRS'},
    payload:{ref:payloadRef,before,after,forced,created,deleted,
      repository:{full_name:repoName}}
  };
  const github={rest:{repos:{
    async compareCommits(args){
      assert.deepEqual(args,{owner:'PhysicsQoo',repo:'QuPRS',
        base:before,head:after,per_page:100});
      if(failCompare)throw Error('Compare is unavailable');
      return {data:{status:compareStatus,behind_by:behind,
        base_commit:{sha:baseCommit},ahead_by:total,
        total_commits:total,commits:commits.map(sha=>({sha})),files}};
    },
    async getContent({path,ref}){
      if(failGet)throw Error('Content is unavailable');
      assert.ok(sources[path],'Unexpected source: '+path);
      assert.ok([before,after].includes(ref),'Unexpected reference: '+ref);
      if(badContent)return {data:badContent};
      const source=sources[path][ref===before?0:1],data=Buffer.from(source);
      return {data:{type:'file',encoding:'base64',size:data.length,
        content:data.toString('base64')}};
    }
  }}};
  return decide({github,context,forceFullMatrix});
}
async function tests(){
  const skip=async (o,msg)=>assert.equal((await fixture(o)).run,false,msg);
  const run=async (o,msg)=>assert.equal((await fixture(o)).run,true,msg);

  await skip({},'pure whole-line Rustdoc on dev');
  await skip({ref:'refs/heads/main'},'pure whole-line Rustdoc on main');
  await skip({sources:{[rust]:['pub fn f() -> i32 { 1 }\n',
    '/// Added\npub fn f() -> i32 { 1 }\n']}},'new Rustdoc');
  await skip({sources:{[rust]:['/// Old\npub fn f() -> i32 { 1 }\n',
    'pub fn f() -> i32 { 1 }\n']}},'removed Rustdoc');
  await skip({files:[{filename:rust,status:'modified'},
    {filename:'rust/quprs/src/circuit.rs',status:'modified'}],
    sources:{[rust]:[oldText,newText],
      'rust/quprs/src/circuit.rs':['//! Old\npub mod circuit;\n',
        '//! New\npub mod circuit;\n']}},'multiple Rustdoc source files');
  await run({sources:{[rust]:[oldText,'/// Updated\npub fn f() -> i32 { 2 }\n']}},'actual logic change');
  await run({sources:{[rust]:['const S: &str = r#"\n/// Old\n"#;\n',
    'const S: &str = r#"\n/// New\n"#;\n']}},'raw string false friend');
  await run({sources:{[rust]:['/*\n/// Old\n*/\npub fn f() {}\n',
    '/*\n/// New\n*/\npub fn f() {}\n']}},'block-comment false friend');
  await run({sources:{[rust]:['// Old\npub fn f(){}\n',
    '// New\npub fn f(){}\n']}},'not doc comment');
  await run({sources:{[rust]:['/// Old\npub fn f() {}\n',
    '/// New\npub fn f() {}\n'+'X'.repeat(150001)]}},'oversized file');
  const sensitive=[
    'test/test_Feynman.py','test/test_solver_process_lifecycle.py',
    'src/QuPRS/pathsum/core.py','src/QuPRS/__init__.py',
    'rust/quprs/Cargo.toml','rust/Cargo.lock',
    'rust/quprs/README.md','rust/quprs/build.rs',
    'GPMC','.gitmodules','pyproject.toml',
    '.github/workflows/pytest.yml',
    '.github/scripts/ci-pytest-push-impact.cjs',
    'docs/development/paper-corpus-manifest.json',
    'benchmarks/codspeed/test.py','README.md'
  ];
  for(const path of sensitive){
    await run({files:[{filename:rust,status:'modified'},
      {filename:path,status:'modified'}]},'mixed source/fixture: '+path);
    await run({files:[{filename:path,status:'modified'}]},'non-Rustdoc-only: '+path);
  }
  await run({files:[{filename:rust,status:'renamed',
    previous_filename:'rust/quprs/src/old.rs'}]},'rename');
  await run({files:[{filename:rust,status:'added'}]},'added Rust');
  await run({files:[{filename:rust,status:'removed'}]},'deleted Rust');
  await run({files:[{filename:rust,status:'modified'},
    {filename:rust,status:'modified'}]},'duplicate name');
  await run({files:[{filename:rust,status:'mystery'}]},'unknown status');
  await run({files:[]},'no files is not sufficient proof');
  await run({files:Array.from({length:300},(_,i)=>
    ({filename:'rust/src/file_'+i+'.rs',status:'modified'}))},'truncated file listing');
  await run({forced:true},'forced push');
  await run({created:true},'initial branch push');
  await run({deleted:true},'deleted branch push');
  await run({before:'0'.repeat(40)},'initial null SHA');
  await run({after:'0'.repeat(40)},'deleted null SHA');
  await run({after:oldSHA},'identical SHAs');
  await run({contextSHA:'c'.repeat(40)},'context SHA mismatch');
  await run({ref:'refs/heads/feature'},'unprotected branch');
  await run({payloadRef:'refs/heads/feature'},'mismatched event branch');
  await run({repoName:'other/repo'},'mismatched repo');
  await run({compareStatus:'diverged'},'divergent history');
  await run({behind:1},'behind base');
  await run({baseCommit:'c'.repeat(40)},'different base commit');
  await run({total:101,commits:[newSHA]},'truncated commit comparison');
  await run({total:2,commits:[newSHA]},'missing commits');
  await run({commits:['c'.repeat(40)]},'different last commit');
  await run({failCompare:true},'compare API failure');
  await run({failGet:true},'content API failure');
  await run({badContent:{type:'dir',encoding:'base64',
    size:1,content:'QQ=='}},'invalid file metadata');
  await run({badContent:{type:'file',encoding:'base64',
    size:99,content:'QQ=='}},'incorrect byte count');
  await run({badContent:{type:'file',encoding:'base64',
    size:150001,content:'QQ=='}},'oversized file metadata');
  await run({eventName:'workflow_dispatch'},'manual must run');
  await run({eventName:'pull_request'},'reusable PR caller must run');
  await run({forceFullMatrix:true},'reusable workflow called from a push must run');

  const workflow=fs.readFileSync('.github/workflows/pytest.yml','utf8');
  assert.match(workflow, /workflow_call:\n    inputs:\n      require_full_matrix:\n/);
  assert.match(workflow, /required: false\n        default: true/);
  assert.match(workflow, /^  workflow_dispatch:/m);
  assert.match(workflow, /^    branches: \[main, dev\]/m);
  assert.match(workflow, /needs: \[source-admission\]/);
  assert.match(workflow, /needs\.source-admission\.outputs\.run_heavy == 'true'/);
  assert.match(workflow, /inputs\.require_full_matrix/);
  assert.match(workflow, /python-version: \["3.11", "3.12", "3.13"\]/);
  assert.match(workflow, /os: \[ubuntu-latest, ubuntu-24\.04-arm, macos-15-intel, macos-15\]/);
  assert.match(workflow, /test-pytest-push-impact\.cjs/);
  assert.match(workflow, /codspeed-pr-impact\.cjs/,
    'Shared Rustdoc lexer modification must trigger Pytest full source validation');
  // A later Rustdoc-only push must not cancel the previous source-changing
  // push before its 12-platform correctness matrix has finished.
  const concurrency=workflow.match(/^concurrency:\n((?:  .*\n)+)\n/m);
  assert.ok(concurrency,'Workflow-level concurrency exists');
  assert.match(concurrency[1],/^  group: .*github\.workflow.*github\.ref.*github\.event_name == 'push' && github\.sha \|\| 'shared'/m,
    'Push concurrency group must include exact github.sha');
  assert.match(concurrency[1],/^  cancel-in-progress: .*github\.event_name != 'push'/m,
    'Pushes may not cancel existing correctness runs');
  const group=(eventName,sha,ref='refs/heads/dev',name='Python Pytest CI')=>
    [name,ref,eventName==='push'?sha:'shared'].join('-');
  const shouldCancel=eventName=>eventName!=='push';
  const shaA='a'.repeat(40),shaB='b'.repeat(40);
  assert.notEqual(group('push',shaA),group('push',shaB),'Different push SHAs do not share a group');
  assert.equal(shouldCancel('push'),false,'A push does not cancel another push');
  for(const event of ['pull_request','workflow_call','workflow_dispatch']){
    assert.equal(group(event,shaA),group(event,shaB),'Same-ref group preserved for '+event);
    assert.equal(shouldCancel(event),true,'Original cancellation retained for '+event);
  }
  assert.notEqual(group('push',shaA,'refs/heads/main'),group('push',shaA),
    'Main and dev have separate groups');

  // Every supported OS/architecture keeps a Rust correctness run on the
  // canonical Python 3.12 slot, while full Python + coverage runs on all 12.
  const solverStep = workflow.match(
    /\n      - name: Verify pinned solver distribution \(Unix\)\n([\s\S]*?)\n      - name: Run Rust source tests \(once per OS\)\n/
  );
  assert.ok(solverStep, 'Pinned solver validation must remain on every Unix slot');
  assert.match(solverStep[1], /python -m QuPRS\.utils\.ganak_distribution/);
  const rustStep = workflow.match(
    /\n      - name: Run Rust source tests \(once per OS\)\n([\s\S]*?)\n      - name: Run tests \(Unix\)\n/
  );
  assert.ok(rustStep, 'Rust source tests must have their own fail-closed step');
  assert.match(rustStep[1], /if: matrix\.os != 'windows-latest' && matrix\.python-version == '3\.12'/);
  assert.match(rustStep[1], /cargo test --locked --manifest-path rust\/Cargo\.toml -p quprs/);
  const pythonStep = workflow.match(
    /\n      - name: Run tests \(Unix\)\n([\s\S]*?)\n      - name: Run tests \(Windows\)\n/
  );
  assert.ok(pythonStep, 'Every Unix matrix slot retains full Python pytest');
  assert.match(pythonStep[1], /if: matrix\.os != 'windows-latest'/);
  assert.match(pythonStep[1], /pytest -n auto -v -ra/);
  assert.doesNotMatch(pythonStep[1], /timeout-minutes:/,
    'No short per-pytest timeout: slow infrastructure must not be mistaken for a test failure');
  assert.match(pythonStep[1], /-o faulthandler_timeout=180/,
    'Report stuck Python test tracebacks before the CI step times out');
  assert.match(pythonStep[1], /--durations=20/,
    'Retain the slowest-test diagnosis after successful pytest runs');
  assert.match(workflow, /\n  build:\n[\s\S]*?\n    timeout-minutes: 60\n/,
    'Only a generous job-level resource ceiling may stop a stuck runner');
  assert.match(pythonStep[1], /--cov=src\/QuPRS --cov-report=xml --cov-report=html/);
  assert.doesNotMatch(pythonStep[1], /matrix\.python-version == '3\.12'/,
    'Python test/coverage must never be reduced to the Rust canonical slot');

  const m=workflow.match(/\n      - id: scope\n([\s\S]*?)\n  build:\n/);
  assert.ok(m,'source step must precede build');
  const embedded=m[1].split('          script: |\n')[1];
  assert.ok(embedded,'GitHub-script body present');
  const js=embedded.split('\n').map(line =>
    line.startsWith('            ') ? line.slice(12) : line).join('\n');
  const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
  assert.doesNotThrow(()=>new AsyncFunction('github','context','core','process',js),
    'inline GitHub-script must be executable JS');
  process.stdout.write('ci-pytest-push-impact: strict source/branch/reuse and workflow contracts passed\n');
}
tests().catch(err=>{console.error(err);process.exitCode=1;});
