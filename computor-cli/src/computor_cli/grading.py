"""CLI commands for course member grading statistics."""

import click
import json
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async


def _select_course(client) -> str | None:
    """Fetch tutor courses and let the user pick one interactively."""
    courses = run_async(client.tutors.get_courses())

    if not courses:
        click.echo("No courses found. You may not have tutor access to any course.")
        return None

    click.echo("\nAvailable courses:\n")
    for idx, course in enumerate(courses, 1):
        click.echo(f"  ({idx}) {course.title or course.path}")

    choice = click.prompt(
        "\nSelect course",
        type=click.IntRange(1, len(courses)),
    )
    return courses[choice - 1].id


# ── Output helpers ──────────────────────────────────────────────────────


def _format_grade(value) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _format_date(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value[:16]
    return value.strftime("%Y-%m-%d %H:%M")


def _print_course_table(gradings):
    """Print course gradings as a formatted table."""
    # Header
    header = f"{'Name':<30} {'Student ID':<14} {'Progress':>9} {'Submitted':>11} {'Grade':>7} {'Last Submission':<18}"
    click.echo(header)
    click.echo("-" * len(header))

    for g in gradings:
        name = f"{g.family_name or ''}, {g.given_name or ''}".strip(", ")
        student_id = g.student_id or "-"
        progress = f"{g.overall_progress_percentage:.1f}%"
        submitted = f"{g.total_submitted_assignments}/{g.total_max_assignments}"
        grade = _format_grade(g.overall_average_grading)
        last_sub = _format_date(g.latest_submission_at)

        click.echo(f"{name:<30} {student_id:<14} {progress:>9} {submitted:>11} {grade:>7} {last_sub:<18}")

    click.echo(f"\n{len(gradings)} members total")


def _print_member_tree(data):
    """Print member grading as a hierarchy tree."""
    name = f"{data.given_name or ''} {data.family_name or ''}".strip()
    click.echo(f"Student:  {name}" + (f" ({data.student_id})" if data.student_id else ""))
    click.echo(f"Progress: {data.overall_progress_percentage:.1f}% ({data.total_submitted_assignments}/{data.total_max_assignments})")
    click.echo(f"Grade:    {_format_grade(data.overall_average_grading)}")

    if data.by_content_type:
        click.echo("\nBy content type:")
        for ct in data.by_content_type:
            click.echo(f"  {ct.course_content_type_slug:<20} {ct.progress_percentage:>6.1f}%  {ct.submitted_assignments}/{ct.max_assignments}  grade: {_format_grade(ct.average_grading)}")

    if not data.nodes:
        return

    click.echo("\nAssignments:")

    for node in data.nodes:
        depth = node.path.count(".")
        indent = "  " * (depth + 1)
        label = node.title or node.path.split(".")[-1]

        if node.submittable:
            status_str = "[submitted]" if node.submitted_assignments > 0 else "[missing]"
            grade_str = _format_grade(node.grading)
            grading_status = f"  ({node.status})" if node.status else ""
            click.echo(f"{indent}{label:<40} {status_str:<14} grade: {grade_str}{grading_status}")
        else:
            progress = f"{node.progress_percentage:.1f}%"
            grade_str = _format_grade(node.average_grading)
            click.echo(f"{indent}{label:<40} {progress:>8}  grade: {grade_str}")


def _gradings_to_csv_rows(gradings) -> list[dict]:
    """Convert course gradings list to flat dicts for CSV/DataFrame export."""
    rows = []
    for g in gradings:
        row = {
            "course_member_id": g.course_member_id,
            "course_id": g.course_id,
            "user_id": g.user_id,
            "username": g.username,
            "given_name": g.given_name,
            "family_name": g.family_name,
            "student_id": g.student_id,
            "total_max_assignments": g.total_max_assignments,
            "total_submitted_assignments": g.total_submitted_assignments,
            "overall_progress_percentage": g.overall_progress_percentage,
            "overall_average_grading": g.overall_average_grading,
            "latest_submission_at": str(g.latest_submission_at) if g.latest_submission_at else None,
        }
        # Flatten by_content_type into columns
        for ct in g.by_content_type:
            slug = ct.course_content_type_slug
            row[f"{slug}_max"] = ct.max_assignments
            row[f"{slug}_submitted"] = ct.submitted_assignments
            row[f"{slug}_progress"] = ct.progress_percentage
            row[f"{slug}_grade"] = ct.average_grading
        rows.append(row)
    return rows


def _member_nodes_to_csv_rows(data) -> list[dict]:
    """Convert member grading nodes to flat dicts for CSV/DataFrame export."""
    rows = []
    for node in data.nodes:
        rows.append({
            "course_member_id": data.course_member_id,
            "student_id": data.student_id,
            "given_name": data.given_name,
            "family_name": data.family_name,
            "path": node.path,
            "title": node.title,
            "submittable": node.submittable,
            "max_assignments": node.max_assignments,
            "submitted_assignments": node.submitted_assignments,
            "progress_percentage": node.progress_percentage,
            "grading": node.grading,
            "average_grading": node.average_grading,
            "status": node.status,
            "latest_submission_at": str(node.latest_submission_at) if node.latest_submission_at else None,
        })
    return rows


def _write_output(data_dicts, output_path: str, fmt: str):
    """Write data to file in the specified format."""
    if fmt == "json":
        with open(output_path, "w") as f:
            json.dump(data_dicts, f, indent=2, default=str)
        click.echo(f"Written {len(data_dicts)} entries to {output_path}")

    elif fmt == "csv":
        import csv
        if not data_dicts:
            click.echo("No data to write.")
            return
        fieldnames = list(data_dicts[0].keys())
        # Collect all keys across all rows (content type columns may vary)
        for row in data_dicts:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_dicts)
        click.echo(f"Written {len(data_dicts)} rows to {output_path}")


