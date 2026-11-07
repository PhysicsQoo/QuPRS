'use strict';
// QOO-106: strictly classify release-version-only input changes.
// Any missing source, unknown package stanza or dependency diff fails closed.
const VERSION_PATHS = new Set(['rust/Cargo.toml','rust/Cargo.lock','src/QuPRS/_version.py']);
const INTERNAL_CRATES = new Set(['QuPRS_cli','quprs','quprs_python']);
const SEMVER = /^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

function canonicalVersion(path, source) {
  if (!VERSION_PATHS.has(path) || typeof source !== 'string' ||
      !source.length || source.length > 150000) return null;
  if (path === 'rust/Cargo.toml') {
    const headers = [...source.matchAll(/^\[workspace\.package\]\r?$/gm)];
    if (headers.length !== 1) return null;
    const start = headers[0].index + headers[0][0].length;
    const next = source.indexOf('\n[', start);
    const end = next === -1 ? source.length : next;
    const block = source.slice(start, end);
    const match = [...block.matchAll(/^version = "([^"\r\n]+)"\r?$/gm)];
    if (match.length !== 1 || !SEMVER.test(match[0][1])) return null;
    const normalized = source.slice(0, start) +
      block.replace(/^version = "[^"\r\n]+"(\r?)$/m, 'version = "<release-version>"$1') +
      source.slice(end);
    return {normalized, version: match[0][1]};
  }
  if (path === 'src/QuPRS/_version.py') {
    const matches = [...source.matchAll(/^__version__ = "([^"\r\n]+)"\r?$/gm)];
    if (matches.length !== 1 || !SEMVER.test(matches[0][1])) return null;
    return {
      normalized: source.replace(
        /^__version__ = "[^"\r\n]+"(\r?)$/m, '__version__ = "<release-version>"$1'
      ),
      version: matches[0][1],
    };
  }
  // Canonicalize complete Cargo.lock blocks, not untrusted truncated PR patches.
  const positions = [...source.matchAll(/^\[\[package\]\]\r?$/gm)];
  if (positions.length < INTERNAL_CRATES.size) return null;
  const found = new Map();
  let normalized = source.slice(0, positions[0].index);
  for (let i = 0; i < positions.length; i++) {
    const start = positions[i].index;
    const end = i+1 < positions.length ? positions[i+1].index : source.length;
    let block = source.slice(start, end);
    const names = [...block.matchAll(/^name = "([^"\r\n]+)"\r?$/gm)];
    if (names.length !== 1) return null;
    const name = names[0][1];
    if (INTERNAL_CRATES.has(name)) {
      const match = [...block.matchAll(/^version = "([^"\r\n]+)"\r?$/gm)];
      if (found.has(name) || match.length !== 1 || !SEMVER.test(match[0][1]) ||
          /^\s*(?:source|checksum)\s*=/m.test(block)) return null;
      found.set(name, match[0][1]);
      block = block.replace(
        /^version = "[^"\r\n]+"(\r?)$/m, 'version = "<release-version>"$1'
      );
    }
    normalized += block;
  }
  if (found.size !== INTERNAL_CRATES.size || new Set(found.values()).size !== 1) return null;
  return {normalized, version: [...found.values()][0]};
}

function isVersionOnlyChange(path, before, after) {
  if (!VERSION_PATHS.has(path)) return null;
  const b = canonicalVersion(path, before), h = canonicalVersion(path, after);
  return b && h && b.version !== h.version && b.normalized === h.normalized
    ? {before:b.version, after:h.version} : null;
}
module.exports = {VERSION_PATHS, canonicalVersion, isVersionOnlyChange};
