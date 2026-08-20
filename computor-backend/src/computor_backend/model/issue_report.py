"""Who filed which problem report — the half that must never reach GitHub.

A report becomes a public-ish GitHub issue, but the reporter's identity is not
part of it: the issue carries only an opaque report id. This table is the join
between the two, so a maintainer can still ask "who reported this?" through an
admin-only lookup while the issue itself stays unattributable to anyone reading
the tracker.

Nothing the user wrote is stored here. The prose lives in the GitHub issue and
only there, so there is a single place to redact from.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class IssueReport(Base):
    """One submitted problem report and the issue it became.

    The row is written *before* GitHub is called, so a submission that fails
    still leaves a trace; ``issue_number``/``issue_url`` are filled in once the
    issue exists. ``id`` is the report id quoted in the issue body and shown to
    the reporter.

    ``user_id`` is ``ON DELETE SET NULL``: erasing a user must remove the link
    to them, but the issue itself outlives the account, and a row that records
    *that* a report happened is worth keeping once it can no longer identify
    anybody.
    """

    __tablename__ = 'issue_report'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    # Denormalised: which tracker this went to, so old rows stay meaningful
    # after the deployment is pointed at a different repository.
    repository = Column(Text, nullable=False)
    issue_number = Column(Integer, nullable=True)
    issue_url = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship('User', foreign_keys=[user_id])
