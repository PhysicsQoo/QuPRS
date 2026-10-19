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
