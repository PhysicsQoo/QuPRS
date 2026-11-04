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
]);
function isPerformanceBearingPath(path) {
  if (typeof path !== 'string' || !path) return false;
  if (direct.has(path)) return true;
  if (/^(?:src|rust|benchmarks)\//.test(path)) return true;
  if (/^test\/(?:_?benchmark_.*|test_benchmark_.*)\.py$/.test(path)) return true;
  if (/^scripts\/.*(?:codspeed|benchmark|paper_corpus|solver_walltime|performance|profil).*/.test(path)) return true;
  return false;
}
module.exports = {isPerformanceBearingPath};
