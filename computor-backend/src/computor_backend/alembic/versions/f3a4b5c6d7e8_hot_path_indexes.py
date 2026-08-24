"""Index the join columns the read paths actually use

``submission_group`` carried nothing but its primary key, and it is joined on
``course_content_id`` in every student, tutor and lecturer content read — so
every one of those reads was a sequential scan over the whole table. The rest
of the list is the same story in smaller print: a foreign key that a hot query
filters on, with no index able to serve it.

``submission_group_member`` is the sharpest case: its unique index is
``(submission_group_id, course_member_id)``, which cannot answer "which groups
is this member in" — the most common student lookup of all. That foreign key is
also ON DELETE RESTRICT, so removing a course member scanned the whole table to
prove the member was unreferenced.

``submission_artifact_submitted_latest_idx`` is partial and ordered rather than
a plain column index: every grading read starts from "the latest submitted
artifact per group", so indexing only ``submit = true`` rows in
``(submission_group_id, created_at DESC, id DESC)`` lets that aggregate read
straight off the index. ``id`` is in the key because two artifacts in a group
can share a ``created_at``, the same tie ``view_mappers`` orders around.

Five further candidates were built, benchmarked and then dropped, because
Postgres never chose them: an index on ``course_member.course_role_id`` (that
filter never appears without ``user_id`` or ``course_id`` beside it, and their
indexes always win the plan), and one each on ``course.organization_id``,
``course_content.course_content_type_id``, ``course_content_type.course_id``
and ``student_profile.organization_id`` (all filters over row counts small
enough, or selectivities poor enough, that a sequential scan is the right
plan and stays right).

Deliberately NOT indexed: the ~60 ``created_by`` / ``updated_by`` foreign keys.
They are ON DELETE SET NULL from almost every table, so indexing them would
speed up user deletion alone while taxing every insert and update in the
system. If deleting a user becomes a problem, index those columns then, on
their own evidence.

CREATE INDEX CONCURRENTLY, so building these does not block writes on
``submission_group`` or ``submission_artifact`` in production. That cannot run
inside a transaction, hence the autocommit block; ``statement_timeout`` is
cleared alongside it because a build on a large table will outrun the
deployment default.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""
from alembic import op


revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


# (index name, table, index definition body)
INDEXES = [
    ('submission_group_course_content_idx', 'submission_group', '(course_content_id)'),
    ('submission_group_course_idx', 'submission_group', '(course_id)'),
    ('submission_group_member_course_member_idx', 'submission_group_member', '(course_member_id)'),
    ('submission_artifact_submitted_latest_idx', 'submission_artifact',
     '(submission_group_id, created_at DESC, id DESC) WHERE submit'),
    ('course_member_course_group_idx', 'course_member', '(course_group_id)'),
]


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        for name, table, definition in INDEXES:
            op.execute(
                f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} {definition}'
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        for name, _table, _definition in reversed(INDEXES):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')
