import assert from 'node:assert/strict';

export function verifySnapshots(before, after) {
  assert.notEqual(before.refs.EXAMPLES, after.refs.EXAMPLES, 'candidate examples must differ from baseline');
  for (const key of ['RETURNING', 'SECOND']) {
    const a = before.learners[key], b = after.learners[key];
    assert.ok(a && b, `${key}: both snapshots required`);
    for (const field of ['courseId', 'assignments', 'artifacts', 'repository', 'workspaces']) {
      assert.deepEqual(b[field], a[field], `${key}: ${field} must persist exactly`);
    }
    for (const field of ['tracked_sha256', 'untracked_sha256']) {
      assert.equal(b.files?.[field], a.files?.[field], `${key}: learner ${field} must survive`);
      assert.ok(b.files?.[field], `${key}: file preservation evidence required`);
    }
    assert.notDeepEqual(b.files.readmes, a.files.readmes, `${key}: README files must update after Refresh`);
    assert.notEqual(b.files.head, a.files.head, `${key}: repository revision must change`);
    assert.notDeepEqual(b.deployments, a.deployments, `${key}: deployed revision must change`);
    assert.notEqual(b.text_sha256, a.text_sha256, `${key}: learner assignment text must change`);
  }
}

