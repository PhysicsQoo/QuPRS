#!/usr/bin/env node
"use strict";
// Execute the actual actions/github-script release gate against synthetic job
// matrices and PR provenance. Tests are independent of a live GitHub API.
const fs = require("node:fs");
const assert = require("node:assert/strict");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const lines = fs.readFileSync(".github/workflows/release-ready-main.yml", "utf8").split(/\r?\n/);
const start = lines.findIndex(line => line.trim() === "script: |");
assert(start >= 0, "Missing gate policy script");
const body = [];
for (let i = start + 1; i < lines.length; i += 1) {
  const line = lines[i];
  if (line.startsWith("            ")) body.push(line.slice(12));
  else if (line.trim() === "") body.push("");
  else break;
}
assert(body.length > 20, "Gate script unexpectedly small");
const evaluate = new AsyncFunction("github", "context", "core", "process", body.join("\n"));
const job = name => ({ name, status: "completed", conclusion: "success" });
const matrix = () => [
  ...Array.from({length:12}, (_,i) => job("Source correctness / build ("+i+")")),
  job("Installed artifacts / Verify version and release ref"),
  ...Array.from({length:4}, (_,i) => job("Installed artifacts / Build wheels on "+i)),
  job("Installed artifacts / Build source distribution"),
  ...Array.from({length:12}, (_,i) => job("Installed artifacts / Wheel smoke ("+i+")")),
  ...Array.from({length:2}, (_,i) => job("Installed artifacts / Sdist smoke ("+i+")")),
];
async function simulate(scenario) {
  const failures = [], infos = [];
  const items = scenario.jobs || matrix();
  const context = {
    eventName: "pull_request", repo: {owner:"PhysicsQoo", repo:"QuPRS"}, runId:123,
    payload: {pull_request: {
      base: {ref:scenario.target||"main"},
      head: {ref:scenario.source||"dev",
        repo: {full_name:scenario.fullName||"PhysicsQoo/QuPRS"}}
    }}
  };
  const core = {setFailed:msg=>failures.push(msg), info:msg=>infos.push(msg)};
  const github = {paginate:async()=>items, rest:{actions:{listJobsForWorkflowRun:()=>{}}}};
  const processMock = {env:{
    SOURCE_RESULT:scenario.sourceResult||"success",
    ARTIFACT_RESULT:scenario.artifactResult||"success",
    PARITY_RESULT:scenario.parityResult||"success",
    NEGATIVE_RESULT:scenario.negativeResult||"success",
  }};
  await evaluate(github,context,core,processMock);
  return failures;
}
async function main() {
  const base = matrix();
  const cases = [
    ["valid dev-to-main promotion",{},false],
    ["valid feature-to-dev integration",{target:"dev",source:"feat/feature"},false],
    ["reject feature-to-main",{source:"feat/unreviewed"},true],
    ["reject forked dev-to-main",{fullName:"DifferentOrg/QuPRS"},true],
    ["reject missing source shard",{jobs:base.filter(x=>x.name!=="Source correctness / build (4)")},true],
    ["reject missing wheel smoke",{jobs:base.filter(x=>x.name!=="Installed artifacts / Wheel smoke (6)")},true],
    ["reject skipped sdist smoke",{jobs:base.map(x=>x.name==="Installed artifacts / Sdist smoke (1)"?{...x,conclusion:"skipped"}:x)},true],
    ["reject incomplete job",{jobs:base.map(x=>x.name==="Installed artifacts / Wheel smoke (1)"?{...x,status:"in_progress",conclusion:null}:x)},true],
    ["reject failure in a smoke job",{jobs:base.map(x=>x.name==="Installed artifacts / Wheel smoke (1)"?{...x,conclusion:"failure"}:x)},true],
    ["reject cancelled source matrix",{sourceResult:"cancelled"},true],
    ["reject missing installed matrix",{artifactResult:"skipped"},true],
    ["reject builder/publisher drift",{parityResult:"failure"},true],
    ["reject missing policy negative tests",{negativeResult:"skipped"},true],
  ];
  for (const [name, scenario, shouldFail] of cases) {
    const errors = await simulate(scenario);
    assert.equal(errors.length>0,shouldFail, name+" produced "+errors.length+" error(s)");
    console.log("PASS "+name+": "+(shouldFail?"rejected":"accepted"));
  }
  console.log("Release policy 13 positive/negative scenarios passed");
}
main().catch(error=>{console.error(error);process.exitCode=1;});

