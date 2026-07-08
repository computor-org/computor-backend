"""Course-level git models: a registry of git server instances, the
per-course binding to one of them, and the per-student repository record.

Git ownership moves from the *organization* to the *course* (see
COURSE_LEVEL_GIT_REFACTOR.md). The legacy organization-scoped ``GitProvider``
model is kept for now and converted by an external migration script.

Invariant: none of this is in the grading path. Submissions are uploaded
over the API; the backend never reads a student's git repository. Git is
only template delivery + the student's own working copy, which is why a
student repo may live anywhere and ``CourseMemberGitRepository`` is purely a
tracking record for the "do you already have a repo?" babysitting check.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPkMixin, VersionedMixin, AuditMixin


class GitServer(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """A git server instance Computor knows about (our Forgejo, an external
    GitLab, ...).

    ``managed`` instances are ones we operate and hold a service ``token``
    for — only those support backend-babysat student-repo provisioning. A
    course's git binding references one of these; the same instance is shared
    across every course bound to it (the "registry" half of the design).
    """

    __tablename__ = 'git_server'
    __table_args__ = (
        UniqueConstraint('type', 'base_url', name='git_server_type_url_key'),
        CheckConstraint("type IN ('forgejo', 'gitlab')", name='git_server_type_check'),
    )

    type = Column(String(50), nullable=False)        # 'forgejo' | 'gitlab'
    base_url = Column(String(2048), nullable=False)
    name = Column(String(255))                        # human-readable label
    managed = Column(Boolean, nullable=False, server_default=text("false"))
    token = Column(String(4096))                      # encrypted service token; managed instances only
    properties = Column(JSONB)

    course_bindings = relationship('CourseGitBinding', back_populates='git_server')


class CourseGitBinding(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """Per-course git binding (1:1 with course).

    Declares where the course's ``student-template`` lives and which
    student-repo modes the course offers. ``delivery`` selects assignment
    delivery (``git`` fork/clone vs ``download`` archive); ``student_repo_modes``
    lists the hosting modes a student may pick (e.g. ``["managed", "external"]``)
    and is only meaningful when ``delivery = 'git'``.
    """

    __tablename__ = 'course_git_binding'
    __table_args__ = (
        UniqueConstraint('course_id', name='course_git_binding_course_key'),
        CheckConstraint("delivery IN ('git', 'download')", name='course_git_binding_delivery_check'),
    )

    course_id = Column(
        ForeignKey('course.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False,
    )
    delivery = Column(String(50), nullable=False, server_default=text("'git'"))
    # Canonical location of the student-template (null for pure download).
    git_server_id = Column(ForeignKey('git_server.id', ondelete='RESTRICT', onupdate='RESTRICT'))
    template_repo = Column(String(2048))      # repo/project ref of the template on the server
    template_url = Column(String(2048))       # clone/web url of the template
    default_branch = Column(String(255), server_default=text("'main'"))
    # Per-course git credential (a GitLab group access token), encrypted at rest.
    # For managed GitLab the token + parent_group_id (in ``properties.gitlab``)
    # live on the binding — the course brings its own creds instead of sharing a
    # managed registry server. Forgejo uses the system server's token, so this
    # stays null for Forgejo-backed courses.
    token = Column(String(4096))
    # Allowed student-repo hosting modes, e.g. ["managed", "external", "download"].
    student_repo_modes = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    properties = Column(JSONB)

    course = relationship('Course', foreign_keys=[course_id])
    git_server = relationship('GitServer', back_populates='course_bindings')


class CourseMemberGitRepository(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """A student's working repository for a course (1:1 with course_member).

    Tracking only — answers "does this student already have a repo for this
    course?" so the VSCode extension knows whether to offer to create one.
    NEVER read for grading (submissions are uploaded over the API).
    """

    __tablename__ = 'course_member_repository'
    __table_args__ = (
        UniqueConstraint('course_member_id', name='course_member_repository_member_key'),
        CheckConstraint(
            "mode IN ('managed', 'external', 'download')",
            name='course_member_repository_mode_check',
        ),
        # No two managed repos may share a (server, repo_ref): a name collision
        # surfaces as a loud error instead of silently sharing one repo across
        # students. Partial so BYO/download rows and many NULL repo_refs are
        # exempt (Postgres counts NULLs as distinct anyway).
        Index(
            'course_member_repository_managed_ref_key',
            'git_server_id', 'repo_ref',
            unique=True,
            postgresql_where=text("mode = 'managed' AND repo_ref IS NOT NULL"),
        ),
    )

    course_member_id = Column(
        ForeignKey('course_member.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False,
    )
    mode = Column(String(50), nullable=False)        # 'managed' | 'external' | 'download'
    # Registry server when the repo lives on one we know; null for a BYO repo
    # on an instance not in the registry (then server_url holds the instance).
    git_server_id = Column(ForeignKey('git_server.id', ondelete='SET NULL', onupdate='RESTRICT'))
    server_url = Column(String(2048))
    repo_ref = Column(String(2048))                   # provider project/repo id
    http_url = Column(String(2048))
    ssh_url = Column(String(2048))
    web_url = Column(String(2048))
    properties = Column(JSONB)

    course_member = relationship('CourseMember', foreign_keys=[course_member_id])
    git_server = relationship('GitServer')
