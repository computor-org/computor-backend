#!/usr/bin/env python3
"""Bring deployed courses' metadata in line with their course files.

``deploy-course`` only creates courses, so a later content release that renames
a course, retitles an item or adds a unit never reaches a deployed instance.
This compares each ``courses/*.yaml`` (a ``HierarchicalCourseConfig``) with the
course of the same path and reports every difference; ``--apply`` writes the
ones that are metadata only:

- course title, description and position,
- content type titles and colours, and missing content types,
- content titles, descriptions and positions,
- missing units (non-submittable contents),
- units the file no longer has (archived and hidden), unless an assignment is
  still deployed beneath them.

A missing assignment, a changed content type or an assignment the file no
longer has needs a release with examples and is only reported. The exit status
is 1 while any difference remains, so ``--check`` (the default) works as a
release gate.

Usage (database from the POSTGRES_* environment variables):
    python -m computor_backend.scripts.sync_course_metadata COURSES_DIR
    python -m computor_backend.scripts.sync_course_metadata COURSES_DIR --apply
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
)


@dataclass
class CourseDrift:
    path: str
    fixable: List[str] = field(default_factory=list)
    blocking: List[str] = field(default_factory=list)
    course_id: Optional[str] = None


def _walk(items, parent: Optional[str] = None):
    for item in items or []:
        full = f"{parent}.{item['path']}" if parent else str(item["path"])
        yield full, item
        yield from _walk(item.get("contents"), full)


def _differs(current: Any, wanted: Any) -> bool:
    if isinstance(wanted, (int, float)) and current is not None:
        return float(current) != float(wanted)
    return current != wanted


def sync_course(db: Session, config: Dict[str, Any], apply: bool) -> CourseDrift:
    """Compare (and with ``apply`` fix) one course; flushes but does not commit."""
    drift = CourseDrift(path=str(config["path"]))
    courses = (
        db.query(Course)
        .filter(Course.path == Ltree(drift.path), Course.archived_at.is_(None))
        .all()
    )
    if len(courses) != 1:
        drift.blocking.append(f"{len(courses)} active courses with path {drift.path}")
        return drift
    course = courses[0]
    drift.course_id = str(course.id)

    def update(entity, label: str, wanted: Dict[str, Any]) -> None:
        for attr, value in wanted.items():
            if _differs(getattr(entity, attr), value):
                drift.fixable.append(f"{label} {attr}: {getattr(entity, attr)!r} -> {value!r}")
                if apply:
                    setattr(entity, attr, value)

    course_fields = {"title": config.get("name")}
    for key in ("description", "position"):
        if key in config:
            course_fields[key] = config[key]
    update(course, "course", course_fields)

    kinds = {k.id: k for k in db.query(CourseContentKind).all()}
    types = {
        (t.slug, t.course_content_kind_id): t
        for t in db.query(CourseContentType).filter(CourseContentType.course_id == course.id)
    }
    for ct in config.get("content_types") or []:
        key = (ct["slug"], ct["kind"])
        if key in types:
            update(types[key], f"content type {ct['slug']}", {"title": ct.get("title"), "color": ct.get("color")})
            continue
        drift.fixable.append(f"content type {ct['slug']} ({ct['kind']}) missing")
        if apply:
            types[key] = CourseContentType(
                slug=ct["slug"],
                title=ct.get("title"),
                color=ct.get("color"),
                properties=dict(ct.get("properties") or {}),
                course_content_kind_id=ct["kind"],
                course_id=course.id,
            )
            db.add(types[key])
            db.flush()
    kinds_by_slug: Dict[str, List[str]] = {}
    for ct in config.get("content_types") or []:
        kinds_by_slug.setdefault(ct["slug"], []).append(ct["kind"])

    contents = {
        str(c.path): c
        for c in db.query(CourseContent).filter(
            CourseContent.course_id == course.id, CourseContent.archived_at.is_(None)
        )
    }
    wanted_paths = set()
    for full, item in _walk(config.get("contents")):
        wanted_paths.add(full)
        # The same slug may name a unit and an assignment; children decide.
        leaf = not item.get("contents")
        options = kinds_by_slug.get(item.get("content_type"), [])
        kind = next((k for k in options if kinds[k].submittable == leaf), options[0] if options else None)
        ct_row = types.get((item.get("content_type"), kind))
        fields = {"title": item.get("title")}
        for key in ("description", "position"):
            if key in item:
                fields[key] = item[key]
        row = contents.get(full)
        if row is None:
            if kind is None or kinds[kind].submittable:
                drift.blocking.append(f"{full} missing; needs a release with its example")
                continue
            drift.fixable.append(f"unit {full} missing")
            if apply:
                parent = full.rsplit(".", 1)[0] if "." in full else ""
                siblings = [c.position for p, c in contents.items()
                            if (p.rsplit(".", 1)[0] if "." in p else "") == parent]
                db.add(CourseContent(
                    title=fields["title"],
                    description=fields.get("description"),
                    path=Ltree(full),
                    course_id=course.id,
                    course_content_type_id=ct_row.id,
                    position=fields.get("position", max(siblings, default=0.0) + 1.0),
                    max_group_size=item.get("max_group_size") or 1,
                ))
                db.flush()
            continue
        if ct_row is not None and row.course_content_type_id != ct_row.id:
            drift.blocking.append(f"{full} has another content type than {item.get('content_type')}")
        update(row, full, fields)
    dropped = sorted(set(contents) - wanted_paths)
    for full in dropped:
        row = contents[full]
        # A dropped unit with no assignment left beneath it is metadata: it is
        # archived and hidden, as the student tree does not filter archived rows.
        if row.is_submittable or any(
            contents[p].is_submittable for p in dropped if p.startswith(f"{full}.")
        ):
            drift.blocking.append(f"{full} is deployed but not in the course file")
            continue
        drift.fixable.append(f"unit {full} dropped from the course file")
        if apply:
            row.archived_at = datetime.now(timezone.utc)
            row.visible = False
    return drift


def _invalidate(db: Session, course_ids: List[str]) -> None:
    from computor_backend.redis_cache import get_cache
    from computor_backend.repositories.course import CourseRepository
    from computor_backend.repositories.course_content_repo import CourseContentRepository

    cache = get_cache()
    course_repo = CourseRepository(db, cache)
    content_repo = CourseContentRepository(db, cache)
    for course_id in course_ids:
        course = db.get(Course, course_id)
        tags = set(course_repo.get_entity_tags(course)) | set(content_repo.get_list_tags(course_id=course_id))
        for content in db.query(CourseContent).filter(CourseContent.course_id == course_id):
            tags |= content_repo.get_entity_tags(content)
        cache.invalidate_tags(*tags)
        cache.invalidate_user_views(entity_type="course_id", entity_id=str(course_id))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("courses_dir", type=Path, help="directory with the courses/*.yaml files")
    parser.add_argument("--apply", action="store_true", help="write the metadata changes")
    args = parser.parse_args()

    files = sorted(args.courses_dir.glob("*.yaml"))
    if not files:
        print(f"no course files in {args.courses_dir}")
        return 2

    from computor_backend.database import get_db

    db = next(get_db())
    remaining = 0
    try:
        results = [
            sync_course(db, yaml.safe_load(f.read_text(encoding="utf-8")), args.apply) for f in files
        ]
        if args.apply:
            db.commit()
            _invalidate(db, [r.course_id for r in results if r.course_id and r.fixable])
        else:
            db.rollback()
    finally:
        db.close()

    verb = "fixed" if args.apply else "drift"
    for r in results:
        print(f"{r.path}: {len(r.fixable)} {verb}, {len(r.blocking)} need a release")
        for line in r.fixable:
            print(f"  {verb}: {line}")
        for line in r.blocking:
            print(f"  release: {line}")
        remaining += len(r.blocking) + (0 if args.apply else len(r.fixable))
    if remaining and not args.apply:
        print("Dry run; nothing was written. Re-run with --apply for the metadata changes.")
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
