DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO computor;

CREATE TABLE "user" (
    id uuid PRIMARY KEY,
    username text NOT NULL,
    email text NOT NULL,
    given_name text,
    family_name text
);

CREATE TABLE student_profile (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES "user"(id),
    student_id text NOT NULL
);

CREATE TABLE course (
    id uuid PRIMARY KEY,
    title text NOT NULL
);

CREATE TABLE course_content_kind (
    id text PRIMARY KEY,
    submittable boolean NOT NULL
);

CREATE TABLE course_content_type (
    id uuid PRIMARY KEY,
    slug text NOT NULL,
    title text NOT NULL,
    color text,
    course_content_kind_id text REFERENCES course_content_kind(id)
);

CREATE TABLE course_content (
    id uuid PRIMARY KEY,
    course_id uuid NOT NULL REFERENCES course(id),
    parent_id uuid REFERENCES course_content(id),
    course_content_type_id uuid NOT NULL REFERENCES course_content_type(id),
    course_content_kind_id text NOT NULL REFERENCES course_content_kind(id),
    title text NOT NULL,
    path text NOT NULL,
    position integer NOT NULL,
    is_submittable boolean NOT NULL
);

CREATE TABLE course_member (
    id uuid PRIMARY KEY,
    course_id uuid NOT NULL REFERENCES course(id),
    user_id uuid NOT NULL REFERENCES "user"(id),
    course_role_id text NOT NULL
);

CREATE TABLE submission_group (
    id uuid PRIMARY KEY,
    course_id uuid NOT NULL REFERENCES course(id),
    course_content_id uuid NOT NULL REFERENCES course_content(id),
    display_name text,
    max_group_size integer NOT NULL,
    max_test_runs integer,
    max_submissions integer
);

CREATE TABLE submission_group_member (
    id uuid PRIMARY KEY,
    course_id uuid NOT NULL REFERENCES course(id),
    submission_group_id uuid NOT NULL REFERENCES submission_group(id),
    course_member_id uuid NOT NULL REFERENCES course_member(id)
);

CREATE TABLE submission_artifact (
    id uuid PRIMARY KEY,
    submission_group_id uuid NOT NULL REFERENCES submission_group(id),
    uploaded_by_course_member_id uuid REFERENCES course_member(id),
    uploaded_at timestamptz NOT NULL,
    file_size bigint NOT NULL,
    bucket_name text NOT NULL,
    object_key text NOT NULL,
    version_identifier text,
    submit boolean NOT NULL
);

CREATE TABLE submission_grade (
    id uuid PRIMARY KEY,
    artifact_id uuid NOT NULL REFERENCES submission_artifact(id),
    graded_by_course_member_id uuid NOT NULL REFERENCES course_member(id),
    graded_at timestamptz NOT NULL,
    grade double precision NOT NULL,
    status integer NOT NULL
);

CREATE TABLE result (
    id uuid PRIMARY KEY,
    course_member_id uuid NOT NULL REFERENCES course_member(id),
    submission_artifact_id uuid REFERENCES submission_artifact(id),
    submission_group_id uuid REFERENCES submission_group(id),
    course_content_id uuid NOT NULL REFERENCES course_content(id),
    course_content_type_id uuid NOT NULL REFERENCES course_content_type(id),
    created_at timestamptz NOT NULL,
    grade double precision,
    status integer NOT NULL,
    version_identifier text NOT NULL
);

INSERT INTO "user" (id, username, email, given_name, family_name) VALUES
    ('10000000-0000-4000-8000-000000000001', 'lecturer', 'lecturer@example.test', 'Lena', 'Lecturer'),
    ('10000000-0000-4000-8000-000000000002', 'tutor', 'tutor@example.test', 'Tom', 'Tutor'),
    ('10000000-0000-4000-8000-000000000101', 'alice', 'alice@example.test', 'Alice', 'Alpha'),
    ('10000000-0000-4000-8000-000000000102', 'bob', 'bob@example.test', 'Bob', 'Beta'),
    ('10000000-0000-4000-8000-000000000103', 'cara', 'cara@example.test', 'Cara', 'Gamma');

