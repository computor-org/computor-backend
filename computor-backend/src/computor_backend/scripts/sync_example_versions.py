#!/usr/bin/env python3
"""Move deployed courses' assignments to the example versions of a content release.

``sync_course_metadata`` brings course texts in line with a content release, but
every assignment stays on the example version it was first released with, so a
new template, new tests or a new reference solution never reach a running
course while its instructions already describe them. This compares each
assignment of ``courses/*.yaml`` with the version of its example in the
release's ``examples/**/meta.yaml`` and reports:

- ``move``: the deployed version differs from the release's;
- ``release``: the version is right, but the student template has not been
  released since it was assigned (an interrupted ``--apply``);
- ``blocked``: anything else (no such course or assignment, another example,
  a deployed version newer than the release's, an assignment never released,
  or, with ``--examples``, a package without the release's version).

``--apply`` (refused while anything is blocked) uploads each missing version
from ``--examples`` to the example library, assigns it, releases the student
template of the moved assignments of each course and waits until every one of
them is deployed again. Submissions and results stay as they are. The exit
status is 1 while a ``move`` or ``release`` or ``blocked`` line remains, so the
default check mode works as a release gate and as the recheck.

Usage (database, MinIO and Temporal from the API container's environment):
    python -m computor_backend.scripts.sync_example_versions CONTENT_DIR [--examples DIR]
    python -m computor_backend.scripts.sync_example_versions CONTENT_DIR --examples DIR --apply

CONTENT_DIR holds ``courses/*.yaml`` and ``examples/**/meta.yaml`` of the
content release; DIR holds one directory per example with its full files
(``python/`` of the examples repository, with ``test.yaml`` and solutions).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from computor_backend.model.course import Course, CourseContent
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import Example, ExampleVersion
from computor_types.validation import SemanticVersion, normalize_version


@dataclass
class Item:
    course_path: str
    path: str
    identifier: str
    current: Optional[str]
    wanted: Optional[str]
    content_id: Optional[str] = None
    course_id: Optional[str] = None


@dataclass
class CourseVersions:
    path: str
    course_id: Optional[str] = None
    moves: List[Item] = field(default_factory=list)
    releases: List[Item] = field(default_factory=list)
    blocked: List[str] = field(default_factory=list)


def _walk(items, parent: Optional[str] = None):
    for item in items or []:
        full = f"{parent}.{item['path']}" if parent else str(item["path"])
        yield full, item
        yield from _walk(item.get("contents"), full)


def _key(version: str) -> Tuple[int, int, int]:
    v = SemanticVersion.from_string(version)
    return (v.major, v.minor, v.patch)


def release_versions(content_dir: Path) -> Dict[str, str]:
    """Example identifier -> normalized version from the release's meta.yaml files."""
    versions = {}
    for meta_path in sorted(content_dir.glob("examples/**/meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if meta.get("slug") and meta.get("version") is not None:
            versions[str(meta["slug"])] = normalize_version(str(meta["version"]))
    return versions


def package_examples(examples_dir: Optional[Path]) -> Dict[str, Tuple[Path, str]]:
    """Example identifier -> (directory, normalized version) of the examples package."""
    found: Dict[str, Tuple[Path, str]] = {}
    if examples_dir is None:
        return found
    for meta_path in sorted(examples_dir.glob("*/meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if meta.get("slug") and meta.get("version") is not None:
            found[str(meta["slug"])] = (meta_path.parent, normalize_version(str(meta["version"])))
    return found


def _released_since_assigned(deployment: CourseContentDeployment) -> bool:
    return (
        deployment.deployment_status == "deployed"
        and deployment.deployed_at is not None
        and (deployment.assigned_at is None or deployment.deployed_at >= deployment.assigned_at)
    )


def check_course(
    db: Session,
    config: Dict[str, Any],
    wanted_versions: Dict[str, str],
    package: Optional[Dict[str, Tuple[Path, str]]] = None,
) -> CourseVersions:
    """Compare the example versions of one course with the release's."""
    result = CourseVersions(path=str(config["path"]))
    courses = (
        db.query(Course)
        .filter(Course.path == Ltree(result.path), Course.archived_at.is_(None))
        .all()
    )
    if len(courses) != 1:
        result.blocked.append(f"{len(courses)} active courses with path {result.path}")
        return result
    course = courses[0]
    result.course_id = str(course.id)

    for full, entry in _walk(config.get("contents")):
        identifier = entry.get("example_identifier")
        if not identifier:
            continue
        wanted = wanted_versions.get(identifier)
        if wanted is None:
            result.blocked.append(f"{full}: the release has no meta.yaml for {identifier}")
            continue
        content = (
            db.query(CourseContent)
            .filter(
                CourseContent.course_id == course.id,
                CourseContent.path == Ltree(full),
                CourseContent.archived_at.is_(None),
            )
            .first()
        )
        deployment = content.deployment if content is not None else None
        if deployment is None:
            result.blocked.append(f"{full}: no deployed assignment; needs a content release")
            continue
        if str(deployment.example_identifier) != identifier:
            result.blocked.append(
                f"{full}: deployed example {deployment.example_identifier}, the release has {identifier}"
            )
            continue
        if deployment.deployed_at is None:
            result.blocked.append(f"{full}: {identifier} was never released; needs a content release")
            continue
        item = Item(result.path, full, identifier, deployment.version_tag, wanted,
                    str(content.id), result.course_id)
        if deployment.version_tag != wanted:
            if _key(deployment.version_tag) > _key(wanted):
                result.blocked.append(
                    f"{full}: deployed {identifier} {deployment.version_tag} is newer than the release's {wanted}"
                )
                continue
            if package is not None:
                have = package.get(identifier)
                if have is None or have[1] != wanted:
                    result.blocked.append(
                        f"{full}: the examples package has {identifier} "
                        f"{have[1] if have else 'not at all'}, the release needs {wanted}"
                    )
                    continue
            result.moves.append(item)
        elif not _released_since_assigned(deployment):
            result.releases.append(item)
    return result


def example_files(directory: Path) -> Dict[str, str]:
    """Every file of an example directory as the upload expects it (binary as base64)."""
    files = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        try:
            files[path.relative_to(directory).as_posix()] = data.decode("utf-8")
        except UnicodeDecodeError:
            files[path.relative_to(directory).as_posix()] = base64.b64encode(data).decode("ascii")
    return files


def _principal():
    from computor_backend.permissions.principal import Principal

    # Operator context like the startup bootstrap: audit columns stay NULL.
    return Principal(is_admin=True, roles=["_admin"])


async def _upload_missing(db: Session, moves: List[Item], package, principal) -> int:
    # The upload endpoint is the one write path for MinIO objects, version rows
    # and test dependencies, so it is called rather than reimplemented.
    from computor_backend.api.examples import upload_example
    from computor_backend.services.storage_service import get_storage_service
    from computor_types.example import ExampleUploadRequest

    storage = get_storage_service()
    uploaded = 0
    for identifier, version in sorted({(m.identifier, m.wanted) for m in moves}):
        example = db.query(Example).filter(Example.identifier == Ltree(identifier)).one()
        exists = (
            db.query(ExampleVersion)
            .filter(ExampleVersion.example_id == example.id, ExampleVersion.version_tag == version)
            .first()
        )
        if exists is not None:
            # A stored version is never overwritten: courses may grade against it.
            continue
        directory, _ = package[identifier]
        request = ExampleUploadRequest(
            repository_id=str(example.example_repository_id),
            directory=example.directory,
            files=example_files(directory),
        )
        await upload_example(request, db=db, permissions=principal, storage_service=storage)
        db.commit()
        uploaded += 1
        print(f"  uploaded: {identifier} {version}")
    return uploaded


async def _wait(workflow_id: str, label: str, timeout: float) -> None:
    from computor_backend.tasks.temporal_executor import get_task_executor

    executor = get_task_executor()
    started = time.monotonic()
    while True:
        info = await executor.get_task_status(workflow_id)
        status = getattr(info.status, "value", info.status)
        if status == "finished":
            return
        if status in ("failed", "cancelled"):
            raise RuntimeError(f"{label}: workflow {workflow_id} {status}: {info.error}")
        if time.monotonic() - started > timeout:
            raise RuntimeError(f"{label}: workflow {workflow_id} still {status} after {timeout:.0f} s")
        await asyncio.sleep(5)


async def apply(db: Session, results: List[CourseVersions], package, timeout: float) -> None:
    from computor_backend.api.system import generate_student_template
    from computor_backend.business_logic.lecturer_deployment import assign_example_to_content
    from computor_backend.redis_cache import get_cache
    from computor_types.system import GenerateTemplateRequest, ReleaseSelection

    principal = _principal()
    moves = [m for r in results for m in r.moves]
    await _upload_missing(db, moves, package, principal)

    cache = get_cache()
    for item in moves:
        assign_example_to_content(
            course_content_id=item.content_id,
            example_identifier=item.identifier,
            version_tag=item.wanted,
            permissions=principal,
            db=db,
        )
        print(f"  assigned: {item.course_path} {item.path} {item.identifier} {item.current} -> {item.wanted}")

    for r in results:
        ids = [m.content_id for m in r.moves + r.releases]
        if not ids:
            continue
        cache.invalidate_user_views(entity_type="course_id", entity_id=r.course_id)
        cache.invalidate_tags(f"lecturer_view:{r.course_id}")
        response = await generate_student_template(
            r.course_id,
            GenerateTemplateRequest(
                commit_message=f"Release {len(ids)} updated example version(s)",
                release=ReleaseSelection(course_content_ids=ids),
            ),
            permissions=principal,
            db=db,
        )
        print(f"  releasing: {r.path} student template workflow {response.workflow_id} ({len(ids)} assignment(s))")
        await _wait(response.workflow_id, f"{r.path} student template", timeout)
        print(f"  released: {r.path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("content_dir", type=Path, help="courses/*.yaml and examples/**/meta.yaml of the release")
    parser.add_argument("--examples", type=Path, help="examples package: one directory per example")
    parser.add_argument("--apply", action="store_true", help="upload, assign and release the new versions")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds to wait for each course's release")
    args = parser.parse_args()

    files = sorted(args.content_dir.glob("courses/*.yaml"))
    wanted = release_versions(args.content_dir)
    if not files or not wanted:
        print(f"no courses/*.yaml or examples/**/meta.yaml in {args.content_dir}")
        return 2
    package = package_examples(args.examples) if args.examples else None
    if args.examples and not package:
        print(f"no example directories with meta.yaml in {args.examples}")
        return 2

    from computor_backend.database import get_db

    db = next(get_db())
    try:
        configs = [yaml.safe_load(f.read_text(encoding="utf-8")) for f in files]
        results = [check_course(db, c, wanted, package) for c in configs]
        blocked = sum(len(r.blocked) for r in results)
        pending = sum(len(r.moves) + len(r.releases) for r in results)
        for r in results:
            print(f"{r.path}: {len(r.moves)} move, {len(r.releases)} to release, {len(r.blocked)} blocked")
            for m in r.moves:
                print(f"  move: {m.path} {m.identifier} {m.current} -> {m.wanted}")
            for m in r.releases:
                print(f"  release: {m.path} {m.identifier} {m.wanted}")
            for line in r.blocked:
                print(f"  blocked: {line}")
        if not args.apply:
            db.rollback()
            return 1 if blocked or pending else 0
        if blocked:
            print("Refusing --apply: blocked items need a content release first; nothing was written.")
            return 1
        if any(r.moves for r in results) and package is None:
            print("Refusing --apply: new versions need --examples; nothing was written.")
            return 1
        if pending:
            asyncio.run(apply(db, results, package, args.timeout))
        db.expire_all()
        after = [check_course(db, c, wanted) for c in configs]
        left = sum(len(r.moves) + len(r.releases) + len(r.blocked) for r in after)
        print(f"after apply: {left} assignment(s) still differ from the release or are not deployed")
        return 1 if left else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
