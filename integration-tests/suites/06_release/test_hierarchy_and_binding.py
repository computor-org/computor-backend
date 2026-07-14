"""Hierarchy + Forgejo binding + staff seating (golden-path phase 1).

`orga` builds org → family → course, binds it to the managed Forgejo (which
materializes the student-template repo and locks the binding), and seats lena
(_lecturer) + tobi (_tutor). The ceiling rule (a plain lecturer can't seat a
tutor) is asserted as a side condition.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.forgejo import repo_exists

pytestmark = pytest.mark.release


def test_hierarchy_created_by_org_manager(
    target_organization: dict, target_course_family: dict, target_course: dict
) -> None:
    assert target_organization["path"] == "it_org"
    assert target_course_family["organization_id"] == target_organization["id"]
    assert target_course["course_family_id"] == target_course_family["id"]


def test_course_git_binding_materialized_and_locked(target_course_git: dict) -> None:
    assert target_course_git["delivery"] == "git"
    assert target_course_git["student_repo_modes"] == ["managed"]
    # First bind creates the template repo and locks the binding.
    assert target_course_git["locked"] is True
    assert target_course_git["template_repo"]
    # URL handed to clients must be the public host, never the docker-internal one.
    assert "forgejo:3030" not in (target_course_git.get("template_url") or "")


def test_template_repo_exists_in_forgejo(
    target_course_git: dict, forgejo_admin: httpx.Client
) -> None:
    assert repo_exists(forgejo_admin, target_course_git["template_repo"]), (
        f"template repo {target_course_git['template_repo']} not found in Forgejo"
    )


def test_staff_seated(seated_staff: dict, personas: dict) -> None:
    assert seated_staff["lecturer"]["user_id"] == personas["lena"].user_id
    assert seated_staff["lecturer"]["course_role_id"] == "_lecturer"
    assert seated_staff["tutor"]["user_id"] == personas["tobi"].user_id
    assert seated_staff["tutor"]["course_role_id"] == "_tutor"


def test_lecturer_cannot_seat_a_tutor(
    lena_client: httpx.Client, target_course: dict, personas: dict
) -> None:
    # Ceiling rule: a plain _lecturer may only enrol _students.
    r = lena_client.post(
        "/course-members",
        json={
            "user_id": personas["s_empty"].user_id,
            "course_id": target_course["id"],
            "course_role_id": "_tutor",
        },
    )
    assert r.status_code == 403, r.text
