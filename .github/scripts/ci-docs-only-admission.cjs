'use strict';

// First-run PR admission for expensive native and Docker CI, not a reuse of
// earlier jobs. Only verified whole-line Rustdoc and explicit prose qualifies.
const {isRustDocOnlyChange} = require('./codspeed-pr-impact.cjs');
const sha = value => typeof value === 'string' && /^[0-9a-f]{40}$/.test(value) &&
  value !== '0'.repeat(40);
const prose = /^(?:README\.md|CHANGELOG\.md|CONTRIBUTING\.md|docs\/[a-zA-Z0-9_./-]+\.md|\.github\/ISSUE_TEMPLATE\/[a-zA-Z0-9_./-]+\.md)$/;

module.exports = async function docsOnlyAdmission({github, context, baseBranches}) {
  const run = reason => ({run: true, reason});
  const skip = reason => ({run: false, reason});
  // Preserve release/tag push and manual workflow_dispatch behavior.
  if (context?.eventName !== 'pull_request')
    return run('Non-PR event: existing release/manual behavior.');
  const pr = context.payload?.pull_request, {owner, repo} = context.repo || {};
  const allowed = Array.isArray(baseBranches) && baseBranches.length > 0 &&
    baseBranches.every(name => name === 'dev' || name === 'main');
  if (!allowed || !owner || !repo || !pr ||
      !['opened','synchronize','reopened','edited','ready_for_review'].includes(context.payload.action) ||
      !baseBranches.includes(pr.base?.ref) ||
      pr.head?.repo?.full_name !== owner + '/' + repo ||
      pr.base?.repo?.full_name !== owner + '/' + repo ||
      !sha(pr.base?.sha) || !sha(pr.head?.sha) ||
      pr.base.sha === pr.head.sha ||
      !Number.isInteger(pr.number) || pr.number < 1 ||
      !Number.isInteger(pr.changed_files) || pr.changed_files < 1 || pr.changed_files > 100)
    return run('Unverifiable PR identity, refs or bounded file-count metadata.');

  try {
    const files = await github.paginate(github.rest.pulls.listFiles, {
      owner, repo, pull_number:pr.number, per_page:100
    });
    if (!Array.isArray(files) || files.length !== pr.changed_files)
      return run('Incomplete GitHub changed-file listing.');
    const fullSource = async (path, ref) => {
      const response = await github.rest.repos.getContent({owner, repo, path, ref});
      const f = response?.data;
      if (!f || Array.isArray(f) || f.type !== 'file' ||
          f.encoding !== 'base64' || typeof f.content !== 'string' ||
          !Number.isInteger(f.size) || f.size < 0 || f.size > 150000)
        throw new Error('Unverifiable complete Rust source: ' + path);
      const bytes = Buffer.from(f.content.replace(/\s/g,''), 'base64');
      if (bytes.length !== f.size)
        throw new Error('Incorrect complete source byte length: ' + path);
      const decoded = bytes.toString('utf8');
      if (!bytes.equals(Buffer.from(decoded,'utf8')))
        throw new Error('Invalid source UTF-8: ' + path);
      return decoded;
    };
    let rustdoc = 0;
    const seen = new Set();
    for (const f of files) {
      const path = f?.filename;
      if (typeof path !== 'string' || !path || seen.has(path) ||
          f.status !== 'modified' || f.previous_filename)
        return run('Unknown, removed or renamed PR source.');
      seen.add(path);
      if (/^rust\/[a-zA-Z0-9_./-]+\.rs$/.test(path)) {
        const before = await fullSource(path,pr.base.sha);
        const after = await fullSource(path,pr.head.sha);
        if (!isRustDocOnlyChange(before,after))
          return run('Executable Rust change or unverified Rustdoc: ' + path);
        rustdoc++;
      } else if (!prose.test(path)) {
        // In particular, rust/**/*.md is not automatically safe:
        // build scripts or published packages may consume Rust tree files.
        return run('Non-documentation or untrusted source: ' + path);
      }
    }
    return skip('Verified initial documentation-only PR at exact base/head SHAs (' +
      rustdoc + ' Rustdoc files); skip expensive native/Docker test jobs.');
  } catch (error) {
    return run('Documentation evidence unavailable; fail closed: ' +
      (error?.message || String(error)));
  }
};
