"""CLI command for generating VS Code JSON schema."""

from __future__ import annotations

import click

from computor_backend.scripts.generate_json_schema import main as generate_schema_main


@click.command(name="generate-schema")
@click.option(
    "--include-timestamp/--no-include-timestamp",
    default=False,
    help="Include generation timestamp in the output schema (added as x-generated-on)",
)
def generate_schema(include_timestamp: bool = False) -> None:
    """Generate JSON schema for extension metadata files."""

    generate_schema_main(include_timestamp=include_timestamp)
    click.echo(click.style("✅ JSON schema generation complete", fg="green"))


if __name__ == "__main__":
    generate_schema()
