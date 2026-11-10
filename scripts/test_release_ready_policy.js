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
    const tagOnly = block => {
      assert.match(block, /github\.event_name == 'push'/);
      assert.match(block, /github\.ref_type == 'tag'/);
      assert.match(block, /startsWith\(github\.ref, 'refs\/tags\/v'\)/);
    };
    for (const block of [preflight, python, rust, release]) tagOnly(block);

    assert.match(preflight, /needs: verify_release_ref/);
    assert.match(preflight, /environment: crates-io/);
    assert.match(preflight, /id-token: write/);
    assert.match(preflight, /CRATES_IO_PUBLISH_ENABLED: \$\{\{ vars\.QUPRS_CRATES_IO_PUBLISH_ENABLED \}\}/);
    assert.match(preflight, /CRATES_IO_PUBLISH_ENABLED" != "true"/);
    assert.match(preflight, /scripts\/stage_rust_crate_candidate\.py/);
    assert.match(preflight, /cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --list --locked/);
    assert.match(preflight, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --dry-run --locked/);
    assert.match(preflight, /cargo publish --manifest-path[^\n]*--dry-run --locked[\s\S]*cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --locked --no-verify[\s\S]*test -s "\$crate"/,
      "The preflight must materialize a persistent locked .crate after dry-run");
    assert.match(preflight, /actions\/upload-artifact@v4/);
    assert.match(preflight, /rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.doesNotMatch(preflight, /cargo publish --manifest-path .* --registry crates-io/,
      "Native preflight must never upload to crates.io");
    assert.doesNotMatch(preflight, /action-gh-release|gh-action-pypi-publish/,
      "Preflight must never publish either registry or GitHub Release");

    assert.match(python, /needs: \[verify_release_ref, build_wheels, build_sdist, artifact_install, sdist_install, rust_preflight\]/,
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

    assert.match(rust, /needs: \[verify_release_ref, rust_preflight, publish\]/,
      "Rust publication must follow successful native preflight and PyPI");
    assert.match(rust, /environment: crates-io/);
    assert.match(rust, /id-token: write/);
    assert.match(rust, /vars\.QUPRS_CRATES_IO_PUBLISH_ENABLED == 'true'/);
    assert.match(rust, /scripts\/stage_rust_crate_candidate\.py/,
      "Rust publish must operate on isolated native crate");
    assert.match(rust, /test "\$\(git rev-parse HEAD\)" = "\$GITHUB_SHA"/,
      "Post-PyPI Rust release must verify the admitted immutable tag commit");
    assert.doesNotMatch(rust, /refs\/remotes\/origin\/main/,
      "A later main advancement must not cause a partially published release");
    assert.match(rust, /id: registry_state/,
      "Rust retry must inspect existing published archive");
    assert.match(rust, /already_published=true/);
    assert.match(rust, /already_published=false/);
    assert.match(rust, /https:\/\/crates\.io\/api\/v1\/crates\/quprs\/\$version/,
      "A retry must check the registry version record, not only a CDN archive");
    assert.match(rust, /python3 scripts\/verify_crates_io_registry_state\.py/,
      "A retry must run the independently tested registry SHA-256 verifier");
    assert.equal((rust.match(/if: steps\.registry_state\.outputs\.already_published == 'false'/g) || []).length, 2,
      "Publishing and token minting must be skipped for already published identical crates");
    assert.match(rust, /cargo package --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --locked/);
    assert.match(rust, /sha256sum -c SHA256SUMS/,
      "Rust publisher must validate the preflight package digest");
    assert.equal((rust.match(/sha256sum -c SHA256SUMS/g) || []).length, 2,
      "Rust archive identity must be validated both before and after upload");
    assert.match(rust, /rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.match(rust, /CARGO_REGISTRY_TOKEN: \$\{\{ steps\.crates_io_auth\.outputs\.token \}\}/);
    assert.match(rust, /cargo publish --manifest-path "\$RUNNER_TEMP\/quprs-crate\/Cargo\.toml" --registry crates-io --locked/);
    assert.match(rust, /\| tee "\$RUNNER_TEMP\/quprs-cargo-publish\.log" \|\| cargo_exit=\$\?/);
    assert.match(rust, /python3 scripts\/reconcile_crates_io_publish\.py/,
      "Post-upload confirmation must check the identical immutable registry archive");

    assert.match(release, /needs: \[verify_release_ref, rust_preflight, publish, publish_crates_io\]/,
      "GitHub Release must wait for successful publication to both registries");
    assert.match(release, /softprops\/action-gh-release@v2/);
    assert.match(release, /pattern: pypi-release-\*/);
    assert.match(release, /release-native-/);
    assert.match(release, /https:\/\/static\.crates\.io\/crates\/quprs\//);
    assert.match(release, /cmp "\$RUNNER_TEMP\/rust-dist\/\$crate" "\$RUNNER_TEMP\/registry-\$crate"/);
    assert.match(release, /SHA256SUMS.txt/);
    assert.match(release, /release-assets\/\*/);
    assert.match(release, /https:\/\/pypi\.org\/project\/QuPRS\//);
    assert.match(release, /https:\/\/crates\.io\/crates\/quprs\//);
  }
  checkDualReleasePolicy(publishYaml);
  // Recovery must remain Rust-only, source-locked, and linked to the original
  // tag-triggered run. This is a manual repair path, never a second release.
  function checkRustRecoveryPolicy(yaml) {
    const verifier = getJob(yaml, "verify_release_ref");
    const preflight = getJob(yaml, "rust_preflight");
    const rust = getJob(yaml, "publish_crates_io");
    const recovery = getJob(yaml, "recover_crates_io");
    const recoveredRelease = getJob(yaml, "recover_github_release");
    assert.match(verifier, /inputs\.recover_tag == ''/,
      "Manual recovery cannot enter the full Python build and publish matrix");
    assert.match(verifier, /Check crates\.io API from this runner without publishing/);
    assert.match(verifier, /--user-agent 'QuPRS-release\/1\.0/);
    for (const section of [preflight, rust, recovery]) {
      assert.match(section, /--user-agent 'QuPRS-release\/1\.0/,
        "Every prepublish metadata query must identify its client");
    }
    assert.match(preflight, /Verify crates\.io registry access before PyPI publication/);
    assert.match(recovery, /github\.event_name == 'workflow_dispatch'/);
    assert.match(recovery, /inputs\.recover_tag != ''/);
    assert.match(recovery, /environment: crates-io/);
    assert.match(recovery, /id-token: write/);
    assert.match(recovery, /actions: read/);
    assert.match(recovery, /SOURCE_RUN_ID: \$\{\{ inputs\.source_run_id \}\}/);
    assert.match(recovery, /CRATES_IO_PUBLISH_ENABLED" != "true"/);
    assert.match(recovery, /record\.get\("event"\) != "push"/);
    assert.match(recovery, /record\.get\("head_sha"\) != sys\.argv\[3\]/);
    assert.match(recovery, /record\.get\("path"\) != "\.github\/workflows\/python-publish\.yml"/);
    assert.match(recovery, /cat-file -t "refs\/tags\/\$RECOVERY_TAG"/);
    assert.match(recovery, /release-native-\$\{\{ steps\.source\.outputs\.tag_commit \}\}/);
    assert.match(recovery, /run-id: \$\{\{ inputs\.source_run_id \}\}/);
    assert.match(recovery, /sha256sum -c SHA256SUMS/);
    assert.equal((recovery.match(/cmp "\$RUNNER_TEMP\/recovery-native-assets\/quprs-\$version\.crate"/g) || []).length, 2,
      "Native archive must be compared both before and after cargo publish");
    assert.match(recovery, /python3 release-source\/scripts\/verify_crates_io_registry_state\.py/);
    assert.equal((recovery.match(/if: steps\.registry_state\.outputs\.already_published == 'false'/g) || []).length, 2);
    assert.match(recovery, /rust-lang\/crates-io-auth-action@[a-f0-9]{40}/);
    assert.match(recovery, /CARGO_REGISTRY_TOKEN: \$\{\{ steps\.crates_io_auth\.outputs\.token \}\}/);
    assert.match(recovery, /python3 scripts\/reconcile_crates_io_publish\.py/);
    assert.doesNotMatch(recovery, /gh-action-pypi-publish/,
      "Rust-only recovery must never upload to PyPI");
    assert.match(recoveredRelease, /needs: recover_crates_io/);
    assert.match(recoveredRelease, /contents: write/);
    assert.match(recoveredRelease, /pattern: pypi-release-\*/);
    assert.match(recoveredRelease, /run-id: \$\{\{ inputs\.source_run_id \}\}/);
    assert.match(recoveredRelease, /release-native-\$\{\{ needs\.recover_crates_io\.outputs\.tag_commit \}\}/);
    assert.match(recoveredRelease, /reconcile_pypi_artifacts\.py verify/);
    assert.match(recoveredRelease, /sha256sum -c SHA256SUMS/);
    assert.match(recoveredRelease, /cmp "\$RUNNER_TEMP\/rust-dist\/\$crate"/);
    assert.match(recoveredRelease, /refusing to overwrite/);
    assert.match(recoveredRelease, /tag_name: \$\{\{ inputs\.recover_tag \}\}/);
    assert.match(recoveredRelease, /softprops\/action-gh-release@v2/);
  }
  checkRustRecoveryPolicy(publishYaml);
  for (const [name, mutation] of [
    ["recovery ignores source-run provenance", x => x.replace(
      'record.get("head_sha") != sys.argv[3]', 'False')],
    ["recovery skips source archive identity", x => x.replace(
      'cmp "$RUNNER_TEMP/recovery-native-assets/quprs-$version.crate"', 'true #')],
    ["recovery uploads without official token", x => x.replace(
      /(  recover_crates_io:[\s\S]*?)CARGO_REGISTRY_TOKEN: \$\{\{ steps\.crates_io_auth\.outputs\.token \}\}/,
      "$1CARGO_REGISTRY_TOKEN: invalid")],
    ["recovery omits PyPI archive reconciliation", x => x.replace(
      'python3 release-source/scripts/reconcile_pypi_artifacts.py verify', 'echo unverified-pypi')],
    ["recovery permits GitHub Release overwrite", x => x.replace(
      'echo "::error::GitHub Release already exists; refusing to overwrite"', 'echo overwrite')],
  ]) {
    const changed = mutation(publishYaml);
    assert.notEqual(changed, publishYaml, "Mutation must change source: " + name);
    assert.throws(() => checkRustRecoveryPolicy(changed), undefined, name);
  }
  for (const [name, mutation] of [
    ["preflight accidentally dispatched", x => x.replace(
      /(  rust_preflight:[\s\S]*?github\.event_name == )'push'/,
      "$1'workflow_dispatch'")],
    ["preflight skips Rust dry-run", x => x.replace(
      'cargo publish --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --dry-run',
      'echo skipped-dry-run')],
    ["preflight does not materialize the Rust archive", x => x.replace(
      'cargo package --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --locked --no-verify',
      'echo missing-crate')],
    ["preflight skips crates.io OIDC", x => x.replace(
      /      - name: Verify crates\.io GitHub OIDC authorization without uploading\n        uses: rust-lang\/crates-io-auth-action@[a-f0-9]{40}/,
      "      - name: Verify crates.io GitHub OIDC authorization without uploading\n        run: true")],
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
    ["Rust publishes before PyPI", x => x.replace(
      "needs: [verify_release_ref, rust_preflight, publish]",
      "needs: [verify_release_ref, rust_preflight]")],
    ["Rust package digest is not checked", x => x.replace(
      "sha256sum -c SHA256SUMS", "echo skip-checksum")],
    ["Rust publishes workspace directly", x => x.replace(
      'cargo publish --manifest-path "$RUNNER_TEMP/quprs-crate/Cargo.toml" --registry crates-io',
      'cargo publish --manifest-path rust/Cargo.toml --registry crates-io')],
    ["Rust rechecks mutable main after successful PyPI upload", x => x.replace(
      'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
      'test "$(git rev-parse HEAD)" = "$(git rev-parse refs/remotes/origin/main)"')],
    ["Rust retry omits registry checksum verifier", x => x.replace(
      /(  publish_crates_io:[\s\S]*?)python3 scripts\/verify_crates_io_registry_state\.py/,
      "$1true")],
    ["Rust upload ignores post-publish registry confirmation", x => x.replace(
      "python3 scripts/reconcile_crates_io_publish.py", "true")],
    ["Rust retries duplicate publication", x => x.replace(
      "if: steps.registry_state.outputs.already_published == 'false'",
      "if: always()")],
    ["GitHub Release created before Rust publish", x => x.replace(
      "needs: [verify_release_ref, rust_preflight, publish, publish_crates_io]",
      "needs: [verify_release_ref, rust_preflight, publish]")],
    ["GitHub Release does not compare registry bytes", x => x.replace(
      'cmp "$RUNNER_TEMP/rust-dist/$crate" "$RUNNER_TEMP/registry-$crate"',
      "echo skip-archive-identity")],
    ["GitHub Release omits Rust registry link", x => x.replace(
      "https://crates.io/crates/quprs/", "https://example.invalid/crate/")],
  ]) {
    const changed = mutation(publishYaml);
    assert.notEqual(changed, publishYaml, "Mutation must change source: " + name);
    assert.throws(() => checkDualReleasePolicy(changed), undefined, name);
  }
  const registryVerifier = fs.readFileSync("scripts/verify_crates_io_registry_state.py", "utf8");
  function checkRegistryVerifier(source) {
    assert.match(source, /hashlib\.sha256\(Path\(crate_file\)\.read_bytes\(\)\)\.hexdigest\(\)/);
    assert.match(source, /record\.get\('checksum'\) != actual_checksum/,
      "Published crate checksum must be checked");
    assert.match(source, /record\.get\('yanked'\) is not False/,
      "Yanked registry versions cannot be accepted");
    assert.match(source, /record\.get\('num'\) != expected_version/,
      "Registry version must match the source tag");
  }
  checkRegistryVerifier(registryVerifier);
  for (const [name, mutation] of [
    ["Reject checksum bypass", s => s.replace("record.get('checksum') != actual_checksum", "False")],
    ["Reject yanked-version acceptance", s => s.replace("record.get('yanked') is not False", "False")],
    ["Reject version mismatch acceptance", s => s.replace("record.get('num') != expected_version", "False")]
  ]) {
    const mutated = mutation(registryVerifier);
    assert.notEqual(mutated, registryVerifier, "Mutation must change verifier: " + name);
    assert.throws(() => checkRegistryVerifier(mutated), undefined, name);
  }
  console.log("Dual-registry publication policy and registry verifier negative controls passed");
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
