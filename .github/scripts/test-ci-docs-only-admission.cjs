'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const admit = require('./ci-docs-only-admission.cjs');
const beforeSha='a'.repeat(40), afterSha='b'.repeat(40);
const file='rust/quprs/src/lib.rs';
const before='/// Before\npub fn check() -> bool { true }\n';
const after='/// After\npub fn check() -> bool { true }\n';
function simulate(settings={}) {
  const {files=[{filename:file,status:'modified'}],changedFiles=files.length,
    texts={[file]:[before,after]},eventName='pull_request',action='opened',
    target='dev',bases=['dev'],headRepo='PhysicsQoo/QuPRS',
    baseRepo='PhysicsQoo/QuPRS',base=beforeSha,head=afterSha,
    invalidSource=null,failList=false,failSource=false}=settings;
  const context={eventName,repo:{owner:'PhysicsQoo',repo:'QuPRS'},
    payload:{action,pull_request:{number:180,changed_files:changedFiles,
      head:{sha:head,repo:{full_name:headRepo}},
      base:{ref:target,sha:base,repo:{full_name:baseRepo}}}}};
  const github={rest:{pulls:{listFiles(){}},repos:{
    async getContent({path,ref}) {
      if(failSource)throw Error('source fetch unavailable');
      assert.ok(texts[path]&&[base,head].includes(ref));
      if(invalidSource)return {data:invalidSource};
      const bytes=Buffer.from(texts[path][ref===base?0:1]);
      return {data:{type:'file',encoding:'base64',size:bytes.length,
        content:bytes.toString('base64')}};
    }
  }},async paginate(method,args){
    assert.equal(method,github.rest.pulls.listFiles);
    assert.deepEqual(args,{owner:'PhysicsQoo',repo:'QuPRS',
      pull_number:180,per_page:100});
    if(failList)throw Error('list unavailable');
    return files;
  }};
  return admit({github,context,baseBranches:bases});
}
async function check() {
  const skip=async(s,name)=>assert.equal((await simulate(s)).run,false,name);
  const run=async(s,name)=>assert.equal((await simulate(s)).run,true,name);
  await skip({},'first Rustdoc-only PR');
  await skip({target:'main',bases:['dev','main']},'Docker PR to main');
  await skip({texts:{[file]:['pub fn check() -> bool { true }\n',
      '/// Public docs\npub fn check() -> bool { true }\n']}},'new Rustdoc');
  await skip({texts:{[file]:['/// Old\npub fn check() -> bool { true }\n',
      'pub fn check() -> bool { true }\n']}},'removed Rustdoc');
  await skip({files:[{filename:file,status:'modified'},
      {filename:'docs/site/usage.md',status:'modified'}]},'Rustdoc + Markdown');
  await skip({files:[{filename:'README.md',status:'modified'}]},'root prose');

  await run({texts:{[file]:[before,'/// After\npub fn check() -> bool { false }\n']}},'real Rust logic');
  await run({texts:{[file]:['const S: &str=r#"\n/// Old\n"#;\n',
      'const S: &str=r#"\n/// New\n"#;\n']}},'Rust raw string is not Rustdoc');
  await run({texts:{[file]:['/*\n/// Old\n*/\npub fn f(){}\n',
      '/*\n/// New\n*/\npub fn f(){}\n']}},'nested block comment is not Rustdoc');
  await run({texts:{[file]:['// Old\npub fn f(){}\n',
      '// New\npub fn f(){}\n']}},'ordinary comment not Rustdoc');
  for(const path of [
    'rust/Cargo.toml','rust/Cargo.lock','rust/quprs/build.rs',
    'rust/quprs/README.md','Dockerfile','pyproject.toml','GPMC',
    'MANIFEST.in','.gitmodules','src/QuPRS/pathsum/core.py',
    '.github/workflows/native-cross-platform-pr.yml',
    '.github/workflows/docker-build.yml','.github/workflows/pytest.yml',
    '.github/scripts/ci-impact-reuse.cjs',
    '.github/scripts/ci-docs-only-admission.cjs'
  ])await run({files:[{filename:file,status:'modified'},
    {filename:path,status:'modified'}]},'unsafe input: '+path);
  await run({files:[{filename:file,status:'renamed',
    previous_filename:'rust/quprs/src/old.rs'}]},'rename');
  await run({files:[{filename:file,status:'added'}]},'added source');
  await run({files:[{filename:'docs/help.md',status:'removed'}]},'removed docs');
  await run({files:[{filename:file,status:'mystery'}]},'unknown status');
  await run({files:[{filename:file,status:'modified'},
    {filename:file,status:'modified'}]},'duplicate path');
  await run({eventName:'workflow_dispatch'},'manual always runs');
  await run({eventName:'push'},'tags always run');
  await run({target:'main'},'native only dev');
  await run({target:'release',bases:['main','dev']},'unsupported base');
  await run({action:'unknown'},'unknown action');
  await run({headRepo:'external/repo'},'fork');
  await run({baseRepo:'external/repo'},'foreign base');
  await run({base:'badsha'},'invalid base SHA');
  await run({head:'badsha'},'invalid head SHA');
  await run({head:beforeSha},'equal SHA');
  await run({changedFiles:2},'missing file');
  await run({changedFiles:101},'over 100 files');
  await run({failList:true},'list API exception');
  await run({failSource:true},'content API exception');
  await run({invalidSource:{type:'dir',encoding:'base64',
    size:1,content:'QQ=='}},'unexpected resource type');
  await run({invalidSource:{type:'file',encoding:'base64',
    size:100,content:'QQ=='}},'incomplete full content');
  await run({invalidSource:{type:'file',encoding:'base64',
    size:150001,content:'QQ=='}},'oversized Rust source');

  for (const path of [
    '.github/workflows/native-cross-platform-pr.yml',
    '.github/workflows/docker-build.yml'
  ]) {
    const yml=fs.readFileSync(path,'utf8');
    assert.match(yml,/ci-docs-only-admission\.cjs/);
    assert.match(yml,/steps\.source_scope\.outputs\.run_source == 'true'/);
    assert.match(yml,/if: \$\{\{ steps\.source_scope\.outputs\.run_source == 'true' \}\}/);
    assert.match(yml,/pull-requests: read/);
    assert.match(yml,/node \.github\/scripts\/test-ci-docs-only-admission\.cjs/);
    const match=yml.match(/\n      - id: source_scope\n([\s\S]*?)\n      - id: resolve\n/);
    assert.ok(match,'source_scope must precede resolve');
    const raw=match[1].split('          script: |\n')[1];
    assert.ok(raw,'GitHub JS script must exist');
    const js=raw.split('\n').map(l=>l.startsWith('            ')?
      l.slice(12):l).join('\n');
    const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
    assert.doesNotThrow(()=>new AsyncFunction('github','context','core',js),
      'parse exact inline GitHub Actions JavaScript');
  }
  const docker=fs.readFileSync('.github/workflows/docker-build.yml','utf8');
  assert.match(docker,/startsWith\(github\.ref, 'refs\/tags\/v'\)/,
    'release image publication must remain unchanged');
  assert.match(docker,/inputs\.run_build_push == true/,
    'manual image publication must remain unchanged');
  process.stdout.write('ci-docs-only-admission: first-run and fail-closed contracts passed\n');
}
check().catch(e=>{console.error(e);process.exitCode=1;});
