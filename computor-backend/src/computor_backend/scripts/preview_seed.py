#!/usr/bin/env python3
"""Seed the small, deterministic dataset used by ``fresh`` previews.

The normal development seeder intentionally creates submissions, messages and
other history. That is useful for demos but makes a regression hard to
reproduce. Preview seeding therefore creates only the course catalogue, course
membership and matching OIDC accounts; no submission or workspace state is
generated.
"""

from __future__ import annotations

import json
import os
from uuid import UUID, uuid5

from computor_backend.custom_types import Ltree
from computor_backend.database import get_db_session
from computor_backend.model.auth import Account, User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
)
from computor_backend.model.organization import Organization
from computor_backend.model.role import Role, UserRole


OIDC_NAMESPACE = UUID("5d1d0ef5-1ce2-4d58-b0cb-6d721d3f0a4a")
USERS = {
    "demo_admin": {
        "email": "admin@computor.local",
        "given_name": "Demo",
        "family_name": "Admin",
        "course_role": "_owner",
    },
    "demo_lecturer": {
        "email": "lecturer@computor.local",
        "given_name": "Demo",
        "family_name": "Lecturer",
        "course_role": "_lecturer",
    },
    "demo_student": {
        "email": "student@computor.local",
        "given_name": "Demo",
        "family_name": "Student",
        "course_role": "_student",
    },
}


def _keycloak_ids() -> dict[str, str]:
    raw = os.environ.get("PREVIEW_KEYCLOAK_USERS", "")
    if raw:
        try:
            values = json.loads(raw)
            if isinstance(values, dict):
                return {str(key): str(value) for key, value in values.items()}
        except json.JSONDecodeError:
            pass
    return {username: str(uuid5(OIDC_NAMESPACE, username)) for username in USERS}


def _get_or_create_user(
    session, username: str, data: dict[str, str], provider_id: str
) -> User:
    # ``user.username`` was removed by the current schema.  Reuse a seeded
    # account by its OIDC subject first, then by its unique email, and keep the
    # human-readable fixture name in JSON properties for diagnostics.
    account = (
        session.query(Account)
        .filter(
            Account.provider == "keycloak",
            Account.provider_account_id == provider_id,
        )
        .one_or_none()
    )
    user = (
        session.query(User).filter(User.id == account.user_id).one_or_none()
        if account is not None
        else session.query(User).filter(User.email == data["email"]).one_or_none()
    )
    if user is None:
        user = User(
            email=data["email"],
            given_name=data["given_name"],
            family_name=data["family_name"],
            properties={"preview_seed": True, "username": username},
        )
        session.add(user)
        session.flush()
    else:
        user.email = data["email"]
        user.given_name = data["given_name"]
        user.family_name = data["family_name"]
        properties = dict(user.properties or {})
        properties.update({"preview_seed": True, "username": username})
        user.properties = properties
    return user


def _link_oidc_account(
    session, user: User, provider_id: str, username: str
) -> None:
    account = (
        session.query(Account)
        .filter(Account.provider == "keycloak", Account.user_id == user.id)
        .one_or_none()
    )
    if account is None:
        session.add(
            Account(
                provider="keycloak",
                type="oidc",
                provider_account_id=provider_id,
                user_id=user.id,
                properties={"preview_seed": True, "username": username},
            )
        )
    else:
        account.type = "oidc"
        account.provider_account_id = provider_id
        account.properties = {"preview_seed": True, "username": username}