// Prevent independent wheel/sdist acceptance on dev-to-main PRs.
// The reusable release-artifact-ci.yml matrix remains required from Release-Ready Main.
{
  const publish = fs.readFileSync(".github/workflows/python-publish.yml", "utf8");
  const release = fs.readFileSync(".github/workflows/release-ready-main.yml", "utf8");
  const prClause = publish.split(/^  pull_request:/m)[1]?.split(/^\S/m)[0] || "";
  assert.match(prClause, /\n    branches: \[dev\]/,
    "Packaging PR CI must be scoped to dev, not main release PRs");
  assert.match(publish, /\n  push:\n    tags:\n      - 'v\*'/,
    "Tagged publishing trigger must be preserved");
  assert.match(release, /uses: \.\/\.github\/workflows\/release-artifact-ci\.yml/,
    "Main Release-Ready must retain full installed archive smoke matrix");
  const source = release.split(/^  source-correctness:/m)[1]?.split(/^  installed-artifacts:/m)[0] || "";
  assert.match(source, /uses: \.\/\.github\/workflows\/pytest\.yml/,
    "Release-Ready must retain its complete source correctness matrix");
  assert.doesNotMatch(source, /require_complete_benchmarks:\s*true\b/,
    "Resource-inconclusive benchmarks must not be Required science failures");
  const pytest = fs.readFileSync(".github/workflows/pytest.yml", "utf8");
  assert.match(pytest, /python scripts\/check_benchmark_evidence\.py --junit pytest-results\.xml --json benchmark-evidence\.json/,
    "The real JUnit auditor must run on every source matrix shard");
  assert.doesNotMatch(pytest, /--require-complete/,
    "Strict performance completeness remains opt-in, not release correctness");
}

 
// Optional crates.io publishing must remain a separately authorized tag-only
// successor to the successful PyPI + GitHub release job. Negative mutations
// guard against weakening the opt-in / OIDC / isolated-package boundary.
{
  const publishYaml = fs.readFileSync(".github/workflows/python-publish.yml", "utf8");
  assert.equal((publishYaml.match(/^  publish_crates_io:$/gm) || []).length, 1,
    "Exactly one optional crates.io publish job is required");
  const job = publishYaml.split(/^  publish_crates_io:\s*$/m)[1];
  function requireCratesGate(yaml) {
    assert.match(yaml, /needs: \[verify_release_ref, publish\]/,
      "Rust publish must wait for verified successful PyPI/GitHub release");
    assert.match(yaml, /github\.event_name == 'push'/,
      "Rust publication must never run from workflow_dispatch or a PR");
    assert.match(yaml, /github\.ref_type == 'tag'/);
    assert.match(yaml, /startsWith\(github\.ref, 'refs\/tags\/v'\)/);
    assert.match(yaml, /vars\.QUPRS_CRATES_IO_PUBLISH_ENABLED == 'true'/,
      "Rust publish must require an explicit repository-level opt-in");
    assert.match(yaml, /environment: crates-io/,
      "Rust publish needs a dedicated protected environment");
    assert.match(yaml, /permissions:\n      contents: read\n      id-token: write/,
      "Only the Rust publishing job may request an OIDC token");
    assert.match(yaml, /scripts\/stage_rust_crate_candidate\.py/,
      "Never publish the workspace directly");
    assert.match(yaml, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --dry-run/);
    assert.match(yaml, /uses: rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.match(yaml, /CARGO_REGISTRY_TOKEN: \$\{\{ steps\.crates_io_auth\.outputs\.token \}\}/);
    assert.match(yaml, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --registry crates-io/);
    assert.match(yaml, /QUPRS_SOLVER_PROVISION: external/);
  }
  requireCratesGate(job);
  for (const [name, mutated] of [
    ["remove opt-in", job.replace("vars.QUPRS_CRATES_IO_PUBLISH_ENABLED == 'true'", "true")],
    ["enable manual publishing", job.replace("github.event_name == 'push'", "github.event_name == 'workflow_dispatch'")],
    ["remove successful PyPI dependency", job.replace("needs: [verify_release_ref, publish]", "needs: verify_release_ref")],
    ["remove OIDC permission", job.replace("id-token: write", "id-token: read")],
    ["publish non-isolated package", job.replace('cargo publish --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --registry crates-io', 'cargo publish --manifest-path rust/Cargo.toml --registry crates-io')],
  ]) {
    assert.throws(() => requireCratesGate(mutated), undefined, name);
  }
  console.log("Optional crates.io publish gate: positive and 5 negative source controls passed");
}


// The root README is version-neutral: release history belongs in CHANGELOG.
{
  const readme = fs.readFileSync("README.md", "utf8");
  const check = source => {
    assert.doesNotMatch(source, /\bv\d+\.\d+\.\d+\b/,
      "Root README must not pin a QuPRS release version");
    assert.doesNotMatch(source, /\bGanak \d+\.\d+\.\d+\b/,
      "Pinned solver versions belong in manifests or reference documents");
    assert.match(source, /https:\/\/github\.com\/PhysicsQoo\/QuPRS\/releases\/latest/,
      "README must point at the latest published release");
    assert.match(source, /https:\/\/pypi\.org\/project\/QuPRS\//,
      "README must point at current PyPI metadata");
    assert.match(source, /\(CHANGELOG\.md\)/,
      "README must route historical version details to CHANGELOG");
  };
  check(readme);
  for (const [name, mutation] of [
    ["hardcoded QuPRS version", readme + "\nFor v0.99.0 only\n"],
    ["pinned solver version", readme + "\nGanak 2.8.0 example\n"],
    ["missing latest release link", readme.replace(
      "https://github.com/PhysicsQoo/QuPRS/releases/latest",
      "https://github.com/PhysicsQoo/QuPRS/releases"
    )],
  ]) {
    assert.throws(() => check(mutation), undefined, name);
  }
  console.log("Evergreen root README and three negative controls passed");
}
