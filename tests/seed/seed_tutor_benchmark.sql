-- Bulk seed for benchmarking the tutor /course-members endpoint.
--
-- Target: the existing "Programming in Physics PYTHON" course.
-- Creates 300 students + 1 tutor in a single course_group, attaches them to
-- 20 assignment-kind course_contents, then populates submission_groups,
-- artifacts, results, grades, and messages with realistic volumes.
--
-- The script is idempotent-ish: it picks up the existing course / content
-- types and only inserts net-new rows. Re-running duplicates the volume.
-- Wrapped in a transaction so a failure leaves the DB clean.
--
-- Scale:
--   course_member                ~301 new
--   submission_group            ~6000 new (20 contents × 300 students)
--   submission_group_member     ~6000 new
--   submission_artifact        ~12000 new (2 per sg: 1 submit, 1 non-submit)
--   result                     ~12000 new
--   submission_grade            ~3000 new
--   message                     ~3000 new

BEGIN;

-- ------------------------------------------------------------------
-- 0. Pin down the course and pick 20 assignment-kind course_contents
-- ------------------------------------------------------------------
CREATE TEMP TABLE _ctx AS
SELECT
    c.id                AS course_id,
    c.organization_id   AS organization_id
FROM course c
WHERE c.id = '2fc15de7-40a7-4e85-b633-448823184684';

CREATE TEMP TABLE _contents AS
SELECT cc.id, cc.course_content_type_id, row_number() OVER (ORDER BY cc.path) AS rn
FROM course_content cc
JOIN course_content_type cct ON cct.id = cc.course_content_type_id
WHERE cc.course_id = (SELECT course_id FROM _ctx)
  AND cct.course_content_kind_id = 'assignment'
  AND cc.archived_at IS NULL
ORDER BY cc.path
LIMIT 20;

-- ------------------------------------------------------------------
-- 1. Create a dedicated course_group for the seeded students
-- ------------------------------------------------------------------
INSERT INTO course_group (id, course_id, title, description)
VALUES (
    uuid_generate_v4(),
    (SELECT course_id FROM _ctx),
    'Benchmark Group ' || to_char(now(), 'YYYYMMDDHH24MISS'),
    'Synthetic group for EXPLAIN ANALYZE benchmarking'
)
RETURNING id;

-- Store the fresh group_id so downstream inserts can reference it
CREATE TEMP TABLE _group AS
SELECT id AS course_group_id
FROM course_group
WHERE course_id = (SELECT course_id FROM _ctx)
ORDER BY created_at DESC
LIMIT 1;

-- ------------------------------------------------------------------
-- 2. Insert 301 users (1 tutor + 300 students)
-- ------------------------------------------------------------------
CREATE TEMP TABLE _users AS
WITH inserted AS (
    INSERT INTO "user" (id, given_name, family_name, email, username)
    SELECT
        uuid_generate_v4(),
        'Given' || lpad(i::text, 4, '0'),
        'Family' || lpad(i::text, 4, '0'),
        'bench_' || to_char(now(), 'YYYYMMDDHH24MISS') || '_' || i || '@example.test',
        'bench_' || to_char(now(), 'YYYYMMDDHH24MISS') || '_' || i
    FROM generate_series(0, 300) AS i
    RETURNING id
)
SELECT id, row_number() OVER () AS rn FROM inserted;

-- ------------------------------------------------------------------
-- 3. Insert course_members
--    - rn=1 is the tutor (no course_group_id)
--    - rn=2..301 are students, bound to the course_group
-- ------------------------------------------------------------------
CREATE TEMP TABLE _members AS
WITH inserted AS (
    INSERT INTO course_member (id, user_id, course_id, course_group_id, course_role_id)
    SELECT
        uuid_generate_v4(),
        u.id,
        (SELECT course_id FROM _ctx),
        CASE WHEN u.rn = 1 THEN NULL ELSE (SELECT course_group_id FROM _group) END,
        CASE WHEN u.rn = 1 THEN '_tutor' ELSE '_student' END
    FROM _users u
    RETURNING id, user_id, course_role_id
)
SELECT
    i.id,
    i.user_id,
    i.course_role_id,
    row_number() OVER (ORDER BY i.id) AS rn
FROM inserted i;

-- ------------------------------------------------------------------
-- 4. Create one submission_group per (content, student) pair.
--    Tutor is skipped — only students submit.
-- ------------------------------------------------------------------
CREATE TEMP TABLE _sgroups AS
WITH inserted AS (
    INSERT INTO submission_group (id, course_id, course_content_id, max_group_size)
    SELECT
        uuid_generate_v4(),
        (SELECT course_id FROM _ctx),
        c.id,
        1
    FROM _contents c
    CROSS JOIN _members m
    WHERE m.course_role_id = '_student'
    RETURNING id, course_content_id
)
SELECT i.id, i.course_content_id, row_number() OVER () AS rn
FROM inserted i;

-- Map each submission_group back to its course_member
-- Need a stable mapping: pair sgroups to students 1:1 within each content
CREATE TEMP TABLE _sgroup_to_member AS
SELECT
    sg.id AS submission_group_id,
    sg.course_content_id,
    m.id AS course_member_id
FROM (
    SELECT id, course_content_id,
           row_number() OVER (PARTITION BY course_content_id ORDER BY id) AS student_rn
    FROM _sgroups
) sg
JOIN (
    SELECT id, row_number() OVER (ORDER BY id) AS student_rn
    FROM _members WHERE course_role_id = '_student'
) m ON m.student_rn = sg.student_rn;