def seed() -> dict[str, object]:
    state_mode = os.environ.get("PREVIEW_STATE_MODE", "fresh")
    if state_mode != "fresh":
        return {
            "state_mode": state_mode,
            "seeded": False,
            "reason": "course fixture is intentionally disabled outside fresh mode",
        }

    ids = _keycloak_ids()
    with get_db_session() as session:
        users = {
            username: _get_or_create_user(
                session,
                username,
                data,
                ids.get(username, str(uuid5(OIDC_NAMESPACE, username))),
            )
            for username, data in USERS.items()
        }
        for username, user in users.items():
            _link_oidc_account(
                session,
                user,
                ids.get(username, str(uuid5(OIDC_NAMESPACE, username))),
                username,
            )

        admin_role = session.query(Role).filter_by(id="_admin").one_or_none()
        if admin_role is not None:
            existing = (
                session.query(UserRole)
                .filter_by(user_id=users["demo_admin"].id, role_id="_admin")
                .one_or_none()
            )
            if existing is None:
                session.add(UserRole(user_id=users["demo_admin"].id, role_id="_admin"))

        organization = (
            session.query(Organization)
            .filter(Organization.path == Ltree("preview"))
            .one_or_none()
        )
        if organization is None:
            organization = Organization(
                title="Computor Preview University",
                description="Deterministic preview fixture",
                organization_type="organization",
                path=Ltree("preview"),
                created_by=users["demo_admin"].id,
            )
            session.add(organization)
            session.flush()

        family = (
            session.query(CourseFamily)
            .filter(
                CourseFamily.organization_id == organization.id,
                CourseFamily.path == Ltree("preview"),
            )
            .one_or_none()
        )
        if family is None:
            family = CourseFamily(
                title="Preview Courses",
                description="Small deterministic catalogue for preview testing",
                path=Ltree("preview"),
                organization_id=organization.id,
                created_by=users["demo_admin"].id,
            )
            session.add(family)
            session.flush()

        course = (
            session.query(Course)
            .filter(
                Course.course_family_id == family.id,
                Course.path == Ltree("release_2026_10"),
            )
            .one_or_none()
        )
        if course is None:
            course = Course(
                title="Computor Preview Course",
                description="A state-light course used by preview smoke tests",
                path=Ltree("release_2026_10"),
                course_family_id=family.id,
                organization_id=organization.id,
                created_by=users["demo_admin"].id,
            )
            session.add(course)
            session.flush()

        group = (
            session.query(CourseGroup)
            .filter(
                CourseGroup.course_id == course.id,
                CourseGroup.title == "Preview students",
            )
            .one_or_none()
        )
        if group is None:
            group = CourseGroup(
                title="Preview students",
                description="Deterministic student group",
                course_id=course.id,
                created_by=users["demo_admin"].id,
            )
            session.add(group)
            session.flush()

        memberships = {}
        for username, data in USERS.items():
            role = data["course_role"]
            member = (
                session.query(CourseMember)
                .filter(
                    CourseMember.user_id == users[username].id,
                    CourseMember.course_id == course.id,
                )
                .one_or_none()
            )
            if member is None:
                member = CourseMember(
                    user_id=users[username].id,
                    course_id=course.id,
                    course_group_id=group.id if role == "_student" else None,
                    course_role_id=role,
                    created_by=users["demo_admin"].id,
                )
                session.add(member)
            else:
                member.course_role_id = role
                member.course_group_id = group.id if role == "_student" else None
            memberships[username] = role

        assignment_kind = (
            session.query(CourseContentKind).filter_by(id="assignment").one_or_none()
        )
        if assignment_kind is not None:
            content_type = (
                session.query(CourseContentType)
                .filter(
                    CourseContentType.course_id == course.id,
                    CourseContentType.slug == "preview",
                )
                .one_or_none()
            )
            if content_type is None:
                content_type = CourseContentType(
                    title="Preview assignment",
                    description="Minimal submittable content for smoke tests",
                    slug="preview",
                    color="#4CAF50",
                    course_content_kind_id=assignment_kind.id,
                    course_id=course.id,
                    created_by=users["demo_admin"].id,
                )
                session.add(content_type)
                session.flush()
            content = (
                session.query(CourseContent)
                .filter(
                    CourseContent.course_id == course.id,
                    CourseContent.path == Ltree("preview"),
                )
                .one_or_none()
            )
            if content is None:
                session.add(
                    CourseContent(
                        title="Preview assignment",
                        description="A deterministic assignment with no submissions",
                        path=Ltree("preview"),
                        course_id=course.id,
                        course_content_type_id=content_type.id,
                        course_content_kind_id=assignment_kind.id,
                        is_submittable=True,
                        position=1.0,
                        max_group_size=1,
                        max_test_runs=5,
                        max_submissions=3,
                        created_by=users["demo_admin"].id,
                    )
                )

        session.commit()
        return {
            "seeded": True,
            "course_id": str(course.id),
            "course_path": "preview.preview.release_2026_10",
            "memberships": memberships,
            "users": {username: str(user.id) for username, user in users.items()},
            "submissions": 0,
            "messages": 0,
            "workspaces": 0,
        }


if __name__ == "__main__":
    result = seed()
    output = os.environ.get("PREVIEW_SEED_OUTPUT", "/opt/computor/shared/preview-seed.json")
    try:
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        # Preview data bind mounts intentionally remain owned by the host
        # account. The controller copies this summary from the exited
        # container, so a read-only mount must not make the seed transaction
        # fail after the database commit.
        print(f"warning: cannot write preview seed summary {output}: {exc}")
    print(json.dumps(result, indent=2, sort_keys=True))
