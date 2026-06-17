from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def aggregate_grading_status(
    statuses: Iterable[str | None],
    default: str | None = "not_reviewed",
) -> str | None:
    valid_statuses = [status for status in statuses if status is not None]
    if not valid_statuses:
        return default
    if "correction_necessary" in valid_statuses:
        return "correction_necessary"
    if "improvement_possible" in valid_statuses:
        return "improvement_possible"
    if all(status == "corrected" for status in valid_statuses):
        return "corrected"
    return "not_reviewed"


def process_hierarchical_stats(
    db_stats: list[dict[str, Any]],
    path_info: dict[str, Any],
    assignment_details: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not db_stats:
        return {
            "total_max_assignments": 0,
            "total_submitted_assignments": 0,
            "overall_progress_percentage": 0.0,
            "latest_submission_at": None,
            "overall_average_grading": None,
            "by_content_type": [],
            "nodes": [],
        }

    submittable_paths = {
        path
        for path, info in path_info.items()
        if isinstance(info, dict) and info.get("submittable")
    }
    by_content_type = defaultdict(_new_content_type_bucket)
    by_node: dict[str, dict[str, Any]] = {}

    total_max = 0
    total_submitted = 0
    total_graded = 0
    total_grade_sum = 0.0
    latest_submission = None

    for row in db_stats:
        path = row["path"]
        content_type_id = row.get("content_type_id")
        max_assignments = row["max_assignments"]
        submitted_assignments = row["submitted_assignments"]
        latest_at = row.get("latest_submission_at")
        graded_assignments = row.get("graded_assignments", 0) or 0
        average_grading = row.get("average_grading")

        is_submittable_path = path in submittable_paths
        if content_type_id and is_submittable_path:
            _add_content_type_stats(
                by_content_type[content_type_id],
                row,
                max_assignments,
                submitted_assignments,
                graded_assignments,
                average_grading,
            )

        node = by_node.setdefault(path, _new_node(path, path_info))
        node["max_assignments"] += max_assignments
        node["submitted_assignments"] += submitted_assignments
        node["graded_assignments"] += graded_assignments
        if average_grading is not None and graded_assignments > 0:
            node["grade_sum"] += average_grading * graded_assignments

        grading_status = row.get("grading_status")
        if grading_status is not None:
            node["grading_statuses"].append(grading_status)

        if latest_at and (
            node["latest_submission_at"] is None
            or latest_at > node["latest_submission_at"]
        ):
            node["latest_submission_at"] = latest_at

        if content_type_id:
            _add_content_type_stats(
                node["by_content_type"][content_type_id],
                row,
                max_assignments,
                submitted_assignments,
                graded_assignments,
                average_grading,
            )

        if is_submittable_path:
            total_max += max_assignments
            total_submitted += submitted_assignments
            total_graded += graded_assignments
            if average_grading is not None and graded_assignments > 0:
                total_grade_sum += average_grading * graded_assignments
            if latest_at and (
                latest_submission is None or latest_at > latest_submission
            ):
                latest_submission = latest_at

    return {
        "total_max_assignments": total_max,
        "total_submitted_assignments": total_submitted,
        "overall_progress_percentage": _percentage(total_submitted, total_max),
        "latest_submission_at": latest_submission,
        "overall_average_grading": _average(total_grade_sum, total_graded),
        "by_content_type": _content_type_stats(by_content_type),
        "nodes": [
            _node_stats(path, node, assignment_details)
            for path, node in by_node.items()
        ],
    }


def _new_content_type_bucket() -> dict[str, Any]:
    return {"max": 0, "submitted": 0, "graded": 0, "grade_sum": 0.0}


def _new_node(path: str, path_info: dict[str, Any]) -> dict[str, Any]:
    title = path
    submittable = None
    position = None
    course_content_type_color = None

    info = path_info.get(path)
    if isinstance(info, dict):
        title = info.get("title", path)
        submittable = info.get("submittable")
        position = info.get("position")
        course_content_type_color = info.get("course_content_type_color")
    elif info is not None:
        title = info

    return {
        "path": path,
        "title": title,
        "submittable": submittable,
        "position": position,
        "course_content_type_color": course_content_type_color,
        "max_assignments": 0,
        "submitted_assignments": 0,
        "graded_assignments": 0,
        "grade_sum": 0.0,
        "latest_submission_at": None,
        "by_content_type": defaultdict(_new_content_type_bucket),
        "grading_statuses": [],
    }


def _add_content_type_stats(
    bucket: dict[str, Any],
    row: dict[str, Any],
    max_assignments: int,
    submitted_assignments: int,
    graded_assignments: int,
    average_grading: float | None,
) -> None:
    bucket["max"] += max_assignments
    bucket["submitted"] += submitted_assignments
    bucket["graded"] += graded_assignments
    if average_grading is not None and graded_assignments > 0:
        bucket["grade_sum"] += average_grading * graded_assignments
    bucket["id"] = row.get("content_type_id")
    bucket["slug"] = row.get("content_type_slug", "")
    bucket["title"] = row.get("content_type_title")
    bucket["color"] = row.get("content_type_color")


def _content_type_stats(
    buckets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "course_content_type_id": ct_id,
            "course_content_type_slug": data.get("slug", ""),
            "course_content_type_title": data.get("title"),
            "course_content_type_color": data.get("color"),
            "max_assignments": data["max"],
            "submitted_assignments": data["submitted"],
            "progress_percentage": _percentage(data["submitted"], data["max"]),
            "latest_submission_at": None,
            "graded_assignments": data["graded"],
            "average_grading": _average(data["grade_sum"], data["graded"]),
        }
        for ct_id, data in buckets.items()
    ]


def _node_stats(
    path: str,
    node: dict[str, Any],
    assignment_details: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    is_submittable = node.get("submittable", False)
    node_graded = node["graded_assignments"]
    node_average = _average(node["grade_sum"], node_graded)
    details = assignment_details.get(path) if is_submittable and assignment_details else None

    return {
        "path": path,
        "title": node["title"],
        "submittable": node.get("submittable"),
        "position": node.get("position"),
        "course_content_type_color": node.get("course_content_type_color"),
        "max_assignments": node["max_assignments"],
        "submitted_assignments": node["submitted_assignments"],
        "progress_percentage": _percentage(
            node["submitted_assignments"],
            node["max_assignments"],
        ),
        "latest_submission_at": node["latest_submission_at"],
        "by_content_type": _content_type_stats(node["by_content_type"]),
        "grading": node_average if is_submittable else None,
        "average_grading": node_average if not is_submittable else None,
        "graded_assignments": node_graded,
        "status": aggregate_grading_status(node["grading_statuses"]),
        "latest_result_id": details.get("latest_result_id") if details else None,
        "latest_result_grade": details.get("latest_result_grade") if details else None,
        "latest_result_status": details.get("latest_result_status") if details else None,
        "latest_result_created_at": details.get("latest_result_created_at")
        if details else None,
        "test_runs_count": details.get("test_runs_count") if details else None,
        "max_test_runs": details.get("max_test_runs") if details else None,
        "submissions_count": details.get("submissions_count") if details else None,
        "max_submissions": details.get("max_submissions") if details else None,
        "graded_by_course_member": details.get("graded_by_course_member")
        if details else None,
    }


def _percentage(value: int, total: int) -> float:
    return round((value / total * 100) if total > 0 else 0.0, 2)


def _average(grade_sum: float, graded: int) -> float | None:
    return round(grade_sum / graded, 4) if graded > 0 else None
