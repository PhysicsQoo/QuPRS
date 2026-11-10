'use strict';

// Keep the fast documentation source checks. Avoid a second full Zensical
// render only when Rust API Docs is independently scheduled for this source.
const fs = require('node:fs');
const { execFileSync } = require('node:child_process');
const SHA = /^[0-9a-f]{40}$/;
const YAML_PATH = '.github/workflows/rust-api-docs.yml';

function workflowPaths(source, eventName) {
  const body = source.split(`\n  ${eventName}:\n`)[1];
  if (!body) throw new Error('Missing documentation event trigger');
  const eventBody = body.split(/\n  [a-z][a-z_-]*:\n/)[0];
  const marker = '    paths:\n';
  const start = eventBody.indexOf(marker);
  if (start < 0) throw new Error('Missing documentation paths filter');
  const lines = eventBody.slice(start + marker.length).split('\n');
  const paths = [];
  for (const line of lines) {
    if (!line) continue;
    const match = /^      - '([^']+)'$/.exec(line);
    if (!match) {
      if (line.startsWith('    ') || line.trim().startsWith('-')) {
        throw new Error('Unexpected path filter syntax');
      }
      break;
    }
    const pattern = match[1];
    if (!/^[A-Za-z0-9_.\/-]+(?:\/\*\*)?$/.test(pattern) ||
        pattern.startsWith('!')) throw new Error('Unsupported path filter');
    paths.push(pattern);
  }
  if (!paths.length) throw new Error('Empty path filter');
  return paths;
}

function matchesPath(path, pattern) {
  if (pattern.endsWith('/**')) return path.startsWith(pattern.slice(0, -2));
  return path === pattern;
}

// The PR check-out defaults to GitHub's synthetic merge commit, while the
// Rustdoc lane explicitly tests the PR head. Do not reuse rendered-site
// evidence if these Git trees differ (e.g. an out-of-date PR base).
function sameSiteSourceTree(headSha) {
  const getTree = ref => execFileSync('git', ['rev-parse', `${ref}^{tree}`],
    {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim();
  return getTree('HEAD') === getTree(headSha);
}

const fallback = reason => ({buildSite: true, reason});

async function decide({github, context, readYaml = () => fs.readFileSync(YAML_PATH, 'utf8'),
                       treeMatches = sameSiteSourceTree}) {
  try {
    const event = context.eventName;
    if (!['pull_request', 'push'].includes(event)) {
      return fallback('Manual or unsupported event: retain strict site build.');
    }
    const {owner, repo} = context.repo;
    if (!owner || !repo) return fallback('Missing repository identity.');
    let files;
    if (event === 'pull_request') {
      const pull = context.payload?.pull_request;
      if (!pull || !['opened', 'reopened', 'synchronize'].includes(context.payload.action) ||
          pull.base?.ref !== 'dev' || pull.head?.repo?.full_name !== `${owner}/${repo}` ||
          !SHA.test(pull.head?.sha || '') || !Number.isSafeInteger(pull.number)) {
        return fallback('Unverifiable PR event or source.');
      }
      files = await github.paginate(github.rest.pulls.listFiles, {
        owner, repo, pull_number: pull.number, per_page: 100
      });
    } else {
      const before = context.payload?.before;
      const head = context.sha;
      if (context.ref !== 'refs/heads/dev' || !SHA.test(before || '') ||
          /^0{40}$/.test(before) || !SHA.test(head || '')) {
        return fallback('Unverifiable dev push.');
      }
      const response = await github.rest.repos.compareCommits({
        owner, repo, base: before, head
      });
      if (response.data?.status !== 'ahead' || response.data?.behind_by !== 0) {
        return fallback('Non-forward or unverifiable push comparison.');
      }
      files = response.data?.files;
    }
    // GitHub's workflow path-filtering may inspect only the first 300 files.
    // A truncated or ambiguous list must never authorize skipping a build.
    if (!Array.isArray(files) || files.length === 0 || files.length >= 300 ||
        files.some(f => !f || typeof f.filename !== 'string' ||
          f.status === 'renamed')) {
      return fallback('Incomplete, oversized or ambiguous changed-file set.');
    }
    const paths = workflowPaths(readYaml(), event);
    if (!files.some(f => paths.some(p => matchesPath(f.filename, p)))) {
      return fallback('No matching Rust API docs trigger: retain strict site build.');
    }
    if (event === 'pull_request' && !treeMatches(context.payload.pull_request.head.sha)) {
      return fallback('PR merge site differs from Rust API docs head: rebuild site.');
    }
    return {buildSite: false, reason:
      'The source-matched Rust API docs lane owns strict site rendering; keep source and negative checks here.'};
  } catch (error) {
    return fallback(`Site ownership could not be verified: ${error.message}`);
  }
}

module.exports = decide;
module.exports.workflowPaths = workflowPaths;
module.exports.matchesPath = matchesPath;
module.exports.sameSiteSourceTree = sameSiteSourceTree;
