'use strict';

// Conservative post-merge Pytest source gate. Unlike CodSpeed, changes to
// arbitrary test/**, fixtures, build scripts and metadata are NEVER ignored.
// Only changed full-file Rustdoc lines in Rust source may skip the 12-slot
// push matrix. Reusable and manual callers always run their full matrix.
const {isRustDocOnlyChange} = require('./codspeed-pr-impact.cjs');
const validSHA = s => typeof s === 'string' && /^[0-9a-f]{40}$/.test(s) &&
  s !== '0'.repeat(40);

module.exports = async function decidePytestPush({github, context, forceFullMatrix = false}) {
  const run = reason => ({run: true, reason});
  const skip = reason => ({run: false, reason});
  if (forceFullMatrix) return run('Reusable workflow call requires the full matrix.');
  if (context?.eventName !== 'push')
    return run('Non-push/manual event requires the full matrix.');
  const p = context.payload;
  const {owner, repo} = context.repo || {};
  const ref = context.ref;
  if (!owner || !repo || !p || !['refs/heads/main','refs/heads/dev'].includes(ref) ||
      p.ref !== ref || p.repository?.full_name !== owner + '/' + repo)
    return run('Unverifiable push branch or repository.');
  const before=p.before, after=p.after;
  if (!validSHA(before) || !validSHA(after) || before === after ||
      context.sha !== after ||
      p.created !== false || p.deleted !== false || p.forced !== false)
    return run('Missing, forced, initial, deleted or inconsistent push SHAs.');

  try {
    const response=await github.rest.repos.compareCommits({
      owner, repo, base:before, head:after, per_page:100
    });
    const d=response?.data;
    if (!d || d.status !== 'ahead' || d.behind_by !== 0 ||
        d.base_commit?.sha !== before ||
        !Number.isInteger(d.total_commits) || d.total_commits < 1 ||
        d.total_commits > 100 || d.ahead_by !== d.total_commits ||
        !Array.isArray(d.commits) || d.commits.length !== d.total_commits ||
        d.commits[d.commits.length - 1]?.sha !== after ||
        !Array.isArray(d.files) || d.files.length < 1 || d.files.length >= 300)
      return run('Incomplete, divergent, oversized or untrusted compare evidence.');
    const seen=new Set();
    for (const f of d.files) {
      const path=f?.filename;
      if (typeof path !== 'string' || !path || seen.has(path) ||
          f.status !== 'modified' || f.previous_filename)
        return run('Unknown file status, duplicate or rename in push.');
      seen.add(path);
      if (!/^rust\/[A-Za-z0-9_./-]+\.rs$/.test(path))
        return run('Non-Rustdoc or build/test/fixture input changed: ' + path);
      const load=async ref => {
        const result=await github.rest.repos.getContent({owner,repo,path,ref});
        const file=result?.data;
        if (!file || Array.isArray(file) || file.type !== 'file' ||
            file.encoding !== 'base64' || typeof file.content !== 'string' ||
            !Number.isInteger(file.size) || file.size < 0 || file.size > 150000)
          throw new Error('Unverifiable full Rust file: '+path);
        const bytes=Buffer.from(file.content.replace(/\s/g,''),'base64');
        if (bytes.length !== file.size)
          throw new Error('Incorrect Rust file size: '+path);
        const value=bytes.toString('utf8');
        if (!bytes.equals(Buffer.from(value,'utf8')))
          throw new Error('Invalid Rust UTF-8: '+path);
        return value;
      };
      if (!isRustDocOnlyChange(await load(before), await load(after)))
        return run('Non-Rustdoc source difference: ' + path);
    }
    return skip('Verified Rustdoc-only push using exact commit and complete file content (' +
      before.slice(0,12) + ' -> ' + after.slice(0,12) +
      '); omit 12-platform Pytest while Rust API documentation remains enabled.');
  } catch (error) {
    return run('Pytest source comparison unavailable; fail closed: ' +
      (error?.message || String(error)));
  }
};
