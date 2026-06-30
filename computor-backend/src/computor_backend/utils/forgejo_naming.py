"""Collision-free, length-bounded Forgejo org/repo naming for course-level git.

Forgejo (Gitea) caps org/user names at **40** characters and repo names at
**100**; names may contain ``[A-Za-z0-9-_.]``, may not start or end with a
separator, and may not contain ``..``. *Every* name this module emits is
guaranteed to satisfy those rules — the length cap in particular is honoured in
every branch, so a name is never rejected by Forgejo for being too long.

Per-course org ("course_org" layout)
------------------------------------
Student repos for a course live in their **own** Forgejo organization, named
from the course's place in the hierarchy. Because a course ``path`` is only
unique *within its family* (not across an organization), the family is needed to
disambiguate two families that reuse a course slug. Candidates are produced most
readable first; the caller takes the first that is **free or already this
course's** (``allocate_course_org_name``), so uniqueness is resolved against
Forgejo, never assumed:

    1. ``{org}-{course}``                 short — the common case
    2. ``{org}-{family}-{course}``        disambiguates a slug shared across families
    3. ``{org}-{family}-{course}-{n}``    numeric suffix, last resort

Any candidate that would exceed 40 chars is truncated and given a 6-char hash of
the (globally unique) ``course_id`` so distinctness survives the cut, e.g.
``itpcp-<truncated>-a1b2c3``. The student repo within that org is simply the
realm-unique handle (``template`` / ``reference`` are reserved for staff repos).

This module is pure (no I/O): the caller injects an ``is_free`` predicate that
checks Forgejo / our own bindings.
"""
import hashlib
from typing import Callable, List

from text_unidecode import unidecode

from computor_backend.utils.git_username import FORGEJO_RESERVED

# Forgejo/Gitea hard limits.
ORG_NAME_MAX = 40
REPO_NAME_MAX = 100

# Hash length appended when a readable name is truncated to fit the cap.
_HASH_LEN = 6

# Repo names reserved for the course's staff repos — a student handle that
# equals one of these is suffixed so a fork can never adopt a staff repo.
STAFF_REPO_NAMES = frozenset({"template", "reference"})


def _hash(seed: str) -> str:
    """Short, stable, dash-free discriminator from a globally unique key."""
    return hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:_HASH_LEN]


def _sanitize(name: str) -> str:
    """Coerce a string into a Forgejo-valid name fragment (may be empty).

    Keeps ``[a-z0-9-_.]`` (replacing anything else with ``-``), collapses ``..``
    (forbidden by Forgejo), and strips leading/trailing separators. Does NOT
    enforce length — callers clamp via :func:`_fit`.
    """
    name = unidecode(str(name).lower())
    name = "".join(
        c if ((c.isalnum() and c.isascii()) or c in "-_.") else "-" for c in name
    )
    while ".." in name:
        name = name.replace("..", ".")
    return name.strip("-_.")


def _dash(ltree_path: str) -> str:
    """Render an ltree path as a sanitized, dash-joined name fragment.

    ltree labels are ``[A-Za-z0-9_]`` (never ``-``), so the only ``-`` come from
    the ``.`` separators — keeping the join unambiguous.
    """
    return _sanitize(str(ltree_path).replace(".", "-"))


def _leaf(ltree_path: str) -> str:
    """The course's own slug — the last label of its (possibly nested) path."""
    return str(ltree_path).split(".")[-1]


def _avoid_reserved(name: str) -> str:
    return f"{name}1" if name.lower() in FORGEJO_RESERVED else name


def _join(*parts: str) -> str:
    """Dash-join the non-empty fragments (so an absent family adds no ``--``)."""
    return "-".join(p for p in parts if p)


def _fit(readable: str, seed: str, *, suffix: str = "", max_len: int = ORG_NAME_MAX) -> str:
    """Return a Forgejo-valid name ``<= max_len`` chars, ending with ``suffix``.

    If ``readable + suffix`` already fits it is returned sanitized. Otherwise the
    readable part is truncated and a hash of ``seed`` is inserted before the
    suffix, so the result stays unique despite the cut.
    """
    readable = _avoid_reserved(_sanitize(readable)) or "course"
    if len(readable) + len(suffix) <= max_len:
        return _sanitize(readable + suffix)
    h = _hash(seed)
    keep = max_len - len(suffix) - 1 - len(h)  # room for "-{hash}{suffix}"
    base = _sanitize(readable[: max(keep, 1)]) or "course"
    return _sanitize(f"{base}-{h}{suffix}")


def course_org_candidates(
    org_path: str,
    family_path: str,
    course_path: str,
    course_id: str,
) -> List[str]:
    """Ordered, length-capped org-name candidates, most readable first.

    ``[ "{org}-{course}", "{org}-{family}-{course}" ]`` — deduped, each guaranteed
    ``<= ORG_NAME_MAX``. Numeric-suffix fallbacks are produced by
    :func:`allocate_course_org_name` when both are taken.
    """
    org = _dash(org_path)
    family = _dash(_leaf(family_path))
    course = _dash(_leaf(course_path))

    short = _fit(_join(org, course), course_id)
    full = _fit(_join(org, family, course), course_id)

    out: List[str] = []
    for c in (short, full):
        if c and c not in out:
            out.append(c)
    return out


def allocate_course_org_name(
    org_path: str,
    family_path: str,
    course_path: str,
    course_id: str,
    is_free: Callable[[str], bool],
    max_suffix: int = 9999,
) -> str:
    """First org name that ``is_free`` accepts, trying readable forms then
    numeric suffixes on the family-qualified form. Always ``<= ORG_NAME_MAX``.

    ``is_free(name)`` must return True when ``name`` is unclaimed *or* already
    belongs to this course (idempotent re-materialization) — i.e. it must never
    accept an org owned by a *different* course.
    """
    for candidate in course_org_candidates(org_path, family_path, course_path, course_id):
        if is_free(candidate):
            return candidate

    org = _dash(org_path)
    family = _dash(_leaf(family_path))
    course = _dash(_leaf(course_path))
    base = _join(org, family, course)
    for n in range(2, max_suffix + 1):
        candidate = _fit(base, course_id, suffix=f"-{n}")
        if is_free(candidate):
            return candidate
    raise ValueError(
        f"Could not allocate a unique Forgejo org name for course {course_id}"
    )


def student_repo_name_in_org(handle: str) -> str:
    """The student fork's repo name inside a per-course org: just the handle.

    The handle is already realm-unique and Forgejo-safe (``utils.git_username``),
    so within the course org it cannot collide with another student. Guards: cap
    to the repo limit and never equal a staff repo name.
    """
    name = _sanitize(handle)[:REPO_NAME_MAX] or "student"
    if name.lower() in STAFF_REPO_NAMES or name.lower() in FORGEJO_RESERVED:
        name = _sanitize(f"{name}-repo")[:REPO_NAME_MAX]
    return name