INSERT INTO student_profile (id, user_id, student_id) VALUES
    ('11000000-0000-4000-8000-000000000101', '10000000-0000-4000-8000-000000000101', 'm101'),
    ('11000000-0000-4000-8000-000000000102', '10000000-0000-4000-8000-000000000102', 'm102'),
    ('11000000-0000-4000-8000-000000000103', '10000000-0000-4000-8000-000000000103', 'm103');

INSERT INTO course (id, title) VALUES
    ('20000000-0000-4000-8000-000000000001', 'Analytics cutoff fixture');

INSERT INTO course_content_kind (id, submittable) VALUES
    ('unit', false),
    ('assignment', true);

INSERT INTO course_content_type (id, slug, title, color, course_content_kind_id) VALUES
    ('30000000-0000-4000-8000-000000000001', 'mandatory', 'Mandatory', '#2563eb', 'assignment'),
    ('30000000-0000-4000-8000-000000000002', 'unit', 'Unit', '#64748b', 'unit');

INSERT INTO course_content (
    id, course_id, parent_id, course_content_type_id, course_content_kind_id,
    title, path, position, is_submittable
) VALUES
    ('40000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', NULL, '30000000-0000-4000-8000-000000000002', 'unit', 'Week 1', 'week1', 1, false),
    ('40000000-0000-4000-8000-000000000101', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'assignment', 'Assignment 1', 'week1.assignment1', 1, true),
    ('40000000-0000-4000-8000-000000000102', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'assignment', 'Assignment 2', 'week1.assignment2', 2, true);

INSERT INTO course_member (id, course_id, user_id, course_role_id) VALUES
    ('50000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', '_lecturer'),
    ('50000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002', '_tutor'),
    ('50000000-0000-4000-8000-000000000101', '20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000101', '_student'),
    ('50000000-0000-4000-8000-000000000102', '20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000102', '_student'),
    ('50000000-0000-4000-8000-000000000103', '20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000103', '_student');

