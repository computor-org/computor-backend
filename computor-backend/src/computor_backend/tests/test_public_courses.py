"""Behavioral tests for public-course discovery and self-subscription."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from computor_backend.api import public_courses
from computor_backend.model.course import Course, CourseGroup, CourseMember
from computor_backend.permissions.principal import Principal


class _Query:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *conditions):
        return self

    def order_by(self, *columns):
        return self

    def offset(self, value):
        return self

    def limit(self, value):
        return self

    def all(self):
        if self.model is Course:
            return [course for course in self.db.courses if course.is_public]
        if self.model is CourseGroup:
            return self.db.groups
        return self.db.members

    def first(self):
        if self.model is Course:
            return next((course for course in self.db.courses if course.is_public), None)
        if self.model is CourseGroup:
            return self.db.groups[0] if self.db.groups else None
        return self.db.members[0] if self.db.members else None


class _Session:
    def __init__(self, courses, groups=None, members=None):
        self.courses = courses
        self.groups = groups or []
        self.members = members or []
        self.added = []
        self.commits = 0

    def query(self, model):
        return _Query(self, model)

    def add(self, entity):
        self.added.append(entity)
        if isinstance(entity, CourseGroup):
            entity.id = entity.id or str(uuid4())
            self.groups.append(entity)
        elif isinstance(entity, CourseMember):
            entity.id = entity.id or str(uuid4())
            self.members.append(entity)

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        return None


def _course(*, public: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=str(uuid4()),
        title="Intro to Python",
        description="A public course",
        course_family_id=str(uuid4()),
        organization_id=str(uuid4()),
        path="intro.python",
        language_code="en",
        properties=None,
        is_public=public,
    )


@pytest.mark.asyncio
async def test_public_catalog_contains_only_explicitly_public_courses():
    public_course = _course(public=True)
    private_course = _course(public=False)
    response = public_courses.list_public_courses(
        skip=0,
        limit=100,
        db=_Session([public_course, private_course]),
    )

    assert [course.id for course in response] == [public_course.id]
    assert response[0].is_public is True


@pytest.mark.asyncio
async def test_self_subscription_creates_student_membership_and_runs_lifecycle(monkeypatch):
    course = _course(public=True)
    session = _Session([course])
    principal = Principal(user_id=str(uuid4()))
    lifecycle_calls = []

    async def fake_lifecycle(member, db):
        lifecycle_calls.append((member, db))

    monkeypatch.setattr(public_courses, "course_member_post_create", fake_lifecycle)

    member = await public_courses.subscribe_to_public_course(
        course_id=UUID(course.id),
        permissions=principal,
        db=session,
    )

    created = session.members[0]
    assert member.course_id == course.id
    assert created.user_id == principal.user_id
    assert created.course_role_id == "_student"
    assert created.course_group_id is not None
    assert created.properties == {"self_subscribed": True}
    assert len(lifecycle_calls) == 1
    assert session.commits == 1


@pytest.mark.asyncio
async def test_self_subscription_is_idempotent_and_never_changes_existing_role(monkeypatch):
    course = _course(public=True)
    user_id = str(uuid4())
    existing = CourseMember(
        id=str(uuid4()),
        user_id=user_id,
        course_id=course.id,
        course_group_id=str(uuid4()),
        course_role_id="_student",
    )
    session = _Session([course], members=[existing])
    monkeypatch.setattr(public_courses, "course_member_post_create", lambda *_: None)

    response = await public_courses.subscribe_to_public_course(
        course_id=UUID(course.id),
        permissions=Principal(user_id=user_id),
        db=session,
    )

    assert response.id == existing.id
    assert len(session.members) == 1
    assert existing.course_role_id == "_student"
    assert session.commits == 0
