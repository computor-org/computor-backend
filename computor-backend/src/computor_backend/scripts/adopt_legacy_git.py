#!/usr/bin/env python3
"""Adopt a legacy system's org-level GitLab configuration into the per-course
git model, preserving the legacy repository naming.

WHY THIS EXISTS
---------------
The legacy system kept one GitLab token per organization and described a
course's repositories in ``course.properties['gitlab']``. Release 2026.10 keeps
that in a ``git_server`` row plus a per-course ``course_git_binding`` whose
``properties.gitlab`` names every repository and group by id and path.

The two systems also *name* the course repositories differently:

    legacy  ``student-template``  ``assignments``
    release ``template``          ``reference``

Nothing in the release backend hardcodes the new names at read time — it reads
the mapping off the binding. So adoption is exactly the job of writing that
mapping down, pointing at the repositories the legacy system already created.
Repositories are never created, renamed or moved.

THREE THINGS THAT ARE EASY TO GET WRONG (all were, before this module)
----------------------------------------------------------------------
1. ``alembic upgrade head`` DESTROYS the org GitLab token and url. Migration
   ``b1c2d3e4f5a6`` copies them into a ``git_provider`` table and strips them
   from the JSONB; ``f0a1b2c3d4e5`` then drops that table. Run ``--stash-org-git``
   BEFORE migrating, or there is no token left to bridge.
2. The template repository is NOT ``course.properties.gitlab.full_path`` — that
   is the course *group*. It is ``projects.student_template.full_path``.
3. ``parent_group_id`` must be a STRING (the DTO types it that way and pydantic
   rejects an int with a 500); every other id must be an INT.

USAGE
-----
Dry-run by default; ``--apply`` writes. Both are safe to re-run.

    # before `alembic upgrade head`, on the restored legacy database:
    python adopt_legacy_git.py --preflight
    python adopt_legacy_git.py --stash-org-git --apply

    # after `alembic upgrade head`:
    python adopt_legacy_git.py --resolve-ids                  # plan only
    python adopt_legacy_git.py --resolve-ids --apply          # write
    python adopt_legacy_git.py --repair --resolve-ids --apply # fill in later

Configuration: secrets come from the environment, behaviour from argv (argv is
visible in ``ps`` and ``docker inspect``).

    TOKEN_SECRET          target system's secret (required to re-encrypt)
    LEGACY_TOKEN_SECRET   source system's secret (defaults to TOKEN_SECRET)
    ADOPT_GITLAB_TOKEN    plaintext PAT, last-resort when no token can be bridged
    ADOPT_DATABASE_URL    full SQLAlchemy URL; otherwise built from POSTGRES_*
    POSTGRES_HOST/PORT/USER/PASSWORD/DB

This module is piped into a running container on stdin (``docker exec -i …
python3 - < adopt_legacy_git.py``) so a migration never needs an image rebuild.
That imposes three rules on the code below, enforced by a unit test:
no ``__file__``, no relative imports, and every backend import lazy and optional.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

#: Bumped when the shape written under ``properties.gitlab.adopted`` changes,
#: so ``--repair`` can tell which rows need upgrading.
ADOPTED_SCHEMA = 1

#: The legacy alembic head. Adoption of the org token must happen at this head.
LEGACY_HEAD = "cc1d2e3f4a5b"


# ---------------------------------------------------------------------------
# Pure helpers — no database, no network. These carry the actual mapping and
# are where the unit tests live.
# ---------------------------------------------------------------------------

def as_dict(value: Any) -> Dict[str, Any]:
    """A JSONB column as a dict, whatever the driver handed back."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _path_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    path = urlparse(url).path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return path or None


def _git_url(base_url: Optional[str], repo: Optional[str]) -> Optional[str]:
    if not base_url or not repo:
        return None
    return f"{base_url.rstrip('/')}/{repo}.git"


def legacy_base_url(
    course_gitlab: Dict[str, Any],
    org_gitlab: Dict[str, Any],
    override: Optional[str] = None,
) -> Optional[str]:
    """The GitLab base URL for a legacy course.

    The course blob is preferred over the organization's: it carries ``url``
    too, and unlike the org blob it SURVIVES ``alembic upgrade head`` (migration
    ``b1c2d3e4f5a6`` only rewrites ``organization``). Falling back to the host of
    the stored template URL keeps courses adoptable even when both blobs were
    stripped.
    """
    for candidate in (
        override,
        course_gitlab.get("url"),
        org_gitlab.get("url"),
    ):
        if candidate:
            return str(candidate).rstrip("/")

    template_url = course_gitlab.get("student_template_url")
    if template_url:
        parsed = urlparse(str(template_url))
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _project_slot(course_gitlab: Dict[str, Any], *names: str) -> Dict[str, Any]:
    projects = course_gitlab.get("projects") or {}
    if not isinstance(projects, dict):
        return {}
    for name in names:
        slot = projects.get(name)
        if isinstance(slot, dict):
            return slot
    return {}


