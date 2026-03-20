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


@click.group()
def grading():
    """Course member grading statistics."""
    pass


@grading.command("course")
@click.option("--course-id", "-c", help="Course ID (prompts for selection if omitted)")
@authenticate
def grading_course(course_id, auth: CLIAuthConfig):
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

    for entry in gradings:
        click.echo(entry.model_dump_json(indent=4))


@grading.command("member")
@click.argument("course_member_id")
@authenticate
def grading_member(course_member_id, auth: CLIAuthConfig):
    """Show detailed grading statistics for a specific course member."""
    client = run_async(get_computor_client(auth))

    grading = run_async(client.course_member_gradings.get(course_member_id))
    click.echo(grading.model_dump_json(indent=4))
