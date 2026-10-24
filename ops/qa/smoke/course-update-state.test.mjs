import { test } from 'node:test';
import assert from 'node:assert/strict';
import { verifySnapshots } from './course-update-state.mjs';

const baseline = () => ({ refs: { EXAMPLES: 'baseline' }, learners: Object.fromEntries(
  ['RETURNING', 'SECOND'].map(key => [key, { courseId: 'course',
    assignments: [{ id: 'assignment', result: { id: 'grade', result: 1 } }],
    artifacts: [{ id: 'submission' }], repository: { id: 'repo' },
    files: { head: 'old', tracked_sha256: 'edited', untracked_sha256: 'untracked', readmes: { README: 'old' } }, workspaces: [{ id: 'workspace' }],
    deployments: [{ id: 'assignment', version: '1' }], text_sha256: 'old text',
  }])) });
function candidate(before) {
  const after = structuredClone(before);
  after.refs.EXAMPLES = 'candidate';
  for (const learner of Object.values(after.learners)) {
    learner.deployments[0].version = '2';
    learner.text_sha256 = 'updated text';
    learner.files.head = 'new';
    learner.files.readmes.README = 'new';
  }
  return after;
}
test('real update preserves both learner states', () => {
  const before = baseline();
  verifySnapshots(before, candidate(before));
});
test('rejects same revision, unchanged deployment, and unchanged learner text', () => {
  const before = baseline();
  for (const change of [a => { a.refs.EXAMPLES = before.refs.EXAMPLES; },
    a => { a.learners.SECOND.deployments = before.learners.SECOND.deployments; },
    a => { a.learners.RETURNING.text_sha256 = before.learners.RETURNING.text_sha256; }]) {
    const after = candidate(before);
    change(after);
    assert.throws(() => verifySnapshots(before, after));
  }
});
test('rejects lost grades, submissions, repositories and workspaces', () => {
  const before = baseline();
  for (const field of ['assignments', 'artifacts', 'repository', 'workspaces']) {
    const after = candidate(before);
    after.learners.SECOND[field] = [];
    assert.throws(() => verifySnapshots(before, after));
  }
});
test('rejects overwritten learner files and stale workspace README', () => {
  const before = baseline();
  for (const field of ['tracked_sha256', 'untracked_sha256']) {
    const after = candidate(before);
    after.learners.RETURNING.files[field] = 'overwritten';
    assert.throws(() => verifySnapshots(before, after));
  }
  const after = candidate(before);
  after.learners.SECOND.files.readmes = before.learners.SECOND.files.readmes;
  assert.throws(() => verifySnapshots(before, after));
});
