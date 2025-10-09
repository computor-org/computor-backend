"""CLI command for generating TypeScript API clients."""

from __future__ import annotations

from pathlib import Path

import click

from computor_backend.scripts.generate_typescript_clients import main as generate_ts_clients


@click.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Output directory for generated clients (default: frontend/src/api/generated)",
)
@click.option(
    "--clean",
    is_flag=True,
    help="Clean output directory before generating",
)
@click.option(
    "--include-timestamps/--no-include-timestamps",
    default=False,
    help="Include \"Generated on\" timestamps in client headers",
)
def generate_clients(output_dir: Path | None, clean: bool, include_timestamps: bool) -> None:
    """Generate TypeScript API clients from backend interfaces."""

    generated = generate_ts_clients(output_dir=output_dir, clean=clean, include_timestamp=include_timestamps)

    click.echo(click.style(f"✅ Generated {len(generated)} client files", fg="green"))


if __name__ == "__main__":
    generate_clients()