# ── Commands ────────────────────────────────────────────────────────────


@click.group()
def grading():
    """Course member grading statistics."""
    pass


@grading.command("course")
@click.option("--course-id", "-c", help="Course ID (prompts for selection if omitted)")
@click.option("--output", "-o", type=click.Path(), help="Save to file instead of printing")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv"]), default="json", help="Output format for --output (default: json)")
@click.option("--json", "raw_json", is_flag=True, help="Print raw JSON to stdout")
@authenticate
def grading_course(course_id, output, fmt, raw_json, auth: CLIAuthConfig):
    """Show grading statistics for all members in a course."""
    client = run_async(get_computor_client(auth))

    if course_id is None:
        course_id = _select_course(client)
        if course_id is None:
            return

    gradings = run_async(client.course_member_gradings.list(course_id=course_id))

    if not gradings:
        click.echo("No grading data found.")
        return

    if output:
        rows = _gradings_to_csv_rows(gradings) if fmt == "csv" else [g.model_dump(mode="json") for g in gradings]
        _write_output(rows, output, fmt)
    elif raw_json:
        for entry in gradings:
            click.echo(entry.model_dump_json(indent=2))
    else:
        _print_course_table(gradings)


@grading.command("member")
@click.argument("course_member_id")
@click.option("--output", "-o", type=click.Path(), help="Save to file instead of printing")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv"]), default="json", help="Output format for --output (default: json)")
@click.option("--json", "raw_json", is_flag=True, help="Print raw JSON to stdout")
@authenticate
def grading_member(course_member_id, output, fmt, raw_json, auth: CLIAuthConfig):
    """Show detailed grading statistics for a specific course member."""
    client = run_async(get_computor_client(auth))

    data = run_async(client.course_member_gradings.get(course_member_id))

    if output:
        rows = _member_nodes_to_csv_rows(data) if fmt == "csv" else data.model_dump(mode="json")
        _write_output(rows if fmt == "csv" else [rows], output, fmt)
    elif raw_json:
        click.echo(data.model_dump_json(indent=2))
    else:
        _print_member_tree(data)
