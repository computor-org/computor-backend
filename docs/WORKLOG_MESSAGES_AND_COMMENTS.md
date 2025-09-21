# Messages & Comments Refactor — Worklog

This file tracks what we changed, why, and what’s next. It’s the shared map for continuing this work later.

## Done

- API cleanup
  - Removed MR-based messaging routes from Students/Tutors and deleted GitLab helper.
  - Added generic `/course-member-comments` CRUD (tutor+ scoped).
  - Added DB-backed `/messages` with read/unread endpoints.

- DB model/schema
  - `message` table with `author_id` and flexible targets: `user_id | course_member_id | course_submission_group_id | course_group_id`.
  - `message_read` with `reader_user_id` and unique `(message_id, reader_user_id)`.
  - Updated `result` partial unique indexes to include `course_content_id`.
  - Moved grading to dedicated `course_submission_group_grading`.
  - Cleaned up `course_submission_group_member` (removed deprecated fields).
  - Consolidated Alembic: kept only the initial migration and folded needed changes into it (fresh DB start).

- Permissions
  - `MessagePermissionHandler`: authors always, direct user messages, member/group visibility, tutor+ course visibility; author-only update/delete.
  - Registered handler.

## Endpoints (current)

- Messages
  - `POST /messages`
  - `GET /messages`
  - `GET /messages/{id}`
  - `PATCH /messages/{id}`
  - `DELETE /messages/{id}`
  - `POST /messages/{id}/reads` (mark read)
  - `DELETE /messages/{id}/reads` (mark unread)
  - Responses include `is_read` for the current user on list/detail requests
  - Student/tutor course-content payloads surface `unread_message_count` for both the content and active submission group

- Course Member Comments
  - `GET /course-member-comments?course_member_id=...`
  - `POST /course-member-comments`
  - `PATCH /course-member-comments/{course_member_comment_id}`
  - `DELETE /course-member-comments/{course_member_comment_id}`

## Breaking Changes / Migration

- Only the initial Alembic migration remains; it now includes the messages schema and result index updates. Use a fresh DB.
- Tutor/student MR-based endpoints were removed. Frontend must switch to DB `/messages`.
- Message author field renamed to `author_id`.

## Open Tasks (Next Iteration)

- VS Code Integration
  - [x] Create lecturer webviews for Messages (course/course group/course content) and Course Member Comments.
  - [x] Add API wiring in extension for `/messages` and `/course-member-comments` endpoints.
  - [x] Surface commands in lecturer tree for viewing discussions and comments.
  - [ ] Student/tutor UI parity (port webviews from old extension for their contexts).

- Messages UX
  - [x] List unread counts per conversation/target (student/tutor content payloads now expose `unread_message_count`).
  - [ ] List readers for a message (optional).
  - [ ] Threaded queries: list by `parent_id`, cascade delete rules verified.
  - [ ] Sorting/pagination defaults, server-side caps.

- Grading API (planned)
  - [ ] Define endpoints for `course_submission_group_grading` (create/list/latest per group, permissions).
  - [ ] Surface grading in student/tutor views (DTO projections).

- Permissions
  - [ ] Double-check tutor+ visibility across all message targets (join plans, query performance).
  - [ ] Admin policy for comments/messages (currently blocked from authoring comments; revisit?).

- Frontend follow-up
  - [x] Port to `/messages` and `/course-member-comments` (VS Code lecturer UI).
  - [ ] Replace any MR-note readers with message reads.

- Tests
  - [ ] Add unit/integration tests for `messages` and permissions.
  - [ ] Add tests for `course-member-comments` ownership/role paths.

## Recent Work (2025-02)

- Added per-user `is_read` state to `/messages` results and aggregated unread counts on student/tutor course-content queries.
- Added `course_content_id` and `course_id` targets to the `Message` model, REST interface, and permission filters so non-submittable content can host discussions.
- Introduced Alembic migration `9b7a6f4f4a1d_add_course_content_to_messages.py` to persist the new columns, indexes, and foreign keys.
- Regenerated TypeScript DTOs and updated the VS Code extension’s `ComputorApiService` with helpers for messages and course-member comments.
- Implemented lecturer webviews:
  - `MessagesWebviewProvider` renders and posts threaded messages for courses, course groups, and course contents.
  - `CourseMemberCommentsWebviewProvider` manages tutor-side comments per course member.
- Wired new tree-context commands (`computor.lecturer.showMessages`, `computor.lecturer.showCourseMemberComments`) and removed the old dedicated assignment-command in favour of a unified course-content flow.

## Notes / Decisions

- Messages target simplification: user-level and group-level targets only (no course-only table yet; use `course_member_id` for course-context messages to a single member, `course_submission_group_id` for content contexts, `course_group_id` for cohort contexts).
- Read/unread is user-based (`reader_user_id`) rather than course-member based.
- We retained student submit (GitLab MR creation) feature; it’s separate from in-app messages.

## Quick Pointers

- Model files: `src/ctutor_backend/model/message.py`, `src/ctutor_backend/model/course.py`, `src/ctutor_backend/model/result.py`.
- API files: `src/ctutor_backend/api/messages.py`, `src/ctutor_backend/api/course_member_comments.py`.
- Permissions: `src/ctutor_backend/permissions/handlers_impl.py` (MessagePermissionHandler) and `permissions/core.py` registration.
- Initial migration: `src/ctutor_backend/alembic/versions/6c2c37382ca7_initial_schema_from_sqlalchemy_models.py`.
