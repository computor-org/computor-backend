"""Live integration tests for ``GitLabProviderClient`` (managed-GitLab course
provisioning) against a real GitLab.

Exercises the actual GitLab API: course-structure creation + idempotency, the
student fork, and member grants. Creates real groups/projects/users under the
configured parent group and cleans the course group up afterwards (best-effort).
Skipped unless ``GITLAB_IT_*`` is configured (see ``conftest.py``).
"""
import time

import pytest

from computor_backend.git_provider.gitlab import GITLAB_MAINTAINER

pytestmark = pytest.mark.gitlab

COURSE_SLUG = "it-course"
STUDENT_SLUG = "it-student-alice"
TEST_USERNAME = "computor-it-student"


def _find_subgroup(gl, parent_id, path):
    parent = gl.groups.get(parent_id)
    for sg in parent.subgroups.list(search=path, all=True):
        if sg.path == path:
            return gl.groups.get(sg.id)
    return None


@pytest.fixture(scope="module")
def course_structure(gitlab_provider, gitlab_cfg):
    """Provision the course structure once for the module; tear it down after.

    Idempotent: reuses any structure left over from a prior run.
    """
    structure = gitlab_provider.ensure_course_structure(
        gitlab_cfg["parent_group_id"], COURSE_SLUG, "IT Course"
    )
    yield structure
    try:
        gl = gitlab_provider._gl()
        grp = _find_subgroup(gl, gitlab_cfg["parent_group_id"], COURSE_SLUG)
        if grp is not None:
            gl.groups.delete(grp.id)
    except Exception:
        pass


@pytest.fixture(scope="module")
def gitlab_test_user(gitlab_provider):
    """A throwaway GitLab user to grant membership to (find-or-create)."""
    gl = gitlab_provider._gl()
    found = gl.users.list(username=TEST_USERNAME)
    if found:
        return found[0]
    return gl.users.create({
        "email": f"{TEST_USERNAME}@example.test",
        "username": TEST_USERNAME,
        "name": "Computor IT Student",
        "password": "7Gq2Vz9Lp4Kn8Xr3Wm6Bt",
        "skip_confirmation": True,
    })


class TestEnsureCourseStructure:
    def test_creates_template_reference_students(self, gitlab_provider, course_structure):
        s = course_structure
        assert s["course_group_path"].endswith(f"/{COURSE_SLUG}")
        assert s["template_path"].endswith(f"/{COURSE_SLUG}/template")
        assert s["reference_path"].endswith(f"/{COURSE_SLUG}/reference")
        assert s["students_group_path"].endswith(f"/{COURSE_SLUG}/students")
        # The projects/group actually exist on the server.
        gl = gitlab_provider._gl()
        assert gl.projects.get(s["template_project_id"]).path == "template"
        assert gl.projects.get(s["reference_project_id"]).path == "reference"
        assert gl.groups.get(s["students_group_id"]).path == "students"

    def test_idempotent(self, gitlab_provider, gitlab_cfg, course_structure):
        again = gitlab_provider.ensure_course_structure(
            gitlab_cfg["parent_group_id"], COURSE_SLUG, "IT Course"
        )
        assert again["course_group_id"] == course_structure["course_group_id"]
        assert again["template_project_id"] == course_structure["template_project_id"]
        assert again["reference_project_id"] == course_structure["reference_project_id"]
        assert again["students_group_id"] == course_structure["students_group_id"]


class TestStudentFork:
    def test_fork_into_students_group(self, gitlab_provider, course_structure):
        result = gitlab_provider.provision_student_fork(
            course_structure["template_project_id"],
            course_structure["students_group_id"],
            STUDENT_SLUG,
        )
        assert result.provider_project_id
        full_path = result.properties["gitlab"]["full_path"]
        assert full_path.endswith(f"/{COURSE_SLUG}/students/{STUDENT_SLUG}")
        # It exists on the server and is a fork of the template.
        gl = gitlab_provider._gl()
        # GitLab forks are async; give the import a moment to register.
        proj = None
        for _ in range(30):
            proj = gl.projects.get(int(result.provider_project_id))
            if getattr(proj, "forked_from_project", None):
                break
            time.sleep(1.0)
        assert proj.path == STUDENT_SLUG
        assert proj.forked_from_project["id"] == course_structure["template_project_id"]

    def test_fork_idempotent(self, gitlab_provider, course_structure):
        r1 = gitlab_provider.provision_student_fork(
            course_structure["template_project_id"],
            course_structure["students_group_id"],
            STUDENT_SLUG,
        )
        r2 = gitlab_provider.provision_student_fork(
            course_structure["template_project_id"],
            course_structure["students_group_id"],
            STUDENT_SLUG,
        )
        assert r1.provider_project_id == r2.provider_project_id


class TestAddMember:
    def test_grant_membership_by_user_id(self, gitlab_provider, course_structure, gitlab_test_user):
        fork = gitlab_provider.provision_student_fork(
            course_structure["template_project_id"],
            course_structure["students_group_id"],
            STUDENT_SLUG,
        )
        project_id = int(fork.provider_project_id)

        assert gitlab_provider.add_member(project_id, gitlab_test_user.id, GITLAB_MAINTAINER) is True
        gl = gitlab_provider._gl()
        member = gl.projects.get(project_id).members.get(gitlab_test_user.id)
        assert member.access_level == GITLAB_MAINTAINER
        # Idempotent — a repeat add (409) is swallowed as success.
        assert gitlab_provider.add_member(project_id, gitlab_test_user.id, GITLAB_MAINTAINER) is True
