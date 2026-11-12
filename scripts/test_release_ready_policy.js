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
const platforms = ["ubuntu-latest", "ubuntu-24.04-arm", "macos-15-intel", "macos-15"];
const versions = ["3.11", "3.12", "3.13", "3.14"];
const prefix = os => "Installed artifacts / Platform wheels ("+os+") / ";
const matrix = () => [
  ...Array.from({length:16}, (_,i) => job("Source correctness / build ("+i+")")),
  job("Installed artifacts / Verify version and release ref"),
  ...platforms.map(os => job(prefix(os)+"Build wheels on "+os)),
  job("Installed artifacts / Build source distribution"),
  ...platforms.flatMap(os => versions.map(py => job(prefix(os)+"Wheel smoke ("+os+", py"+py+")"))),
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
    ["reject missing wheel smoke",{jobs:base.filter(x=>x.name!==prefix("macos-15-intel")+"Wheel smoke (macos-15-intel, py3.11)")},true],
    ["reject skipped sdist smoke",{jobs:base.map(x=>x.name==="Installed artifacts / Sdist smoke (1)"?{...x,conclusion:"skipped"}:x)},true],
    ["reject incomplete job",{jobs:base.map(x=>x.name===prefix("ubuntu-latest")+"Wheel smoke (ubuntu-latest, py3.12)"?{...x,status:"in_progress",conclusion:null}:x)},true],
    ["reject failure in a smoke job",{jobs:base.map(x=>x.name===prefix("ubuntu-latest")+"Wheel smoke (ubuntu-latest, py3.12)"?{...x,conclusion:"failure"}:x)},true],
    ["reject duplicated smoke masking a missing OS/Python pair",{jobs:base.map(x=>x.name===prefix("macos-15")+"Wheel smoke (macos-15, py3.13)"?{...x,name:prefix("ubuntu-latest")+"Wheel smoke (ubuntu-latest, py3.13)"}:x)},true],
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
  console.log("Release policy 14 positive/negative scenarios passed");
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

 
// Platform-local smoke must not wait for unrelated wheel builders.
{
  const common = fs.readFileSync(".github/workflows/platform-wheel-ci.yml", "utf8");
  const candidate = fs.readFileSync(".github/workflows/release-artifact-ci.yml", "utf8");
  const publisher = fs.readFileSync(".github/workflows/python-publish.yml", "utf8");
  const check = text => {
    assert.match(text, /\n  artifact_install:\n[\s\S]*?    needs: build_wheels\n/);
    assert.match(text, /name: all-builds-dist-wheels-\$\{\{ inputs\.os \}\}/);
    assert.doesNotMatch(text, /pattern: all-builds-dist-wheels-\*/);
    assert.match(text, /CIBW_ARCHS: \$\{\{ inputs\.arch \}\}/);
    assert.match(text, /python-version: \["3\.11", "3\.12", "3\.13", "3\.14"\]/);
  };
  check(common);
  for (const text of [candidate, publisher]) {
    assert.match(text, /uses: \.\/\.github\/workflows\/platform-wheel-ci\.yml/);
    assert.doesNotMatch(text, /needs: \[verify_release_ref, build_wheels\]/);
  }
  for (const [name, mutate] of [
    ["lost local build dependency", x => x.replace("needs: build_wheels", "needs: build_sdist")],
    ["cross-platform wheel download", x => x.replace("name: all-builds-dist-wheels-${{ inputs.os }}", "pattern: all-builds-dist-wheels-*")],
  ]) {
    const changed = mutate(common);
    assert.notEqual(changed, common, name);
    assert.throws(() => check(changed), undefined, name);
  }
}
// Dual-registry releases must fail closed before their first irreversible
// upload. GitHub Release is public only after both registries publish, and
// must carry the same Rust crate bytes as crates.io.
{
  const publishYaml = fs.readFileSync(".github/workflows/python-publish.yml", "utf8");
  const getJob = (yaml, name) => {
    const sections = yaml.split(new RegExp("^  " + name + ":\\s*$", "m"));
    assert.equal(sections.length, 2, "Expected one release job: " + name);
    return sections[1].split(/^  [a-z][a-z0-9_]*:\s*$/m)[0];
  };
  function checkDualReleasePolicy(yaml) {
    const preflight = getJob(yaml, "rust_preflight");
    const python = getJob(yaml, "publish");
    const rust = getJob(yaml, "publish_crates_io");
    const release = getJob(yaml, "github_release");
    assert.match(yaml, /format\('release-\{0\}', inputs\.recover_tag\)/,
      "Recovery of an immutable tag must share the normal tag publishing lock");
    assert.match(yaml, /format\('release-\{0\}', github\.ref_name\)/,
      "Normal tag publication must share the recovery publishing lock");
    const tagOnly = block => {
      assert.match(block, /github\.event_name == 'push'/);
      assert.match(block, /github\.ref_type == 'tag'/);
      assert.match(block, /startsWith\(github\.ref, 'refs\/tags\/v'\)/);
    };
    for (const block of [preflight, python, rust, release]) tagOnly(block);

    assert.match(preflight, /needs: verify_release_ref/);
    assert.match(preflight, /environment: crates-io/);
    assert.doesNotMatch(preflight, /id-token: write/, "Preflight must not request publishing credentials");
    assert.match(preflight, /CRATES_IO_PUBLISH_ENABLED: \$\{\{ vars\.QUPRS_CRATES_IO_PUBLISH_ENABLED \}\}/);
    assert.match(preflight, /CRATES_IO_PUBLISH_ENABLED" != "true"/);
    assert.match(preflight, /scripts\/stage_rust_crate_candidate\.py/);
    assert.match(preflight, /cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --list --locked/);
    assert.match(preflight, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --dry-run --locked/);
    assert.match(preflight, /cargo publish --manifest-path[^\n]*--dry-run --locked[\s\S]*cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --locked --no-verify[\s\S]*test -s "\$crate"/,
      "The preflight must materialize a persistent locked .crate after dry-run");
    assert.match(preflight, /actions\/upload-artifact@v4/);
    assert.match(preflight, /retention-days: 90/,
      "Reviewed Rust crate archive must survive a later partial-release recovery");
    assert.doesNotMatch(preflight, /crates-io-auth-action/, "OIDC token is obtained only for actual publish");
    assert.doesNotMatch(preflight, /cargo publish --manifest-path .* --registry crates-io/,
      "Native preflight must never upload to crates.io");
    assert.doesNotMatch(preflight, /action-gh-release|gh-action-pypi-publish/,
      "Preflight must never publish either registry or GitHub Release");

    assert.match(python, /needs: \[verify_release_ref, platform_wheels, build_sdist, sdist_install, rust_preflight\]/,
      "Python publishing must depend on successful native preflight");
    assert.match(python, /id-token: write/);
    assert.match(python, /pypa\/gh-action-pypi-publish@release\/v1/);
    assert.match(python, /scripts\/reconcile_pypi_artifacts\.py plan/,
      "PyPI must compare existing files before irreversible upload");
    assert.match(python, /scripts\/reconcile_pypi_artifacts\.py verify/,
      "PyPI must verify all registry archive hashes after upload");
    assert.match(python, /if: steps\.pypi_plan\.outputs\.publish_required == 'true'/,
      "Publishing must be skipped if all immutable files are already identical");
    assert.match(python, /packages-dir: pypi-to-upload\//,
      "Publish only the preverified missing file subset");
    assert.doesNotMatch(python, /skip-existing:\s*true/,
      "Do not silently ignore an existing mismatched PyPI distribution");

    assert.doesNotMatch(python, /action-gh-release/,
      "Public GitHub Release must follow both registries");

    assert.match(rust, /needs: \[verify_release_ref, platform_wheels, build_sdist, sdist_install, rust_preflight\]/,
      "Rust publishing must wait for the same completed artifact smoke and native preflight gates as PyPI");
    assert.doesNotMatch(rust, /needs: \[[^\]]*\bpublish\b[^\]]*\]/,
      "PyPI and crates.io must publish independently after their common safety gates");
    assert.match(rust, /environment: crates-io/);
    assert.match(rust, /id-token: write/);
    assert.match(rust, /vars\.QUPRS_CRATES_IO_PUBLISH_ENABLED == 'true'/);
    assert.match(rust, /scripts\/stage_rust_crate_candidate\.py/,
      "Rust publish must operate on isolated native crate");
    assert.match(rust, /test "\$\(git rev-parse HEAD\)" = "\$GITHUB_SHA"/,
      "Post-PyPI Rust release must verify the admitted immutable tag commit");
    assert.doesNotMatch(rust, /refs\/remotes\/origin\/main/,
      "A later main advancement must not cause a partially published release");
    assert.doesNotMatch(rust, /registry_state|api\/v1\/crates|reconcile_crates_io_publish/,
      "Normal publishing must use Cargo instead of custom registry API gates");
    assert.match(rust, /cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --locked/);
    assert.match(rust, /sha256sum -c SHA256SUMS/,
      "The released crate must match the preflight archive");
    assert.match(rust, /rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.match(rust, /CARGO_REGISTRY_TOKEN: \$\{\{ steps\.crates_io_auth\.outputs\.token \}\}/);
    assert.match(rust, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --registry crates-io --locked/);
    assert.match(release, /needs: \[verify_release_ref, rust_preflight, publish, publish_crates_io\]/,
      "GitHub Release must wait for successful publication to both registries");
    assert.match(release, /softprops\/action-gh-release@v2/);
    assert.match(release, /pattern: pypi-release-\*/);
    assert.match(release, /release-native-/);
    assert.match(release, /sha256sum -c SHA256SUMS/,
      "GitHub release must attach the checked immutable crate");
    assert.match(release, /cp "\$RUNNER_TEMP\/rust-dist\/\$crate" "\$RUNNER_TEMP\/release-assets\/\$crate"/);
    assert.doesNotMatch(release, /static\.crates\.io/,
      "GitHub release must not depend on a second registry CDN request");
    assert.match(release, /SHA256SUMS.txt/);
    assert.match(release, /release-assets\/\*/);
    assert.match(release, /https:\/\/pypi\.org\/project\/QuPRS\//);
    assert.match(release, /https:\/\/crates\.io\/crates\/quprs\//);
  }
  checkDualReleasePolicy(publishYaml);
  for (const [name, mutation] of [
    ["preflight accidentally dispatched", x => x.replace(
      /(  rust_preflight:[\s\S]*?github\.event_name == )'push'/,
      "$1'workflow_dispatch'")],
    ["shorten original Rust archive retention", x => x.replace(
      "retention-days: 90", "retention-days: 7")],
    ["preflight skips Rust dry-run", x => x.replace(
      'cargo publish --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --dry-run',
      'echo skipped-dry-run')],
    ["preflight does not materialize the Rust archive", x => x.replace(
      'cargo package --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --locked --no-verify',
      'echo missing-crate')],
    ["Rust opt-in disabled by mutation", x => x.replace(
      "vars.QUPRS_CRATES_IO_PUBLISH_ENABLED == 'true'", "true")],
    ["Python publishes before Rust preflight", x => x.replace(
      "sdist_install, rust_preflight]", "sdist_install]")],
    ["PyPI retry skips source artifact reconciliation", x => x.replace(
      "python3 scripts/reconcile_pypi_artifacts.py plan", "echo unchecked-artifacts")],
    ["PyPI retry ignores published archive verification", x => x.replace(
      "python3 scripts/reconcile_pypi_artifacts.py verify", "echo unchecked-registry")],
    ["PyPI retry uploads the unfiltered distribution set", x => x.replace(
      "packages-dir: pypi-to-upload/", "packages-dir: dist/")],
    ["Rust skips installed artifact safety gates", x => x.replace(
      "needs: [verify_release_ref, platform_wheels, build_sdist, sdist_install, rust_preflight]",
      "needs: [verify_release_ref, rust_preflight]")],
    ["Rust waits for PyPI instead of publishing independently", x => x.replace(
      "needs: [verify_release_ref, platform_wheels, build_sdist, sdist_install, rust_preflight]",
      "needs: [verify_release_ref, rust_preflight, publish]")],
    ["Rust package digest is not checked", x => x.replace(
      "sha256sum -c SHA256SUMS", "echo skip-checksum")],
    ["Rust publishes workspace directly", x => x.replace(
      'cargo publish --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --registry crates-io',
      'cargo publish --manifest-path rust/Cargo.toml --registry crates-io')],
    ["Rust rechecks mutable main after successful PyPI upload", x => x.replace(
      'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
      'test "$(git rev-parse HEAD)" = "$(git rev-parse refs/remotes/origin/main)"')],
    ["GitHub Release created before Rust publish", x => x.replace(
      "needs: [verify_release_ref, rust_preflight, publish, publish_crates_io]",
      "needs: [verify_release_ref, rust_preflight, publish]")],
    ["GitHub Release uses unchecked native artifact", x => x.replace(
      '(cd "$RUNNER_TEMP/rust-dist" && sha256sum -c SHA256SUMS)',
      "echo skip-archive-identity")],
    ["GitHub Release omits Rust registry link", x => x.replace(
      "https://crates.io/crates/quprs/", "https://example.invalid/crate/")],
  ]) {
    const changed = mutation(publishYaml);
    assert.notEqual(changed, publishYaml, "Mutation must change source: " + name);
    assert.throws(() => checkDualReleasePolicy(changed), undefined, name);
  }

  function checkRecoveryPolicy(yaml) {
    const ordinary = getJob(yaml, "verify_release_ref");
    const recover = getJob(yaml, "recover_crates_io");
    const gh = getJob(yaml, "recover_github_release");
    assert.match(ordinary, /!inputs\.recover_tag/,
      "Recovery must not run the full Python build/upload pipeline");
    assert.match(recover, /github\.event_name == 'workflow_dispatch'/);
    assert.match(recover, /environment: crates-io/);
    assert.match(recover, /id-token: write/);
    assert.match(recover, /SOURCE_RUN_ID: \$\{\{ inputs\.source_run_id \}\}/);
    assert.match(recover, /gh api "repos\/\$GITHUB_REPOSITORY\/actions\/runs\/\$SOURCE_RUN_ID"/);
    assert.match(recover, /git -C release-source cat-file -t/);
    assert.match(recover, /git\/tags\/\$tag_obj/);
    assert.match(recover, /sha256sum -c SHA256SUMS/);
    assert.match(recover, /cmp "\$RUNNER_TEMP\/original-crate\//);
    assert.equal((recover.match(/if: inputs\.perform_publish == true/g) || []).length, 2,
      "Recovery must gate both token acquisition and Cargo upload on explicit opt-in");
    assert.match(recover, /rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.match(recover, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --registry crates-io --locked/);
    assert.doesNotMatch(recover, /gh-action-pypi-publish/);
    assert.match(gh, /needs: recover_crates_io/);
    assert.match(gh, /inputs\.perform_publish == true/);
    assert.match(gh, /reconcile_pypi_artifacts\.py verify/);
    assert.match(gh, /scripts\/release_version\.py --kind python/,
      "Recovery must publish versioned Python release links");
    assert.match(gh, /https:\/\/pypi\.org\/project\/QuPRS\/\$\{\{ steps\.prepare\.outputs\.python_version \}\}/,
      "Recovery release notes must link the exact Python version");
    assert.match(gh, /\[Changelog\]/,
      "Recovered GitHub Release must preserve the public changelog link");
    assert.match(gh, /softprops\/action-gh-release@v2/);
  }
  checkRecoveryPolicy(publishYaml);
  for (const [name, replacement] of [
    ["missing signed tag verification", ["git/tags/$tag_obj", "missing-tag-verification"]],
    ["missing crate identity comparison", ['cmp "$RUNNER_TEMP/original-crate/', 'true # "$RUNNER_TEMP/original-crate/']],
    ["missing explicit publish opt-in", ["if: inputs.perform_publish == true", "if: true"]],
    ["recovery release notes omit exact Python version", ['echo "python_version=$(cd release-source && python3 scripts/release_version.py --kind python)" >> "$GITHUB_OUTPUT"', "echo missing-version"]],
  ]) {
    const [needle, substitute] = replacement;
    const changed = publishYaml.replace(needle, substitute);
    assert.notEqual(changed, publishYaml, name + " did not mutate policy");
    assert.throws(() => checkRecoveryPolicy(changed), undefined, name);
  }
  console.log("Dual-registry publication and minimal recovery policy controls passed");
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