def legacy_template_ref(
    course_gitlab: Dict[str, Any], base_url: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """(repo path, clone url) of the legacy student-template repository.

    Deliberately does NOT fall back to ``course_gitlab['full_path']``: that is
    the course *group*, and using it produced bindings whose ``template_repo``
    pointed at a group rather than a repository. The conventional
    ``<group>/student-template`` fallback is spelled out instead.
    """
    slot = _project_slot(course_gitlab, "student_template", "student-template", "template")
    repo = slot.get("full_path")

    if not repo:
        repo = _path_from_url(course_gitlab.get("student_template_url"))
    if not repo and course_gitlab.get("full_path"):
        repo = f"{course_gitlab['full_path']}/student-template"
    if not repo:
        return None, None

    url = course_gitlab.get("student_template_url") or slot.get("http_url_to_repo") or slot.get("web_url")
    url = str(url) if url else _git_url(base_url, repo)
    if url and not url.endswith(".git"):
        url = f"{url}.git"
    return repo, url


def legacy_reference_ref(
    course_gitlab: Dict[str, Any], base_url: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """(repo path, clone url) of the legacy assignments repository — what the
    release model calls the *reference* repository.

    This is the mapping that makes solutions keep flowing after a migration:
    ``push_reference_repo`` reads ``properties.gitlab.reference_path`` and skips
    silently when it is absent.
    """
    slot = _project_slot(course_gitlab, "assignments", "reference")
    repo = slot.get("full_path")

    if not repo:
        repo = _path_from_url(course_gitlab.get("assignments_url"))
    if not repo and course_gitlab.get("full_path"):
        repo = f"{course_gitlab['full_path']}/assignments"
    if not repo:
        return None, None

    url = course_gitlab.get("assignments_url") or slot.get("http_url_to_repo") or slot.get("web_url")
    url = str(url) if url else _git_url(base_url, repo)
    if url and not url.endswith(".git"):
        url = f"{url}.git"
    return repo, url


def legacy_group_ids(course_gitlab: Dict[str, Any]) -> Dict[str, Any]:
    """Group ids and paths from the legacy course blob, typed the way the
    release model stores them.

    Typing is load-bearing: ``parent_group_id`` is a string because
    ``CourseGitBindingGet`` types it that way and pydantic rejects an int (a 500
    on every read of the binding); the rest are ints because they are handed to
    python-gitlab.
    """
    out: Dict[str, Any] = {}

    course_group_id = _as_int(course_gitlab.get("group_id"))
    if course_group_id is not None:
        out["course_group_id"] = course_group_id
    if course_gitlab.get("full_path"):
        out["course_group_path"] = course_gitlab["full_path"]

    parent = course_gitlab.get("parent_id")
    if parent is None:
        parent = course_gitlab.get("parent")
    if parent is not None:
        out["parent_group_id"] = str(parent)

    students = course_gitlab.get("students_group")
    students = students if isinstance(students, dict) else {}
    students_id = _as_int(students.get("group_id"))
    if students_id is not None:
        out["students_group_id"] = students_id
    students_path = students.get("full_path")
    if not students_path and course_gitlab.get("full_path"):
        students_path = f"{course_gitlab['full_path']}/students"
    if students_path:
        out["students_group_path"] = students_path

    tutors = course_gitlab.get("tutors_group")
    tutors = tutors if isinstance(tutors, dict) else {}
    tutors_id = _as_int(tutors.get("group_id"))
    if tutors_id is not None:
        out["tutors_group_id"] = tutors_id

    return out


def strip_secrets(blob: Dict[str, Any]) -> Dict[str, Any]:
    """A copy of a legacy blob safe to keep as provenance.

    The legacy schema allows ``course.properties.gitlab.token`` and the legacy
    runtime honoured it. Kept verbatim it would be a ciphertext under the OLD
    secret — undecryptable here, and able to shadow the correctly bridged token.
    """
    return {k: v for k, v in blob.items() if k != "token"}


def build_binding_properties(
    course_gitlab: Dict[str, Any],
    *,
    template_repo: str,
    template_url: Optional[str],
    reference_path: Optional[str],
    resolved_ids: Optional[Dict[str, Any]] = None,
    token_source: Optional[str] = None,
    ids_degraded: Optional[str] = None,
    adopted_at: Optional[str] = None,
) -> Dict[str, Any]:
    """``course_git_binding.properties`` for an adopted course.

    Produces the same key set as ``GitLabProviderClient.ensure_course_structure``
    so that ``_provision_gitlab_managed``, ``push_reference_repo``,
    ``register_gitlab_managed_access`` and the binding DTO all work unchanged —
    only pointed at the legacy names.
    """
    gitlab: Dict[str, Any] = legacy_group_ids(course_gitlab)
    gitlab["template_path"] = template_repo
    if template_url:
        gitlab["template_url"] = template_url
    if reference_path:
        gitlab["reference_path"] = reference_path

    # Ids resolved from GitLab win: they are observed, not derived.
    for key, value in (resolved_ids or {}).items():
        if value is not None:
            gitlab[key] = value

    gitlab["adopted"] = {
        "tool": "adopt_legacy_git",
        "schema": ADOPTED_SCHEMA,
        "at": adopted_at or datetime.now(timezone.utc).isoformat(),
        "legacy_head": LEGACY_HEAD,
        # Why template_path says "student-template": so a later reader does not
        # "correct" it to the release naming.
        "naming": {"template": "student-template", "reference": "assignments"},
        "ids": {"resolved": bool(resolved_ids), "degraded": ids_degraded},
        "token": {"bridged": token_source is not None, "from": token_source},
        "legacy": strip_secrets(course_gitlab),
    }
    return {"gitlab": gitlab}


@dataclass
class MemberRepoPlan:
    """One ``course_member_repository`` row derived from a legacy member blob."""

    course_member_id: str
    mode: str
    repo_ref: str
    http_url: Optional[str]
    ssh_url: Optional[str]
    web_url: Optional[str]
    properties: Dict[str, Any]


def build_member_repo_plan(
    course_member_id: str,
    member_gitlab: Dict[str, Any],
    base_url: Optional[str],
    *,
    mode: str = "managed",
    adopted_at: Optional[str] = None,
) -> Optional[MemberRepoPlan]:
    """The student's existing repository, as a ``course_member_repository`` row.

    Without these rows every migrated student looks unprovisioned, and the first
    provision call forks a SECOND, empty repository over the top of their work.

    ``project_id`` is mandatory downstream (``register_gitlab_managed_access``
    refuses without it). Legacy stores it as ``gitlab_project_id`` and also as
    ``group_id`` — note that on a member blob ``group_id`` is a PROJECT id,
    while on a team submission-group blob the same key is a namespace id, so
    this extractor must never be reused for those.
    """
    repo_ref = member_gitlab.get("full_path") or member_gitlab.get("gitlab_project_path")
    if not repo_ref:
        return None

    project_id = _as_int(member_gitlab.get("gitlab_project_id"))
    if project_id is None:
        project_id = _as_int(member_gitlab.get("group_id"))
    namespace_id = _as_int(member_gitlab.get("namespace_id"))

    gitlab: Dict[str, Any] = {"full_path": repo_ref}
    if project_id is not None:
        gitlab["project_id"] = project_id
    if namespace_id is not None:
        gitlab["namespace_id"] = namespace_id

    return MemberRepoPlan(
        course_member_id=str(course_member_id),
        mode=mode,
        repo_ref=repo_ref,
        http_url=member_gitlab.get("http_url_to_repo") or _git_url(base_url, repo_ref),
        ssh_url=member_gitlab.get("ssh_url_to_repo"),
        web_url=member_gitlab.get("web_url") or (f"{base_url.rstrip('/')}/{repo_ref}" if base_url else None),
        properties={
            "gitlab": gitlab,
            "adopted": {
                "tool": "adopt_legacy_git",
                "at": adopted_at or datetime.now(timezone.utc).isoformat(),
                "legacy": strip_secrets(member_gitlab),
            },
        },
    )


def detect_repo_ref_collisions(
    plans: Sequence[MemberRepoPlan],
    git_server_id: str,
    existing: Set[Tuple[str, str]],
) -> List[str]:
    """``(git_server_id, repo_ref)`` pairs that would violate the partial unique
    index on managed member repositories.

    Reported loudly rather than swallowed by ``ON CONFLICT``, which would drop
    rows and leave those students silently unprovisioned.
    """
    problems: List[str] = []
    seen: Set[str] = set()
    for plan in plans:
        if plan.mode != "managed" or not plan.repo_ref:
            continue
        if plan.repo_ref in seen:
            problems.append(f"{plan.repo_ref} (duplicated within this course)")
            continue
        seen.add(plan.repo_ref)
        if (git_server_id, plan.repo_ref) in existing:
            problems.append(f"{plan.repo_ref} (already claimed by another member)")
    return problems


def bridge_token(ciphertext: str, legacy_secret: str, new_secret: str) -> str:
    """Re-key a keycove secret from the source system's TOKEN_SECRET to this one.

    Both branches call keycove with the RAW ``TOKEN_SECRET`` (no derivation) and
    pin the same keycove version, so this is wire-compatible. A wrong legacy
    secret raises rather than quietly writing a NULL token.
    """
    from keycove import decrypt, encrypt

    plaintext = decrypt(ciphertext, legacy_secret)
    if not isinstance(plaintext, str) or not plaintext.strip():
        raise ValueError("token decrypted to an empty value")
    return encrypt(plaintext, new_secret)


@dataclass
class CoursePlan:
    course_id: str
    course_title: str
    org_title: str
    action: str = "create"  # create | repair | skip
    skip_reason: Optional[str] = None
    base_url: Optional[str] = None
    template_repo: Optional[str] = None
    template_url: Optional[str] = None
    reference_path: Optional[str] = None
    token_ciphertext: Optional[str] = None
    token_source: Optional[str] = None
    student_repo_modes: List[str] = field(default_factory=lambda: ["managed"])
    properties: Dict[str, Any] = field(default_factory=dict)
    members: List[MemberRepoPlan] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Database access — raw SQL against explicitly named columns.
#
# Deliberately not the ORM: this module is piped into a container whose backend
# code may be a different revision than the repository it came from, so binding
# to the SCHEMA (which it verifies) is safer than binding to model classes. It
# also keeps the import surface small enough to run anywhere.
# ---------------------------------------------------------------------------

def make_engine(database_url: Optional[str] = None) -> Engine:
    """Engine from ``--database-url``/``ADOPT_DATABASE_URL``, else ``POSTGRES_*``.

    The calling shell decides where to point: the published host port when run
    from the repo, the container's own coordinates when piped inside. Built with
    ``URL.create`` so a password containing ``@ / % :`` survives.
    """
    url = database_url or os.environ.get("ADOPT_DATABASE_URL")
    if url:
        return create_engine(url)

    missing = [k for k in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"!! missing database configuration: {', '.join(missing)}")

    return create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DB"],
        )
    )


