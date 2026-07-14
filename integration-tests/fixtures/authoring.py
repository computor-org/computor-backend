"""Golden-path phase 3: the lecturer authors content, assigns examples, releases.

`lena` creates a course group, enrols the three students, builds a unit + six
assignment contents (one per Python example), assigns each example, and triggers
the student-template generation (Temporal `generate_student_template_v2`), which
pushes per-assignment folders into the Forgejo template repo.

Two backend workarounds (flagged for P4): `course_content_type` create drops the
`color` default → NULL breaks the list/get DTOs, and `course_content` create
drops the `position` default → NOT NULL violation. Both are always sent here.
"""

from __future__ import annotations

import time

import httpx
import pytest

from fixtures.forgejo import repo_tree


def example_label(directory: str) -> str:
    """'itpcp.pgph.py.dict_und_json' -> 'dict_und_json' (ltree-safe label)."""
    return directory.split(".")[-1]


def template_folder(directory: str) -> str:
    """The folder name the release uses in the template repo — the example
    *identifier* (slug), i.e. the directory with '_' collapsed to '.'
    ('itpcp.pgph.py.dict_und_json' -> 'itpcp.pgph.py.dict.und.json').
    """
    return directory.replace("_", ".")


# ---- course group + student enrolment (lecturer) -------------------------

@pytest.fixture(scope="session")
def target_course_group(lena_client: httpx.Client, target_course: dict, seated_staff: dict) -> dict:
    cid = target_course["id"]
    listing = lena_client.get("/course-groups", params={"course_id": cid})
    listing.raise_for_status()
    for g in listing.json():
        if isinstance(g, dict) and g.get("course_id") == cid and g.get("title") == "IT Group 1":
            return g
    r = lena_client.post("/course-groups", json={"course_id": cid, "title": "IT Group 1"})
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def enrolled_students(
    lena_client: httpx.Client,
    target_course: dict,
    target_course_group: dict,
    personas: dict,
) -> dict:
    """Enrol the three students (_student needs a course_group_id)."""
    cid, gid = target_course["id"], target_course_group["id"]
    out: dict = {}
    for key in ("s_correct", "s_empty", "s_mixed"):
        uid = personas[key].user_id
        members = lena_client.get(
            "/course-members", params={"course_id": cid, "user_id": uid}
        ).json()
        member = next((m for m in members if isinstance(m, dict) and m.get("user_id") == uid), None)
        if member is None:
            r = lena_client.post(
                "/course-members",
                json={
                    "user_id": uid,
                    "course_id": cid,
                    "course_role_id": "_student",
                    "course_group_id": gid,
                },
            )
            assert r.status_code in (200, 201), f"enrol {key}: {r.status_code} {r.text}"
            member = r.json()
        out[key] = member
    return out


# ---- content types + contents (lecturer) ---------------------------------

def _ensure_content_type(
    lena: httpx.Client, course_id: str, slug: str, kind_id: str, title: str
) -> dict:
    r = lena.post(
        "/course-content-types",
        json={
            "slug": slug,
            "title": title,
            "course_id": course_id,
            "course_content_kind_id": kind_id,
            "color": "green",  # must be sent — backend drops the default → NULL
        },
    )
    if r.status_code in (200, 201):
        return r.json()
    # duplicate → find it (list serializes now that rows carry a color)
    for t in lena.get("/course-content-types", params={"course_id": course_id}).json():
        if isinstance(t, dict) and t.get("slug") == slug and t.get("course_id") == course_id:
            return t
    raise AssertionError(f"content type {slug}: {r.status_code} {r.text}")


@pytest.fixture(scope="session")
def content_types(lena_client: httpx.Client, target_course: dict, seated_staff: dict) -> dict:
    cid = target_course["id"]
    return {
        "unit": _ensure_content_type(lena_client, cid, "unit", "unit", "Unit"),
        "assignment": _ensure_content_type(lena_client, cid, "assignment", "assignment", "Assignment"),
    }


def _ensure_content(
    lena: httpx.Client, course_id: str, path: str, type_id: str, title: str, position: int, **extra
) -> dict:
    for cc in lena.get("/course-contents", params={"course_id": course_id}).json():
        if isinstance(cc, dict) and cc.get("path") == path and cc.get("course_id") == course_id:
            return cc
    body = {
        "path": path,
        "course_id": course_id,
        "course_content_type_id": type_id,
        "title": title,
        "position": position,  # must be sent — backend drops the default → NOT NULL
    }
    body.update(extra)
    r = lena.post("/course-contents", json=body)
    assert r.status_code in (200, 201), f"content {path}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def course_contents(
    lena_client: httpx.Client, target_course: dict, content_types: dict, python_examples: tuple
) -> dict:
    """One unit + one assignment content per example. Keyed by example directory."""
    cid = target_course["id"]
    unit = _ensure_content(lena_client, cid, "unit", content_types["unit"]["id"], "Unit 1", 0)
    assignments: dict = {}
    for i, ex in enumerate(python_examples, start=1):
        label = example_label(ex.directory)
        assignments[ex.directory] = _ensure_content(
            lena_client,
            cid,
            f"unit.{label}",
            content_types["assignment"]["id"],
            ex.meta.get("title", label),
            i,
            max_submissions=10,
            max_test_runs=20,
        )
    return {"unit": unit, "assignments": assignments}


# ---- example assignment + release (lecturer) -----------------------------

@pytest.fixture(scope="session")
def assigned_examples(
    lena_client: httpx.Client, course_contents: dict, uploaded_examples: dict
) -> dict:
    """Assign each example to its assignment content (by id — identifiers dot-mangle)."""
    for directory, cc in course_contents["assignments"].items():
        example = uploaded_examples[directory]
        r = lena_client.post(
            f"/lecturers/course-contents/{cc['id']}/assign-example",
            json={"example_id": example["id"], "version_tag": "1.0.0"},
        )
        assert r.status_code in (200, 201), f"assign {directory}: {r.status_code} {r.text}"
    return course_contents["assignments"]


@pytest.fixture(scope="session")
def released_template(
    lena_client: httpx.Client,
    target_course: dict,
    target_course_git: dict,
    assigned_examples: dict,
    python_examples: tuple,
    forgejo_admin: httpx.Client,
) -> dict:
    """Trigger student-template generation and wait for all assignment dirs to land."""
    cid = target_course["id"]
    r = lena_client.post(f"/system/courses/{cid}/generate-student-template", json={})
    assert r.status_code == 200, r.text
    repo = target_course_git["template_repo"]
    expected_dirs = {template_folder(ex.directory) for ex in python_examples}

    present: set[str] = set()
    paths: list[str] = []
    for _ in range(60):  # generation is async (Temporal) and pushes progressively
        paths = repo_tree(forgejo_admin, repo)
        present = {p.split("/", 1)[0] for p in paths if "/" in p}
        if expected_dirs.issubset(present):
            return {"repo": repo, "paths": paths, "workflow_id": r.json().get("workflow_id")}
        time.sleep(3)
    raise AssertionError(
        f"template still missing {expected_dirs - present} after polling; have {sorted(present)}"
    )
