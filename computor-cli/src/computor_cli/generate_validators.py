"""CLI command for generating TypeScript validation classes."""

from __future__ import annotations

from pathlib import Path

import click

from computor_backend.scripts.generate_pydantic_schemas import main as export_schemas_func
from computor_backend.scripts.generate_typescript_validators import main as generate_validators_func


@click.command(name="generate-validators")
@click.option(
    "--schema-dir",
    "-s",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Directory containing JSON schema files (default: frontend/src/types/schemas)",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Output directory for validators (default: frontend/src/types/validators)",
)
@click.option(
    "--include-timestamps/--no-include-timestamps",
    default=False,
    help="Include generation timestamps in output files",
)
@click.option(
    "--export-schemas",
    is_flag=True,
    help="Export JSON schemas from Pydantic models before generating validators",
)
def generate_validators_cmd(
    schema_dir: Path | None,
    output_dir: Path | None,
    include_timestamps: bool,
    export_schemas: bool,
) -> None:
    """Generate TypeScript validation classes from Pydantic schemas."""

    # Determine paths
    backend_dir = Path(__file__).parent.parent
    src_dir = backend_dir.parent
    project_root = src_dir.parent

    if schema_dir is None:
        schema_dir = project_root / "frontend" / "src" / "types" / "schemas"

    if output_dir is None:
        output_dir = project_root / "frontend" / "src" / "types" / "validators"

    # Export schemas if requested
    if export_schemas:
        click.echo(click.style("📦 Exporting JSON schemas from Pydantic models...", fg="cyan"))
        export_schemas_func(output_dir=schema_dir, include_timestamp=include_timestamps)
        click.echo("")

    # Generate validators
    click.echo(click.style("🔧 Generating TypeScript validation classes...", fg="cyan"))
    generated_files = generate_validators_func(
        schema_dir=schema_dir,
        output_dir=output_dir,
        include_timestamp=include_timestamps
    )

    click.echo("")
    click.echo(click.style(f"✅ Generated {len(generated_files)} validator files", fg="green"))


if __name__ == "__main__":
    generate_validators_cmd()