"""Verify that posting or deleting a message invalidates tutor_view cache.

Flow:
  1. Prime the tutor cache by calling list_tutor_course_members.
  2. Confirm the cache key exists in Redis.
  3. Create a new submission-group-scoped message (course_id=NULL on Message row).
  4. Confirm the tutor cache entry is gone.
  5. Repeat for soft-delete.
"""
import os
from uuid import UUID

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres_secret")
os.environ.setdefault("POSTGRES_DB", "codeability")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_PASSWORD", "redis_password")

from sqlalchemy import text

from computor_backend.database import SessionLocal
from computor_backend.redis_cache import get_cache
from computor_backend.business_logic.tutor import list_tutor_course_members
from computor_backend.business_logic.messages import (
    create_message_with_author,
    invalidate_tutor_lecturer_views_for_message,
)
from computor_backend.business_logic.message_operations import soft_delete_message
from computor_backend.permissions.principal import Principal, Claims
from computor_types.course_members import CourseMemberQuery
from computor_types.messages import MessageCreate
from computor_backend.model.message import Message
from computor_backend.model.course import CourseMember


COURSE_ID = "2fc15de7-40a7-4e85-b633-448823184684"


def tutor_cache_key_exists(cache) -> bool:
    """Return True if any cached tutor:course_members entry exists for any user."""
    # The cache key is user-scoped: computor:user_view:{user_id}:tutor:course_members:{params_hash}
    client = cache.client
    keys = list(client.scan_iter(match="computor:user_view:*:tutor:course_members:*"))
    return len(keys) > 0, keys


def make_principal(user_id: str, is_admin: bool = False) -> Principal:
    return Principal(
        is_admin=is_admin,
        user_id=user_id,
        roles=[],
        claims=Claims(general={}, dependent={}),
        permissions={},
    )


def step(label: str) -> None:
    print(f"\n=== {label} ===")


def main():
    cache = get_cache()

    # Resolve tutor + one seeded submission_group
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT cm.id AS tutor_member_id, cm.user_id AS tutor_user_id
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            WHERE cm.course_role_id = '_tutor'
              AND cm.course_id = :cid
              AND u.username LIKE 'bench_%%'
            ORDER BY u.created_at DESC LIMIT 1
        """), {"cid": COURSE_ID}).first()
        if not row:
            print("No benchmark tutor found. Run seed_tutor_benchmark.sql first.")
            return
        tutor_user_id = str(row.tutor_user_id)

        sg_row = db.execute(text("""
            SELECT sg.id AS sg_id, sg.course_content_id
            FROM submission_group sg
            JOIN course_content cc ON cc.id = sg.course_content_id
            WHERE sg.course_id = :cid
            LIMIT 1
        """), {"cid": COURSE_ID}).first()
        sg_id = str(sg_row.sg_id)
        cc_id = str(sg_row.course_content_id)

        # Find a student member of that submission_group to act as message author
        student_row = db.execute(text("""
            SELECT cm.user_id
            FROM submission_group_member sgm
            JOIN course_member cm ON cm.id = sgm.course_member_id
            WHERE sgm.submission_group_id = :sgid
            LIMIT 1
        """), {"sgid": sg_id}).first()
        author_user_id = str(student_row.user_id)

    print(f"tutor_user_id      = {tutor_user_id}")
    print(f"submission_group   = {sg_id}")
    print(f"course_content     = {cc_id}")
    print(f"author_user_id     = {author_user_id}")

    # ------------------------------------------------------------------
    # 1. Prime the tutor cache
    # ------------------------------------------------------------------
    step("1. Prime tutor cache (first call populates Redis)")
    cache.invalidate_tags(f"tutor_view:{COURSE_ID}")  # clean slate

    principal = make_principal(tutor_user_id)
    params = CourseMemberQuery(course_id=COURSE_ID)
    with SessionLocal() as db:
        list_tutor_course_members(principal, params, db, cache=cache)

    exists, keys = tutor_cache_key_exists(cache)
    print(f"cache keys after prime: {len(keys)}  -> {'PRESENT' if exists else 'MISSING'}")
    assert exists, "Cache should contain tutor view after first call"

    # ------------------------------------------------------------------
    # 2. Post a submission-group-scoped message (course_id=NULL on row)
    # ------------------------------------------------------------------
    step("2. Post new submission-group message as student author")

    author_principal = make_principal(author_user_id)
    with SessionLocal() as db:
        payload = MessageCreate(
            title="Invalidation test",
            content="Does this invalidate the tutor cache?",
            submission_group_id=sg_id,
            level=0,
        )
        model_dump = create_message_with_author(payload, author_principal, db)
        msg = Message(**model_dump)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        print(f"created message {msg.id}  (course_id on row = {msg.course_id})")
        # Call the invalidation helper as the endpoint would
        invalidate_tutor_lecturer_views_for_message(msg, db, cache)
        created_msg_id = msg.id

    exists, keys = tutor_cache_key_exists(cache)
    print(f"cache keys after create: {len(keys)}  -> {'PRESENT (BUG)' if exists else 'CLEARED ✓'}")
    assert not exists, "Cache should be cleared after message create"

    # ------------------------------------------------------------------
    # 3. Re-prime, then soft-delete, verify invalidation
    # ------------------------------------------------------------------
    step("3. Re-prime, then soft-delete and check again")
    with SessionLocal() as db:
        list_tutor_course_members(principal, params, db, cache=cache)
    exists, _ = tutor_cache_key_exists(cache)
    print(f"cache keys after re-prime: {'PRESENT' if exists else 'MISSING'}")
    assert exists

    with SessionLocal() as db:
        deleted = soft_delete_message(
            message_id=created_msg_id,
            principal=author_principal,
            db=db,
            reason="verification_test",
        )
        invalidate_tutor_lecturer_views_for_message(deleted, db, cache)

    exists, _ = tutor_cache_key_exists(cache)
    print(f"cache keys after delete: {'PRESENT (BUG)' if exists else 'CLEARED ✓'}")
    assert not exists, "Cache should be cleared after message delete"

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
