from __future__ import annotations

from collections import defaultdict
from typing import Any, Protocol
from uuid import UUID

from computor_types.course_member_gradings import (
    ContentTypeGradingStats,
    CourseMemberGradingNode,
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
)

from ..utils.grading_stats import process_hierarchical_stats


class CourseMemberGradingReadBackend(Protocol):
    def get_hierarchical_stats_for_member(
        self,
        course_member_id: UUID | str,
        course_id: UUID | str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
        max_depth: int | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_path_info(self, course_id: UUID | str) -> dict[str, Any]:
        ...

    def get_assignment_details_for_member(
        self,
        course_member_id: UUID | str,
        course_id: UUID | str,
    ) -> dict[str, dict[str, Any]]:
        ...

    def get_course_level_stats_for_all_members(
        self,
        course_id: UUID | str,
        path_prefix: str | None = None,
        course_content_type_id: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_all_course_members_with_students_role(
        self,
        course_id: UUID | str,
    ) -> list[dict[str, Any]]:
        ...


def build_course_member_grading_response(
    backend: CourseMemberGradingReadBackend,
    course_member_id: UUID | str,
    course_id: UUID | str,
    member_info: Any,
) -> CourseMemberGradingsGet:
    db_stats = backend.get_hierarchical_stats_for_member(
        course_member_id=course_member_id,
        course_id=course_id,
        path_prefix=None,
        course_content_type_id=None,
        max_depth=None,
    )
    path_info = backend.get_path_info(course_id)
    assignment_details = backend.get_assignment_details_for_member(
        course_member_id=course_member_id,
        course_id=course_id,
    )

    stats = process_hierarchical_stats(db_stats, path_info, assignment_details)

    return CourseMemberGradingsGet(
        course_member_id=str(course_member_id),
        course_id=str(course_id),
        user_id=str(_row_value(member_info, "user_id"))
        if _row_value(member_info, "user_id") else None,
        username=_row_value(member_info, "username"),
        given_name=_row_value(member_info, "given_name"),
        family_name=_row_value(member_info, "family_name"),
        student_id=_row_value(member_info, "student_id"),
        total_max_assignments=stats["total_max_assignments"],
        total_submitted_assignments=stats["total_submitted_assignments"],
        overall_progress_percentage=stats["overall_progress_percentage"],
        latest_submission_at=stats["latest_submission_at"],
        overall_average_grading=stats["overall_average_grading"],
        by_content_type=[
            ContentTypeGradingStats(**ct_stats)
            for ct_stats in stats["by_content_type"]
        ],
        nodes=[
            CourseMemberGradingNode(
                path=node["path"],
                title=node["title"],
                submittable=node["submittable"],
                position=node["position"],
                course_content_type_color=node["course_content_type_color"],
                max_assignments=node["max_assignments"],
                submitted_assignments=node["submitted_assignments"],
                progress_percentage=node["progress_percentage"],
                latest_submission_at=node["latest_submission_at"],
                by_content_type=[
                    ContentTypeGradingStats(**ct)
                    for ct in node["by_content_type"]
                ],
                grading=node["grading"],
                average_grading=node["average_grading"],
                graded_assignments=node["graded_assignments"],
                status=node["status"],
                latest_result_id=node.get("latest_result_id"),
                latest_result_grade=node.get("latest_result_grade"),
                latest_result_status=node.get("latest_result_status"),
                latest_result_created_at=node.get("latest_result_created_at"),
                test_runs_count=node.get("test_runs_count"),
                max_test_runs=node.get("max_test_runs"),
                submissions_count=node.get("submissions_count"),
                max_submissions=node.get("max_submissions"),
                graded_by_course_member=node.get("graded_by_course_member"),
            )
            for node in stats["nodes"]
        ],
    )


def build_course_member_grading_list_response(
    backend: CourseMemberGradingReadBackend,
    course_id: UUID | str,
) -> list[CourseMemberGradingsList]:
    db_stats = backend.get_course_level_stats_for_all_members(
        course_id=course_id,
        path_prefix=None,
        course_content_type_id=None,
    )

    if not db_stats:
        return [
            CourseMemberGradingsList(
                course_member_id=member["course_member_id"],
                course_id=str(course_id),
                user_id=member["user_id"],
                username=member["username"],
                given_name=member["given_name"],
                family_name=member["family_name"],
                student_id=member["student_id"],
                total_max_assignments=0,
                total_submitted_assignments=0,
                overall_progress_percentage=0.0,
                latest_submission_at=None,
                by_content_type=[],
            )
            for member in backend.get_all_course_members_with_students_role(course_id)
        ]

    members_data: dict[str, dict[str, Any]] = {}
    members_ct: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in db_stats:
        member_id = row["course_member_id"]
        if member_id not in members_data:
            members_data[member_id] = {
                "course_member_id": member_id,
                "course_id": str(course_id),
                "user_id": row.get("user_id"),
                "username": row.get("username"),
                "given_name": row.get("given_name"),
                "family_name": row.get("family_name"),
                "student_id": row.get("student_id"),
            }
        members_ct[member_id].append(row)

    results = []
    for member_id, member_info in members_data.items():
        total_max = 0
        total_submitted = 0
        total_graded = 0
        total_grade_sum = 0.0
        latest_submission = None
        by_content_type = []

        for ct_row in members_ct[member_id]:
            max_assignments = ct_row["max_assignments"]
            submitted_assignments = ct_row["submitted_assignments"]
            graded_assignments = ct_row.get("graded_assignments", 0) or 0
            average_grading = ct_row.get("average_grading")
            latest_at = ct_row.get("latest_submission_at")

            total_max += max_assignments
            total_submitted += submitted_assignments
            total_graded += graded_assignments
            if average_grading is not None and graded_assignments > 0:
                total_grade_sum += average_grading * graded_assignments

            if latest_at and (latest_submission is None or latest_at > latest_submission):
                latest_submission = latest_at

            by_content_type.append(ContentTypeGradingStats(
                course_content_type_id=ct_row["content_type_id"],
                course_content_type_slug=ct_row["content_type_slug"],
                course_content_type_title=ct_row.get("content_type_title"),
                course_content_type_color=ct_row.get("content_type_color"),
                max_assignments=max_assignments,
                submitted_assignments=submitted_assignments,
                progress_percentage=round(
                    (submitted_assignments / max_assignments * 100)
                    if max_assignments > 0 else 0.0,
                    2,
                ),
                graded_assignments=graded_assignments,
                average_grading=round(average_grading, 4)
                if average_grading is not None else None,
            ))

        results.append(CourseMemberGradingsList(
            **member_info,
            total_max_assignments=total_max,
            total_submitted_assignments=total_submitted,
            overall_progress_percentage=round(
                (total_submitted / total_max * 100) if total_max > 0 else 0.0,
                2,
            ),
            latest_submission_at=latest_submission,
            overall_average_grading=round(total_grade_sum / total_graded, 4)
            if total_graded > 0 else None,
            by_content_type=by_content_type,
        ))

    return results


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)
