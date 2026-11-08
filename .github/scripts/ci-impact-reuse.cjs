'use strict';
const {isRustDocOnlyChange} = require('./codspeed-pr-impact.cjs');
module.exports = async function resolver({ github, context, core, workflowFile, requiredJobs, baseBranch = 'dev' }) {
  const result = async (runHeavy, reason, evidence) => {
    core.setOutput('run_heavy', String(runHeavy));
    core.setOutput('reason', reason);
    core.setOutput('reused_run_id', evidence ? String(evidence.id) : '');
    core.setOutput('measured_head_sha', evidence ? evidence.head_sha : '');
    core.info(`CI impact ${runHeavy ? 'RUN' : 'REUSE'}: ${reason}`);
    if (core.summary) {
      core.summary.addRaw(`### Incremental CI impact: ${runHeavy ? 'RUN' : 'REUSE'}\n\n${reason}\n\n`);
      if (evidence) core.summary.addRaw(`Previous successful evidence: run ${evidence.id}, measured SHA \`${evidence.head_sha}\`. This is **not** a new measurement on the current SHA.\n`);
      await core.summary.write();
    }
    return { runHeavy, reason, evidence };
  };
  if (context.eventName !== 'pull_request') return result(true, 'Non-PR event: existing workflow behavior.');
  const pull = context.payload && context.payload.pull_request;
  const act = context.payload && context.payload.action;
  if (!pull || !pull.head || !pull.base || pull.base.ref !== baseBranch) return result(true, 'Missing/unsupported PR metadata or non-dev base.');
  if (!['synchronize', 'edited', 'reopened', 'ready_for_review'].includes(act)) return result(true, `PR ${act || 'unknown'} requires fresh validation.`);
  const { owner, repo } = context.repo;
  if (pull.head.repo?.full_name !== `${owner}/${repo}`) return result(true, 'Fork PR: fail-closed; no evidence reuse.');
  if (!/^[0-9a-f]{40}$/.test(pull.head.sha || '') || !/^[0-9a-f]{40}$/.test(pull.base.sha || '')) return result(true, 'Invalid current SHA metadata.');
  try {
    const response = await github.rest.actions.listWorkflowRuns({
      owner, repo, workflow_id: workflowFile,
      event: 'pull_request', branch: pull.head.ref, per_page: 100
    });
    const runs = response.data && response.data.workflow_runs;
    if (!Array.isArray(runs)) return result(true, 'No trusted workflow run list.');
    for (const candidate of runs) {
      if (candidate.id === context.runId || candidate.conclusion !== 'success' || candidate.status !== 'completed') continue;
      if (!/^[0-9a-f]{40}$/.test(candidate.head_sha || '')) continue;
      const linked = (candidate.pull_requests || []).some(p =>
        p.number === pull.number &&
        p.head?.repo?.id === pull.head.repo?.id &&
        p.base?.sha === pull.base.sha &&
        p.base?.ref === pull.base.ref
      );
      if (!linked) continue;
      if (candidate.head_sha !== pull.head.sha) {
        const comparison = await github.rest.repos.compareCommits({
          owner, repo, base: candidate.head_sha, head: pull.head.sha
        });
        const diff = comparison.data;
        if (diff.status !== 'ahead' || diff.behind_by !== 0 || !Array.isArray(diff.files) || diff.files.length >= 300) continue;
        // Independent workflow files do not alter this lane's program/fixtures.
        // Own workflows, transitive reusable-workflow inputs and shared CI
        // logic must invalidate previous evidence and run normally.
        const documentation = /^(?:docs\/.*\.md|README\.md|CHANGELOG\.md|CONTRIBUTING\.md|\.github\/ISSUE_TEMPLATE\/.*\.md)$/;
        const workflowSource = /^\.github\/workflows\/([a-zA-Z0-9_-]+\.ya?ml)$/;
        const indirect = workflowFile === 'native-cross-platform-pr.yml' ? ['pytest.yml'] : [];
        const loadSource = async (path, ref) => {
          const response = await github.rest.repos.getContent({owner, repo, path, ref});
          const file = response.data;
          if (!file || Array.isArray(file) || file.type !== 'file' ||
              file.encoding !== 'base64' || typeof file.content !== 'string' ||
              file.size > 150000) throw new Error('Unverifiable Rustdoc input');
          return Buffer.from(file.content, 'base64').toString('utf8');
        };
        const isUnrelated = async f => {
          if (f.status !== 'modified' || f.previous_filename) return false;
          const path = f.filename || '';
          if (documentation.test(path)) return true;
          const match = workflowSource.exec(path);
          if (match) return match[1] !== workflowFile && !indirect.includes(match[1]);
          if (workflowFile !== 'codspeed.yml' || !/^rust\/.*\.rs$/.test(path)) return false;
          const before = await loadSource(path, candidate.head_sha);
          const after = await loadSource(path, pull.head.sha);
          return isRustDocOnlyChange(before, after);
        };
        let sourceChanged = false;
        for (const file of diff.files) {
          if (!await isUnrelated(file)) { sourceChanged = true; break; }
        }
        if (sourceChanged) continue;
      }
      const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {
        owner, repo, run_id: candidate.id, filter: 'latest', per_page: 100
      });
      if (!Array.isArray(jobs)) continue;
      const matches = requiredJobs.every(rule => {
        const items = jobs.filter(job => job.name === rule.name || (rule.prefix && job.name.startsWith(rule.prefix)));
        return items.length === rule.count && items.every(job => job.status === 'completed' && job.conclusion === 'success');
      });
      if (matches) return result(false, 'Only source-irrelevant paths differ from a completed, same-base, same-PR successful workflow.', candidate);
    }
    return result(true, 'No same-base, same-PR completed SUCCESS run with matching required jobs and source-irrelevant differences.');
  } catch (error) {
    core.warning(`Evidence resolution failed closed: ${error.message || error}`);
    return result(true, 'GitHub evidence query unavailable; fail-closed.');
  }
};
