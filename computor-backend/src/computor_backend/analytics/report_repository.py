from __future__ import annotations

from typing import Any

import duckdb

from .config import AnalyticsCutoffs
from .grading_repository import AnalyticsDuckDbGradingRepository


class AnalyticsDuckDbReportRepository(AnalyticsDuckDbGradingRepository):
    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        cutoffs: AnalyticsCutoffs | None = None,
    ):
        super().__init__(connection, cutoffs=cutoffs)

    def get_course_rows(self) -> list[dict[str, Any]]:
        return self._rows(
            f"""
            SELECT
                c.id AS course_id,
                c.title,
                {self._course_path_expression()} AS path,
                COUNT(DISTINCT CASE
                    WHEN students.course_role_id = '_student' THEN students.id
                    ELSE NULL
                END) AS total_students
            FROM course c
            LEFT JOIN course_member students ON students.course_id = c.id
            GROUP BY c.id, c.title{self._course_path_group()}
            ORDER BY c.title NULLS LAST, path NULLS LAST
            """,
        )

    def get_course_rows_for_user_email(self, email: str) -> list[dict[str, Any]]:
        return self._rows(
            f"""
            SELECT
                c.id AS course_id,
                c.title,
                {self._course_path_expression()} AS path,
                cm.course_role_id AS role,
                COUNT(DISTINCT CASE
                    WHEN students.course_role_id = '_student' THEN students.id
                    ELSE NULL
                END) AS total_students
            FROM course c
            JOIN course_member cm ON cm.course_id = c.id
            JOIN "user" u ON u.id = cm.user_id
            LEFT JOIN course_member students ON students.course_id = c.id
            WHERE lower(u.email) = lower(?)
            GROUP BY c.id, c.title{self._course_path_group()}, cm.course_role_id
            ORDER BY c.title NULLS LAST, path NULLS LAST
            """,
            [email],
        )

    def get_course_roles_for_user_email(
        self,
        course_id: str,
        email: str,
    ) -> list[str]:
        rows = self._rows(
            """
            SELECT cm.course_role_id AS role
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            WHERE cm.course_id = ?
              AND lower(u.email) = lower(?)
            """,
            [str(course_id), email],
        )
        return [str(row["role"]) for row in rows if row.get("role")]

    def get_student_checkpoint_rows(self, course_id: str) -> list[dict[str, Any]]:
        submittable_filter, submittable_params = self._submittable_filter(course_id)
        profile_join, profile_params = self._student_profile_join(course_id)
        time_column = self._submission_time_column()

        submitted_params: list[Any] = []
        submission_cutoff = self._cutoff_filter(
            f"sa.{time_column}",
            self.cutoffs.submission,
            submitted_params,
        )
        late_params: list[Any] = []
        late_submission_filter = self._after_cutoff_filter(
            f"sa.{time_column}",
            self.cutoffs.submission,
            late_params,
        )
        grade_params: list[Any] = []
        grade_submission_cutoff = self._cutoff_filter(
            f"sa.{time_column}",
            self.cutoffs.submission,
            grade_params,
        )
        grading_cutoff = self._cutoff_filter(
            "sgd.graded_at",
            self.cutoffs.grading,
            grade_params,
        )

        return self._rows(
            f"""
            WITH submittable_contents AS (
                SELECT cc.id AS content_id
                FROM course_content cc
                JOIN course_content_type cct ON cct.id = cc.course_content_type_id
                JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
                WHERE {submittable_filter}
            ),
            all_students AS (
                SELECT
                    cm.id AS course_member_id,
                    cm.user_id,
                    u.email AS username,
                    u.given_name,
                    u.family_name,
                    sp.student_id
                FROM course_member cm
                JOIN "user" u ON u.id = cm.user_id
                {profile_join}
                WHERE cm.course_id = ?
                  AND cm.course_role_id = '_student'
            ),
            submitted_slots AS (
                SELECT
                    sgm.course_member_id,
                    sg.course_content_id,
                    MAX(sa.{time_column}) AS latest_submission_at
                FROM submittable_contents sc
                JOIN submission_group sg ON sg.course_content_id = sc.content_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                JOIN submission_artifact sa ON sa.submission_group_id = sg.id
                WHERE sa.submit = true
                  {submission_cutoff}
                GROUP BY sgm.course_member_id, sg.course_content_id
            ),
            late_official_submissions AS (
                SELECT
                    sgm.course_member_id,
                    COUNT(DISTINCT sg.course_content_id) AS late_submission_count
                FROM submittable_contents sc
                JOIN submission_group sg ON sg.course_content_id = sc.content_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                JOIN submission_artifact sa ON sa.submission_group_id = sg.id
                WHERE sa.submit = true
                  {late_submission_filter}
                GROUP BY sgm.course_member_id
            ),
            latest_grade_rows AS (
                SELECT *
                FROM (
                    SELECT
                        sgm.course_member_id,
                        sg.course_content_id,
                        sgd.grade,
                        ROW_NUMBER() OVER (
                            PARTITION BY sgm.course_member_id, sg.course_content_id
                            ORDER BY sgd.graded_at DESC
                        ) AS rn
                    FROM submittable_contents sc
                    JOIN submission_group sg ON sg.course_content_id = sc.content_id
                    JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                    JOIN submission_artifact sa ON sa.submission_group_id = sg.id
                    JOIN submission_grade sgd ON sgd.artifact_id = sa.id
                    WHERE sa.submit = true
                      {grade_submission_cutoff}
                      {grading_cutoff}
                ) ranked
                WHERE rn = 1
            )
            SELECT
                s.course_member_id,
                s.user_id,
                s.username,
                s.given_name,
                s.family_name,
                s.student_id,
                COUNT(sc.content_id) AS total_max_assignments,
                COUNT(sub.course_content_id) AS total_submitted_assignments,
                COUNT(grd.course_content_id) AS total_graded_assignments,
                COUNT(CASE WHEN grd.grade >= 0.6 THEN grd.course_content_id END)
                    AS standard_passed,
                AVG(grd.grade) AS average_grading,
                MAX(sub.latest_submission_at) AS latest_submission_at,
                COALESCE(MAX(late.late_submission_count), 0) AS late_submission_count
            FROM all_students s
            CROSS JOIN submittable_contents sc
            LEFT JOIN submitted_slots sub
                ON sub.course_member_id = s.course_member_id
                AND sub.course_content_id = sc.content_id
            LEFT JOIN latest_grade_rows grd
                ON grd.course_member_id = s.course_member_id
                AND grd.course_content_id = sc.content_id
            LEFT JOIN late_official_submissions late
                ON late.course_member_id = s.course_member_id
            GROUP BY
                s.course_member_id,
                s.user_id,
                s.username,
                s.given_name,
                s.family_name,
                s.student_id
            ORDER BY s.family_name, s.given_name
            """,
            [
                *submittable_params,
                *profile_params,
                str(course_id),
                *submitted_params,
                *late_params,
                *grade_params,
            ],
        )

    def get_timeline_events(
        self,
        course_id: str,
        course_member_id: str,
    ) -> list[dict[str, Any]]:
        events = [
            *self._artifact_events(course_id, course_member_id),
            *self._result_events(course_id, course_member_id),
            *self._grading_events(course_id, course_member_id),
        ]
        for event in events:
            event["relation_to_submission_cutoff"] = self._cutoff_relation(
                event.get("occurred_at")
            )
        return sorted(events, key=lambda event: event["occurred_at"])

    def _artifact_events(
        self,
        course_id: str,
        course_member_id: str,
    ) -> list[dict[str, Any]]:
        time_column = self._submission_time_column()
        return self._rows(
            f"""
            SELECT
                sa.{time_column} AS occurred_at,
                CASE
                    WHEN sa.submit = true THEN 'official_submission'
                    ELSE 'test_submission'
                END AS event_type,
                cc.id AS course_content_id,
                CAST(cc.path AS VARCHAR) AS path,
                cc.title,
                sa.id AS artifact_id,
                NULL AS result_id,
                NULL AS grade,
                NULL AS status,
                sa.submit,
                sa.version_identifier
            FROM submission_artifact sa
            JOIN submission_group sg ON sg.id = sa.submission_group_id
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            JOIN course_content cc ON cc.id = sg.course_content_id
            WHERE sg.course_id = ?
              AND sgm.course_member_id = ?
            """,
            [str(course_id), str(course_member_id)],
        )

    def _result_events(
        self,
        course_id: str,
        course_member_id: str,
    ) -> list[dict[str, Any]]:
        result_grade_column = "result" if self._has_column("result", "result") else "grade"
        return self._rows(
            f"""
            SELECT
                r.created_at AS occurred_at,
                'test_result' AS event_type,
                cc.id AS course_content_id,
                CAST(cc.path AS VARCHAR) AS path,
                cc.title,
                r.submission_artifact_id AS artifact_id,
                r.id AS result_id,
                r.{result_grade_column} AS grade,
                r.status,
                false AS submit,
                r.version_identifier
            FROM result r
            JOIN course_content cc ON cc.id = r.course_content_id
            WHERE cc.course_id = ?
              AND r.course_member_id = ?
            """,
            [str(course_id), str(course_member_id)],
        )

    def _grading_events(
        self,
        course_id: str,
        course_member_id: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT
                sgd.graded_at AS occurred_at,
                'grading' AS event_type,
                cc.id AS course_content_id,
                CAST(cc.path AS VARCHAR) AS path,
                cc.title,
                sa.id AS artifact_id,
                NULL AS result_id,
                sgd.grade,
                sgd.status,
                sa.submit,
                sa.version_identifier
            FROM submission_grade sgd
            JOIN submission_artifact sa ON sa.id = sgd.artifact_id
            JOIN submission_group sg ON sg.id = sa.submission_group_id
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            JOIN course_content cc ON cc.id = sg.course_content_id
            WHERE sg.course_id = ?
              AND sgm.course_member_id = ?
            """,
            [str(course_id), str(course_member_id)],
        )

    def _after_cutoff_filter(
        self,
        column: str,
        cutoff: Any,
        params: list[Any],
    ) -> str:
        if cutoff is None:
            return "AND false"
        params.append(cutoff)
        return f"AND {column} > ?"

    def _cutoff_relation(self, occurred_at: Any) -> str | None:
        if self.cutoffs.submission is None or occurred_at is None:
            return None
        if occurred_at <= self.cutoffs.submission:
            return "before_submission_cutoff"
        return "after_submission_cutoff"

    def _course_path_expression(self) -> str:
        if self._has_column("course", "path"):
            return "CAST(c.path AS VARCHAR)"
        return "NULL"

    def _course_path_group(self) -> str:
        if self._has_column("course", "path"):
            return ", c.path"
        return ""
