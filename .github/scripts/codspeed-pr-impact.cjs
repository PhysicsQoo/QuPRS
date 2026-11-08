'use strict';

// A PR must change an actual measured source, solver, fixture or benchmark
// instrumentation input to spend the regular CodSpeed runner budget.
// This is intentionally broader than a single microbenchmark's import graph;
// unfamiliar paths fail open at the API stage, not by guessing source semantics.
const direct = new Set([
  'GPMC', '.gitmodules', 'pyproject.toml',
  'test/test_Feynman.py', 'test/test_MQT.py', 'test/conftest.py',
  'test/test_codspeed_qasm261_simulation_additive.py',
  '.github/workflows/codspeed.yml',
  '.github/scripts/codspeed-pr-impact.cjs',
  '.github/scripts/codspeed-metadata-only.cjs',
  '.github/scripts/ci-impact-reuse.cjs',
]);
function isPerformanceBearingPath(path) {
  if (typeof path !== 'string' || !path) return false;
  if (direct.has(path)) return true;
  if (path.startsWith('rust/') && path.endsWith('.md')) return false;
  if (/^(?:src|rust|benchmarks)\//.test(path)) return true;
  if (/^test\/(?:_?benchmark_.*|test_benchmark_.*)\.py$/.test(path)) return true;
  if (/^scripts\/.*(?:codspeed|benchmark|paper_corpus|solver_walltime|performance|profil).*/.test(path)) return true;
  return false;
}

// Compare only Rustdoc comments that occupy a whole source line. A stateful
// lexer keeps comment-looking text inside raw strings, strings, chars and
// nested block comments intact. Unknown or unbalanced input fails closed.
// In particular, stripping comments globally or comparing GitHub diff hunks
// is not sufficient evidence for skipping a performance measurement.
function rustWithoutDocLines(source) {
  if (typeof source !== 'string' || source.length > 150000 || source.includes('\0')) return null;
  const lines = source.match(/[^\n]*\n|[^\n]+$/g) || [];
  let code = '', docs = 0, mode = 'code', depth = 0, hashes = 0;
  for (const line of lines) {
    if (mode === 'code' && /^[ \t]*\/\/(?:\/(?!\/)|!)/.test(line)) {
      docs++;
      continue;
    }
    code += line;
    for (let i = 0; i < line.length;) {
      if (mode === 'block') {
        if (line.startsWith('/*', i)) { depth++; i += 2; continue; }
        if (line.startsWith('*/', i)) {
          depth--;
          i += 2;
          if (depth === 0) mode = 'code';
          continue;
        }
        i++;
        continue;
      }
      if (mode === 'raw') {
        const closing = '"' + '#'.repeat(hashes);
        if (line.startsWith(closing, i)) {
          i += closing.length;
          mode = 'code';
        } else i++;
        continue;
      }
      if (mode === 'string') {
        if (line[i] === '\\') { i += 2; continue; }
        if (line[i] === '"') mode = 'code';
        i++;
        continue;
      }
      if (line.startsWith('//', i)) break;
      if (line.startsWith('/*', i)) {
        mode = 'block';
        depth = 1;
        i += 2;
        continue;
      }
      const raw = /^(?:b|c)?r(#{0,255})"/.exec(line.slice(i));
      if (raw && (i === 0 || !/[a-zA-Z0-9_]/.test(line[i - 1]))) {
        mode = 'raw';
        hashes = raw[1].length;
        i += raw[0].length;
        continue;
      }
      if (line[i] === '"') { mode = 'string'; i++; continue; }
      if (line[i] === "'") {
        // A character literal has a closing quote. Rust lifetimes such as
        // 'a and 'static deliberately do not match this expression.
        const character = /^'(?:\\(?:[nrt0'"\\]|x[0-7][0-9a-fA-F]|u\{[0-9a-fA-F_]+\})|[^'\\\r\n])'/u.exec(line.slice(i));
        if (character) { i += character[0].length; continue; }
      }
      i++;
    }
  }
  if (mode !== 'code' || depth !== 0) return null;
  return {code, docs};
}
function isRustDocOnlyChange(before, after) {
  if (before === after) return false;
  const left = rustWithoutDocLines(before);
  const right = rustWithoutDocLines(after);
  return Boolean(left && right && (left.docs || right.docs) && left.code === right.code);
}


// On pushes, compare the exact before/after commits. GitHub compare has
// bounded file/commit pages; incomplete evidence is always RUN, never SKIP.
// Manual dispatch and PR source decisions remain separate policies.
async function assessPushSourceImpact({github, context}) {
  const run = reason => ({run: true, reason});
  const skip = reason => ({run: false, reason});
  const valid = sha => typeof sha === 'string' && /^[0-9a-f]{40}$/.test(sha) &&
    sha !== '0'.repeat(40);
  if (!context || context.eventName !== 'push') return run('Not a push event.');
  const payload = context.payload;
  const {owner, repo} = context.repo || {};
  if (!owner || !repo || !payload || !['refs/heads/dev', 'refs/heads/main'].includes(context.ref) ||
      payload.ref !== context.ref || (payload.repository &&
      payload.repository.full_name !== owner + '/' + repo)) return run('Untrusted push branch or repository metadata.');
  const before = payload.before, after = payload.after;
  if (!valid(before) || !valid(after) || before === after || context.sha !== after ||
      payload.created !== false || payload.deleted !== false ||
      payload.forced !== false) return run('Missing, forced, created, deleted or non-contiguous push evidence.');
  try {
    const response = await github.rest.repos.compareCommits({
      owner, repo, base: before, head: after, per_page: 100
    });
    const diff = response && response.data;
    if (!diff || diff.status !== 'ahead' || diff.behind_by !== 0 ||
        diff.base_commit?.sha !== before ||
        !Number.isInteger(diff.total_commits) || diff.total_commits < 1 ||
        diff.total_commits > 100 || diff.ahead_by !== diff.total_commits ||
        !Array.isArray(diff.commits) || diff.commits.length !== diff.total_commits ||
        diff.commits[diff.commits.length - 1]?.sha !== after ||
        !Array.isArray(diff.files) || diff.files.length === 0 ||
        diff.files.length >= 300) return run('Unverifiable or truncated push ancestry/commit/file comparison.');
    const {VERSION_PATHS, isVersionOnlyChange} = require('./codspeed-metadata-only.cjs');
    const load = async (path, ref) => {
      const content = await github.rest.repos.getContent({owner, repo, path, ref});
      const file = content && content.data;
      if (!file || Array.isArray(file) || file.type !== 'file' ||
          file.encoding !== 'base64' || typeof file.content !== 'string' ||
          !Number.isInteger(file.size) || file.size > 150000) throw new Error('Invalid full source file: ' + path);
      const value = Buffer.from(file.content.replace(/\s/g, ''), 'base64');
      if (value.length !== file.size) throw new Error('Incorrect source size: ' + path);
      return value.toString('utf8');
    };
    let versions = [];
    const seen = new Set();
    for (const f of diff.files) {
      const path = f.filename;
      if (typeof path !== 'string' || !path || seen.has(path) ||
          !['added', 'modified', 'removed', 'renamed'].includes(f.status))
        return run('Unknown/duplicate push file metadata.');
      seen.add(path);
      // A renamed file may have moved out of a performance-bearing path.
      if (!isPerformanceBearingPath(path) &&
          !(f.previous_filename && isPerformanceBearingPath(f.previous_filename))) continue;
      if (f.status !== 'modified' || f.previous_filename)
        return run('Changed performance-bearing file status: ' + path);
      if (path.startsWith('rust/') && path.endsWith('.rs')) {
        if (isRustDocOnlyChange(await load(path, before), await load(path, after))) continue;
        return run('Rust executable change or unverified Rustdoc: ' + path);
      }
      if (VERSION_PATHS.has(path)) {
        const version = isVersionOnlyChange(path, await load(path, before),
          await load(path, after));
        if (!version) return run('Non-release-only metadata change: ' + path);
        versions.push(version);
        continue;
      }
      return run('Performance-bearing push change: ' + path);
    }
    if (versions.length && !versions.every(v =>
      v.before === versions[0].before && v.after === versions[0].after))
      return run('Inconsistent version-only metadata on push.');
    return skip('Verified source-irrelevant push from ' + before.slice(0, 12) +
      ' to ' + after.slice(0, 12) + '; no new performance measurement.');
  } catch (error) {
    return run('Push source evidence unavailable; fail closed: ' +
      (error?.message || String(error)));
  }
}

module.exports = {isPerformanceBearingPath, isRustDocOnlyChange, assessPushSourceImpact};
