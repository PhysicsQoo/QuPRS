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
]);
function isPerformanceBearingPath(path) {
  if (typeof path !== 'string' || !path) return false;
  if (direct.has(path)) return true;
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
      const raw = /^(?:b|c)?r(#{0,32})"/.exec(line.slice(i));
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

module.exports = {isPerformanceBearingPath, isRustDocOnlyChange};