def current_head(conn) -> Optional[str]:
    try:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return None


def assert_release_schema(conn) -> None:
    """Fail clearly, not with an opaque UndefinedColumn, when the target has not
    been migrated yet."""
    head = current_head(conn)
    if head == LEGACY_HEAD:
        raise SystemExit(
            f"!! database is still at the legacy head ({LEGACY_HEAD}).\n"
            "   Run `alembic upgrade head` first — but stash the org token BEFORE\n"
            "   that, with: adopt_legacy_git.py --stash-org-git --apply"
        )
    for table in ("git_server", "course_git_binding", "course_member_repository"):
        if conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar() is None:
            raise SystemExit(f"!! table '{table}' is missing; is this the right database?")


def stash_org_git(conn, *, apply: bool) -> int:
    """Copy ``organization.properties.gitlab`` to a ``gitlab_legacy`` sibling.

    Migration ``b1c2d3e4f5a6`` strips ``token`` and ``url`` out of the ``gitlab``
    key and ``f0a1b2c3d4e5`` drops the table they were moved to, so without this
    there is nothing left to bridge after migrating.

    The copy is a SIBLING key on purpose: the migration only rewrites
    ``properties->'gitlab'``, and ``OrganizationProperties`` allows extra
    top-level keys, whereas a key nested inside ``gitlab`` would be dropped on
    the next pydantic round-trip.
    """
    count = conn.execute(text(
        "SELECT count(*) FROM organization "
        "WHERE properties ? 'gitlab' AND NOT (properties ? 'gitlab_legacy')"
    )).scalar() or 0
    if apply and count:
        conn.execute(text(
            "UPDATE organization "
            "SET properties = jsonb_set(properties, '{gitlab_legacy}', properties->'gitlab', true) "
            "WHERE properties ? 'gitlab' AND NOT (properties ? 'gitlab_legacy')"
        ))
    return count