-- ------------------------------------------------------------------
-- 5. Link students to submission_groups
-- ------------------------------------------------------------------
INSERT INTO submission_group_member (id, course_id, submission_group_id, course_member_id)
SELECT
    uuid_generate_v4(),
    (SELECT course_id FROM _ctx),
    m.submission_group_id,
    m.course_member_id
FROM _sgroup_to_member m;

-- ------------------------------------------------------------------
-- 6. Two submission_artifacts per submission_group
--    (one submit=true, one submit=false practice run)
-- ------------------------------------------------------------------
CREATE TEMP TABLE _artifacts AS
WITH inserted AS (
    INSERT INTO submission_artifact (
        id, submission_group_id, uploaded_by_course_member_id,
        file_size, bucket_name, object_key, submit, version_identifier
    )
    SELECT
        uuid_generate_v4(),
        s.submission_group_id,
        s.course_member_id,
        1024,
        'submissions',
        'bench/' || s.submission_group_id || '/' || v.vid,
        v.submit_flag,
        'v' || v.vid || '_' || substr(s.submission_group_id::text, 1, 8)
    FROM _sgroup_to_member s
    CROSS JOIN (
        VALUES (1, true), (2, false)
    ) AS v(vid, submit_flag)
    RETURNING id, submission_group_id, submit
)
SELECT * FROM inserted;

-- ------------------------------------------------------------------
-- 7. One result per artifact (status=0 FINISHED, test_system_id set)
-- ------------------------------------------------------------------
-- Need the course_content_type_id for each artifact -> go via sgroup
INSERT INTO result (
    id, course_member_id, submission_group_id, course_content_id,
    course_content_type_id, submission_artifact_id,
    test_system_id, version_identifier, status
)
SELECT
    uuid_generate_v4(),
    s.course_member_id,
    s.submission_group_id,
    s.course_content_id,
    c.course_content_type_id,
    a.id,
    'bench-testsys-' || substr(a.id::text, 1, 8),
    'res-' || substr(a.id::text, 1, 12),
    0
FROM _artifacts a
JOIN _sgroup_to_member s ON s.submission_group_id = a.submission_group_id
JOIN _contents c ON c.id = s.course_content_id;

-- ------------------------------------------------------------------
-- 8. submission_grade: grade half of the submit=true artifacts.
--    Mix of statuses so `is_unreviewed` logic exercises both branches.
-- ------------------------------------------------------------------
-- Grader is the tutor (first _tutor member)
INSERT INTO submission_grade (id, artifact_id, graded_by_course_member_id, grade, status)
SELECT
    uuid_generate_v4(),
    a.id,
    (SELECT id FROM _members WHERE course_role_id = '_tutor' LIMIT 1),
    (random())::numeric(4,2)::float,
    -- Half NOT_REVIEWED (0), quarter CORRECTED (1), quarter CORRECTION_NECESSARY (2)
    CASE (row_number() OVER ()) % 4
        WHEN 0 THEN 0
        WHEN 1 THEN 1
        WHEN 2 THEN 0
        WHEN 3 THEN 2
    END
FROM _artifacts a
WHERE a.submit = true
  AND (hashtext(a.id::text) % 2) = 0;  -- ~50% of submit=true artifacts

-- ------------------------------------------------------------------
-- 9. Messages: one per submission_group for ~half the groups
-- ------------------------------------------------------------------
-- Student authors a message on their own submission_group
INSERT INTO message (
    id, author_id, level, content,
    submission_group_id, course_content_id
)
SELECT
    uuid_generate_v4(),
    u.id,  -- student user id
    0,
    'Bench question #' || s.rn,
    s.submission_group_id,
    s.course_content_id
FROM (
    SELECT
        sg.id AS submission_group_id,
        sg.course_content_id,
        m.user_id AS student_user_id,
        row_number() OVER () AS rn
    FROM _sgroups sg
    JOIN _sgroup_to_member s2m ON s2m.submission_group_id = sg.id
    JOIN _members m ON m.id = s2m.course_member_id
    WHERE (hashtext(sg.id::text) % 2) = 0
) s
JOIN "user" u ON u.id = s.student_user_id;

-- ------------------------------------------------------------------
-- 10. Report what was inserted
-- ------------------------------------------------------------------
SELECT 'course_member'              AS tbl, count(*) FROM _members
UNION ALL SELECT 'submission_group',           count(*) FROM _sgroups
UNION ALL SELECT 'submission_artifact',        count(*) FROM _artifacts;

COMMIT;

-- Refresh stats so the planner can see the new volume
ANALYZE course_member;
ANALYZE submission_group;
ANALYZE submission_group_member;
ANALYZE submission_artifact;
ANALYZE result;
ANALYZE submission_grade;
ANALYZE message;

-- Emit the key IDs for subsequent EXPLAIN runs
SELECT 'course_id'        AS name, id::text AS value FROM course WHERE id = '2fc15de7-40a7-4e85-b633-448823184684'
UNION ALL
SELECT 'tutor_user_id',          u.id::text
    FROM "user" u
    JOIN course_member cm ON cm.user_id = u.id
    WHERE cm.course_role_id = '_tutor'
      AND cm.course_id = '2fc15de7-40a7-4e85-b633-448823184684'
      AND u.username LIKE 'bench_%'
    ORDER BY u.created_at DESC LIMIT 1;
