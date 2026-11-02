'use strict';
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
        if (diff.files.some(f => !/^(?:docs\/.*\.md|README\.md|CHANGELOG\.md|CONTRIBUTING\.md|\.github\/ISSUE_TEMPLATE\/.*\.md)$/.test(f.filename || '') ||
          (f.previous_filename && !/^(?:docs\/.*\.md|README\.md|CHANGELOG\.md|CONTRIBUTING\.md|\.github\/ISSUE_TEMPLATE\/.*\.md)$/.test(f.previous_filename)))) continue;
      }
      const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {
        owner, repo, run_id: candidate.id, filter: 'latest', per_page: 100
      });
      if (!Array.isArray(jobs)) continue;
      const matches = requiredJobs.every(rule => {
        const items = jobs.filter(job => job.name === rule.name || (rule.prefix && job.name.startsWith(rule.prefix)));
        return items.length === rule.count && items.every(job => job.status === 'completed' && job.conclusion === 'success');
      });
      if (matches) return result(false, 'Only safe documentation differs from a completed, same-base, same-PR full successful workflow.', candidate);
    }
    return result(true, 'No same-base, same-PR completed SUCCESS run with matching required jobs and documentation-only source difference.');
  } catch (error) {
    core.warning(`Evidence resolution failed closed: ${error.message || error}`);
    return result(true, 'GitHub evidence query unavailable; fail-closed.');
  }
};