def forget_stash(conn) -> int:
    """Drop the stash once its contents are safely on the bindings.

    It holds an encrypted token and ``OrganizationProperties`` echoes extra keys
    to organization readers, so it must not outlive the adoption.
    """
    result = conn.execute(text(
        "UPDATE organization SET properties = properties - 'gitlab_legacy' "
        "WHERE properties ? 'gitlab_legacy'"
    ))
    return result.rowcount or 0


def load_legacy_courses(conn, only: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Every course carrying a legacy GitLab blob, with its org and family blobs.

    The organization blob is read from the stash first so this works both before
    and after ``alembic upgrade head``.
    """
    sql = """
        SELECT c.id, c.title, c.properties->'gitlab' AS course_gitlab,
               o.title AS org_title,
               COALESCE(o.properties->'gitlab_legacy', o.properties->'gitlab') AS org_gitlab,
               cf.properties->'gitlab' AS family_gitlab
        FROM course c
        JOIN organization o ON o.id = c.organization_id
        LEFT JOIN course_family cf ON cf.id = c.course_family_id
        WHERE c.properties ? 'gitlab'
    """
    params: Dict[str, Any] = {}
    if only:
        sql += " AND c.id = ANY(CAST(:ids AS uuid[]))"
        params["ids"] = list(only)
    sql += " ORDER BY o.title, c.title"

    return [
        {
            "course_id": str(row[0]),
            "course_title": row[1] or "(untitled)",
            "course_gitlab": as_dict(row[2]),
            "org_title": row[3] or "(untitled)",
            "org_gitlab": as_dict(row[4]),
            "family_gitlab": as_dict(row[5]),
        }
        for row in conn.execute(text(sql), params).all()
    ]


def load_legacy_members(conn, course_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    rows = conn.execute(text(
        "SELECT id, properties->'gitlab' FROM course_member "
        "WHERE course_id = :c AND properties ? 'gitlab' ORDER BY id"
    ), {"c": course_id}).all()
    return [(str(r[0]), as_dict(r[1])) for r in rows]


def existing_binding(conn, course_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(text(
        "SELECT id, git_server_id, template_repo, template_url, properties "
        "FROM course_git_binding WHERE course_id = :c"
    ), {"c": course_id}).first()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "git_server_id": str(row[1]) if row[1] else None,
        "template_repo": row[2],
        "template_url": row[3],
        "properties": as_dict(row[4]),
    }


def existing_managed_repo_refs(conn) -> Set[Tuple[str, str]]:
    rows = conn.execute(text(
        "SELECT git_server_id, repo_ref FROM course_member_repository "
        "WHERE mode = 'managed' AND repo_ref IS NOT NULL AND git_server_id IS NOT NULL"
    )).all()
    return {(str(r[0]), r[1]) for r in rows}


def get_or_create_git_server(
    conn, base_url: str, name: Optional[str], *, apply: bool, cache: Dict[str, str]
) -> Optional[str]:
    if base_url in cache:
        return cache[base_url]

    row = conn.execute(text(
        "SELECT id FROM git_server WHERE type = 'gitlab' AND base_url = :u"
    ), {"u": base_url}).first()
    if row:
        cache[base_url] = str(row[0])
        return cache[base_url]

    if not apply:
        return None

    display = name or f"GitLab ({urlparse(base_url).netloc or base_url})"
    # managed=false: the credential lives on the binding, which
    # `_binding_has_managed_creds` accepts on its own for GitLab.
    new_id = conn.execute(text(
        "INSERT INTO git_server (type, base_url, name, managed) "
        "VALUES ('gitlab', :u, :n, false) RETURNING id"
    ), {"u": base_url, "n": display}).scalar()
    cache[base_url] = str(new_id)
    return cache[base_url]


def write_binding(conn, plan: CoursePlan, git_server_id: str, default_branch: str) -> None:
    conn.execute(text("""
        INSERT INTO course_git_binding
            (course_id, delivery, git_server_id, template_repo, template_url,
             default_branch, token, student_repo_modes, properties)
        VALUES (:c, 'git', :srv, :repo, :url, :branch, :token,
                CAST(:modes AS jsonb), CAST(:props AS jsonb))
    """), {
        "c": plan.course_id,
        "srv": git_server_id,
        "repo": plan.template_repo,
        "url": plan.template_url,
        "branch": default_branch,
        "token": plan.token_ciphertext,
        "modes": json.dumps(plan.student_repo_modes),
        "props": json.dumps(plan.properties),
    })


def repair_binding(conn, plan: CoursePlan) -> None:
    """Update only ``properties.gitlab`` (and the mode list) on an adopted binding.

    Identity columns are never touched: repointing ``git_server_id`` or
    ``template_repo`` after student repositories exist would orphan every
    student's ``origin`` remote — which is exactly what the binding lock in the
    API exists to prevent, and why this writes rows directly instead of going
    through the bind endpoint.
    """
    conn.execute(text("""
        UPDATE course_git_binding
        SET properties = jsonb_set(
                COALESCE(properties, '{}'::jsonb), '{gitlab}',
                COALESCE(properties->'gitlab', '{}'::jsonb) || CAST(:patch AS jsonb), true),
            student_repo_modes = CAST(:modes AS jsonb),
            updated_at = now()
        WHERE course_id = :c
          AND properties->'gitlab'->'adopted' IS NOT NULL
    """), {
        "c": plan.course_id,
        "patch": json.dumps(plan.properties.get("gitlab", {})),
        "modes": json.dumps(plan.student_repo_modes),
    })


def write_member_repos(conn, plan: CoursePlan, git_server_id: str, server_url: str) -> int:
    written = 0
    for member in plan.members:
        result = conn.execute(text("""
            INSERT INTO course_member_repository
                (course_member_id, mode, git_server_id, server_url, repo_ref,
                 http_url, ssh_url, web_url, properties)
            VALUES (:m, :mode, :srv, :server_url, :ref, :http, :ssh, :web,
                    CAST(:props AS jsonb))
            ON CONFLICT (course_member_id) DO NOTHING
        """), {
            "m": member.course_member_id,
            "mode": member.mode,
            "srv": git_server_id,
            "server_url": server_url,
            "ref": member.repo_ref,
            "http": member.http_url,
            "ssh": member.ssh_url,
            "web": member.web_url,
            "props": json.dumps(member.properties),
        })
        written += result.rowcount or 0
    return written


# ---------------------------------------------------------------------------
# Optional, read-only GitLab lookups
# ---------------------------------------------------------------------------

def _resolvers(base_url: str, token: str):
    """``(resolve_project, resolve_group)`` for a GitLab instance.

    Prefers the backend's provider client for its Docker-aware URL handling, and
    falls back to a bare python-gitlab client when the installed backend
    predates ``resolve_project`` — which is the normal case when this module is
    piped into a container built from an older revision.
    """
    try:
        from computor_backend.git_provider.gitlab import (  # noqa: WPS433 (lazy on purpose)
            GitLabProviderClient,
            make_gitlab_client,
        )

        client = GitLabProviderClient(base_url, token, None)
        if hasattr(client, "resolve_project"):
            return client.resolve_project, client.resolve_group
        gl = make_gitlab_client(base_url, token)
    except Exception:
        import gitlab as python_gitlab

        gl = python_gitlab.Gitlab(url=base_url, private_token=token, keep_base_url=True)

    return (lambda ref: gl.projects.get(ref)), (lambda ref: gl.groups.get(ref))


def resolve_gitlab_ids(
    base_url: str,
    token: str,
    *,
    template_path: str,
    reference_path: Optional[str],
    students_group_path: Optional[str],
) -> Dict[str, Any]:
    """Numeric ids for repositories the legacy system already created.

    ``_provision_gitlab_managed`` forks by project id, and the legacy blob never
    stored one. Read-only: nothing is created, renamed or deleted.
    """
    get_project, get_group = _resolvers(base_url, token)
    found: Dict[str, Any] = {}

    template = get_project(template_path)
    found["template_project_id"] = int(template.id)
    found["template_path"] = template.path_with_namespace

    if reference_path:
        try:
            reference = get_project(reference_path)
            found["reference_project_id"] = int(reference.id)
            found["reference_path"] = reference.path_with_namespace
        except Exception:
            # A missing reference repo disables the solution push, nothing more.
            pass

    if students_group_path:
        try:
            students = get_group(students_group_path)
            found["students_group_id"] = int(students.id)
            found["students_group_path"] = students.full_path
        except Exception:
            pass

    return found


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def plan_course(
    conn,
    record: Dict[str, Any],
    args: argparse.Namespace,
    secrets: Dict[str, str],
    adopted_at: str,
) -> CoursePlan:
    course_gitlab = record["course_gitlab"]
    org_gitlab = record["org_gitlab"]

    plan = CoursePlan(
        course_id=record["course_id"],
        course_title=record["course_title"],
        org_title=record["org_title"],
    )

    bound = existing_binding(conn, plan.course_id)
    adopted = bool(bound and (bound["properties"].get("gitlab") or {}).get("adopted"))
    if bound and not adopted:
        plan.action = "skip"
        plan.skip_reason = f"already bound to {bound['template_repo']!r} by something other than this tool"
        return plan
    if bound and not args.repair:
        plan.action = "skip"
        plan.skip_reason = "already adopted (re-run with --repair to refresh it)"
        return plan
    if not bound and args.repair:
        plan.action = "skip"
        plan.skip_reason = "no adopted binding to repair"
        return plan
    plan.action = "repair" if bound else "create"

    plan.base_url = legacy_base_url(course_gitlab, org_gitlab, args.gitlab_base_url)
    if not plan.base_url:
        plan.action = "skip"
        plan.skip_reason = "no GitLab base URL on the course or organization (pass --gitlab-base-url)"
        return plan

    plan.template_repo, plan.template_url = legacy_template_ref(course_gitlab, plan.base_url)
    if not plan.template_repo:
        plan.action = "skip"
        plan.skip_reason = f"no student-template found (gitlab keys: {sorted(course_gitlab)})"
        return plan

    plan.reference_path, _ = legacy_reference_ref(course_gitlab, plan.base_url)
    if not plan.reference_path:
        plan.warnings.append("no assignments repository found — the reference push stays disabled")

    # --- credential ------------------------------------------------------
    token_candidates = (
        ("organization", org_gitlab.get("token")),
        ("course", course_gitlab.get("token")),
    )
    for source, ciphertext in token_candidates:
        if not ciphertext:
            continue
        try:
            plan.token_ciphertext = bridge_token(ciphertext, secrets["legacy"], secrets["new"])
            plan.token_source = source
            break
        except Exception as exc:
            plan.action = "skip"
            plan.skip_reason = f"could not decrypt the {source} token ({exc}) — wrong LEGACY_TOKEN_SECRET?"
            return plan

    if plan.token_ciphertext is None and secrets.get("gitlab_pat"):
        from keycove import encrypt

        plan.token_ciphertext = encrypt(secrets["gitlab_pat"], secrets["new"])
        plan.token_source = "ADOPT_GITLAB_TOKEN"

    if plan.token_ciphertext is None:
        plan.warnings.append(
            "no token could be bridged — the binding will have no credential "
            "(did you run --stash-org-git before migrating?)"
        )

    # --- ids -------------------------------------------------------------
    resolved: Dict[str, Any] = {}
    degraded: Optional[str] = None
    group_ids = legacy_group_ids(course_gitlab)

    if args.resolve_ids:
        if not plan.token_ciphertext:
            degraded = "no_token"
            plan.warnings.append("cannot resolve ids without a token")
        else:
            from keycove import decrypt

            try:
                resolved = resolve_gitlab_ids(
                    plan.base_url,
                    decrypt(plan.token_ciphertext, secrets["new"]),
                    template_path=plan.template_repo,
                    reference_path=plan.reference_path,
                    students_group_path=group_ids.get("students_group_path"),
                )
            except Exception as exc:
                degraded = "resolution_failed"
                if args.on_resolve_failure == "abort-run":
                    raise SystemExit(f"!! GitLab lookup failed for {plan.course_title}: {exc}")
                if args.on_resolve_failure == "skip-course":
                    plan.action = "skip"
                    plan.skip_reason = f"GitLab lookup failed ({exc})"
                    return plan
                plan.warnings.append(f"GitLab lookup failed ({exc}); adopting without ids")
    else:
        degraded = "not_resolved"

    have_ids = bool(resolved.get("template_project_id")) and bool(
        resolved.get("students_group_id") or group_ids.get("students_group_id")
    )
    if not have_ids:
        # A binding advertising "managed" that cannot fork is a trap: the student
        # gets an error instead of a repository. Existing students are unaffected
        # — provision short-circuits on their adopted member row before the mode
        # list is consulted — so this only gates NEW students until --repair runs.
        plan.student_repo_modes = []
        plan.warnings.append(
            "student_repo_modes left empty: no template project id "
            "(re-run with --repair --resolve-ids to enable managed provisioning)"
        )

    plan.properties = build_binding_properties(
        course_gitlab,
        template_repo=plan.template_repo,
        template_url=plan.template_url,
        reference_path=plan.reference_path,
        resolved_ids=resolved,
        token_source=plan.token_source,
        ids_degraded=degraded,
        adopted_at=adopted_at,
    )

    # --- members ---------------------------------------------------------
    if args.members:
        for member_id, member_gitlab in load_legacy_members(conn, plan.course_id):
            member_plan = build_member_repo_plan(
                member_id, member_gitlab, plan.base_url,
                mode=args.member_mode, adopted_at=adopted_at,
            )
            if member_plan is None:
                plan.warnings.append(f"member {member_id} has no repository path — skipped")
                continue
            plan.members.append(member_plan)

    return plan


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_plan(plans: Sequence[CoursePlan], *, apply: bool) -> None:
    print()
    print(f"   === adoption {'APPLY' if apply else 'DRY-RUN'} ===")
    print()
    for plan in plans:
        print(f"   - {plan.course_title}  (org: {plan.org_title})")
        if plan.action == "skip":
            print(f"       -> SKIP  {plan.skip_reason}")
            continue
        gitlab = plan.properties.get("gitlab", {})
        print(f"       -> {plan.action.upper()}  server={plan.base_url}")
        print(f"          template  {plan.template_repo}")
        print(f"          reference {plan.reference_path or '(none)'}")
        print(
            "          ids       "
            f"template_project={gitlab.get('template_project_id', '-')} "
            f"students_group={gitlab.get('students_group_id', '-')} "
            f"parent={gitlab.get('parent_group_id', '-')}"
        )
        print(
            f"          token     {plan.token_source or 'NONE'}"
            f"   modes={plan.student_repo_modes or '[]'}"
            f"   members={len(plan.members)}"
        )
        for warning in plan.warnings:
            print(f"          !  {warning}")
    print()


def run_preflight(conn) -> int:
    """Read-only checks, meant to run on the restored database BEFORE migrating.

    Everything here is cheaper to learn now than after a restore plus 29
    migrations.
    """
    problems = 0
    head = current_head(conn)
    print(f"   alembic head: {head}")
    if head != LEGACY_HEAD:
        print(f"   !  expected the legacy head {LEGACY_HEAD}")

    tokens = conn.execute(text(
        "SELECT count(*) FROM organization WHERE properties->'gitlab'->>'token' IS NOT NULL"
    )).scalar() or 0
    print(f"   organizations with a GitLab token: {tokens}")
    if not tokens:
        problems += 1
        print("   !! no org token found — adoption would produce tokenless bindings.")
        print("      If you have already migrated, the token is GONE (b1c2d3e4f5a6 +")
        print("      f0a1b2c3d4e5); restore again and run --stash-org-git first.")

    courses = conn.execute(text("SELECT count(*) FROM course WHERE properties ? 'gitlab'")).scalar() or 0
    print(f"   courses carrying properties.gitlab: {courses}")

    missing_template = conn.execute(text(
        "SELECT count(*) FROM course WHERE properties ? 'gitlab' "
        "AND properties->'gitlab'->'projects'->'student_template'->>'full_path' IS NULL"
    )).scalar() or 0
    if missing_template:
        print(f"   !  {missing_template} course(s) fall back to a conventional template path")

    internal = conn.execute(text(
        "SELECT DISTINCT properties->'gitlab'->>'url' FROM course "
        "WHERE properties ? 'gitlab' AND properties->'gitlab'->>'url' IS NOT NULL"
    )).all()
    for (url,) in internal:
        host = urlparse(url).hostname or ""
        if host in {"localhost", "127.0.0.1"} or "." not in host:
            problems += 1
            print(f"   !! base URL looks internal: {url} — it is student-facing")

    duplicates = conn.execute(text("""
        SELECT properties->'gitlab'->>'full_path' AS p, count(*) AS n
        FROM course_member WHERE properties->'gitlab'->>'full_path' IS NOT NULL
        GROUP BY p HAVING count(*) > 1
    """)).all()
    if duplicates:
        problems += 1
        print(f"   !! {len(duplicates)} repository path(s) claimed by more than one member")

    emails = conn.execute(text("""
        WITH emails AS (
          SELECT id AS user_id, lower(email) AS em FROM "user" WHERE email IS NOT NULL
          UNION ALL
          SELECT user_id, lower(student_email) FROM student_profile WHERE student_email IS NOT NULL
        )
        SELECT em FROM emails GROUP BY em HAVING count(DISTINCT user_id) > 1
    """)).all()
    if emails:
        problems += 1
        print(f"   !! {len(emails)} email(s) map to more than one user — those people cannot log in via SSO")

    teams = conn.execute(text(
        "SELECT count(*) FROM submission_group WHERE max_group_size > 1 AND properties ? 'gitlab'"
    )).scalar() or 0
    if teams:
        print(f"   i  {teams} team repositories — not adopted (the new model is one repo per member)")

    print()
    print("   preflight: " + ("OK" if not problems else f"{problems} blocking finding(s)"))
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adopt_legacy_git",
        description="Adopt legacy org-GitLab configuration into per-course git bindings.",
    )
    parser.add_argument("--apply", action="store_true", help="write (default: dry-run)")
    parser.add_argument("--preflight", action="store_true", help="read-only checks; run before migrating")
    parser.add_argument("--stash-org-git", action="store_true",
                        help="copy the org GitLab blob aside BEFORE `alembic upgrade head`")
    parser.add_argument("--forget-stash", action="store_true", help="remove the stash without adopting")
    parser.add_argument("--repair", action="store_true",
                        help="refresh properties on already-adopted bindings; never touches identity")
    parser.add_argument("--resolve-ids", action="store_true",
                        help="make READ-ONLY GitLab API calls to resolve project/group ids")
    parser.add_argument("--on-resolve-failure", choices=("skip-course", "degrade", "abort-run"),
                        default="skip-course")
    parser.add_argument("--members", dest="members", action="store_true", default=True,
                        help="adopt existing student repositories (default)")
    parser.add_argument("--no-members", dest="members", action="store_false")
    parser.add_argument("--member-mode", choices=("managed", "external"), default="managed")
    parser.add_argument("--gitlab-base-url", default=os.environ.get("GITLAB_BASE_URL") or None)
    parser.add_argument("--gitlab-name", default=os.environ.get("GITLAB_NAME") or None)
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--course", action="append", dest="courses", metavar="UUID",
                        help="limit to these course ids (repeatable)")
    parser.add_argument("--database-url", default=None)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    engine = make_engine(args.database_url)

    # --- phases that run at the LEGACY head -------------------------------
    if args.preflight:
        with engine.connect() as conn:
            return 1 if run_preflight(conn) else 0

    if args.stash_org_git:
        with engine.connect() as conn:
            transaction = conn.begin()
            count = stash_org_git(conn, apply=args.apply)
            if args.apply:
                transaction.commit()
                print(f">> stashed the GitLab blob of {count} organization(s) as properties.gitlab_legacy")
                print("   Now run `alembic upgrade head`, then adopt.")
            else:
                transaction.rollback()
                print(f">> DRY-RUN: would stash {count} organization(s). Re-run with --apply.")
        return 0

    if args.forget_stash:
        with engine.connect() as conn:
            transaction = conn.begin()
            count = forget_stash(conn)
            transaction.commit() if args.apply else transaction.rollback()
            print(f">> {'removed' if args.apply else 'would remove'} the stash from {count} organization(s)")
        return 0

    # --- adoption proper --------------------------------------------------
    secrets = {
        "new": os.environ.get("TOKEN_SECRET") or "",
        "legacy": os.environ.get("LEGACY_TOKEN_SECRET") or os.environ.get("TOKEN_SECRET") or "",
        "gitlab_pat": os.environ.get("ADOPT_GITLAB_TOKEN") or "",
    }
    if not secrets["new"]:
        raise SystemExit("!! TOKEN_SECRET is not set; cannot encrypt tokens for this system")

    if args.resolve_ids:
        print("!! --resolve-ids: this run makes READ-ONLY GitLab API calls")
        print("   (GET /projects/<path>, GET /groups/<path>). It creates nothing.")

    adopted_at = datetime.now(timezone.utc).isoformat()

    with engine.connect() as conn:
        assert_release_schema(conn)
        transaction = conn.begin()
        try:
            records = load_legacy_courses(conn, args.courses)
            print(f"   {len(records)} course(s) carry properties.gitlab")

            plans = [plan_course(conn, r, args, secrets, adopted_at) for r in records]
            print_plan(plans, apply=args.apply)

            actionable = [p for p in plans if p.action != "skip"]
            if not args.apply:
                transaction.rollback()
                print(f"   === DRY-RUN: {len(actionable)} course(s) would be written. "
                      "Re-run with --apply. ===")
                return 0

            existing_refs = existing_managed_repo_refs(conn)
            server_cache: Dict[str, str] = {}
            created = repaired = members_written = 0

            for plan in actionable:
                git_server_id = get_or_create_git_server(
                    conn, plan.base_url, args.gitlab_name, apply=True, cache=server_cache
                )
                collisions = detect_repo_ref_collisions(plan.members, git_server_id, existing_refs)
                if collisions:
                    raise SystemExit(
                        f"!! repository path collision for {plan.course_title}: "
                        + ", ".join(collisions)
                        + "\n   Nothing was written. Resolve the duplicates and re-run."
                    )
                existing_refs.update((git_server_id, m.repo_ref) for m in plan.members)

                if plan.action == "create":
                    write_binding(conn, plan, git_server_id, args.default_branch)
                    created += 1
                else:
                    repair_binding(conn, plan)
                    repaired += 1
                members_written += write_member_repos(conn, plan, git_server_id, plan.base_url)

            forgotten = forget_stash(conn)
            transaction.commit()

            print(f"   === APPLIED: {created} created, {repaired} repaired, "
                  f"{members_written} student repositories adopted ===")
            if forgotten:
                print(f"   (removed the org token stash from {forgotten} organization(s))")
            print("   Restart the API and the Temporal workers to pick this up.")
            return 0
        except Exception:
            transaction.rollback()
            raise


if __name__ == "__main__":
    sys.exit(main())
