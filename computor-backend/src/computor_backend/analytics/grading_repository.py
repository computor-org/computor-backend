from __future__ import annotations

from datetime import datetime
from typing import Any

import duckdb

from computor_backend.services.course_member_grading_stats import (
    aggregate_grading_status,
)

from .config import AnalyticsCutoffs


class AnalyticsDuckDbGradingRepository:
    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        cutoffs: AnalyticsCutoffs | None = None,
    ):
        self.connection = connection
        self.cutoffs = (cutoffs or AnalyticsCutoffs()).normalized()
        self._column_cache: dict[tuple[str, str], bool] = {}

    def get_path_info(self, course_id: str) -> dict[str, dict[str, Any]]:
        archived_filter = self._archived_filter()
        rows = self._rows(
            f"""
            SELECT
                CAST(cc.path AS VARCHAR) AS path,
                cc.title,
                cc.position,
                cck.submittable,
                cct.color AS course_content_type_color
            FROM course_content cc
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = ?
              AND {archived_filter}
            """,
            [str(course_id)],
        )
        return {
            row["path"]: {
                "title": row["title"],
                "submittable": bool(row["submittable"]),
                "position": row["position"],
                "course_content_type_color": row["course_content_type_color"],
            }
            for row in rows
        }

    def get_all_course_members_with_students_role(
        self,
        course_id: str,
    ) -> list[dict[str, Any]]:
        profile_join, params = self._student_profile_join(course_id)

        return self._rows(
            f"""
            SELECT
                cm.id AS course_member_id,
                cm.user_id AS user_id,
                u.email AS username,
                u.given_name,
                u.family_name,
                sp.student_id
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            {profile_join}
            WHERE cm.course_id = ?
              AND cm.course_role_id = '_student'
            ORDER BY u.family_name, u.given_name
            """,
            [*params, str(course_id)],
        )

    def get_course_level_stats_for_all_members(
        self,
        course_id: str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
    ) -> list[dict[str, Any]]:
        submittable_filter, submittable_params = self._submittable_filter(
            course_id,
            path_prefix=path_prefix,
            course_content_type_id=course_content_type_id,
        )
        profile_join, profile_params = self._student_profile_join(course_id)

        cutoff_params: list[Any] = []
        submission_cutoff = self._cutoff_filter(
            f"sa.{self._submission_time_column()}",
            self.cutoffs.submission,
            cutoff_params,
        )
        grading_cutoff = self._cutoff_filter(
            "sgd.graded_at",
            self.cutoffs.grading,
            cutoff_params,
        )

        return self._rows(
            f"""
            WITH submittable_contents AS (
                SELECT
                    cc.id AS content_id,
                    cc.path,
                    cct.id AS content_type_id,
                    cct.slug AS content_type_slug,
                    cct.title AS content_type_title,
                    cct.color AS content_type_color
                FROM course_content cc
                JOIN course_content_type cct ON cct.id = cc.course_content_type_id
                JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
                WHERE {submittable_filter}
            ),
            content_type_counts AS (
                SELECT
                    content_type_id,
                    content_type_slug,
                    content_type_title,
                    content_type_color,
                    COUNT(*) AS max_assignments
                FROM submittable_contents
                GROUP BY
                    content_type_id,
                    content_type_slug,
                    content_type_title,
                    content_type_color
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
            submitted_by_member_and_type AS (
                SELECT
                    sgm.course_member_id,
                    sc.content_type_id,
                    COUNT(DISTINCT sc.content_id) AS submitted_assignments,
                    MAX(sa.{self._submission_time_column()}) AS latest_submission_at
                FROM submittable_contents sc
                JOIN submission_group sg ON sg.course_content_id = sc.content_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                JOIN submission_artifact sa ON sa.submission_group_id = sg.id
                WHERE sa.submit = true
                  {submission_cutoff}
                GROUP BY sgm.course_member_id, sc.content_type_id
            ),
            latest_grade_rows AS (
                SELECT *
                FROM (
                    SELECT
                        sgm.course_member_id,
                        sc.content_id,
                        sc.content_type_id,
                        sgd.grade,
                        ROW_NUMBER() OVER (
                            PARTITION BY sgm.course_member_id, sc.content_id
                            ORDER BY sgd.graded_at DESC
                        ) AS rn
                    FROM submittable_contents sc
                    JOIN submission_group sg ON sg.course_content_id = sc.content_id
                    JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                    JOIN submission_artifact sa ON sa.submission_group_id = sg.id
                    JOIN submission_grade sgd ON sgd.artifact_id = sa.id
                    WHERE sa.submit = true
                      {grading_cutoff}
                ) ranked
                WHERE rn = 1
            ),
            all_contents_with_grades AS (
                SELECT
                    s.course_member_id,
                    sc.content_id,
                    sc.content_type_id,
                    COALESCE(lg.grade, 0) AS grade
                FROM all_students s
                CROSS JOIN submittable_contents sc
                LEFT JOIN latest_grade_rows lg
                    ON lg.course_member_id = s.course_member_id
                    AND lg.content_id = sc.content_id
            ),
            graded_by_member_and_type AS (
                SELECT
                    course_member_id,
                    content_type_id,
                    COUNT(*) AS graded_assignments,
                    AVG(grade) AS average_grading
                FROM all_contents_with_grades
                GROUP BY course_member_id, content_type_id
            )
            SELECT
                s.course_member_id,
                s.user_id,
                s.username,
                s.given_name,
                s.family_name,
                s.student_id,
                ctc.content_type_id,
                ctc.content_type_slug,
                ctc.content_type_title,
                ctc.content_type_color,
                ctc.max_assignments,
                COALESCE(sbmt.submitted_assignments, 0) AS submitted_assignments,
                sbmt.latest_submission_at,
                COALESCE(grd.graded_assignments, 0) AS graded_assignments,
                grd.average_grading
            FROM all_students s
            CROSS JOIN content_type_counts ctc
            LEFT JOIN submitted_by_member_and_type sbmt
                ON sbmt.course_member_id = s.course_member_id
                AND sbmt.content_type_id = ctc.content_type_id
            LEFT JOIN graded_by_member_and_type grd
                ON grd.course_member_id = s.course_member_id
                AND grd.content_type_id = ctc.content_type_id
            ORDER BY s.family_name, s.given_name, ctc.content_type_slug
            """,
            [
                *submittable_params,
                *profile_params,
                str(course_id),
                *cutoff_params,
            ],
        )

    def get_hierarchical_stats_for_member(
        self,
        course_member_id: str,
        course_id: str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
        max_depth: int | None = None,
    ) -> list[dict[str, Any]]:
        contents = self._submittable_contents(
            course_id,
            path_prefix=path_prefix,
            course_content_type_id=course_content_type_id,
        )
        submissions = self._latest_submissions(course_id, course_member_id)
        grades = self._latest_grades(course_id, course_member_id)
        grouped: dict[tuple[str, str], dict[str, Any]] = {}

        for content in contents:
            parts = content["path"].split(".")
            for depth in range(1, len(parts) + 1):
                if max_depth is not None and depth > max_depth:
                    continue
                prefix = ".".join(parts[:depth])
                type_id = content["course_content_type_id"]
                key = (prefix, type_id)
                bucket = grouped.setdefault(
                    key,
                    {
                        "path": prefix,
                        "path_depth": depth,
                        "content_type_id": type_id,
                        "content_type_slug": content["content_type_slug"],
                        "content_type_title": content["content_type_title"],
                        "content_type_color": content["content_type_color"],
                        "max_assignments": 0,
                        "submitted_assignments": 0,
                        "latest_submission_at": None,
                        "grades": [],
                        "statuses": [],
                    },
                )

                content_key = (str(course_member_id), content["course_content_id"])
                submitted_at = submissions.get(content_key, {}).get("latest_submission_at")
                grade = grades.get(content_key, {}).get("grade", 0.0) or 0.0
                status = _grading_status_name(grades.get(content_key, {}).get("status"))

                bucket["max_assignments"] += 1
                bucket["grades"].append(float(grade))
                bucket["statuses"].append(status)
                if submitted_at is not None:
                    bucket["submitted_assignments"] += 1
                    if (
                        bucket["latest_submission_at"] is None
                        or submitted_at > bucket["latest_submission_at"]
                    ):
                        bucket["latest_submission_at"] = submitted_at

        return [
            {
                "path": row["path"],
                "path_depth": row["path_depth"],
                "content_type_id": row["content_type_id"],
                "content_type_slug": row["content_type_slug"],
                "content_type_title": row["content_type_title"],
                "content_type_color": row["content_type_color"],
                "max_assignments": row["max_assignments"],
                "submitted_assignments": row["submitted_assignments"],
                "latest_submission_at": row["latest_submission_at"],
                "graded_assignments": row["max_assignments"],
                "average_grading": sum(row["grades"]) / len(row["grades"])
                if row["grades"] else None,
                "grading_status": _aggregate_status(row["statuses"]),
            }
            for row in sorted(
                grouped.values(),
                key=lambda item: (item["path_depth"], item["path"], item["content_type_slug"]),
            )
        ]

    def get_assignment_details_for_member(
        self,
        course_member_id: str,
        course_id: str,
    ) -> dict[str, dict[str, Any]]:
        contents = self._submittable_contents(course_id)
        results = self._latest_results(course_id, course_member_id)
        grades = self._latest_grades(course_id, course_member_id)
        submissions = self._latest_submissions(course_id, course_member_id)
        groups = self._submission_groups(course_id, course_member_id)

        details = {}
        for content in contents:
            content_id = content["course_content_id"]
            key = (str(course_member_id), content_id)
            group = groups.get(content_id, {})
            latest_result = results.get(key, {})
            latest_grade = grades.get(key, {})
            details[content["path"]] = {
                "content_id": content_id,
                "max_test_runs": group.get("max_test_runs") or content.get("max_test_runs"),
                "max_submissions": group.get("max_submissions") or content.get("max_submissions"),
                "latest_result_id": latest_result.get("result_id"),
                "latest_result_grade": latest_result.get("result_grade"),
                "latest_result_status": latest_result.get("result_status"),
                "latest_result_created_at": latest_result.get("result_created_at"),
                "test_runs_count": latest_result.get("test_runs_count", 0),
                "submissions_count": submissions.get(key, {}).get("submissions_count", 0),
                "graded_by_course_member": latest_grade.get("graded_by_course_member"),
            }
        return details

    def _submittable_filter(
        self,
        course_id: str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        params: list[Any] = [str(course_id)]
        filters = [
            "cc.course_id = ?",
            "cck.submittable = true",
            self._archived_filter(),
        ]
        if path_prefix:
            filters.append("(CAST(cc.path AS VARCHAR) = ? OR CAST(cc.path AS VARCHAR) LIKE ?)")
            params.extend([path_prefix, f"{path_prefix}.%"])
        if course_content_type_id:
            filters.append("cct.id = ?")
            params.append(str(course_content_type_id))
        return " AND ".join(filters), params

    def _student_profile_join(self, course_id: str) -> tuple[str, list[Any]]:
        if (
            self._has_column("student_profile", "organization_id")
            and self._has_column("course", "organization_id")
        ):
            return (
                """
                LEFT JOIN student_profile sp ON sp.user_id = cm.user_id
                    AND sp.organization_id = (
                        SELECT organization_id FROM course WHERE id = ?
                    )
                """,
                [str(course_id)],
            )
        return "LEFT JOIN student_profile sp ON sp.user_id = cm.user_id", []

    def _submittable_contents(
        self,
        course_id: str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
    ) -> list[dict[str, Any]]:
        archived_filter = self._archived_filter()
        max_test_runs_column = (
            "cc.max_test_runs"
            if self._has_column("course_content", "max_test_runs")
            else "NULL"
        )
        max_submissions_column = (
            "cc.max_submissions"
            if self._has_column("course_content", "max_submissions")
            else "NULL"
        )
        params: list[Any] = [str(course_id)]
        filters = []
        if path_prefix:
            filters.append("(CAST(cc.path AS VARCHAR) = ? OR CAST(cc.path AS VARCHAR) LIKE ?)")
            params.extend([path_prefix, f"{path_prefix}.%"])
        if course_content_type_id:
            filters.append("cct.id = ?")
            params.append(str(course_content_type_id))
        extra = f"AND {' AND '.join(filters)}" if filters else ""

        return self._rows(
            f"""
            SELECT
                cc.id AS course_content_id,
                CAST(cc.path AS VARCHAR) AS path,
                cc.title,
                cct.id AS course_content_type_id,
                cct.slug AS content_type_slug,
                cct.title AS content_type_title,
                cct.color AS content_type_color,
                cc.position,
                {max_test_runs_column} AS max_test_runs,
                {max_submissions_column} AS max_submissions
            FROM course_content cc
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = ?
              AND cck.submittable = true
              AND {archived_filter}
              {extra}
            ORDER BY CAST(cc.path AS VARCHAR), cct.slug
            """,
            params,
        )

    def _latest_submissions(
        self,
        course_id: str,
        course_member_id: str | None = None,
    ) -> dict[tuple[str, str], dict[str, Any]]:
        time_column = self._submission_time_column()
        params: list[Any] = [str(course_id)]
        member_filter = ""
        if course_member_id:
            member_filter = "AND sgm.course_member_id = ?"
            params.append(str(course_member_id))
        cutoff_filter = self._cutoff_filter(f"sa.{time_column}", self.cutoffs.submission, params)

        rows = self._rows(
            f"""
            SELECT
                sgm.course_member_id,
                sg.course_content_id,
                MAX(sa.{time_column}) AS latest_submission_at,
                COUNT(DISTINCT sa.id) AS submissions_count
            FROM submission_artifact sa
            JOIN submission_group sg ON sg.id = sa.submission_group_id
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            WHERE sg.course_id = ?
              AND sa.submit = true
              {member_filter}
              {cutoff_filter}
            GROUP BY sgm.course_member_id, sg.course_content_id
            """,
            params,
        )
        return {
            (row["course_member_id"], row["course_content_id"]): row
            for row in rows
        }

    def _latest_grades(
        self,
        course_id: str,
        course_member_id: str | None = None,
    ) -> dict[tuple[str, str], dict[str, Any]]:
        params: list[Any] = [str(course_id)]
        member_filter = ""
        if course_member_id:
            member_filter = "AND sgm.course_member_id = ?"
            params.append(str(course_member_id))
        grading_cutoff = self._cutoff_filter("sgd.graded_at", self.cutoffs.grading, params)

        rows = self._rows(
            f"""
            SELECT *
            FROM (
                SELECT
                    sgm.course_member_id,
                    sg.course_content_id,
                    sgd.grade,
                    sgd.status,
                    sgd.graded_at,
                    sgd.graded_by_course_member_id,
                    cm.course_role_id AS grader_course_role_id,
                    cm.user_id AS grader_user_id,
                    u.given_name AS grader_given_name,
                    u.family_name AS grader_family_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY sgm.course_member_id, sg.course_content_id
                        ORDER BY sgd.graded_at DESC
                    ) AS rn
                FROM submission_grade sgd
                JOIN submission_artifact sa ON sa.id = sgd.artifact_id
                JOIN submission_group sg ON sg.id = sa.submission_group_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
                LEFT JOIN course_member cm ON cm.id = sgd.graded_by_course_member_id
                LEFT JOIN "user" u ON u.id = cm.user_id
                WHERE sg.course_id = ?
                  AND sa.submit = true
                  {member_filter}
                  {grading_cutoff}
            ) ranked
            WHERE rn = 1
            """,
            params,
        )
        return {
            (row["course_member_id"], row["course_content_id"]): {
                **row,
                "graded_by_course_member": {
                    "course_role_id": row["grader_course_role_id"],
                    "user_id": row["grader_user_id"],
                    "user": {
                        "given_name": row["grader_given_name"],
                        "family_name": row["grader_family_name"],
                    } if row["grader_user_id"] else None,
                } if row["graded_by_course_member_id"] else None,
            }
            for row in rows
        }

    def _latest_results(
        self,
        course_id: str,
        course_member_id: str,
    ) -> dict[tuple[str, str], dict[str, Any]]:
        result_grade_column = "result" if self._has_column("result", "result") else "grade"
        rows = self._rows(
            f"""
            SELECT *
            FROM (
                SELECT
                    r.course_member_id,
                    r.course_content_id,
                    r.id AS result_id,
                    r.{result_grade_column} AS result_grade,
                    r.status AS result_status,
                    r.created_at AS result_created_at,
                    COUNT(*) OVER (
                        PARTITION BY r.course_member_id, r.course_content_id
                    ) AS test_runs_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY r.course_member_id, r.course_content_id
                        ORDER BY r.created_at DESC
                    ) AS rn
                FROM result r
                JOIN course_content cc ON cc.id = r.course_content_id
                WHERE cc.course_id = ?
                  AND r.course_member_id = ?
            ) ranked
            WHERE rn = 1
            """,
            [str(course_id), str(course_member_id)],
        )
        return {
            (row["course_member_id"], row["course_content_id"]): row
            for row in rows
        }

    def _submission_groups(
        self,
        course_id: str,
        course_member_id: str,
    ) -> dict[str, dict[str, Any]]:
        rows = self._rows(
            """
            SELECT
                sg.course_content_id,
                sg.max_test_runs,
                sg.max_submissions
            FROM submission_group sg
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            WHERE sg.course_id = ?
              AND sgm.course_member_id = ?
            """,
            [str(course_id), str(course_member_id)],
        )
        return {row["course_content_id"]: row for row in rows}

    def _archived_filter(self) -> str:
        if self._has_column("course_content", "archived_at"):
            return "cc.archived_at IS NULL"
        return "true"

    def _submission_time_column(self) -> str:
        if self._has_column("submission_artifact", "uploaded_at"):
            return "uploaded_at"
        return "created_at"

    def _cutoff_filter(
        self,
        column: str,
        cutoff: datetime | None,
        params: list[Any],
    ) -> str:
        if cutoff is None:
            return ""
        params.append(cutoff)
        return f"AND {column} <= ?"

    def _has_column(self, table: str, column: str) -> bool:
        key = (table, column)
        if key in self._column_cache:
            return self._column_cache[key]
        row = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = ?
              AND column_name = ?
            """,
            [table, column],
        ).fetchone()
        exists = bool(row and row[0])
        self._column_cache[key] = exists
        return exists

    def _rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        cursor = self.connection.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [
            {column: _normalize_value(value) for column, value in zip(columns, row)}
            for row in cursor.fetchall()
        ]


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat") and not isinstance(value, (str, bytes)):
        return value
    return str(value) if value.__class__.__name__ == "UUID" else value


def _grading_status_name(status: Any) -> str:
    if status == 2:
        return "correction_necessary"
    if status == 3:
        return "improvement_possible"
    if status == 1:
        return "corrected"
    return "not_reviewed"


def _aggregate_status(statuses: list[str]) -> str:
    return aggregate_grading_status(statuses, default="not_reviewed")