INSERT INTO submission_group (id, course_id, course_content_id, display_name, max_group_size, max_test_runs, max_submissions) VALUES
    ('60000000-0000-4000-8000-000000000111', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000101', 'Alice Assignment 1', 1, 20, 3),
    ('60000000-0000-4000-8000-000000000112', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000102', 'Alice Assignment 2', 1, 20, 3),
    ('60000000-0000-4000-8000-000000000121', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000101', 'Bob Assignment 1', 1, 20, 3),
    ('60000000-0000-4000-8000-000000000122', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000102', 'Bob Assignment 2', 1, 20, 3),
    ('60000000-0000-4000-8000-000000000131', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000101', 'Cara Assignment 1', 1, 20, 3),
    ('60000000-0000-4000-8000-000000000132', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000102', 'Cara Assignment 2', 1, 20, 3);

INSERT INTO submission_group_member (id, course_id, submission_group_id, course_member_id) VALUES
    ('61000000-0000-4000-8000-000000000111', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000111', '50000000-0000-4000-8000-000000000101'),
    ('61000000-0000-4000-8000-000000000112', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000112', '50000000-0000-4000-8000-000000000101'),
    ('61000000-0000-4000-8000-000000000121', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000121', '50000000-0000-4000-8000-000000000102'),
    ('61000000-0000-4000-8000-000000000122', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000122', '50000000-0000-4000-8000-000000000102'),
    ('61000000-0000-4000-8000-000000000131', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000131', '50000000-0000-4000-8000-000000000103'),
    ('61000000-0000-4000-8000-000000000132', '20000000-0000-4000-8000-000000000001', '60000000-0000-4000-8000-000000000132', '50000000-0000-4000-8000-000000000103');

INSERT INTO submission_artifact (
    id, submission_group_id, uploaded_by_course_member_id, uploaded_at,
    file_size, bucket_name, object_key, version_identifier, submit
) VALUES
    ('70000000-0000-4000-8000-000000000111', '60000000-0000-4000-8000-000000000111', '50000000-0000-4000-8000-000000000101', '2026-06-18 20:30:00+00', 1200, 'submissions', 'alice/a1/pre.zip', 'alice-a1-pre', true),
    ('70000000-0000-4000-8000-000000000112', '60000000-0000-4000-8000-000000000112', '50000000-0000-4000-8000-000000000101', '2026-06-18 21:55:00+00', 1300, 'submissions', 'alice/a2/pre.zip', 'alice-a2-pre', true),
    ('70000000-0000-4000-8000-000000000121', '60000000-0000-4000-8000-000000000121', '50000000-0000-4000-8000-000000000102', '2026-06-17 18:00:00+00', 1100, 'submissions', 'bob/a1/pre.zip', 'bob-a1-pre', true),
    ('70000000-0000-4000-8000-000000000122', '60000000-0000-4000-8000-000000000122', '50000000-0000-4000-8000-000000000102', '2026-06-18 22:20:00+00', 1400, 'submissions', 'bob/a2/late.zip', 'bob-a2-late', true),
    ('70000000-0000-4000-8000-000000000131', '60000000-0000-4000-8000-000000000131', '50000000-0000-4000-8000-000000000103', '2026-06-19 09:10:00+00', 1500, 'submissions', 'cara/a1/late.zip', 'cara-a1-late', true),
    ('70000000-0000-4000-8000-000000000921', '60000000-0000-4000-8000-000000000122', '50000000-0000-4000-8000-000000000102', '2026-06-18 21:30:00+00', 900, 'submissions', 'bob/a2/test1.zip', 'bob-a2-test1', false),
    ('70000000-0000-4000-8000-000000000922', '60000000-0000-4000-8000-000000000122', '50000000-0000-4000-8000-000000000102', '2026-06-18 21:45:00+00', 920, 'submissions', 'bob/a2/test2.zip', 'bob-a2-test2', false),
    ('70000000-0000-4000-8000-000000000923', '60000000-0000-4000-8000-000000000122', '50000000-0000-4000-8000-000000000102', '2026-06-18 21:58:00+00', 940, 'submissions', 'bob/a2/test3.zip', 'bob-a2-test3', false);

INSERT INTO submission_grade (id, artifact_id, graded_by_course_member_id, graded_at, grade, status) VALUES
    ('80000000-0000-4000-8000-000000000111', '70000000-0000-4000-8000-000000000111', '50000000-0000-4000-8000-000000000002', '2026-06-19 08:00:00+00', 0.85, 1),
    ('80000000-0000-4000-8000-000000000112', '70000000-0000-4000-8000-000000000112', '50000000-0000-4000-8000-000000000002', '2026-06-20 08:00:00+00', 0.90, 1),
    ('80000000-0000-4000-8000-000000000121', '70000000-0000-4000-8000-000000000121', '50000000-0000-4000-8000-000000000002', '2026-06-18 20:00:00+00', 0.70, 3);

INSERT INTO result (
    id, course_member_id, submission_artifact_id, submission_group_id,
    course_content_id, course_content_type_id, created_at, grade, status,
    version_identifier
) VALUES
    ('90000000-0000-4000-8000-000000000921', '50000000-0000-4000-8000-000000000102', '70000000-0000-4000-8000-000000000921', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:31:00+00', 0.25, 0, 'bob-a2-test1'),
    ('90000000-0000-4000-8000-000000000922', '50000000-0000-4000-8000-000000000102', '70000000-0000-4000-8000-000000000922', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:46:00+00', 0.55, 0, 'bob-a2-test2'),
    ('90000000-0000-4000-8000-000000000923', '50000000-0000-4000-8000-000000000102', '70000000-0000-4000-8000-000000000923', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:59:00+00', 0.95, 0, 'bob-a2-test3');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'analytics_reader'
    ) THEN
        CREATE ROLE analytics_reader LOGIN PASSWORD 'analytics_reader_secret';
    ELSE
        ALTER ROLE analytics_reader WITH PASSWORD 'analytics_reader_secret';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;
