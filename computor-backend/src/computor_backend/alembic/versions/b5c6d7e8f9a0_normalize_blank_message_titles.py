"""normalize blank message subjects to NULL

``Message.title`` is the human subject line. It is required on announcement
scopes (global / organization / course_family / course / course_content /
course_group) and forbidden on conversational ones (submission_group /
course_member / user), a rule now enforced at the API boundary.

Existing rows do not respect it. Every message posted from a conversational
view carries ``''`` rather than NULL, because the compose UI renders no
subject input there but still submitted the (empty) field. That made
``title IS NULL`` false for messages that visibly have no subject, so any
query or report distinguishing "has a subject" from "does not" was wrong.

This collapses blank and whitespace-only subjects to NULL across the board.
It does not touch announcements that legitimately have no subject — they
also become NULL here, which is the honest representation; the API now
refuses to create more of them, and clients render such legacy rows with a
"(no subject)" placeholder rather than pretending the field is meaningful.

Irreversible in the strict sense: '' and NULL are indistinguishable
afterwards. The downgrade is a no-op rather than a lie, since restoring ''
everywhere would corrupt rows that were correctly NULL all along.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE message
           SET title = NULL
         WHERE title IS NOT NULL
           AND btrim(title) = ''
        """
    )


def downgrade() -> None:
    # Intentionally a no-op — see the module docstring.
    pass
